"""`batch`/`pass_play` write primitives (TICKET-0075, BRIEF-0075-a — the
declaration socle: plumbing only, no resolution, no model call;
`write_pass_play_resolution` added BRIEF-0075-d — the first writer of
`pass_play.history`, S5; `write_day_feasibility` added BRIEF-0075-g — the
SECOND entry kind `pass_play.history` carries).

`pass_play.history` holds two entry kinds (BRIEF-0075-g): a resolution
entry (`write_pass_play_resolution`'s shape, no `"kind"` key — the ORIGINAL
shape, unchanged for every pre-existing row) and a feasibility entry
(`write_day_feasibility`'s shape, `"kind": "feasibility"`). `read_latest_
resolution`/`resolution_count` filter to the FIRST kind only — an entry is
a resolution entry iff its `"kind"` is anything other than `"feasibility"`,
which is true both for every entry written before this brief (no `"kind"`
key at all) and for every resolution entry written after it (still no
`"kind"` key — only feasibility entries carry one). BRIEF-0075-e's
`resolution_count() > 1` == replay invariant is unaffected: a feasibility
entry is written once, at `/plan` time, and never again for the same
`pass_play` (Scope OUT, BRIEF-0075-g: "retrying a rejected verdict" is
never done), so it never inflates the replay count.

Every function here follows the same commit-free contract as the rest of
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

from ..day_feasibility import VetoVerdict
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


def _is_resolution_entry(entry: object) -> bool:
    """A resolution entry (`write_pass_play_resolution`'s shape) is any
    dict whose `"kind"` is not `"feasibility"` — true for every entry ever
    written before BRIEF-0075-g (no `"kind"` key existed) and for every
    resolution entry written since (still none)."""
    return isinstance(entry, dict) and entry.get("kind") != "feasibility"


def read_latest_resolution(pass_play: PassPlay) -> Optional[dict]:
    """Return the most recent `write_pass_play_resolution` entry (the
    LATEST resolution — a replay appends a second entry, the first stays
    intact), or `None` if the day has never resolved. Skips over any
    feasibility entry (BRIEF-0075-g) interleaved in the same list.
    BRIEF-0075-e's day account route reads through this helper rather than
    `pass_play.history` directly: `routes/day.py` must never reference
    `.history` (`pipeline_wiring.py`'s R5), and re-running extraction/
    concordance just to rebuild what `resolve_day` already computed once
    would also cost a fresh, non-deterministic model call on every read."""
    for entry in reversed(pass_play.history or []):
        if _is_resolution_entry(entry):
            return entry
    return None


def resolution_count(pass_play: PassPlay) -> int:
    """Number of resolution attempts recorded on `pass_play` — more than
    one means the day was replayed (BRIEF-0075-d Scope IN item 5). Excludes
    the (at most one) feasibility entry BRIEF-0075-g may have appended."""
    return sum(1 for entry in (pass_play.history or []) if _is_resolution_entry(entry))


def write_day_feasibility(db: Session, *, pass_play: PassPlay, verdict: VetoVerdict) -> PassPlay:
    """Append one feasibility-veto verdict to `pass_play.history`
    (TICKET-0075, BRIEF-0075-g, decision Y1 — the observability half:
    Python's count, the veto's count, the reason, and the honoured/clamped/
    unavailable outcome, so the calibration numbers are auditable). A
    SEPARATE entry kind from `write_pass_play_resolution`'s (`"kind":
    "feasibility"`, see module docstring) — append-only, same discipline as
    every other `.history`/`change_history` writer: a NEW list (the old one
    plus one new entry) replaces the column value, no existing entry is
    ever mutated. Written exactly once per `pass_play`, at `/plan` time,
    BEFORE `pass_play.status` moves to `'resolving'` — never re-invoked on
    a replay (Scope OUT, BRIEF-0075-g: "retrying a rejected verdict").
    Caller adds the row to the session."""
    entry = {
        "kind": "feasibility",
        "python_retained": verdict.python_retained,
        "veto_retained": verdict.veto_retained,
        "reason": verdict.reason,
        "cited_step_order": verdict.cited_step_order,
        "cited_objective": verdict.cited_objective,
        "outcome": verdict.outcome,
        "decided_at": datetime.now(UTC).isoformat(),
    }
    history = list(pass_play.history or [])
    history.append(entry)
    pass_play.history = history
    sa_attrs.flag_modified(pass_play, "history")
    return pass_play


def read_latest_feasibility(pass_play: PassPlay) -> Optional[dict]:
    """Return the most recent feasibility entry (`write_day_feasibility`'s
    shape), or `None` if none was ever recorded (a plan predating
    BRIEF-0075-g, or a day that has been declared but not yet planned).
    `routes/day.py` reads through this rather than `pass_play.history`
    directly, same boundary as `read_latest_resolution` (`pipeline_wiring.
    py`'s R5)."""
    for entry in reversed(pass_play.history or []):
        if isinstance(entry, dict) and entry.get("kind") == "feasibility":
            return entry
    return None
