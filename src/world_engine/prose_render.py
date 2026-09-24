"""Prose render — the identity-token read chokepoint (TICKET-0091,
BRIEF-0091-J, contract C-13, decision F1).

A name written into canon prose (`fact.content`, `knowledge.content`) is
stored as an identity token `[[e:<entity id>|<name at write time>]]`
(`prose_tokens.py` poses them). Every reader of that prose reads it through
this module: each token becomes the entity's CURRENT name, so renaming an
entity renames it everywhere it is cited. A token whose entity row no
longer exists falls back to the name it stored. Text without tokens is
returned unchanged; `None` stays `None`.

The model attribute holding the stored text is `content_raw` (SQL column
`content`). Outside `models/`, `writes/`, `knowledge_resolve.py` and the
migrations, this is the only module that reads it
(`tooling/verify/checks/identity_tokens.py` R1). Read-only: never `db.add`.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from sqlmodel import Session, select

from .models import Entity

TOKEN_RE = re.compile(r"\[\[e:([0-9a-fA-F-]{36})\|([^\]|]*)\]\]")


def entity_token(entity_id: str, name: str) -> str:
    """The stored form of a reference to `entity_id`; `]` and `|` are
    stripped from the fallback name so the token stays parseable."""
    clean = (name or "").replace("]", "").replace("|", "")
    return f"[[e:{entity_id}|{clean}]]"


def _current_names(db: Session, texts: Iterable[Optional[str]]) -> dict[str, str]:
    ids = {m.group(1) for text in texts if text for m in TOKEN_RE.finditer(text)}
    if not ids:
        return {}
    return {entity_id: name for entity_id, name in db.exec(
        select(Entity.id, Entity.name).where(Entity.id.in_(ids))
    ).all()}


def _substitute(text: Optional[str], names: dict[str, str]) -> Optional[str]:
    if text is None or "[[e:" not in text:
        return text
    return TOKEN_RE.sub(lambda m: names.get(m.group(1), m.group(2)), text)


def render_many(db: Session, texts: list[Optional[str]]) -> list[Optional[str]]:
    """Render every text; one entity query for all the ids they cite."""
    names = _current_names(db, texts)
    return [_substitute(text, names) for text in texts]


def render(db: Session, text: Optional[str]) -> Optional[str]:
    return render_many(db, [text])[0]


def fact_text(db: Session, fact) -> str:
    return render(db, fact.content_raw)


def knowledge_text(db: Session, k) -> Optional[str]:
    return render(db, k.content_raw)


def fact_texts(db: Session, facts: list) -> list[str]:
    """`fact_text` for many facts, one entity query."""
    return render_many(db, [fact.content_raw for fact in facts])


def knowledge_texts(db: Session, rows: list) -> list[Optional[str]]:
    """`knowledge_text` for many rows, one entity query."""
    return render_many(db, [k.content_raw for k in rows])
