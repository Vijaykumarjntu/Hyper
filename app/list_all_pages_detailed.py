# list_all_pages_detailed.py
import os
from dotenv import load_dotenv
load_dotenv()

from notion_client import Client

notion = Client(auth=os.getenv("NOTION_API_KEY"))

print("Listing all accessible pages with their content...\n")

results = notion.search(filter={"property": "object", "value": "page"})

for page in results.get("results", []):
    page_id = page["id"]
    
    # Get title
    title = "Untitled"
    try:
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_text = prop.get("title", [])
                if title_text:
                    title = title_text[0].get("plain_text", "Untitled")
                    break
    except:
        pass
    
    # Get block count
    blocks = notion.blocks.children.list(page_id)
    block_count = len(blocks.get("results", []))
    
    # Get preview of content
    preview = ""
    for block in blocks.get("results", [])[:2]:
        block_type = block.get("type")
        if block_type and block.get(block_type, {}).get("rich_text"):
            rich_text = block[block_type]["rich_text"]
            if rich_text:
                preview = rich_text[0].get("plain_text", "")[:50]
                break
    
    print(f"📄 Title: {title}")
    print(f"   ID: {page_id}")
    print(f"   Blocks: {block_count}")
    print(f"   Preview: {preview if preview else '(empty)'}")
    print()