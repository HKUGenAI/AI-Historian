import os
import base64
import re
import csv
from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import openai
from openai import AzureOpenAI


# Get Environment settings from .env file
load_dotenv()

# Azure AI Search Index Settings
service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
text_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_TEXT")
image_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_IMAGE")

## Create a client for handling creation of indexes
index_client = SearchIndexClient(service_endpoint, index_creds)
## Create a client for querying the index
text_search_client = SearchClient(endpoint=service_endpoint, index_name=text_search_index_name, credential=index_creds)
image_search_client = SearchClient(endpoint=service_endpoint, index_name=image_search_index_name, credential=index_creds)

# Azure Openai Settings
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.azure_endpoint = os.getenv("OPENAI_API_ENDPOINT")
openai.api_version = os.getenv("OPENAI_API_VERSION")

azure_openai_client = AzureOpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
    api_version = os.getenv("OPENAI_API_VERSION"),
    azure_endpoint = os.getenv("OPENAI_API_ENDPOINT")
)

# Text Embedding (model=[Deployment Name], DONOT change this)
text_embedding_model = os.getenv("TEXT_EMBEDDING_MODEL_NAME")
def get_embedding(text, model=text_embedding_model): # model=[Deployment Name], DONOT change this
   text = text.replace("\n", " ")
   return azure_openai_client.embeddings.create(input = [text], model=model).data[0].embedding