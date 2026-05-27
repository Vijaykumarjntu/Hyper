"""
Hyper — Notion Ingestion Webhook
Listens for Notion page changes → extracts text → stores in Pinecone
"""

import os
import hashlib
import logging
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.notion_client_helper import extract_page_text
from app.memory import upsert_to_pinecone

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("hyper.ingest")

app = FastAPI(title="Hyper — Notion Ingestion", version="0.1.0")

WEBHOOK_SECRET = os.getenv("NOTION_WEBHOOK_SECRET", "")

def _verify_signature(raw_body: bytes, signature: str) -> bool:
    """Optional HMAC verification if Notion sends a secret header."""
    if not WEBHOOK_SECRET:
        return True  # skip verification when secret not configured
    expected = "sha256=" + hashlib.sha256(
        (WEBHOOK_SECRET + raw_body.decode()).encode()
    ).hexdigest()
    return signature == expected


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hyper-notion-ingest", "ts": datetime.utcnow().isoformat()}

@app.post("/")
async def homepage(request:Request):
    body = await request.json()
    print(body)
    print(request)
    return {"status":"ok","message":"hello"}
@app.post("/webhook/notion")
async def notion_webhook(
    request: Request,
    x_notion_signature: str = Header(default=""),
):
    raw_body = await request.body()

    # ── Signature check ───────────────────────────────────────────────────────
    if not _verify_signature(raw_body, x_notion_signature):
        log.warning("Invalid webhook signature — rejecting request")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("type", "")
    log.info(f"Received Notion event: {event_type}")

    # ── Only care about page-level changes ────────────────────────────────────
    if event_type not in ("page.created", "page.updated", "page.content_updated"):
        return JSONResponse({"status": "ignored", "event": event_type})

    page_id: str = (
        payload.get("entity", {}).get("id")          # newer Notion format
        or payload.get("page_id")                     # older format
        or ""
    )

    if not page_id:
        raise HTTPException(status_code=400, detail="Could not resolve page_id from payload")

    # ── Extract text from Notion ───────────────────────────────────────────────
    log.info(f"Extracting text from page {page_id}")
    page_data = await extract_page_text(page_id)

    if not page_data["text"].strip():
        log.info(f"Page {page_id} has no text content — skipping")
        return JSONResponse({"status": "skipped", "reason": "empty_content", "page_id": page_id})

    # ── Upsert into Pinecone ───────────────────────────────────────────────────
    log.info(f"Upserting page {page_id} → Pinecone  ({len(page_data['text'])} chars)")
    result = await upsert_to_pinecone(page_data)

    log.info(f"✓ Ingested page {page_id} — {result['chunks']} chunks stored")
    return JSONResponse({
        "status": "ok",
        "page_id": page_id,
        "title": page_data["title"],
        "chunks_stored": result["chunks"],
    })
