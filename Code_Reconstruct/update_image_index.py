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
 
# prints parent directory
parent_dir = os.path.dirname(path)
print(parent_dir)

csv_path = os.path.join(parent_dir, "outputupdated.csv")

images = []
batch_num = 1 # The batch of images uploaded
with open(csv_path, 'rt', newline='', encoding='utf-8', errors='ignore') as csvfile:
    csvreader = csv.reader(csvfile)
    item_num = 1
    for item in csvreader:
        image_item = {
            "id": f"{batch_num}-{item_num}",
            "Image_name": item[0],
            "Image_path": item[1],
            "Caption": item[4],
            "Embedding": setup.get_embedding(f"{item[0]}. {item[4]}")
        }
        item_num += 1
        images.append(image_item)
print(f"Finished Indexing: {len(images)} items in total")

image_upload_results = setup.image_search_client.upload_documents(documents=images)
print("Uploading")
succeeded = sum([1 for r in image_upload_results if r.succeeded])
print(f"Indexed {len(image_upload_results)} sections, {succeeded} succeeded")