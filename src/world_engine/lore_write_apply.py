"""Validate and apply a lore proposal (TICKET-0098, BRIEF-0098-C, C-02).

A proposal is what the creator confirmed in the Lore shell's writing panel:
entities to create or reuse, facts to create, extend or rewrite, who knows
them, faction memberships and `controls` edges (decisions C1, D1, E1, P1,
R1, S1). This module never calls a model and never commits. `validate`
reads only; `apply_proposal` validates first, then writes through the
chokepoints (`writes/facets.py`, `writes/knowledge.py`,
`writes/factions.py`, `writes/relations.py`, `writes/lore_entries.py`) in
one caller-owned transaction, and records every row it wrote against one
`lore_entry`. A row that already exists (a knower already holding the fact,
a participant already attached, an active membership, a `controls` edge) is
skipped and reported, never duplicated.

Entities are created through a callable the caller injects
(`create_entity(name, type) -> Entity`, flushed): the commit-free creation
core lives with the creator CRUD, which this module does not import.
Every id in a proposal is re-read here against the proposal's world.

TICKET-0119 (BRIEF-0119-G, U1): a proposal may hold EVENTS, each naming
the entities of the statement by their ref -- its participants, its place,
its scopes, the entities its changes name and an entity a change's value
names. They are written after everything else, each through the journal's
one writer (`event_payloads.spec_from_payload`, `writes.events.record_event`:
its fact, its participants' knowledge, its changes), and every row it wrote
is recorded against the entry. A type the world lacks is created from the
panel before the commit, never here: an event still carrying `new_type` is
refused. A refused event refuses the whole proposal (INV-57).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from .event_payloads import spec_from_payload
from .facets import DESCRIPTIVE_FACETS, FACETS
from .fact_refs import find_held
from .models import Entity, Fact, FactDefault, FactionMembership, FactParticipant, Relation
from .writes.facets import ScopeChoice, add_lore_fact, edit_entity_fact
from .writes.facts import FACT_CHANGE_KINDS
from .writes.facts import attach_participants, create_fact_default
from .writes.factions import write_membership
from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER, write_knowledge
from .writes.events import record_event
from .writes.lore_entries import record_entry_row, write_lore_entry
from .writes.relations import write_relation

CREATED_BY = "creator_lore"
ENTITY_TYPES: tuple[str, ...] = ("character", "location", "faction", "item")
FACT_ACTIONS: tuple[str, ...] = ("create", "existing", "rewrite")
SCOPE_TYPES: tuple[str, ...] = ("world", "faction", "location", "rencontre")
_SCOPE_ENTITY_TYPE: dict[str, Optional[str]] = {
    "world": None, "faction": "faction", "location": "location", "rencontre": None,
}


class ProposalError(ValueError):
    """The proposal cannot be written; the message is shown to the creator."""


@dataclass
class ApplyResult:
    entry_id: str
    written: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)


def _list(proposal: dict, key: str) -> list[dict]:
    value = proposal.get(key) or []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProposalError(f"« {key} » doit être une liste d'objets.")
    return value


def _text(item: dict, key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProposalError(f"{where} : « {key} » est vide.")
    return value.strip()


def _validate_entities(db: Session, world_id: str, entities: list[dict]) -> dict[str, dict]:
    """ref -> the entity item, with `_type` set (the type an existing entity has)."""
    refs: dict[str, dict] = {}
    for item in entities:
        ref = _text(item, "ref", "Entité")
        if ref in refs:
            raise ProposalError(f"Entité « {ref} » déclarée deux fois.")
        action = item.get("action")
        if action == "create":
            _text(item, "name", f"Entité {ref}")
            if item.get("type") not in ENTITY_TYPES:
                raise ProposalError(f"Entité {ref} : type {item.get('type')!r} non permis.")
            item["_type"] = item["type"]
        elif action == "existing":
            entity = db.get(Entity, item.get("entity_id") or "")
            if entity is None or entity.world_id != world_id or entity.status != "active":
                raise ProposalError(f"Entité {ref} : aucune entité active de ce monde.")
            item["_type"] = entity.type
        else:
            raise ProposalError(f"Entité {ref} : action {action!r} inconnue.")
        refs[ref] = item
    return refs


def _entity_ref(refs: dict[str, dict], ref: Any, where: str, want: Optional[str] = None) -> str:
    if ref not in refs:
        raise ProposalError(f"{where} : l'entité « {ref} » n'est pas dans la proposition.")
    if want is not None and refs[ref]["_type"] != want:
        raise ProposalError(f"{where} : « {ref} » doit être de type {want}.")
    return ref


def _validate_scopes(refs: dict[str, dict], item: dict, where: str) -> None:
    seen = set()
    for scope in _list(item, "defaults"):
        scope_type = scope.get("scope_type")
        if scope_type not in SCOPE_TYPES:
            raise ProposalError(f"{where} : portée {scope_type!r} inconnue.")
        if scope_type == "world":
            if scope.get("scope_ref") is not None:
                raise ProposalError(f"{where} : la portée monde ne nomme pas d'entité.")
        else:
            _entity_ref(refs, scope.get("scope_ref"), where, _SCOPE_ENTITY_TYPE[scope_type])
        key = (scope_type, scope.get("scope_ref"))
        if key in seen:
            raise ProposalError(f"{where} : la même portée est listée deux fois.")
        seen.add(key)


def _validate_knowers(refs: dict[str, dict], item: dict, where: str) -> None:
    seen = set()
    for knower in _list(item, "knowers"):
        ref = _entity_ref(refs, knower.get("entity_ref"), where)
        if ref in seen:
            raise ProposalError(f"{where} : « {ref} » sait deux fois le même fait.")
        seen.add(ref)
        if knower.get("level") not in KNOWLEDGE_LEVEL_LADDER:
            raise ProposalError(f"{where} : niveau {knower.get('level')!r} inconnu.")
        for flag in ("is_secret", "is_incorrect"):
            if not isinstance(knower.get(flag, False), bool):
                raise ProposalError(f"{where} : « {flag} » doit être vrai ou faux.")


def _world_fact(db: Session, world_id: str, fact_id: Any, where: str) -> Fact:
    fact = db.get(Fact, fact_id or "")
    if fact is None or fact.world_id != world_id:
        raise ProposalError(f"{where} : aucun fait de ce monde ne porte cet identifiant.")
    return fact


def _validate_fact(db: Session, world_id: str, refs: dict[str, dict], item: dict) -> None:
    ref = _text(item, "ref", "Fait")
    where = f"Fait {ref}"
    action = item.get("action")
    if action not in FACT_ACTIONS:
        raise ProposalError(f"{where} : action {action!r} inconnue.")
    participants = item.get("participants") or []
    if not isinstance(participants, list):
        raise ProposalError(f"{where} : « participants » doit être une liste.")
    for participant in participants:
        _entity_ref(refs, participant, where)
    if action == "create":
        _text(item, "content", where)
        spec = FACETS.get(item.get("facet"))
        if spec is None or spec.granularity == "typed":
            raise ProposalError(f"{where} : facette {item.get('facet')!r} non permise.")
        if (spec.granularity == "bloc" or item["facet"] == "appellation") and len(participants) != 1:
            raise ProposalError(f"{where} : une facette {item['facet']} a un seul participant.")
    else:
        fact = _world_fact(db, world_id, item.get("fact_id"), where)
        typed = fact.relation_id or fact.event_id or fact.world_law_id
        if participants and typed:
            raise ProposalError(f"{where} : un fait typé ne reçoit pas de participant.")
        if action == "rewrite":
            _text(item, "content", where)
            spec = FACETS.get(fact.facet or "")
            if fact.facet not in DESCRIPTIVE_FACETS or spec is None or spec.granularity != "bloc":
                raise ProposalError(f"{where} : seul un fait « bloc » se réécrit.")
            if item.get("kind") not in FACT_CHANGE_KINDS:
                raise ProposalError(
                    f"{where} : dis si la réécriture est une correction ou un changement dans le monde.")
    _validate_scopes(refs, item, where)
    _validate_knowers(refs, item, where)


def validate(db: Session, world_id: str, proposal: dict) -> dict[str, dict]:
    """Raise `ProposalError` on the first defect; return the entity refs.
    Reads only."""
    if not isinstance(proposal, dict):
        raise ProposalError("La proposition doit être un objet.")
    _text(proposal, "statement", "Proposition")
    refs = _validate_entities(db, world_id, _list(proposal, "entities"))
    fact_refs: set[str] = set()
    for item in _list(proposal, "facts"):
        _validate_fact(db, world_id, refs, item)
        if item["ref"] in fact_refs:
            raise ProposalError(f"Fait « {item['ref']} » déclaré deux fois.")
        fact_refs.add(item["ref"])
    for item in _list(proposal, "memberships"):
        _entity_ref(refs, item.get("entity_ref"), "Appartenance", "character")
        _entity_ref(refs, item.get("faction_ref"), "Appartenance", "faction")
    for item in _list(proposal, "controls"):
        _entity_ref(refs, item.get("owner_ref"), "Possession")
        _entity_ref(refs, item.get("location_ref"), "Possession", "location")
    for item in _list(proposal, "events"):
        _validate_event(refs, item)
    if not (fact_refs or proposal.get("memberships") or proposal.get("controls") or proposal.get("events")):
        raise ProposalError("La proposition n'écrit rien.")
    return refs


def _validate_event(refs: dict[str, dict], item: dict) -> None:
    where = f"Événement {item.get('ref') or '?'}"
    if item.get("new_type") is not None:
        raise ProposalError(f"{where} : crée d'abord le type proposé.")
    if not isinstance(item.get("type_id"), str) or not item["type_id"]:
        raise ProposalError(f"{where} : choisis son type.")
    _text(item, "title", where)
    for p in item.get("participants") or []:
        if not isinstance(p, dict):
            raise ProposalError(f"{where} : un participant doit être un objet.")
        if p.get("entity_ref") is not None:
            _entity_ref(refs, p["entity_ref"], where)
    if item.get("location_ref") is not None:
        _entity_ref(refs, item["location_ref"], where, "location")
    for change in item.get("state_changes") or []:
        if not isinstance(change, dict):
            raise ProposalError(f"{where} : un changement doit être un objet.")
        _entity_ref(refs, change.get("entity_ref"), where)
    for scope in item.get("scopes") or []:
        if isinstance(scope, dict) and scope.get("scope_ref") is not None:
            _entity_ref(refs, scope["scope_ref"], where)


class _Writer:
    """Applies one validated proposal; every written row is recorded."""

    def __init__(self, db: Session, world_id: str, entry_id: str) -> None:
        self.db, self.world_id = db, world_id
        self.result = ApplyResult(entry_id=entry_id)
        self.ids: dict[str, str] = {}

    def record(self, table: str, row_id: str, action: str = "created") -> None:
        record_entry_row(self.db, entry_id=self.result.entry_id, row_table=table,
                         row_id=row_id, action=action)
        key = f"{table}:{action}"
        self.result.written[key] = self.result.written.get(key, 0) + 1

    def entities(self, refs: dict[str, dict], create_entity: Callable[[str, str], Entity]) -> None:
        for ref, item in refs.items():
            if item["action"] == "existing":
                self.ids[ref] = item["entity_id"]
                continue
            entity = create_entity(item["name"].strip(), item["type"])
            self.ids[ref] = entity.id
            self.record("entity", entity.id)
        self.db.flush()

    def scopes(self, item: dict) -> tuple[ScopeChoice, ...]:
        return tuple(
            ScopeChoice(s["scope_type"], None if s["scope_type"] == "world" else self.ids[s["scope_ref"]])
            for s in _list(item, "defaults")
        )

    def add_defaults(self, fact: Fact, scopes: tuple[ScopeChoice, ...]) -> None:
        for scope in scopes:
            held = self.db.exec(select(FactDefault).where(
                FactDefault.fact_id == fact.id, FactDefault.scope_type == scope.scope_type,
                FactDefault.scope_id == scope.scope_id)).first()
            if held is not None:
                self.result.skipped.append(f"portée {scope.scope_type} déjà présente sur un fait")
                continue
            row = create_fact_default(self.db, world_id=self.world_id, fact_id=fact.id,
                                      scope_type=scope.scope_type, scope_id=scope.scope_id,
                                      level="knows", created_by=CREATED_BY)
            self.db.flush()
            self.record("fact_default", row.id)

    def add_participants(self, fact: Fact, entity_ids: list[str]) -> None:
        held = set(self.db.exec(select(FactParticipant.entity_id).where(
            FactParticipant.fact_id == fact.id)).all())
        fresh = [eid for eid in entity_ids if eid not in held]
        if len(fresh) < len(entity_ids):
            self.result.skipped.append("participant déjà rattaché à un fait")
        for row in attach_participants(self.db, fact=fact, entity_ids=fresh) if fresh else []:
            self.db.flush()
            self.record("fact_participant", row.id)

    def knowers(self, fact: Fact, item: dict) -> None:
        for knower in _list(item, "knowers"):
            entity_id = self.ids[knower["entity_ref"]]
            if find_held(self.db, entity_id, {"fact_id": fact.id}) is not None:
                self.result.skipped.append("une entité connaissait déjà un fait")
                continue
            row = write_knowledge(
                self.db, mode="update", entity_id=entity_id, fact_id=fact.id,
                level=knower["level"], is_secret=bool(knower.get("is_secret", False)),
                is_incorrect=bool(knower.get("is_incorrect", False)), changed_by=CREATED_BY,
            )
            self.db.flush()
            self.record("knowledge", row.id)

    def fact(self, item: dict) -> None:
        participants = [self.ids[ref] for ref in item.get("participants") or []]
        if item["action"] == "create":
            rows = add_lore_fact(
                self.db, world_id=self.world_id, facet=item["facet"], content=item["content"],
                created_by=CREATED_BY, participant_ids=participants, aspect=item.get("aspect"),
                scopes=self.scopes(item), mentions=item.get("mentions") or None,
            )
            self.db.flush()
            fact = rows.fact
            self.record("fact", fact.id)
            for row in rows.participants:
                self.record("fact_participant", row.id)
            for row in rows.defaults:
                self.record("fact_default", row.id)
        else:
            fact = self.db.get(Fact, item["fact_id"])
            if item["action"] == "rewrite":
                edit_entity_fact(self.db, fact_id=fact.id, content=item["content"],
                                 changed_by=CREATED_BY, kind=item["kind"])
                self.record("fact", fact.id, "updated")
            self.add_participants(fact, participants)
            self.add_defaults(fact, self.scopes(item))
        self.knowers(fact, item)

    def event(self, item: dict) -> None:
        """U1: one event through the journal's writer, every row recorded."""
        spec = spec_from_payload(self.db, self.world_id, _event_payload(item, self.ids))
        written = record_event(self.db, world_id=self.world_id, spec=spec, created_by=CREATED_BY)
        seen: set[tuple[str, str]] = set()
        for table, row_id, action in written.rows:
            if (table, row_id) not in seen:
                seen.add((table, row_id))
                self.record(table, row_id, action)

    def membership(self, item: dict) -> None:
        entity_id, faction_id = self.ids[item["entity_ref"]], self.ids[item["faction_ref"]]
        held = self.db.exec(select(FactionMembership).where(
            FactionMembership.entity_id == entity_id, FactionMembership.faction_id == faction_id,
            FactionMembership.left_at.is_(None))).first()
        if held is not None:
            self.result.skipped.append("appartenance déjà active")
            return
        row = write_membership(self.db, mode="open", world_id=self.world_id,
                               entity_id=entity_id, faction_id=faction_id)
        self.db.flush()
        self.record("faction_membership", row.id)

    def control(self, item: dict) -> None:
        owner_id, location_id = self.ids[item["owner_ref"]], self.ids[item["location_ref"]]
        held = self.db.exec(select(Relation).where(
            Relation.type == "controls", Relation.entity_a_id == owner_id,
            Relation.entity_b_id == location_id)).first()
        if held is not None:
            self.result.skipped.append("possession déjà enregistrée")
            return
        row = write_relation(self.db, mode="set", world_id=self.world_id, entity_a_id=owner_id,
                             entity_b_id=location_id, type="controls", value=50,
                             changed_by=CREATED_BY)
        self.db.flush()
        self.record("relation", row.id)


def _event_payload(item: dict, ids: dict[str, str]) -> dict:
    """An event of the proposal as a typed `event_creation` payload, its refs
    made ids."""
    def value(raw: Any) -> Any:
        return ids.get(raw, raw) if isinstance(raw, str) else raw

    payload = {
        "title": item["title"], "description": item.get("description"), "type_id": item["type_id"],
        "quantity": item.get("quantity"),
        "location_id": ids[item["location_ref"]] if item.get("location_ref") else None,
        "participants": [{"role_id": p.get("role_id"), "role": p.get("role"),
                          "entity_id": ids[p["entity_ref"]] if p.get("entity_ref") else None,
                          "sorte_id": p.get("sorte_id"), "secret": p.get("secret")}
                         for p in item.get("participants") or []],
        "state_changes": [{"entity_id": ids[c["entity_ref"]], "attribute": c.get("attribute"),
                           "mode": c.get("mode") or "set", "value": value(c.get("value"))}
                          for c in item.get("state_changes") or []],
    }
    if isinstance(item.get("scopes"), list):
        payload["scopes"] = [{"scope_type": s.get("scope_type"), "level": s.get("level") or "knows",
                              "scope_id": ids[s["scope_ref"]] if s.get("scope_ref") else None}
                             for s in item["scopes"] if isinstance(s, dict)]
    return payload


def apply_proposal(
    db: Session, world_id: str, proposal: dict,
    create_entity: Callable[[str, str], Entity],
) -> ApplyResult:
    """Validate, then write the whole proposal. Never commits: the caller
    commits once on success and rolls back on any exception. A write-site
    `ValueError` surfaces as `ProposalError`."""
    refs = validate(db, world_id, proposal)
    entry = write_lore_entry(db, world_id=world_id, statement=proposal["statement"],
                             questions=proposal.get("questions"), answers=proposal.get("answers"))
    db.flush()
    writer = _Writer(db, world_id, entry.id)
    try:
        writer.entities(refs, create_entity)
        for item in _list(proposal, "facts"):
            writer.fact(item)
        for item in _list(proposal, "memberships"):
            writer.membership(item)
        for item in _list(proposal, "controls"):
            writer.control(item)
        for item in _list(proposal, "events"):
            writer.event(item)
    except ProposalError:
        raise
    except ValueError as exc:
        raise ProposalError(f"Écriture refusée : {exc}") from exc
    return writer.result
