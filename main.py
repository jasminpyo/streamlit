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

bedrock = setup_bedrock()
kb_id = os.getenv('KNOWLEDGE_BASE_ID')

# Authentication Process
if "auth" not in st.session_state: # alter so its "if KEY not in"
    st.session_state.auth = False

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# CSV file
df = pd.read_csv('SLATE_Query_With_Names_Formatted.csv')

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
                # Call Bedrock Knowledge Base
                response = bedrock.retrieve_and_generate(
                    # augmented prompt / LLM instructions
                    input={
                        'text': (
                            "You are a helpful assistant. "
                            "Always respond in clear, concise sentences. "
                            "If you are unsure of the answer, ask the user to clarify their question. "
                            "After clarification, if you don't know the answer, tell the user to contact the math department. "
                            "When using the knowledge base please keep the current date and time in mind: "
                            f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                            "When you use information from the knowledge base, cite it at the end.\n\n"
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