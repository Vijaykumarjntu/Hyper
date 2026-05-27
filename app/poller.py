# test_notion.py
import asyncio
import os
from notion_client import AsyncClient
from dotenv import load_dotenv

load_dotenv()

_notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))

async def test():
    results = await _notion.search(
        filter={"property": "object", "value": "page"},
    )
    pages = results.get("results", [])
    print(f"Total pages found: {len(pages)}")
    for page in pages:
        print(f"  - {page.get('id')} | {page.get('last_edited_time')}")

asyncio.run(test())