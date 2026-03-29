import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX")
NAMESPACE = "__default__"   

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

search_text = "What is the representation space?"

response = index.search(
    namespace=NAMESPACE,
    query={
        "inputs": {"text": search_text},
        "top_k": 5
    },
    fields=["text", "source", "topic"]   
)

print(response)