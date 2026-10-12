"""The play analyzer's typed events (TICKET-0114, BRIEF-0114-H; decisions
I2 and R1 of the conditions series).

The conversation analysis (`analyzer_transcript.analyze_transcript`) shows
the model the world's event types as a coded list (`t`, each with its
roles) and its sortes by name. Its `event_creation` names a type by code
(`event_type`), each participant by the NAME of the role it holds -- an
entity by id, or a sorte by name -- and a quantity when the type counts
one. When no type says what happened, it may propose one (`new_type`, I2):
the creator approves the type with the event, and the applier writes both
in its one savepoint (`event_payloads`).

`typed_payload` reads that proposal into the payload the queue shows and
the applier reads, fail-closed: an unknown type code, or a proposed type
the writer refuses, drops the proposal; a participant whose role the type
lacks, or whose entity is not one of the world's the role accepts, is left
out, never guessed. A sorte the world lacks keeps its name (`sorte_name`):
it is created with the event. A payload with neither `event_type` nor
`new_type` is the former, untyped shape (`event_payloads` types it by its
domain).

Since TICKET-0119 (BRIEF-0119-C, M-c), a payload of an existing type
carries its `state_changes`: its type's effects made concrete on its
participants (`event_changes.type_changes`), which the creator keeps, edits
or drops on the card. A proposed type has no effects yet.

Reads only; writes nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlmodel import Session

from .event_changes import type_changes
from .event_proposals import type_definition, type_spec
from .event_vocab import EventTypeView, role_accepts, world_event_types, world_sortes
from .fact_refs import CodedRefs, code_refs
from .interpreter_events import event_type_line
from .lore_resolve import normalize_surface
from .models import Entity
from .writes.event_types import clean_event_type

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisVocabulary:
    """The world's event vocabulary as one analysis call shows it."""

    codes: CodedRefs
    types: dict[str, EventTypeView] = field(default_factory=dict)
    sortes: dict[str, str] = field(default_factory=dict)  # id -> name

    def prompt_values(self) -> dict[str, str]:
        return {"event_types": "\n".join(self.codes.lines) or "(aucun)",
                "sortes": ", ".join(self.sortes.values()) or "(aucune)"}


def analysis_vocabulary(db: Session, world_id: str) -> AnalysisVocabulary:
    from .attributes import world_entity_type_labels

    labels = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
    types = {view.id: view for view in world_event_types(db, world_id)}
    return AnalysisVocabulary(
        codes=code_refs("t", ((tid, event_type_line(view, labels)) for tid, view in types.items())),
        types=types, sortes={s.id: s.name for s in world_sortes(db, world_id)},
    )


@dataclass(frozen=True)
class _Role:
    id: Optional[str]
    name: str
    entity_types: tuple[str, ...]
    accepts_sorte: bool


def _type_of(db: Session, world_id: str, payload: dict, vocab: AnalysisVocabulary):
    """(type id, type name, its roles, counts quantity, new type definition)
    or None when the proposal names no type it may."""
    code = payload.get("event_type")
    if code is not None and not isinstance(code, dict):
        type_id = vocab.codes.resolve(code)
        if type_id is None:
            _log.warning("[skip] event_creation: unknown event type code %r", code)
            return None
        view = vocab.types[type_id]
        roles = tuple(_Role(r.id, r.name, r.entity_types, r.accepts_sorte) for r in view.active_roles())
        return type_id, view.name, roles, view.counts_quantity, None
    raw = payload.get("new_type")
    if not isinstance(raw, dict):
        return None
    same = next((v for v in vocab.types.values()
                 if normalize_surface(v.name) == normalize_surface(str(raw.get("name") or ""))), None)
    if same is not None:  # a type the world has under that very name
        return _type_of(db, world_id, {"event_type": vocab.codes.code_of(same.id)}, vocab)
    try:
        clean = clean_event_type(db, world_id, type_spec(raw))
    except ValueError as exc:
        _log.warning("[skip] event_creation: proposed type refused (%s): %r", exc, raw)
        return None
    roles = tuple(_Role(None, r.name, r.entity_types, r.accepts_sorte) for r in clean.roles)
    return None, clean.name, roles, clean.counts_quantity, type_definition(clean)


def _participant(db: Session, world_id: str, raw: Any, roles: tuple[_Role, ...],
                 vocab: AnalysisVocabulary) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    key = normalize_surface(str(raw.get("role") or ""))
    role = next((r for r in roles if key and normalize_surface(r.name) == key), None)
    if role is None:
        return None
    out = {"role_id": role.id, "role": role.name, "entity_id": None, "sorte_id": None, "sorte_name": None,
           "secret": None}
    if raw.get("sorte") not in (None, ""):
        if not role.accepts_sorte:
            return None
        name = str(raw["sorte"]).strip()
        out["sorte_id"] = next((sid for sid, s in vocab.sortes.items()
                                if normalize_surface(s) == normalize_surface(name)), None)
        out["sorte_name"] = vocab.sortes.get(out["sorte_id"], name)
        return out
    entity = db.get(Entity, raw.get("entity_id")) if isinstance(raw.get("entity_id"), str) else None
    if entity is None or entity.world_id != world_id or entity.status != "active" \
            or not role_accepts(role, entity.type):
        return None
    out["entity_id"] = entity.id
    return out


def typed_payload(db: Session, world_id: str, payload: dict, vocab: AnalysisVocabulary) -> Optional[dict]:
    """The queue's payload of one typed `event_creation`, or None to drop it.
    A payload naming no type at all is returned as it is (the untyped shape)."""
    if payload.get("event_type") is None and payload.get("new_type") is None:
        return payload
    found = _type_of(db, world_id, payload, vocab)
    if found is None:
        return None
    type_id, type_name, roles, counts, definition = found
    participants: list[dict] = []
    for raw in payload.get("participants") or []:
        item = _participant(db, world_id, raw, roles, vocab)
        if item is None:
            _log.warning("[skip] event_creation participant left out: %r", raw)
            continue
        if not any((p["role"], p["entity_id"], p["sorte_name"]) == (item["role"], item["entity_id"],
                                                                    item["sorte_name"]) for p in participants):
            participants.append(item)
    quantity = payload.get("quantity")
    quantity = quantity if counts and isinstance(quantity, int) and not isinstance(quantity, bool) \
        and quantity >= 1 else None
    place = db.get(Entity, payload.get("location_id")) if isinstance(payload.get("location_id"), str) else None
    out = {
        "title": str(payload.get("title") or "").strip() or type_name,
        "description": payload.get("description") or None,
        "type_id": type_id, "type_name": type_name,
        "participants": participants, "quantity": quantity,
        "location_id": place.id if place is not None and place.world_id == world_id
        and place.type == "location" else None,
    }
    if definition is not None:
        out["new_type"] = definition
    else:
        out["state_changes"] = type_changes(db, world_id, vocab.types[type_id],
                                            [(p["role_id"], p["entity_id"]) for p in participants])
    return out
