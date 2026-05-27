# debug_notion.py
import os
from dotenv import load_dotenv
load_dotenv()

from notion_client import Client

notion = Client(auth=os.getenv("NOTION_API_KEY"))

print("Testing different search methods...\n")

# Method 1: Search with no filter
print("1. Search (no filter):")
results = notion.search()
print(f"   Found: {len(results.get('results', []))} items\n")

# Method 2: Search only pages
print("2. Search (pages only):")
results = notion.search(filter={"property": "object", "value": "page"})
print(f"   Found: {len(results.get('results', []))} pages\n")

# Method 3: List users (to confirm API works)
print("3. Testing API connection by listing users:")
try:
    users = notion.users.list()
    print(f"   ✅ API works! Found {len(users.get('results', []))} users in workspace")
except Exception as e:
    print(f"   ❌ API error: {e}")

# Method 4: Get a specific page (if you know the ID)
print("\n4. To manually share a page:")
print("   - Open any Notion page")
print("   - Click '...' → 'Connections' → 'Add connections'")
print("   - Select your integration name")
print("   - Then re-run this script")