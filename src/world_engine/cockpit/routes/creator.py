"""Creator-mode generation + composite routes: entity/world/player/skill-
catalogue/agenda/event draft generation, world CRUD, bootstrap,
player-character composite create, NPC listing.

Split out of `cockpit/app.py` (TICKET-0027, BRIEF-0027-d) — pure move, no
logic change, no route path/method change. Region generation + commit live
in the sibling `cockpit/routes/regions.py` (module-budget split).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...entity_author import build_world_roster as _build_world_roster
from ...entity_author import generate_agenda_draft as _generate_agenda_draft
from ...entity_author import generate_entity_draft as _generate_entity_draft
from ...entity_author import generate_event_draft as _generate_event_draft
from ...entity_author import generate_npc_goals as _generate_npc_goals
from ...entity_author import generate_player_draft as _generate_player_draft
from ...entity_author import generate_skill_catalogue_draft as _generate_skill_catalogue_draft
from ...entity_author import generate_world_draft as _generate_world_draft
from ...db import get_session
from ...models import (
    BASE_SKILL_DOMAINS,
    Character,
    Entity,
    Faction,
    FactionMembership,
    ProposedMutation,
    Skill,
    SkillDefinition,
    User,
    World,
)
from ...writes import (
    KNOWLEDGE_LEVELS,
    delete_world_cascade as _delete_world_cascade,
    write_knowledge,
    write_world_laws,
)
from .. import crud as _crud

router = APIRouter()


class EntityGenerateBody(BaseModel):
    entity_type: str
    brief: str


def _generate_draft_with_l1(entity_type: str, brief: str, db: Session) -> dict:
    """Shared write-free generation core (BRIEF-0019-a item 4, RECON F2) —
    both `/api/entities/generate` and `/api/creations/{mutation_id}/generate`
    call this instead of `generate_entity_draft` directly, so there is ONE
    generation path and L1 goals come for free on either route. Writes
    nothing; never raises (see `entity_author.generate_entity_draft`).

    L1 (BRIEF-0013-b): on a successful character draft, also calls
    generate_npc_goals with the draft's public fields and the resolved
    faction's `goals` (read-only query, None when unaffiliated) and merges
    the result as `draft["public"]["goals"]`. A goal-generation failure never
    fails the draft — it's appended to `notes` and the character draft ships
    without goals.
    """
    result = _generate_entity_draft(entity_type, brief, db)
    if entity_type == "character" and result.get("ok"):
        pub = result["draft"]["public"]
        faction_goals = None
        faction_id = pub.get("faction_id")
        if faction_id:
            faction = db.get(Faction, faction_id)
            faction_goals = faction.goals if faction else None
        goals_result = _generate_npc_goals(
            pub.get("name", ""), pub.get("description", ""), pub.get("backstory", ""), faction_goals, db
        )
        if goals_result.get("ok"):
            pub["goals"] = {"long": goals_result.get("long", ""), "shorts": goals_result.get("shorts", [])}
        else:
            result.setdefault("notes", []).append(
                f"Génération des objectifs échouée : {goals_result.get('error')}"
            )
    return result


@router.post("/api/entities/generate")
def generate_entity(
    body: EntityGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI draft generator (BRIEF-24; L1 goals, BRIEF-0013-b).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — keeping it in a separate router makes
    that property legible. Performs no write itself. Returns
    {"ok": false, "error": ...} (never a 500) on any failure — see
    entity_author.generate_entity_draft.
    """
    return _generate_draft_with_l1(body.entity_type, body.brief, db)


# ── Two-stage entity creation realization (TICKET-0019, BRIEF-0019-a) ───────
# The tick (or, dormantly, a conversation — RECON F6) proposes a THIN germ;
# creator approval parks it (`approve_mutation`'s short-circuit above); these
# two routes serve the Création tab's "Créations en attente" strip — one pure
# read, one pure write-free generation. Realization itself (the actual canon
# write) happens only in crud.py's create_entity, via its optional
# `mutation_id` linkage.

_ENTITY_CREATION_TYPES = frozenset({"character", "location", "faction"})

_ENTITY_CREATION_INTROS: dict[str, str] = {
    "character": "Nouveau personnage",
    "location": "Nouveau lieu",
    "faction": "Nouvelle faction",
}


def _compose_entity_creation_brief(payload: dict) -> str:
    """French prose brief for the pure generation chain (item 4) — weaves
    name + concept + anchor into 2-4 sentences. `anchor` already carries any
    scope-situating prose the model proposed (near/within/serves — RECON F7),
    so no extra lookup against the mutation's tick/scope is needed. Tolerant
    of the dormant conversation channel's shapeless payload (RECON F6):
    name/concept fall back across `name|title` and `concept|description|
    content`.
    """
    entity_type = str(payload.get("entity_type") or "").strip().casefold()
    intro = _ENTITY_CREATION_INTROS.get(entity_type, "Nouvelle entité")
    name = str(payload.get("name") or payload.get("title") or "").strip()
    concept = str(
        payload.get("concept") or payload.get("description") or payload.get("content") or ""
    ).strip()
    anchor = str(payload.get("anchor") or "").strip()

    sentences = [f"{intro} : {name}." if name else f"{intro}."]
    if concept:
        sentences.append(concept if concept.endswith((".", "!", "?")) else f"{concept}.")
    if anchor:
        sentences.append(anchor if anchor.endswith((".", "!", "?")) else f"{anchor}.")
    return " ".join(sentences)


@router.get("/api/creations/pending")
def list_pending_creations(db: Session = Depends(get_session)) -> list[dict]:
    """Approved-but-unrealized entity_creation germs, ALL sources — tick AND
    the dormant conversation channel join the same list (0017-style
    awakening, RECON F6). Query: mutation_type == entity_creation,
    status == approved, payload lacks created_entity_id.
    """
    rows = db.exec(
        select(ProposedMutation)
        .where(
            ProposedMutation.mutation_type == "entity_creation",
            ProposedMutation.status == "approved",
        )
        .order_by(ProposedMutation.proposed_at.desc())
    ).all()

    items: list[dict] = []
    for mut in rows:
        payload = mut.payload if isinstance(mut.payload, dict) else {}
        if "created_entity_id" in payload:
            continue
        entity_type = str(payload.get("entity_type") or "").strip().casefold()
        items.append({
            "mutation_id": mut.id,
            "source": "tick" if mut.tick_id else "conversation",
            "proposed_at": mut.proposed_at.isoformat() if mut.proposed_at else None,
            "name": str(payload.get("name") or payload.get("title") or "").strip(),
            "concept": str(
                payload.get("concept") or payload.get("description") or payload.get("content") or ""
            ).strip(),
            "anchor": payload.get("anchor"),
            "entity_type": entity_type if entity_type in _ENTITY_CREATION_TYPES else None,
        })
    return items


@router.post("/api/creations/{mutation_id}/generate")
def generate_creation_draft(mutation_id: str, db: Session = Depends(get_session)) -> dict:
    """Realization generation (item 4) — pure, writes nothing; reuses the
    same write-free chain as `/api/entities/generate` (+ L1 goals) via
    `_generate_draft_with_l1`. Regenerating later is free: an abandoned
    draft costs nothing because the mutation stays 'approved' until
    create_entity's guarded linkage flips it.
    """
    mut = db.get(ProposedMutation, mutation_id)
    if mut is None or mut.mutation_type != "entity_creation" or mut.status != "approved":
        raise HTTPException(409, "Mutation is not an approved, unrealized entity_creation germ")

    payload = mut.payload if isinstance(mut.payload, dict) else {}
    if "created_entity_id" in payload:
        raise HTTPException(409, "This germ has already been realized")

    entity_type = str(payload.get("entity_type") or "").strip().casefold()
    if entity_type not in _ENTITY_CREATION_TYPES:
        raise HTTPException(409, "Germ has no valid entity_type — cannot generate")

    brief = _compose_entity_creation_brief(payload)
    result = _generate_draft_with_l1(entity_type, brief, db)
    return {
        "ok": result.get("ok", False),
        "draft": result.get("draft"),
        "notes": result.get("notes", []),
        "error": result.get("error"),
        "mutation_id": mutation_id,
        "entity_type": entity_type,
    }


class WorldGenerateBody(BaseModel):
    brief: str


@router.post("/api/worlds/generate")
def generate_world(
    body: WorldGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI world-premise draft generator (BRIEF-47).

    Deliberately NOT in crud.py and NOT routed through generate_entity:
    World has no entity_id FK, so it is not an entity type. Writes
    nothing — delegates only to entity_author.generate_world_draft.
    Returns {"ok": false, "error": ...} (never a 500) on any failure.
    """
    return _generate_world_draft(body.brief, db)


class PlayerGenerateBody(BaseModel):
    brief: str


@router.post("/api/characters/player/generate")
def generate_player(
    body: PlayerGenerateBody, db: Session = Depends(get_session)
) -> dict:
    """Creator-side AI PC-draft generator (BRIEF-52).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_player_draft. Returns {"ok": false, "error": ...}
    (never a 500) on any failure.
    """
    return _generate_player_draft(body.brief, db)


class SkillCatalogueGenerateBody(BaseModel):
    brief: str


@router.post("/api/skill-definitions/generate")
def generate_skill_catalogue(
    body: SkillCatalogueGenerateBody, db: Session = Depends(get_session)
) -> dict:
    """Creator-side AI skill-catalogue draft generator (BRIEF-56,
    D2-attach-b/D2-template-b).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_skill_catalogue_draft. Returns
    {"ok": false, "error": ...} (never a 500) on any failure. The creator
    edits/accepts the proposed skills through the existing creator-CRUD
    `POST /api/skill-definitions` (crud.py) — never written here.
    """
    return _generate_skill_catalogue_draft(body.brief, db)


class AgendaGenerateBody(BaseModel):
    owner_entity_id: str
    brief: str


@router.post("/api/agendas/generate")
def generate_agenda(
    body: AgendaGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI agenda-draft assistant (TICKET-0021, BRIEF-0021-b,
    B1/C1/D1).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_agenda_draft. Server-side D1 resolution mirrors
    write_agenda's owner rule so the assistant can never draft for an owner
    the create would reject: 404/422 if the entity is missing, inactive, or
    not `faction`/`character`. owner_context is built from PUBLIC fields
    only (faction: description + Faction.philosophy; character: description
    + Character.backstory) — secrets stay structurally excluded: no
    `knowledge` row, no `character.secrets`, no `internal_tensions` is ever
    read here. Returns {"ok": false, "error": ...} (never a 500) on any
    failure.
    """
    owner = db.get(Entity, body.owner_entity_id)
    if owner is None:
        raise HTTPException(404, f"Entity {body.owner_entity_id!r} not found")
    if owner.status != "active" or owner.type not in ("faction", "character"):
        raise HTTPException(422, "owner_entity_id must be an active faction or character")

    if owner.type == "faction":
        owner_kind = "faction"
        faction = db.get(Faction, owner.id)
        philosophy = f"Philosophie : {faction.philosophy}" if faction and faction.philosophy else None
        parts = [p for p in (owner.description, philosophy) if p]
    else:
        owner_kind = "personnage"
        character = db.get(Character, owner.id)
        backstory = f"Passé : {character.backstory}" if character and character.backstory else None
        parts = [p for p in (owner.description, backstory) if p]
    owner_context = "\n".join(parts) if parts else "(aucune description)"

    return _generate_agenda_draft(owner_kind, owner.name, owner_context, body.brief, db)


class EventGenerateBody(BaseModel):
    brief: str
    location_id: Optional[str] = None


@router.post("/api/events/generate")
def generate_event(
    body: EventGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI event-draft assistant (TICKET-0022, BRIEF-0022-b,
    I2/J3).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_event_draft. `location_id`, when supplied, must
    resolve to an active `location` entity in the active world (the same
    predicate as `_apply_mutation`'s `event_creation` branch); it then wins
    outright over the model's own location proposal. `location_context` is
    the location's `name` + `description` only — public fields, never
    `internal_name`, never `metadata`. The J3 roster
    (`entity_author.build_world_roster`) is public-only, filtered in SQL.
    Returns {"ok": false, "error": ...} (never a 500) on any failure.
    """
    brief = (body.brief or "").strip()
    if not brief:
        raise HTTPException(422, "Intention requise.")

    world_id = _crud._world_id(db)

    location_hint = ""
    location_context = ""
    if body.location_id:
        location = db.get(Entity, body.location_id)
        if (
            location is None
            or location.type != "location"
            or location.status != "active"
            or location.world_id != world_id
        ):
            raise HTTPException(422, f"location_id {body.location_id!r} is not an active location in this world")
        location_hint = location.name
        parts = [p for p in (location.name, location.description) if p]
        location_context = "\n".join(parts)

    roster = _build_world_roster(db, world_id)

    return _generate_event_draft(brief, location_hint, location_context, roster, db)


@router.get("/api/worlds")
def list_worlds(db: Session = Depends(get_session)) -> list:
    worlds = db.exec(select(World)).all()
    return [
        {"id": w.id, "name": w.name, "is_active": w.is_active}
        for w in worlds
    ]


@router.post("/api/worlds/{world_id}/activate")
def activate_world(world_id: str, db: Session = Depends(get_session)) -> dict:
    target = db.get(World, world_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"World {world_id!r} not found")
    try:
        for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
            w.is_active = False
            db.add(w)
        db.flush()
        target.is_active = True
        db.add(target)
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "world_id": target.id}


class WorldCreateBody(BaseModel):
    name: str
    description: str = ""
    fundamental_laws: str = ""


@router.post("/api/worlds")
def create_world(body: WorldCreateBody, db: Session = Depends(get_session)) -> dict:
    """Generic empty-world bootstrap (BRIEF-44, B2). Creates one fresh-UUID
    `world` row and auto-activates it in the same transaction (reuses
    activate_world's deactivate-then-activate logic). The created world is
    empty: no PC, no session, no locations, no templates, no entities."""
    try:
        new_world = World(
            name=body.name,
            description=body.description,
        )
        db.add(new_world)
        db.flush()
        write_world_laws(
            db, world=new_world,
            laws=body.fundamental_laws.splitlines(),
            changed_by="creator",
        )
        for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
            w.is_active = False
            db.add(w)
        db.flush()
        new_world.is_active = True
        db.add(new_world)
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "world_id": new_world.id}


def _activate_world_core(world_id: str, db: Session) -> None:
    """Commit-free deactivate-then-activate core (BRIEF-54, E1 deferral).

    Replicates `activate_world`'s inline logic: deactivate every currently-
    active world, `db.flush()`, then activate the target. The flush-between
    is required — `idx_world_one_active` is a partial UNIQUE index, not a
    FK, so `PRAGMA defer_foreign_keys` does not cover it; two active rows
    must never coexist, even mid-transaction. Used by the delete route only
    in this brief — `activate_world` and `create_world` keep their own
    inline duplication (named deferral, not rewired here)."""
    for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
        w.is_active = False
        db.add(w)
    db.flush()
    target = db.get(World, world_id)
    target.is_active = True
    db.add(target)


@router.delete("/api/worlds/{world_id}")
def delete_world(world_id: str, db: Session = Depends(get_session)) -> dict:
    """Hard-delete a world block, full cascade, irreversible (BRIEF-54, A1).

    The sole sanctioned exception to "History is sacred" — see
    `delete_world_cascade` (`writes.py`). One atomic transaction: cascade +
    survivor re-activation either both happen or neither does."""
    target = db.get(World, world_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"World {world_id!r} not found")
    was_active = target.is_active
    try:
        _delete_world_cascade(world_id, db)
        remaining_worlds = db.exec(select(World)).all()
        remaining = len(remaining_worlds)
        if remaining == 0:
            active_world_id = None
        elif was_active:
            survivor = max(remaining_worlds, key=lambda w: w.created_at)
            _activate_world_core(survivor.id, db)
            active_world_id = survivor.id
        else:
            active = next((w for w in remaining_worlds if w.is_active), None)
            active_world_id = active.id if active else None
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "remaining": remaining, "active_world_id": active_world_id}


# ── Bootstrap — resolved play context for the static cockpit JS (BRIEF-45) ────

@router.get("/api/bootstrap")
def get_bootstrap(db: Session = Depends(get_session)) -> dict:
    """Resolved play context for index.html, which is served as a static file
    with no server-side templating. Read-only; opens no session.

    Returns the active world's id, the structurally-resolved player character
    id (character_type='player'), and that character's current_location_id.
    `player_id`/`current_location_id` are null when the active world has no
    PC yet (BRIEF-46: a freshly created world has none until the creator uses
    the create-PC form) — `world_id` must still resolve so that form can
    scope its starting-location dropdown.
    """
    world_id = _crud._world_id(db)
    try:
        player_id = _crud._player_character_id(db, world_id)
    except HTTPException:
        player_id = None
    player_char = db.get(Character, player_id) if player_id else None
    return {
        "world_id": world_id,
        "player_id": player_id,
        "current_location_id": player_char.current_location_id if player_char else None,
    }


# ── Create-PC path (BRIEF-46) ──────────────────────────────────────────────────

class PlayerKnowledgeItem(BaseModel):
    subject: str
    level: str
    content: str


class PlayerCharacterCreateBody(BaseModel):
    name: str
    current_location_id: str
    description: Optional[str] = None
    appearance: Optional[str] = None
    backstory: Optional[str] = None
    knowledge: Optional[list[PlayerKnowledgeItem]] = None


@router.post("/api/characters/player")
def create_player_character(
    body: PlayerCharacterCreateBody, db: Session = Depends(get_session)
) -> dict:
    """Create a PC and place it at a starting location in the active world.

    Binds to the lone creator user (`role='creator'`) — there is no real
    multiplayer user identity yet. Mirrors `seed_pilot.py`'s `char-player`
    creation: entity + `character` row + the four `skill` rows (physical,
    agility, perception, composure) at `tier=0`, since the skill sheet and
    physical-resolution arbiter both read those rows off a PC. One PC per
    user per world is defended by `idx_character_one_pc_per_user_world`
    (partial unique index) — a collision surfaces as a clean `{"ok": false}`,
    not a 500.

    BRIEF-52 (E1): also accepts the optional PC creation assistant draft —
    `description`/`appearance`/`backstory` set on the rows that own them,
    and `knowledge` written through `write_knowledge` with `is_secret=False`
    (never through `POST /api/entities/{id}/knowledge`, which 422s on a bad
    level instead of defaulting to "rumor"). The base-domain skill seed stays
    untouched (B1, no proposed tiers).

    BRIEF-55 (B1, schema v1.63): after the four base-domain rows, also seeds
    one `skill` row per `skill_definition` of the PC's world, at `tier=0`,
    `domain=<definition.base_domain>`, `skill_definition_id=<definition.id>`
    — never proposed by a model.
    """
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    world_id = _crud._world_id(db)

    location_entity = db.get(Entity, body.current_location_id)
    if (
        location_entity is None
        or location_entity.world_id != world_id
        or location_entity.type != "location"
    ):
        raise HTTPException(
            status_code=400,
            detail="current_location_id must be a location entity in the active world",
        )

    creator_user = db.exec(select(User).where(User.role == "creator")).first()
    if creator_user is None:
        raise HTTPException(status_code=400, detail="No creator user found.")

    try:
        entity = Entity(
            world_id=world_id,
            type="character",
            name=name,
            description=(body.description or None),
        )
        db.add(entity)
        db.flush()
        character = Character(
            id=entity.id,
            world_id=world_id,
            character_type="player",
            user_id=creator_user.id,
            current_location_id=body.current_location_id,
            appearance=(body.appearance or None),
            backstory=(body.backstory or None),
        )
        db.add(character)
        for domain in BASE_SKILL_DOMAINS:
            db.add(Skill(character_id=entity.id, domain=domain, tier=0))
        # B1 (schema v1.63): flat tier-0 seed for every custom skill of the
        # PC's world — never proposed by a model, set here after the draft
        # is accepted.
        custom_defs = db.exec(
            select(SkillDefinition).where(SkillDefinition.world_id == world_id)
        ).all()
        for definition in custom_defs:
            db.add(Skill(
                character_id=entity.id,
                domain=definition.base_domain,
                tier=0,
                skill_definition_id=definition.id,
            ))
        for item in (body.knowledge or []):
            level = item.level if item.level in KNOWLEDGE_LEVELS else "rumor"
            write_knowledge(
                db,
                entity_id=entity.id,
                subject=item.subject,
                level=level,
                content=item.content,
                source="pc_creation",
                is_incorrect=False,
                is_secret=False,
                share_threshold=50,
                session_id=None,
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        return {
            "ok": False,
            "error": "A player character already exists for this user in this world.",
        }
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}

    db.refresh(entity)
    return {"ok": True, "id": entity.id, "name": entity.name}


# ── Play loop — provisional creator entry point ───────────────────────────────
# These three endpoints (npcs, conversations/start, say, end) form the play
# loop introduced for browser-based conversations.  The NPC selector and
# /start endpoint are PROVISIONAL creator-side scaffolding; they will be
# replaced by a full player view.  The persistence and streaming logic (say,
# end) is the durable piece.

@router.get("/api/npcs")
def list_npcs(db: Session = Depends(get_session)) -> list:
    """Return every NPC character in the world (id, display name, faction)."""
    chars = db.exec(
        select(Character).where(Character.character_type == "npc")
    ).all()
    result = []
    for char in chars:
        entity = db.get(Entity, char.id)
        if entity is None:
            continue
        faction_name: Optional[str] = None
        membership = db.exec(
            select(FactionMembership).where(
                FactionMembership.entity_id == char.id,
                FactionMembership.left_at.is_(None),
                FactionMembership.is_primary == True,  # noqa: E712
            )
        ).first()
        if membership:
            fac = db.get(Entity, membership.faction_id)
            if fac:
                faction_name = fac.name
        result.append({"id": char.id, "name": entity.name, "faction": faction_name})
    return result
