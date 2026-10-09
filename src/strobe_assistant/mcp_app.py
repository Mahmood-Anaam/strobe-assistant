"""Dedicated MCP server exposing retrieval tools to the Strobe agent."""

import hmac
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .container import Container

container = Container.build()
mcp = FastMCP("Strobe MCP", stateless_http=True, json_response=True)


def _search(query: str, user_id: str, top_k: int) -> list[dict[str, Any]]:
    embedding = container.bedrock.embed_text(query)
    results = []
    for result in container.vector_store.search(embedding, user_id, top_k):
        item = result.to_dict()
        item["image_url"] = container.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": container.settings.media_bucket, "Key": result.object_key},
            ExpiresIn=300,
        )
        results.append(item)
    return results


@mcp.tool()
def search_photos(query: str, user_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Semantically search one Strobe user's classified photos."""

    return _search(query, user_id, top_k)


@mcp.tool()
def get_recent_posts(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent posts owned by one Strobe user."""

    return container.repository.list_posts(user_id, limit)


@mcp.tool()
def get_agent_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Return persisted scheduled heartbeat records."""

    return container.repository.list_agent_runs(limit)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_id: str = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = container.settings.mcp_api_key
    if expected and (not x_api_key or not hmac.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Invalid MCP API key")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Strobe MCP Server", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/tools/search", dependencies=[Depends(require_api_key)])
def search(request: SearchRequest) -> dict[str, Any]:
    return {"results": _search(request.query, request.user_id, request.top_k)}


@app.get("/api/tools/posts/{user_id}", dependencies=[Depends(require_api_key)])
def posts(user_id: str, limit: int = 10) -> dict[str, Any]:
    return {"posts": container.repository.list_posts(user_id, min(max(limit, 1), 50))}


@app.get("/api/tools/runs", dependencies=[Depends(require_api_key)])
def runs(limit: int = 10) -> dict[str, Any]:
    return {"runs": container.repository.list_agent_runs(min(max(limit, 1), 50))}


app.mount("/mcp", mcp.streamable_http_app())
