"""Shared AI clients — Ollama (primary) and Claude via claude-max-proxy (legacy)."""
import json
import os
import urllib.request as _ur
from urllib.request import Request

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://ollama:11434")
OLLAMA_MODEL = "kimi-k2.5:cloud"
# Thinking models need a large num_predict budget (thinking tokens + output tokens)
OLLAMA_NUM_PREDICT = 16000

CLAUDE_API_BASE = os.environ.get("CLAUDE_API_BASE", "http://claude-max-proxy:8318/v1")


def call_ollama(prompt: str, *, num_predict: int = None, timeout: int = 300) -> str:
    """Call Ollama (kimi-k2.5:cloud). Returns assistant message text."""
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": num_predict or OLLAMA_NUM_PREDICT},
    }).encode()
    req = _ur.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=body,
        headers={"content-type": "application/json"},
    )
    with _ur.urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    return d["message"]["content"]


def search_web(prompt: str, *, max_uses: int = 3, max_tokens: int = 1024,
               timeout: int = 45) -> dict:
    """Call Haiku via claude-max-proxy /v1/messages with web_search tool.

    Returns {"text": str, "urls": [{"url": str, "title": str}, ...]}.
    Routes through claude-max-proxy's Anthropic passthrough (OAuth auth handled by proxy).
    """
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "tools": [{"type": "web_search_20250305", "name": "web_search",
                    "max_uses": max_uses}],
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = Request(
        f"{CLAUDE_API_BASE}/messages",
        data=body,
        headers={
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    # Plain urlopen — HTTP to ai_net, no proxy needed
    with _ur.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    # Extract text blocks
    text_parts = [b["text"] for b in data.get("content", [])
                  if b.get("type") == "text"]
    text = "\n".join(text_parts).strip()

    # Extract URLs from web_search_tool_result blocks
    urls = []
    for block in data.get("content", []):
        if block.get("type") == "web_search_tool_result":
            for r in block.get("content", []):
                if r.get("type") == "web_search_result":
                    urls.append({"url": r["url"], "title": r.get("title", "")})

    return {"text": text, "urls": urls}


def call_claude(model: str, user_content: str, *,
                system: str = None, max_tokens: int = 4096,
                timeout: int = 180) -> str:
    """Call Claude via claude-max-proxy (Anthropic /v1/messages format).

    model: "claude-sonnet-4", "claude-opus-4", or "claude-haiku-4"
    Returns the assistant message text.
    """
    # Map short names to full model IDs for the Anthropic API
    _MODEL_MAP = {
        "claude-sonnet-4": "claude-sonnet-4-20250514",
        "claude-opus-4": "claude-opus-4-20250514",
        "claude-haiku-4": "claude-haiku-4-5-20251001",
    }
    model_id = _MODEL_MAP.get(model, model)

    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_content}],
    }
    if system:
        payload["system"] = system

    body = json.dumps(payload).encode()

    req = Request(
        f"{CLAUDE_API_BASE}/messages",
        data=body,
        headers={
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    with _ur.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    return data["content"][0]["text"]
