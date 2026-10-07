# BRIEF 0108-A — "v2.17: quest tables, eight requirement forms, four of them the model's"

Lot: LOT-0108-quest-offers.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (`main` at `4b06dde` or later, schema v2.16).

- `src/world_engine/day_plan.py:75` -> `REQUIREMENT_TYPES` is the four-form tuple `("knowledge", "relation_gte", "resource", "location_reachable")`.
- `src/world_engine/day_plan.py:166-189` -> `_eval_relation_gte` selects the pair's row in either order with `.first()`, no type filter.
- `src/world_engine/day_plan.py:414-420` -> `_validate_requirement` refuses a type not in `REQUIREMENT_TYPES`.
- `src/world_engine/models/config.py:127-136` -> `ck_agenda_step_requirement_type` and `_shape` name four forms.
- `src/world_engine/writes/goals_agendas.py:588-624` -> `_clean_requirement` with the literal groups `("relation_gte", "location_reachable")` and `("relation_gte", "resource")`.
- `src/world_engine/day_resolve.py:260-265` -> `_BLOCKED_DETAIL_FR` has four keys.
- `src/world_engine/skill_access.py:45-58` -> `_base_row`, `_definition_row`.
- `src/world_engine/writes/worlds.py:66-78` -> `_DIRECT_WORLD_SCOPED_DELETES` ends with `"world_law",`.
- `src/world_engine/schema_version.py:15` -> `"v2.16"`.
- `tooling/verify/checks/day_plan.py:190` -> `EXPECTED_REQUIREMENT_TYPES` is the four forms.
- `tooling/verify/checks/json_ui_boundary.py:55` -> `"AgendaStep.change_history",`.
- `scripts/migrate_v2_15_skill_ranks.py:133` -> `def _rebuild(cursor, model, insert_columns: str, select_columns: str)`.
- No table named `quest_offer`, `quest_offer_step`, `quest_offer_requirement` or `quest` exists in `src/world_engine/models/`.

## Facts carried

### R-05 — the requirement table's CHECKs [M]
Opened: `src/world_engine/models/config.py:124-149` (the declaring file).
Finding: `ck_agenda_step_requirement_type` lists four forms;
`ck_agenda_step_requirement_shape` has three groups (entity target, key
target, threshold); unique index on `(step_id, type, target_entity_id,
target_key)`.
Consequence: widening needs a table rebuild -- SQLite cannot alter a CHECK.

### R-06 — the evaluators and the model's parser share one tuple [M]
Opened: `src/world_engine/day_plan.py:75` (`REQUIREMENT_TYPES`), `:144-221`
(the four evaluators, `_EVALUATORS`), `:256-276` (`evaluate_requirements`),
`:414-432` (`_validate_requirement`: the model's requirement is checked
against `REQUIREMENT_TYPES`).
Finding: widening `REQUIREMENT_TYPES` alone would let the day-plan model
emit a creator form.
Consequence: `MODEL_REQUIREMENT_TYPES` (the four) for the parser.

### R-07 — `relation_gte` reads either direction, structural rows included [M]
Opened: `day_plan.py:166-189`; `src/world_engine/models/canon_knowledge.py:
23-41` (`idx_relation_oriented_social`: one social row per ORIENTED pair,
`type NOT IN ('connects_to','borde','controls')`);
`src/world_engine/relation_orientation.py:1-40` (`entity_a` feels toward
`entity_b`; `is_social`); `src/world_engine/writes/relations.py:105-118`
(`_find_perceived_relation`: `entity_a = perceiver`, `entity_b = target`,
social only -- the reader of the NPC-goal prerequisite judge).
Finding: the evaluator takes the first row of the pair in either order,
with no type filter.
Consequence: B-dir -- the row `entity_a = target`, `entity_b = character`,
`is_social`, 0 when absent: `_find_perceived_relation`'s query restated
(importing it would cycle: `writes/goals_agendas.py` imports `day_plan`).
Model-emitted day plans read it too.

### R-08 — `resource` is money [M]
Opened: `day_plan.py:191-200`; `models/canon.py:454-473` (`Ledger`: signed
`amount`, no currency column).
Finding: the evaluator sums the character's whole ledger; `target_key` is
not read.
Consequence: `resource` stays the name and means money, its key a label;
an object is never a `resource` (objects held in quantity: TICKET-0109).

### R-09 — the requirement writer [M]
Opened: `goals_agendas.py:588-637` (`_clean_requirement`: entity forms
`("relation_gte", "location_reachable")` hard-coded, key otherwise, threshold
forms `("relation_gte", "resource")`; an entity target must exist in the
world; a key target is not resolved), `:46` (imports `REQUIREMENT_TYPES`).
Consequence: its three groups come from `day_plan`; key targets are
resolved (a fact, a skill, an offer of the world); `faction_member` must
name a faction; the two model-emitted entity forms keep exactly the check
they had, so no day plan is refused for anything new.

### R-10 — the player-facing reason is fail-closed [M]
Opened: `src/world_engine/day_resolve.py:255-275` (`_BLOCKED_DETAIL_FR`,
`requirement_detail_fr` raises on an unknown type);
`tooling/verify/checks/day_narration.py:651-682` (R15: its keys equal
`REQUIREMENT_TYPES`).
Consequence: four French lines, each naming its target through
`required_label`.

### R-11 — the other readers of requirement rows filter by type [M]
Opened: `routes/day.py:274-310` (`_account_rendezvous` reads `relation_gte`
targets), `src/world_engine/day_mutations.py:145-175` (reads `knowledge`
requirements), `:225-270` (reads `knowledge` verdicts), `day_resolve.py:
384-386` (keeps `character` and `location` refs only).
Finding: each selects a named type; none fails on another.
Consequence: the new forms pass them untouched. Report only: a `has_met`
target is not named as a rendezvous.

### R-12 — encounters [M]
Opened: `src/world_engine/models/ephemeral.py:160-196` (`rencontre`: one row
per UNORDERED pair, `entity_lo_id < entity_hi_id`, unique).
Consequence: `has_met` reads the sorted pair.

### R-13 — memberships [M]
Opened: `src/world_engine/models/canon_faction.py:83-129` (`FactionMembership`:
active iff `left_at IS NULL`; `is_secret`, whose comment asks every
non-creator READER to filter it out); `src/world_engine/tick_context.py:
315-330` (an NPC's own briefing reads its secret memberships, marked).
Consequence: `faction_member` counts the character's own secret membership
-- the gate is about him, the `tick_context` self-briefing precedent.

### R-14 — ranks [M]
Opened: `models/canon.py:655-690` (`Skill`: `rank` 0..5,
`skill_definition_id` NULL on a base row); `src/world_engine/skill_access.
py:45-58` (`_base_row`, `_definition_row`); `src/world_engine/skill_ranks.
py:32` (`DEFAULT_RANK: int = 1`, Initié).
Consequence: `skill_access.held_rank` -- a base domain without a row is
`DEFAULT_RANK`, a definition without a row is not held.

### R-22 — the world cascade names every world-scoped table [M]
Opened: `src/world_engine/writes/worlds.py:13-25`, `:66-78`
(`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/checks/world_cascade.py:
1-35` (W1 coverage, W3 one `_FIXTURE` row per cascaded table).

### R-23 — canon writes, and the full-replace deletes [M]
Opened: `tooling/verify/canon_write_policy.txt` (`[CANON_TABLES]`;
`[ALLOWED_SITES]` is function-scoped, not interprocedural);
`tooling/verify/checks/single_canon_write.py:46-90` (the hard-delete law
and its full-replace list); `src/world_engine/writes/config.py:76-106`
(`write_npc_prices`: `DELETE FROM` scoped to its parent, then insert).

### R-24 — the migration's shape [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py:126-180` (`_rebuild` and
`_create_from_model` on a raw connection, both PRAGMAs before `BEGIN`);
`scripts/migrate_v1_95_parked_plans.py:60-100` (why raw);
`scripts/migrate_v2_16_npc_skills.py:68` and `:148-170` (the foreign-key
post-check judges only the tables the migration writes, AMENDMENT-0107-01);
`src/world_engine/schema_version.py:15`; `tooling/verify/checks/
schema_partition.py` (the changelog's newest entry is the header version).
`agenda_step_requirement`'s v2.16 DDL was dumped from `main` (embedded in
`quests.py`).

### R-25 — JSON columns and decision headers [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-56` (every JSON column
named in `JSON_COLUMN_ALLOWLIST`); `tooling/verify/checks/decisions_index.
py:15-17` (strict header: the brief letter is lower case).

## Contracts

### C-01 — the requirement vocabulary (family contract)
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B, BRIEF-0108-C
Written before its members; re-read after the last (`quest_completed`).

In `src/world_engine/day_plan.py`, literal tuples, in this order:

```python
REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable",
                     "has_met", "faction_member", "skill_rank_gte", "quest_completed")
MODEL_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
ENTITY_TARGET_TYPES = ("relation_gte", "location_reachable", "has_met", "faction_member")
KEY_TARGET_TYPES = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
THRESHOLD_TYPES = ("relation_gte", "resource", "skill_rank_gte")
```

The two CHECK texts, carried byte for byte by `agenda_step_requirement`
(`ck_agenda_step_requirement_type`, `_shape`) and `quest_offer_requirement`
(`ck_quest_offer_requirement_type`, `_shape`):

```
type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')
(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
```

Members (every row has all six columns):

| form | target | threshold | met iff | blocked reason (French) | `_clean_requirement` refuses | model |
|---|---|---|---|---|---|---|
| `knowledge` | key: fact id | -- | the character holds a row on the fact | unchanged | a fact not of the world | yes |
| `relation_gte` | entity | >= 1 | the target's social row toward the character >= threshold (0 if none) | unchanged | an entity not of the world | yes |
| `resource` | key: a label | >= 1 | the character's ledger balance >= threshold | unchanged | -- (label) | yes |
| `location_reachable` | entity | -- | the target is in the character's `connects_to` component | unchanged | an entity not of the world | yes |
| `has_met` | entity | -- | a `rencontre` row of the sorted pair | « il n'a encore jamais rencontré {name} » | an entity not of the world | no |
| `faction_member` | entity: a faction | -- | an active membership, secret included | « il n'appartient pas à {name} » | not a faction of the world | no |
| `skill_rank_gte` | key: base domain or definition id | 1-5 | `held_rank` >= threshold | « sa maîtrise de « {label} » ne suffit pas encore » | an unknown skill; threshold 0 or > 5 | no |
| `quest_completed` | key: quest offer id | -- | a quest of the character from that offer whose agenda is `completed` | « il doit d'abord mener à bien « {title} » » | an offer not of the world | no |

`Verdict.required_label` carries the target's name for `relation_gte` and
the four new forms.

### C-02 — evaluation
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B
Signature: `day_plan.evaluate_specs(requirements: tuple[RequirementSpec, ...],
character: Character, db: Session) -> list[Verdict]`; `evaluate_requirements
(step, character, db)` returns `evaluate_specs(step.requirements, character,
db)`. `skill_access.held_rank(db, character_id, skill_key) -> Optional[int]`.
Return shape: one `Verdict(type, met, current, required, reason,
required_label)` per requirement, in order.
Error and empty cases: an unknown type raises `ValueError`; an empty tuple
returns `[]`; `_day_reachable_ids` runs at most once, only for a
`location_reachable`.

### C-06 — schema v2.17
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B
`src/world_engine/models/quests.py`, canon:
- `quest_offer(id, world_id, giver_entity_id -> entity, title, summary,
  repeatable BOOLEAN DEFAULT 0, status DEFAULT 'open' CHECK IN ('open',
  'closed'), created_at, updated_at, change_history JSON)`, index on
  `world_id`; `QUEST_OFFER_STATUSES = ("open", "closed")`.
- `quest_offer_step(id, world_id, offer_id -> quest_offer, step_order,
  objective, cost CHECK BETWEEN 1 AND 4, domain)`, unique `(offer_id,
  step_order)`.
- `quest_offer_requirement(id, world_id, offer_id -> quest_offer, step_id ->
  quest_offer_step NULL, type, target_entity_id -> entity, target_key,
  threshold)`, C-01's two CHECKs, index on `offer_id`.
- `quest(id, world_id, offer_id -> quest_offer, character_id -> entity,
  agenda_id -> agenda, accepted_at)`, unique `agenda_id`, indexes on
  `character_id`, `offer_id`.
- `agenda_step_requirement`: C-01's two CHECKs.

## Context

Nia locked A1 (a quest is an open plan born `paused`), the v1 requirement forms of B (eight, one language for eligibility and steps), B-dir (the NPC's appreciation of the PC) and H1, L1, M1. This brief lays the schema (v2.17) and the vocabulary the two next briefs write and read: four quest tables, the widened CHECKs, four evaluators, and a separate tuple so the day-plan model keeps emitting only its four forms.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/models/quests.py` (`QuestOffer`, `QuestOfferStep`, `QuestOfferRequirement`, `Quest`, `QUEST_OFFER_STATUSES` -- C-06) and exports them from `models/__init__.py`;
   - widens `agenda_step_requirement`'s two CHECKs in `models/config.py` to C-01's texts;
   - in `day_plan.py`: `REQUIREMENT_TYPES` (eight), `MODEL_REQUIREMENT_TYPES`, `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES` (C-01); `_eval_relation_gte` reads the target's social row toward the character (R-07); `_eval_has_met`, `_eval_faction_member`, `_eval_skill_rank_gte`, `_eval_quest_completed`; `evaluate_specs`, with `evaluate_requirements` delegating to it (C-02); `_validate_requirement` checks `MODEL_REQUIREMENT_TYPES`; `_eval_resource` documented as money;
   - adds `skill_access.held_rank` (C-02);
   - adds four lines to `day_resolve._BLOCKED_DETAIL_FR` (C-01);
   - rewrites `writes/goals_agendas._clean_requirement` on `day_plan`'s groups, resolving every key target and checking `faction_member` names a faction (R-09);
   - adds the four tables to `writes/worlds._DIRECT_WORLD_SCOPED_DELETES`, to `[CANON_TABLES]`, and one fixture row each to `world_cascade.py`;
   - allow-lists `QuestOffer.change_history` in `json_ui_boundary.py`;
   - updates `day_plan.py` (the check)'s `EXPECTED_REQUIREMENT_TYPES` and shape pairs;
   - bumps the version to v2.17 (constant, schema doc header), documents the four tables and the eight forms, adds the v2.17 changelog entry;
   - creates `scripts/migrate_v2_17_quests.py` (the v2.15/v2.16 migrations' shape: env guard, refusal below v2.16, the raw-connection rebuild, the tables created from their models, post-checks scoped to the five tables it writes, `schema_meta` convergence);
   - creates `tooling/verify/checks/quests.py` with QA1-QA3;
   - appends the decision entry above the `---` / `*Co-built…*` footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(quests): quest offers and eight requirement forms, schema v2.17 (BRIEF-0108-a)`.

````diff
diff --git a/scripts/migrate_v2_17_quests.py b/scripts/migrate_v2_17_quests.py
new file mode 100644
index 0000000..ded26fb
--- /dev/null
+++ b/scripts/migrate_v2_17_quests.py
@@ -0,0 +1,208 @@
+"""Migration v2.17 — quest offers and the widened requirement vocabulary
+(TICKET-0108, BRIEF-0108-A, decisions A1, B, B-dir, H1, L1, M1).
+
+1. Rebuild. `agenda_step_requirement` is rebuilt from the model so its two
+   CHECKs carry the four new forms (`has_met`, `faction_member`,
+   `skill_rank_gte`, `quest_completed`). SQLite cannot alter a CHECK: the
+   table is renamed, recreated from `models.AgendaStepRequirement`, its rows
+   copied column for column, the old table dropped -- the
+   `migrate_v2_15_skill_ranks.py` raw-connection rebuild, verbatim in shape.
+   The new CHECKs accept every row the old ones accepted.
+2. Create. `quest_offer`, `quest_offer_step`, `quest_offer_requirement` and
+   `quest`, from their models, when missing.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.16 (the migrations are sequential), before any change.
+
+Idempotent: the rebuild runs only while the stored CHECK lacks
+`'quest_completed'`; each table is created only when missing.
+
+Post-checks, before `schema_meta` converges: the stored CHECK names the four
+new forms; the `agenda_step_requirement` row count is unchanged; the four
+new tables exist; `PRAGMA foreign_key_check` is empty on the five tables
+this migration writes. A dangling reference elsewhere in the database
+predates it: it is listed, never a reason to stop (AMENDMENT-0107-01).
+
+Run from the project root:
+
+    python scripts/migrate_v2_17_quests.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_17_quests.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.16"
+_REQUIREMENT_COLUMNS = "id, world_id, step_id, type, target_entity_id, target_key, threshold"
+_NEW_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
+# Parents first: an offer before its steps, its steps before its requirements.
+_NEW_MODELS = (models.QuestOffer, models.QuestOfferStep, models.QuestOfferRequirement, models.Quest)
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("agenda_step_requirement",) + tuple(m.__tablename__ for m in _NEW_MODELS)
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
+            f"Migration v2.17 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _requirement_table_sql() -> str:
+    with engine.connect() as conn:
+        row = conn.execute(text(
+            "SELECT sql FROM sqlite_master WHERE type='table' AND name='agenda_step_requirement'"
+        )).first()
+    return row[0] if row is not None else ""
+
+
+def _row_count(table: str) -> int:
+    with engine.connect() as conn:
+        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _rebuild_requirements(cursor) -> None:
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agenda_step_requirement' "
+        "AND sql IS NOT NULL"
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute("ALTER TABLE agenda_step_requirement RENAME TO agenda_step_requirement_old")
+    _create_from_model(cursor, models.AgendaStepRequirement)
+    cursor.execute(
+        f"INSERT INTO agenda_step_requirement ({_REQUIREMENT_COLUMNS}) "
+        f"SELECT {_REQUIREMENT_COLUMNS} FROM agenda_step_requirement_old"
+    )
+    cursor.execute("DROP TABLE agenda_step_requirement_old")
+
+
+def _apply_ddl() -> list[str]:
+    """One raw transaction (see `migrate_v1_95_parked_plans.py`'s docstring:
+    the PRAGMAs must land before any transaction exists): the rebuild when
+    the CHECK lacks the new forms, then each missing quest table."""
+    rebuild = "'quest_completed'" not in _requirement_table_sql()
+    existing = set(inspect(engine).get_table_names())
+    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
+    if not rebuild and not missing:
+        return []
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        if rebuild:
+            _rebuild_requirements(cursor)
+            applied.append("agenda_step_requirement rebuilt")
+        for model in missing:
+            _create_from_model(cursor, model)
+            applied.append(f"{model.__tablename__} created")
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
+def _post_checks(requirements_before: int) -> None:
+    stored = _requirement_table_sql()
+    absent = [form for form in _NEW_FORMS if f"'{form}'" not in stored]
+    if absent:
+        raise SystemExit(f"Migration v2.17 aborted, post-check failed: the CHECK lacks {absent}.")
+    after = _row_count("agenda_step_requirement")
+    if after != requirements_before:
+        raise SystemExit(
+            "Migration v2.17 aborted, post-check failed: agenda_step_requirement row count "
+            f"changed ({requirements_before} -> {after})."
+        )
+    tables = set(inspect(engine).get_table_names())
+    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
+    if missing:
+        raise SystemExit(f"Migration v2.17 aborted, post-check failed: tables missing {missing}.")
+    with engine.connect() as conn:
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    if dangling:
+        raise SystemExit(f"Migration v2.17 aborted, post-check failed: foreign_key_check {dangling}.")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: CHECK widened; {after} requirement row(s) preserved; four quest tables in place.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.17 — quest offers, quests, eight requirement forms")
+    _refuse()
+    before = _row_count("agenda_step_requirement")
+    applied = _apply_ddl()
+    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.17 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 94dae4a..848e75b 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -3,7 +3,7 @@ plan-emission-and-budget step; decisions F1, M1, P2, S1, H1).
 
 One model call (`emit_plan`) turns a player's day declaration into a full,
 ordered step list — the model PROPOSES. Everything downstream is Python: the
-four named requirement evaluators judge each step's preconditions, and
+named requirement evaluators judge each step's preconditions, and
 `budget_cut` (pure, sequential, not a knapsack) decides how much of the plan
 happens today against `DAY_BUDGET_SLOTS`. This module authors no prose and
 emits no `proposed_mutation` — persistence is `writes.write_day_plan`.
@@ -50,19 +50,27 @@ from .fact_refs import CodedFacts, code_facts
 from .models import (
     BASE_SKILL_DOMAINS,
     SCHEDULE_PHASES,
+    Agenda,
     AgendaStep,
     AgendaStepRequirement,
     Character,
     Entity,
     Fact,
+    FactionMembership,
     Knowledge,
     Ledger,
     PromptTemplate,
+    Quest,
+    QuestOffer,
     Relation,
+    Rencontre,
+    SkillDefinition,
 )
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
 from .prose_render import fact_text, fact_texts
+from .relation_orientation import is_social
+from .skill_access import held_rank
 
 _log = logging.getLogger(__name__)
 
@@ -71,8 +79,24 @@ _log = logging.getLogger(__name__)
 # as a literal.
 DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)
 
-# S1: four requirement forms, each with a named evaluator.
-REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")
+# S1: the closed requirement vocabulary, each form with a named evaluator.
+# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
+# day-plan model may emit, then four only the creator authors (quest offers).
+REQUIREMENT_TYPES: tuple[str, ...] = (
+    "knowledge", "relation_gte", "resource", "location_reachable",
+    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+)
+
+# What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
+# forms it always could. A creator-only form in a model's plan is a parse
+# failure, never a row.
+MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")
+
+# The shape of each form, the three groups of the `*_requirement_shape`
+# CHECK (C-01): which column names its target, and which need a threshold.
+ENTITY_TARGET_TYPES: tuple[str, ...] = ("relation_gte", "location_reachable", "has_met", "faction_member")
+KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
+THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")
 
 # Emission bound (Scope IN item 4). Anything beyond is truncated with a
 # reported count (logged), not silently dropped.
@@ -164,31 +188,41 @@ def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, rea
 
 
 def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """What the TARGET feels toward the character (TICKET-0108, B-dir): the
+    social row `entity_a = target`, `entity_b = character`, `is_social`;
+    0 when there is none. A deliberate duplicate of
+    `writes.relations._find_perceived_relation`'s query (perceiver = the
+    target), not an import: writes/goals_agendas.py imports FROM this module,
+    so importing FROM writes/ here would cycle the package. The reverse row
+    (the character's own feeling) and the structural types are never read."""
     del reachable_ids
-    # Deliberate duplicate of writes.relations._find_relation_pair's
-    # both-directions first-match query, not an import: writes/goals_agendas.py
-    # (which constructs agenda_step_requirement rows) imports FROM this
-    # module, so importing FROM writes/ here would cycle the package.
-    # Same posture as the connects_to readers above — reported, not acted on.
-    rel = db.exec(
+    rows = db.exec(
         select(Relation).where(
-            ((Relation.entity_a_id == character.id) & (Relation.entity_b_id == req.target_entity_id))
-            | ((Relation.entity_a_id == req.target_entity_id) & (Relation.entity_b_id == character.id))
+            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,
         )
-    ).first()
+    ).all()
+    rel = next((row for row in rows if is_social(row.type)), None)
     current = rel.intensity if rel else 0
     threshold = req.threshold or 0
     met = current >= threshold
     target = db.get(Entity, req.target_entity_id)
     target_name = target.name if target else req.target_entity_id
     reason = (
-        f"relation with {target_name} is {current}, meets requires >= {threshold}" if met
-        else f"prerequisite not met — relation with {target_name} is {current}, requires >= {threshold}"
+        f"relation of {target_name} toward the character is {current}, meets requires >= {threshold}" if met
+        else f"prerequisite not met — relation of {target_name} toward the character is {current}, "
+        f"requires >= {threshold}"
+    )
+    return Verdict(
+        type=req.type, met=met, current=current, required=threshold, reason=reason,
+        required_label=target_name,
     )
-    return Verdict(type=req.type, met=met, current=current, required=threshold, reason=reason)
 
 
 def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """Money: the character's ledger balance. A world has one currency (the
+    `ledger` has no currency column), so `target_key` is a label and is not
+    read; an object is never a `resource` (TICKET-0108, E1: objects held in
+    quantity come with `item_holding`)."""
     del reachable_ids
     total = db.exec(select(func.sum(Ledger.amount)).where(Ledger.entity_id == character.id)).first() or 0
     threshold = req.threshold or 0
@@ -215,11 +249,108 @@ def _eval_location_reachable(req: RequirementSpec, character: Character, db: Ses
     )
 
 
+def _entity_name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else str(entity_id)
+
+
+def _eval_has_met(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """The character and the target have an encounter row (`rencontre`, one
+    row per unordered pair, `entity_lo_id < entity_hi_id`)."""
+    del reachable_ids
+    low, high = sorted((character.id, req.target_entity_id))
+    row = db.exec(
+        select(Rencontre).where(Rencontre.entity_lo_id == low, Rencontre.entity_hi_id == high)
+    ).first()
+    met = row is not None
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"has met {name}" if met else f"prerequisite not met — has not met {name}"
+    return Verdict(
+        type=req.type, met=met, current=("met" if met else "not met"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _eval_faction_member(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """The character holds an ACTIVE membership (`left_at IS NULL`) of the
+    target faction. A secret membership counts: it is the character's own
+    (the `tick_context` self-briefing precedent); secrecy hides it from
+    others, not from the gate."""
+    del reachable_ids
+    row = db.exec(
+        select(FactionMembership).where(
+            FactionMembership.entity_id == character.id,
+            FactionMembership.faction_id == req.target_entity_id,
+            FactionMembership.left_at.is_(None),
+        )
+    ).first()
+    met = row is not None
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"member of {name}" if met else f"prerequisite not met — not a member of {name}"
+    return Verdict(
+        type=req.type, met=met, current=("member" if met else "not a member"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _skill_label(db: Session, skill_key: Optional[str]) -> str:
+    if skill_key in BASE_SKILL_DOMAINS:
+        return str(skill_key)
+    definition = db.get(SkillDefinition, skill_key) if skill_key else None
+    return definition.name if definition is not None else str(skill_key)
+
+
+def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a base domain or a skill definition id; the rank held
+    is `skill_access.held_rank` (a missing base row is Initié, a missing
+    definition row is not held)."""
+    del reachable_ids
+    rank = held_rank(db, character.id, req.target_key)
+    threshold = req.threshold or 0
+    met = rank is not None and rank >= threshold
+    label = _skill_label(db, req.target_key)
+    current = rank if rank is not None else "not held"
+    reason = (
+        f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
+        else f"prerequisite not met — skill {label!r} is {current}, requires rank >= {threshold}"
+    )
+    return Verdict(
+        type=req.type, met=met, current=current, required=threshold, reason=reason, required_label=label,
+    )
+
+
+def _eval_quest_completed(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a quest offer id: met iff a quest the character took
+    from that offer has its agenda `completed` (M1: a quest's state is its
+    agenda's)."""
+    del reachable_ids
+    row = db.exec(
+        select(Quest.id)
+        .join(Agenda, Agenda.id == Quest.agenda_id)
+        .where(
+            Quest.character_id == character.id, Quest.offer_id == req.target_key,
+            Agenda.status == "completed",
+        )
+    ).first()
+    met = row is not None
+    offer = db.get(QuestOffer, req.target_key) if req.target_key else None
+    label = offer.title if offer is not None else str(req.target_key)
+    reason = f"quest {label!r} completed" if met else f"prerequisite not met — quest {label!r} not completed"
+    return Verdict(
+        type=req.type, met=met, current=("completed" if met else "not completed"), required=req.target_key,
+        reason=reason, required_label=label,
+    )
+
+
 _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
     "knowledge": _eval_knowledge,
     "relation_gte": _eval_relation_gte,
     "resource": _eval_resource,
     "location_reachable": _eval_location_reachable,
+    "has_met": _eval_has_met,
+    "faction_member": _eval_faction_member,
+    "skill_rank_gte": _eval_skill_rank_gte,
+    "quest_completed": _eval_quest_completed,
 }
 
 
@@ -253,21 +384,23 @@ def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
     return frozenset(visited)
 
 
-def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
-    """Judge every requirement on `step` against `character`'s current
-    state. Dispatches through `_EVALUATORS`; an unknown `type` raises
-    fail-closed — it cannot happen through the DB (the CHECK forbids it),
-    the branch exists so that widening `REQUIREMENT_TYPES` without adding an
-    evaluator fails loudly.
-
-    `_day_reachable_ids` is computed AT MOST ONCE per call, only if `step`
-    actually carries a `location_reachable` requirement — never per
-    requirement item."""
-    needs_reachable = any(r.type == "location_reachable" for r in step.requirements)
+def evaluate_specs(
+    requirements: tuple[RequirementSpec, ...], character: Character, db: Session,
+) -> list[Verdict]:
+    """Judge each requirement against `character`'s current state (C-02).
+    Dispatches through `_EVALUATORS`; an unknown `type` raises fail-closed —
+    it cannot happen through the DB (the CHECK forbids it), the branch exists
+    so that widening `REQUIREMENT_TYPES` without adding an evaluator fails
+    loudly. Shared by a step (`evaluate_requirements`) and a quest offer's
+    eligibility (`quest_reads`), so both are one judgment.
+
+    `_day_reachable_ids` is computed AT MOST ONCE per call, only if a
+    `location_reachable` requirement is present — never per requirement."""
+    needs_reachable = any(r.type == "location_reachable" for r in requirements)
     reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None
 
     verdicts: list[Verdict] = []
-    for req in step.requirements:
+    for req in requirements:
         evaluator = _EVALUATORS.get(req.type)
         if evaluator is None:
             raise ValueError(f"unknown requirement type {req.type!r}")
@@ -275,6 +408,12 @@ def evaluate_requirements(step: PlanStep, character: Character, db: Session) ->
     return verdicts
 
 
+def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
+    """Judge every requirement on `step` (`evaluate_specs` on its
+    requirements)."""
+    return evaluate_specs(step.requirements, character, db)
+
+
 def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Session) -> EvaluatedStep:
     """One `agenda_step` row plus its requirement rows, judged against
     `character`'s current state (TICKET-0080, BRIEF-0080-b). Carved out of
@@ -415,7 +554,7 @@ def _validate_requirement(raw: object) -> RequirementSpec:
     if not isinstance(raw, dict):
         raise llm_parse.LlmParseError(f"day_plan: requirement entry must be an object, got {raw!r}")
     req_type = raw.get("type")
-    if req_type not in REQUIREMENT_TYPES:
+    if req_type not in MODEL_REQUIREMENT_TYPES:
         raise llm_parse.LlmParseError(f"day_plan: unknown requirement type {req_type!r}")
     threshold = raw.get("threshold")
     if not isinstance(threshold, int) or isinstance(threshold, bool):
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 4fe1b0d..1df4f64 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -262,6 +262,11 @@ _BLOCKED_DETAIL_FR: dict[str, str] = {
     "resource": "il ne dispose pas des moyens nécessaires",
     "relation_gte": "ses appuis ne sont pas encore assez solides pour cela",
     "location_reachable": "l'endroit n'est pas accessible depuis là où il se trouve",
+    # TICKET-0108 (BRIEF-0108-A): the four creator-only forms.
+    "has_met": "il n'a encore jamais rencontré {required}",
+    "faction_member": "il n'appartient pas à {required}",
+    "skill_rank_gte": "sa maîtrise de « {required} » ne suffit pas encore",
+    "quest_completed": "il doit d'abord mener à bien « {required} »",
 }
 
 
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index b5f510a..7e93cb2 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -28,13 +28,16 @@ Layout, by stratum:
     observation.py   — observed-scene instrumentation (ObservationRun and
                         friends, TICKET-0051); telemetry, never canon —
                         absent from canon_write_policy.txt's [CANON_TABLES].
+    quests.py        — quest offers and accepted quests (QuestOffer,
+                        QuestOfferStep, QuestOfferRequirement, Quest;
+                        TICKET-0108, schema v2.17), canon.
 
 This module re-exports the ENTIRE former public surface of the flat
 `models.py` — every class, constant, and the two module functions
 (`_uuid`, `_created_ts`) — so every existing `from .models import X` /
 `from world_engine.models import X` in `src/` and `scripts/` resolves
 unchanged. Import order (canon, canon_faction, canon_knowledge, config,
-ephemeral, pipeline, observation) keeps table registration on
+ephemeral, pipeline, observation, quests) keeps table registration on
 `SQLModel.metadata` deterministic;
 cross-stratum foreign keys (string table-name references) resolve
 regardless of file order.
@@ -124,6 +127,7 @@ from .observation import (
     ObservationRun,
     ObservationRunTemplate,
 )
+from .quests import QUEST_OFFER_STATUSES, Quest, QuestOffer, QuestOfferRequirement, QuestOfferStep
 
 __all__ = [
     "World",
@@ -187,6 +191,11 @@ __all__ = [
     "Agenda",
     "AgendaStep",
     "AgendaStepRequirement",
+    "QUEST_OFFER_STATUSES",
+    "Quest",
+    "QuestOffer",
+    "QuestOfferRequirement",
+    "QuestOfferStep",
     "GoalAgendaLink",
     "EntityType",
     "EntityTypeHistory",
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index 07cfb27..534e89c 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -107,14 +107,19 @@ class AgendaStep(SQLModel, table=True):
 # agenda_step_requirement  (day-plan precondition gate, schema v1.94,
 # TICKET-0075, BRIEF-0075-b). `goal_prerequisite` shape precedent (same
 # id/world_id/type/target_entity_id/threshold spine), widened to a closed
-# four-form vocabulary and a `target_key` column for the two forms that gate
-# on a string (knowledge fact id since TICKET-0097, resource tag) rather than an entity.
+# vocabulary and a `target_key` column for the forms that gate on a string
+# (knowledge fact id since TICKET-0097, resource tag, skill key, quest offer
+# id) rather than an entity. Eight forms since v2.17 (TICKET-0108,
+# BRIEF-0108-A): the four the day-plan model may emit, plus `has_met`,
+# `faction_member`, `skill_rank_gte` and `quest_completed`, authored by the
+# creator only (`day_plan.MODEL_REQUIREMENT_TYPES`).
 #
 # The per-type shape CHECK is the structural guarantee that an ill-formed row
-# cannot exist: `relation_gte`/`location_reachable` require target_entity_id
-# NOT NULL; `knowledge`/`resource` require target_key NOT NULL;
-# `relation_gte`/`resource` require threshold NOT NULL. Curated plan
-# metadata, same family as `npc_schedule` — no `change_history`.
+# cannot exist; its three groups are `day_plan.ENTITY_TARGET_TYPES`,
+# `KEY_TARGET_TYPES` and `THRESHOLD_TYPES`. `quest_offer_requirement`
+# (models/quests.py) carries the same two CHECK texts, byte for byte
+# (`quests.py` check, QA1). Curated plan metadata, same family as
+# `npc_schedule` — no `change_history`.
 #
 # THE POSITIONAL WALL: `location_reachable`'s target lives HERE, on the
 # requirement row, never on `agenda_step` — a requirement states "the player
@@ -125,13 +130,16 @@ class AgendaStepRequirement(SQLModel, table=True):
     __tablename__ = "agenda_step_requirement"
     __table_args__ = (
         CheckConstraint(
-            "type IN ('knowledge','relation_gte','resource','location_reachable')",
+            "type IN ('knowledge','relation_gte','resource','location_reachable',"
+            "'has_met','faction_member','skill_rank_gte','quest_completed')",
             name="ck_agenda_step_requirement_type",
         ),
         CheckConstraint(
-            "(type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL) "
-            "AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL) "
-            "AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)",
+            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') "
+            "OR target_entity_id IS NOT NULL) "
+            "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
+            "OR target_key IS NOT NULL) "
+            "AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)",
             name="ck_agenda_step_requirement_shape",
         ),
         Index(
diff --git a/src/world_engine/models/quests.py b/src/world_engine/models/quests.py
new file mode 100644
index 0000000..1a473c8
--- /dev/null
+++ b/src/world_engine/models/quests.py
@@ -0,0 +1,133 @@
+"""Quest offers and accepted quests (schema v2.17, TICKET-0108, BRIEF-0108-A).
+
+Canon stratum, quest family. An offer is what the creator authors (E1): who
+gives it (a character or a faction, H1), its title, its steps and the
+requirements that decide who it is offered to (eligibility, a requirement
+row with no step) and what each step needs. Accepting it (B1) copies its
+steps and their requirements into a new `agenda` of the player, born
+`paused` (A1); `quest` links that agenda to the offer it came from. A
+quest's state is its agenda's status, never a second column (M1).
+
+The requirement vocabulary is `agenda_step_requirement`'s, not a second
+language (B1): `quest_offer_requirement` carries the same two CHECK texts,
+byte for byte, and `day_plan.evaluate_specs` judges both.
+
+Offers are curated content: their steps and requirements are replaced
+whole when the creator saves an offer (the `npc_price` full-replace
+precedent); an accepted quest is unaffected, its agenda holds its own copy.
+The offer row itself keeps a `change_history`.
+"""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Optional
+
+from sqlalchemy import CheckConstraint, Column, Index, JSON, text
+from sqlmodel import Field, SQLModel
+
+from .canon import _created_ts, _uuid
+
+# The two lifecycle states of an offer: `open` is proposed to whoever is
+# eligible, `closed` is proposed to no one. An offer is never deleted.
+QUEST_OFFER_STATUSES: tuple[str, ...] = ("open", "closed")
+
+
+# -----------------------------------------------------------------------------
+# quest_offer  (a quest the creator authored)
+# -----------------------------------------------------------------------------
+class QuestOffer(SQLModel, table=True):
+    __tablename__ = "quest_offer"
+    __table_args__ = (
+        CheckConstraint("status IN ('open','closed')", name="ck_quest_offer_status"),
+        Index("idx_quest_offer_world", "world_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    # A character or a faction of the world (H1), checked by the writer.
+    giver_entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    title: str
+    summary: Optional[str] = None
+    # L1: a repeatable offer may be accepted again once the last quest taken
+    # from it is over; any other offer once per character.
+    repeatable: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    status: str = Field(default="open", sa_column_kwargs={"server_default": text("'open'")})
+    created_at: datetime = _created_ts()
+    updated_at: datetime = _created_ts()
+    change_history: list = Field(
+        default_factory=list,
+        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
+    )
+
+
+# -----------------------------------------------------------------------------
+# quest_offer_step  (one step of an offer, copied to agenda_step on accept)
+# -----------------------------------------------------------------------------
+class QuestOfferStep(SQLModel, table=True):
+    __tablename__ = "quest_offer_step"
+    __table_args__ = (
+        CheckConstraint("cost BETWEEN 1 AND 4", name="ck_quest_offer_step_cost"),
+        Index("idx_quest_offer_step_order", "offer_id", "step_order", unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
+    step_order: int
+    objective: str
+    cost: int  # day-budget slots, as agenda_step.cost
+    domain: Optional[str] = None  # a base skill domain, or NULL: no roll
+
+
+# -----------------------------------------------------------------------------
+# quest_offer_requirement  (eligibility when step_id is NULL; else a step's
+# requirement). Same vocabulary and CHECK texts as agenda_step_requirement.
+# -----------------------------------------------------------------------------
+class QuestOfferRequirement(SQLModel, table=True):
+    __tablename__ = "quest_offer_requirement"
+    __table_args__ = (
+        CheckConstraint(
+            "type IN ('knowledge','relation_gte','resource','location_reachable',"
+            "'has_met','faction_member','skill_rank_gte','quest_completed')",
+            name="ck_quest_offer_requirement_type",
+        ),
+        CheckConstraint(
+            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') "
+            "OR target_entity_id IS NOT NULL) "
+            "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
+            "OR target_key IS NOT NULL) "
+            "AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)",
+            name="ck_quest_offer_requirement_shape",
+        ),
+        Index("idx_quest_offer_requirement_offer", "offer_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
+    step_id: Optional[str] = Field(default=None, foreign_key="quest_offer_step.id")
+    type: str
+    target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    target_key: Optional[str] = None
+    threshold: Optional[int] = None
+
+
+# -----------------------------------------------------------------------------
+# quest  (an offer a character accepted: the link to its agenda). Immutable:
+# the quest's state is `agenda.status` (M1).
+# -----------------------------------------------------------------------------
+class Quest(SQLModel, table=True):
+    __tablename__ = "quest"
+    __table_args__ = (
+        Index("idx_quest_agenda", "agenda_id", unique=True),
+        Index("idx_quest_character", "character_id"),
+        Index("idx_quest_offer", "offer_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
+    character_id: str = Field(foreign_key="entity.id", nullable=False)
+    agenda_id: str = Field(foreign_key="agenda.id", nullable=False)
+    accepted_at: datetime = _created_ts()
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index db940d3..0a5a0bb 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.16"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.17"
diff --git a/src/world_engine/skill_access.py b/src/world_engine/skill_access.py
index fc3f296..5831614 100644
--- a/src/world_engine/skill_access.py
+++ b/src/world_engine/skill_access.py
@@ -25,7 +25,7 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
-from .models import Skill, SkillDefinition
+from .models import BASE_SKILL_DOMAINS, Skill, SkillDefinition
 from .resolution import Verdict
 from .skill_ranks import DEFAULT_RANK, rank_modifier
 
@@ -79,6 +79,18 @@ def opposition_modifier(db: Session, npc_id: str, base_domain: str, definition:
     return rank_modifier(row.rank if row is not None else DEFAULT_RANK)
 
 
+def held_rank(db: Session, character_id: str, skill_key: Optional[str]) -> Optional[int]:
+    """The rank a character holds in `skill_key` (TICKET-0108, BRIEF-0108-A,
+    the `skill_rank_gte` requirement): a base domain reads its base row, else
+    `DEFAULT_RANK` (every character has the four base domains, D1); a skill
+    definition id reads the character's row for it, else None -- not held."""
+    if skill_key in BASE_SKILL_DOMAINS:
+        row = _base_row(db, character_id, skill_key)
+        return row.rank if row is not None else DEFAULT_RANK
+    row = _definition_row(db, character_id, skill_key) if skill_key else None
+    return row.rank if row is not None else None
+
+
 def locked_verdict(skill_name: str) -> Verdict:
     """The verdict of a locked skill (B1): no dice were rolled. `domain`
     carries the skill's name, for the verdict event and the MJ rubric."""
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index 5ba39b6..e0bbe1d 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -43,15 +43,26 @@ from sqlalchemy import text
 from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session, select
 
-from ..day_plan import REQUIREMENT_TYPES, PlanStep, RequirementSpec
+from ..day_plan import (
+    ENTITY_TARGET_TYPES,
+    KEY_TARGET_TYPES,
+    REQUIREMENT_TYPES,
+    THRESHOLD_TYPES,
+    PlanStep,
+    RequirementSpec,
+)
 from ..models import (
+    BASE_SKILL_DOMAINS,
     Agenda,
     AgendaStep,
     AgendaStepRequirement,
     Entity,
+    Fact,
     GoalAgendaLink,
     GoalPrerequisite,
     NpcGoal,
+    QuestOffer,
+    SkillDefinition,
 )
 
 # npc_goal.horizon enum (world-engine-schema.md v1.69): short | long.
@@ -585,33 +596,69 @@ def write_agenda_status(
     return agenda
 
 
+# The entity type each entity-targeted form must name (TICKET-0108, C-01);
+# `None` accepts any entity of the world -- the two model-emitted forms keep
+# the check they always had, so a day plan is refused for nothing new.
+_TARGET_ENTITY_TYPE: dict[str, Optional[str]] = {
+    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": "faction",
+}
+
+
+def _clean_target_key(db: Session, world_id: str, req: RequirementSpec) -> Optional[str]:
+    """The error for a key-targeted form whose key names nothing in
+    `world_id`, or None. `resource`'s key is a label (one currency per
+    world), never resolved."""
+    if req.type == "knowledge":
+        fact = db.get(Fact, req.target_key)
+        return None if fact is not None and fact.world_id == world_id else f"unknown fact {req.target_key!r}"
+    if req.type == "skill_rank_gte":
+        if req.target_key in BASE_SKILL_DOMAINS:
+            return None
+        definition = db.get(SkillDefinition, req.target_key)
+        ok = definition is not None and definition.world_id == world_id
+        return None if ok else f"unknown skill {req.target_key!r}"
+    if req.type == "quest_completed":
+        offer = db.get(QuestOffer, req.target_key)
+        return None if offer is not None and offer.world_id == world_id else f"unknown quest offer {req.target_key!r}"
+    return None
+
+
 def _clean_requirement(db: Session, world_id: str, step_index: int, req: RequirementSpec) -> dict:
-    """Validate one requirement against the six-condition per-type shape
-    (the `agenda_step_requirement` CHECK, duplicated here as a readable
-    `ValueError` rather than a bare `IntegrityError`) and resolve it into the
-    exact kwargs `AgendaStepRequirement` needs. Raises on any violation —
-    carved out of `write_day_plan` so that function fits the 80-line cap
-    (`_build_relation_delta`/`_build_relation_set` precedent, R7)."""
+    """Validate one requirement against the per-type shape (the
+    `*_requirement_shape` CHECK, duplicated here as a readable `ValueError`
+    rather than a bare `IntegrityError`; its groups are `day_plan`'s
+    `ENTITY_TARGET_TYPES`/`KEY_TARGET_TYPES`/`THRESHOLD_TYPES`), check that
+    its target exists in `world_id`, and resolve it into the exact kwargs a
+    requirement row needs. Raises on any violation. Shared by
+    `write_day_plan` and the quest writers (`writes/quests.py`, C-03)."""
     if req.type not in REQUIREMENT_TYPES:
         raise ValueError(f"write_day_plan: unknown requirement type {req.type!r}")
 
-    entity_gated = req.type in ("relation_gte", "location_reachable")
+    entity_gated = req.type in ENTITY_TARGET_TYPES
     if entity_gated:
         if not req.target_entity_id:
             raise ValueError(
                 f"write_day_plan: step {step_index} requirement type {req.type!r} needs a target_entity_id"
             )
         target = db.get(Entity, req.target_entity_id)
-        if target is None or target.world_id != world_id:
+        wanted = _TARGET_ENTITY_TYPE[req.type]
+        if target is None or target.world_id != world_id or (wanted is not None and target.type != wanted):
             raise ValueError(f"write_day_plan: unknown target entity {req.target_entity_id!r}")
-    elif not req.target_key:
-        raise ValueError(f"write_day_plan: step {step_index} requirement type {req.type!r} needs a target_key")
+    else:
+        if not req.target_key:
+            raise ValueError(f"write_day_plan: step {step_index} requirement type {req.type!r} needs a target_key")
+        error = _clean_target_key(db, world_id, req)
+        if error is not None:
+            raise ValueError(f"write_day_plan: step {step_index} requirement type {req.type!r}: {error}")
 
     threshold = req.threshold
-    if req.type in ("relation_gte", "resource"):
-        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
+    if req.type in THRESHOLD_TYPES:
+        top = 5 if req.type == "skill_rank_gte" else None
+        if (not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1
+                or (top is not None and threshold > top)):
             raise ValueError(
                 f"write_day_plan: step {step_index} requirement type {req.type!r} needs a positive integer threshold"
+                + (f" of at most {top}" if top is not None else "")
             )
     else:
         threshold = None
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 17634d7..9138c2b 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -74,7 +74,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
     "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
     "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
-    "world_law",
+    "world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 8b3874e..f7d97ac 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18039,6 +18039,44 @@ creator's bypass. Each row names its master. A skill's fiche carries
 **Rejected.** A second component for NPC sheets: the same rows, the same
 routes, two places to keep in step.
 
+
+## A QUEST IS OFFERED, THEN ACCEPTED AS AN OPEN PLAN (TICKET-0108) -- EIGHT REQUIREMENT FORMS, FOUR FOR THE MODEL (BRIEF-0108-a, schema v2.17)
+
+**B1, A1.** A quest offer (`quest_offer`, its steps, its requirements) is
+authored by the creator; accepting it creates an agenda of the player born
+`paused` -- one open plan among the others, so several quests run at once
+without lifting the one-active-agenda rule: a day selects the plan it
+advances (TICKET-0077), or the player pins it. `quest` links the agenda to
+its offer and holds no state of its own (M1).
+
+**B, one language.** `agenda_step_requirement` gains four forms --
+`has_met`, `faction_member`, `skill_rank_gte`, `quest_completed` -- and
+`quest_offer_requirement` carries its two CHECK texts byte for byte; a
+requirement with no step is eligibility. `day_plan.evaluate_specs` judges
+both. The day-plan model may still emit only the four forms it always
+could (`MODEL_REQUIREMENT_TYPES`); a creator form in its plan is a parse
+failure. `resource` stays money, its key a label: an object is never a
+resource.
+
+**B-dir.** `relation_gte` reads what the target feels toward the
+character (the social row target -> character), the same row the NPC-goal
+prerequisite judge reads (`_find_perceived_relation`); before this, a day
+plan read the first row of the pair in either direction, structural rows
+included.
+
+**A secret membership counts** for `faction_member`: it is the character's
+own (the `tick_context` self-briefing precedent).
+
+**Offers are curated content.** Saving an offer replaces its steps and
+requirements whole (the `npc_price` precedent, a named exception to
+"history is sacred"); an accepted quest keeps its own copy in its agenda,
+and the offer row keeps a `change_history`.
+
+**Rejected.** A3, several active agendas per character: `pass_play.
+agenda_id`, the resolve guard and `active_plan` all assume one. A separate
+targeting vocabulary for eligibility (B2): a second language. Renaming
+`resource`: a data migration and a prompt change for a label.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 3ec1723..f5526fc 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -5,7 +5,7 @@ event artifact npc_goal agenda agenda_step goal_agenda_link
 npc_price world_law obstacle obstacle_vertex door
 location_type_catalog entity_type entity_type_history conversation_window_config
 npc_schedule agenda_step_requirement fact fact_participant fact_default
-skill_rank
+skill_rank quest_offer quest_offer_step quest_offer_requirement quest
 
 [ALLOWED_SITES]
 # path::function                                              tables
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index a124054..a2a460c 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -5,11 +5,11 @@ BRIEF-0075-b). Stdlib `ast` and text only, no DB — same FAILURES/fail()/
 R1 (evaluator bijection, `_SOURCE_LOOKUPS` precedent): `_EVALUATORS`' key set
 equals `REQUIREMENT_TYPES` exactly, in both directions.
 R2 (type vocabulary): `agenda_step_requirement`'s `type` CHECK
-(`ck_agenda_step_requirement_type`) quotes exactly `REQUIREMENT_TYPES`'s four
-values.
+(`ck_agenda_step_requirement_type`) quotes exactly `REQUIREMENT_TYPES`'s
+values (eight since TICKET-0108).
 R3 (shape CHECK): `ck_agenda_step_requirement_shape` exists and its
-expression mentions all six (type, column) pairs from the per-type shape
-rule.
+expression mentions every (type, column) pair from the per-type shape rule
+(eleven since TICKET-0108).
 R4 (budget derivation): `DAY_BUDGET_SLOTS` is a `len(...)` derivation, never
 a numeric literal.
 R5 (P2 / positional read exclusion): `day_plan.py` contains no reference to
@@ -187,7 +187,12 @@ SEED_PILOT_FILE = ROOT / "scripts" / "seed_pilot.py"
 # headroom, TICKET-0075/BRIEF-0075-b) — Agenda stays in canon.py.
 _MODEL_FILES = (CANON_FILE, CONFIG_FILE)
 
-EXPECTED_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
+# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A): the model's four, then
+# the creator's four. Which ones the model may emit is `quests.py`'s QA1.
+EXPECTED_REQUIREMENT_TYPES = (
+    "knowledge", "relation_gte", "resource", "location_reachable",
+    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+)
 EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")
 EXPECTED_PLAN_ACTIONS = ("continue", "modify", "replace", "resume")
 # day_plans.OPEN_PLAN_STATUSES, restated here for the static R23 total-mapping
@@ -355,6 +360,11 @@ def check_shape_constraint() -> None:
         ("resource", "target_key"),
         ("relation_gte", "threshold"),
         ("resource", "threshold"),
+        ("has_met", "target_entity_id"),
+        ("faction_member", "target_entity_id"),
+        ("skill_rank_gte", "target_key"),
+        ("quest_completed", "target_key"),
+        ("skill_rank_gte", "threshold"),
     ]
     missing = [pair for pair in required_pairs if pair[0] not in expr or pair[1] not in expr]
     if missing:
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index 4d6639e..d083a53 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -53,6 +53,9 @@ JSON_COLUMN_ALLOWLIST = {
     "Skill.change_history",
     "Agenda.change_history",
     "AgendaStep.change_history",
+    # TICKET-0108 (BRIEF-0108-A): an offer's audit trail, the same posture
+    # as the change_history columns above -- never rendered as a UI field.
+    "QuestOffer.change_history",
     # Internal engine snapshots — never rendered in any UI surface.
     "PassPlay.injected_context",
     "PassPlay.history",
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
new file mode 100644
index 0000000..5acef3c
--- /dev/null
+++ b/tooling/verify/checks/quests.py
@@ -0,0 +1,430 @@
+"""G1 check for TICKET-0108 -- quest offers, accepted quests, and the
+requirement vocabulary they share with day plans.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`npc_skills.py` precedent, TICKET-0107). Each brief adds its rules here in
+the same commit.
+
+QA1 -- vocabulary (BRIEF-0108-A, static and import). `day_plan.REQUIREMENT_
+   TYPES` holds the eight forms; `MODEL_REQUIREMENT_TYPES` is exactly the
+   model's four and a subset of it; `ENTITY_TARGET_TYPES` and
+   `KEY_TARGET_TYPES` partition it and `THRESHOLD_TYPES` is inside it; the
+   three `type NOT IN (...)` groups of `ck_agenda_step_requirement_shape`
+   are, in order, those three constants; `quest_offer_requirement`'s two
+   CHECK texts equal `agenda_step_requirement`'s; `day_plan.
+   _validate_requirement` (the model's parser) accepts each model form and
+   refuses each creator form.
+QA2 -- migration `scripts/migrate_v2_17_quests.py`, on a v2.16-shaped
+   database (`agenda_step_requirement` in its v2.16 DDL, verbatim below, no
+   quest table), holding one requirement row and a `session` row pointing
+   to a missing world:
+   a. at v2.15 it refuses (non-zero exit) and changes nothing;
+   b. at v2.16 it keeps the requirement row, its stored CHECK names the four
+      new forms, the four quest tables exist with the models' columns, a
+      `has_met` requirement row can be inserted, `PRAGMA foreign_key_check`
+      is empty on the five tables it writes, the orphan `session` is noted
+      and not stopped on, and `schema_meta` is the code's version;
+   c. a second run exits zero and changes no row.
+QA3 -- the evaluators (fixture). `relation_gte` reads what the target feels
+   toward the character: the character's own row toward the target and a
+   structural row are not read. `has_met` reads `rencontre`;
+   `faction_member` an active membership, secret included, a left one not;
+   `skill_rank_gte` a base domain without a row at Initié, a definition
+   without a row as not held, a row at its rank; `quest_completed` a quest
+   whose agenda is `completed`, not `paused`. `requirement_detail_fr` names
+   the target of each new form. `_clean_requirement` refuses a
+   `faction_member` aimed at a character, a `skill_rank_gte` threshold of
+   6, an unknown skill, an unknown quest offer, and accepts each form well
+   aimed.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import re
+import sqlite3
+import subprocess
+import sys
+import tempfile
+from datetime import UTC, datetime
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+MIGRATION = ROOT / "scripts" / "migrate_v2_17_quests.py"
+
+FAILURES: list[str] = []
+
+MODEL_FORMS = ("knowledge", "relation_gte", "resource", "location_reachable")
+CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
+QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")
+
+# `agenda_step_requirement` as v2.16 created it (dumped from `main` at 4b06dde).
+_V216_DDL = (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
+    "(step_id, type, target_entity_id, target_key)",
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
+# --- QA1 -----------------------------------------------------------------------
+
+def _check_texts(table) -> dict[str, str]:
+    from sqlalchemy import CheckConstraint
+
+    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+
+
+def _shape_groups(shape: str) -> list[tuple[str, ...]]:
+    return [tuple(re.findall(r"'([^']*)'", group)) for group in re.findall(r"type NOT IN \(([^)]*)\)", shape)]
+
+
+def check_qa1() -> None:
+    from world_engine import day_plan, llm_parse
+    from world_engine.models import AgendaStepRequirement, QuestOfferRequirement
+
+    types = day_plan.REQUIREMENT_TYPES
+    if tuple(types) != MODEL_FORMS + CREATOR_FORMS:
+        fail(f"QA1: REQUIREMENT_TYPES is {types}")
+    if tuple(day_plan.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
+        fail(f"QA1: MODEL_REQUIREMENT_TYPES is {day_plan.MODEL_REQUIREMENT_TYPES}")
+    entity, key, threshold = (set(day_plan.ENTITY_TARGET_TYPES), set(day_plan.KEY_TARGET_TYPES),
+                              set(day_plan.THRESHOLD_TYPES))
+    if entity & key or entity | key != set(types) or not threshold or not threshold <= set(types):
+        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {threshold}")
+
+    agenda = _check_texts(AgendaStepRequirement.__table__)
+    offer = _check_texts(QuestOfferRequirement.__table__)
+    shape = agenda.get("ck_agenda_step_requirement_shape", "")
+    groups = _shape_groups(shape)
+    expected = [tuple(day_plan.ENTITY_TARGET_TYPES), tuple(day_plan.KEY_TARGET_TYPES), tuple(day_plan.THRESHOLD_TYPES)]
+    if groups != expected:
+        fail(f"QA1: the shape CHECK groups are {groups}, expected {expected}")
+    pairs = (("ck_agenda_step_requirement_type", "ck_quest_offer_requirement_type"),
+             ("ck_agenda_step_requirement_shape", "ck_quest_offer_requirement_shape"))
+    for agenda_name, offer_name in pairs:
+        if not agenda.get(agenda_name) or agenda.get(agenda_name) != offer.get(offer_name):
+            fail(f"QA1: {offer_name} differs from {agenda_name}")
+
+    for form in MODEL_FORMS:
+        try:
+            day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
+        except llm_parse.LlmParseError as exc:
+            fail(f"QA1: the model's parser refuses {form!r}: {exc}")
+    for form in CREATOR_FORMS:
+        try:
+            day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
+        except llm_parse.LlmParseError:
+            continue
+        fail(f"QA1: the model's parser accepts the creator form {form!r}")
+
+
+# --- QA2 -----------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _shape(conn, table: str) -> list[tuple]:
+    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))
+
+
+def _seed_v216(db_path: str) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import Agenda, AgendaStep, Entity, SchemaMeta, World
+
+    create_db_and_tables()
+    ids: dict = {}
+    with Session(engine) as session:
+        world = World(name="Quests QA2", is_active=True)
+        session.add(world)
+        session.flush()
+        person = Entity(world_id=world.id, type="character", name="pc")
+        session.add(person)
+        session.flush()
+        agenda = Agenda(world_id=world.id, owner_entity_id=person.id, title="t", change_history=[])
+        session.add(agenda)
+        session.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", change_history=[])
+        session.add(step)
+        session.flush()
+        ids.update(world=world.id, person=person.id, step=step.id)
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.16"))
+        session.commit()
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        ids["model_shapes"] = {t: _shape(conn, t) for t in QUEST_TABLES}
+        conn.execute("PRAGMA foreign_keys=OFF")
+        for table in QUEST_TABLES[::-1] + ("agenda_step_requirement",):
+            conn.execute(f"DROP TABLE {table}")
+        for statement in _V216_DDL:
+            conn.execute(statement)
+        conn.execute(
+            "INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_key) "
+            "VALUES ('req-1', ?, ?, 'knowledge', 'fact-x')", (ids["world"], ids["step"]))
+        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
+        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
+    return ids
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "requirements": conn.execute("SELECT * FROM agenda_step_requirement ORDER BY id").fetchall(),
+            "check": conn.execute("SELECT sql FROM sqlite_master WHERE name='agenda_step_requirement'").fetchone()[0],
+            "quest_tables": {t: _shape(conn, t) for t in QUEST_TABLES if t in tables},
+        }
+
+
+def check_qa2(db_path: str) -> None:
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    ids = _seed_v216(db_path)
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.15' WHERE id = 1")
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail(f"QA2a: at v2.15 the migration exit {result.returncode} or the database changed")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.16' WHERE id = 1")
+    result = _run_migration(db_path)
+    if result.returncode != 0:
+        fail(f"QA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
+        return
+    after = _state(db_path)
+    if after["requirements"] != before["requirements"] or not after["requirements"]:
+        fail(f"QA2b: the requirement rows are {after['requirements']}")
+    absent = [form for form in CREATOR_FORMS if f"'{form}'" not in after["check"]]
+    if absent:
+        fail(f"QA2b: the stored CHECK lacks {absent}")
+    if after["quest_tables"] != ids["model_shapes"]:
+        fail(f"QA2b: the quest tables are {after['quest_tables']}, expected the models' {ids['model_shapes']}")
+    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"QA2b: schema_meta is {after['version']}")
+    if "Note: session rowid" not in result.stdout:
+        fail("QA2b: the orphan session row was not noted")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("PRAGMA foreign_keys=ON")
+        try:
+            conn.execute(
+                "INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id) "
+                "VALUES ('req-2', ?, ?, 'has_met', ?)", (ids["world"], ids["step"], ids["person"]))
+        except sqlite3.DatabaseError as exc:
+            fail(f"QA2b: a has_met row cannot be inserted: {exc}")
+        dangling = [r for t in ("agenda_step_requirement",) + QUEST_TABLES
+                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
+        if dangling:
+            fail(f"QA2b: foreign_key_check {dangling}")
+    again_before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode != 0 or _state(db_path) != again_before:
+        fail(f"QA2c: a second run exit {result.returncode} or changed a row")
+
+
+# --- QA3 -----------------------------------------------------------------------
+
+def _qa3_world(session) -> dict:
+    from world_engine.models import Character, Entity, Faction, SkillDefinition, World
+
+    world = World(name="Quests QA3", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind in (("pc", "player"), ("npc", "npc")):
+        row = Entity(world_id=world.id, type="character", name=key.upper())
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
+        ids[key] = row.id
+    faction = Entity(world_id=world.id, type="faction", name="Guilde")
+    session.add(faction)
+    session.flush()
+    session.add(Faction(id=faction.id))
+    ids["faction"] = faction.id
+    definition = SkillDefinition(world_id=world.id, name="Herboristerie", base_domain="perception")
+    session.add(definition)
+    session.flush()
+    ids["definition"] = definition.id
+    session.commit()
+    return ids
+
+
+def _verdict(session, character, form: str, **target):
+    from world_engine.day_plan import RequirementSpec, evaluate_specs
+
+    return evaluate_specs((RequirementSpec(type=form, **target),), character, session)[0]
+
+
+def _qa3_relation_and_meeting(session, ids, pc) -> None:
+    from world_engine.models import Relation, Rencontre
+
+    session.add(Relation(world_id=ids["world"], entity_a_id=ids["pc"], entity_b_id=ids["npc"],
+                         type="ami", direction="a_to_b", intensity=90, change_history=[]))
+    session.add(Relation(world_id=ids["world"], entity_a_id=ids["npc"], entity_b_id=ids["pc"],
+                         type="controls", direction="a_to_b", intensity=95, change_history=[]))
+    session.commit()
+    if _verdict(session, pc, "relation_gte", target_entity_id=ids["npc"], threshold=50).met:
+        fail("QA3: relation_gte read the character's own row, or a structural row")
+    session.add(Relation(world_id=ids["world"], entity_a_id=ids["npc"], entity_b_id=ids["pc"],
+                         type="ami", direction="a_to_b", intensity=60, change_history=[]))
+    session.commit()
+    verdict = _verdict(session, pc, "relation_gte", target_entity_id=ids["npc"], threshold=50)
+    if not verdict.met or verdict.current != 60:
+        fail(f"QA3: relation_gte with the target's row at 60 is {verdict}")
+    if _verdict(session, pc, "has_met", target_entity_id=ids["npc"]).met:
+        fail("QA3: has_met is met with no encounter")
+    low, high = sorted((ids["pc"], ids["npc"]))
+    now = datetime(2026, 1, 1, tzinfo=UTC)
+    session.add(Rencontre(world_id=ids["world"], entity_lo_id=low, entity_hi_id=high, first_at=now,
+                          last_at=now, source="visit"))
+    session.commit()
+    if not _verdict(session, pc, "has_met", target_entity_id=ids["npc"]).met:
+        fail("QA3: has_met is unmet with an encounter row")
+
+
+def _qa3_faction_and_skill(session, ids, pc) -> None:
+    from world_engine.models import FactionMembership, Skill
+
+    left = FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["faction"],
+                             left_at=datetime(2026, 1, 1, tzinfo=UTC))
+    session.add(left)
+    session.commit()
+    if _verdict(session, pc, "faction_member", target_entity_id=ids["faction"]).met:
+        fail("QA3: faction_member is met by a membership the character left")
+    session.add(FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["faction"],
+                                  is_secret=True))
+    session.commit()
+    if not _verdict(session, pc, "faction_member", target_entity_id=ids["faction"]).met:
+        fail("QA3: faction_member is unmet by an active secret membership")
+    initie = _verdict(session, pc, "skill_rank_gte", target_key="agility", threshold=1)
+    apprenti = _verdict(session, pc, "skill_rank_gte", target_key="agility", threshold=2)
+    if not initie.met or apprenti.met:
+        fail(f"QA3: a base domain with no row reads {initie.current}, not Initié")
+    if _verdict(session, pc, "skill_rank_gte", target_key=ids["definition"], threshold=1).met:
+        fail("QA3: a skill definition with no row is held")
+    session.add(Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["definition"],
+                      rank=3, change_history=[]))
+    session.commit()
+    held = _verdict(session, pc, "skill_rank_gte", target_key=ids["definition"], threshold=3)
+    if not held.met or held.required_label != "Herboristerie":
+        fail(f"QA3: a definition row at rank 3 gives {held}")
+
+
+def _qa3_quest(session, ids, pc) -> None:
+    from world_engine.models import Agenda, Quest, QuestOffer
+
+    offer = QuestOffer(world_id=ids["world"], giver_entity_id=ids["npc"], title="La fourrure", change_history=[])
+    agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["pc"], title="La fourrure", status="paused",
+                    change_history=[])
+    session.add(offer)
+    session.add(agenda)
+    session.flush()
+    session.add(Quest(world_id=ids["world"], offer_id=offer.id, character_id=ids["pc"], agenda_id=agenda.id))
+    session.commit()
+    ids["offer"] = offer.id
+    if _verdict(session, pc, "quest_completed", target_key=offer.id).met:
+        fail("QA3: quest_completed is met by a paused quest")
+    agenda.status = "completed"
+    session.add(agenda)
+    session.commit()
+    if not _verdict(session, pc, "quest_completed", target_key=offer.id).met:
+        fail("QA3: quest_completed is unmet by a completed quest")
+
+
+def _qa3_wording_and_cleaning(session, ids, pc) -> None:
+    from world_engine.day_plan import RequirementSpec
+    from world_engine.day_resolve import requirement_detail_fr
+    from world_engine.writes.goals_agendas import _clean_requirement
+
+    targets = {
+        "has_met": {"target_entity_id": ids["npc"]},
+        "faction_member": {"target_entity_id": ids["faction"]},
+        "skill_rank_gte": {"target_key": ids["definition"], "threshold": 2},
+        "quest_completed": {"target_key": ids["offer"]},
+    }
+    names = {"has_met": "NPC", "faction_member": "Guilde", "skill_rank_gte": "Herboristerie",
+             "quest_completed": "La fourrure"}
+    for form, target in targets.items():
+        text = requirement_detail_fr(_verdict(session, pc, form, **target))
+        if names[form] not in text:
+            fail(f"QA3: requirement_detail_fr for {form!r} is {text!r}")
+        try:
+            _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, **target))
+        except ValueError as exc:
+            fail(f"QA3: _clean_requirement refuses a well-aimed {form!r}: {exc}")
+    refused = (
+        RequirementSpec(type="faction_member", target_entity_id=ids["npc"]),
+        RequirementSpec(type="skill_rank_gte", target_key="agility", threshold=6),
+        RequirementSpec(type="skill_rank_gte", target_key="no-such-skill", threshold=1),
+        RequirementSpec(type="quest_completed", target_key="no-such-offer"),
+    )
+    for spec in refused:
+        try:
+            _clean_requirement(session, ids["world"], 0, spec)
+        except ValueError:
+            continue
+        fail(f"QA3: _clean_requirement accepts {spec}")
+
+
+def check_qa3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Character
+
+    with Session(engine) as session:
+        ids = _qa3_world(session)
+        pc = session.get(Character, ids["pc"])
+        _qa3_relation_and_meeting(session, ids, pc)
+        _qa3_faction_and_skill(session, ids, pc)
+        _qa3_quest(session, ids, pc)
+        _qa3_wording_and_cleaning(session, ids, pc)
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_qa1()
+    check_qa2(db_path)
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_qa3(engine)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model "
+          "emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, "
+          "and judges what the target feels, encounters, memberships, ranks and completed quests")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index ea238a3..89c35a9 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -188,6 +188,15 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                "skill_definition_id": "sd-{w}"}),
     ("skill_resolution", {"id": "sr-{w}", "world_id": "{w}", "conversation_id": "co-{w}",
                           "surface_form": "s", "verdict": "unmatched"}),
+    ("quest_offer", {"id": "qo-{w}", "world_id": "{w}", "giver_entity_id": "{w}-char",
+                     "title": "q"}),
+    ("quest_offer_step", {"id": "qos-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
+                          "step_order": 1, "objective": "o", "cost": 1}),
+    ("quest_offer_requirement", {"id": "qor-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
+                                 "step_id": "qos-{w}", "type": "has_met",
+                                 "target_entity_id": "{w}-char"}),
+    ("quest", {"id": "qu-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
+               "character_id": "{w}-char", "agenda_id": "ag-{w}"}),
 )
 
 
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 1f39d16..484ab87 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,14 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.17** — TICKET-0108, BRIEF-0108-A: quest offers and quests.
+  `quest_offer`, `quest_offer_step`, `quest_offer_requirement` and `quest`
+  are added. `agenda_step_requirement`'s two CHECKs gain four forms
+  (`has_met`, `faction_member`, `skill_rank_gte`, `quest_completed`), which
+  only the creator authors; `quest_offer_requirement` carries the same two
+  CHECK texts. `migrate_v2_17_quests.py` rebuilds `agenda_step_requirement`
+  from the model (rows copied), creates the four tables, and refuses a
+  database older than v2.16.
 - **v2.16** — TICKET-0107, BRIEF-0107-A: NPC skill sheets and skills
   learned from a master. `skill_definition.requires_master` (default 0) and
   `skill.taught_by_id` (FK `entity`, nullable) are added; an NPC holds skill
diff --git a/world-engine-schema.md b/world-engine-schema.md
index d4dc703..d540925 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.16
+Current schema version: v2.17
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -2205,20 +2205,31 @@ CREATE UNIQUE INDEX idx_agenda_step_one_active
 
 Day-plan precondition gate on one `agenda_step` (schema v1.94, TICKET-0075,
 BRIEF-0075-b). `goal_prerequisite` shape precedent, widened to a closed
-four-form vocabulary (`knowledge`, `relation_gte`, `resource`,
-`location_reachable`) and a `target_key` column for the two forms that gate
-on a string (a knowledge fact id since v2.09, TICKET-0097; a resource tag)
-rather than an entity. The
-per-type shape CHECK is the structural guarantee that an ill-formed row
-cannot exist: `relation_gte`/`location_reachable` require `target_entity_id`
-NOT NULL; `knowledge`/`resource` require `target_key` NOT NULL;
-`relation_gte`/`resource` require `threshold` NOT NULL. Curated plan
-metadata, same family as `npc_schedule` — no `change_history`. THE
-POSITIONAL WALL: `location_reachable`'s target lives HERE, never on
-`agenda_step` — a requirement states "the player must be able to reach L", a
-precondition on the player, never a position of an NPC (see
-BRIEF-0074-a-amendment-1). Written only by `writes.write_day_plan`, read
-only by `day_plan.evaluate_requirements`.
+vocabulary and a `target_key` column for the forms that gate on a string
+(a knowledge fact id since v2.09, TICKET-0097; a resource label; a skill
+key; a quest offer id) rather than an entity. Eight forms since v2.17
+(TICKET-0108, BRIEF-0108-A): `knowledge`, `relation_gte`, `resource`,
+`location_reachable` -- the four the day-plan model may emit
+(`day_plan.MODEL_REQUIREMENT_TYPES`) -- and `has_met`, `faction_member`,
+`skill_rank_gte`, `quest_completed`, authored by the creator only, on a
+quest offer. The per-type shape CHECK is the structural guarantee that an
+ill-formed row cannot exist: `relation_gte`/`location_reachable`/`has_met`/
+`faction_member` require `target_entity_id` NOT NULL;
+`knowledge`/`resource`/`skill_rank_gte`/`quest_completed` require
+`target_key` NOT NULL; `relation_gte`/`resource`/`skill_rank_gte` require
+`threshold` NOT NULL. Meanings: `relation_gte` reads what the TARGET feels
+toward the character (the social row target -> character, v2.17);
+`resource` is the character's money (one currency per world, `target_key`
+a label); `has_met` an encounter row of the pair; `faction_member` an
+active membership of the target faction; `skill_rank_gte` the rank held in
+a base domain or a skill definition (`target_key`), `threshold` 1-5;
+`quest_completed` a quest taken from the offer `target_key` whose agenda is
+`completed`. Curated plan metadata, same family as `npc_schedule` -- no
+`change_history`. THE POSITIONAL WALL: `location_reachable`'s target lives
+HERE, never on `agenda_step` -- a requirement states "the player must be
+able to reach L", a precondition on the player, never a position of an NPC
+(see BRIEF-0074-a-amendment-1). Written by `writes.write_day_plan` and the
+quest acceptance; read by `day_plan.evaluate_specs`.
 
 ```sql
 CREATE TABLE agenda_step_requirement (
@@ -2226,14 +2237,17 @@ CREATE TABLE agenda_step_requirement (
   world_id          TEXT NOT NULL REFERENCES world(id),
   step_id           TEXT NOT NULL REFERENCES agenda_step(id),
   type              TEXT NOT NULL
-                      CHECK (type IN ('knowledge','relation_gte','resource','location_reachable')),
+                      CHECK (type IN ('knowledge','relation_gte','resource','location_reachable',
+                                      'has_met','faction_member','skill_rank_gte','quest_completed')),
   target_entity_id  TEXT REFERENCES entity(id),
   target_key        TEXT,
   threshold         INTEGER,
   CHECK (
-    (type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL)
-    AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL)
-    AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)
+    (type NOT IN ('relation_gte','location_reachable','has_met','faction_member')
+       OR target_entity_id IS NOT NULL)
+    AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed')
+       OR target_key IS NOT NULL)
+    AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
   )
 );
 CREATE UNIQUE INDEX idx_agenda_step_requirement_unique
@@ -2242,6 +2256,105 @@ CREATE UNIQUE INDEX idx_agenda_step_requirement_unique
 
 -----
 
+### `quest_offer`
+
+A quest the creator authored (schema v2.17, TICKET-0108, BRIEF-0108-A, E1).
+The giver is a character or a faction of the world (H1). `status`: `open`
+(proposed to whoever is eligible) or `closed` (proposed to no one); an
+offer is never deleted. `repeatable` (L1): a repeatable offer may be
+accepted again once the last quest taken from it is over; any other offer
+once per character. Its steps and requirements are replaced whole on save
+(the `npc_price` full-replace precedent); the offer row keeps a
+`change_history`. Written only by `writes.write_quest_offer`.
+
+```sql
+CREATE TABLE quest_offer (
+  id               TEXT PRIMARY KEY,
+  world_id         TEXT NOT NULL REFERENCES world(id),
+  giver_entity_id  TEXT NOT NULL REFERENCES entity(id),
+  title            TEXT NOT NULL,
+  summary          TEXT,
+  repeatable       BOOLEAN NOT NULL DEFAULT 0,
+  status           TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
+  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
+  updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
+  change_history   JSON NOT NULL DEFAULT '[]'
+);
+CREATE INDEX idx_quest_offer_world ON quest_offer(world_id);
+```
+
+-----
+
+### `quest_offer_step`
+
+One step of an offer, in order (v2.17). Copied to `agenda_step` when the
+offer is accepted: `cost` and `domain` mean what they mean there.
+
+```sql
+CREATE TABLE quest_offer_step (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  offer_id    TEXT NOT NULL REFERENCES quest_offer(id),
+  step_order  INTEGER NOT NULL,
+  objective   TEXT NOT NULL,
+  cost        INTEGER NOT NULL CHECK (cost BETWEEN 1 AND 4),
+  domain      TEXT
+);
+CREATE UNIQUE INDEX idx_quest_offer_step_order ON quest_offer_step(offer_id, step_order);
+```
+
+-----
+
+### `quest_offer_requirement`
+
+A requirement of an offer (v2.17): with no `step_id`, an ELIGIBILITY
+requirement -- the offer is proposed only to a character who meets all of
+them; with a `step_id`, a requirement of that step, copied to
+`agenda_step_requirement` on acceptance. The vocabulary is
+`agenda_step_requirement`'s, never a second one (B1): its two CHECK texts
+are that table's, byte for byte (checked by `quests.py`).
+
+```sql
+CREATE TABLE quest_offer_requirement (
+  id                TEXT PRIMARY KEY,
+  world_id          TEXT NOT NULL REFERENCES world(id),
+  offer_id          TEXT NOT NULL REFERENCES quest_offer(id),
+  step_id           TEXT REFERENCES quest_offer_step(id),
+  type              TEXT NOT NULL,      -- agenda_step_requirement's type CHECK
+  target_entity_id  TEXT REFERENCES entity(id),
+  target_key        TEXT,
+  threshold         INTEGER
+  -- agenda_step_requirement's shape CHECK
+);
+CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement(offer_id);
+```
+
+-----
+
+### `quest`
+
+An offer a character accepted (v2.17, B1): the link to the agenda the
+acceptance created, born `paused` (A1) -- one open plan among the player's,
+which a day selects or the player pins. Immutable: a quest's state is its
+agenda's status (M1: `active`/`paused` open, `completed`, `failed`,
+`abandoned`). Written only by `writes.accept_quest`.
+
+```sql
+CREATE TABLE quest (
+  id            TEXT PRIMARY KEY,
+  world_id      TEXT NOT NULL REFERENCES world(id),
+  offer_id      TEXT NOT NULL REFERENCES quest_offer(id),
+  character_id  TEXT NOT NULL REFERENCES entity(id),
+  agenda_id     TEXT NOT NULL REFERENCES agenda(id),
+  accepted_at   DATETIME DEFAULT CURRENT_TIMESTAMP
+);
+CREATE UNIQUE INDEX idx_quest_agenda ON quest(agenda_id);
+CREATE INDEX idx_quest_character ON quest(character_id);
+CREATE INDEX idx_quest_offer ON quest(offer_id);
+```
+
+-----
+
 ### `goal_agenda_link`
 
 Many-to-many tie between an `npc_goal` and the `agenda` intrigue(s) it
````

## Scope OUT

- `write_agenda`'s `paused` birth, the quest writers, reads, routes and the pin (B).
- Both surfaces (C).
- Costs, rewards, « déclarer accomplie », objects held in quantity, the indicative unit (TICKET-0109); debts (0110); rank trials (0111).
- The forms not in v1 (3, 6, 7, 10, 11, 13, 14) and a faction-role requirement.
- Renaming `resource`, or giving `ledger` a currency.
- Letting the model's parser accept a creator form; changing the `day_plan` prompt text.
- Running the migration on Nia's database (live gate).
- Every later brief of this lot.

## Invariants to defend

**The schema is authoritative:** model, schema doc, changelog, constant and migration move together, in this commit. **Two canon-write paths:** no new write site here -- the four tables are canon, their writers come in B. **History is sacred:** the rebuild copies every `agenda_step_requirement` row (post-checked). **The model proposes, Python judges:** the day-plan model's vocabulary stays four forms, by construction (`MODEL_REQUIREMENT_TYPES`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- QA2 of `quests.py` fails (the migration on a v2.16-shaped database).
- Any existing `agenda_step_requirement` row would be lost or changed by the migration.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `tooling/verify/checks/world_cascade.py` because another fixture row was appended last: add this brief's four rows at the end of `_FIXTURE` by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quests.py` -> `PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, and judges what the target feels, encounters, memberships, ranks and completed quests`.
- `day_plan.py`, `day_narration.py`, `day_feasibility.py`, `single_canon_write.py`, `world_cascade.py`, `json_ui_boundary.py`, `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py`, `module_budget.py`, `function_length.py`, `pipeline_state.py`, `decisions_index.py`, `claude_md_contract.py` -> `PASS`.
- Mutation tests, each red then reverted: in `_eval_relation_gte`, `            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,` -> `            Relation.entity_a_id == character.id, Relation.entity_b_id == req.target_entity_id,` -> `QA3`; in `_validate_requirement`, `    if req_type not in MODEL_REQUIREMENT_TYPES:` -> `    if req_type not in REQUIREMENT_TYPES:` -> `QA1`; in the migration, `    rebuild = "'quest_completed'" not in _requirement_table_sql()` -> `    rebuild = False` -> `QA2b`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 141/141.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema changelog v2.17, schema doc header and sections, decision entry `A QUEST IS OFFERED, THEN ACCEPTED AS AN OPEN PLAN (TICKET-0108) -- EIGHT REQUIREMENT FORMS, FOUR FOR THE MODEL (BRIEF-0108-a, schema v2.17)` — all in the diff. CLAUDE.md is not touched (no new invariant; 160 characters left).
