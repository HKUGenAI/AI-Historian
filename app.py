import os
import base64
import re
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter
from pypdf import PdfReader, PdfWriter
import openai
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import gradio as gr

# Get Environment Settings from .env file
load_dotenv()

# Get Azure Search API Keys
# service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
# index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
# index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

# Azure OpenAI Settings
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.azure_endpoint = os.getenv("OPENAI_API_ENDPOINT")
openai.api_version = os.getenv("OPENAI_API_VERSION")

azure_openai_client = AzureOpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
    api_version = os.getenv("OPENAI_API_VERSION"),
    azure_endpoint = os.getenv("OPENAI_API_ENDPOINT")
)

# query = "What is the capital of Angola?"
# messages = [
#     {'role' : 'user', 'content' : query }
# ]
# testresponse = openai.chat.completions.create(
#         model = 'trygpt4o', 
#         messages = messages,
#         temperature = 0.7,
#         max_tokens = 1024,
#         n=1)

# print(testresponse.choices[0].message.content)

def chatInterface(message, history):
    history_openai = []
    for user, assistant in history:
        history_openai.append({'role': 'user', 'content': user})
        history_openai.append({'role': 'assistant', 'content': assistant})
    history_openai.append({'role': 'user', 'content': message})

    response = azure_openai_client.chat.completions.create(
        model = 'trygpt4o', 
        messages = history_openai,
        temperature = 0.7,
        max_tokens = 4096)
    
    return response.choices[0].message.content

gr.ChatInterface(chatInterface).launch()

