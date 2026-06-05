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
from typing import Iterator

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
    format: str | dict | None = None,
) -> str:
    """Send a chat request; return the assistant content WITH the think block stripped.

    `messages` is a list of {"role": "system"|"user"|"assistant", "content": str}.
    Pass `format="json"` to enable Ollama's JSON-constrained generation (Ollama ≥ 0.1.x).
    Pass `format={...schema...}` for structured outputs (Ollama ≥ 0.4).
    """
    url = f"{host}/api/chat"
    payload: dict = {"model": model, "messages": messages, "stream": False}
    if format is not None:
        payload["format"] = format
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


class _StreamThinkFilter:
    """Stateful streaming filter that suppresses the <think>…</think> block.

    Phases
    ------
    scanning : initial; buffering until we can tell whether a think block
               is present.  Once len(buf) >= len("<think>") we know.
    thinking : inside the block; nothing yielded.
    speaking : after the block (or when confirmed absent); yield every chunk.

    Boundary robustness: "</think>" may straddle two chunks.  We keep the
    entire think-phase buffer until "</think>" is found, so no span is missed.
    """

    _OPEN  = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._buf   = ""
        self._phase = "scanning"   # scanning | thinking | speaking

    def feed(self, chunk: str) -> str:
        """Return the portion of *chunk* that should be emitted (may be "")."""
        if self._phase == "speaking":
            return chunk

        self._buf += chunk

        if self._phase == "scanning":
            lo = self._buf.lower()
            if lo.startswith(self._OPEN):
                # Might already have the close tag in the same chunk.
                ci = lo.find(self._CLOSE)
                if ci != -1:
                    after = self._buf[ci + len(self._CLOSE):]
                    self._buf = ""
                    self._phase = "speaking"
                    return after.lstrip()
                # Open tag confirmed, close tag not yet arrived.
                self._phase = "thinking"
                return ""
            if len(self._buf) >= len(self._OPEN):
                # No <think> at the start; check for orphan </think> (rare).
                ci = lo.find(self._CLOSE)
                if ci != -1:
                    after = self._buf[ci + len(self._CLOSE):]
                    self._buf = ""
                    self._phase = "speaking"
                    return after.lstrip()
                # Confirmed: no think block.  Flush buffer and start speaking.
                text, self._buf = self._buf, ""
                self._phase = "speaking"
                return text
            # Not enough chars to decide yet; keep buffering.
            return ""

        # phase == "thinking"
        ci = self._buf.lower().find(self._CLOSE)
        if ci != -1:
            after = self._buf[ci + len(self._CLOSE):]
            self._buf = ""
            self._phase = "speaking"
            return after.lstrip()
        return ""

    def flush(self) -> str:
        """Return any remaining buffered spoken text when the stream ends."""
        text = self._buf
        self._buf = ""
        # scanning: stream ended before accumulating enough chars — no think
        #   block possible, so treat the buffer as spoken content.
        # thinking: stream ended while inside a think block — discard.
        # speaking: normal; return whatever's left.
        return text if self._phase in ("speaking", "scanning") else ""


def chat_stream(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    host: str = OLLAMA_HOST,
    timeout: float = 300.0,
) -> Iterator[str]:
    """Yield spoken token chunks from Ollama with the <think> block stripped.

    Thinking is left ENABLED (same as analyze_conversation.py).  The filter
    suppresses every byte up to and including </think>; only the spoken reply
    is yielded.  The caller sees nothing until the first spoken token, which
    gives the UI its "réflexion…" window naturally.

    Raises OllamaError if the server is unreachable or returns an error.
    """
    url = f"{host}/api/chat"
    payload: dict = {"model": model, "messages": messages, "stream": True}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    filt = _StreamThinkFilter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    raise OllamaError(f"Ollama error: {obj['error']}")
                token = obj.get("message", {}).get("content", "")
                if token:
                    spoken = filt.feed(token)
                    if spoken:
                        yield spoken
                if obj.get("done"):
                    tail = filt.flush()
                    if tail:
                        yield tail
                    break
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
