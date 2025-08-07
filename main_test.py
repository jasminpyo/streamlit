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
                    
                    # Call Bedrock Knowledge Base
                    response = bedrock.retrieve_and_generate(
                        # augmented prompt / LLM instructions
                        input={
                            'text': (
                                "You are a helpful assistant for Cal Poly's math placement system. "
                                "Always respond in clear, concise sentences. "
                                "If student data is provided, use it to give personalized assistance. "
                                "If you are unsure of the answer, ask the user to clarify their question. "
                                "After clarification, if you don't know the answer, tell the user to contact the math department. "
                                "When using the knowledge base please keep the current date and time in mind: "
                                f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                                "When you use information from the knowledge base, cite it at the end."
                                "If student data is provided, use it to give personalized assistance. "
                                f"{student_context}\n\n"
                                f"User question: {prompt}"
                            )
                        },
                        retrieveAndGenerateConfiguration={
                            'type': 'KNOWLEDGE_BASE',
                            'knowledgeBaseConfiguration': {
                                'knowledgeBaseId': kb_id,
                                'modelArn': f'arn:aws:bedrock:us-west-2::foundation-model/{os.getenv("BEDROCK_MODEL_ID")}'
                            }
                        }
                    )
                    
                    answer = response['output']['text']
                    st.write(answer)
                    
                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"Error: {e}")