"""`batch`/`pass_play` write primitives (TICKET-0075, BRIEF-0075-a — the
declaration socle: plumbing only, no resolution, no model call;
`write_pass_play_resolution` added BRIEF-0075-d — the first writer of
`pass_play.history`, S5).

All three functions follow the same commit-free contract as the rest of
`writes/`: none commits, the caller adds the returned row(s) to the session
and commits. `PASS_PLAY_STATUSES` is declared here because `routes/day.py`
renders it; `flagged` is reserved for a future input classifier and is
never written by anything in this module. `BATCH_STATUSES` is the same
idiom for `batch.status` (BRIEF-0075-d): `write_batch` only ever writes
`"pending"`; `BATCH_RESOLVED_STATUS` is the value the resolve route moves
a batch to once its day narration is judged and accepted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, func, select

from ..models import Batch, PassPlay

MAX_DECLARATION_CHARS = 4000

PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted", "resolving", "resolved", "flagged")

BATCH_STATUSES: tuple[str, ...] = ("pending", "resolved_awaiting_review")
BATCH_RESOLVED_STATUS: str = BATCH_STATUSES[1]


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


def write_pass_play_resolution(
    db: Session, *, pass_play: PassPlay, fact_sheet: dict, prose: str, judge_verdict: dict,
) -> PassPlay:
    """Append one resolution attempt to `pass_play.history` (BRIEF-0075-d —
    this function is `history`'s first writer, S5). Append-only by
    construction: a NEW list (the old one plus one new entry) replaces the
    column value — no existing entry is ever mutated, matching every other
    `change_history` writer's discipline (`write_agenda_step_status`,
    `write_npc_goal_status`). A replay calls this a second time on the same
    `pass_play` and appends a SECOND entry; the first stays intact. Caller
    sets `pass_play.status` and adds the row to the session."""
    entry = {
        "fact_sheet": fact_sheet,
        "prose": prose,
        "judge_verdict": judge_verdict,
        "resolved_at": datetime.now(UTC).isoformat(),
    }
    history = list(pass_play.history or [])
    history.append(entry)
    pass_play.history = history
    sa_attrs.flag_modified(pass_play, "history")
    return pass_play


def read_latest_resolution(pass_play: PassPlay) -> Optional[dict]:
    """Return the most recent `write_pass_play_resolution` entry (the
    LATEST resolution — a replay appends a second entry, the first stays
    intact), or `None` if the day has never resolved. BRIEF-0075-e's day
    account route reads through this helper rather than `pass_play.
    history` directly: `routes/day.py` must never reference `.history`
    (`pipeline_wiring.py`'s R5), and re-running extraction/concordance just
    to rebuild what `resolve_day` already computed once would also cost a
    fresh, non-deterministic model call on every read."""
    history = pass_play.history or []
    return history[-1] if history else None


def resolution_count(pass_play: PassPlay) -> int:
    """Number of resolution attempts recorded on `pass_play` — more than
    one means the day was replayed (BRIEF-0075-d Scope IN item 5)."""
    return len(pass_play.history or [])
