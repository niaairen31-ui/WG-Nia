"""The Lore shell's usage journal writer (TICKET-0103, BRIEF-0103-A, C-01).

`lore_usage_event` is non-canon and append-only: this module inserts, never
updates or deletes, and nothing deletes the journal -- not even the world
cascade (I1: the table carries no `world_id`). Nothing here commits; the
caller owns the transaction. Every shape the schema CHECKs is asserted here
first, so a malformed record fails as a `ValueError` naming the field
rather than as an `IntegrityError` at flush.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from ..models import LoreUsageEvent
from ..models.pipeline import LORE_USAGE_OUTCOMES, LORE_USAGE_STEPS

MODEL_CALL_KEYS: frozenset[str] = frozenset({
    "usage", "prompt_version_id", "prompt_version_number", "model",
    "system_prompt", "user_message", "raw_output", "error",
})
# The payload of each step, by key (C-02). `error` is None on `ok` and the
# message the creator was shown otherwise; the step's answer key is None
# whenever the step did not answer.
PAYLOAD_KEYS: dict[str, frozenset[str]] = {
    "questions": frozenset({"statement", "questions", "error"}),
    "draft": frozenset({"statement", "answers", "draft", "error"}),
    "commit": frozenset({"proposal", "result", "error"}),
    "ask": frozenset({"question", "response", "error"}),
    "resolve": frozenset({"question", "plan", "bindings", "response", "error"}),
}


def _validate_model_call(call: Any) -> None:
    if not isinstance(call, dict) or set(call) != MODEL_CALL_KEYS:
        got = sorted(call) if isinstance(call, dict) else type(call).__name__
        raise ValueError(f"lore_usage_event: a model call must carry exactly {sorted(MODEL_CALL_KEYS)}, got {got}")
    if not isinstance(call["usage"], str) or not call["usage"]:
        raise ValueError("lore_usage_event: a model call has no usage")


def write_usage_event(
    db: Session, *, attempt_id: str, world_ref: str, world_name: str, kind: str,
    step: str, outcome: str, payload: dict, model_calls: list[dict],
    lore_entry_ref: Optional[str] = None,
) -> LoreUsageEvent:
    """Insert one `lore_usage_event`. `ValueError` on any shape the schema
    refuses: an empty id or world, a `(kind, step)` pair outside
    `LORE_USAGE_STEPS`, an outcome outside `LORE_USAGE_OUTCOMES`, a payload
    without exactly the step's `PAYLOAD_KEYS` or whose `error` disagrees with
    the outcome, a model call without exactly `MODEL_CALL_KEYS`, or a
    `lore_entry_ref` present anywhere but on a successful commit (and absent
    there)."""
    for name, value in (("attempt_id", attempt_id), ("world_ref", world_ref), ("world_name", world_name)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"lore_usage_event: {name} is empty")
    if step not in LORE_USAGE_STEPS.get(kind, ()):
        raise ValueError(f"lore_usage_event: step {step!r} is not a step of kind {kind!r}")
    if outcome not in LORE_USAGE_OUTCOMES:
        raise ValueError(f"lore_usage_event: unknown outcome {outcome!r}")
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS[step]:
        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        raise ValueError(f"lore_usage_event: a {step} payload carries exactly {sorted(PAYLOAD_KEYS[step])}, got {got}")
    if (payload["error"] is None) != (outcome == "ok"):
        raise ValueError("lore_usage_event: payload error is set exactly when the outcome is not ok")
    if not isinstance(model_calls, list):
        raise ValueError("lore_usage_event: model_calls is not a list")
    for call in model_calls:
        _validate_model_call(call)
    if (lore_entry_ref is not None) != (step == "commit" and outcome == "ok"):
        raise ValueError("lore_usage_event: lore_entry_ref is set exactly on a successful commit")
    event = LoreUsageEvent(
        attempt_id=attempt_id, world_ref=world_ref, world_name=world_name, kind=kind,
        step=step, outcome=outcome, payload=payload, model_calls=model_calls,
        lore_entry_ref=lore_entry_ref,
    )
    db.add(event)
    return event
