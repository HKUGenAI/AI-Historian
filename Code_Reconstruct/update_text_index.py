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

import setup

# get current directory
path = os.getcwd()
print("Current Directory", path)
 
# get data directory
data_dir = os.path.join(path, "data")

csv_path = os.path.join(data_dir, "ch4to6.csv")

sections = []
with open(csv_path, 'rt', newline='', encoding='utf-8', errors='ignore') as csvfile:
    csvreader = csv.reader(csvfile)
    for item in csvreader:
        section = {
            "id": f"{item[0]}-{item[1]}-{item[2]}",
            "Chapter": item[0],
            "Section": item[1],
            "Paragraph": item[2],
            "Content": item[3],
            "Embedding": setup.get_embedding(item[3]),
        }
        sections.append(section)
print(f"Finished Indexing: {len(sections)} items in total")


text_upload_results = setup.text_search_client.upload_documents(documents=sections)
print("Uploading")
succeeded = sum([1 for r in text_upload_results if r.succeeded])
print(f"Indexed {len(text_upload_results)} sections, {succeeded} succeeded")