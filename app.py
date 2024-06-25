import os
import base64
import re
import csv
from dotenv import load_dotenv, find_dotenv
from pypdf import PdfReader, PdfWriter
from pypdf import PdfReader, PdfWriter
import openai
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import gradio as gr

# Get Environment Settings from .env file
load_dotenv(find_dotenv())

# Get Azure Search API Keys
service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
text_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_TEXT")
image_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_IMAGE")

## Create a client for updating the index
text_search_client = SearchClient(endpoint=service_endpoint, index_name=text_index_name, credential=index_creds)
image_search_client = SearchClient(endpoint=service_endpoint, index_name=image_index_name, credential=index_creds)

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

print("Successfully validated azure credentials")

# Embedding model for indexing database and search queries
def get_embedding(text, model="textembedding"): # model=[Deployment Name], DONOT change this
   text = text.replace("\n", " ")
   return azure_openai_client.embeddings.create(input = [text], model=model).data[0].embedding

# Define system message for AI assistant behavior
systemMessage = """AI Assistant that helps user to answer questions from sources provided.
                    Answer ONLY with the facts listed in the list of sources below. 
                    If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. 
                    Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. 
                    Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
                """
history_openai = [
    {'role' : 'user', 'content' : systemMessage},
    {'role' : 'system', 'content' : ""}
]

# Run the chatbot using Gradio's ChatInterface Abstraction
def chatInterface(message, history):
    query_vector = get_embedding(message)
    r = text_search_client.search(
        search_text=None,
        top=3,
        vector_queries=[VectorizedQuery(
            vector=query_vector,
            fields="Embedding"
        )]
    )
    text_search_results = []
    for result in r:
        text_search_results.append("Source: " + result["id"] + "; Content: " + result["Content"])

    for user, system in history:
        history_openai.append({'role': 'user', 'content': user})
        history_openai.append({'role': 'system', 'content': system})
    history_openai.append({'role': 'user', 'content': message + "   Source:" + " ".join(text_search_results)})

    response = azure_openai_client.chat.completions.create(
        model = 'summer', 
        messages = history_openai,
        temperature = 0.7,
    )

    r = image_search_client.search(
        search_text=None,
        top=3,
        vector_queries=[VectorizedQuery(
            vector=query_vector,
            fields="Embedding"
        )]
    )

    image_search_results = []
    for result in r:
        image_search_results.append("\nImage: " + result["Image_name"] + "; Caption: " + result["Caption"])
        
    return response.choices[0].message.content + "\n" + "".join(image_search_results)

gr.ChatInterface(fn=chatInterface,title="HKU AI Historian").launch()

