"""G1 check for TICKET-0114 -- the event journal's vocabulary: a world's event types, their roles, who learns them, its sortes.

BRIEF-0114-A's rules. The journal's writer, readers and forms have their
own checks (`event_writes.py`, `event_contexts.py`, `event_conditions.py`),
so each stays inside the corpus's per-check time budget.

EA1 -- storage (import). The seven new tables carry exactly their
   contract's columns, CHECK names and index names; no column of theirs is
   JSON; `EVENT_DOMAINS` is `tick_normalize._EVENT_TYPES` and the domain
   CHECK's values, `EVENT_SCOPE_KINDS` and `EVENT_VOCAB_STATUSES` their
   CHECKs', `EVENT_SCOPE_LEVELS` is `writes.knowledge.KNOWLEDGE_LEVEL_LADDER`;
   `event` has `type_id` and `quantity`, `agenda_step` has `started_at`,
   `condition_node` has `since` with `CONDITION_WINDOWS` its CHECK's values;
   `CONDITION_ROLES` ends with `failure` and is the role CHECK's; every
   `DOMAIN_LABELS_FR` key is a domain; the code's schema version is v2.24
   or later.
EA2 -- the type writer (fixture). `write_event_type` writes « Tuer » (two
   roles, the second accepting a sorte; a `location` and a `rencontre`
   scope) and `type_view` reads back its roles in order with their types,
   its scopes with their role, its flags. Refused, each with no row
   written: an empty name, another type's name (« tuer », « TUER »), an
   unknown domain, no role, two roles of one name, a role accepting nothing,
   an unknown entity type, an unknown scope, a `rencontre` scope on no role
   or a sorte-only role, a `faction` scope on a role accepting no faction, a
   `world` scope naming a role, a level `unaware`, an id on a new type's
   role.
EA3 -- in use (fixture). Once a participant fills a role: dropping that
   role, dropping the entity type it holds, or a sorte role's sorte, is
   refused; an unused role dropped is retired, its row kept, and named
   again comes back; a type whose event has a quantity cannot stop
   counting; a type is retired and restored.
EA4 -- sortes (fixture). `write_sorte` writes « Loup », refuses « loup »
   and an empty name; `near_sortes` finds « Loup » for « loups »,
   `near_event_types` finds « Tuer » for « tuers », and nothing for
   « Pacte »; `world_sortes` / `world_event_types` leave a retired one out
   unless asked.
EA5 -- the type made from a domain (fixture). `ensure_domain_type` makes
   « Social » with one role « Impliqué » accepting every entity type of
   the world (an active runtime type included, a retired one not); a
   second call, and a call for « mystery », find « Social » again and make
   « Mystère »; an unknown domain is `other`.
EA6 -- migration `scripts/migrate_v2_24_event_journal.py`, on a v2.23
   database (the four changed tables in their v2.23 DDL, frozen below)
   holding a `public` event with two `event_entity` rows, a `secret` one
   with none, a condition and two nodes: at v2.22 it refuses and changes
   nothing; at v2.23 it types each event by its category (« Social »,
   « Autre »), moves the links into `event_participant` in the role
   « Impliqué », gives each event one `evenement` fact -- a `world` default
   at `knows` for the public one, none for the secret -- keeps the
   condition and nodes, adds the columns and tables, and sets
   `schema_meta` to v2.24; a second run writes nothing.
EA7 -- the reader writes nothing (static, AST). `event_vocab.py` calls no
   `add`, `commit`, `delete`, `execute` or `flush`.
EB1 -- the routes (BRIEF-0114-B, route functions on the EA world made
   active). `event_vocabulary` lists the types (the retired included, each
   with `in_condition` and its count of events), the sortes, the world's
   entity types, the seven domains, the four scope kinds and five levels
   (never `unaware`). A new type named near another (« Tuers » beside
   « Tuer ») answers `saved: false` with the near one and writes nothing;
   `confirm_near` writes it; saving a type under its own name asks nothing;
   a refused type answers 422 and writes nothing; a type is retired then
   restored. A sorte near another (« Loups ») asks, `confirm_near` writes
   it, and an unknown sorte answers 404.
EB2 -- the Création surfaces (static). `tabs.js` has no `etats` entry; its
   `vocabulaire` entry mounts the `vocabulary` island in
   `creation-vocabulaire` and routes « + Nouveau » through
   `triggerPrimaryAction('vocabulary')`; `registry.js` declares
   `vocabulary` as origin 'new', created by TICKET-0114, and no `states`
   island; `mount.js` maps `vocabulary` to `Vocabulary`; `creation.css`
   sizes `#creation-vocabulaire`; `Vocabulary.svelte` exports
   `primaryAction` and renders `<States`, `<EventTypes` and `<Sortes`;
   `EventTypes.svelte` and `Sortes.svelte` export `primaryAction`;
   `EventTypes.svelte` renders `<EventTypeForm`, which offers the three
   flags, a role's entity types and its sorte, and the scopes;
   `eventVocab.svelte.js` exports `typeDraft` and `typeBody` and sends
   `confirm_near`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION_V2_24 = ROOT / "scripts" / "migrate_v2_24_event_journal.py"

FAILURES: list[str] = []

TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "event_type": (
        ("id", "world_id", "name", "domain", "counts_quantity", "in_chronicle", "participants_secret", "status",
         "created_at", "updated_at"),
        ("ck_event_type_domain", "ck_event_type_status"),
        ("idx_event_type_name",),
    ),
    "event_type_role": (
        ("id", "world_id", "type_id", "name", "position", "accepts_sorte", "status"),
        ("ck_event_type_role_status",),
        ("idx_event_type_role_name",),
    ),
    "event_type_role_type": (
        ("id", "world_id", "role_id", "entity_type"),
        (),
        ("idx_event_type_role_type_unique",),
    ),
    "event_type_scope": (
        ("id", "world_id", "type_id", "scope_kind", "role_id", "level"),
        ("ck_event_type_scope_kind", "ck_event_type_scope_role", "ck_event_type_scope_level"),
        ("idx_event_type_scope_type",),
    ),
    "event_sorte": (
        ("id", "world_id", "name", "status", "created_at"),
        ("ck_event_sorte_status",),
        ("idx_event_sorte_name",),
    ),
    "event_participant": (
        ("id", "world_id", "event_id", "role_id", "entity_id", "sorte_id", "position"),
        ("ck_event_participant_one",),
        ("idx_event_participant_event", "idx_event_participant_entity", "idx_event_participant_unique_entity",
         "idx_event_participant_unique_sorte"),
    ),
    "condition_node_filter": (
        ("id", "world_id", "node_id", "role_id", "entity_id", "sorte_id", "position"),
        ("ck_condition_node_filter_one",),
        ("idx_condition_node_filter_node",),
    ),
}

# The four tables v2.24 changes, as v2.23 declared them (frozen: EA6 builds
# the database the migration was written for).
V2_23_DDL: tuple[str, ...] = (
    "CREATE TABLE event (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, session_id VARCHAR, batch_id VARCHAR, "
    "title VARCHAR NOT NULL, description VARCHAR, type VARCHAR, knowledge_status VARCHAR DEFAULT 'secret' NOT NULL, "
    "location_id VARCHAR, has_magic_impact BOOLEAN DEFAULT 0 NOT NULL, consequences JSON, occurred_at DATETIME, "
    "recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(session_id) REFERENCES session (id), "
    "FOREIGN KEY(batch_id) REFERENCES batch (id), FOREIGN KEY(location_id) REFERENCES entity (id))",
    "CREATE INDEX idx_event_world ON event (world_id)",
    "CREATE TABLE agenda_step (id VARCHAR NOT NULL, agenda_id VARCHAR NOT NULL, step_order INTEGER NOT NULL, "
    "objective VARCHAR NOT NULL, status VARCHAR DEFAULT 'pending' NOT NULL, outcome VARCHAR, visibility_trace VARCHAR, "
    "cost INTEGER, domain VARCHAR, created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
    "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, change_history JSON DEFAULT '[]' NOT NULL, "
    "PRIMARY KEY (id), CONSTRAINT ck_agenda_step_status CHECK (status IN ('pending','active','completed','failed')), "
    "CONSTRAINT ck_agenda_step_cost CHECK (cost IS NULL OR cost BETWEEN 1 AND 4), "
    "FOREIGN KEY(agenda_id) REFERENCES agenda (id))",
    "CREATE INDEX idx_agenda_step_agenda ON agenda_step (agenda_id, step_order)",
    "CREATE UNIQUE INDEX idx_agenda_step_one_active ON agenda_step (agenda_id) WHERE status = 'active'",
    "CREATE TABLE condition (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, role VARCHAR NOT NULL, "
    "quest_offer_id VARCHAR, quest_offer_step_id VARCHAR, agenda_step_id VARCHAR, "
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
    "CONSTRAINT ck_condition_role CHECK (role IN ('eligibility','prerequisite','completion')), "
    "CONSTRAINT ck_condition_owner CHECK ((quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) "
    "+ (agenda_step_id IS NOT NULL) = 1), "
    "CONSTRAINT ck_condition_owner_role CHECK ((quest_offer_id IS NOT NULL) = (role = 'eligibility')), "
    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(quest_offer_id) REFERENCES quest_offer (id), "
    "FOREIGN KEY(quest_offer_step_id) REFERENCES quest_offer_step (id), "
    "FOREIGN KEY(agenda_step_id) REFERENCES agenda_step (id))",
    "CREATE UNIQUE INDEX idx_condition_agenda_step ON condition (agenda_step_id, role)",
    "CREATE UNIQUE INDEX idx_condition_offer_step ON condition (quest_offer_step_id, role)",
    "CREATE UNIQUE INDEX idx_condition_offer ON condition (quest_offer_id, role)",
    "CREATE TABLE condition_node (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, condition_id VARCHAR NOT NULL, "
    "parent_id VARCHAR, position INTEGER DEFAULT 0 NOT NULL, op VARCHAR NOT NULL, n INTEGER, form VARCHAR, "
    "subject_role VARCHAR, subject_entity_id VARCHAR, target_entity_id VARCHAR, target_key VARCHAR, "
    "threshold INTEGER, value VARCHAR, PRIMARY KEY (id), "
    "CONSTRAINT ck_condition_node_op CHECK (op IN ('all','any','not','at_least','leaf')), "
    "CONSTRAINT ck_condition_node_leaf CHECK ((op = 'leaf') = (form IS NOT NULL)), "
    "CONSTRAINT ck_condition_node_connector CHECK (op = 'leaf' OR (subject_role IS NULL AND subject_entity_id "
    "IS NULL AND target_entity_id IS NULL AND target_key IS NULL AND threshold IS NULL AND value IS NULL)), "
    "CONSTRAINT ck_condition_node_subject CHECK (op <> 'leaf' OR ((subject_role IS NULL) <> "
    "(subject_entity_id IS NULL))), "
    "CONSTRAINT ck_condition_node_role CHECK (subject_role IS NULL OR subject_role IN ('doer','giver','contact')), "
    "CONSTRAINT ck_condition_node_n CHECK ((op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)), "
    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(condition_id) REFERENCES condition (id), "
    "FOREIGN KEY(parent_id) REFERENCES condition_node (id), FOREIGN KEY(subject_entity_id) REFERENCES entity (id), "
    "FOREIGN KEY(target_entity_id) REFERENCES entity (id))",
    "CREATE INDEX idx_condition_node_condition ON condition_node (condition_id, parent_id, position)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


# --- EA1 -------------------------------------------------------------------------

def _quoted(sql: str) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']+)'", sql))


def _ck(table: str, name: str) -> str:
    from sqlalchemy import CheckConstraint
    from sqlmodel import SQLModel

    return next(str(c.sqltext) for c in SQLModel.metadata.tables[table].constraints
                if isinstance(c, CheckConstraint) and c.name == name)


def _ea1_tables() -> None:
    from sqlalchemy import JSON, CheckConstraint
    from sqlmodel import SQLModel

    seen = 0
    for name, (columns, checks, indexes) in TABLES.items():
        table = SQLModel.metadata.tables.get(name)
        if table is None:
            fail(f"EA1: table {name} is not declared")
            continue
        seen += 1
        if tuple(table.c.keys()) != columns:
            fail(f"EA1: {name} columns are {tuple(table.c.keys())}")
        found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
        if found != tuple(sorted(checks)):
            fail(f"EA1: {name} CHECKs are {found}")
        if tuple(sorted(i.name for i in table.indexes)) != tuple(sorted(indexes)):
            fail(f"EA1: {name} indexes are {sorted(i.name for i in table.indexes)}")
        for column in table.c:
            if isinstance(column.type, JSON):
                fail(f"EA1: {name}.{column.name} is JSON")
    if seen != len(TABLES):
        fail(f"EA1: {seen} of {len(TABLES)} tables declared")


def check_ea1() -> None:
    from sqlmodel import SQLModel

    from world_engine import models
    from world_engine.event_vocab import DOMAIN_LABELS_FR
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.tick_normalize import _EVENT_TYPES
    from world_engine.writes.knowledge import KNOWLEDGE_LEVEL_LADDER

    _ea1_tables()
    meta = SQLModel.metadata.tables
    pairs = (
        (models.EVENT_DOMAINS, _ck("event_type", "ck_event_type_domain")),
        (models.EVENT_VOCAB_STATUSES, _ck("event_type", "ck_event_type_status")),
        (models.EVENT_VOCAB_STATUSES, _ck("event_type_role", "ck_event_type_role_status")),
        (models.EVENT_VOCAB_STATUSES, _ck("event_sorte", "ck_event_sorte_status")),
        (models.EVENT_SCOPE_KINDS, _ck("event_type_scope", "ck_event_type_scope_kind")),
        (models.EVENT_SCOPE_LEVELS, _ck("event_type_scope", "ck_event_type_scope_level")),
        (models.CONDITION_ROLES, _ck("condition", "ck_condition_role")),
        (models.CONDITION_WINDOWS, _ck("condition_node", "ck_condition_node_since")),
    )
    for values, sql in pairs:
        if tuple(values) != _quoted(sql):
            fail(f"EA1: {values} is not the CHECK's {_quoted(sql)}")
    if set(models.EVENT_DOMAINS) != set(_EVENT_TYPES):
        fail(f"EA1: EVENT_DOMAINS {models.EVENT_DOMAINS} is not tick_normalize._EVENT_TYPES {sorted(_EVENT_TYPES)}")
    if tuple(models.EVENT_SCOPE_LEVELS) != tuple(KNOWLEDGE_LEVEL_LADDER):
        fail("EA1: EVENT_SCOPE_LEVELS is not KNOWLEDGE_LEVEL_LADDER")
    if models.CONDITION_ROLES[-1] != "failure":
        fail(f"EA1: CONDITION_ROLES is {models.CONDITION_ROLES}")
    if set(DOMAIN_LABELS_FR) != set(models.EVENT_DOMAINS):
        fail(f"EA1: DOMAIN_LABELS_FR names {sorted(DOMAIN_LABELS_FR)}")
    for table, column in (("event", "type_id"), ("event", "quantity"), ("agenda_step", "started_at"),
                          ("condition_node", "since")):
        if column not in meta[table].c:
            fail(f"EA1: {table}.{column} is not declared")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 24):
        fail(f"EA1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- fixture -----------------------------------------------------------------------

def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, EntityType, Faction, Location, World

    with Session(engine) as db:
        world = World(name="Journal", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
                                ("foret", "location", "Forêt"), ("guilde", "faction", "Guilde")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
            elif kind == "location":
                db.add(Location(id=entity.id))
            else:
                db.add(Faction(id=entity.id))
        for slug, status in (("navire", "active"), ("epave", "retired")):
            db.add(EntityType(world_id=world.id, name=slug, slug=slug, physical_table=f"ext_{slug}",
                              status=status))
        db.commit()
    return ids


def _counts(db) -> tuple[int, ...]:
    from sqlmodel import func, select

    from world_engine import models

    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
        models.EventType, models.EventTypeRole, models.EventTypeRoleType, models.EventTypeScope,
        models.EventSorte))


def _refused(db, label: str, rule: str, call) -> None:
    before = _counts(db)
    try:
        call()
    except ValueError:
        db.rollback()
        if _counts(db) != before:
            fail(f"{rule}: {label} was refused after writing a row")
        return
    db.rollback()
    fail(f"{rule}: {label} was accepted")


def _role(name, types=("character",), sorte=False, role_id=None):
    from world_engine.writes.event_types import RoleSpec

    return RoleSpec(name=name, entity_types=tuple(types), accepts_sorte=sorte, id=role_id)


def _tuer(**fields):
    from world_engine.writes.event_types import EventTypeSpec, ScopeSpec

    base = dict(name="Tuer", domain="military", counts_quantity=True,
                roles=(_role("tueur"), _role("victime", ("character",), sorte=True)),
                scopes=(ScopeSpec("location", level="rumor"), ScopeSpec("rencontre", role="victime")))
    base.update(fields)
    return EventTypeSpec(**base)


def check_ea2(engine, ids: dict) -> str:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.writes.event_types import EventTypeSpec, ScopeSpec, write_event_type

    world = ids["world"]
    with Session(engine) as db:
        tuer = write_event_type(db, world_id=world, spec=_tuer()).id
        db.commit()
        view = type_view(db, tuer)
        roles = [(r.name, r.position, r.entity_types, r.accepts_sorte, r.status) for r in view.roles]
        if roles != [("tueur", 0, ("character",), False, "active"), ("victime", 1, ("character",), True, "active")]:
            fail(f"EA2: the roles read back as {roles}")
        scopes = sorted((s.kind, view.role(s.role_id).name if s.role_id else None, s.level) for s in view.scopes)
        if scopes != [("location", None, "rumor"), ("rencontre", "victime", "knows")]:
            fail(f"EA2: the scopes read back as {scopes}")
        if (view.domain, view.counts_quantity, view.in_chronicle, view.participants_secret) != \
                ("military", True, True, False):
            fail(f"EA2: the flags read back as {view}")
        cases = {
            "an empty name": _tuer(name="  "),
            "another type's name (tuer)": _tuer(name="tuer"),
            "another type's name (TUER)": _tuer(name="TUER"),
            "an unknown domain": _tuer(name="A", domain="weather"),
            "no role": _tuer(name="A", roles=(), scopes=()),
            "two roles of one name": _tuer(name="A", roles=(_role("x"), _role("X")), scopes=()),
            "a role accepting nothing": _tuer(name="A", roles=(_role("x", ()),), scopes=()),
            "an unknown entity type": _tuer(name="A", roles=(_role("x", ("dragon",)),), scopes=()),
            "an unknown scope": _tuer(name="A", scopes=(ScopeSpec("planet"),)),
            "a rencontre scope on no role": _tuer(name="A", scopes=(ScopeSpec("rencontre"),)),
            "a rencontre scope on a sorte-only role": _tuer(
                name="A", roles=(_role("x", (), sorte=True),), scopes=(ScopeSpec("rencontre", role="x"),)),
            "a faction scope on a role accepting no faction": _tuer(
                name="A", scopes=(ScopeSpec("faction", role="tueur"),)),
            "a world scope naming a role": _tuer(name="A", scopes=(ScopeSpec("world", role="tueur"),)),
            "a level unaware": _tuer(name="A", scopes=(ScopeSpec("world", level="unaware"),)),
            "an id on a new type's role": _tuer(name="A", roles=(_role("x", role_id="r1"),), scopes=()),
        }
        for label, spec in cases.items():
            _refused(db, label, "EA2", lambda spec=spec: write_event_type(db, world_id=world, spec=spec))
        if not isinstance(EventTypeSpec(name="x"), EventTypeSpec):
            fail("EA2: EventTypeSpec does not build")
    return tuer


def check_ea3(engine, ids: dict, tuer: str) -> None:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Event, EventParticipant
    from world_engine.writes.event_types import set_event_type_status, write_event_type, write_sorte

    world = ids["world"]
    with Session(engine) as db:
        view = type_view(db, tuer)
        tueur, victime = view.roles[0].id, view.roles[1].id
        loup = write_sorte(db, world_id=world, name="Bête").id
        event = Event(world_id=world, title="Brakk tue trois bêtes", type_id=tuer, quantity=3)
        db.add(event)
        db.flush()
        db.add(EventParticipant(world_id=world, event_id=event.id, role_id=tueur, entity_id=ids["brakk"]))
        db.add(EventParticipant(world_id=world, event_id=event.id, role_id=victime, sorte_id=loup))
        db.commit()
        kept = (_role("tueur", role_id=tueur), _role("victime", ("character",), True, role_id=victime))
        for label, spec in {
            "dropping a role an event holds": _tuer(roles=(kept[1],), scopes=()),
            "dropping the entity type a participant holds": _tuer(
                roles=(_role("tueur", ("location",), role_id=tueur), kept[1]), scopes=()),
            "dropping a sorte role's sorte": _tuer(
                roles=(kept[0], _role("victime", ("character",), False, role_id=victime)), scopes=()),
            "a type with a quantity that stops counting": _tuer(roles=kept, scopes=(), counts_quantity=False),
        }.items():
            _refused(db, label, "EA3", lambda spec=spec: write_event_type(db, world_id=world, spec=spec,
                                                                          type_id=tuer))
        write_event_type(db, world_id=world, spec=_tuer(roles=kept + (_role("témoin"),), scopes=()), type_id=tuer)
        write_event_type(db, world_id=world, spec=_tuer(roles=kept, scopes=()), type_id=tuer)
        db.commit()
        temoin = [r for r in type_view(db, tuer).roles if r.name == "témoin"]
        if len(temoin) != 1 or temoin[0].status != "retired":
            fail(f"EA3: an unused role dropped reads {temoin}, not one retired row")
        write_event_type(db, world_id=world, spec=_tuer(roles=kept + (_role("Témoin"),), scopes=()), type_id=tuer)
        db.commit()
        back = [r for r in type_view(db, tuer).roles if r.name == "Témoin"]
        if len(back) != 1 or back[0].status != "active" or back[0].id != temoin[0].id:
            fail(f"EA3: a retired role named again reads {back}")
        retired = set_event_type_status(db, world_id=world, type_id=tuer, status="retired").status
        restored = set_event_type_status(db, world_id=world, type_id=tuer, status="active").status
        db.commit()
        if (retired, restored) != ("retired", "active"):
            fail(f"EA3: a type with no condition was {retired} then {restored}")


def check_ea4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_vocab import near_event_types, near_sortes, world_event_types, world_sortes
    from world_engine.writes.event_types import set_sorte_status, write_sorte

    world = ids["world"]
    with Session(engine) as db:
        loup = write_sorte(db, world_id=world, name="Loup").id
        db.commit()
        for label, name in (("« loup »", "loup"), ("an empty name", " ")):
            _refused(db, label, "EA4", lambda name=name: write_sorte(db, world_id=world, name=name))
        if [n.name for n in near_sortes(db, world, "loups")][:1] != ["Loup"]:
            fail(f"EA4: near_sortes finds {near_sortes(db, world, 'loups')} for « loups »")
        if [n.name for n in near_event_types(db, world, "tuers")][:1] != ["Tuer"]:
            fail(f"EA4: near_event_types finds {near_event_types(db, world, 'tuers')} for « tuers »")
        if near_event_types(db, world, "Pacte"):
            fail(f"EA4: near_event_types finds {near_event_types(db, world, 'Pacte')} for « Pacte »")
        set_sorte_status(db, world_id=world, sorte_id=loup, status="retired")
        db.commit()
        if any(s.id == loup for s in world_sortes(db, world)) or \
                not any(s.id == loup for s in world_sortes(db, world, include_retired=True)):
            fail("EA4: world_sortes does not leave the retired « Loup » out unless asked")
        if not world_event_types(db, world):
            fail("EA4: world_event_types lists nothing")


def check_ea5(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_vocab import DOMAIN_ROLE_FR, type_view
    from world_engine.writes.event_types import ensure_domain_type

    world = ids["world"]
    with Session(engine) as db:
        social = ensure_domain_type(db, world_id=world, domain="social")
        again = ensure_domain_type(db, world_id=world, domain="social")
        mystere = ensure_domain_type(db, world_id=world, domain="mystery")
        other = ensure_domain_type(db, world_id=world, domain="weather")
        db.commit()
        view = type_view(db, social.id)
        if social.id != again.id or view.name != "Social" or view.domain != "social":
            fail(f"EA5: ensure_domain_type gave {view} then {again.id}")
        if [(r.name, r.entity_types) for r in view.roles] != [
                (DOMAIN_ROLE_FR, ("character", "faction", "item", "location", "navire"))]:
            fail(f"EA5: « Social »'s roles are {[(r.name, r.entity_types) for r in view.roles]}")
        if (mystere.name, other.name, other.domain) != ("Mystère", "Autre", "other"):
            fail(f"EA5: mystery made {mystere.name}, an unknown domain {other.name}/{other.domain}")


# --- EA6 -------------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION_V2_24)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _v2_23_db() -> str:
    """A database the migration was written for: every table of the code
    but the seven new ones and the four it changes, those in v2.23 DDL."""
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
    eng = create_engine(f"sqlite:///{db_path}")
    skipped = set(TABLES) | {"event", "agenda_step", "condition", "condition_node", "event_entity"}
    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n not in skipped])
    eng.dispose()
    with sqlite3.connect(db_path) as conn:
        for statement in V2_23_DDL:
            conn.execute(statement)
        conn.execute("CREATE TABLE event_entity (id VARCHAR NOT NULL, event_id VARCHAR NOT NULL, entity_id VARCHAR "
                     "NOT NULL, PRIMARY KEY (id), FOREIGN KEY(event_id) REFERENCES event (id), "
                     "FOREIGN KEY(entity_id) REFERENCES entity (id))")
        conn.executescript("""
            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.22', '2026-10-01');
            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
              VALUES ('a', 'w', 'character', 'A', 'active', '2026-10-01', '2026-10-01'),
                     ('b', 'w', 'location', 'B', 'active', '2026-10-01', '2026-10-01');
            INSERT INTO event (id, world_id, title, description, type, knowledge_status, recorded_at)
              VALUES ('ev1', 'w', 'La fête', 'On danse.', 'social', 'public', '2026-10-01'),
                     ('ev2', 'w', 'Le pacte', NULL, 'weather', 'secret', '2026-10-02');
            INSERT INTO event_entity (id, event_id, entity_id) VALUES ('l1', 'ev1', 'a'), ('l2', 'ev1', 'b');
            INSERT INTO agenda (id, world_id, owner_entity_id, title, status, created_at, updated_at)
              VALUES ('ag', 'w', 'a', 'T', 'active', '2026-10-01', '2026-10-01');
            INSERT INTO agenda_step (id, agenda_id, step_order, objective) VALUES ('s1', 'ag', 1, 'o');
            INSERT INTO condition (id, world_id, role, agenda_step_id) VALUES ('c1', 'w', 'prerequisite', 's1');
            INSERT INTO condition_node (id, world_id, condition_id, position, op) VALUES ('n1', 'w', 'c1', 0, 'all');
            INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op, form, subject_role,
              target_key) VALUES ('n2', 'w', 'c1', 'n1', 0, 'leaf', 'knowledge', 'doer', 'k');
        """)
    return db_path


def _snapshot(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        def rows(sql):
            try:
                return sorted(conn.execute(sql).fetchall())
            except sqlite3.OperationalError:
                return None
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "types": rows("SELECT e.title, t.name FROM event e JOIN event_type t ON t.id = e.type_id"),
            "participants": rows("SELECT p.event_id, p.entity_id, r.name FROM event_participant p "
                                 "JOIN event_type_role r ON r.id = p.role_id"),
            "facts": rows("SELECT f.event_id, f.facet, f.content, (SELECT group_concat(scope_type || ':' || level) "
                          "FROM fact_default d WHERE d.fact_id = f.id) FROM fact f WHERE f.event_id IS NOT NULL"),
            "nodes": rows("SELECT id, form FROM condition_node"),
            "conditions": rows("SELECT id, role FROM condition"),
            "started": rows("SELECT started_at FROM agenda_step"),
        }


def check_ea6() -> None:
    db_path = _v2_23_db()
    before = _snapshot(db_path)
    refused = _run_migration(db_path)
    if refused.returncode == 0 or _snapshot(db_path) != before:
        fail(f"EA6: v2.22 was not refused untouched (exit {refused.returncode})")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.23' WHERE id = 1")
    result = _run_migration(db_path)
    after = _snapshot(db_path)
    want = {
        "version": "v2.24",
        "types": [("La fête", "Social"), ("Le pacte", "Autre")],
        "participants": [("ev1", "a", "Impliqué"), ("ev1", "b", "Impliqué")],
        "facts": [("ev1", "evenement", "La fête — On danse.", "world:knows"), ("ev2", "evenement", "Le pacte", None)],
        "nodes": [("n1", None), ("n2", "knowledge")],
        "conditions": [("c1", "prerequisite")],
        "started": [(None,)],
    }
    if result.returncode != 0 or after != want:
        fail(f"EA6: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
        fail(f"EA6: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


# --- EA7 -------------------------------------------------------------------------

def check_ea7() -> None:
    path = SRC / "event_vocab.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    if not calls:
        fail("EA7: event_vocab.py makes no attribute call at all")
    for call in calls:
        if call.func.attr in ("add", "commit", "delete", "execute", "flush"):
            fail(f"EA7: event_vocab.py calls .{call.func.attr} on line {call.lineno}")


# --- EB1 -------------------------------------------------------------------------

def check_eb1(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session, func, select

    from world_engine.cockpit.routes import event_types as routes
    from world_engine.models import EventSorte, EventType, World

    def count(db, model) -> int:
        return db.exec(select(func.count()).select_from(model)).one()

    with Session(engine) as db:
        db.get(World, ids["world"]).is_active = True
        db.commit()
        listed = routes.event_vocabulary(db)
        if not listed["types"] or not all("in_condition" in t and "events" in t for t in listed["types"]):
            fail(f"EB1: event_vocabulary lists types {listed['types'][:1]}")
        shape = (len(listed["domains"]), len(listed["scope_kinds"]), [l["value"] for l in listed["levels"]])
        if shape != (7, 4, ["rumor", "suspicious", "partial", "knows", "fully_understands"]) \
                or not listed["entity_types"]:
            fail(f"EB1: event_vocabulary's lists are {shape}")
        before = count(db, EventType)
        body = routes.EventTypeBody(name="Tuers", roles=[routes.RoleBody(name="x", entity_types=["character"])])
        asked = routes.create_event_type(body, db)
        if asked.get("saved") is not False or "Tuer" not in [n["name"] for n in asked.get("near", [])] \
                or count(db, EventType) != before:
            fail(f"EB1: a near type name answered {asked}")
        body.confirm_near = True
        made = routes.create_event_type(body, db)
        if made.get("saved") is not True or count(db, EventType) != before + 1:
            fail(f"EB1: confirm_near answered {made}")
        type_id = made["type"]["id"]
        roles = [routes.RoleBody(name="x", entity_types=["character"], id=made["type"]["roles"][0]["id"])]
        same = routes.save_event_type(type_id, routes.EventTypeBody(name="Tuers", roles=roles), db)
        if same.get("saved") is not True:
            fail(f"EB1: saving a type under its own name answered {same}")
        try:
            routes.create_event_type(routes.EventTypeBody(name="Vide", confirm_near=True), db)
            fail("EB1: a type with no role was accepted")
        except HTTPException as exc:
            if exc.status_code != 422 or count(db, EventType) != before + 1:
                fail(f"EB1: a type with no role answered {exc.status_code}")
        retired = routes.event_type_status(type_id, routes.StatusBody(status="retired"), db)["status"]
        restored = routes.event_type_status(type_id, routes.StatusBody(status="active"), db)["status"]
        if (retired, restored) != ("retired", "active"):
            fail(f"EB1: a type was {retired} then {restored}")
        sortes = count(db, EventSorte)
        asked = routes.create_sorte(routes.SorteBody(name="Loups"), db)
        if asked.get("saved") is not False or count(db, EventSorte) != sortes:
            fail(f"EB1: a near sorte answered {asked}")
        if routes.create_sorte(routes.SorteBody(name="Loups", confirm_near=True), db).get("saved") is not True:
            fail("EB1: confirm_near did not write the sorte")
        try:
            routes.save_sorte("nope", routes.SorteBody(name="x"), db)
            fail("EB1: an unknown sorte was saved")
        except HTTPException as exc:
            if exc.status_code != 404:
                fail(f"EB1: an unknown sorte answered {exc.status_code}")


# --- EB2 -------------------------------------------------------------------------

def check_eb2() -> None:
    front = ROOT / "frontend" / "src" / "creation"

    def read(path: pathlib.Path) -> str:
        if not path.exists():
            fail(f"EB2: {path.name} is missing")
            return ""
        return path.read_text(encoding="utf-8")

    tabs = read(front / "tabs.js")
    if re.search(r"\n  etats: \{", tabs):
        fail("EB2: tabs.js still has an etats entry")
    entry = re.search(r"\n  vocabulaire: \{(.*?)\n  \},", tabs, re.S)
    body = entry.group(1) if entry else ""
    for needle in ("{ key: 'vocabulary', containerId: 'creation-vocabulaire' }",
                   "triggerPrimaryAction('vocabulary')", "label: 'Vocabulaire du monde'"):
        if needle not in body:
            fail(f"EB2: tabs.js's vocabulaire entry lacks {needle}")
    registry = read(front / "registry.js")
    island = re.search(r"\n  vocabulary: Object\.freeze\(\{(.*?)\}\),", registry, re.S)
    if not island or "origin: 'new'" not in island.group(1) or "createdBy: 'TICKET-0114'" not in island.group(1):
        fail("EB2: registry.js does not declare the vocabulary island as new, TICKET-0114")
    if re.search(r"\n  states: Object\.freeze", registry):
        fail("EB2: registry.js still declares a states island")
    if "vocabulary: Vocabulary" not in read(front / "mount.js"):
        fail("EB2: mount.js does not map vocabulary to Vocabulary")
    if "#creation-vocabulaire" not in read(ROOT / "frontend" / "public" / "creation.css"):
        fail("EB2: creation.css does not size #creation-vocabulaire")
    needles = {
        "Vocabulary.svelte": ("export function primaryAction", "<States", "<EventTypes", "<Sortes"),
        "EventTypes.svelte": ("export function primaryAction", "<EventTypeForm"),
        "Sortes.svelte": ("export function primaryAction",),
        "EventTypeForm.svelte": ("draft.counts_quantity", "draft.in_chronicle", "draft.participants_secret",
                                 "role.entity_types", "role.accepts_sorte", "draft.scopes"),
        "eventVocab.svelte.js": ("export function typeDraft", "export function typeBody", "confirm_near"),
    }
    for name, wanted in needles.items():
        text = read(front / name)
        for needle in wanted:
            if needle not in text:
                fail(f"EB2: {name} lacks {needle}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    state: dict = {}

    def ea2() -> None:
        state["tuer"] = check_ea2(engine, ids)

    rules = (
        ("EA1", check_ea1), ("EA2", ea2), ("EA3", lambda: check_ea3(engine, ids, state["tuer"])),
        ("EA4", lambda: check_ea4(engine, ids)), ("EA5", lambda: check_ea5(engine, ids)),
        ("EA6", check_ea6), ("EA7", check_ea7), ("EB1", lambda: check_eb1(engine, ids)), ("EB2", check_eb2),
    )
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_journal -- v2.24 keeps a world's event types with their roles, the entity types each "
          "accepts, who learns them, and its sortes; nothing in use is taken away; every earlier event is "
          "typed by its category, its links become participants and it gets its fact; Création keeps the "
          "vocabulary in one tab and asks before a near name")
    return 0


if __name__ == "__main__":
    sys.exit(main())
