"""Single chokepoint for parsing local-model JSON output (TICKET-0027 R2,
BRIEF-0027-e).

Owns extraction and normalization only: fence stripping, `<think>`
stripping (via `ollama_client.strip_think`), first-balanced JSON
extraction, and array/object shape coercion. Domain/field validation
(e.g. entity_author's field checks, subculture shape validation) stays
with the callers, unchanged.
"""

from __future__ import annotations

import json
import re

from .ollama_client import strip_think

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class LlmParseError(ValueError):
    """Raised when model output cannot be extracted into the expected shape."""


def _defenced(raw: str) -> str:
    """Strip `<think>` reasoning and code fences, in that order."""
    text = strip_think(raw)
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1)
    return text


def _first_balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    start = text.find(open_ch)
    if start == -1:
        return None
    end = text.rfind(close_ch)
    if end == -1 or end < start:
        return None
    return text[start : end + 1]


def extract_object(raw: str) -> dict:
    """Parse `raw` model output into a JSON object.

    Raises `LlmParseError` if no `{...}` span is found, the span isn't
    valid JSON, or the parsed value isn't an object.
    """
    text = _defenced(raw)
    candidate = _first_balanced(text, "{", "}")
    if candidate is None:
        raise LlmParseError("no JSON object found in model output")
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LlmParseError(f"model output is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LlmParseError("parsed JSON value is not an object")
    return parsed


def extract_object_or_none(raw: str) -> dict | None:
    """Like `extract_object`, but returns None instead of raising."""
    try:
        return extract_object(raw)
    except LlmParseError:
        return None


def _load_array(candidate: str) -> list:
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LlmParseError(f"model output is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise LlmParseError("parsed JSON value is not an array")
    return parsed


def extract_array(raw: str) -> list:
    """Parse `raw` model output into a JSON array.

    Shape tolerance (legacy `analyzer._extract_json_array` behavior): an
    array is used as-is; a lone object is wrapped into a one-element
    array; neither delimiter present yields an empty array — a model
    reply with no JSON structure at all is "no items", not a failure.
    Raises `LlmParseError` only when a delimiter was found but the
    resulting text isn't valid JSON (or doesn't parse to an array).
    """
    text = _defenced(raw)

    bracket_start = text.find("[")
    brace_start = text.find("{")

    if bracket_start != -1 and (brace_start == -1 or bracket_start <= brace_start):
        candidate = _first_balanced(text, "[", "]")
        if candidate is not None:
            return _load_array(candidate)

    if brace_start != -1:
        candidate = _first_balanced(text, "{", "}")
        if candidate is not None:
            return _load_array(f"[{candidate}]")

    return []


def extract_array_or_none(raw: str) -> list | None:
    """Like `extract_array`, but returns None instead of raising."""
    try:
        return extract_array(raw)
    except LlmParseError:
        return None
