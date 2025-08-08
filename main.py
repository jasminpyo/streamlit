import streamlit as st
import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

# Setup
st.set_page_config(page_title="Simple RAG Chatbot", page_icon="🤖")
st.title("Simple RAG Chatbot")

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
    return boto3.client(
        'bedrock-agent-runtime',
        # aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        # aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        # region_name=os.getenv('AWS_DEFAULT_REGION')
    )

# Initialize
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "student_info" not in st.session_state:
    st.session_state.student_info = None

bedrock = setup_bedrock()
kb_id = os.getenv('KNOWLEDGE_BASE_ID')
student_df = load_student_data()

# Authentication Check
if not st.session_state.authenticated:
    st.subheader("Student Authentication Required")
    student_id = st.text_input("Enter your Student ID:", type="password")
    
    if st.button("Login"):
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
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Logout button
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.student_info = None
        st.session_state.messages = []
        st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask me anything about Cal Poly San Luis Obispo's math placement system..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
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
                            "type": "KNOWLEDGE_BASE",
                            "knowledgeBaseConfiguration": {
                                "knowledgeBaseId": kb_id,
                                'modelArn': f'arn:aws:bedrock:us-west-2::foundation-model/{os.getenv("BEDROCK_MODEL_ID")}',
                                "generationConfiguration": {
                                    # Temperature control
                                    # "temperature": 0.3,
                                    # Guardrail config as documented
                                    "guardrailConfiguration": {
                                        "guardrailId": os.getenv("GUARDRAIL_ID"),
                                        "guardrailVersion": os.getenv("GUARDRAIL_VERSION")
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
                    print(e)
                    st.error(f"Error: {e}")
