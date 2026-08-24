"""`batch`/`pass_play` write primitives (TICKET-0075, BRIEF-0075-a — the
declaration socle: plumbing only, no resolution, no model call).

Both functions follow the same commit-free contract as the rest of
`writes/`: neither commits, the caller adds the returned row(s) to the
session and commits. `PASS_PLAY_STATUSES` is declared here because
`routes/day.py` renders it; `flagged` is reserved for a future input
classifier and is never written by anything in this module.
"""

from __future__ import annotations

from sqlmodel import Session, func, select

from ..models import Batch, PassPlay

MAX_DECLARATION_CHARS = 4000

PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted", "resolving", "resolved", "flagged")


def write_batch(db: Session, *, session_id: str, changed_by: str) -> Batch:
    """Allocate a new `batch` row for `session_id`: `day_number` is
    `max(day_number) + 1` for that session, or `1` when the session has
    none. Caller adds the returned row to the session and commits."""
    max_day = db.exec(
        select(func.max(Batch.day_number)).where(Batch.session_id == session_id)
    ).first()
    return Batch(session_id=session_id, day_number=(max_day or 0) + 1, status="pending")


def write_pass_play(
    db: Session, *, batch_id: str, session_id: str, character_id: str, declared_action: str,
) -> PassPlay:
    """Write one `pass_play` row bound to `batch_id`. Validates all-or-
    nothing before any write: `declared_action` stripped must be non-empty
    and at most `MAX_DECLARATION_CHARS` long. `declared_action` is
    write-once by construction — this constructor is the ONLY place it is
    ever assigned; there is no update path for it anywhere."""
    cleaned = declared_action.strip()
    if not cleaned:
        raise ValueError("write_pass_play: declared_action must be non-empty")
    if len(cleaned) > MAX_DECLARATION_CHARS:
        raise ValueError(
            f"write_pass_play: declared_action exceeds {MAX_DECLARATION_CHARS} characters"
        )
    return PassPlay(
        batch_id=batch_id,
        session_id=session_id,
        character_id=character_id,
        declared_action=cleaned,
        status="submitted",
        batch_order=1,
        history=[],
    )
