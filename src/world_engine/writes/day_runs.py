"""The writers of a day's run: its failures, its reopening, its abandonment and its publication (TICKET-0128, L1, M1, Z1, C1, T1).

Commit-free: the caller owns the commit. None of them touches
`pass_play.history` (the resolution history stays the chain's own, L2
rejected). `pass_play` and `day_run_failure` are pipeline tables, never
canon.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session

from ..models import DAY_RUN_FAILURE_CODES, DAY_RUN_STAGES, DayRunFailure, PassPlay

DAY_NOT_FLAGGED = "Cette journée n'est pas en échec."
DAY_NOT_PUBLISHABLE = "Cette journée n'est pas à publier."
EMPTY_NARRATIVE = "Le récit publié est vide."
MAX_REASON_CHARS = 2000


def write_day_run_failure(
    db: Session, *, pass_play: PassPlay, world_id: str, stage: str, code: str, reason: str,
) -> DayRunFailure:
    """L1: one failure row for the day (`stage` and `code` from their closed
    vocabularies, else `ValueError`), and the day turns `flagged`."""
    if stage not in DAY_RUN_STAGES:
        raise ValueError(f"write_day_run_failure: unknown stage {stage!r}")
    if code not in DAY_RUN_FAILURE_CODES:
        raise ValueError(f"write_day_run_failure: unknown code {code!r}")
    text_ = (reason or "").strip()[:MAX_REASON_CHARS] or "—"
    row = DayRunFailure(world_id=world_id, pass_play_id=pass_play.id, stage=stage, code=code, reason=text_)
    db.add(row)
    pass_play.status = "flagged"
    db.add(pass_play)
    return row


def reopen_day(db: Session, *, pass_play: PassPlay) -> str:
    """M1 « Relancer »: a flagged day goes back to the stage that failed
    (`plan` -> `submitted`, `resolve` -> `resolving`); returns the stage."""
    from ..day_run_reads import latest_failure  # lazy: the reads import the models only

    if pass_play.status != "flagged":
        raise ValueError(DAY_NOT_FLAGGED)
    failure = latest_failure(db, pass_play.id)
    stage = failure.stage if failure is not None else "plan"
    pass_play.status = "resolving" if stage == "resolve" else "submitted"
    db.add(pass_play)
    return stage


def abandon_day(db: Session, *, pass_play: PassPlay) -> None:
    """Z1 « Abandonner »: a flagged day becomes `abandoned`, for good."""
    if pass_play.status != "flagged":
        raise ValueError(DAY_NOT_FLAGGED)
    pass_play.status = "abandoned"
    db.add(pass_play)


def publish_day(db: Session, *, pass_play: PassPlay, text: str) -> PassPlay:
    """C1, C′2, T1: the creator publishes a resolved day once, with the
    text the player will read; `batch.final_result` (the narrator's text)
    is never touched."""
    if pass_play.status != "resolved" or pass_play.published_at is not None:
        raise ValueError(DAY_NOT_PUBLISHABLE)
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError(EMPTY_NARRATIVE)
    pass_play.published_text = cleaned
    pass_play.published_at = datetime.now(UTC)
    db.add(pass_play)
    return pass_play
