# check_workspace_type.py
import os
from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

try:
    response = client.auth_test()
    team_id = response.get("team_id", "")
    team_name = response.get("team", "")
    
    print(f"✅ Connected to: {team_name}")
    print(f"   Team ID: {team_id}")
    
    if team_id.startswith("T0"):
        print("   ⚠️ This is a TRIAL workspace — restricted API access")
        print("   → Bot events (messages) will NOT work")
    else:
        print("   ✅ This is a STANDARD workspace — full API access")
        
except Exception as e:
    print(f"❌ Failed: {e}")