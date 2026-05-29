# test_slack.py
import os
from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest

print("Testing Slack connection...")

# Test Bot Token
bot_token = os.getenv("SLACK_BOT_TOKEN")
web_client = WebClient(token=bot_token)

try:
    response = web_client.auth_test()
    print(f"✅ Bot Token works! Bot name: {response['user']}")
except Exception as e:
    print(f"❌ Bot Token failed: {e}")

# Test App Token (Socket Mode)
app_token = os.getenv("SLACK_APP_TOKEN")

if app_token and app_token.startswith("xapp-"):
    print(f"✅ App Token found: {app_token[:15]}...")
else:
    print("❌ App Token missing or invalid (should start with xapp-)")

print("\nTokens ready to use!")