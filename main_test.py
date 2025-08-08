import streamlit as st
import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

# Setup
st.set_page_config(page_title="MR. MINI CLINT", page_icon="🧮")

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&display=swap');

.stApp {
    background-color: #F8F8F8;
}

h1 {
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    color: #154734;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 2rem;
}

.stChatMessage {
    margin: 10px 0;
    border-radius: 15px;
}
            
.stChatMessage[data-testid="user-message"] {
    background-color: #e0e0e0;
    margin-left: 20%;
}

/* div[data-testid="stChatMessage"] {
    background-color: #ffd9b3;
    color: black;
} */


.stChatMessage[data-testid="assistant-message"] {
    background-color: #154734;
    color: white;
    margin-right: 20%;
}

.stChatInput input {
    border-radius: 25px;
    border: 2px solid #154734;
}

.stButton button {
    background-color: #154734;
    color: white;
    border-radius: 25px;
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
}

.stTextInput input {
    border-radius: 25px;
    border: 2px solid #154734;
}

hr {
    border: none;
    height: 2px;
    background-color: #154734;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Display Cal Poly logo at top
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("calpoly-logo.png", width=150)


# Initialize
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "student_info" not in st.session_state:
    st.session_state.student_info = None

st.title("MR. MINI CLINT")
st.markdown('<hr style="border: none; height: 2px; background-color: #154734; margin: 20px 0;">', unsafe_allow_html=True)

if st.session_state.authenticated == True:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.student_info = None
        st.session_state.messages = []
        st.rerun()

# Student Data Setup
@st.cache_data
def load_student_data():
    try:
        return pd.read_csv('SLATE_Query_With_Names_Formatted.csv')
    except FileNotFoundError:
        st.error("Student data file not found")
        return pd.DataFrame()

def find_student_data(df, student_id):
    if df.empty:
        return None
    
    # Find student based on ID
    row = df[df['EMPLID'] == int(student_id)]
    if not row.empty:
        return row.iloc[0].to_dict()
    else:
        return None

# Authentication Setup
def authenticate_student(df, student_id):
    if df.empty:
        return False, None
    
    matches = df[df['EMPLID'] == int(student_id)]
    if not matches.empty:
        return True, matches.iloc[0].to_dict()
    else:
        return False, None

# AWS Setup
@st.cache_resource
def setup_bedrock():
    session_token = os.getenv('AWS_SESSION_TOKEN')
    if session_token:
        return boto3.client(
            'bedrock-agent-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=session_token,
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )
    else:
        return boto3.client(
            'bedrock-agent-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )



bedrock = setup_bedrock()
kb_id = os.getenv('KNOWLEDGE_BASE_ID')
student_df = load_student_data()

# Authentication Check
if not st.session_state.authenticated:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Welcome! Please sign in")
        student_id = st.text_input("Enter your Student ID:", type="password", placeholder="Student ID")
        
        # Button layout
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Login", use_container_width=True):
                if student_id:
                    is_valid, student_data = authenticate_student(student_df, student_id)
                    if is_valid:
                        st.session_state.authenticated = True
                        st.session_state.student_info = student_data
                        st.success("Authentication successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Student ID. Please try again.")
                else:
                    st.error("Please enter your Student ID.")
        
        with btn_col2:
            if st.button("Guest", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.student_info = {"name": "Guest User", "EMPLID": "guest"}
                st.success("Welcome, Guest!")
                st.rerun()
else:
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar='🐴'):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar='🧮'):
                st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Math ain't mathing? Ask me..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar='🐴'):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant", avatar='🧮'):
            with st.spinner("Thinking..."):
                try:
                    # Use authenticated student data
                    student_context = f"\n\nStudent Data: {st.session_state.student_info}"
                    
                    # Get last 5 messages for context
                    recent_messages = st.session_state.messages[-5:] if len(st.session_state.messages) >= 5 else st.session_state.messages
                    chat_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

                    # Call Bedrock Knowledge Base
                    response = bedrock.retrieve_and_generate(
                        # augmented prompt / LLM instructions
                        input={
                            'text': (
                                "You are a helpful and encouraging assistant for Cal Poly's math department. "
                                "Always respond in clear, concise sentences. Format your response in short, accessable paragraphs. No more than 5 sentences per paragraph. Be as helpful as possible and ensure the user does not have to email the math department."
                                "Use bullet points, bolding, italics, headers, hyperlinks, and other formatting options to separate text and make it readable. "
                                "Your priority is to provide students with advice and information about the department and its courses as well as information about math placement. "
                                "Requests for unrelated information (e.g., cooking recipes, movie reviews, personal advice, roleplay, general trivia) should be politefully declined. "
                                "Friendly conversation like saying 'Hi' or 'Hello' should still be allowed and is not considered off-topic. "
                                 f"{'For the very first response, start with a casual greeting using the time of day and the student\'s first name (e.g., "Good evening, Blake!"). Do not greet in subsequent responses. ' if len(st.session_state.messages) == 1 else ''}"
                                "If the user asks about potential math placement, reply with particular courses they all elligible for take using all the information provided. "
                                "State which specific Cal Poly courses the student is eligible to enroll in (e.g., A score of 5 on the AP Calculus AB exam gives you credit for MATH 141 and allows you to enroll in MATH 142), as well as their next available courses. "
                                "If the user does not provide the year in which they took a particular exam, such as AP or SAT, clarify which year the exam was taken. When the user gives you the year, answer their previous question."
                                "For the resources and next steps you are referencing include any links that the user would find useful in accomplishing those tasks. "
                                "If you are unsure of the answer, ask the user to clarify their question. "
                                "If the next steps you are providing have a resource availaible also provide a link to that resource. "
                                "After clarification, if the question hasn't been answered with complete certainty, tell the user to contact the math department. "
                                "When using the knowledge base please keep the current date and time in mind: "
                                f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                                "When you use information from the knowledge base, cite it at the end."
                                "If student data is provided, use it to give personalized assistance. "
                                f"Student Context: {student_context}\n\n"
                                f"Recent Chat History: {chat_history}\n\n"
                                f"User question: {prompt}"
                            )
                        },
                        retrieveAndGenerateConfiguration={
                            'type': 'KNOWLEDGE_BASE',
                            'knowledgeBaseConfiguration': {
                                'knowledgeBaseId': kb_id,
                                'modelArn': f'arn:aws:bedrock:us-west-2::foundation-model/{os.getenv("BEDROCK_MODEL_ID")}',
                                'generationConfiguration': {
                                    'guardrailConfiguration': {
                                        'guardrailId': os.getenv('GUARDRAIL_ID'),
                                        'guardrailVersion': os.getenv('GUARDRAIL_VERSION')
                                    }
                                }
                            }
                        }
                    )
                    
                    answer = response['output']['text']
                    st.write(answer)
                    
                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Logout button at bottom
    