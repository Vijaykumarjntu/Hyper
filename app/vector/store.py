import pinecone
from app.vector.embed import embed_text
import os

# Initialize Pinecone once
pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENVIRONMENT")
)

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "hyper-mvp")

def get_index():
    if INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(
            INDEX_NAME,
            dimension=384,  # MiniLM dimension
            metric="cosine",
            metadata_config={"indexed": ["source", "tool", "timestamp"]}
        )
    return pinecone.Index(INDEX_NAME)

def upsert_doc(doc_id: str, text: str, metadata: dict):
    """Store a document and its embedding."""
    index = get_index()
    vector = embed_text(text)
    index.upsert(vectors=[(doc_id, vector, metadata)])

def query_similar(text: str, top_k: int = 5, filter_dict: dict = None):
    """Retrieve top-k similar documents."""
    index = get_index()
    query_vector = embed_text(text)
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict
    )
    return results.matches