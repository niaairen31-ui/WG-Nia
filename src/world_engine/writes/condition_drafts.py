"""The condition interpreter's journal writer (TICKET-0112, BRIEF-0112-B,
decision IH1).

`condition_draft` is non-canon: one row per proposal of the interpreter,
whose `outcome` moves along `CONDITION_DRAFT_MOVES` and nowhere else. This
module is its one writer; nothing here deletes a row, and nothing deletes
the journal -- not even the world cascade (no `world_id` column). Nothing
here commits; the caller owns the transaction.

- `write_condition_draft(...)` : insert one proposal, in one of the
  `FIRST_OUTCOMES`.
- `move_condition_draft(...)`  : move a proposal to its next outcome, the
  payload replaced whole when a new one is given (a name picked).
- `mark_draft_saved(...)`      : the offer holding an inserted proposal was
  saved -- `saved`, its offer and whether the saved tree is the proposed
  one. Never fails the creator's save: a draft it cannot mark is skipped.

Every shape the schema CHECKs is asserted here first, so a malformed record
fails as a `ValueError` naming the field rather than as an `IntegrityError`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from ..models import CONDITION_DRAFT_OUTCOMES, CONDITION_ROLES, ConditionDraft, World

# What the interpreter may record first, and where each outcome may go.
FIRST_OUTCOMES: tuple[str, ...] = ("proposed", "needs_choice", "refused", "unavailable", "parse_error")
CONDITION_DRAFT_MOVES: dict[str, tuple[str, ...]] = {
    "needs_choice": ("proposed", "refused", "discarded"),
    "proposed": ("inserted", "discarded"),
    "inserted": ("saved",),
}
# The payload of a proposal, by key: the tree it started from (the dict form
# of `conditions.node_to_dict`, or None), the model's tree as code read it
# with names still to pick (`pending`), the names it mentions and the picks
# made, the tree code validated (`proposed`, dict form), the notes and the
# errors shown to the creator.
PAYLOAD_KEYS: frozenset[str] = frozenset({
    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors",
})
WORLD_NAME_UNKNOWN = "(monde introuvable)"


def _payload(payload: Any) -> dict:
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS:
        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        raise ValueError(f"condition_draft: a payload carries exactly {sorted(PAYLOAD_KEYS)}, got {got}")
    return jsonable_encoder(payload)


def write_condition_draft(
    db: Session, *, attempt_id: str, world_id: str, role: str, instruction: str, outcome: str,
    payload: dict, model_calls: list[dict], retried: bool = False,
) -> ConditionDraft:
    """Insert one proposal. `ValueError` on an empty attempt, world or
    instruction, a role outside `CONDITION_ROLES`, an outcome outside
    `FIRST_OUTCOMES`, a payload without exactly `PAYLOAD_KEYS`, or
    `model_calls` that is not a list."""
    for name, value in (("attempt_id", attempt_id), ("world_id", world_id), ("instruction", instruction)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"condition_draft: {name} is empty")
    if role not in CONDITION_ROLES:
        raise ValueError(f"condition_draft: unknown role {role!r}")
    if outcome not in FIRST_OUTCOMES:
        raise ValueError(f"condition_draft: a proposal cannot start {outcome!r}")
    if not isinstance(model_calls, list):
        raise ValueError("condition_draft: model_calls is not a list")
    world = db.get(World, world_id)
    draft = ConditionDraft(
        attempt_id=attempt_id, world_ref=world_id,
        world_name=world.name if world is not None else WORLD_NAME_UNKNOWN,
        role=role, instruction=instruction.strip(), outcome=outcome, retried=bool(retried),
        payload=_payload(payload), model_calls=jsonable_encoder(model_calls),
    )
    db.add(draft)
    return draft


def move_condition_draft(
    db: Session, draft: ConditionDraft, outcome: str, payload: Optional[dict] = None,
) -> ConditionDraft:
    """Move `draft` to `outcome`; `ValueError` when `CONDITION_DRAFT_MOVES`
    does not allow it. `saved` is `mark_draft_saved`'s alone."""
    if outcome == "saved" or outcome not in CONDITION_DRAFT_MOVES.get(draft.outcome, ()):
        raise ValueError(f"condition_draft: a {draft.outcome!r} proposal cannot become {outcome!r}")
    if payload is not None:
        draft.payload = _payload(payload)
    draft.outcome = outcome
    draft.decided_at = datetime.now(UTC)
    db.add(draft)
    return draft


def mark_draft_saved(
    db: Session, *, world_id: str, draft_id: Optional[str], offer_id: str, tree: Optional[dict],
) -> bool:
    """The offer `offer_id` was saved holding `tree` (dict form) where the
    creator inserted `draft_id`. True when the draft was marked; False --
    and nothing written -- when there is no such draft in `world_id`, or it
    is not `inserted`."""
    if not draft_id:
        return False
    draft = db.get(ConditionDraft, draft_id)
    if draft is None or draft.world_ref != world_id or draft.outcome != "inserted":
        return False
    draft.outcome = "saved"
    draft.offer_ref = offer_id
    draft.saved_as_proposed = jsonable_encoder(tree) == draft.payload.get("proposed")
    draft.decided_at = datetime.now(UTC)
    db.add(draft)
    return True

