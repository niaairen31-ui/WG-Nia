"""Fact references (TICKET-0097): how a model names a fact, and how the
mutation pipeline tells two knowledge proposals apart.

A knowledge row is identified by the fact it knows (schema v2.09). Two
consequences live here, and only here:

- **Codes (D1'a, L1, Z2).** A model never emits a fact id and never copies a
  free-text key. It is shown a coded list (`f1 — <the fact's text>`), emits
  a code, and `CodedFacts.resolve` turns it back into a fact id -- or None
  for any code the list did not show. Codes are positional: the same fact
  ids in the same order give the same codes, so a list rebuilt from the same
  rows resolves the codes a prompt carried.
- **Identity key (M1).** `knowledge_key(payload)` is the dedup identity of a
  `new_knowledge` payload or a `resource_change` knowledge leg:
  `("fact", fact_id)` when the payload names an existing fact,
  `("text", text_key(content))` otherwise. `text_key` is the former
  `analyzer_transcript._content_to_subject_slug`, moved unchanged; it is
  computed at compare time and never stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlmodel import Session, select

from .models import Fact, Knowledge
from .prose_render import fact_texts, knowledge_texts

CODE_PREFIX = "f"

# Strips non-word chars for text keys.
_SLUG_NON_WORD = re.compile(r"[^\w]")


def text_key(content: Optional[str]) -> str:
    """Derive a short comparison key from free-text content: the first five
    words, lower-cased, non-word characters stripped, joined by `_`, at
    most 50 characters; "unknown" for empty content."""
    if not content:
        return "unknown"
    words = content.lower().split()[:5]
    parts = [_SLUG_NON_WORD.sub("", w) for w in words if w]
    return ("_".join(p for p in parts if p))[:50] or "unknown"


def knowledge_key(payload: dict) -> tuple[str, str]:
    """The dedup identity of a knowledge payload (see module docstring)."""
    fact_id = payload.get("fact_id")
    if fact_id:
        return ("fact", str(fact_id))
    return ("text", text_key(str(payload.get("content") or "")))


def find_held(db: Session, entity_id: Optional[str], payload: dict) -> Optional[Knowledge]:
    """The row of `entity_id` a knowledge payload would duplicate, or None:
    the row on the payload's `fact_id`, or else a row whose fact text or own
    text has the payload's `text_key`."""
    if not entity_id:
        return None
    kind, value = knowledge_key(payload)
    if kind == "fact":
        return db.exec(
            select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == value)
        ).first()
    rows = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id)).all()
    fact_keys = [text_key(t) for t in fact_texts(db, [db.get(Fact, row.fact_id) for row in rows])]
    row_keys = [text_key(t) for t in knowledge_texts(db, rows)]
    for row, fact_key, row_key in zip(rows, fact_keys, row_keys):
        if value in (fact_key, row_key):
            return row
    return None


@dataclass(frozen=True)
class CodedFacts:
    """A coded fact list: `lines[i]` shows the fact coded `f{i+1}`."""

    codes: dict[str, str]
    lines: tuple[str, ...]

    def resolve(self, code: object) -> Optional[str]:
        """The fact id behind `code`, or None when the list did not show it.
        Surrounding whitespace and brackets are tolerated (`[f3]`, ` F3 `)."""
        if not isinstance(code, str):
            return None
        return self.codes.get(code.strip().strip("[]").strip().lower())

    def code_of(self, fact_id: str) -> Optional[str]:
        """The code the list gives `fact_id`, or None."""
        return next((code for code, fid in self.codes.items() if fid == fact_id), None)


def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedFacts:
    """Code `fact_ids` in order, first occurrence wins; an id with no `fact`
    row is skipped. Each line is `f<n> — <the fact's rendered text>`."""
    ordered: list[str] = []
    for fact_id in fact_ids:
        if fact_id and fact_id not in ordered:
            ordered.append(fact_id)
    facts = [fact for fact in (db.get(Fact, fid) for fid in ordered) if fact is not None]
    codes: dict[str, str] = {}
    lines: list[str] = []
    for index, (fact, text) in enumerate(zip(facts, fact_texts(db, facts)), start=1):
        code = f"{CODE_PREFIX}{index}"
        codes[code] = fact.id
        lines.append(f"{code} — {text}")
    return CodedFacts(codes=codes, lines=tuple(lines))
