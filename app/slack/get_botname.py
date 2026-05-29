# get_bot_name.py
import os
from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient

# Use your actual token directly for testing

client = WebClient(token=token)

try:
    response = client.auth_test()
    print(f"✅ Bot Name: {response['user']}")
    print(f"   Bot ID: {response['user_id']}")
    print(f"   Workspace: {response['team']}")
    print(f"\n👉 Invite your bot using: /invite @{response['user']}")
except Exception as e:
    print(f"❌ Error: {e}")