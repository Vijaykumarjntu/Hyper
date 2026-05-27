# test_notion.py
import os
from dotenv import load_dotenv
load_dotenv()

from notion_client import Client

# Initialize
notion = Client(auth=os.getenv("NOTION_API_KEY"))

# List all pages the integration can access
print("Finding accessible pages...")
search_results = notion.search(filter={"property": "object", "value": "page"})

pages = search_results.get("results", [])
print(f"✅ Found {len(pages)} pages\n")

for page in pages[:3]:  # Show first 3
    page_id = page["id"]
    title = page.get("properties", {}).get("title", {}).get("title", [{}])[0].get("plain_text", "Untitled")
    print(f"  📄 {title} (ID: {page_id})")
    
    # Get page content
    blocks = notion.blocks.children.list(page_id)
    print(f"     Blocks: {len(blocks['results'])}")