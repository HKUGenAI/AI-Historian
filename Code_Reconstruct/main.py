# Standard library imports
import base64, csv, os, re

# Third-party imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI

# Application-specific imports
import setup

def get_embedding(client, text, model="textembedding"): # model=[Deployment Name], DONOT change this
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

def create_index(name):
    index = SearchIndex(
        name=name,
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

def section_files(client, filename):
    print("Indexing...")
    sections = []
    with open(filename, 'rt', newline='', encoding='utf-8', errors='ignore') as csvfile:
        csvreader = csv.reader(csvfile)
        for item in csvreader:
            section = {
                "id": f"{item[0]}-{item[1]}-{item[2]}",
                "Chapter": item[0],
                "Section": item[1],
                "Paragraph": item[2],
                "Content": item[3],
                "Embedding": get_embedding(client, item[3]),
            }
            sections.append(section)
    print(f"Finished Indexing: {len(sections)} items in total")
    return sections

def upload_sections(client, sections):
    print("Uploading...")
    results = client.upload_documents(documents=sections)
    succeeded = sum([1 for r in results if r.succeeded])
    print(f"Uploaded {len(results)} sections, {succeeded} succeeded")

def main():
    file_sections = section_files(azure_openai_client, "data/ch4to6.csv")
    create_index("ch4to6")
    upload_sections(text_search_client, file_sections)

if __name__ == "__main__":
    text_search_client, image_search_client, index_client, azure_openai_client = setup.setup()
    main()