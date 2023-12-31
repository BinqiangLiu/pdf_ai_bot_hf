import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.embeddings import HuggingFaceEmbeddings, SentenceTransformerEmbeddings
from langchain import HuggingFaceHub
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from htmlTemplates import bot_template, user_template, css
from transformers import pipeline
import sys
import os
from dotenv import load_dotenv

HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
repo_id=os.getenv("repo_id")

def get_pdf_text(pdf_files):    
    text = ""
    for pdf_file in pdf_files:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def get_chunk_text(text):    
    text_splitter = CharacterTextSplitter(
    separator = "\n",
    chunk_size = 1000,
    chunk_overlap = 200,
    length_function = len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    # For OpenAI Embeddings    
    #embeddings = OpenAIEmbeddings()    
    # For Huggingface Embeddings
    #embeddings = HuggingFaceInstructEmbeddings(model_name = "hkunlp/instructor-xl")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") 
    vectorstore = FAISS.from_texts(texts = text_chunks, embedding = embeddings)
    return vectorstore

def get_conversation_chain(vector_store):   
    # OpenAI Model
    #llm = ChatOpenAI()
    #HuggingFace Model
    #llm = HuggingFaceHub(repo_id="google/flan-t5-xxl")
    #llm = HuggingFaceHub(repo_id="tiiuae/falcon-40b-instruct", model_kwargs={"temperature":0.5, "max_length":512}) #出现超时timed out错误
    #llm = HuggingFaceHub(repo_id="meta-llama/Llama-2-70b-hf", model_kwargs={"min_length":100, "max_length":1024,"temperature":0.1})
    #repo_id="HuggingFaceH4/starchat-beta"
    llm = HuggingFaceHub(repo_id=repo_id,
                         model_kwargs={"min_length":1024,
                                       "max_new_tokens":5632, "do_sample":True,
                                       "temperature":0.1,
                                       "top_k":50,
                                       "top_p":0.95, "eos_token_id":49155}) 
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm = llm,
        retriever = vector_store.as_retriever(),
        memory = memory
    )
    print("***Start of printing Conversation_Chain***")
    print(conversation_chain)
    print("***End of printing Conversation_Chain***")
    st.write("***Start of printing Conversation_Chain***")
    st.write(conversation_chain)
    st.write("***End of printing Conversation_Chain***")    
    return conversation_chain

def handle_user_input(question):
    response = st.session_state.conversation({'question':question})    
    st.session_state.chat_history = response['chat_history']
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            
def main():
    load_dotenv()
    st.set_page_config(page_title='Chat with Your own PDFs', page_icon=':books:')
    st.write(css, unsafe_allow_html=True)    
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    st.header('Chat with Your own PDFs :books:')
    question = st.text_input("Ask anything to your PDF: ")
    if question:
        handle_user_input(question)  
    with st.sidebar:
        st.subheader("Upload your Documents Here: ")
        pdf_files = st.file_uploader("Choose your PDF Files and Press OK", type=['pdf'], accept_multiple_files=True)
        if st.button("OK"):
            with st.spinner("Processing your PDFs..."):
                # Get PDF Text
                raw_text = get_pdf_text(pdf_files)
                # Get Text Chunks
                text_chunks = get_chunk_text(raw_text)               
                # Create Vector Store                
                vector_store = get_vector_store(text_chunks)
                st.write("DONE")
                # Create conversation chain
                st.session_state.conversation =  get_conversation_chain(vector_store)

if __name__ == '__main__':
    main()
