"""Closed shared-helper set for the `writes/` package (TICKET-0028,
BRIEF-0028-b — decomposed from `writes.py`).

Mirrors `cockpit/crud/_shared.py`'s convention: a small, closed set of
helpers genuinely used by more than one domain module. `_clamp` clamps
`relation.intensity` (`relations.py`) and `knowledge.share_threshold`
(`knowledge.py`); `_append_history_snapshot` is `relations.py`'s own history
discipline (kept here as part of the same closed set, not because a second
domain calls it). Nothing else enters this file without a brief (R7).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs

from ..models import Relation


def _clamp(value: int, lo: int = 1, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


def _append_history_snapshot(rel: Relation, mutation_id: Optional[str] = None) -> None:
    """Append a snapshot of `rel`'s current state to its `change_history`.

    Shared by both `write_relation` modes — history is sacred on either
    write path (delta or set). `mutation_id` is None for author-CRUD edits
    (no `proposed_mutation` row is involved).
    """
    history = list(rel.change_history or [])
    history.append({
        "intensity": rel.intensity,
        "last_evolved_at": rel.last_evolved_at.isoformat() if rel.last_evolved_at else None,
        "mutation_id": mutation_id,
    })
    rel.change_history = history
    # flag_modified ensures SQLAlchemy detects the JSON list change
    # even though we replaced the object (not mutated it in place).
    sa_attrs.flag_modified(rel, "change_history")
