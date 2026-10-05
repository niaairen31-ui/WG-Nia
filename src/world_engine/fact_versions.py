"""The version of a fact someone knows (TICKET-0105, BRIEF-0105-C, C-05).

A fact's history is a list of entries `{"content", "changed_by", "at",
"kind"}`, each holding the text the fact had BEFORE that rewrite. A
`correction` fixes the text for everyone; a `changement` is a change in the
world (G1). An entry without `kind` predates TICKET-0105 and reads as a
correction (M1).

Someone whose last contact with the fact was at `as_of` knows the text the
fact had just before the first `changement` made after `as_of` -- with
every correction made before that change included -- or the current text
when no change in the world came after `as_of`. `as_of=None` means "always
in contact" (a fact everyone knows, one's own description): the current
text.

Pure: no query, no write, no model attribute. The caller passes the stored
history and the current stored text (`prose_render.fact_texts_at` does,
the one reader of the raw text) and renders what comes back.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional


def utc(value: datetime) -> datetime:
    """`value` as an aware UTC datetime; a naive value is taken to be UTC
    (SQLite returns plain `DateTime` columns naive)."""
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)


def _entry_at(entry: dict) -> Optional[datetime]:
    raw = entry.get("at")
    if not isinstance(raw, str):
        return None
    try:
        return utc(datetime.fromisoformat(raw))
    except ValueError:
        return None


def version_text(history: Optional[list], current: str, as_of: Optional[datetime]) -> str:
    """The stored text known by someone last in contact at `as_of`, given
    the fact's `history` and `current` stored text (module docstring)."""
    if as_of is None:
        return current
    since = utc(as_of)
    for entry in history or []:
        if not isinstance(entry, dict) or entry.get("kind") != "changement":
            continue
        at = _entry_at(entry)
        if at is not None and at > since and isinstance(entry.get("content"), str):
            return entry["content"]
    return current
