import os
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
text_index_client = SearchIndexClient(service_endpoint, index_creds)
image_index_client = SearchIndexClient(service_endpoint, index_creds)

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

# Index the text database
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

# Update azure search text index
text_index = SearchIndex(
    name=text_index_name,
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
text_index_client.create_or_update_index(text_index)

results = text_search_client.upload_documents(documents=sections)
print("Uploading")
succeeded = sum([1 for r in results if r.succeeded])
print(f"Indexed {len(results)} sections, {succeeded} succeeded")
batch = []

print("Successfully updated text index")




# Index the image database
sections = []
with open('./OHNO/outputupdated.csv', 'rt', newline='', encoding='utf-8', errors='ignore') as csvfile:
    csvreader = csv.reader(csvfile)
    item_num = 0
    for item in csvreader:
        section = {
            "id": f"{item_num}",
            "Image_name": item[0],
            "Image_path": item[1],
            "Response1": item[2],
            "Response2": item[3],
            "Caption": item[4],
            "Embedding": get_embedding(''.join(item[0:5]))
        }
        item_num += 1
        sections.append(section)
print(f"Finished Indexing: {len(sections)} items in total")

# Update azure search image index
image_index = SearchIndex(
    name=image_index_name,
    fields=[
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="Image_name", type="Edm.String", analyzer_name="standard.lucene", 
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Image_path", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Response1", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Response2", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Caption", type="Edm.String", analyzer_name="standard.lucene",
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

image_index_client.create_or_update_index(image_index)

results = image_search_client.upload_documents(documents=sections)
print("Uploading")
succeeded = sum([1 for r in results if r.succeeded])
print(f"Indexed {len(results)} sections, {succeeded} succeeded")
batch = []

print("Successfully updated image index")