"""Minimal client for a local Ollama server (stdlib only — no new dependency).

Talks to Ollama's HTTP API at http://localhost:11434 and strips qwen3's
<think>...</think> reasoning block so it never reaches the player or the
database. See the "Local model notes" in CLAUDE.md.

Environment:
- OLLAMA_HOST                  (default http://localhost:11434)
- WORLD_ENGINE_OLLAMA_MODEL    (default huihui_ai/qwen3-abliterated:8b-v2)
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv(
    "WORLD_ENGINE_OLLAMA_MODEL", "huihui_ai/qwen3-abliterated:8b-v2"
)

# Matches a well-formed <think> ... </think> block (any case, across newlines).
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class OllamaError(RuntimeError):
    """Raised with a human-readable message when Ollama can't be used."""


def strip_think(text: str | None) -> str:
    """Remove qwen3 reasoning so only the spoken line remains.

    Handles three shapes robustly:
    - a complete <think>...</think> block,
    - an unclosed <think> with no closing tag (drop to the end),
    - reasoning that ends in a stray </think> with no opening tag (drop the head).
    """
    if not text:
        return ""
    # 1. Remove complete blocks.
    text = _THINK_BLOCK.sub("", text)
    # 2. Drop an unclosed <think> ... running to the end.
    open_idx = text.lower().find("<think>")
    if open_idx != -1:
        text = text[:open_idx]
    # 3. Drop an orphan reasoning head ending in </think>.
    close_idx = text.lower().rfind("</think>")
    if close_idx != -1:
        text = text[close_idx + len("</think>"):]
    return text.strip()


def _connection_error(host: str, exc: Exception) -> OllamaError:
    return OllamaError(
        f"Ollama is not reachable at {host}. Is the server running? "
        f"Start it with `ollama serve`.\n  (underlying error: {exc})"
    )


def ping(host: str = OLLAMA_HOST, timeout: float = 5.0) -> list[str]:
    """Return the list of locally available model names, or raise OllamaError."""
    url = f"{host}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # reachable but unhappy
        raise OllamaError(f"Ollama returned HTTP {exc.code} from {url}.") from exc
    except urllib.error.URLError as exc:
        raise _connection_error(host, exc.reason) from exc
    except OSError as exc:
        raise _connection_error(host, exc) from exc
    return [model.get("name", "") for model in body.get("models", [])]


def chat(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    host: str = OLLAMA_HOST,
    timeout: float = 300.0,
) -> str:
    """Send a chat request; return the assistant content WITH the think block stripped.

    `messages` is a list of {"role": "system"|"user"|"assistant", "content": str}.
    """
    url = f"{host}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        if exc.code == 404 or "not found" in detail.lower():
            raise OllamaError(
                f"Model '{model}' is not available in Ollama. "
                f"Pull it first: `ollama pull {model}`."
            ) from exc
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise _connection_error(host, exc.reason) from exc
    except OSError as exc:
        raise _connection_error(host, exc) from exc

    if body.get("error"):
        raise OllamaError(f"Ollama error: {body['error']}")
    content = body.get("message", {}).get("content", "")
    return strip_think(content)
