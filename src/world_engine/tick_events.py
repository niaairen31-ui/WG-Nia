"""The world tick's typed events (TICKET-0119, BRIEF-0119-E; decisions A1,
M-c and R1 of the conditions series).

The scope-level tick call (`tick._tick_call_scope_model`) shows the model
the world's event types as Play does -- the coded `t` list, each with its
roles, and the sortes by name (`event_analysis.analysis_vocabulary`). Its
`event_creation` names a type by code (`event_type`) and each participant
by the role it holds: a person, place or faction by its NAME as the
briefing writes it, or a sorte by name; a quantity when the type counts one.

`typed_tick_payload` reads that into the payload Play's analyzer makes
(`event_analysis.typed_payload`, fail-closed: an unknown code drops the
proposal, a participant its type cannot take is left out), its changes
pre-filled from the type's effects (M-c). A name resolves through the
scope's roster first, then every active entity of the world; one that does
not is left out with a note, never guessed. The tick proposes no new type
(A1): it runs unattended, three events per scope, and its vocabulary would
drift -- a `new_type` is set aside with a note, and an item naming no
existing type keeps the former, untyped shape (typed by its domain at
approval, `event_payloads`).

Reads only; writes nothing.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from .event_analysis import AnalysisVocabulary, typed_payload

# The marker of an item that names no type: the caller keeps its untyped shape.
UNTYPED = "untyped"


def _participants(raw: Any, roster: dict[str, str], actives: dict[str, str], title: str,
                  notes: list[str]) -> list[dict]:
    out: list[dict] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        if str(item.get("sorte") or "").strip():
            out.append({"role": role, "sorte": str(item["sorte"]).strip()})
            continue
        name = str(item.get("name") or "").strip()
        entity_id = roster.get(name.casefold()) or actives.get(name.casefold())
        if entity_id is None:
            notes.append(f"event {title!r}: unresolved participant name {name!r} dropped")
            continue
        out.append({"role": role, "entity_id": entity_id})
    return out


def typed_tick_payload(
    payload_in: dict, *, title: str, description: Optional[str], location_id: Optional[str],
    roster: dict[str, str], actives: dict[str, str], vocab: Optional[AnalysisVocabulary], db: Session,
    world_id: str, notes: list[str],
) -> Any:
    """The queue's typed payload of one tick item, None to drop it, or
    `UNTYPED` when it names no existing type (see the module docstring)."""
    if payload_in.get("new_type") is not None:
        notes.append(f"event {title!r}: the tick proposes no new type (A1) -- set aside")
    code = payload_in.get("event_type")
    if vocab is None or code in (None, "") or isinstance(code, dict):
        return UNTYPED
    raw = {
        "title": title, "description": description, "event_type": code, "location_id": location_id,
        "participants": _participants(payload_in.get("participants"), roster, actives, title, notes),
        "quantity": payload_in.get("quantity"),
    }
    typed = typed_payload(db, world_id, raw, vocab)
    if typed is None:
        notes.append(f"event {title!r}: unknown event type code {code!r} dropped")
    return typed
