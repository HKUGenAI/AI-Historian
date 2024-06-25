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
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import gradio as gr

# Get Environment Settings from .env file
load_dotenv(find_dotenv())

# Get Azure Search API Keys
service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_TEXT")

## Create a client for querying the index
search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=index_creds)
index_client = SearchIndexClient(service_endpoint, index_creds)

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

# Index the database
sections = []
with open('./OHNO/ch1to3.csv', 'rt', newline='', encoding='utf-8', errors='ignore') as csvfile:
    csvreader = csv.reader(csvfile)
    for item in csvreader:
        section = {
            "id": f"{item[0]}-{item[1]}-{item[2]}",
            "Chapter": item[0],
            "Section": item[1],
            "Paragraph": item[2],
            "Content": item[3],
            "Embedding": get_embedding(item[3]),
        }
        sections.append(section)
print(f"Finished Indexing: {len(sections)} items in total")

# Update azure search index with new indexed database
index = SearchIndex(
    name=index_name,
    fields=[
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="Chapter", type="Edm.String", analyzer_name="standard.lucene", 
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Section", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Paragraph", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),        
        SearchableField(name="Content", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchField(name="Embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),  
            hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
            vector_search_dimensions=1536, vector_search_profile_name="my-vector-config"),
    ],
    vector_search=VectorSearch(
        profiles=[VectorSearchProfile(
            name="my-vector-config",
            algorithm_configuration_name="my-hnsw")
        ],
        algorithms=[
            HnswAlgorithmConfiguration(name="my-hnsw")
        ]
    )
)
index_client.create_or_update_index(index)

# Define system message for AI assistant behavior
systemMessage = """AI Assistant that helps user to answer questions from sources provided. Be brief in your answers.
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
    r = search_client.search(
        search_text=None,
        top=3,
        vector_queries=[VectorizedQuery(
            vector=query_vector,
            fields="Embedding"
        )]
    )
    search_results = []
    for result in r:
        search_results.append("Source: " + result["id"] + "; Content: " + result["Content"])

    for user, system in history:
        history_openai.append({'role': 'user', 'content': user})
        history_openai.append({'role': 'system', 'content': system})
    history_openai.append({'role': 'user', 'content': message + "   Source:" + " ".join(search_results)})

    response = azure_openai_client.chat.completions.create(
        model = 'summer', 
        messages = history_openai,
        temperature = 0.7,
    )
    
    return response.choices[0].message.content

gr.ChatInterface(fn=chatInterface,title="HKU AI Historian").launch()

