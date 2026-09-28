import os

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

load_dotenv()

BASE_URL = os.getenv("ANYTHING_LLM_BASE_URL", "http://localhost:3001").rstrip("/")
API_KEY = os.getenv("ANYTHING_LLM_API_KEY", "")
WORKSPACE_SLUG = os.getenv("ANYTHING_LLM_WORKSPACE_SLUG", "")

server = MCPServer(
    name="anythingllm-mcp",
    title="AnythingLLM Workspace MCP",
    version="0.1.0",
)


@server.tool()
async def ask_workspace(question: str) -> str:
    """Answer a question using information from the configured AnythingLLM workspace (RAG retrieval)."""
    if not API_KEY or not WORKSPACE_SLUG:
        raise ValueError("ANYTHING_LLM_API_KEY and ANYTHING_LLM_WORKSPACE_SLUG must be set in .env")

    payload = {
        "message": question,
        "mode": "query",
        "sessionId": "mcp-mvp",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("type") != "textResponse":
        return f"error: {data.get('error') or 'unexpected response'}"
    return data.get("textResponse", "")


app = server.streamable_http_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)