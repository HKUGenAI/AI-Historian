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

print(setup.image_search_index_name)
image_index = SearchIndex(
    name=setup.image_search_index_name,
    fields=[
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="Image_name", type="Edm.String", analyzer_name="standard.lucene", 
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Image_path", type="Edm.String", analyzer_name="standard.lucene",
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
setup.index_client.create_or_update_index(image_index)