"""The Lore shell's usage recorder (TICKET-0103, BRIEF-0103-C, C-04).

The routes of the Lore shell -- consultation (`cockpit/routes/lore.py`) and
writing (`cockpit/routes/lore_write.py`) -- record each step they serve
here, once the request has reached the model or the apply step: what the
step received and answered (`writes/lore_usage.PAYLOAD_KEYS`) and the model
exchanges it captured (`model_exchange.ModelExchange`). Requests refused
before that point (no active world, an empty text, a non-local origin) are
not recorded.

`stage` adds the row to the caller's transaction (a successful commit
journals atomically with the canon it wrote); `record` stages and commits,
for a route that has nothing else to commit -- a draft, a question, a
consultation, or a refusal after its rollback. Nothing here reads the
journal back, calls a model, or imports the consultation pipeline or the
writing panel (`lore_usage.py` U10).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from .model_exchange import ModelExchange
from .models import World
from .writes.lore_usage import write_usage_event

WORLD_NAME_UNKNOWN = "(monde introuvable)"


def attempt_id(raw: Optional[str]) -> str:
    """The panel's attempt id in canonical form when it is a UUID; a fresh
    one otherwise (absent, empty or malformed) -- a journal id never fails
    the creator's request."""
    try:
        return str(uuid.UUID(str(raw)))
    except (ValueError, TypeError, AttributeError):
        return str(uuid.uuid4())


def _plain(value: Any) -> Any:
    """A JSON-native copy of `value` (a date becomes ISO text), detached from
    any dict the caller may still change -- the encoding FastAPI applies to
    the response itself."""
    return jsonable_encoder(value)


def stage(
    db: Session, *, attempt: str, world_id: str, kind: str, step: str, outcome: str,
    payload: dict, exchanges: Optional[list[ModelExchange]] = None,
    lore_entry_ref: Optional[str] = None,
) -> None:
    """Add one journal row to `db`'s transaction; never commits. The world's
    name is read now, so the row stays readable after the world is gone."""
    world = db.get(World, world_id) if world_id else None
    write_usage_event(
        db, attempt_id=attempt, world_ref=world_id or WORLD_NAME_UNKNOWN,
        world_name=world.name if world is not None else WORLD_NAME_UNKNOWN,
        kind=kind, step=step, outcome=outcome, payload=_plain(payload),
        model_calls=[_plain(e.to_record()) for e in exchanges or []],
        lore_entry_ref=lore_entry_ref,
    )


def record(db: Session, **row: Any) -> None:
    """`stage`, then commit: for a step whose session holds nothing else."""
    stage(db, **row)
    db.commit()
