# notion_ingestion.py (FIXED - grabs title and all properties)
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from notion_client import Client
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

notion = Client(auth=os.getenv("NOTION_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("hyper-test")
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_all_text_from_page(page_id):
    """Extract ALL text including title, properties, and blocks"""
    all_texts = []
    
    try:
        # Get the page
        page = notion.pages.retrieve(page_id)
        
        # Extract from ALL properties (including title)
        props = page.get("properties", {})
        for prop_name, prop_value in props.items():
            prop_type = prop_value.get("type")
            
            # Title property
            if prop_type == "title":
                title_parts = prop_value.get("title", [])
                for part in title_parts:
                    if part.get("plain_text"):
                        text = part["plain_text"]
                        all_texts.append(text)
                        print(f"   Found title text: '{text[:100]}'")
            
            # Rich text property
            elif prop_type == "rich_text":
                text_parts = prop_value.get("rich_text", [])
                for part in text_parts:
                    if part.get("plain_text"):
                        text = part["plain_text"]
                        all_texts.append(text)
                        print(f"   Found rich text: '{text[:100]}'")
            
            # Other property types that might contain text
            elif prop_type in ["select", "multi_select", "status"]:
                if prop_value.get(prop_type):
                    name = prop_value[prop_type].get("name", "") if isinstance(prop_value[prop_type], dict) else str(prop_value[prop_type])
                    if name:
                        all_texts.append(name)
        
        # Also get blocks (in case there are any)
        blocks = notion.blocks.children.list(page_id)
        
        def extract_from_block(block):
            texts = []
            block_type = block.get("type")
            if block_type:
                block_content = block.get(block_type, {})
                if "rich_text" in block_content:
                    for rich_text in block_content["rich_text"]:
                        if rich_text.get("plain_text"):
                            texts.append(rich_text["plain_text"])
                if "title" in block_content:
                    for title_part in block_content["title"]:
                        if title_part.get("plain_text"):
                            texts.append(title_part["plain_text"])
            return texts
        
        for block in blocks.get("results", []):
            texts = extract_from_block(block)
            all_texts.extend(texts)
            
            # Check children
            if block.get("has_children"):
                children = notion.blocks.children.list(block["id"])
                for child in children.get("results", []):
                    child_texts = extract_from_block(child)
                    all_texts.extend(child_texts)
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return " ".join(all_texts)

def store_page(page_id):
    """Extract and store page content"""
    print(f"\n📄 Processing page: {page_id}")
    
    try:
        # Get page metadata
        page = notion.pages.retrieve(page_id)
        
        # Extract all content
        content = extract_all_text_from_page(page_id)
        
        print(f"\n   Total content length: {len(content)} chars")
        
        if not content or len(content) < 10:
            print(f"   ⏭️ Skipping: not enough content")
            return
        
        print(f"   Full content preview: {content[:300]}...")
        
        # Create embedding
        vector = model.encode(content)
        
        # Store in Pinecone
        doc_id = f"notion_{page_id}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        index.upsert(vectors=[(
            doc_id,
            vector.tolist(),
            {
                "source": "notion",
                "page_id": page_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )])
        
        print(f"   ✅ Stored in Pinecone!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_ingest():
    """Ingest all accessible pages"""
    print("🔍 Looking for pages to ingest...\n")
    
    # Get all pages
    search_results = notion.search(filter={"property": "object", "value": "page"})
    pages = search_results.get("results", [])
    
    if not pages:
        print("❌ No pages found.")
        return
    
    print(f"Found {len(pages)} page(s)\n")
    
    # Process each page
    for page in pages:
        page_id = page["id"]
        store_page(page_id)
    
    # Verify
    print("\n" + "="*50)
    stats = index.describe_index_stats()
    print(f"📊 Total vectors in Pinecone: {stats['total_vector_count']}")

if __name__ == "__main__":
    test_ingest()