# slack_debug.py
import os
from dotenv import load_dotenv
load_dotenv()

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest

# Get tokens
app_token = os.getenv("SLACK_APP_TOKEN")
bot_token = os.getenv("SLACK_BOT_TOKEN")

if not app_token or not bot_token:
    print("❌ Missing tokens in .env file")
    print("   SLACK_BOT_TOKEN should start with xoxb-")
    print("   SLACK_APP_TOKEN should start with xapp-")
    exit(1)

print(f"✅ Bot token found: {bot_token[:15]}...")
print(f"✅ App token found: {app_token[:15]}...")

# Create the client
client = SocketModeClient(
    app_token=app_token,
    logger=None  # Use default logger
)

# Define a handler that prints EVERYTHING
def process(client: SocketModeClient, req: SocketModeRequest):
    print("\n" + "="*50)
    print(f"📨 Received event type: {req.type}")
    print(f"   Full payload: {req.payload}")
    
    if req.type == "events_api":
        event = req.payload.get("event", {})
        event_type = event.get("type")
        print(f"   Event subtype: {event_type}")
        
        if event_type == "message":
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text", "")
            print(f"   📝 MESSAGE: #{channel} | {user} | {text[:100]}")
    
    # ALWAYS acknowledge the event so Slack knows we received it
    req.ack()

client.socket_mode_request_listeners.append(process)

print("\n🚀 Connecting to Slack...")
try:
    client.connect()
    print("✅ Connected! Waiting for messages...")
    print("   Send a message in any channel your bot is in, and watch this terminal.\n")
    
    import time
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n👋 Disconnecting...")
    client.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")