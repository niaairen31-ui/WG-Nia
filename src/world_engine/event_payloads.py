"""A model's event proposal, read into the journal's spec (TICKET-0114,
BRIEF-0114-C; decisions D1, E1, I2, N1 and O1 of the conditions series).

`_apply_mutation`'s `event_creation` branch applies what the creator
approved through `writes.events.write_event`; this module turns the
proposal's payload into that writer's `EventSpec`. Two payload shapes:

- typed (the play analyzer since BRIEF-0114-H): `type_id`, `participants`
  (`role_id` with an `entity_id` or a `sorte_id`, and `secret`),
  `quantity`, `location_id`. Its scopes are its type's (W1). Or, instead
  of `type_id`, `new_type` (I2): the type the model proposed, approved with
  the event -- written first (`write_event_type`; a type the world has by
  then under that name is used instead), its participants naming its roles
  by `role`; a participant's `sorte_name` is a sorte the world lacked,
  written likewise (`write_sorte`) unless it exists by then. All inside the
  applier's savepoint: refused, nothing is written.
- untyped (the world tick until TICKET-0119, and every proposal written
  before): `type` (a former category), `involved_entities`,
  `knowledge_status`, `location_id`. It is typed by its domain
  (`writes.event_types.ensure_domain_type`, N1), its entities take the one
  role « Impliqué » when that role accepts their type (an entity it does
  not accept is left out, never forced), and it is known by everyone at
  `knows` when `public` or `confirmed`, by its participants only when
  `secret` -- the meaning `knowledge_status` had (O1).

Where it happened in time (E1): `provenance` reads the session of the
mutation's conversation, or the session and day of its declared action; a
tick proposal has neither.

Reads, and writes only through `ensure_domain_type` (an untyped proposal
whose domain has no type yet makes it), `write_event_type` and
`write_sorte` (a typed one's proposed type and sortes) -- each inside the
applier's savepoint.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .event_proposals import type_spec
from .event_vocab import role_accepts, type_view, world_event_types, world_sortes
from .lore_resolve import normalize_surface
from .models import Conversation, Entity, PassPlay, ProposedMutation
from .writes.event_types import ensure_domain_type, write_event_type, write_sorte
from .writes.events import EventScopeSpec, EventSpec, ParticipantSpec

PUBLIC_STATUSES: tuple[str, ...] = ("public", "confirmed")
PUBLIC_LEVEL = "knows"


def provenance(db: Session, mut: ProposedMutation) -> tuple[Optional[str], Optional[str]]:
    """(session_id, batch_id) of the mutation's source, when it has one."""
    if mut.conversation_id:
        conversation = db.get(Conversation, mut.conversation_id)
        return (conversation.session_id if conversation is not None else None), None
    if mut.pass_play_id:
        pass_play = db.get(PassPlay, mut.pass_play_id)
        if pass_play is not None:
            return pass_play.session_id, pass_play.batch_id
    return None, None


def _new_type(db: Session, world_id: str, definition: dict) -> str:
    """The proposed type's id: the world's type of that name, or the one
    written now. The card's definition is the writer's spec in the form
    of `event_proposals.type_definition`."""
    key = normalize_surface(str(definition.get("name") or ""))
    same = next((v for v in world_event_types(db, world_id) if normalize_surface(v.name) == key), None)
    if same is not None:
        return same.id
    spec = type_spec({"name": definition.get("name"), "domain": definition.get("domain"),
                      "quantity": definition.get("counts_quantity"),
                      "chronicle": definition.get("in_chronicle"), "secret": definition.get("participants_secret"),
                      "roles": [{"name": r.get("name"), "for": r.get("entity_types") or [],
                                 "sorte": r.get("accepts_sorte")}
                                for r in definition.get("roles") or [] if isinstance(r, dict)]})
    return write_event_type(db, world_id=world_id, spec=spec).id


def _sorte(db: Session, world_id: str, name: str) -> str:
    key = normalize_surface(name)
    same = next((s for s in world_sortes(db, world_id) if normalize_surface(s.name) == key), None)
    return same.id if same is not None else write_sorte(db, world_id=world_id, name=name).id


def _typed(db: Session, world_id: str, payload: dict) -> EventSpec:
    type_id = payload.get("type_id")
    if not type_id and isinstance(payload.get("new_type"), dict):
        type_id = _new_type(db, world_id, payload["new_type"])
    view = type_view(db, str(type_id))
    by_name = {normalize_surface(r.name): r.id for r in view.active_roles()} if view is not None else {}
    participants = []
    for p in payload.get("participants") or []:
        if not isinstance(p, dict):
            continue
        role_id = p.get("role_id") or by_name.get(normalize_surface(str(p.get("role") or ""))) or ""
        sorte_id = p.get("sorte_id") or None
        if sorte_id is None and str(p.get("sorte_name") or "").strip():
            sorte_id = _sorte(db, world_id, str(p["sorte_name"]).strip())
        participants.append(ParticipantSpec(
            role_id=str(role_id), entity_id=p.get("entity_id") or None, sorte_id=sorte_id,
            secret=p.get("secret") if isinstance(p.get("secret"), bool) else None))
    quantity = payload.get("quantity")
    return EventSpec(
        type_id=str(type_id), title=str(payload.get("title") or ""),
        description=payload.get("description"), location_id=payload.get("location_id") or None,
        quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
        participants=tuple(participants),
    )


def _untyped(db: Session, world_id: str, payload: dict) -> EventSpec:
    event_type = ensure_domain_type(db, world_id=world_id, domain=payload.get("type"))
    view = type_view(db, event_type.id)
    role = view.active_roles()[0]
    participants = []
    for entity_id in payload.get("involved_entities") or []:
        entity = db.get(Entity, entity_id) if isinstance(entity_id, str) else None
        if entity is not None and entity.world_id == world_id and role_accepts(role, entity.type) \
                and all(p.entity_id != entity.id for p in participants):
            participants.append(ParticipantSpec(role_id=role.id, entity_id=entity.id))
    public = payload.get("knowledge_status") in PUBLIC_STATUSES
    return EventSpec(
        type_id=event_type.id, title=str(payload.get("title") or ""), description=payload.get("description"),
        location_id=payload.get("location_id") or None, participants=tuple(participants),
        scopes=(EventScopeSpec("world", None, PUBLIC_LEVEL),) if public else (),
    )


def spec_from_payload(db: Session, world_id: str, payload: dict, *, session_id: Optional[str] = None,
                      batch_id: Optional[str] = None) -> EventSpec:
    """The `EventSpec` of one `event_creation` payload, typed or not."""
    typed = payload.get("type_id") or isinstance(payload.get("new_type"), dict)
    spec = _typed(db, world_id, payload) if typed else _untyped(db, world_id, payload)
    return EventSpec(**{**spec.__dict__, "session_id": session_id, "batch_id": batch_id})
