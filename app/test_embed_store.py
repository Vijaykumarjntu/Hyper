# test_embed_store.py (UPDATED for new Pinecone API)
import os
from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

print("=" * 50)
print("TEST 1: Loading embedding model")
print("=" * 50)

model = SentenceTransformer('all-MiniLM-L6-v2')
test_text = "Hyper learns from every update in your team's tools"
vector = model.encode(test_text)

print(f"✅ Model loaded")
print(f"   Vector shape: {vector.shape}")
print()

# ============================================

print("=" * 50)
print("TEST 2: Connecting to Pinecone (new API)")
print("=" * 50)

api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    print("❌ Missing PINECONE_API_KEY in .env file")
    print("\nCreate a .env file with:")
    print("PINECONE_API_KEY=your-key-here")
    exit(1)

# Initialize with JUST the API key (no environment!)
pc = Pinecone(api_key=api_key)
print("✅ Connected to Pinecone")

# ============================================

print("=" * 50)
print("TEST 3: Creating index")
print("=" * 50)

index_name = "hyper-test"

# List existing indexes
existing_indexes = [idx.name for idx in pc.list_indexes()]
print(f"Existing indexes: {existing_indexes}")

if index_name in existing_indexes:
    print(f"⚠️ Index '{index_name}' exists, deleting...")
    pc.delete_index(index_name)

# Create new index (serverless, no environment needed)
print(f"Creating index '{index_name}'...")
pc.create_index(
    name=index_name,
    dimension=384,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"  # You can change this
    )
)

print(f"✅ Index '{index_name}' created")

# ============================================

print("=" * 50)
print("TEST 4: Storing a vector")
print("=" * 50)

index = pc.Index(index_name)

doc_id = "doc_001"
index.upsert(vectors=[
    (doc_id, vector.tolist(), {"source": "test"})
])

print(f"✅ Stored document '{doc_id}'")

stats = index.describe_index_stats()
print(f"   Total vectors: {stats['total_vector_count']}")

# ============================================

print("=" * 50)
print("TEST 5: Querying")
print("=" * 50)

query_text = "How does team knowledge work?"
query_vector = model.encode(query_text)

results = index.query(
    vector=query_vector.tolist(),
    top_k=3,
    include_metadata=True
)

print(f"Query: '{query_text}'")
for match in results['matches']:
    print(f"   Score: {match['score']:.4f} - {match['id']}")

print()
print("✅ ALL TESTS PASSED")