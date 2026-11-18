"""A declared day, from either shell: written at once, then handed to the day worker (TICKET-0128, K1).

A day module (INV-71): it receives its world and its character from its
caller, never reads the active ones.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session

from .. import quest_reads
from ..day_run_reads import DAY_IN_PROGRESS, unpublished_day
from ..models import Batch, Character, PassPlay
from ..prompt_coverage import DAY_CHAIN_USAGES, missing_usages
from ..writes import write_batch, write_pass_play
from .day_runner import enqueue_day


def declare(
    db: Session, *, world_id: str, character: Character, declared_action: str,
    quest_id: Optional[str], changed_by: str,
) -> tuple[Batch, PassPlay]:
    """Write the day (one commit), then enqueue it for the worker. E1: one
    unpublished day per character."""
    missing = missing_usages(DAY_CHAIN_USAGES, db)
    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "day chain unavailable: no active prompt_template with a version for "
                f"{', '.join(missing)} -- run "
                "python scripts/apply_ticket_0077_plan_select_seed.py"
            ),
        )
    if unpublished_day(db, character.id) is not None:
        raise HTTPException(status_code=409, detail=DAY_IN_PROGRESS)
    if quest_id:
        try:
            quest_reads.pinned_plan(quest_id, character, db)
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=404 if isinstance(exc, LookupError) else 409,
                                detail=str(exc)) from exc

    from .routes.day import _get_or_open_session  # lazy: the route module imports this one

    game_session = _get_or_open_session(world_id, db)
    batch = write_batch(db, session_id=game_session.id, changed_by=changed_by)
    try:
        pass_play = write_pass_play(
            db,
            batch_id=batch.id,
            session_id=game_session.id,
            character_id=character.id,
            declared_action=declared_action,
            quest_id=quest_id or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(batch)
    db.add(pass_play)
    db.commit()
    db.refresh(batch)
    db.refresh(pass_play)
    enqueue_day(batch.id)
    return batch, pass_play
