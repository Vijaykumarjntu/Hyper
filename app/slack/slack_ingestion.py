# slack_webhook.py
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import re
from fastapi import FastAPI, Request, BackgroundTasks
from slack_sdk import WebClient
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Initialize FastAPI
app = FastAPI(title="Hyper Slack Webhook")

# Initialize clients
slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("hyper-test")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Configuration
MIN_MESSAGE_LENGTH = 15
SKIP_PATTERNS = ["thanks", "lgtm", "+1", "👍", "🙏", "ack", "hello", "hi"]

def is_noise(text: str) -> bool:
    text_lower = text.lower()
    for pattern in SKIP_PATTERNS:
        if pattern in text_lower and len(text) < 30:
            return True
    return False

async def process_slack_event(body: dict):
    """Process Slack event - THIS WAS MISSING"""
    event = body.get("event", {})
    event_type = event.get("type")
    print("now processing has started")
    print(body)
     # Handle app_mention (someone mentioned @Hyper)
    if event_type == "app_mention":
        channel = event.get("channel")
        user = event.get("user", "unknown")
        text = event.get("text", "").strip()
        ts = event.get("ts")
        
        # Remove the bot mention from text
        clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
        if clean_text:
            channel_name = channel
            try:
                info = slack_client.conversations_info(channel=channel)
                channel_name = info["channel"]["name"]
            except:
                pass
            
            print(f"\n🔔 @Hyper mentioned in #{channel_name}:")
            print(f"   User: {user}")
            print(f"   Question: {clean_text[:100]}...")
            
            store_slack_message(channel_name, user, f"[MENTION] {clean_text}", ts)

            try:
                slack_client.chat_postMessage(
                    channel=channel,
                    text=f"👋 Got it! I'll remember that. (Hyper is learning...)"
                )
            except:
                pass
        
        return {"status": "ok"}

    if event_type == "message":
        # Skip bot messages and threads
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return {"status": "ignored"}
        if event.get("thread_ts"):
                return {"status": "ignored"}
            
        channel = event.get("channel")
        user = event.get("user", "unknown")
        text = event.get("text", "").strip()
        ts = event.get("ts")
        if text:
                # Get channel name
                channel_name = channel
                try:
                    info = slack_client.conversations_info(channel=channel)
                    channel_name = info["channel"]["name"]
                except Exception as e:
                    print(f"   Could not get channel name: {e}")
                
                print(f"\n📨 Slack message from #{channel_name}:")
                print(f"   User: {user}")
                print(f"   Text: {text[:100]}...")

    return {"status": "ok"}


@app.post("/")
async def root_post(request: Request):
    """Handle Slack verification at root path"""
    body = await request.json()
    
    # Slack URL verification challenge
    if body.get("type") == "url_verification":
        print("✅ Slack URL verified at root path!")
        return {"challenge": body.get("challenge")}
    
    # Process regular events if they come to root
    return await process_slack_event(body)

def store_slack_message(channel: str, user: str, text: str, ts: str):
    """Store Slack message in Pinecone"""
    if is_noise(text) or len(text) < MIN_MESSAGE_LENGTH:
        print(f"   ⏭️ Skipped (noise): {text[:30]}...")
        return False
    
    # Create embedding
    vector = model.encode(text)
    
    # Create unique ID
    doc_id = f"slack_{channel}_{ts}_{hashlib.md5(text.encode()).hexdigest()[:6]}"
    
    # Store in Pinecone
    index.upsert(vectors=[(
        doc_id,
        vector.tolist(),
        {
            "source": "slack",
            "channel": channel,
            "user": user,
            "content": text[:2000],
            "timestamp": datetime.fromtimestamp(float(ts)).isoformat(),
            "message_ts": ts
        }
    )])
    
    print(f"   ✅ Stored: #{channel} | {user} | {text[:60]}...")
    return True

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Receive Slack events via webhook"""
    body = await request.json()
    
    # Slack URL verification challenge
    if body.get("type") == "url_verification":
        print("✅ Slack URL verified!")
        return {"challenge": body.get("challenge")}
    
    # Process event
    event = body.get("event", {})
    event_type = event.get("type")
    
    if event_type == "message":
        # Skip bot messages and threads
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return {"status": "ignored"}
        
        if event.get("thread_ts"):
            return {"status": "ignored"}
        
        channel = event.get("channel")
        user = event.get("user", "unknown")
        text = event.get("text", "").strip()
        ts = event.get("ts")
        
        if text:
            # Get channel name
            channel_name = channel
            try:
                info = slack_client.conversations_info(channel=channel)
                channel_name = info["channel"]["name"]
            except Exception as e:
                print(f"   Could not get channel name: {e}")
            
            print(f"\n📨 Slack message from #{channel_name}:")
            print(f"   User: {user}")
            print(f"   Text: {text[:100]}...")
            
            background_tasks.add_task(store_slack_message, channel_name, user, text, ts)
    
    return {"status": "ok"}

@app.get("/health")
async def health():
    stats = index.describe_index_stats()
    return {
        "status": "alive",
        "vectors": stats["total_vector_count"],
        "source": "slack_webhook"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Slack webhook listener running on http://localhost:8000")
    print("   Configure your Slack app Event Subscriptions to send to:")
    print("   https://YOUR_NGROK_URL.ngrok.io/slack/events\n")
    uvicorn.run(app, host="0.0.0.0", port=3000)