# simple_dashboard.py
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

app = FastAPI()

# Initialize
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("hyper-test")
model = SentenceTransformer('all-MiniLM-L6-v2')

# HTML directly as string
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Hyper Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            flex: 1;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }
        .search-box {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        input {
            width: 80%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin-left: 10px;
        }
        button:hover {
            background: #5a67d8;
        }
        .results {
            display: grid;
            gap: 15px;
        }
        .card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .notion { background: #e8f5e9; color: #2e7d32; }
        .slack { background: #e3f2fd; color: #1565c0; }
        .content {
            color: #555;
            margin: 10px 0;
            line-height: 1.5;
        }
        .meta {
            color: #999;
            font-size: 12px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Hyper Dashboard</h1>
            <p>Team knowledge from Notion and Slack</p>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalCount">-</div>
                <div>Total Items</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="notionCount">-</div>
                <div>From Notion</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="slackCount">-</div>
                <div>From Slack</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Ask Hyper... (e.g., deployment process)">
            <button onclick="search()">Search</button>
        </div>
        
        <div class="results" id="results">
            <div class="loading">Loading knowledge...</div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('totalCount').innerText = data.total;
                document.getElementById('notionCount').innerText = data.notion;
                document.getElementById('slackCount').innerText = data.slack;
            } catch(e) { console.error(e); }
        }
        
        async function loadRecent() {
            try {
                const res = await fetch('/api/recent');
                const data = await res.json();
                displayResults(data);
            } catch(e) { console.error(e); }
        }
        
        async function search() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            document.getElementById('results').innerHTML = '<div class="loading">Searching...</div>';
            
            try {
                const res = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await res.json();
                displayResults(data);
            } catch(e) { console.error(e); }
        }
        
        function displayResults(items) {
            if (!items || items.length === 0) {
                document.getElementById('results').innerHTML = '<div class="loading">No knowledge found yet. Add content to Notion or Slack!</div>';
                return;
            }
            
            const html = items.map(item => {
                const source = item.source || 'unknown';
                const badgeClass = source === 'notion' ? 'notion' : 'slack';
                const badgeText = source === 'notion' ? 'Notion' : 'Slack';
                const title = item.title || item.channel || 'Untitled';
                const content = (item.content || 'No content').substring(0, 300);
                const date = item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown';
                const score = item.score ? (item.score * 100).toFixed(1) : 0;
                
                return `
                    <div class="card">
                        <div class="badge ${badgeClass}">${badgeText}</div>
                        <div><strong>${escapeHtml(title)}</strong></div>
                        <div class="content">${escapeHtml(content)}${item.content?.length > 300 ? '...' : ''}</div>
                        <div class="meta">${date} ${score > 0 ? `| Score: ${score}%` : ''}</div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('results').innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        loadStats();
        loadRecent();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(HTML_PAGE)

@app.get("/api/stats")
async def get_stats():
    try:
        stats = index.describe_index_stats()
        total = stats.get('total_vector_count', 0)
        
        notion_count = 0
        slack_count = 0
        
        if total > 0:
            dummy = [0.0] * 384
            sample = index.query(vector=dummy, top_k=min(100, total), include_metadata=True)
            for match in sample.get('matches', []):
                source = match.get('metadata', {}).get('source', '')
                if source == 'notion':
                    notion_count += 1
                elif source == 'slack':
                    slack_count += 1
        
        return {"total": total, "notion": notion_count, "slack": slack_count}
    except Exception as e:
        return {"total": 0, "notion": 0, "slack": 0}

@app.get("/api/recent")
async def get_recent():
    try:
        dummy = [0.0] * 384
        results = index.query(vector=dummy, top_k=30, include_metadata=True)
        items = []
        for match in results.get('matches', []):
            meta = match.get('metadata', {})
            items.append({
                "source": meta.get('source', 'unknown'),
                "title": meta.get('title', meta.get('channel', 'Untitled')),
                "content": meta.get('content', ''),
                "timestamp": meta.get('timestamp', ''),
                "score": match.get('score', 0)
            })
        return items
    except Exception as e:
        return []

@app.get("/api/search")
async def search_query(q: str = ""):
    if not q:
        return []
    try:
        vector = model.encode(q)
        results = index.query(vector=vector.tolist(), top_k=10, include_metadata=True)
        items = []
        for match in results.get('matches', []):
            meta = match.get('metadata', {})
            items.append({
                "source": meta.get('source', 'unknown'),
                "title": meta.get('title', meta.get('channel', 'Untitled')),
                "content": meta.get('content', ''),
                "timestamp": meta.get('timestamp', ''),
                "score": match.get('score', 0)
            })
        return items
    except Exception as e:
        return []

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*40)
    print("Hyper Dashboard: http://localhost:8001")
    print("="*40 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)