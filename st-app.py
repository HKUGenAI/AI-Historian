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
from filter_images import filter_images

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

systemMessage = """You are a friendly and informative AI Historian that helps user to answer questions from sources provided. Be specific in your answers.
                    Answer ONLY with the facts listed in the list of sources below. If the question is not related to the sources, politely decline. 
                    After anwering the user quesitons, start a new line and give 3 keywords (names, places, etc.) of your response. Do NOT give keywords "HKU", "The University of Hong Kong", "Hong Kong".
                    If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. 
                    Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. 
                    Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
                """
history_init = [
    {'role' : 'user', 'content' : ""},
    {'role' : 'system', 'content' : systemMessage}
]

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Initialize session state for OpenAI chat history if not already present
if "history_openai" not in st.session_state:
    st.session_state["history_openai"] = history_init


# Function to compute text embedding using Azure OpenAI
def get_embedding(text, model="textembedding"):
    text = text.replace("\n", " ")
    response = azure_openai_client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


# Function to handle user queries and generate responses
def query_and_respond(query):
    vector_query = get_embedding(query)

    # Perform text search using vector-based queries
    text_results = text_search_client.search(
        search_text=None,
        top=5,
        vector_queries=[VectorizedQuery(vector=vector_query, fields="Embedding")],
    )
    # Perform neighboring search
    sections = []
    for result in text_results:
        sections.append(result["id"])
    print(sections)
    search_text_results = []
    used_sections = []
    for sec in sections:
        doc = text_search_client.get_document(key=sec)
        if doc["id"] == "Chapter-Section-Paragraph": continue
        print(doc["id"])
        used_sections.append(doc["id"])
        search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        try:
            neighbor_sec = sec[:-2] + "-" + str(int(sec[-1]) + 1)
            if neighbor_sec not in used_sections:
                doc = text_search_client.get_document(key=neighbor_sec)
                print(doc["id"])
                used_sections.append(doc["id"])
                search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        except:
            pass
        try:
            neighbor_sec = sec[:-2] + "-" + str(int(sec[-1]) - 1)
            if neighbor_sec not in used_sections:
                doc = text_search_client.get_document(key=neighbor_sec)
                print(doc["id"])
                used_sections.append(doc["id"])
                search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        except:
            pass
    # Update conversation history for AI response
    chat_message = f"{query} Source: " + " ".join(search_text_results)
    history_openai = st.session_state["history_openai"]
    history_openai.append({"role": "user", "content": chat_message})

    # Generate AI response using chat completions
    response = azure_openai_client.chat.completions.create(
        model="summer",
        messages=history_openai,
        temperature=0.7,
    )
    history_openai.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )
    st.session_state["history_openai"] = history_openai

    # Perform image search using vector-based KEYWORDS
    chat_content = response.choices[0].message.content
    image_search_keywords = chat_content.split("\n")[-1].replace("Keywords: ", "")
    print(image_search_keywords)
    image_results = image_search_client.search(
        search_text=None,
        top=5,
        vector_queries=[VectorizedQuery(vector=get_embedding(image_search_keywords), fields="Embedding")],
    )
    image_search_results = [
        f"\nImage: {result['Image_name']}; Caption: {result['Caption']}"
        for result in image_results
    ]
    filtered_images = filter_images(azure_openai_client, chat_content, image_search_results)
    return (
        response.choices[0].message.content,
        search_text_results,
        filtered_images,
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
    print(image_result)
    if image_result != ['']:
        # Extract and display images from the search results
        file_names = []
        # viewing in a grid
        for i in range(len(image_result)):
            file_names.append("./jpg/" + str(image_result[i]))

        st.image(file_names, width=300)
