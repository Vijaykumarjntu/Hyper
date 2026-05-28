# ai_proxy.py
import os
import json
import httpx
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Hyper AI Proxy")

# Initialize Hyper's memory
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("hyper-test")
model = SentenceTransformer('all-MiniLM-L6-v2')

# AI providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def get_relevant_context(query: str, top_k: int = 3) -> str:
    """Search Pinecone for relevant knowledge from your team"""
    print(query)
    query_vector = model.encode(query)
    print("this is the query")
    print("now we are inside the get relevant context")
    print("this is the vector")
    print(query)
    print(query_vector.tolist())
    index = pc.Index("hyper-test")
    results = index.query(
        vector=query_vector.tolist(),
        top_k=top_k,
        include_metadata=True
    )
    # index = pc.Index(host="INDEX_HOST")

    # results = index.search(
    #     namespace="example-namespace", 
    #     query={
    #         "inputs": {"text": "Disease prevention"}, 
    #         "top_k": 2
    #     },
    #     fields=["category", "chunk_text"]
    # )

    print(results)
    print("these are the results")
    print(results)

    if not results['matches']:
        return ""
    
    context_parts = []
    for match in results['matches']:
        if match['score'] > 0.1:  # Only include relevant matches
            metadata = match.get('metadata', {})
            source = metadata.get('source', 'unknown')
            context_parts.append(f"[From {source}]: {match['id']}")
    
    if not context_parts:
        return ""
    
    return "Relevant context from your team:\n" + "\n".join(context_parts)

@app.post("/v1/chat/completions")
async def proxy_chat_completion(request: Request):
    """Intercept OpenAI/Claude requests and inject Hyper context"""
    print("we are inside the chat completions")
    body = await request.json()
    messages = body.get("messages", [])
    
    # Get the last user message
    # user_messages = [m for m in messages if m.get("role") == "user"]
    user_messages = True 
    if user_messages:
        # last_user_query = user_messages[-1].get("content", "")
        
        # Get relevant context from Hyper
        print(body)
        print(type(body))
        print("this is just below body")
        ip = body["input"]
        print(ip)

        print(type(ip))
        hyper_context = get_relevant_context(ip)
        print("this is the hyper context")
        print(hyper_context)
        if hyper_context:
            # print(f"🔍 Found context for: '{last_user_query[:50]}...'")
            print(f"🔍 Found context for: '{ip}...'")
            
            # Inject as system message
            system_message = {
                "role": "system",
                "content": hyper_context + "\n\nUse the above context to answer the user's question accurately."
            }
            messages.insert(0, system_message)
            print(f"   ✅ Injected {hyper_context.count('[From')} context items")
    
    # Forward to actual API
    provider = body.get("provider", "openai")  # or "anthropic"
    print("provider is ")
    print(provider)
    if provider == "openai":
        return await proxy_openai(body, messages)
    elif provider == "anthropic":
        return await proxy_anthropic(body, messages)
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")

async def proxy_openai(original_body: dict, modified_messages: list):
    """Forward to OpenAI"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": original_body.get("model", "gpt-3.5-turbo"),
        "messages": modified_messages,
        "temperature": original_body.get("temperature", 0.7),
        "stream": original_body.get("stream", False)
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        print("this is the response of open ai proxy")
        print(response)
        
        if original_body.get("stream"):
            print("if block working")
            return StreamingResponse(response.aiter_bytes())
        else:
            print("else block working")
            return JSONResponse(content=response.json())

async def proxy_anthropic(original_body: dict, modified_messages: list):
    """Forward to Anthropic Claude"""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    # Convert OpenAI format to Anthropic format
    user_content = "\n".join([m["content"] for m in modified_messages if m["role"] == "user"])
    system_prompts = [m["content"] for m in modified_messages if m["role"] == "system"]
    
    payload = {
        "model": original_body.get("model", "claude-3-haiku-20240307"),
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": original_body.get("max_tokens", 1024)
    }
    
    if system_prompts:
        payload["system"] = "\n".join(system_prompts)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        return JSONResponse(content=response.json())

@app.get("/health")
async def health():
    stats = index.describe_index_stats()
    return {
        "status": "alive",
        "vectors": stats["total_vector_count"],
        "proxy": "ready"
    }

@app.post("/responses")
async def proxy(request:Request):
    data = await request.json()
    print(data)
    # Return the structure OpenAI client expects
    await proxy_chat_completion(request)

    return JSONResponse(content={
        "id": "resp_123",
        "object": "response",
        "model": "gpt-3.5-turbo",
        "output_text": "Once upon a time, there was a magical unicorn who lived in a rainbow forest...",
        "output": [
            {
                "type": "message",
                "role": "assistant", 
                "content": "Once upon a time, there was a magical unicorn who lived in a rainbow forest..."
            }
        ]
    })
    # return JSONResponse(content="this is the response from the hyper interceptor")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Hyper AI Proxy running on http://localhost:8000")
    print("   Set your AI tools to use: http://localhost:8000/v1/chat/completions")
    uvicorn.run(app, host="0.0.0.0", port=8000)