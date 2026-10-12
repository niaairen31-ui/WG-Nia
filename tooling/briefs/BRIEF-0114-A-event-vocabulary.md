<!-- slug: event-vocabulary -->
# BRIEF 0114-A — "The event journal's vocabulary -- a world's event types, their roles, who learns them, its sortes; every earlier event typed (schema v2.24)"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after `main` at `b16d91e`).

- `src/world_engine/models/config.py:130` -> `CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion")`
- `src/world_engine/models/config.py:157` -> `class ConditionNode(SQLModel, table=True):`
- `src/world_engine/models/canon.py:479` -> `class Event(SQLModel, table=True):`; `:510` -> `class EventEntity(SQLModel, table=True):`
- `src/world_engine/models/pipeline.py:451` -> `class ConditionDraft(SQLModel, table=True):`
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.23"`
- `src/world_engine/tick_normalize.py:67` -> `_EVENT_TYPES = frozenset(`
- No `src/world_engine/models/canon_event.py`, `event_vocab.py`, `writes/event_types.py`, `scripts/migrate_v2_24_event_journal.py`, `tooling/verify/checks/event_journal.py`.

## Facts carried

### R-01 — `event` and `event_entity` [M]
Opened: `src/world_engine/models/canon.py:479` (`Event`: `session_id`,
`batch_id`, `title`, `description`, `type` free text, `knowledge_status`
default `'secret'`, `location_id`, `has_magic_impact`, `consequences`
JSON, `occurred_at`, `recorded_at`; one index `idx_event_world`), `:510`
(`EventEntity`: `event_id`, `entity_id`, unique `idx_event_entity_unique`).
Consequence: A adds `type_id` and `quantity` (nullable at v2.24, so the
migration can fill them); D rebuilds `event` without `type`,
`knowledge_status`, `has_magic_impact`, `consequences`, `occurred_at`,
`type_id` NOT NULL, and drops `event_entity` once every link has its
`event_participant` twin.

### R-02 — production holds four events, none with a fact [M]
Measured by Nia on her database (2026-10-11): four events -- `military`,
`other`, `political` with `knowledge_status = 'secret'`, `social` with
`'public'` --; each carries `consequences` = the JSON `null` (never SQL
NULL), no `has_magic_impact`, no `occurred_at`; zero `fact` rows with an
`event_id`.
Consequence: N1 (the type required) types them by their category, which
the migration makes as « Militaire », « Autre », « Politique »,
« Social », each with one role « Impliqué »; O1: the public one gets a
`world` scope at `knows`, the secret ones none. Nothing in the dropped
columns is lost (L1).

### R-03 — the seven categories [M]
Opened: `src/world_engine/tick_normalize.py:67` (`_EVENT_TYPES`:
`political`, `magical`, `criminal`, `military`, `social`, `mystery`,
`other`), `:445` (an unknown one reads `other`).
Consequence: they become a type's DOMAIN (`EVENT_DOMAINS`, EA1 keeps the
two equal); French labels `DOMAIN_LABELS_FR`.

### R-05 — facts, their defaults and who knows them
Opened: `src/world_engine/models/canon_knowledge.py:87` (`Fact`, `:107`
`event_id`, at most one owner, `idx_fact_event`), `:164` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, `scope_id`
NULL for `world`), `:199` (`Knowledge`); `src/world_engine/facets.py:79`
(facet `evenement`, monde, typed); `src/world_engine/writes/facts.py:75`
(`create_fact`), `:163` (`update_typed_fact_content`, kind `correction`),
`:204` (`create_fact_default`); `src/world_engine/knowledge_resolve.py:253`
(`resolve_known_for_entity`, 0105: own rows, then scopes in contact);
`src/world_engine/writes/knowledge.py:72` (`KNOWLEDGE_LEVEL_LADDER`).
Consequence: an event's fact is facet `evenement`, its text « title —
description »; a type's scopes are written as `fact_default` rows; the
models read through `resolve_known_for_entity` (Q1); a scope's level is
on the ladder, never `unaware`.

### R-07 — conditions: roles, nodes, the draft journal
Opened: `src/world_engine/models/config.py:130` (`CONDITION_ROLES =
("eligibility", "prerequisite", "completion")`), `:157` (`ConditionNode`),
`:71` (`AgendaStep`, no start time); `src/world_engine/models/pipeline.py:451`
(`ConditionDraft`, its own role CHECK);
`src/world_engine/conditions.py:430` (`read_condition`);
`src/world_engine/writes/conditions.py:210` (`write_condition`, the one
writer).
Consequence: A adds `failure` to both role CHECKs (rebuilding
`condition` and `condition_draft`), `condition_node.since` (CHECK on
`CONDITION_WINDOWS`), `condition_node_filter`, `agenda_step.started_at`.

### R-09 — the vocabulary helpers TICKET-0113 left
Opened: `src/world_engine/lore_resolve.py:73` (`normalize_surface`:
case- and accent-blind), `:186` (`near_ratio`);
`src/world_engine/attributes.py:129` (`world_entity_types`), `:274`
(`near_attributes`, the near-name precedent).
Consequence: a type's or sorte's name is compared with
`normalize_surface` in Python (SQLite's `lower()` is not accent-blind),
near names by `near_ratio`.

### R-13 — the canon-write policy and the hard-delete list
Opened: `tooling/verify/canon_write_policy.txt` (header line 4 lists the
canon tables; one line per writer and table);
`tooling/verify/checks/single_canon_write.py` (docstring: the closed list
of hard deletes, INV-12; an unattributable assignment is a failure).
Consequence: A, C, E add their writers and tables; the full-replace
deletes (`fact_default` of an event, a type's scopes, a node's filters)
are named in the docstring.

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contracts

### C-01 — the vocabulary's tables (v2.24)
Produced by: BRIEF-0114-A   Consumed by: B-H
`event_type` (`world_id`, `name` unique per world, `domain` in
`EVENT_DOMAINS`, `counts_quantity`, `in_chronicle`, `participants_secret`,
`status` in `EVENT_VOCAB_STATUSES = ("active", "retired")`);
`event_type_role` (`type_id`, `name` unique per type, `position`,
`accepts_sorte`, `status`); `event_type_role_type` (`role_id`,
`entity_type`); `event_type_scope` (`type_id`, `kind` in
`EVENT_SCOPE_KINDS = ("location", "world", "rencontre", "faction")`,
`role_id` for `rencontre`/`faction`, `level` on the ladder);
`event_sorte` (`world_id`, `name` unique per world, `status`);
`event_participant` (`event_id`, `role_id`, `entity_id` XOR `sorte_id`,
`position`); `condition_node_filter` (`node_id`, `role_id`, `entity_id`
XOR `sorte_id`, `position`). Columns: `event.type_id`, `event.quantity`
(1 or more), `agenda_step.started_at`, `condition_node.since` (in
`CONDITION_WINDOWS = ("always", "quest", "step")`); `CONDITION_ROLES` ends
with `failure`.

### C-02 — `event_vocab` (reads)
Produced by: BRIEF-0114-A   Consumed by: B-H
`DOMAIN_LABELS_FR`, `DOMAIN_ROLE_FR = "Impliqué"`, `EVENT_FORM = "event"`;
`RoleView(id, name, position, entity_types, accepts_sorte, status)`,
`ScopeView(kind, role_id, level)`, `EventTypeView(id, world_id, name,
domain, counts_quantity, in_chronicle, participants_secret, status, roles,
scopes)` with `role(role_id)` and `active_roles()`;
`role_accepts(role, entity_type) -> bool`; `type_view(db, type_id) ->
Optional[EventTypeView]`; `world_event_types(db, world_id,
include_retired=False)`; `world_sortes(db, world_id,
include_retired=False) -> list[EventSorte]`; `near_event_types` /
`near_sortes(db, world_id, name, exclude_id=None) ->
tuple[NearName(id, name, score)]` (retired included, best first). Writes
nothing (EA7).

### C-03 — `writes.event_types` (the vocabulary's one writer)
Produced by: BRIEF-0114-A   Consumed by: B, C, G, H
`RoleSpec(name, entity_types=(), accepts_sorte=False, id=None)`,
`ScopeSpec(kind, role=None (a role's NAME), level="knows")`,
`EventTypeSpec(name, domain="other", roles=(), counts_quantity=False,
in_chronicle=True, participants_secret=False, scopes=())`;
`clean_event_type(db, world_id, spec, type_id=None) -> EventTypeSpec`
(`ValueError`, writes nothing); `write_event_type(db, *, world_id, spec,
type_id=None) -> EventType` (flushed; on an existing type nothing in use
is taken away, an unused role is retired); `set_event_type_status`;
`clean_sorte_name(db, world_id, name, sorte_id=None) -> str`;
`write_sorte(db, *, world_id, name, sorte_id=None) -> EventSorte`;
`set_sorte_status`; `ensure_domain_type(db, *, world_id, domain) ->
EventType` (the world's type of that domain's label, or made with one
role « Impliqué » accepting every entity type).

## Context

The series' third layer starts here (C1, F1): what happens in a world becomes one of its own EVENT TYPES, as data. This brief lays the vocabulary -- types, roles and the entity types each accepts, scopes (who learns), sortes -- and the columns the later briefs fill (`event.type_id`, `event.quantity`, `agenda_step.started_at`, `condition_node.since`, the `failure` role, `condition_node_filter`). v2.24 types the four production events by their category (N1) and gives each its fact (O1, K-a); nothing reads the new tables yet.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `models/canon_event.py` (new): `EventType`, `EventTypeRole`, `EventTypeRoleType`, `EventTypeScope`, `EventSorte`, `EventParticipant`; `EVENT_DOMAINS`, `EVENT_SCOPE_KINDS`, `EVENT_VOCAB_STATUSES`, `EVENT_SCOPE_LEVELS` (C-01); exported by `models/__init__.py`;
   - `models/config.py`: `CONDITION_ROLES` gains `failure`, `CONDITION_WINDOWS`, `ConditionNode.since` (`ck_condition_node_since`), `ConditionNodeFilter`, `AgendaStep.started_at`; `models/pipeline.py`: `ConditionDraft`'s role CHECK gains `failure`; `models/canon.py`: `Event.type_id`, `Event.quantity` (nullable at v2.24);
   - `event_vocab.py` (new, C-02) and `writes/event_types.py` (new, C-03), exported by `writes/__init__.py`;
   - `scripts/migrate_v2_24_event_journal.py` (new): rebuilds `condition`, `condition_draft`, `condition_node` (the CHECKs), adds the columns and the seven tables, then `_backfill(cursor)` types every event by its category (« Impliqué »), copies its `event_entity` links into `event_participant`, writes its fact (`evenement`, « title — description ») and, when `public`/`confirmed`, a `world` default at `knows`; refuses below v2.23; idempotent; post-checks; `schema_meta` -> v2.24;
   - `schema_version.py` -> v2.24; `world-engine-schema.md` (header, the seven tables, the columns) and `world-engine-schema-changelog.md` (v2.24);
   - `writes/worlds.py` (the world cascade deletes the new rows) and `checks/world_cascade.py`; `canon_write_policy.txt` (the new writers and tables); `checks/single_canon_write.py` docstring (the full-replace deletes of a type's scopes); `condition_interpreter.ROLE_LABELS_FR["failure"]`; `checks/conditions.py` and `checks/condition_interpreter.py` follow the roles;
   - creates check `event_journal.py` (EA1-EA7);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_24_event_journal.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/event_vocab.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/canon.py
   - src/world_engine/models/canon_event.py
   - src/world_engine/models/config.py
   - src/world_engine/models/pipeline.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/event_types.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/conditions.py
   - tooling/verify/checks/event_journal.py
   - tooling/verify/checks/single_canon_write.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_24_event_journal.py b/scripts/migrate_v2_24_event_journal.py
new file mode 100644
index 0000000..ffaf37b
--- /dev/null
+++ b/scripts/migrate_v2_24_event_journal.py
@@ -0,0 +1,352 @@
+"""Migration v2.24 — the event journal's vocabulary (TICKET-0114,
+BRIEF-0114-A; decisions F1, B1, C1, D1, H1, K-a, N1, O1 and V1 of the
+conditions series).
+
+Schema, additive except two rebuilds:
+
+- creates `event_type`, `event_type_role`, `event_type_role_type`,
+  `event_type_scope`, `event_sorte`, `event_participant` and
+  `condition_node_filter`, exactly as the models declare them;
+- adds `event.type_id`, `event.quantity` and `agenda_step.started_at`;
+- rebuilds `condition` and `condition_draft` (their role CHECK gains
+  `failure`, H1) and `condition_node` (a `since` column and its CHECK, F1),
+  every row copied.
+
+Data, for every event written before it (N1, V1, O1):
+
+- each event is typed by its former category: the world's type named after
+  that domain (« Social », « Autre »...), created when missing with one role
+  « Impliqué » accepting every entity type of the world;
+- each `event_entity` row becomes an `event_participant` in that role
+  (`event_entity` itself stays until v2.25 drops it);
+- each event gets its fact (`fact.event_id`, facet `evenement`, its title
+  then its description), and an event that was `public` or `confirmed`
+  gets a `world` default at `knows` -- known by everyone, as before; a
+  `secret` one gets none -- known by no one (O1). No `knowledge` row is
+  written.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.23. Idempotent: each step checks what is already there. One raw
+transaction (`foreign_keys` and `legacy_alter_table` set before it).
+
+Post-check, before `schema_meta` moves: every event has a type and exactly
+one fact; `event_participant` holds as many rows as `event_entity`;
+`condition`, `condition_node` and `condition_draft` kept their row counts;
+`PRAGMA foreign_key_check` on the tables this migration writes is empty (a
+dangling row elsewhere is a note, never a failure -- AMENDMENT-0107-01).
+`schema_meta` then moves to v2.24 -- its own version, not the code's:
+v2.25 (BRIEF-0114-C) drops what this one keeps.
+
+Run from the project root:
+
+    python scripts/migrate_v2_24_event_journal.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import uuid
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_24_event_journal.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+import unicodedata  # noqa: E402
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.23"
+_THIS_VERSION = "v2.24"
+# Parents first.
+_NEW_MODELS = (
+    models.EventType, models.EventTypeRole, models.EventTypeRoleType, models.EventTypeScope,
+    models.EventSorte, models.EventParticipant, models.ConditionNodeFilter,
+)
+_CONDITION_COLUMNS = "id, world_id, role, quest_offer_id, quest_offer_step_id, agenda_step_id, created_at"
+_DRAFT_COLUMNS = ("id, attempt_id, world_ref, world_name, role, instruction, outcome, retried, offer_ref, "
+                  "saved_as_proposed, payload, model_calls, created_at, decided_at")
+_NODE_COLUMNS = ("id, world_id, condition_id, parent_id, position, op, n, form, subject_role, "
+                 "subject_entity_id, target_entity_id, target_key, threshold, value")
+_ADDED_COLUMNS = (
+    ("event", "type_id", "VARCHAR REFERENCES event_type (id)"),
+    ("event", "quantity", "INTEGER"),
+    ("agenda_step", "started_at", "DATETIME"),
+)
+# The domains and their French type names -- frozen here as v2.24 wrote
+# them (`event_vocab.DOMAIN_LABELS_FR`, `DOMAIN_ROLE_FR` at v2.24).
+_DOMAIN_NAMES = {
+    "political": "Politique", "magical": "Magique", "criminal": "Criminel", "military": "Militaire",
+    "social": "Social", "mystery": "Mystère", "other": "Autre",
+}
+_ROLE_NAME = "Impliqué"
+_BUILTIN_TYPES = ("character", "location", "faction", "item")
+_CREATED_BY = "migration_v2_24"
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = (
+    "event", "agenda_step", "condition", "condition_node", "condition_draft", "event_type", "event_type_role",
+    "event_type_role_type", "event_type_scope", "event_sorte", "event_participant",
+    "condition_node_filter", "fact", "fact_default",
+)
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.24 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _table_sql(table: str) -> str:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
+    return row[0] if row is not None else ""
+
+
+def _columns(table: str) -> set[str]:
+    return {column["name"] for column in inspect(engine).get_columns(table)}
+
+
+def _count(conn, table: str) -> int:
+    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _rebuild(cursor, table: str, model, columns: str) -> None:
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
+    _create_from_model(cursor, model)
+    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
+    cursor.execute(f"DROP TABLE {table}_old")
+
+
+def _plan() -> dict:
+    existing = set(inspect(engine).get_table_names())
+    return {
+        "condition": "'failure'" not in _table_sql("condition"),
+        "condition_draft": "'failure'" not in _table_sql("condition_draft"),
+        "condition_node": "since" not in _columns("condition_node"),
+        "columns": [(t, c, ddl) for t, c, ddl in _ADDED_COLUMNS if c not in _columns(t)],
+        "models": [m for m in _NEW_MODELS if m.__tablename__ not in existing],
+    }
+
+
+# --- the data (N1, V1, O1) -------------------------------------------------------
+
+def _key(name: str) -> str:
+    decomposed = unicodedata.normalize("NFKD", name.casefold())
+    return " ".join("".join(ch for ch in decomposed if not unicodedata.combining(ch)).split())
+
+
+def _now() -> str:
+    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
+
+
+def _world_types(cursor, world_id: str) -> list[str]:
+    slugs = [row[0] for row in cursor.execute(
+        "SELECT slug FROM entity_type WHERE world_id = ? AND status = 'active'", (world_id,)).fetchall()]
+    return list(_BUILTIN_TYPES) + sorted(s for s in slugs if s not in _BUILTIN_TYPES)
+
+
+def _domain_type(cursor, world_id: str, domain: str, made: dict) -> tuple[str, str]:
+    """(type id, role id) of the world's type for `domain`, made if missing."""
+    name = _DOMAIN_NAMES[domain]
+    if (world_id, domain) in made:
+        return made[(world_id, domain)]
+    for type_id, type_name in cursor.execute(
+            "SELECT id, name FROM event_type WHERE world_id = ?", (world_id,)).fetchall():
+        if _key(type_name) == _key(name):
+            role = cursor.execute("SELECT id FROM event_type_role WHERE type_id = ? ORDER BY position, id",
+                                  (type_id,)).fetchone()
+            made[(world_id, domain)] = (type_id, role[0])
+            return made[(world_id, domain)]
+    now = _now()
+    type_id, role_id = str(uuid.uuid4()), str(uuid.uuid4())
+    cursor.execute(
+        "INSERT INTO event_type (id, world_id, name, domain, counts_quantity, in_chronicle, participants_secret, "
+        "status, created_at, updated_at) VALUES (?, ?, ?, ?, 0, 1, 0, 'active', ?, ?)",
+        (type_id, world_id, name, domain, now, now))
+    cursor.execute(
+        "INSERT INTO event_type_role (id, world_id, type_id, name, position, accepts_sorte, status) "
+        "VALUES (?, ?, ?, ?, 0, 0, 'active')", (role_id, world_id, type_id, _ROLE_NAME))
+    for entity_type in _world_types(cursor, world_id):
+        cursor.execute("INSERT INTO event_type_role_type (id, world_id, role_id, entity_type) VALUES (?, ?, ?, ?)",
+                       (str(uuid.uuid4()), world_id, role_id, entity_type))
+    made[(world_id, domain)] = (type_id, role_id)
+    return type_id, role_id
+
+
+def _fact_text(title: str, description) -> str:
+    description = (description or "").strip()
+    return f"{title} — {description}" if description else title
+
+
+def _backfill(cursor) -> list[str]:
+    done: list[str] = []
+    made: dict = {}
+    events = cursor.execute(
+        "SELECT id, world_id, type, title, description, knowledge_status FROM event WHERE type_id IS NULL "
+        "ORDER BY recorded_at, id").fetchall()
+    for event_id, world_id, category, title, description, status in events:
+        domain = category if category in _DOMAIN_NAMES else "other"
+        type_id, role_id = _domain_type(cursor, world_id, domain, made)
+        cursor.execute("UPDATE event SET type_id = ? WHERE id = ?", (type_id, event_id))
+        links = cursor.execute("SELECT entity_id FROM event_entity WHERE event_id = ? ORDER BY rowid",
+                               (event_id,)).fetchall()
+        for position, (entity_id,) in enumerate(links):
+            cursor.execute(
+                "INSERT INTO event_participant (id, world_id, event_id, role_id, entity_id, position) "
+                "VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), world_id, event_id, role_id, entity_id, position))
+        if cursor.execute("SELECT 1 FROM fact WHERE event_id = ?", (event_id,)).fetchone() is None:
+            fact_id = str(uuid.uuid4())
+            cursor.execute(
+                "INSERT INTO fact (id, world_id, event_id, content, facet, default_level, created_at, created_by, "
+                "change_history) VALUES (?, ?, ?, ?, 'evenement', 'unaware', ?, ?, '[]')",
+                (fact_id, world_id, event_id, _fact_text(title, description), _now(), _CREATED_BY))
+            if status in ("public", "confirmed"):
+                cursor.execute(
+                    "INSERT INTO fact_default (id, world_id, fact_id, scope_type, scope_id, level, created_at, "
+                    "created_by) VALUES (?, ?, ?, 'world', NULL, 'knows', ?, ?)",
+                    (str(uuid.uuid4()), world_id, fact_id, _now(), _CREATED_BY))
+        done.append(event_id)
+    return done
+
+
+def _apply(plan: dict) -> list[str]:
+    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
+    PRAGMAs must land before any transaction exists)."""
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        if plan["condition"]:
+            _rebuild(cursor, "condition", models.Condition, _CONDITION_COLUMNS)
+            applied.append("condition rebuilt")
+        if plan["condition_draft"]:
+            _rebuild(cursor, "condition_draft", models.ConditionDraft, _DRAFT_COLUMNS)
+            applied.append("condition_draft rebuilt")
+        if plan["condition_node"]:
+            _rebuild(cursor, "condition_node", models.ConditionNode, _NODE_COLUMNS)
+            applied.append("condition_node rebuilt")
+        for table, column, ddl in plan["columns"]:
+            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
+            applied.append(f"{table}.{column} added")
+        for model in plan["models"]:
+            _create_from_model(cursor, model)
+            applied.append(f"{model.__tablename__} created")
+        typed = _backfill(cursor)
+        if typed:
+            applied.append(f"{len(typed)} event(s) typed, with their participants and facts")
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    return applied
+
+
+def _post_checks(before: dict[str, int]) -> None:
+    with engine.connect() as conn:
+        untyped = conn.execute(text("SELECT COUNT(*) FROM event WHERE type_id IS NULL")).scalar_one()
+        unfacted = conn.execute(text(
+            "SELECT COUNT(*) FROM event e WHERE (SELECT COUNT(*) FROM fact f WHERE f.event_id = e.id) != 1"
+        )).scalar_one()
+        participants, links = _count(conn, "event_participant"), _count(conn, "event_entity")
+        after = {t: _count(conn, t) for t in before}
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    problems = []
+    if untyped:
+        problems.append(f"{untyped} event(s) without a type")
+    if unfacted:
+        problems.append(f"{unfacted} event(s) without exactly one fact")
+    if participants != links:
+        problems.append(f"event_participant holds {participants} row(s), event_entity {links}")
+    if after != before:
+        problems.append(f"row counts changed {before} -> {after}")
+    if "'failure'" not in _table_sql("condition") or "'failure'" not in _table_sql("condition_draft") \
+            or "since" not in _columns("condition_node"):
+        problems.append("condition, condition_draft or condition_node was not rebuilt")
+    if dangling:
+        problems.append(f"foreign_key_check {dangling}")
+    if problems:
+        raise SystemExit("Migration v2.24 aborted, post-check failed: " + "; ".join(problems) + ".")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: every event typed with one fact; {participants} participant(s); counts kept {after}.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=_THIS_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {_THIS_VERSION!r}")
+        elif _version_key(row.static_version) < _version_key(_THIS_VERSION):
+            previous = row.static_version
+            row.static_version = _THIS_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.24 — the event journal's vocabulary")
+    _refuse()
+    with engine.connect() as conn:
+        before = {t: _count(conn, t) for t in ("condition", "condition_node", "condition_draft", "event",
+                                               "agenda_step")}
+    applied = _apply(_plan())
+    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.24 already fully applied.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.24 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index 6106336..991447b 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -71,6 +71,7 @@ ROLE_LABELS_FR: dict[str, str] = {
     "eligibility": "à qui l'offre est proposée",
     "prerequisite": "ce qu'il faut pour tenter l'étape",
     "completion": "quand l'objectif de l'étape est atteint",
+    "failure": "quand l'étape a échoué",
 }
 
 # What each form takes as its target, in the model's form (C-03). One line
diff --git a/src/world_engine/event_vocab.py b/src/world_engine/event_vocab.py
new file mode 100644
index 0000000..491b131
--- /dev/null
+++ b/src/world_engine/event_vocab.py
@@ -0,0 +1,168 @@
+"""The event journal's vocabulary, read (TICKET-0114, BRIEF-0114-A;
+decisions B1, C1, D1, N1 and W1 of the conditions series).
+
+A world's event types -- each with its roles in order, the entity types a
+role accepts and whether a sorte may fill it, who learns an event of it --
+and its sortes. Every surface that names an event type or a sorte reads
+them here: the Création « Vocabulaire du monde » tab, the journal's sheet,
+the `event` condition form, the interpreter, the play analyzer.
+
+`near_event_types` / `near_sortes` find the names near a new one, so a
+creator never makes « Tuer » twice as « tuer » (the WK2 rule of
+TICKET-0113, `lore_resolve.near_ratio`).
+
+`DOMAIN_LABELS_FR` names each domain in French; `DOMAIN_ROLE_FR` is the one
+role of a type made from a domain (`writes.event_types.ensure_domain_type`,
+and the v2.24 migration for the events written before it).
+
+This module writes nothing; `writes/event_types.py` is its writer.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .lore_resolve import near_ratio, near_score, normalize_surface
+from .models import (
+    EventSorte,
+    EventType,
+    EventTypeRole,
+    EventTypeRoleType,
+    EventTypeScope,
+)
+
+DOMAIN_LABELS_FR: dict[str, str] = {
+    "political": "Politique", "magical": "Magique", "criminal": "Criminel", "military": "Militaire",
+    "social": "Social", "mystery": "Mystère", "other": "Autre",
+}
+DOMAIN_ROLE_FR = "Impliqué"
+# The condition form that counts events (BRIEF-0114-D); named here so the
+# vocabulary's writer can tell which leaves name a type (`event_journal.py`
+# keeps it in `condition_forms.REQUIREMENT_TYPES`).
+EVENT_FORM = "event"
+
+
+@dataclass(frozen=True)
+class RoleView:
+    id: str
+    name: str
+    position: int
+    entity_types: tuple[str, ...]
+    accepts_sorte: bool
+    status: str
+
+
+@dataclass(frozen=True)
+class ScopeView:
+    kind: str
+    role_id: Optional[str]
+    level: str
+
+
+@dataclass(frozen=True)
+class EventTypeView:
+    id: str
+    world_id: str
+    name: str
+    domain: str
+    counts_quantity: bool
+    in_chronicle: bool
+    participants_secret: bool
+    status: str
+    roles: tuple[RoleView, ...]
+    scopes: tuple[ScopeView, ...]
+
+    def role(self, role_id: Optional[str]) -> Optional[RoleView]:
+        return next((r for r in self.roles if r.id == role_id), None)
+
+    def active_roles(self) -> tuple[RoleView, ...]:
+        return tuple(r for r in self.roles if r.status == "active")
+
+
+def role_accepts(role: RoleView, entity_type: Optional[str]) -> bool:
+    """A role accepts an entity of `entity_type` when it names that type."""
+    return entity_type is not None and entity_type in role.entity_types
+
+
+def _roles(db: Session, type_id: str) -> tuple[RoleView, ...]:
+    rows = db.exec(select(EventTypeRole).where(EventTypeRole.type_id == type_id)
+                   .order_by(EventTypeRole.position, EventTypeRole.id)).all()
+    views = []
+    for row in rows:
+        types = tuple(db.exec(select(EventTypeRoleType.entity_type).where(
+            EventTypeRoleType.role_id == row.id).order_by(EventTypeRoleType.entity_type)).all())
+        views.append(RoleView(row.id, row.name, row.position, types, row.accepts_sorte, row.status))
+    return tuple(views)
+
+
+def _scopes(db: Session, type_id: str) -> tuple[ScopeView, ...]:
+    rows = db.exec(select(EventTypeScope).where(EventTypeScope.type_id == type_id)
+                   .order_by(EventTypeScope.scope_kind, EventTypeScope.id)).all()
+    return tuple(ScopeView(row.scope_kind, row.role_id, row.level) for row in rows)
+
+
+def _view(db: Session, row: EventType) -> EventTypeView:
+    return EventTypeView(
+        id=row.id, world_id=row.world_id, name=row.name, domain=row.domain,
+        counts_quantity=row.counts_quantity, in_chronicle=row.in_chronicle,
+        participants_secret=row.participants_secret, status=row.status,
+        roles=_roles(db, row.id), scopes=_scopes(db, row.id),
+    )
+
+
+def type_view(db: Session, type_id: Optional[str]) -> Optional[EventTypeView]:
+    """One event type, its roles and scopes; None when there is none."""
+    row = db.get(EventType, type_id) if type_id else None
+    return _view(db, row) if row is not None else None
+
+
+def world_event_types(db: Session, world_id: str, include_retired: bool = False) -> list[EventTypeView]:
+    """A world's event types, by name; the retired ones only when asked."""
+    query = select(EventType).where(EventType.world_id == world_id)
+    if not include_retired:
+        query = query.where(EventType.status == "active")
+    rows = db.exec(query).all()
+    return [_view(db, row) for row in sorted(rows, key=lambda r: (r.name.casefold(), r.id))]
+
+
+def world_sortes(db: Session, world_id: str, include_retired: bool = False) -> list[EventSorte]:
+    """A world's sortes, by name; the retired ones only when asked."""
+    query = select(EventSorte).where(EventSorte.world_id == world_id)
+    if not include_retired:
+        query = query.where(EventSorte.status == "active")
+    return sorted(db.exec(query).all(), key=lambda r: (r.name.casefold(), r.id))
+
+
+@dataclass(frozen=True)
+class NearName:
+    id: str
+    name: str
+    score: int
+
+
+def _near(rows, name: str, exclude_id: Optional[str]) -> tuple[NearName, ...]:
+    target = normalize_surface(name or "")
+    if not target:
+        return ()
+    found = []
+    for row_id, row_name in rows:
+        if row_id == exclude_id:
+            continue
+        ratio = near_ratio(target, row_name)
+        if ratio is not None:
+            found.append(NearName(row_id, row_name, near_score(ratio)))
+    return tuple(sorted(found, key=lambda n: (-n.score, n.name.casefold(), n.id)))
+
+
+def near_event_types(db: Session, world_id: str, name: str, exclude_id: Optional[str] = None) -> tuple[NearName, ...]:
+    """The world's event types (retired included) whose name is near
+    `name`, best first. For display: the creator picks, the tool never does."""
+    return _near(((v.id, v.name) for v in world_event_types(db, world_id, include_retired=True)), name, exclude_id)
+
+
+def near_sortes(db: Session, world_id: str, name: str, exclude_id: Optional[str] = None) -> tuple[NearName, ...]:
+    """The world's sortes (retired included) whose name is near `name`."""
+    return _near(((s.id, s.name) for s in world_sortes(db, world_id, include_retired=True)), name, exclude_id)
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 1abdf68..16c5714 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -21,6 +21,10 @@ Layout, by stratum:
                         AttributeDefinitionType, AttributeChoice,
                         AttributeValue, AttributeChange; TICKET-0113,
                         schema v2.22), canon.
+    canon_event.py   — the event journal's vocabulary and participants
+                        (EventType, EventTypeRole, EventTypeRoleType,
+                        EventTypeScope, EventSorte, EventParticipant;
+                        TICKET-0114, schema v2.24), canon.
     config.py        — canon curated-config tables too new/small to justify
                         growing canon.py at its module_budget cap
                         (ConversationWindowConfig, TICKET-0050).
@@ -44,7 +48,7 @@ This module re-exports the ENTIRE former public surface of the flat
 (`_uuid`, `_created_ts`) — so every existing `from .models import X` /
 `from world_engine.models import X` in `src/` and `scripts/` resolves
 unchanged. Import order (canon, canon_faction, canon_knowledge,
-canon_attribute, config,
+canon_attribute, canon_event, config,
 ephemeral, pipeline, observation, quests) keeps table registration on
 `SQLModel.metadata` deterministic;
 cross-stratum foreign keys (string table-name references) resolve
@@ -102,12 +106,26 @@ from .canon_attribute import (
     AttributeDefinitionType,
     AttributeValue,
 )
+from .canon_event import (
+    EVENT_DOMAINS,
+    EVENT_SCOPE_KINDS,
+    EVENT_SCOPE_LEVELS,
+    EVENT_VOCAB_STATUSES,
+    EventParticipant,
+    EventSorte,
+    EventType,
+    EventTypeRole,
+    EventTypeRoleType,
+    EventTypeScope,
+)
 from .config import (
     CONDITION_OPS,
     CONDITION_ROLES,
+    CONDITION_WINDOWS,
     AgendaStep,
     Condition,
     ConditionNode,
+    ConditionNodeFilter,
     ConversationWindowConfig,
     SkillRank,
 )
@@ -202,6 +220,16 @@ __all__ = [
     "ATTRIBUTE_TYPE_SIDES",
     "ATTRIBUTE_STATUSES",
     "ATTRIBUTE_CHANGE_KINDS",
+    "EventType",
+    "EventTypeRole",
+    "EventTypeRoleType",
+    "EventTypeScope",
+    "EventSorte",
+    "EventParticipant",
+    "EVENT_DOMAINS",
+    "EVENT_SCOPE_KINDS",
+    "EVENT_SCOPE_LEVELS",
+    "EVENT_VOCAB_STATUSES",
     "NpcGoal",
     "GoalPrerequisite",
     "Ledger",
@@ -249,7 +277,9 @@ __all__ = [
     "AgendaStep",
     "Condition",
     "ConditionNode",
+    "ConditionNodeFilter",
     "CONDITION_OPS",
+    "CONDITION_WINDOWS",
     "CONDITION_ROLES",
     "QUEST_OFFER_STATUSES",
     "Quest",
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index 46fed67..d2733ed 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -498,6 +498,10 @@ class Event(SQLModel, table=True):
     consequences: Optional[Any] = Field(default=None, sa_column=Column(JSON))
     occurred_at: Optional[datetime] = None
     recorded_at: datetime = _created_ts()
+    # v2.24 (TICKET-0114, BRIEF-0114-A, N1): the world's type it is one of
+    # (`models/canon_event.py`), and how many, when its type counts (D1).
+    type_id: Optional[str] = Field(default=None, foreign_key="event_type.id")
+    quantity: Optional[int] = None
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/models/canon_event.py b/src/world_engine/models/canon_event.py
new file mode 100644
index 0000000..2d2a0d4
--- /dev/null
+++ b/src/world_engine/models/canon_event.py
@@ -0,0 +1,163 @@
+"""Canon SQLModel table classes -- the event journal's vocabulary and its
+participants (TICKET-0114, BRIEF-0114-A, schema v2.24; decisions F1, B1, C1,
+D1, K-a, N1, V1 and W1 of the conditions series).
+
+A world names what can happen in it -- « Tuer », « Repérer », « Pacte » --
+and every `event` row is one happening of one of those types:
+
+- `event_type`            : one type of one world -- its name, its domain
+  (one of the seven former categories, F1), whether an event of it carries
+  a quantity (« 3 loups »), whether it enters the chronicle the models read
+  (Q1), whether its participants keep it secret by default (X1), active or
+  retired.
+- `event_type_role`       : the roles of a type (C1) -- « tueur »,
+  « victime » -- in order; a role is retired, never deleted.
+- `event_type_role_type`  : the entity types a role accepts (C1, the
+  `attribute_definition_type` shape). A role may also accept a sorte
+  (`accepts_sorte`, D1).
+- `event_type_scope`      : who learns an event of the type (K-a, W1): its
+  place, everyone, the acquaintances of a role, the faction a role names --
+  each at a knowledge level. No row: the participants only.
+- `event_sorte`           : the anonymous kinds of a world (D1) -- « loup »,
+  « bandit » -- a role may be filled by one, with the event's quantity.
+- `event_participant`     : who took part in one event, in which role: an
+  entity or a sorte, exactly one (V1; it replaces `event_entity`).
+
+`writes/event_types.py` is the one writer of the vocabulary tables,
+`writes/events.py` the one writer of `event_participant`. Same
+schema-fidelity conventions as `canon.py`.
+"""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Optional
+
+from sqlalchemy import CheckConstraint, Index, text
+from sqlmodel import Field, SQLModel
+
+from .canon import _created_ts, _uuid
+
+# F1: the seven former `event.type` categories, now a type's domain. Quoted
+# by the CHECK below; `tick_normalize._EVENT_TYPES` is the same set
+# (`event_journal.py` EA1 keeps them equal).
+EVENT_DOMAINS: tuple[str, ...] = (
+    "political", "magical", "criminal", "military", "social", "mystery", "other",
+)
+# W1: who learns an event, besides its participants. `rencontre` and
+# `faction` name a role of the type; `location` is the event's place.
+EVENT_SCOPE_KINDS: tuple[str, ...] = ("location", "world", "rencontre", "faction")
+EVENT_VOCAB_STATUSES: tuple[str, ...] = ("active", "retired")
+# The knowledge ladder -- `writes.knowledge.KNOWLEDGE_LEVEL_LADDER`, quoted by
+# the CHECK below (models never import `writes`; EA1 keeps them equal).
+EVENT_SCOPE_LEVELS: tuple[str, ...] = (
+    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
+)
+
+
+def _in(values: tuple[str, ...]) -> str:
+    return ",".join(f"'{v}'" for v in values)
+
+
+class EventType(SQLModel, table=True):
+    __tablename__ = "event_type"
+    __table_args__ = (
+        CheckConstraint(f"domain IN ({_in(EVENT_DOMAINS)})", name="ck_event_type_domain"),
+        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_type_status"),
+        Index("idx_event_type_name", "world_id", text("name COLLATE NOCASE"), unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    name: str
+    domain: str = Field(default="other", sa_column_kwargs={"server_default": text("'other'")})
+    counts_quantity: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    in_chronicle: bool = Field(default=True, sa_column_kwargs={"server_default": text("1")})
+    participants_secret: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
+    created_at: datetime = _created_ts()
+    updated_at: datetime = _created_ts()
+
+
+class EventTypeRole(SQLModel, table=True):
+    __tablename__ = "event_type_role"
+    __table_args__ = (
+        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_type_role_status"),
+        Index("idx_event_type_role_name", "type_id", text("name COLLATE NOCASE"), unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    type_id: str = Field(foreign_key="event_type.id", nullable=False)
+    name: str
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+    accepts_sorte: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
+
+
+class EventTypeRoleType(SQLModel, table=True):
+    __tablename__ = "event_type_role_type"
+    __table_args__ = (
+        Index("idx_event_type_role_type_unique", "role_id", "entity_type", unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
+    entity_type: str
+
+
+class EventTypeScope(SQLModel, table=True):
+    __tablename__ = "event_type_scope"
+    __table_args__ = (
+        CheckConstraint(f"scope_kind IN ({_in(EVENT_SCOPE_KINDS)})", name="ck_event_type_scope_kind"),
+        CheckConstraint(
+            "(scope_kind IN ('rencontre','faction')) = (role_id IS NOT NULL)", name="ck_event_type_scope_role",
+        ),
+        CheckConstraint(f"level IN ({_in(EVENT_SCOPE_LEVELS)})", name="ck_event_type_scope_level"),
+        Index("idx_event_type_scope_type", "type_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    type_id: str = Field(foreign_key="event_type.id", nullable=False)
+    scope_kind: str
+    role_id: Optional[str] = Field(default=None, foreign_key="event_type_role.id")
+    level: str = Field(default="knows", sa_column_kwargs={"server_default": text("'knows'")})
+
+
+class EventSorte(SQLModel, table=True):
+    __tablename__ = "event_sorte"
+    __table_args__ = (
+        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_sorte_status"),
+        Index("idx_event_sorte_name", "world_id", text("name COLLATE NOCASE"), unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    name: str
+    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
+    created_at: datetime = _created_ts()
+
+
+class EventParticipant(SQLModel, table=True):
+    __tablename__ = "event_participant"
+    __table_args__ = (
+        CheckConstraint(
+            "(entity_id IS NOT NULL) + (sorte_id IS NOT NULL) = 1", name="ck_event_participant_one",
+        ),
+        Index("idx_event_participant_event", "event_id", "position"),
+        Index("idx_event_participant_entity", "entity_id"),
+        Index("idx_event_participant_unique_entity", "event_id", "role_id", "entity_id", unique=True,
+              sqlite_where=text("entity_id IS NOT NULL")),
+        Index("idx_event_participant_unique_sorte", "event_id", "role_id", "sorte_id", unique=True,
+              sqlite_where=text("sorte_id IS NOT NULL")),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    event_id: str = Field(foreign_key="event.id", nullable=False)
+    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
+    entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    sorte_id: Optional[str] = Field(default=None, foreign_key="event_sorte.id")
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index 6bdd127..8c1a26c 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -98,6 +98,10 @@ class AgendaStep(SQLModel, table=True):
     domain: Optional[str] = None
     created_at: datetime = _created_ts()
     updated_at: datetime = _created_ts()
+    # v2.24 (TICKET-0114, BRIEF-0114-A, F1): when the step became active --
+    # the « depuis le début de l'étape » window. NULL on a step activated
+    # before v2.24 (its quest's `accepted_at` stands in).
+    started_at: Optional[datetime] = None
     change_history: list = Field(
         default_factory=list,
         sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
@@ -127,14 +131,19 @@ class AgendaStep(SQLModel, table=True):
 # Curated plan metadata, the requirement rows' family: no `change_history`
 # (an offer snapshots itself; a save replaces its conditions whole).
 # -----------------------------------------------------------------------------
-CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion")
+# `failure` (v2.24, TICKET-0114, H1): when the step has failed -- shown, never
+# acting, like `completion` (M1).
+CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion", "failure")
 CONDITION_OPS: tuple[str, ...] = ("all", "any", "not", "at_least", "leaf")
+# F1 (v2.24, TICKET-0114): since when a leaf counts -- ever, since its quest
+# was accepted, since its step became active.
+CONDITION_WINDOWS: tuple[str, ...] = ("always", "quest", "step")
 
 
 class Condition(SQLModel, table=True):
     __tablename__ = "condition"
     __table_args__ = (
-        CheckConstraint("role IN ('eligibility','prerequisite','completion')", name="ck_condition_role"),
+        CheckConstraint("role IN ('eligibility','prerequisite','completion','failure')", name="ck_condition_role"),
         CheckConstraint(
             "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + (agenda_step_id IS NOT NULL) = 1",
             name="ck_condition_owner",
@@ -161,7 +170,7 @@ class ConditionNode(SQLModel, table=True):
         CheckConstraint("(op = 'leaf') = (form IS NOT NULL)", name="ck_condition_node_leaf"),
         CheckConstraint(
             "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND target_entity_id IS NULL "
-            "AND target_key IS NULL AND threshold IS NULL AND value IS NULL)",
+            "AND target_key IS NULL AND threshold IS NULL AND value IS NULL AND since IS NULL)",
             name="ck_condition_node_connector",
         ),
         CheckConstraint(
@@ -172,6 +181,8 @@ class ConditionNode(SQLModel, table=True):
             "subject_role IS NULL OR subject_role IN ('doer','giver','contact')", name="ck_condition_node_role",
         ),
         CheckConstraint("(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)", name="ck_condition_node_n"),
+        CheckConstraint(f"since IS NULL OR since IN ({','.join(repr(w) for w in CONDITION_WINDOWS)})",
+                        name="ck_condition_node_since"),
         Index("idx_condition_node_condition", "condition_id", "parent_id", "position"),
     )
 
@@ -189,6 +200,31 @@ class ConditionNode(SQLModel, table=True):
     target_key: Optional[str] = None
     threshold: Optional[int] = None
     value: Optional[str] = None
+    # v2.24 (TICKET-0114, F1): since when a leaf counts what happened --
+    # `CONDITION_WINDOWS`; NULL on every leaf that counts nothing.
+    since: Optional[str] = None
+
+
+# A leaf's filters on the other roles of its event type (v2.24, TICKET-0114,
+# BRIEF-0114-A, decision 3 of the lot): « un loup », « à Ombreval » -- one row
+# per role, filled by an entity or a sorte, exactly one. Rows, never JSON
+# (INV-20); written only by `writes.conditions.write_condition`.
+class ConditionNodeFilter(SQLModel, table=True):
+    __tablename__ = "condition_node_filter"
+    __table_args__ = (
+        CheckConstraint(
+            "(entity_id IS NOT NULL) + (sorte_id IS NOT NULL) = 1", name="ck_condition_node_filter_one",
+        ),
+        Index("idx_condition_node_filter_node", "node_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    node_id: str = Field(foreign_key="condition_node.id", nullable=False)
+    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
+    entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    sorte_id: Optional[str] = Field(default=None, foreign_key="event_sorte.id")
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index 128ba12..aa81f5b 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -454,7 +454,7 @@ class ConditionDraft(SQLModel, table=True):
         Index("idx_condition_draft_attempt", "attempt_id", "created_at"),
         Index("idx_condition_draft_world", "world_ref", "created_at"),
         CheckConstraint(
-            "role IN ('eligibility','prerequisite','completion')",
+            "role IN ('eligibility','prerequisite','completion','failure')",
             name="ck_condition_draft_role",
         ),
         CheckConstraint(
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 4034795..198cae8 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.23"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.24"
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index a73467d..70c5442 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -65,6 +65,13 @@ Layout, by canon domain:
                           `clean_definition`, `write_attribute_definition`,
                           `set_attribute_status`, `write_attribute_value`
                           (TICKET-0113, BRIEF-0113-A).
+    event_types.py      — the event journal's vocabulary: `event_type`,
+                          `event_type_role`, `event_type_role_type`,
+                          `event_type_scope`, `event_sorte`:
+                          `clean_event_type`, `write_event_type`,
+                          `set_event_type_status`, `write_sorte`,
+                          `set_sorte_status`, `ensure_domain_type`
+                          (TICKET-0114, BRIEF-0114-A).
     worlds.py           — `delete_world_cascade` (the sole delete-side
                           helper, wildcard-allowed in canon_write_policy.txt).
 
@@ -172,6 +179,18 @@ from .attributes import (
     write_attribute_definition,
     write_attribute_value,
 )
+from .event_types import (
+    EventTypeSpec,
+    RoleSpec,
+    ScopeSpec,
+    clean_event_type,
+    clean_sorte_name,
+    ensure_domain_type,
+    set_event_type_status,
+    set_sorte_status,
+    write_event_type,
+    write_sorte,
+)
 from .pipeline import (
     BATCH_RESOLVED_STATUS,
     BATCH_STATUSES,
diff --git a/src/world_engine/writes/event_types.py b/src/world_engine/writes/event_types.py
new file mode 100644
index 0000000..6659a08
--- /dev/null
+++ b/src/world_engine/writes/event_types.py
@@ -0,0 +1,375 @@
+"""The writer of the event journal's vocabulary (TICKET-0114, BRIEF-0114-A;
+decisions B1, C1, D1, N1 and W1 of the conditions series): the one writer of
+`event_type`, `event_type_role`, `event_type_role_type`, `event_type_scope`
+and `event_sorte`.
+
+- `clean_event_type(db, world_id, spec, type_id=None)` : a type as it will
+  be written, or `ValueError` -- its name is no other type's of the world
+  (compared through `lore_resolve.normalize_surface`), its domain one of
+  `EVENT_DOMAINS`, one role or more with distinct names, each accepting one
+  of the world's entity types or a sorte; a scope on `rencontre` names a
+  role that accepts an entity, on `faction` a role that accepts a faction.
+  On an existing type, nothing in use is taken away: a role an event or a
+  condition names, an entity type a participant has, a sorte a participant
+  is, a quantity an event carries. Writes nothing -- the interpreter and the
+  analyzer validate a proposed type through it.
+- `write_event_type(db, *, world_id, spec, type_id=None)` : create or save
+  one type after cleaning it. Roles are matched by id, else by name; a role
+  dropped from the list is retired, never deleted, and comes back when named
+  again. A role's entity types and the type's scopes are replaced whole.
+- `set_event_type_status(db, *, world_id, type_id, status)` : retire or
+  restore a type; retiring is refused while a condition names it.
+- `clean_sorte_name` / `write_sorte(db, *, world_id, name, sorte_id=None)` /
+  `set_sorte_status(...)` : the same for a sorte; retiring is refused while
+  a condition names it.
+- `ensure_domain_type(db, *, world_id, domain)` : the type made from a
+  domain (N1) -- « Social », one role « Impliqué » accepting every entity
+  type of the world -- found by its name, created when the world has none.
+  It types what still arrives untyped (the world tick until TICKET-0119).
+
+None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlalchemy import text
+from sqlmodel import Session, select
+
+from ..attributes import world_entity_types
+from ..event_vocab import DOMAIN_LABELS_FR, DOMAIN_ROLE_FR, EVENT_FORM
+from ..lore_resolve import normalize_surface
+from ..models import (
+    EVENT_DOMAINS,
+    EVENT_SCOPE_KINDS,
+    EVENT_SCOPE_LEVELS,
+    EVENT_VOCAB_STATUSES,
+    ConditionNode,
+    ConditionNodeFilter,
+    Entity,
+    Event,
+    EventParticipant,
+    EventSorte,
+    EventType,
+    EventTypeRole,
+    EventTypeRoleType,
+    EventTypeScope,
+)
+
+MAX_NAME_CHARS = 80
+MAX_ROLES = 8
+
+
+@dataclass(frozen=True)
+class RoleSpec:
+    """One role as the creator states it; `id` names an existing role."""
+    name: str
+    entity_types: tuple[str, ...] = ()
+    accepts_sorte: bool = False
+    id: Optional[str] = None
+
+
+@dataclass(frozen=True)
+class ScopeSpec:
+    """Who learns an event of the type (W1); `role` is a role's NAME, for a
+    `rencontre` or `faction` scope."""
+    kind: str
+    role: Optional[str] = None
+    level: str = "knows"
+
+
+@dataclass(frozen=True)
+class EventTypeSpec:
+    name: str
+    domain: str = "other"
+    roles: tuple[RoleSpec, ...] = ()
+    counts_quantity: bool = False
+    in_chronicle: bool = True
+    participants_secret: bool = False
+    scopes: tuple[ScopeSpec, ...] = ()
+
+
+# --- cleaning ------------------------------------------------------------------
+
+def _clean_label(raw: object, what: str) -> str:
+    if not isinstance(raw, str) or not raw.strip():
+        raise ValueError(f"{what} needs a name")
+    clean = " ".join(raw.split())
+    if len(clean) > MAX_NAME_CHARS:
+        raise ValueError(f"{what}'s name has at most {MAX_NAME_CHARS} characters")
+    return clean
+
+
+def _clean_type_name(db: Session, world_id: str, name: object, type_id: Optional[str]) -> str:
+    clean = _clean_label(name, "an event type")
+    key = normalize_surface(clean)
+    for other in db.exec(select(EventType).where(EventType.world_id == world_id)).all():
+        if other.id != type_id and normalize_surface(other.name) == key:
+            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
+    return clean
+
+
+def _clean_role(world_types: tuple[str, ...], role: RoleSpec) -> RoleSpec:
+    name = _clean_label(role.name, "a role")
+    if isinstance(role.entity_types, str) or not isinstance(role.entity_types, (list, tuple)):
+        raise ValueError(f"the role « {name} »'s entity types are a list")
+    types: list[str] = []
+    for entity_type in role.entity_types:
+        if entity_type not in world_types:
+            raise ValueError(f"unknown entity type {entity_type!r}")
+        if entity_type not in types:
+            types.append(entity_type)
+    if not types and not role.accepts_sorte:
+        raise ValueError(f"the role « {name} » accepts an entity type or a sorte")
+    return RoleSpec(name=name, entity_types=tuple(types), accepts_sorte=bool(role.accepts_sorte), id=role.id)
+
+
+def _clean_roles(world_types: tuple[str, ...], roles: tuple[RoleSpec, ...]) -> tuple[RoleSpec, ...]:
+    cleaned = tuple(_clean_role(world_types, role) for role in roles)
+    if not cleaned:
+        raise ValueError("an event type has one role or more")
+    if len(cleaned) > MAX_ROLES:
+        raise ValueError(f"an event type has at most {MAX_ROLES} roles")
+    keys = [normalize_surface(role.name) for role in cleaned]
+    for key, role in zip(keys, cleaned):
+        if keys.count(key) > 1:
+            raise ValueError(f"the role « {role.name} » is given twice")
+    return cleaned
+
+
+def _clean_scopes(roles: tuple[RoleSpec, ...], scopes: tuple[ScopeSpec, ...]) -> tuple[ScopeSpec, ...]:
+    by_key = {normalize_surface(role.name): role for role in roles}
+    seen: list[ScopeSpec] = []
+    for scope in scopes:
+        if scope.kind not in EVENT_SCOPE_KINDS:
+            raise ValueError(f"unknown scope {scope.kind!r}")
+        if scope.level not in EVENT_SCOPE_LEVELS or scope.level == "unaware":
+            raise ValueError(f"a scope's level is one the knower holds, not {scope.level!r}")
+        role = None
+        if scope.kind in ("rencontre", "faction"):
+            role = by_key.get(normalize_surface(scope.role or ""))
+            if role is None:
+                raise ValueError(f"a {scope.kind} scope names one of the type's roles")
+            if scope.kind == "rencontre" and not role.entity_types:
+                raise ValueError(f"the role « {role.name} » holds no entity: no one has met it")
+            if scope.kind == "faction" and "faction" not in role.entity_types:
+                raise ValueError(f"the role « {role.name} » accepts no faction")
+        elif scope.role is not None:
+            raise ValueError(f"a {scope.kind} scope names no role")
+        clean = ScopeSpec(kind=scope.kind, role=role.name if role else None, level=scope.level)
+        if any(s.kind == clean.kind and s.role == clean.role for s in seen):
+            raise ValueError(f"the scope {scope.kind!r} is given twice")
+        seen.append(clean)
+    return tuple(seen)
+
+
+def clean_event_type(db: Session, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None) -> EventTypeSpec:
+    """`spec` as it will be written; raises `ValueError` on any violation.
+    Writes nothing."""
+    if spec.domain not in EVENT_DOMAINS:
+        raise ValueError(f"unknown event domain {spec.domain!r}")
+    roles = _clean_roles(world_entity_types(db, world_id), tuple(spec.roles))
+    clean = EventTypeSpec(
+        name=_clean_type_name(db, world_id, spec.name, type_id), domain=spec.domain, roles=roles,
+        counts_quantity=bool(spec.counts_quantity), in_chronicle=bool(spec.in_chronicle),
+        participants_secret=bool(spec.participants_secret), scopes=_clean_scopes(roles, tuple(spec.scopes)),
+    )
+    if type_id is not None:
+        _clean_update(db, world_id, type_id, clean)
+    elif any(role.id for role in clean.roles):
+        raise ValueError("a new event type's roles carry no id")
+    return clean
+
+
+# --- what an existing type holds -------------------------------------------------
+
+def _role_rows(db: Session, type_id: str) -> list[EventTypeRole]:
+    return list(db.exec(select(EventTypeRole).where(EventTypeRole.type_id == type_id)
+                        .order_by(EventTypeRole.position, EventTypeRole.id)).all())
+
+
+def _type_leaves(db: Session, type_id: str) -> list[ConditionNode]:
+    return list(db.exec(select(ConditionNode).where(
+        ConditionNode.form == EVENT_FORM, ConditionNode.target_key == type_id)).all())
+
+
+def _role_in_condition(db: Session, role_id: str) -> bool:
+    leaf = db.exec(select(ConditionNode.id).where(
+        ConditionNode.form == EVENT_FORM, ConditionNode.value == role_id)).first()
+    found = db.exec(select(ConditionNodeFilter.id).where(ConditionNodeFilter.role_id == role_id)).first()
+    return leaf is not None or found is not None
+
+
+def _participants(db: Session, role_id: str) -> list[EventParticipant]:
+    return list(db.exec(select(EventParticipant).where(EventParticipant.role_id == role_id)).all())
+
+
+def _matched(rows: list[EventTypeRole], role: RoleSpec) -> Optional[EventTypeRole]:
+    if role.id:
+        return next((r for r in rows if r.id == role.id), None)
+    return next((r for r in rows if normalize_surface(r.name) == normalize_surface(role.name)), None)
+
+
+def _clean_kept_role(db: Session, row: EventTypeRole, role: RoleSpec) -> None:
+    for participant in _participants(db, row.id):
+        if participant.sorte_id and not role.accepts_sorte:
+            raise ValueError(f"the role « {row.name} » is held by a sorte: it keeps accepting one")
+        entity = db.get(Entity, participant.entity_id) if participant.entity_id else None
+        if entity is not None and entity.type not in role.entity_types:
+            raise ValueError(f"the role « {row.name} » is held by a {entity.type}: that type stays")
+
+
+def _clean_update(db: Session, world_id: str, type_id: str, clean: EventTypeSpec) -> None:
+    row = db.get(EventType, type_id)
+    if row is None or row.world_id != world_id:
+        raise ValueError(f"unknown event type {type_id!r}")
+    rows = _role_rows(db, type_id)
+    for role in clean.roles:
+        if role.id and _matched(rows, role) is None:
+            raise ValueError(f"unknown role {role.id!r}")
+    kept = {matched.id for role in clean.roles if (matched := _matched(rows, role)) is not None}
+    for row_role in rows:
+        if row_role.id in kept:
+            _clean_kept_role(db, row_role, next(r for r in clean.roles if _matched(rows, r) is row_role))
+        elif row_role.status == "active" and (_participants(db, row_role.id) or _role_in_condition(db, row_role.id)):
+            raise ValueError(f"the role « {row_role.name} » is in use: it stays")
+    if not clean.counts_quantity and db.exec(select(Event.id).where(
+            Event.type_id == type_id, Event.quantity.is_not(None))).first() is not None:
+        raise ValueError(f"« {row.name} » has events with a quantity: it keeps counting")
+
+
+# --- writing a type ---------------------------------------------------------------
+
+def _write_roles(db: Session, world_id: str, type_id: str, clean: EventTypeSpec) -> dict[str, str]:
+    """The roles, matched by id then name; returns name key -> role id."""
+    rows = _role_rows(db, type_id)
+    ids: dict[str, str] = {}
+    kept: set[str] = set()
+    for position, role in enumerate(clean.roles):
+        row = _matched(rows, role)
+        if row is None:
+            row = EventTypeRole(world_id=world_id, type_id=type_id, name=role.name)
+        row.name, row.position, row.accepts_sorte, row.status = role.name, position, role.accepts_sorte, "active"
+        db.add(row)
+        db.flush()
+        kept.add(row.id)
+        ids[normalize_surface(role.name)] = row.id
+        db.execute(text("DELETE FROM event_type_role_type WHERE role_id = :rid"), {"rid": row.id})
+        for entity_type in role.entity_types:
+            db.add(EventTypeRoleType(world_id=world_id, role_id=row.id, entity_type=entity_type))
+    for row in rows:
+        if row.id not in kept and row.status != "retired":
+            row.status = "retired"
+            db.add(row)
+    return ids
+
+
+def _write_scopes(db: Session, world_id: str, type_id: str, clean: EventTypeSpec, ids: dict[str, str]) -> None:
+    db.execute(text("DELETE FROM event_type_scope WHERE type_id = :tid"), {"tid": type_id})
+    for scope in clean.scopes:
+        role_id = ids[normalize_surface(scope.role)] if scope.role else None
+        db.add(EventTypeScope(world_id=world_id, type_id=type_id, scope_kind=scope.kind, role_id=role_id,
+                              level=scope.level))
+
+
+def write_event_type(
+    db: Session, *, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None,
+) -> EventType:
+    """Create (`type_id` None) or save one event type after
+    `clean_event_type`. Returns its row, flushed."""
+    clean = clean_event_type(db, world_id, spec, type_id)
+    if type_id is None:
+        row = EventType(world_id=world_id, name=clean.name)
+    else:
+        row = db.get(EventType, type_id)
+    row.name, row.domain = clean.name, clean.domain
+    row.counts_quantity, row.in_chronicle = clean.counts_quantity, clean.in_chronicle
+    row.participants_secret = clean.participants_secret
+    row.updated_at = datetime.now(UTC)
+    db.add(row)
+    db.flush()
+    ids = _write_roles(db, world_id, row.id, clean)
+    _write_scopes(db, world_id, row.id, clean, ids)
+    db.flush()
+    return row
+
+
+def set_event_type_status(db: Session, *, world_id: str, type_id: str, status: str) -> EventType:
+    """Retire or restore one type. Retiring is refused while a condition
+    names it. Its events keep it: history is sacred."""
+    if status not in EVENT_VOCAB_STATUSES:
+        raise ValueError(f"unknown status {status!r}")
+    row = db.get(EventType, type_id)
+    if row is None or row.world_id != world_id:
+        raise ValueError(f"unknown event type {type_id!r}")
+    if status == "retired" and _type_leaves(db, type_id):
+        raise ValueError(f"« {row.name} » is named by a condition: it cannot be retired")
+    row.status = status
+    row.updated_at = datetime.now(UTC)
+    db.add(row)
+    db.flush()
+    return row
+
+
+# --- sortes ---------------------------------------------------------------------
+
+def clean_sorte_name(db: Session, world_id: str, name: object, sorte_id: Optional[str] = None) -> str:
+    """A sorte's name as it will be written; `ValueError` when it is empty,
+    too long, or another sorte's of the world."""
+    clean = _clean_label(name, "a sorte")
+    key = normalize_surface(clean)
+    for other in db.exec(select(EventSorte).where(EventSorte.world_id == world_id)).all():
+        if other.id != sorte_id and normalize_surface(other.name) == key:
+            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
+    return clean
+
+
+def write_sorte(db: Session, *, world_id: str, name: str, sorte_id: Optional[str] = None) -> EventSorte:
+    """Create or rename one sorte. Returns its row, flushed."""
+    clean = clean_sorte_name(db, world_id, name, sorte_id)
+    if sorte_id is None:
+        row = EventSorte(world_id=world_id, name=clean)
+    else:
+        row = db.get(EventSorte, sorte_id)
+        if row is None or row.world_id != world_id:
+            raise ValueError(f"unknown sorte {sorte_id!r}")
+        row.name = clean
+    db.add(row)
+    db.flush()
+    return row
+
+
+def set_sorte_status(db: Session, *, world_id: str, sorte_id: str, status: str) -> EventSorte:
+    """Retire or restore one sorte; retiring is refused while a condition
+    names it."""
+    if status not in EVENT_VOCAB_STATUSES:
+        raise ValueError(f"unknown status {status!r}")
+    row = db.get(EventSorte, sorte_id)
+    if row is None or row.world_id != world_id:
+        raise ValueError(f"unknown sorte {sorte_id!r}")
+    named = db.exec(select(ConditionNodeFilter.id).where(ConditionNodeFilter.sorte_id == sorte_id)).first()
+    if status == "retired" and named is not None:
+        raise ValueError(f"« {row.name} » is named by a condition: it cannot be retired")
+    row.status = status
+    db.add(row)
+    db.flush()
+    return row
+
+
+# --- the type made from a domain (N1) -------------------------------------------
+
+def ensure_domain_type(db: Session, *, world_id: str, domain: Optional[str]) -> EventType:
+    """The world's type named after `domain` (an unknown or empty domain is
+    `other`), created with one role « Impliqué » accepting every entity type
+    of the world when the world has none of that name."""
+    domain = domain if domain in EVENT_DOMAINS else "other"
+    name = DOMAIN_LABELS_FR[domain]
+    key = normalize_surface(name)
+    for found in db.exec(select(EventType).where(EventType.world_id == world_id)).all():
+        if normalize_surface(found.name) == key:
+            return found
+    role = RoleSpec(name=DOMAIN_ROLE_FR, entity_types=world_entity_types(db, world_id))
+    return write_event_type(db, world_id=world_id, spec=EventTypeSpec(name=name, domain=domain, roles=(role,)))
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index ed3a747..19b55c0 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -79,6 +79,8 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "debt", "debt_term",
     "attribute_definition", "attribute_definition_type", "attribute_choice",
     "attribute_value", "attribute_change",
+    "event_type", "event_type_role", "event_type_role_type", "event_type_scope",
+    "event_sorte", "event_participant", "condition_node_filter",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 513b24c..7506215 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19227,6 +19227,60 @@ leaving a definition behind). Adding a missing label to an existing
 attribute from the interpreter: deferred (reactivation: the journal shows
 proposals refused because the existing attribute lacks the label).
 
+## WHAT HAPPENS IN A WORLD IS ONE OF ITS OWN EVENT TYPES (TICKET-0114) -- TYPES, ROLES, SORTES AND WHO LEARNS THEM, AS DATA; EVERY EARLIER EVENT TYPED BY ITS CATEGORY (BRIEF-0114-a, schema v2.24)
+
+**F1, B1, C1, D1 of the conditions series.** The `event` table stays the one
+journal; what it lacked was a vocabulary. A world names its own event types
+(`event_type`): « Tuer », « Repérer », « Pacte » -- each with a domain (one
+of the seven former `event.type` categories), whether it counts a quantity,
+whether it enters the chronicle the models read, whether its participants
+keep it secret by default (X1). A type has roles in order
+(`event_type_role`, C1), each accepting the entity types it names
+(`event_type_role_type`, the `attribute_definition_type` shape) and, when
+`accepts_sorte`, a sorte (`event_sorte`, D1): « 3 loups » needs no wolf to
+be an entity. `event_participant` (V1) says who took part in which role --
+an entity or a sorte, exactly one -- and replaces `event_entity` (dropped at
+v2.25): one way to say « took part ». The vocabulary grows by data, never by
+code.
+
+**K-a, W1.** Who learns an event besides its participants is declared by its
+type (`event_type_scope`): its place, everyone, the acquaintances of a
+role's entity, the faction a role names, each at a level. They become
+`fact_default` rows on the event's own fact when it is written
+(BRIEF-0114-C); no row is the participants only.
+
+**Nothing in use is taken away.** A role an event or a condition names, an
+entity type a participant holds, a sorte role's sorte, a quantity an event
+carries. A role dropped is retired, never deleted, and named again comes
+back; a type or a sorte is retired, refused while a condition names it.
+`_write_roles` / `_write_scopes` replace a role's types and a type's scopes
+whole, named in `single_canon_write.py`. Names are compared through
+`lore_resolve.normalize_surface`; `event_vocab.near_event_types` /
+`near_sortes` let the creator pick before a near duplicate.
+`writes/event_types.py` is the one writer, `event_vocab.py` the reader.
+
+**N1, O1, V1: the events written before.** `migrate_v2_24_event_journal.py`
+types each by its former category -- the world's type named after that
+domain (« Social », « Autre »), with one role « Impliqué » accepting every
+entity type of the world (`writes.event_types.ensure_domain_type` makes the
+same type at run time for what still arrives untyped) --, moves its
+`event_entity` rows into `event_participant`, and gives it its fact
+(`fact.event_id`, facet `evenement`): a `public` or `confirmed` event a
+`world` default at `knows`, a `secret` one none -- known by no one, as
+before. No knowledge row is written.
+
+**The language's side, ahead of its readers.** `condition` and
+`condition_draft` gain the role `failure` (H1), `condition_node` a `since`
+column (F1: `always`, `quest`, `step`) and `condition_node_filter` (a leaf's
+filters on the other roles), `agenda_step` a `started_at`: the `event` form
+of BRIEF-0114-D reads them. v2.24 moves `schema_meta` to v2.24 only: v2.25
+(BRIEF-0114-C) drops what this one keeps.
+
+**Rejected.** V2 (keep `event_entity` beside a roles table: two ways to say
+« took part »), N2 (an optional type: two sorts of events forever), C2 (fixed
+universal roles), D2 (an entity standing for a species: it pollutes the
+NPC lists and `name_index`), D3 (named entities only), W2 (three scopes).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index e18ed81..8e89818 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -9,6 +9,7 @@ skill_rank quest_offer quest_offer_step quest
 item_holding quest_offer_term quest_term quest_economy
 debt debt_term
 attribute_definition attribute_definition_type attribute_choice attribute_value attribute_change
+event_type event_type_role event_type_role_type event_type_scope event_sorte event_participant condition_node_filter
 
 [ALLOWED_SITES]
 # path::function                                              tables
@@ -74,6 +75,13 @@ src/world_engine/writes/attributes.py::_write_types             attribute_defini
 src/world_engine/writes/attributes.py::_write_choices           attribute_choice
 src/world_engine/writes/attributes.py::set_attribute_status     attribute_definition
 src/world_engine/writes/attributes.py::write_attribute_value    attribute_value attribute_change
+# TICKET-0114, BRIEF-0114-A: the event journal's vocabulary's one writer -- write_event_type creates or saves a type, _write_roles adds, renames and retires its roles (never a DELETE of a role) and replaces each role's entity types whole, _write_scopes replaces the type's scopes whole (the write_offer_terms full-replace shape), set_event_type_status retires or restores it, write_sorte creates or renames a sorte, set_sorte_status retires or restores it. Creator CRUD only (and, from BRIEF-0114-F/G, a confirmed interpreter or analyzer proposal, through the same functions).
+src/world_engine/writes/event_types.py::write_event_type       event_type
+src/world_engine/writes/event_types.py::_write_roles           event_type_role event_type_role_type
+src/world_engine/writes/event_types.py::_write_scopes          event_type_scope
+src/world_engine/writes/event_types.py::set_event_type_status  event_type
+src/world_engine/writes/event_types.py::write_sorte            event_sorte
+src/world_engine/writes/event_types.py::set_sorte_status       event_sorte
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index 18b1c2d..71cad02 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -342,7 +342,7 @@ def check_na2(engine) -> None:
 DRAFT_COLUMNS = ("id", "attempt_id", "world_ref", "world_name", "role", "instruction", "outcome", "retried",
                  "offer_ref", "saved_as_proposed", "payload", "model_calls", "created_at", "decided_at")
 DRAFT_CHECKS = {
-    "ck_condition_draft_role": "role IN ('eligibility','prerequisite','completion')",
+    "ck_condition_draft_role": "role IN ('eligibility','prerequisite','completion','failure')",
     "ck_condition_draft_outcome": "outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',"
                                   "'inserted','discarded','saved')",
     "ck_condition_draft_saved": "(offer_ref IS NOT NULL) = (outcome = 'saved') "
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index 3598872..c12ca89 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -43,7 +43,8 @@ CB5 -- the language writes nothing (static, AST). Neither `conditions.py`
    `flush`.
 
 CC1 -- storage (BRIEF-0111-C, import). `condition` and `condition_node`
-   carry exactly their contract's columns and CHECK texts; `CONDITION_ROLES`
+   carry exactly their contract's columns and CHECK texts (since v2.24,
+   TICKET-0114: the role `failure` and the `since` column); `CONDITION_ROLES`
    and `CONDITION_OPS` are the values those CHECKs quote, in order; no CHECK
    of either table names a form; `models` declares neither
    `AgendaStepRequirement` nor `QuestOfferRequirement`; the code's schema
@@ -464,9 +465,9 @@ def check_cb5() -> None:
 
 CONDITION_COLUMNS = ("id", "world_id", "role", "quest_offer_id", "quest_offer_step_id", "agenda_step_id", "created_at")
 NODE_COLUMNS = ("id", "world_id", "condition_id", "parent_id", "position", "op", "n", "form", "subject_role",
-                "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")
+                "subject_entity_id", "target_entity_id", "target_key", "threshold", "value", "since")
 CONDITION_CHECKS = {
-    "ck_condition_role": "role IN ('eligibility','prerequisite','completion')",
+    "ck_condition_role": "role IN ('eligibility','prerequisite','completion','failure')",
     "ck_condition_owner": "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + "
                           "(agenda_step_id IS NOT NULL) = 1",
     "ck_condition_owner_role": "(quest_offer_id IS NOT NULL) = (role = 'eligibility')",
@@ -476,10 +477,11 @@ NODE_CHECKS = {
     "ck_condition_node_leaf": "(op = 'leaf') = (form IS NOT NULL)",
     "ck_condition_node_connector": "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND "
                                    "target_entity_id IS NULL AND target_key IS NULL AND threshold IS NULL AND "
-                                   "value IS NULL)",
+                                   "value IS NULL AND since IS NULL)",
     "ck_condition_node_subject": "op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))",
     "ck_condition_node_role": "subject_role IS NULL OR subject_role IN ('doer','giver','contact')",
     "ck_condition_node_n": "(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)",
+    "ck_condition_node_since": "since IS NULL OR since IN ('always','quest','step')",
 }
 
 
diff --git a/tooling/verify/checks/event_journal.py b/tooling/verify/checks/event_journal.py
new file mode 100644
index 0000000..fbb5f00
--- /dev/null
+++ b/tooling/verify/checks/event_journal.py
@@ -0,0 +1,612 @@
+"""G1 check for TICKET-0114 -- the event journal's vocabulary: a world's event types, their roles, who learns them, its sortes.
+
+BRIEF-0114-A's rules. The journal's writer, readers and forms have their
+own checks (`event_writes.py`, `event_contexts.py`, `event_conditions.py`),
+so each stays inside the corpus's per-check time budget.
+
+EA1 -- storage (import). The seven new tables carry exactly their
+   contract's columns, CHECK names and index names; no column of theirs is
+   JSON; `EVENT_DOMAINS` is `tick_normalize._EVENT_TYPES` and the domain
+   CHECK's values, `EVENT_SCOPE_KINDS` and `EVENT_VOCAB_STATUSES` their
+   CHECKs', `EVENT_SCOPE_LEVELS` is `writes.knowledge.KNOWLEDGE_LEVEL_LADDER`;
+   `event` has `type_id` and `quantity`, `agenda_step` has `started_at`,
+   `condition_node` has `since` with `CONDITION_WINDOWS` its CHECK's values;
+   `CONDITION_ROLES` ends with `failure` and is the role CHECK's; every
+   `DOMAIN_LABELS_FR` key is a domain; the code's schema version is v2.24
+   or later.
+EA2 -- the type writer (fixture). `write_event_type` writes « Tuer » (two
+   roles, the second accepting a sorte; a `location` and a `rencontre`
+   scope) and `type_view` reads back its roles in order with their types,
+   its scopes with their role, its flags. Refused, each with no row
+   written: an empty name, another type's name (« tuer », « TUER »), an
+   unknown domain, no role, two roles of one name, a role accepting nothing,
+   an unknown entity type, an unknown scope, a `rencontre` scope on no role
+   or a sorte-only role, a `faction` scope on a role accepting no faction, a
+   `world` scope naming a role, a level `unaware`, an id on a new type's
+   role.
+EA3 -- in use (fixture). Once a participant fills a role: dropping that
+   role, dropping the entity type it holds, or a sorte role's sorte, is
+   refused; an unused role dropped is retired, its row kept, and named
+   again comes back; a type whose event has a quantity cannot stop
+   counting; a type is retired and restored.
+EA4 -- sortes (fixture). `write_sorte` writes « Loup », refuses « loup »
+   and an empty name; `near_sortes` finds « Loup » for « loups »,
+   `near_event_types` finds « Tuer » for « tuers », and nothing for
+   « Pacte »; `world_sortes` / `world_event_types` leave a retired one out
+   unless asked.
+EA5 -- the type made from a domain (fixture). `ensure_domain_type` makes
+   « Social » with one role « Impliqué » accepting every entity type of
+   the world (an active runtime type included, a retired one not); a
+   second call, and a call for « mystery », find « Social » again and make
+   « Mystère »; an unknown domain is `other`.
+EA6 -- migration `scripts/migrate_v2_24_event_journal.py`, on a v2.23
+   database (the four changed tables in their v2.23 DDL, frozen below)
+   holding a `public` event with two `event_entity` rows, a `secret` one
+   with none, a condition and two nodes: at v2.22 it refuses and changes
+   nothing; at v2.23 it types each event by its category (« Social »,
+   « Autre »), moves the links into `event_participant` in the role
+   « Impliqué », gives each event one `evenement` fact -- a `world` default
+   at `knows` for the public one, none for the secret -- keeps the
+   condition and nodes, adds the columns and tables, and sets
+   `schema_meta` to v2.24; a second run writes nothing.
+EA7 -- the reader writes nothing (static, AST). `event_vocab.py` calls no
+   `add`, `commit`, `delete`, `execute` or `flush`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import re
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION_V2_24 = ROOT / "scripts" / "migrate_v2_24_event_journal.py"
+
+FAILURES: list[str] = []
+
+TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
+    "event_type": (
+        ("id", "world_id", "name", "domain", "counts_quantity", "in_chronicle", "participants_secret", "status",
+         "created_at", "updated_at"),
+        ("ck_event_type_domain", "ck_event_type_status"),
+        ("idx_event_type_name",),
+    ),
+    "event_type_role": (
+        ("id", "world_id", "type_id", "name", "position", "accepts_sorte", "status"),
+        ("ck_event_type_role_status",),
+        ("idx_event_type_role_name",),
+    ),
+    "event_type_role_type": (
+        ("id", "world_id", "role_id", "entity_type"),
+        (),
+        ("idx_event_type_role_type_unique",),
+    ),
+    "event_type_scope": (
+        ("id", "world_id", "type_id", "scope_kind", "role_id", "level"),
+        ("ck_event_type_scope_kind", "ck_event_type_scope_role", "ck_event_type_scope_level"),
+        ("idx_event_type_scope_type",),
+    ),
+    "event_sorte": (
+        ("id", "world_id", "name", "status", "created_at"),
+        ("ck_event_sorte_status",),
+        ("idx_event_sorte_name",),
+    ),
+    "event_participant": (
+        ("id", "world_id", "event_id", "role_id", "entity_id", "sorte_id", "position"),
+        ("ck_event_participant_one",),
+        ("idx_event_participant_event", "idx_event_participant_entity", "idx_event_participant_unique_entity",
+         "idx_event_participant_unique_sorte"),
+    ),
+    "condition_node_filter": (
+        ("id", "world_id", "node_id", "role_id", "entity_id", "sorte_id", "position"),
+        ("ck_condition_node_filter_one",),
+        ("idx_condition_node_filter_node",),
+    ),
+}
+
+# The four tables v2.24 changes, as v2.23 declared them (frozen: EA6 builds
+# the database the migration was written for).
+V2_23_DDL: tuple[str, ...] = (
+    "CREATE TABLE event (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, session_id VARCHAR, batch_id VARCHAR, "
+    "title VARCHAR NOT NULL, description VARCHAR, type VARCHAR, knowledge_status VARCHAR DEFAULT 'secret' NOT NULL, "
+    "location_id VARCHAR, has_magic_impact BOOLEAN DEFAULT 0 NOT NULL, consequences JSON, occurred_at DATETIME, "
+    "recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
+    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(session_id) REFERENCES session (id), "
+    "FOREIGN KEY(batch_id) REFERENCES batch (id), FOREIGN KEY(location_id) REFERENCES entity (id))",
+    "CREATE INDEX idx_event_world ON event (world_id)",
+    "CREATE TABLE agenda_step (id VARCHAR NOT NULL, agenda_id VARCHAR NOT NULL, step_order INTEGER NOT NULL, "
+    "objective VARCHAR NOT NULL, status VARCHAR DEFAULT 'pending' NOT NULL, outcome VARCHAR, visibility_trace VARCHAR, "
+    "cost INTEGER, domain VARCHAR, created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
+    "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, change_history JSON DEFAULT '[]' NOT NULL, "
+    "PRIMARY KEY (id), CONSTRAINT ck_agenda_step_status CHECK (status IN ('pending','active','completed','failed')), "
+    "CONSTRAINT ck_agenda_step_cost CHECK (cost IS NULL OR cost BETWEEN 1 AND 4), "
+    "FOREIGN KEY(agenda_id) REFERENCES agenda (id))",
+    "CREATE INDEX idx_agenda_step_agenda ON agenda_step (agenda_id, step_order)",
+    "CREATE UNIQUE INDEX idx_agenda_step_one_active ON agenda_step (agenda_id) WHERE status = 'active'",
+    "CREATE TABLE condition (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, role VARCHAR NOT NULL, "
+    "quest_offer_id VARCHAR, quest_offer_step_id VARCHAR, agenda_step_id VARCHAR, "
+    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
+    "CONSTRAINT ck_condition_role CHECK (role IN ('eligibility','prerequisite','completion')), "
+    "CONSTRAINT ck_condition_owner CHECK ((quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) "
+    "+ (agenda_step_id IS NOT NULL) = 1), "
+    "CONSTRAINT ck_condition_owner_role CHECK ((quest_offer_id IS NOT NULL) = (role = 'eligibility')), "
+    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(quest_offer_id) REFERENCES quest_offer (id), "
+    "FOREIGN KEY(quest_offer_step_id) REFERENCES quest_offer_step (id), "
+    "FOREIGN KEY(agenda_step_id) REFERENCES agenda_step (id))",
+    "CREATE UNIQUE INDEX idx_condition_agenda_step ON condition (agenda_step_id, role)",
+    "CREATE UNIQUE INDEX idx_condition_offer_step ON condition (quest_offer_step_id, role)",
+    "CREATE UNIQUE INDEX idx_condition_offer ON condition (quest_offer_id, role)",
+    "CREATE TABLE condition_node (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, condition_id VARCHAR NOT NULL, "
+    "parent_id VARCHAR, position INTEGER DEFAULT 0 NOT NULL, op VARCHAR NOT NULL, n INTEGER, form VARCHAR, "
+    "subject_role VARCHAR, subject_entity_id VARCHAR, target_entity_id VARCHAR, target_key VARCHAR, "
+    "threshold INTEGER, value VARCHAR, PRIMARY KEY (id), "
+    "CONSTRAINT ck_condition_node_op CHECK (op IN ('all','any','not','at_least','leaf')), "
+    "CONSTRAINT ck_condition_node_leaf CHECK ((op = 'leaf') = (form IS NOT NULL)), "
+    "CONSTRAINT ck_condition_node_connector CHECK (op = 'leaf' OR (subject_role IS NULL AND subject_entity_id "
+    "IS NULL AND target_entity_id IS NULL AND target_key IS NULL AND threshold IS NULL AND value IS NULL)), "
+    "CONSTRAINT ck_condition_node_subject CHECK (op <> 'leaf' OR ((subject_role IS NULL) <> "
+    "(subject_entity_id IS NULL))), "
+    "CONSTRAINT ck_condition_node_role CHECK (subject_role IS NULL OR subject_role IN ('doer','giver','contact')), "
+    "CONSTRAINT ck_condition_node_n CHECK ((op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)), "
+    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(condition_id) REFERENCES condition (id), "
+    "FOREIGN KEY(parent_id) REFERENCES condition_node (id), FOREIGN KEY(subject_entity_id) REFERENCES entity (id), "
+    "FOREIGN KEY(target_entity_id) REFERENCES entity (id))",
+    "CREATE INDEX idx_condition_node_condition ON condition_node (condition_id, parent_id, position)",
+)
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+# --- EA1 -------------------------------------------------------------------------
+
+def _quoted(sql: str) -> tuple[str, ...]:
+    return tuple(re.findall(r"'([^']+)'", sql))
+
+
+def _ck(table: str, name: str) -> str:
+    from sqlalchemy import CheckConstraint
+    from sqlmodel import SQLModel
+
+    return next(str(c.sqltext) for c in SQLModel.metadata.tables[table].constraints
+                if isinstance(c, CheckConstraint) and c.name == name)
+
+
+def _ea1_tables() -> None:
+    from sqlalchemy import JSON, CheckConstraint
+    from sqlmodel import SQLModel
+
+    seen = 0
+    for name, (columns, checks, indexes) in TABLES.items():
+        table = SQLModel.metadata.tables.get(name)
+        if table is None:
+            fail(f"EA1: table {name} is not declared")
+            continue
+        seen += 1
+        if tuple(table.c.keys()) != columns:
+            fail(f"EA1: {name} columns are {tuple(table.c.keys())}")
+        found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
+        if found != tuple(sorted(checks)):
+            fail(f"EA1: {name} CHECKs are {found}")
+        if tuple(sorted(i.name for i in table.indexes)) != tuple(sorted(indexes)):
+            fail(f"EA1: {name} indexes are {sorted(i.name for i in table.indexes)}")
+        for column in table.c:
+            if isinstance(column.type, JSON):
+                fail(f"EA1: {name}.{column.name} is JSON")
+    if seen != len(TABLES):
+        fail(f"EA1: {seen} of {len(TABLES)} tables declared")
+
+
+def check_ea1() -> None:
+    from sqlmodel import SQLModel
+
+    from world_engine import models
+    from world_engine.event_vocab import DOMAIN_LABELS_FR
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.tick_normalize import _EVENT_TYPES
+    from world_engine.writes.knowledge import KNOWLEDGE_LEVEL_LADDER
+
+    _ea1_tables()
+    meta = SQLModel.metadata.tables
+    pairs = (
+        (models.EVENT_DOMAINS, _ck("event_type", "ck_event_type_domain")),
+        (models.EVENT_VOCAB_STATUSES, _ck("event_type", "ck_event_type_status")),
+        (models.EVENT_VOCAB_STATUSES, _ck("event_type_role", "ck_event_type_role_status")),
+        (models.EVENT_VOCAB_STATUSES, _ck("event_sorte", "ck_event_sorte_status")),
+        (models.EVENT_SCOPE_KINDS, _ck("event_type_scope", "ck_event_type_scope_kind")),
+        (models.EVENT_SCOPE_LEVELS, _ck("event_type_scope", "ck_event_type_scope_level")),
+        (models.CONDITION_ROLES, _ck("condition", "ck_condition_role")),
+        (models.CONDITION_WINDOWS, _ck("condition_node", "ck_condition_node_since")),
+    )
+    for values, sql in pairs:
+        if tuple(values) != _quoted(sql):
+            fail(f"EA1: {values} is not the CHECK's {_quoted(sql)}")
+    if set(models.EVENT_DOMAINS) != set(_EVENT_TYPES):
+        fail(f"EA1: EVENT_DOMAINS {models.EVENT_DOMAINS} is not tick_normalize._EVENT_TYPES {sorted(_EVENT_TYPES)}")
+    if tuple(models.EVENT_SCOPE_LEVELS) != tuple(KNOWLEDGE_LEVEL_LADDER):
+        fail("EA1: EVENT_SCOPE_LEVELS is not KNOWLEDGE_LEVEL_LADDER")
+    if models.CONDITION_ROLES[-1] != "failure":
+        fail(f"EA1: CONDITION_ROLES is {models.CONDITION_ROLES}")
+    if set(DOMAIN_LABELS_FR) != set(models.EVENT_DOMAINS):
+        fail(f"EA1: DOMAIN_LABELS_FR names {sorted(DOMAIN_LABELS_FR)}")
+    for table, column in (("event", "type_id"), ("event", "quantity"), ("agenda_step", "started_at"),
+                          ("condition_node", "since")):
+        if column not in meta[table].c:
+            fail(f"EA1: {table}.{column} is not declared")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 24):
+        fail(f"EA1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- fixture -----------------------------------------------------------------------
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, EntityType, Faction, Location, World
+
+    with Session(engine) as db:
+        world = World(name="Journal", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
+                                ("foret", "location", "Forêt"), ("guilde", "faction", "Guilde")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
+            elif kind == "location":
+                db.add(Location(id=entity.id))
+            else:
+                db.add(Faction(id=entity.id))
+        for slug, status in (("navire", "active"), ("epave", "retired")):
+            db.add(EntityType(world_id=world.id, name=slug, slug=slug, physical_table=f"ext_{slug}",
+                              status=status))
+        db.commit()
+    return ids
+
+
+def _counts(db) -> tuple[int, ...]:
+    from sqlmodel import func, select
+
+    from world_engine import models
+
+    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
+        models.EventType, models.EventTypeRole, models.EventTypeRoleType, models.EventTypeScope,
+        models.EventSorte))
+
+
+def _refused(db, label: str, rule: str, call) -> None:
+    before = _counts(db)
+    try:
+        call()
+    except ValueError:
+        db.rollback()
+        if _counts(db) != before:
+            fail(f"{rule}: {label} was refused after writing a row")
+        return
+    db.rollback()
+    fail(f"{rule}: {label} was accepted")
+
+
+def _role(name, types=("character",), sorte=False, role_id=None):
+    from world_engine.writes.event_types import RoleSpec
+
+    return RoleSpec(name=name, entity_types=tuple(types), accepts_sorte=sorte, id=role_id)
+
+
+def _tuer(**fields):
+    from world_engine.writes.event_types import EventTypeSpec, ScopeSpec
+
+    base = dict(name="Tuer", domain="military", counts_quantity=True,
+                roles=(_role("tueur"), _role("victime", ("character",), sorte=True)),
+                scopes=(ScopeSpec("location", level="rumor"), ScopeSpec("rencontre", role="victime")))
+    base.update(fields)
+    return EventTypeSpec(**base)
+
+
+def check_ea2(engine, ids: dict) -> str:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.writes.event_types import EventTypeSpec, ScopeSpec, write_event_type
+
+    world = ids["world"]
+    with Session(engine) as db:
+        tuer = write_event_type(db, world_id=world, spec=_tuer()).id
+        db.commit()
+        view = type_view(db, tuer)
+        roles = [(r.name, r.position, r.entity_types, r.accepts_sorte, r.status) for r in view.roles]
+        if roles != [("tueur", 0, ("character",), False, "active"), ("victime", 1, ("character",), True, "active")]:
+            fail(f"EA2: the roles read back as {roles}")
+        scopes = sorted((s.kind, view.role(s.role_id).name if s.role_id else None, s.level) for s in view.scopes)
+        if scopes != [("location", None, "rumor"), ("rencontre", "victime", "knows")]:
+            fail(f"EA2: the scopes read back as {scopes}")
+        if (view.domain, view.counts_quantity, view.in_chronicle, view.participants_secret) != \
+                ("military", True, True, False):
+            fail(f"EA2: the flags read back as {view}")
+        cases = {
+            "an empty name": _tuer(name="  "),
+            "another type's name (tuer)": _tuer(name="tuer"),
+            "another type's name (TUER)": _tuer(name="TUER"),
+            "an unknown domain": _tuer(name="A", domain="weather"),
+            "no role": _tuer(name="A", roles=(), scopes=()),
+            "two roles of one name": _tuer(name="A", roles=(_role("x"), _role("X")), scopes=()),
+            "a role accepting nothing": _tuer(name="A", roles=(_role("x", ()),), scopes=()),
+            "an unknown entity type": _tuer(name="A", roles=(_role("x", ("dragon",)),), scopes=()),
+            "an unknown scope": _tuer(name="A", scopes=(ScopeSpec("planet"),)),
+            "a rencontre scope on no role": _tuer(name="A", scopes=(ScopeSpec("rencontre"),)),
+            "a rencontre scope on a sorte-only role": _tuer(
+                name="A", roles=(_role("x", (), sorte=True),), scopes=(ScopeSpec("rencontre", role="x"),)),
+            "a faction scope on a role accepting no faction": _tuer(
+                name="A", scopes=(ScopeSpec("faction", role="tueur"),)),
+            "a world scope naming a role": _tuer(name="A", scopes=(ScopeSpec("world", role="tueur"),)),
+            "a level unaware": _tuer(name="A", scopes=(ScopeSpec("world", level="unaware"),)),
+            "an id on a new type's role": _tuer(name="A", roles=(_role("x", role_id="r1"),), scopes=()),
+        }
+        for label, spec in cases.items():
+            _refused(db, label, "EA2", lambda spec=spec: write_event_type(db, world_id=world, spec=spec))
+        if not isinstance(EventTypeSpec(name="x"), EventTypeSpec):
+            fail("EA2: EventTypeSpec does not build")
+    return tuer
+
+
+def check_ea3(engine, ids: dict, tuer: str) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Event, EventParticipant
+    from world_engine.writes.event_types import set_event_type_status, write_event_type, write_sorte
+
+    world = ids["world"]
+    with Session(engine) as db:
+        view = type_view(db, tuer)
+        tueur, victime = view.roles[0].id, view.roles[1].id
+        loup = write_sorte(db, world_id=world, name="Bête").id
+        event = Event(world_id=world, title="Brakk tue trois bêtes", type_id=tuer, quantity=3)
+        db.add(event)
+        db.flush()
+        db.add(EventParticipant(world_id=world, event_id=event.id, role_id=tueur, entity_id=ids["brakk"]))
+        db.add(EventParticipant(world_id=world, event_id=event.id, role_id=victime, sorte_id=loup))
+        db.commit()
+        kept = (_role("tueur", role_id=tueur), _role("victime", ("character",), True, role_id=victime))
+        for label, spec in {
+            "dropping a role an event holds": _tuer(roles=(kept[1],), scopes=()),
+            "dropping the entity type a participant holds": _tuer(
+                roles=(_role("tueur", ("location",), role_id=tueur), kept[1]), scopes=()),
+            "dropping a sorte role's sorte": _tuer(
+                roles=(kept[0], _role("victime", ("character",), False, role_id=victime)), scopes=()),
+            "a type with a quantity that stops counting": _tuer(roles=kept, scopes=(), counts_quantity=False),
+        }.items():
+            _refused(db, label, "EA3", lambda spec=spec: write_event_type(db, world_id=world, spec=spec,
+                                                                          type_id=tuer))
+        write_event_type(db, world_id=world, spec=_tuer(roles=kept + (_role("témoin"),), scopes=()), type_id=tuer)
+        write_event_type(db, world_id=world, spec=_tuer(roles=kept, scopes=()), type_id=tuer)
+        db.commit()
+        temoin = [r for r in type_view(db, tuer).roles if r.name == "témoin"]
+        if len(temoin) != 1 or temoin[0].status != "retired":
+            fail(f"EA3: an unused role dropped reads {temoin}, not one retired row")
+        write_event_type(db, world_id=world, spec=_tuer(roles=kept + (_role("Témoin"),), scopes=()), type_id=tuer)
+        db.commit()
+        back = [r for r in type_view(db, tuer).roles if r.name == "Témoin"]
+        if len(back) != 1 or back[0].status != "active" or back[0].id != temoin[0].id:
+            fail(f"EA3: a retired role named again reads {back}")
+        retired = set_event_type_status(db, world_id=world, type_id=tuer, status="retired").status
+        restored = set_event_type_status(db, world_id=world, type_id=tuer, status="active").status
+        db.commit()
+        if (retired, restored) != ("retired", "active"):
+            fail(f"EA3: a type with no condition was {retired} then {restored}")
+
+
+def check_ea4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import near_event_types, near_sortes, world_event_types, world_sortes
+    from world_engine.writes.event_types import set_sorte_status, write_sorte
+
+    world = ids["world"]
+    with Session(engine) as db:
+        loup = write_sorte(db, world_id=world, name="Loup").id
+        db.commit()
+        for label, name in (("« loup »", "loup"), ("an empty name", " ")):
+            _refused(db, label, "EA4", lambda name=name: write_sorte(db, world_id=world, name=name))
+        if [n.name for n in near_sortes(db, world, "loups")][:1] != ["Loup"]:
+            fail(f"EA4: near_sortes finds {near_sortes(db, world, 'loups')} for « loups »")
+        if [n.name for n in near_event_types(db, world, "tuers")][:1] != ["Tuer"]:
+            fail(f"EA4: near_event_types finds {near_event_types(db, world, 'tuers')} for « tuers »")
+        if near_event_types(db, world, "Pacte"):
+            fail(f"EA4: near_event_types finds {near_event_types(db, world, 'Pacte')} for « Pacte »")
+        set_sorte_status(db, world_id=world, sorte_id=loup, status="retired")
+        db.commit()
+        if any(s.id == loup for s in world_sortes(db, world)) or \
+                not any(s.id == loup for s in world_sortes(db, world, include_retired=True)):
+            fail("EA4: world_sortes does not leave the retired « Loup » out unless asked")
+        if not world_event_types(db, world):
+            fail("EA4: world_event_types lists nothing")
+
+
+def check_ea5(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import DOMAIN_ROLE_FR, type_view
+    from world_engine.writes.event_types import ensure_domain_type
+
+    world = ids["world"]
+    with Session(engine) as db:
+        social = ensure_domain_type(db, world_id=world, domain="social")
+        again = ensure_domain_type(db, world_id=world, domain="social")
+        mystere = ensure_domain_type(db, world_id=world, domain="mystery")
+        other = ensure_domain_type(db, world_id=world, domain="weather")
+        db.commit()
+        view = type_view(db, social.id)
+        if social.id != again.id or view.name != "Social" or view.domain != "social":
+            fail(f"EA5: ensure_domain_type gave {view} then {again.id}")
+        if [(r.name, r.entity_types) for r in view.roles] != [
+                (DOMAIN_ROLE_FR, ("character", "faction", "item", "location", "navire"))]:
+            fail(f"EA5: « Social »'s roles are {[(r.name, r.entity_types) for r in view.roles]}")
+        if (mystere.name, other.name, other.domain) != ("Mystère", "Autre", "other"):
+            fail(f"EA5: mystery made {mystere.name}, an unknown domain {other.name}/{other.domain}")
+
+
+# --- EA6 -------------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION_V2_24)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _v2_23_db() -> str:
+    """A database the migration was written for: every table of the code
+    but the seven new ones and the four it changes, those in v2.23 DDL."""
+    from sqlalchemy import create_engine
+    from sqlmodel import SQLModel
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    skipped = set(TABLES) | {"event", "agenda_step", "condition", "condition_node", "event_entity"}
+    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n not in skipped])
+    eng.dispose()
+    with sqlite3.connect(db_path) as conn:
+        for statement in V2_23_DDL:
+            conn.execute(statement)
+        conn.execute("CREATE TABLE event_entity (id VARCHAR NOT NULL, event_id VARCHAR NOT NULL, entity_id VARCHAR "
+                     "NOT NULL, PRIMARY KEY (id), FOREIGN KEY(event_id) REFERENCES event (id), "
+                     "FOREIGN KEY(entity_id) REFERENCES entity (id))")
+        conn.executescript("""
+            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.22', '2026-10-01');
+            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
+            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
+              VALUES ('a', 'w', 'character', 'A', 'active', '2026-10-01', '2026-10-01'),
+                     ('b', 'w', 'location', 'B', 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO event (id, world_id, title, description, type, knowledge_status, recorded_at)
+              VALUES ('ev1', 'w', 'La fête', 'On danse.', 'social', 'public', '2026-10-01'),
+                     ('ev2', 'w', 'Le pacte', NULL, 'weather', 'secret', '2026-10-02');
+            INSERT INTO event_entity (id, event_id, entity_id) VALUES ('l1', 'ev1', 'a'), ('l2', 'ev1', 'b');
+            INSERT INTO agenda (id, world_id, owner_entity_id, title, status, created_at, updated_at)
+              VALUES ('ag', 'w', 'a', 'T', 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO agenda_step (id, agenda_id, step_order, objective) VALUES ('s1', 'ag', 1, 'o');
+            INSERT INTO condition (id, world_id, role, agenda_step_id) VALUES ('c1', 'w', 'prerequisite', 's1');
+            INSERT INTO condition_node (id, world_id, condition_id, position, op) VALUES ('n1', 'w', 'c1', 0, 'all');
+            INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op, form, subject_role,
+              target_key) VALUES ('n2', 'w', 'c1', 'n1', 0, 'leaf', 'knowledge', 'doer', 'k');
+        """)
+    return db_path
+
+
+def _snapshot(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        def rows(sql):
+            try:
+                return sorted(conn.execute(sql).fetchall())
+            except sqlite3.OperationalError:
+                return None
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "types": rows("SELECT e.title, t.name FROM event e JOIN event_type t ON t.id = e.type_id"),
+            "participants": rows("SELECT p.event_id, p.entity_id, r.name FROM event_participant p "
+                                 "JOIN event_type_role r ON r.id = p.role_id"),
+            "facts": rows("SELECT f.event_id, f.facet, f.content, (SELECT group_concat(scope_type || ':' || level) "
+                          "FROM fact_default d WHERE d.fact_id = f.id) FROM fact f WHERE f.event_id IS NOT NULL"),
+            "nodes": rows("SELECT id, form FROM condition_node"),
+            "conditions": rows("SELECT id, role FROM condition"),
+            "started": rows("SELECT started_at FROM agenda_step"),
+        }
+
+
+def check_ea6() -> None:
+    db_path = _v2_23_db()
+    before = _snapshot(db_path)
+    refused = _run_migration(db_path)
+    if refused.returncode == 0 or _snapshot(db_path) != before:
+        fail(f"EA6: v2.22 was not refused untouched (exit {refused.returncode})")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.23' WHERE id = 1")
+    result = _run_migration(db_path)
+    after = _snapshot(db_path)
+    want = {
+        "version": "v2.24",
+        "types": [("La fête", "Social"), ("Le pacte", "Autre")],
+        "participants": [("ev1", "a", "Impliqué"), ("ev1", "b", "Impliqué")],
+        "facts": [("ev1", "evenement", "La fête — On danse.", "world:knows"), ("ev2", "evenement", "Le pacte", None)],
+        "nodes": [("n1", None), ("n2", "knowledge")],
+        "conditions": [("c1", "prerequisite")],
+        "started": [(None,)],
+    }
+    if result.returncode != 0 or after != want:
+        fail(f"EA6: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
+        fail(f"EA6: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+# --- EA7 -------------------------------------------------------------------------
+
+def check_ea7() -> None:
+    path = SRC / "event_vocab.py"
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
+    if not calls:
+        fail("EA7: event_vocab.py makes no attribute call at all")
+    for call in calls:
+        if call.func.attr in ("add", "commit", "delete", "execute", "flush"):
+            fail(f"EA7: event_vocab.py calls .{call.func.attr} on line {call.lineno}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    state: dict = {}
+
+    def ea2() -> None:
+        state["tuer"] = check_ea2(engine, ids)
+
+    rules = (
+        ("EA1", check_ea1), ("EA2", ea2), ("EA3", lambda: check_ea3(engine, ids, state["tuer"])),
+        ("EA4", lambda: check_ea4(engine, ids)), ("EA5", lambda: check_ea5(engine, ids)),
+        ("EA6", check_ea6), ("EA7", check_ea7),
+    )
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_journal -- v2.24 keeps a world's event types with their roles, the entity types each "
+          "accepts, who learns them, and its sortes; nothing in use is taken away; every earlier event is "
+          "typed by its category, its links become participants and it gets its fact")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index 42cd5ab..dd49b48 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -83,12 +83,14 @@ single-row correction): `write_npc_prices`, `write_world_laws`,
 (TICKET-0111: one owner's condition and its nodes) and
 `write_offer_terms` (TICKET-0109, BRIEF-0109-B: an offer's terms) and
 `writes/attributes.py::_write_types` (TICKET-0113, BRIEF-0113-A: an
-attribute definition's entity types) each
+attribute definition's entity types) and `writes/event_types.py::_write_roles`
+/ `_write_scopes` (TICKET-0114, BRIEF-0114-A: a role's entity types, an
+event type's scopes -- never a role itself, retired instead) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
-location / offer / definition) then re-insert the submitted set, in one
+location / offer / definition / role / type) then re-insert the submitted set, in one
 transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`,
 `create_world`, `set_location_geometry`, `set_location_doors`,
-`save_offer`, the attribute definition routes;
+`save_offer`, the attribute definition routes, the event type routes;
 `location_subculture` and
 its writer were dropped in schema v2.06, TICKET-0091, BRIEF-0091-I), never
 reachable from any AI or play path. These
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 79b9205..8100aa6 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -126,6 +126,18 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
               "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
     ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t"}),
     ("event_entity", {"id": "eve-{w}", "event_id": "ev-{w}", "entity_id": "{w}-char"}),
+    # TICKET-0114 (BRIEF-0114-A): a type, its role and scope, a sorte, a
+    # participant, and a filter on the condition leaf above.
+    ("event_type", {"id": "et-{w}", "world_id": "{w}", "name": "Tuer"}),
+    ("event_type_role", {"id": "etr-{w}", "world_id": "{w}", "type_id": "et-{w}", "name": "tueur"}),
+    ("event_type_role_type", {"id": "etrt-{w}", "world_id": "{w}", "role_id": "etr-{w}",
+                              "entity_type": "character"}),
+    ("event_type_scope", {"id": "ets-{w}", "world_id": "{w}", "type_id": "et-{w}", "scope_kind": "world"}),
+    ("event_sorte", {"id": "eso-{w}", "world_id": "{w}", "name": "loup"}),
+    ("event_participant", {"id": "ep-{w}", "world_id": "{w}", "event_id": "ev-{w}", "role_id": "etr-{w}",
+                           "entity_id": "{w}-char"}),
+    ("condition_node_filter", {"id": "cnf-{w}", "world_id": "{w}", "node_id": "cnn-{w}", "role_id": "etr-{w}",
+                               "sorte_id": "eso-{w}"}),
     ("fact", {"id": "fa-{w}", "world_id": "{w}", "content": "c",
               "created_by": "creator_crud"}),
     ("fact_default", {"id": "fd-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 806a3b7..26fc791 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,25 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.24** — TICKET-0114, BRIEF-0114-A: the event journal's vocabulary.
+  `event_type` (a world's type of event: its name, its domain -- one of the
+  seven former categories --, whether it counts a quantity, enters the
+  chronicle, is kept secret by its participants by default; retired never
+  deleted), `event_type_role` (its roles, in order; a role may accept a
+  sorte), `event_type_role_type` (the entity types a role accepts),
+  `event_type_scope` (who learns an event of it: its place, everyone, the
+  acquaintances or the faction of a role, at a level), `event_sorte` (a
+  world's anonymous kinds), `event_participant` (who took part, in which
+  role: an entity or a sorte) and `condition_node_filter` (an `event`
+  leaf's filters on the other roles). `event` gains `type_id` and
+  `quantity`, `agenda_step` gains `started_at`; `condition` and
+  `condition_draft` are rebuilt with the role `failure`, `condition_node`
+  with a `since` column.
+  `migrate_v2_24_event_journal.py` types every event by its former category
+  (the world's type named after it, one role « Impliqué »), moves its
+  `event_entity` rows into `event_participant`, gives it its fact (a
+  `world` default at `knows` when it was `public` or `confirmed`), refuses
+  a database older than v2.23 and moves `schema_meta` to v2.24.
 - **v2.23** — TICKET-0113, BRIEF-0113-B: no table change. The condition
   form `vital_status` is retired: its leaves become `attribute` leaves
   reading the system attribute `sys:vital_status` (`target_key`), subject
diff --git a/world-engine-schema.md b/world-engine-schema.md
index c10a9ff..f3f01df 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.23
+Current schema version: v2.24
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1253,7 +1253,7 @@ CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_a
 The condition interpreter's journal (schema v2.21, TICKET-0112, BRIEF-0112-B,
 decision IH1): one row per proposal of the interpreter -- the creator's
 `instruction` for one condition of a quest offer (`role`: `eligibility`,
-`prerequisite` or `completion`), grouped by `attempt_id`, the id the editor
+`prerequisite`, `completion` or, since v2.24, `failure`), grouped by `attempt_id`, the id the editor
 holds for one use. `payload` is what the proposal started from and became
 (`current`, `pending`, `mentions`, `bindings`, `proposed`, `notes`,
 `errors`); `model_calls` is every model exchange of it (prompt version,
@@ -1293,7 +1293,7 @@ CREATE TABLE condition_draft (
   created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
   decided_at         DATETIME,
   CONSTRAINT ck_condition_draft_role CHECK (
-    role IN ('eligibility','prerequisite','completion')),
+    role IN ('eligibility','prerequisite','completion','failure')),   -- failure: v2.24
   CONSTRAINT ck_condition_draft_outcome CHECK (
     outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',
                 'inserted','discarded','saved')),
@@ -1619,10 +1619,20 @@ CREATE TABLE event (
   has_magic_impact      BOOLEAN DEFAULT FALSE,
   consequences          JSON,     -- changes applied to the world
   occurred_at           DATETIME,
-  recorded_at           DATETIME DEFAULT CURRENT_TIMESTAMP
+  recorded_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
+  type_id               TEXT REFERENCES event_type(id),   -- v2.24
+  quantity              INTEGER                           -- v2.24
 );
 ```
 
+`type_id` / `quantity` (v2.24, TICKET-0114, BRIEF-0114-A; F1, N1, D1): the
+world's event type this event is one of (`event_type`), and how many when
+its type counts (« 3 loups »). The v2.24 migration typed every earlier event
+by its former category -- the world's type named after that domain, one
+role « Impliqué » -- moved its `event_entity` rows into `event_participant`,
+and gave it its fact (`fact.event_id`, facet `evenement`): a `public` or
+`confirmed` event a `world` default at `knows`, a `secret` one none (O1).
+
 Two producers write this table (TICKET-0017/BRIEF-0017-a, no schema
 change), both through `_apply_mutation`'s `event_creation` branch ->
 `write_event` (the single canon-write site): a scope-level `world_tick`
@@ -1663,6 +1673,151 @@ CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity(event_id, entity_id)
 
 -----
 
+### `event_type`
+
+One type of event of one world (v2.24, TICKET-0114, BRIEF-0114-A; F1, B1,
+N1). « Tuer », « Repérer », « Pacte »: the creator names what can happen in
+her world, the vocabulary grows by data, never by code. `domain` is one of
+the seven former `event.type` categories (F1). `counts_quantity`: an event
+of it carries a quantity (D1). `in_chronicle`: its events enter the
+chronicle the models read (Q1). `participants_secret`: by default, its
+participants keep it secret (X1, each participant's own knowledge row
+says so). Retired, never deleted; retiring is refused while a condition
+names it. Its name is no other type's of its world (compared case- and
+accent-blind by the writer, case-blind by the index). Written only by
+`writes/event_types.py`.
+
+```sql
+CREATE TABLE event_type (
+  id                   TEXT PRIMARY KEY,
+  world_id             TEXT NOT NULL REFERENCES world(id),
+  name                 TEXT NOT NULL,
+  domain               TEXT NOT NULL DEFAULT 'other'
+                         CHECK (domain IN ('political','magical','criminal','military','social','mystery','other')),
+  counts_quantity      BOOLEAN NOT NULL DEFAULT 0,
+  in_chronicle         BOOLEAN NOT NULL DEFAULT 1,
+  participants_secret  BOOLEAN NOT NULL DEFAULT 0,
+  status               TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
+  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
+);
+CREATE UNIQUE INDEX idx_event_type_name ON event_type(world_id, name COLLATE NOCASE);
+```
+
+-----
+
+### `event_type_role`
+
+The roles of an event type (C1), in `position` order -- « tueur »,
+« victime ». `accepts_sorte`: a sorte may fill it (D1). A role dropped from
+the type is retired, never deleted, and refused while an event or a
+condition names it.
+
+```sql
+CREATE TABLE event_type_role (
+  id             TEXT PRIMARY KEY,
+  world_id       TEXT NOT NULL REFERENCES world(id),
+  type_id        TEXT NOT NULL REFERENCES event_type(id),
+  name           TEXT NOT NULL,
+  position       INTEGER NOT NULL DEFAULT 0,
+  accepts_sorte  BOOLEAN NOT NULL DEFAULT 0,
+  status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired'))
+);
+CREATE UNIQUE INDEX idx_event_type_role_name ON event_type_role(type_id, name COLLATE NOCASE);
+```
+
+-----
+
+### `event_type_role_type`
+
+The entity types a role accepts (C1; the `attribute_definition_type`
+shape): a built-in type or a runtime type's slug. Replaced whole by the
+writer, which refuses to drop a type a participant holds.
+
+```sql
+CREATE TABLE event_type_role_type (
+  id           TEXT PRIMARY KEY,
+  world_id     TEXT NOT NULL REFERENCES world(id),
+  role_id      TEXT NOT NULL REFERENCES event_type_role(id),
+  entity_type  TEXT NOT NULL
+);
+CREATE UNIQUE INDEX idx_event_type_role_type_unique ON event_type_role_type(role_id, entity_type);
+```
+
+-----
+
+### `event_type_scope`
+
+Who learns an event of the type (K-a, W1), besides its participants: its
+place (`location`, learned on visiting it), everyone (`world`), the
+acquaintances of a role's entity (`rencontre`), the faction a role names
+(`faction`) -- each at a knowledge `level`. No row: the participants only.
+When an event is written, each row becomes a `fact_default` on its fact,
+which the event may change.
+
+```sql
+CREATE TABLE event_type_scope (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  type_id     TEXT NOT NULL REFERENCES event_type(id),
+  scope_kind  TEXT NOT NULL CHECK (scope_kind IN ('location','world','rencontre','faction')),
+  role_id     TEXT REFERENCES event_type_role(id),
+  level       TEXT NOT NULL DEFAULT 'knows'
+                CHECK (level IN ('unaware','rumor','suspicious','partial','knows','fully_understands')),
+  CHECK ((scope_kind IN ('rencontre','faction')) = (role_id IS NOT NULL))
+);
+CREATE INDEX idx_event_type_scope_type ON event_type_scope(type_id);
+```
+
+-----
+
+### `event_sorte`
+
+An anonymous kind of a world (D1) -- « loup », « bandit » -- that fills a
+role accepting sortes, with the event's quantity: no wolf needs to be an
+entity to be counted. Retired, never deleted; retiring is refused while a
+condition names it.
+
+```sql
+CREATE TABLE event_sorte (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  name        TEXT NOT NULL,
+  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
+  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
+);
+CREATE UNIQUE INDEX idx_event_sorte_name ON event_sorte(world_id, name COLLATE NOCASE);
+```
+
+-----
+
+### `event_participant`
+
+Who took part in one event, in which role (V1): an entity or a sorte,
+exactly one. It replaces `event_entity` (dropped at v2.25). Written only by
+`writes/events.py`.
+
+```sql
+CREATE TABLE event_participant (
+  id         TEXT PRIMARY KEY,
+  world_id   TEXT NOT NULL REFERENCES world(id),
+  event_id   TEXT NOT NULL REFERENCES event(id),
+  role_id    TEXT NOT NULL REFERENCES event_type_role(id),
+  entity_id  TEXT REFERENCES entity(id),
+  sorte_id   TEXT REFERENCES event_sorte(id),
+  position   INTEGER NOT NULL DEFAULT 0,
+  CHECK ((entity_id IS NOT NULL) + (sorte_id IS NOT NULL) = 1)
+);
+CREATE INDEX idx_event_participant_event ON event_participant(event_id, position);
+CREATE INDEX idx_event_participant_entity ON event_participant(entity_id);
+CREATE UNIQUE INDEX idx_event_participant_unique_entity
+  ON event_participant(event_id, role_id, entity_id) WHERE entity_id IS NOT NULL;
+CREATE UNIQUE INDEX idx_event_participant_unique_sorte
+  ON event_participant(event_id, role_id, sorte_id) WHERE sorte_id IS NOT NULL;
+```
+
+-----
+
 ### `artifact`
 
 Magical or historically significant objects.
@@ -2250,7 +2405,10 @@ CREATE INDEX idx_agenda_owner_status ON agenda(owner_entity_id, status);
 Ordered step of an `agenda`, schema v1.72, TICKET-0018/BRIEF-0018-a. The
 model never addresses a step directly — it names the agenda by TITLE; the
 active step is always derived in code (this table's partial unique index
-guarantees at most one). Advancement (`complete` -> next step active / agenda
+guarantees at most one). `started_at` (v2.24, TICKET-0114, F1): when the
+step became active, the « depuis le début de l'étape » window of an `event`
+leaf; NULL on a step activated before v2.24, whose quest's `accepted_at`
+stands in. Advancement (`complete` -> next step active / agenda
 completed; `fail` -> whole agenda failed) is CODE, at apply.
 
 `cost`/`domain` (schema v1.94, TICKET-0075, BRIEF-0075-b): day-plan budget
@@ -2275,7 +2433,8 @@ CREATE TABLE agenda_step (
   domain            TEXT,
   created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
   updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
-  change_history    JSON DEFAULT '[]'
+  change_history    JSON DEFAULT '[]',
+  started_at        DATETIME          -- v2.24
 );
 CREATE INDEX idx_agenda_step_agenda ON agenda_step(agenda_id, step_order);
 -- STRUCTURAL invariant (RECON-0018 F2): at most ONE active step per agenda,
@@ -2294,7 +2453,9 @@ v2.20, TICKET-0111, BRIEF-0111-C (decisions A1, I1, O-a). It replaced
 `agenda_step_requirement` (v1.94) and `quest_offer_requirement` (v2.17): the
 migration turned each owner's rows into one tree, `all` of them. At most one
 condition per owner and role. `completion` (M1) is shown in Journée and in
-« Déclarer accomplie », never acted on by the engine. Curated plan metadata,
+« Déclarer accomplie », never acted on by the engine; `failure` (v2.24,
+TICKET-0114, H1) likewise -- when the step has failed, shown, never acting.
+Curated plan metadata,
 the requirement rows' family: no `change_history`; a save replaces a
 condition whole. Written only by `writes.conditions.write_condition` (and
 `delete_offer_conditions` before an offer is saved); read by
@@ -2304,7 +2465,7 @@ condition whole. Written only by `writes.conditions.write_condition` (and
 CREATE TABLE condition (
   id                   TEXT PRIMARY KEY,
   world_id             TEXT NOT NULL REFERENCES world(id),
-  role                 TEXT NOT NULL CHECK (role IN ('eligibility','prerequisite','completion')),
+  role                 TEXT NOT NULL CHECK (role IN ('eligibility','prerequisite','completion','failure')),
   quest_offer_id       TEXT REFERENCES quest_offer(id),
   quest_offer_step_id  TEXT REFERENCES quest_offer_step(id),
   agenda_step_id       TEXT REFERENCES agenda_step(id),
@@ -2361,15 +2522,43 @@ CREATE TABLE condition_node (
   target_key         TEXT,
   threshold          INTEGER,
   value              TEXT,
+  since              TEXT CHECK (since IS NULL OR since IN ('always','quest','step')),   -- v2.24
   CHECK ((op = 'leaf') = (form IS NOT NULL)),
   CHECK (op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND target_entity_id IS NULL
-                         AND target_key IS NULL AND threshold IS NULL AND value IS NULL)),
+                         AND target_key IS NULL AND threshold IS NULL AND value IS NULL AND since IS NULL)),
   CHECK (op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))),
   CHECK ((op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1))
 );
 CREATE INDEX idx_condition_node_condition ON condition_node(condition_id, parent_id, position);
 ```
 
+`since` (v2.24, TICKET-0114, F1): since when a leaf counts what happened --
+`always`, since its quest was accepted (`quest`), since its step became
+active (`step`); NULL on every leaf that counts nothing.
+
+-----
+
+### `condition_node_filter`
+
+A leaf's filters on the other roles of its event type (v2.24, TICKET-0114,
+BRIEF-0114-A): « un loup », « à Ombreval » -- one row per role, filled by an
+entity or a sorte, exactly one. Rows, never JSON (INV-20); written only by
+`writes.conditions.write_condition`.
+
+```sql
+CREATE TABLE condition_node_filter (
+  id         TEXT PRIMARY KEY,
+  world_id   TEXT NOT NULL REFERENCES world(id),
+  node_id    TEXT NOT NULL REFERENCES condition_node(id),
+  role_id    TEXT NOT NULL REFERENCES event_type_role(id),
+  entity_id  TEXT REFERENCES entity(id),
+  sorte_id   TEXT REFERENCES event_sorte(id),
+  position   INTEGER NOT NULL DEFAULT 0,
+  CHECK ((entity_id IS NOT NULL) + (sorte_id IS NOT NULL) = 1)
+);
+CREATE INDEX idx_condition_node_filter_node ON condition_node_filter(node_id);
+```
+
 -----
 
 ### `quest_offer`
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Any writer of `event` or `event_participant` (C), any reader (D), the `event` form (E), the routes and the tab (B).
- Dropping `event.type`, `knowledge_status`, `consequences`, `occurred_at`, `has_magic_impact`, `event_entity` -- v2.25, brief D.
- A type's effects on states (M-c), Lore declaring events (U1) -- TICKET-0119.
- The calendar (`occurred_at`'s successor) -- TICKET-0120.
- Every later brief of this lot: BRIEF-0114-B, BRIEF-0114-C, BRIEF-0114-D, BRIEF-0114-E, BRIEF-0114-F, BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-08 / INV-12 (`single_canon_write.py`): the new writers enter the policy, and the full-replace deletes are named in its docstring -- never a silent hard delete. INV-60: the boot guard moves to v2.24 with the migration; the app refuses an unmigrated database. INV-20: no new column is JSON. INV-07: the migration writes no knowledge row, so no PC can be made secret here.

## Decision rights

STOP:
- The migration, run on a copy of a v2.23 database, changes a row it does not name (its post-check fails).
- A table of C-01 needs a column or a CHECK the contract does not list.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/conditions.py` -> `PASS`.
- `python tooling/verify/checks/condition_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/world_cascade.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/schema_version_agreement.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (151 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EA1** -- `models/canon_event.py`: `name="ck_event_type_status")` -> `name="ck_event_type_state")`
  - **EA2** -- `writes/event_types.py` `_clean_roles`: `if keys.count(key) > 1:` -> `if False:`
  - **EA3** -- `writes/event_types.py` `_clean_update`: `raise ValueError(f"the role « {row_role.name} » is in use: it stays")` -> `pass`
  - **EA4** -- `writes/event_types.py` `clean_sorte_name`: its duplicate-name `raise ValueError(...)` -> `pass`
  - **EA5** -- `writes/event_types.py` `ensure_domain_type`: `if normalize_surface(found.name) == key:` -> `if False:`
  - **EA6** -- `migrate_v2_24_event_journal.py`: `if status in ("public", "confirmed"):` -> `if status in ("confirmed",):`
  - **EA7** -- `event_vocab.py` `world_sortes`: add `db.flush()` before its `return`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

Schema changelog v2.24 and `world-engine-schema.md` (in the diff); ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
