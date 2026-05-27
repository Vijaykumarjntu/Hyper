# test_direct.py
import os
from dotenv import load_dotenv
load_dotenv()

from notion_client import Client

notion = Client(auth=os.getenv("NOTION_API_KEY"))

PAGE_ID = "500d592b1bb54424a75aee7345c1b5c4"

print(f"Testing direct access to page: {PAGE_ID}\n")

try:
    # Get page metadata
    page = notion.pages.retrieve(PAGE_ID)
    print("✅ Page retrieved successfully!")
    
    # Get title
    title = "Untitled"
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_text = prop.get("title", [])
            if title_text:
                title = title_text[0].get("plain_text", "Untitled")
            break
    print(f"   Title: {title}")
    
    # Get page content
    blocks = notion.blocks.children.list(PAGE_ID)
    print(f"   Number of content blocks: {len(blocks.get('results', []))}")
    
    # Show content preview
    print("\n📄 Content preview:")
    for block in blocks.get("results", [])[:5]:
        block_type = block.get("type")
        if block_type and block.get(block_type, {}).get("rich_text"):
            rich_text = block[block_type]["rich_text"]
            if rich_text:
                text = rich_text[0].get("plain_text", "")
                print(f"   - {text[:100]}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    print("\nThis means the page is NOT shared with your integration yet.")
    print("Even though you added 'hyper2', the API might need a few minutes.")
    print("\nTry:")
    print("1. Remove the connection from the page")
    print("2. Add it again")
    print("3. Wait 60 seconds")
    print("4. Run this script again")