#!/usr/bin/env python
# coding: utf-8

# !pip install openai chromadb
from extract_urls import crawl
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.indexes import VectorstoreIndexCreator
from langchain.chains import RetrievalQA
import os
import streamlit as st


# Initialize session state variables
if 'base_url' not in st.session_state:
    st.session_state['base_url'] = None
if 'urls' not in st.session_state:
    st.session_state['urls'] = None
if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'splits' not in st.session_state:
    st.session_state['splits'] = None
    

def main():
  qa_chain = None
  with st.sidebar:
    st.title("Website Chatbot")

    # options to select 
    option = st.selectbox('How would you like to proceed?',
                          ('Create Embeddings', 'Load Embeddings'))
    
    if option == "Create Embeddings":
        # User input
        base_url = st.text_input("Enter Website URL:")
        st.session_state['base_url'] = base_url
        
        if st.session_state['base_url']:
          # Get the API key
          api_key = st.text_input("Enter your OpenAI API key",
                                   help="Please ensure you have an OpenAI API account with credits.", 
                                   type="password")
          if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
          
            #url extractor
            urls = crawl(base_url, max_urls=10)
            st.session_state['urls'] = urls
            st.write("Total URLs:", len(urls))
          
            if st.session_state['urls']:        
              #loader
              loader = WebBaseLoader(st.session_state['urls'])
              data = loader.load()
              st.write("Total docs:", len(data))
              st.session_state['data'] = data
            
              #splitter
              chunk_size = st.text_input("Enter chunk size:", 1000,
                                          help="the maximum size of your chunks (as measured by the length function)")
              chunk_overlap = st.text_input("Enter chunk overlap:", 100,
                                            help="the maximum overlap between chunks. It can be nice to have some overlap to maintain some continuity between chunks (e.g. do a sliding window).")
              text_splitter = RecursiveCharacterTextSplitter(chunk_size = int(chunk_size), chunk_overlap = int(chunk_overlap))
              all_splits = text_splitter.split_documents(st.session_state['data'])
              st.write("Total splits:", len(all_splits))
              st.session_state['splits'] = all_splits
            
              #storing
              persist_directory_default = base_url[8:].replace("/", "_")+'_embeddings'
              persist_directory = st.text_input("Enter directory to store embeddings:", persist_directory_default)
              
              vectorstore = Chroma.from_documents(documents=st.session_state['splits'],  
                                                  embedding=OpenAIEmbeddings(),
                                                  persist_directory=persist_directory)
              st.write(f"document indexes are stored at {persist_directory}")
        
              #retrieval
              llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
              qa_chain = RetrievalQA.from_chain_type(llm,
                                                     retriever=vectorstore.as_retriever(),
                                                     return_source_documents=True,)                                            
        
            else:
              st.warning("No URLs found or the given website is not crawlable")
          else:
            st.warning("Please enter OpenAI API key to proceed")
        else:
          st.warning("Please enter Website URL to proceed")
    
    elif option == 'Load Embeddings':
      indices_dir = st.text_input("Enter the directory of Embeddings")
      if indices_dir:
        # Get the API key
        api_key = st.text_input("Enter your OpenAI API key",
                                   help="Please ensure you have an OpenAI API account with credits.", 
                                   type="password")
        if api_key:
          os.environ['OPENAI_API_KEY'] = api_key
          vectorstore = Chroma(persist_directory=indices_dir, embedding_function=OpenAIEmbeddings())
          st.write(f"There are {vectorstore._collection.count()} collections")
          #retrieval
          llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
          qa_chain = RetrievalQA.from_chain_type(llm,
                                                 retriever=vectorstore.as_retriever(),
                                                 return_source_documents=True,)     
        else:
          st.warning("Please enter the OpenAI API key to proceed")
      else:
        st.warning("Enter existing Embeddings directory or choose to create Embeddings")
        
  if qa_chain:
    question = st.text_area("Enter your question:")
    if st.button("Submit") and question:
      #output
      result = qa_chain({"query": question})
      st.markdown(f"## Answer: \n {result['result']} \n\n")
      with st.expander("Sources"):
        for source in result['source_documents']:
          st.markdown(f"### Title: {source.metadata['title']}\n")
          st.write(f"{source.metadata['source']}\n")
          st.write(f"{source.page_content}\n")
          st.write("--"*25)
    else:
      st.warning("Please enter a question to answer.")

if __name__ == "__main__":
    main()