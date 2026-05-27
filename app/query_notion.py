# query_notion.py
from dotenv import load_dotenv
load_dotenv()
import os

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("hyper-test")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Ask a question related to your Notion page
question = input("Ask about what you wrote in Notion: ")

vector = model.encode(question)
results = index.query(
    vector=vector.tolist(),
    top_k=3,
    include_metadata=True
)

print("\n📚 Found relevant knowledge:")
for match in results['matches']:
    print(f"   Score: {match['score']:.3f}")
    print(f"   Source: {match['metadata'].get('title', 'Unknown')}")
    print()