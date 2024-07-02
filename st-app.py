import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import openai
from openai import AzureOpenAI
import re

# Load environment variables
load_dotenv(find_dotenv())

# Configuration for Azure services
service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
text_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_TEXT")
image_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_IMAGE")

# Create clients for Azure text and image search
text_search_client = SearchClient(
    endpoint=service_endpoint, index_name=text_index_name, credential=index_creds
)
image_search_client = SearchClient(
    endpoint=service_endpoint, index_name=image_index_name, credential=index_creds
)

# Initialize Azure OpenAI client configuration
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.azure_endpoint = os.getenv("OPENAI_API_ENDPOINT")
openai.api_version = os.getenv("OPENAI_API_VERSION")
azure_openai_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_ENDPOINT"),
)

# Set the title of the Streamlit app
st.title("HKU AI Historian")

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Initialize session state for OpenAI chat history if not already present
if "history_openai" not in st.session_state:
    st.session_state["history_openai"] = []


# Function to compute text embedding using Azure OpenAI
def get_embedding(text, model="textembedding"):
    text = text.replace("\n", " ")
    response = azure_openai_client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


# Function to handle user queries and generate responses
def query_and_respond(query):
    vector = get_embedding(query)

    # Perform text search using vector-based queries
    text_results = text_search_client.search(
        search_text=None,
        top=3,
        vector_queries=[VectorizedQuery(vector=vector, fields="Embedding")],
    )
    # Perform neighboring search
    sections = []
    search_text_results=""
    for result in text_results:
        section_id = result["id"][:-2]
        if section_id not in sections:
            sections.append(section_id)
    for _section_ in sections:
        i = 1
        while(True):
            try:
                doc = text_search_client.get_document(key=f"{_section_}-{i}")
                print(doc["id"])
                search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
                i += 1
            except:
                break

    # Perform image search using vector-based queries
    image_results = image_search_client.search(
        search_text=None,
        top=3,
        vector_queries=[VectorizedQuery(vector=vector, fields="Embedding")],
    )
    image_search_results = [
        f"\nImage: {result['Image_name']}; Caption: {result['Caption']}"
        for result in image_results
    ]

    # Update conversation history for AI response
    chat_message = f"{query} Source: " + " ".join(search_text_results)
    history = st.session_state["history_openai"]
    history.append({"role": "user", "content": chat_message})

    # Generate AI response using chat completions
    response = azure_openai_client.chat.completions.create(
        model="summer",
        messages=history,
        temperature=0.7,
    )
    history.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )
    st.session_state["history_openai"] = history

    return (
        response.choices[0].message.content,
        search_text_results,
        image_search_results,
    )


# User interface for chat interaction
user_input = st.chat_input("Type your message here:")
if user_input:
    ai_response, search_results, image_result = query_and_respond(user_input)
    st.session_state["chat_history"].append({"user": "You", "message": user_input})
    st.session_state["chat_history"].append({"user": "AI", "message": ai_response})

    # Display the conversation history
    for chat in st.session_state["chat_history"]:
        st.text_area(
            f"{chat['user']}:",
            value=chat["message"],
            height=100,
            key=chat["user"] + chat["message"],
        )

    # Extract and display images from the search results
    file_name_pattern = r"Image: (.*?);"
    file_names = [
        re.search(file_name_pattern, line).group(1)
        for line in image_result
        if re.search(file_name_pattern, line)
    ]

    # viewing in a grid
    for i in range(len(file_names)):
        file_names[i] = "./jpg/" + str(file_names[i])

    st.image(file_names, width=300)
