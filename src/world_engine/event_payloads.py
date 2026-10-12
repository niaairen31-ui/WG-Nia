"""A model's event proposal, read into the journal's spec (TICKET-0114,
BRIEF-0114-C; decisions D1, E1, I2, N1 and O1 of the conditions series).

`_apply_mutation`'s `event_creation` branch applies what the creator
approved through `writes.events.write_event`; this module turns the
proposal's payload into that writer's `EventSpec`. Two payload shapes:

- typed (the play analyzer since BRIEF-0114-H): `type_id`, `participants`
  (`role_id` with an `entity_id` or a `sorte_id`, and `secret`),
  `quantity`, `location_id`. Its scopes are its type's (W1).
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
whose domain has no type yet makes it, inside the applier's savepoint).
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .event_vocab import role_accepts, type_view
from .models import Conversation, Entity, PassPlay, ProposedMutation
from .writes.event_types import ensure_domain_type
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


def _typed(payload: dict) -> EventSpec:
    participants = tuple(
        ParticipantSpec(role_id=str(p.get("role_id") or ""), entity_id=p.get("entity_id") or None,
                        sorte_id=p.get("sorte_id") or None,
                        secret=p.get("secret") if isinstance(p.get("secret"), bool) else None)
        for p in (payload.get("participants") or []) if isinstance(p, dict)
    )
    quantity = payload.get("quantity")
    return EventSpec(
        type_id=str(payload.get("type_id")), title=str(payload.get("title") or ""),
        description=payload.get("description"), location_id=payload.get("location_id") or None,
        quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
        participants=participants,
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
    spec = _typed(payload) if payload.get("type_id") else _untyped(db, world_id, payload)
    return EventSpec(**{**spec.__dict__, "session_id": session_id, "batch_id": batch_id})
