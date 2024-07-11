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
from openai import AzureOpenAI

import setup

index = SearchIndex(
    # name=setup.text_search_index_name,
    name="friday",
    fields=[
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="Source", type="Edm.String", analyzer_name="standard.lucene", 
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchableField(name="Page", type="Edm.String", analyzer_name="standard.lucene",
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

setup.index_client.create_or_update_index(index)