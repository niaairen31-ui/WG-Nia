<!-- slug: cascade-fix -->
# BRIEF 0096-B — "the world cascade deletes every world-scoped row, or refuses"

Lot: LOT-0096-world-cascade.md (authoritative on conflict)
Depends on: BRIEF-0096-A (`world_cascade.py` exists and is red)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `tooling/verify/checks/world_cascade.py` exists and
  `WORLD_ENGINE_ENV=test python tooling/verify/checks/world_cascade.py`
  exits 1 with BRIEF-0096-A's Done-means output (42 `W1`, 35 `W3`, 2 `W4`,
  1 `W5`, 2 `W6` lines). If it passes: STOP.
- `src/world_engine/writes/worlds.py` is 91 lines, content per R-01 (10
  subquery triples, 12 direct names, the `prompt_template` delete on line 88).
- `src/world_engine/writes/__init__.py:143`
  `from .worlds import delete_world_cascade`; `__all__` contains
  `"delete_world_cascade",` followed by `"KNOWLEDGE_LEVELS",`.
- `src/world_engine/cockpit/routes/creator.py`: lines 27-28 are
  `from ...event_author import generate_event_draft as _generate_event_draft`
  then `from ...db import get_session`; the `from ...writes import (` block
  (42-48) starts `KNOWLEDGE_LEVELS,` then
  `delete_world_cascade as _delete_world_cascade,`; inside `delete_world`
  (461), the `try:` body's first statement is
  `_delete_world_cascade(world_id, db)` and the handler is one
  `except Exception as exc:` with `db.rollback()` and
  `return {"ok": False, "error": str(exc)}`.
- `src/world_engine/link_author.py` is 914 lines; line 33
  `from sqlalchemy.orm import attributes as sa_attrs`; it ends with
  `commit_batch`'s `return {"committed": committed, "skipped": skipped}`;
  its `from .models import (` block names `LinkBatch` and `LinkBatchRow`.
- `src/world_engine/npc_group_author.py` is 496 lines; line 27
  `from sqlalchemy.orm import attributes as sa_attrs`; line 33 imports
  `Entity, Faction, NpcBatch, NpcBatchRow, PromptTemplate, World`; it ends
  with `patch_npc_row`'s `return row.model_dump()`.
- `tooling/verify/checks/single_canon_write.py:51-52` read:
  ```
  named here, never added silently. The list: `delete_world_cascade`
  (broadest — every row scoped to a world, world row included);
  ```
- `tooling/verify/checks/link_agent_strata.py:50`
  `STRATA_TABLES = ("link_batch", "link_batch_row")`;
  `tooling/verify/checks/npc_agent_strata.py:49`
  `STRATA_TABLES = ("npc_batch", "npc_batch_row")`.

## Facts carried

Verbatim from the lot header.

#### R-01 — the cascade, and the defect measured
Opened: `src/world_engine/writes/worlds.py:1-91` (whole file)
Finding [M]: `_SUBQUERY_SCOPED_DELETES` (24-35) = conversation_message,
gathering_member, batch, pass_play, knowledge, skill, location, faction,
artifact, item. `_DIRECT_WORLD_SCOPED_DELETES` (41-45) = faction_membership,
relation, character, discoverable_detail, proposed_mutation, ledger, event,
gathering, conversation, session, skill_definition, entity. Line 88 deletes
`prompt_template WHERE world_id = :wid`; line 91 the world row. Every write
is an f-string or literal inside `delete_world_cascade` (48-91), after
`PRAGMA defer_foreign_keys = ON` (72).
Measured: `init_db.py` + `seed_pilot.py` on a temp DB, then
`delete_world_cascade("verkhaal")`; `PRAGMA foreign_key_check` before the
commit reports `fact`→world 17, `fact_default`→entity 3 / →world 3,
`fact_participant`→entity 4 / →world 4, `npc_price`→entity 3 / →world 3; the
commit raises `IntegrityError: FOREIGN KEY constraint failed`.
Consequence: no world holding a fact is deletable today. The fix is lists,
not logic: the three-phase shape (subqueries, direct, world row) stays.

#### R-02 — which tables reach `world` (the enumeration behind W1)
Opened: `SQLModel.metadata.tables` after `import world_engine.models`
(the declaring source of every table, column and FK); command in (c).
Finding [M]: 70 tables; 67 reach `world` (a `world_id` column, or an FK to a
table that does); 2 do not (`schema_meta`, `user`), plus `world` itself. The
full classification is case table (b1). No FK declares `ON DELETE CASCADE`
or `SET NULL`; two declare `ON DELETE RESTRICT`: `skill.skill_definition_id`
and `skill_definition.system_id` (same command). Measured on a bare SQLite
connection: with `PRAGMA defer_foreign_keys = ON`, deleting a parent that a
RESTRICT child still references succeeds, and the COMMIT succeeds once the
child is gone too — RESTRICT is deferred as well. Every table with no
`world_id` has at least one direct parent that has one.
Consequence: every world-scoped table is either a direct delete or a
one-level subquery delete, and the order among direct deletes stays free.
The fixture (C-05) sets both RESTRICT keys so that stays proven. `user` and
`schema_meta` are never named.

#### R-04 — runtime entity types cannot be deleted without breaking a law
Opened: `src/world_engine/writes/schema.py:27-40`, `85-94`, `111-155`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:9238-9245` (Ddrop1);
`CLAUDE.md` Invariants (boot guard, rollback contract)
Finding [M]: `create_entity_type` runs `CREATE TABLE ext_<slug>` with
`id TEXT PRIMARY KEY REFERENCES entity(id)` and inserts `entity_type` +
`entity_type_history`. Ddrop1: no `DROP`/`ALTER` exists in `writes/schema.py`,
enforced by `runtime_ddl_guard.py`. Measured: a world with
`create_entity_type(..., slug="navire")`, its `entity_type` and
`entity_type_history` rows deleted along with the rest: the commit succeeds
and `schema_reconcile.unaccounted_tables(engine, session)` returns
`['ext_navire']` — the boot guard would refuse to start the cockpit.
Consequence: decision E1. `entity_type` is a refusing root; `entity_trait`
and `entity_type_history` are its guarded children; nothing in this lot
deletes, drops or renames them.

#### R-06 — prompt templates owned by a world
Opened: `tooling/verify/checks/prompt_version.py:60-68`, `119-143`, `163-173`;
`src/world_engine/models/pipeline.py:415-419`; `scripts/seed_pilot.py:123-150`
and every `upsert_prompt_template(` call in `scripts/`
Finding [M]: `prompt_template.world_id` is nullable (`pipeline.py:419`).
Rule 3 fails on a `text(...)` call naming `prompt_version` outside five
files; rule 5 fails on the text `UPDATE prompt_version` or `DELETE FROM
prompt_version` anywhere in `src/` or the migration, "no allowlist".
Enumeration of every seeded template's `world_id` (36 calls in four
scripts) is pasted in (c): all `None` or absent. The seeded DB holds zero
`prompt_template` rows with a non-null `world_id`.
Consequence: decision D1. `prompt_template` is a refusing root;
`prompt_version` and `prompt_variable` its guarded children. Line 88's
delete goes (a world reaching it is refused first). No brief may write the
text `DELETE FROM prompt_version` anywhere, docstrings included.

#### R-07 — the staging strata forbid their names in `writes/`
Opened: `tooling/verify/checks/link_agent_strata.py:1-35`, `50-58`, `98-107`;
`tooling/verify/checks/npc_agent_strata.py:49-58`, `97-106`
Finding [M]: each check fails when the substring `link_batch` /
`link_batch_row` (resp. `npc_batch` / `npc_batch_row`) appears in any file
under `src/world_engine/writes/`, and when `LinkBatch`/`LinkBatchRow`
(resp. `NpcBatch`/`NpcBatchRow`) is referenced outside an allow-list that
contains `link_author.py` (resp. `npc_group_author.py`) and `cockpit/app.py`.
Measured: adding the four names to `worlds.py`'s lists turns both checks red.
Consequence: decision G1. The four staging tables are purged by functions in
`link_author.py` and `npc_group_author.py` (C-03), called by the route
(C-04). `writes/worlds.py` never contains `link_batch` or `npc_batch` —
not in code, comments or docstrings.

#### R-08 — the delete route and what the modal shows
Opened: `src/world_engine/cockpit/routes/creator.py:42-48`, `460-488`;
`frontend/src/creation/worldCrud.svelte.js:48-60`, `145-160`;
`frontend/src/creation/WorldCrud.svelte:57-67`
Finding [M]: `delete_world(world_id, db)` → 404 if absent; in one `try`:
`_delete_world_cascade`, survivor re-activation, `db.commit()`; `except
Exception` → `db.rollback()` and `{"ok": False, "error": str(exc)}` (HTTP
200). Success → `{"ok": True, "remaining", "active_world_id"}`. The
frontend's local `api()` throws `new Error(body.detail)` on a non-2xx
response with a string `detail`; `worldDeleteConfirm` shows `err.message`
(or `res.error` on `ok: false`) in the modal's red line and keeps the modal
open.
Consequence: a 409 whose `detail` is the French refusal message is shown as
is, with no frontend change and no rebuild.

#### R-09 — the text-regex DELETE guards
Opened: every `tooling/verify/checks/*.py` compiling a regex containing
`DELETE` (enumeration in (c))
Finding [M]: only `encounter_registry.py:101` (`DELETE FROM rencontre`) and
`prompt_version.py:166` (`DELETE FROM prompt_version`) target a table the
cascade touches; `runtime_ddl_guard.py:40` scans `writes/schema.py` only;
`single_canon_write.py:166-167` is the policy scanner (R-11). The cascade's
SQL is an f-string, so neither table-specific regex sees its deletes.
Consequence: C1 is recorded in decision entry b, since no guard makes it
visible. `worlds.py` never contains the literal `DELETE FROM rencontre`.

#### R-10 — a second importer of the cascade
Opened: `src/world_engine/cockpit/routes/mutations.py:86-93`; `grep -rn
delete_world_cascade src`
Finding [M]: `mutations.py` imports `delete_world_cascade as
_delete_world_cascade` and never calls it; `creator.py` is the only caller.
Consequence: REPORT-ONLY; the route of C-04 is the only path.

#### R-11 — the canon-write policy
Opened: `tooling/verify/canon_write_policy.txt:58`;
`tooling/verify/checks/single_canon_write.py:40-80`, `166-201`, `535-560`
Finding [M]: `writes/worlds.py::delete_world_cascade *` is wildcarded.
`check_file` fails only on an unattributable site or a write to a
`[CANON_TABLES]` table outside its allowed sites; the four staging tables
are not canon. The docstring's Section 2 is the named list of hard deletes
("any new hard-delete path must be named here"). Measured on the prototype:
Core `delete(LinkBatchRow)` / `delete(LinkBatch)` in `link_author.py`
(and the NPC pair in `npc_group_author.py`) pass.
Consequence: no policy edit. The two purges join Section 2's list (B item 5).

#### R-12 — the two agent modules
Opened: `src/world_engine/link_author.py:25-60`, `875-914`;
`src/world_engine/npc_group_author.py:19-36`, `470-496`;
`src/world_engine/cockpit/app.py:139-170`
Finding [M]: `link_author.py` is 914 lines, 34 top-level functions, imports
`Session, select` from `sqlmodel` (34) and `LinkBatch, LinkBatchRow` from
`.models` (45-55), no `delete`. `npc_group_author.py`: 496 lines, 17
functions, same `sqlmodel` import (28), `NpcBatch, NpcBatchRow` (33), no
`delete`. `_purge_closed_batches` deletes rows then batches by two Core
`delete()` statements, citing BRIEF-0037-e (no `relationship()`, so no
unit-of-work ordering). `creator.py` does not import `cockpit/app.py`, which
imports `creator.py` (a cycle if reversed).
Consequence: each purge is one function appended to its module (C-03);
`from sqlalchemy import delete` joins each; budgets hold (915-925 / 1000
lines, 35 / 40 functions). `import_cycle.py` passes on the prototype.

#### R-14 — governance files
Opened: `tooling/tickets/TICKET-0095-choice-review.md:1-15`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16899-16935`;
`tooling/verify/checks/decisions_index.py:15-17`; `CLAUDE.md` Invariants
("Hard deletes are a closed, named list -- enforced by
`single_canon_write.py`")
Finding [M]: TICKET-0095 line 5 reads `status: live-gate`. The registry
ends with `---`, a blank line and `*Co-built with Claude, June 2026.*`; new
entries go above that footer. Header regex: `(BRIEF-NNNN-x, no schema
change)` with a lowercase letter. CLAUDE.md delegates the hard-delete list to
`single_canon_write.py`.
Consequence: no CLAUDE.md edit; the named list is updated in
`single_canon_write.py` (B). Regenerate `DECISIONS_INDEX.md` after each
entry.

## Contracts

Verbatim from the lot header.

Two families, each written before its members and re-read after the last:

- **refusal** — one `WorldDeleteRefused` class, one table of refusing roots
  (C-01); members: the `entity_type` refusal and the `prompt_template`
  refusal. Both raise before `PRAGMA defer_foreign_keys`; both messages are
  French, end with a period, and name the offending rows between
  parentheses; the route maps the class, never a message, to 409 (C-04).
- **staging purge** — `purge_world_<agent>_batches(world_id: str, db:
  Session) -> None` (C-03); members: link, npc. Both: rows then batches,
  Core `delete()`, every status, no commit, no flush, called only by the
  route after the cascade.

Re-read after the last member: both refusals and both purges match their
family line for line (checked against the prototype).

#### C-01 — refusal
Produced by: B   Consumed by: C-04, C-05 (W1, W5, W6)
In `src/world_engine/writes/worlds.py`:
```python
class WorldDeleteRefused(ValueError):
    """The world holds a row the cascade must never delete; nothing was
    deleted. The message is shown to the creator as is."""

_REFUSING_TABLES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "entity_type", "name", ("entity_trait", "entity_type_history"),
        "Suppression refusée : ce monde porte des types d'entité personnalisés "
        "({labels}). Leur suppression n'est pas encore prise en charge.",
    ),
    (
        "prompt_template", "id", ("prompt_version", "prompt_variable"),
        "Suppression refusée : ce monde possède des gabarits de prompt propres "
        "({labels}), dont les versions ne sont jamais effacées.",
    ),
)
```
`_refusal(world_id, db) -> str | None`: for each root in order, `SELECT
<label> FROM <root> WHERE world_id = :wid`; the first root with ≥1 row
returns `message.format(labels=", ".join(sorted(labels)))`; else `None`.
Reads only. `WorldDeleteRefused` is exported from `writes/__init__.py`
(import line and `__all__`, after `"delete_world_cascade"`).
Error and empty cases: no refusing row → `None`, the cascade proceeds. Both
kinds present → the `entity_type` message only.

#### C-02 — `delete_world_cascade` (amended)
Produced by: B   Consumed by: C-04, C-05 (W1-W4)
Signature unchanged: `delete_world_cascade(world_id: str, db: Session) ->
None`; the caller owns transaction and commit.
Behaviour, in order:
1. `refusal = _refusal(world_id, db)`; not `None` → `raise
   WorldDeleteRefused(refusal)` — before any PRAGMA or DELETE.
2. `PRAGMA defer_foreign_keys = ON`.
3. Every `_SUBQUERY_SCOPED_DELETES` triple, in tuple order.
4. Every `_DIRECT_WORLD_SCOPED_DELETES` table, in tuple order.
5. `DELETE FROM world WHERE id = :wid`.
No `prompt_template` statement remains. List contents: case table (b1).

#### C-03 — staging purges
Produced by: B   Consumed by: C-04, C-05 (W4)
Appended at the end of `src/world_engine/link_author.py`:
```python
def purge_world_link_batches(world_id: str, db: Session) -> None:
    """Delete every `link_batch` of `world_id` and its `link_batch_row` rows,
    whatever their status (TICKET-0096, BRIEF-0096-B). Called only by the
    world delete route, in its transaction, after `delete_world_cascade`;
    never commits. Children first, by statement order (BRIEF-0037-e)."""
    batch_ids = select(LinkBatch.id).where(LinkBatch.world_id == world_id)
    db.exec(delete(LinkBatchRow).where(LinkBatchRow.batch_id.in_(batch_ids)))
    db.exec(delete(LinkBatch).where(LinkBatch.world_id == world_id))
```
Appended at the end of `src/world_engine/npc_group_author.py`:
```python
def purge_world_npc_batches(world_id: str, db: Session) -> None:
    """Delete every `npc_batch` of `world_id` and its `npc_batch_row` rows,
    whatever their status (TICKET-0096, BRIEF-0096-B). Called only by the
    world delete route, in its transaction, after `delete_world_cascade`;
    never commits. Children first, by statement order (BRIEF-0037-e)."""
    batch_ids = select(NpcBatch.id).where(NpcBatch.world_id == world_id)
    db.exec(delete(NpcBatchRow).where(NpcBatchRow.batch_id.in_(batch_ids)))
    db.exec(delete(NpcBatch).where(NpcBatch.world_id == world_id))
```
Each module gains `from sqlalchemy import delete` on the line before
`from sqlalchemy.orm import attributes as sa_attrs`.
Error and empty cases: no batch → both statements delete nothing.

#### C-04 — `DELETE /api/worlds/{world_id}`
Produced by: B   Consumed by: C-05 (W6), the live gate
In `src/world_engine/cockpit/routes/creator.py::delete_world`, inside the
existing `try`, the call sequence becomes:
`_delete_world_cascade(world_id, db)`, `purge_world_link_batches(world_id,
db)`, `purge_world_npc_batches(world_id, db)`, then the unchanged survivor
logic and `db.commit()`. A new `except WorldDeleteRefused as exc:` BEFORE
`except Exception`: `db.rollback()`, then `raise
HTTPException(status_code=409, detail=str(exc)) from exc`. Outcomes: case
table (b2).

#### C-05 — `tooling/verify/checks/world_cascade.py`
Produced by: A   Consumed by: B (Done means), the ticket gate
Rules W1-W6 as its docstring states; the file is carried verbatim in
BRIEF-0096-A. On `main` (A's state) it FAILS with exactly: one `W1 ...
declares no _REFUSING_TABLES`, 41 `W1 world-reaching table not named`, 35
`W3 fixture row for a table the cascade does not delete`, `W4
purge_world_link_batches / purge_world_npc_batches missing`, `W4 cascade on
a populated world raised IntegrityError`, `W5 world_engine.writes exports no
WorldDeleteRefused`, `W6 refused world did not answer 409`, `W6 populated
world: route answered {'ok': False, ...}` (measured). After B it prints one
`PASS:` line (measured).

## Case tables

Verbatim from the lot header's gate output.

**(b1) Every world-reaching table (R-02) and what deletes it.** `new` marks
an entry this lot adds.

| class | tables |
|---|---|
| direct, existing (12) | faction_membership, relation, character, discoverable_detail, proposed_mutation, ledger, event, gathering, conversation, session, skill_definition, entity |
| direct, new (26) | agenda, agenda_step_requirement, conversation_window_config, day_mention_choice, day_mention_resolution, day_mention_review, day_rewrite, door, fact, fact_default, fact_participant, faction_role, goal_agenda_link, goal_prerequisite, location_type_catalog, npc_goal, npc_price, npc_schedule, observation_run, obstacle, rencontre, skill_resolution, skill_system, unresolved_mention, visit, world_law |
| subquery, existing (10) | conversation_message←conversation, gathering_member←gathering, batch←session, pass_play←session, knowledge←entity, skill←entity (character_id), location/faction/artifact/item←entity (id) |
| subquery, new (9) | agenda_step←agenda, event_entity←event, obstacle_vertex←obstacle, observation_beat / observation_intent / observation_mutation_link / observation_run_template←observation_run (run_id), day_mention_choice_candidate / day_mention_choice_evidence←day_mention_choice (choice_id) |
| staging, purged by owner (4) | link_batch, link_batch_row (link_author); npc_batch, npc_batch_row (npc_group_author) |
| refused root → guarded children (6) | entity_type → entity_trait, entity_type_history; prompt_template → prompt_version, prompt_variable |
| never named (2) | user, schema_meta |

12 + 26 + 10 + 9 + 4 + 6 = 67 = every world-reaching table. Fixture rows:
38 + 19 + 4 = 61 tables.

**(b2) The route (C-04).**

| world state | cascade | purges | HTTP | body / detail | DB after |
|---|---|---|---|---|---|
| absent | not called | not called | 404 | `World '<id>' not found` | unchanged |
| holds an `entity_type` (any status) | raises before any DELETE | not called | 409 | entity-type message | unchanged (rollback) |
| owns a `prompt_template` (no `entity_type`) | raises before any DELETE | not called | 409 | template message | unchanged (rollback) |
| both | raises (entity-type message) | not called | 409 | entity-type message | unchanged |
| neither, deletable | runs | run | 200 | `{"ok": True, "remaining", "active_world_id"}` | world and every row of b1's first four classes gone |
| neither, any other exception | runs | may run | 200 | `{"ok": False, "error": ...}` (unchanged) | unchanged (rollback) |

## Context

BRIEF-0096-A shipped `world_cascade.py`, red on `main`: the cascade names
22 of the 67 world-scoped tables (R-01, R-02). This brief completes the
lists (b1), adds the two refusals Nia locked (E1: a runtime entity type;
D1: a world-owned prompt template), moves the four staging tables to their
owning agent modules (G1, because the strata checks forbid their names in
`writes/`, R-07), and maps a refusal to a 409 the modal already displays
(R-08). No schema change, no frontend change.

## Scope IN

1. **`src/world_engine/writes/worlds.py`** — replace the whole file with
   exactly this content (C-01, C-02, b1):

```python
"""`world` cascade-delete chokepoint (TICKET-0028, BRIEF-0028-b —
decomposed from `writes.py`).

DOCUMENTED EXCEPTION to "History is sacred": `delete_world_cascade` is the
only helper in the codebase that hard-deletes canon. It exists solely for
whole-world block deletion (creator authority, irreversible). No other
delete-side helper may be added here; History is sacred holds everywhere
else. `canon_write_policy.txt` wildcards this one function (`*`) — every
write inside it is sanctioned, which is why `_SUBQUERY_SCOPED_DELETES`
(pure data, not a write) is the only extraction taken from it: every
`db.execute` that writes stays textually inside `delete_world_cascade`
itself so the wildcard entry keeps covering the whole function, unchanged.

The exception covers the world's append-only tables too (`ledger`,
`rencontre`, `skill_resolution`, the day-chain tables): a deleted world
leaves no reader for its history (TICKET-0096, C1). It never covers a
table in `_REFUSING_TABLES`: a world holding such a row is refused before
any delete (TICKET-0096, D1 and E1).

`tooling/verify/checks/world_cascade.py` keeps these three lists equal to
the world-reaching tables of the schema — a new world-scoped table is a red
gate until it is named here.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session


class WorldDeleteRefused(ValueError):
    """The world holds a row the cascade must never delete; nothing was
    deleted. The message is shown to the creator as is."""


# Subquery-scoped deletes (child_table, child_fk_column, parent_table) — run
# BEFORE their parent table is cleared (see delete_world_cascade's
# docstring on ordering). Every parent is a direct table below.
_SUBQUERY_SCOPED_DELETES: tuple[tuple[str, str, str], ...] = (
    ("conversation_message", "conversation_id", "conversation"),
    ("gathering_member", "gathering_id", "gathering"),
    ("batch", "session_id", "session"),
    ("pass_play", "session_id", "session"),
    ("knowledge", "entity_id", "entity"),
    ("skill", "character_id", "entity"),
    ("location", "id", "entity"),
    ("faction", "id", "entity"),
    ("artifact", "id", "entity"),
    ("item", "id", "entity"),
    ("agenda_step", "agenda_id", "agenda"),
    ("event_entity", "event_id", "event"),
    ("obstacle_vertex", "obstacle_id", "obstacle"),
    ("observation_beat", "run_id", "observation_run"),
    ("observation_intent", "run_id", "observation_run"),
    ("observation_mutation_link", "run_id", "observation_run"),
    ("observation_run_template", "run_id", "observation_run"),
    ("day_mention_choice_candidate", "choice_id", "day_mention_choice"),
    ("day_mention_choice_evidence", "choice_id", "day_mention_choice"),
)

# Direct world_id-scoped deletes — order free under the FK deferral.
# `skill_definition` (BRIEF-55, schema v1.63) must still come after the
# subquery-based `skill` delete above so no `skill.skill_definition_id`
# is left pointing at a missing row by commit time (RESTRICT, deferred).
_DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
    "faction_membership", "relation", "character", "discoverable_detail",
    "proposed_mutation", "ledger", "event", "gathering", "conversation",
    "session", "skill_definition", "entity",
    "agenda", "agenda_step_requirement", "conversation_window_config",
    "day_mention_choice", "day_mention_resolution", "day_mention_review",
    "day_rewrite", "door", "fact", "fact_default", "fact_participant",
    "faction_role", "goal_agenda_link", "goal_prerequisite",
    "location_type_catalog", "npc_goal", "npc_price",
    "npc_schedule", "observation_run", "obstacle", "rencontre",
    "skill_resolution", "skill_system", "unresolved_mention", "visit",
    "world_law",
)

# Refusing tables (root_table, label_column, guarded_children, message) —
# a world holding a root row is never deleted: `delete_world_cascade`
# raises `WorldDeleteRefused` before any DELETE. The guarded children hang
# off a root row and are never deleted here either. `entity_type`: its
# `ext_*` table can never be dropped (Ddrop1). `prompt_template`: its
# versions are append-only with no exception. `{labels}` is the sorted,
# comma-separated `label_column` values of the world's root rows.
_REFUSING_TABLES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "entity_type", "name", ("entity_trait", "entity_type_history"),
        "Suppression refusée : ce monde porte des types d'entité personnalisés "
        "({labels}). Leur suppression n'est pas encore prise en charge.",
    ),
    (
        "prompt_template", "id", ("prompt_version", "prompt_variable"),
        "Suppression refusée : ce monde possède des gabarits de prompt propres "
        "({labels}), dont les versions ne sont jamais effacées.",
    ),
)


def _refusal(world_id: str, db: Session) -> str | None:
    """The message of the first refusing table holding a row of `world_id`,
    or None. Reads only."""
    for root, label, _children, message in _REFUSING_TABLES:
        labels = db.execute(
            text(f"SELECT {label} FROM {root} WHERE world_id = :wid"),
            {"wid": world_id},
        ).scalars().all()
        if labels:
            return message.format(labels=", ".join(sorted(labels)))
    return None


def delete_world_cascade(world_id: str, db: Session) -> None:
    """Hard-delete every row scoped to `world_id`, including the `world` row
    itself. Caller owns the transaction and the commit (BRIEF-54).

    Raises `WorldDeleteRefused` before any DELETE when the world holds a row
    of a refusing table (`_REFUSING_TABLES`); nothing is deleted then.

    Sets `PRAGMA defer_foreign_keys = ON` on the session connection before
    any DELETE, so the self-referential columns
    (`location.parent_location_id`, `faction.parent_faction_id`,
    `character.current_location_id`) resolve without nulling — the deferral
    is per-transaction and resets after commit/rollback.

    Statement order below is NOT arbitrary despite the FK deferral: several
    deletes are correlated subqueries against `entity`/`conversation`/
    `gathering`/`session` (e.g. `knowledge` via `entity_id IN (SELECT id FROM
    entity WHERE world_id = :wid)`) — those must run while the referenced
    parent rows still exist, or the subquery returns nothing and orphans get
    left behind. So every subquery-based delete (`_SUBQUERY_SCOPED_DELETES`)
    runs before its parent table is cleared; only the direct
    `world_id`-scoped deletes (`_DIRECT_WORLD_SCOPED_DELETES`, no subquery)
    are free to run in any order relative to each other, per the FK deferral.

    Never touches the `user` table (global accounts, no world scope) nor any
    `prompt_template` row: a world owning one is refused above, and the
    global seeds (`world_id IS NULL`) are shared by every world.
    """
    refusal = _refusal(world_id, db)
    if refusal is not None:
        raise WorldDeleteRefused(refusal)

    db.execute(text("PRAGMA defer_foreign_keys = ON"))
    params = {"wid": world_id}

    for child_table, fk_column, parent_table in _SUBQUERY_SCOPED_DELETES:
        db.execute(
            text(
                f"DELETE FROM {child_table} WHERE {fk_column} IN "
                f"(SELECT id FROM {parent_table} WHERE world_id = :wid)"
            ),
            params,
        )

    for table in _DIRECT_WORLD_SCOPED_DELETES:
        db.execute(text(f"DELETE FROM {table} WHERE world_id = :wid"), params)

    # The world row itself, last.
    db.execute(text("DELETE FROM world WHERE id = :wid"), params)
```

   It must not contain the substrings `link_batch`, `npc_batch`,
   `DELETE FROM rencontre` or `DELETE FROM prompt_version` anywhere,
   comments and docstrings included (R-06, R-07, R-09).

2. **`src/world_engine/writes/__init__.py`** — line 143 becomes
   `from .worlds import WorldDeleteRefused, delete_world_cascade`; in
   `__all__`, insert `    "WorldDeleteRefused",` on the line after
   `    "delete_world_cascade",`.

3. **Staging purges (C-03).**
   - `src/world_engine/link_author.py`: insert `from sqlalchemy import delete`
     on the line before `from sqlalchemy.orm import attributes as sa_attrs`;
     append, after two blank lines at the end of the file,
     `purge_world_link_batches` exactly as in C-03.
   - `src/world_engine/npc_group_author.py`: the same import line at the same
     place; append `purge_world_npc_batches` exactly as in C-03.
   Neither function commits, flushes, or is called from anywhere but item 4.

4. **The route (C-04)** in `src/world_engine/cockpit/routes/creator.py`:
   - after `from ...event_author import generate_event_draft as _generate_event_draft`
     insert
     `from ...link_author import purge_world_link_batches` and
     `from ...npc_group_author import purge_world_npc_batches` (two lines);
   - in the `from ...writes import (` block, insert `    WorldDeleteRefused,`
     after `    KNOWLEDGE_LEVELS,`;
   - in `delete_world`, right after `_delete_world_cascade(world_id, db)`,
     insert `purge_world_link_batches(world_id, db)` then
     `purge_world_npc_batches(world_id, db)` (same indentation);
   - before `    except Exception as exc:` of `delete_world`, insert:
     ```python
         except WorldDeleteRefused as exc:
             db.rollback()
             raise HTTPException(status_code=409, detail=str(exc)) from exc
     ```
   Nothing else in `creator.py` changes. `HTTPException` is already imported
   (the 404 above uses it).

5. **Named hard-delete list.** In `tooling/verify/checks/single_canon_write.py`,
   replace the two docstring lines
   ```
   named here, never added silently. The list: `delete_world_cascade`
   (broadest — every row scoped to a world, world row included);
   ```
   with
   ```
   named here, never added silently. The list: `delete_world_cascade`
   (broadest — every row scoped to a world, world row included; it refuses,
   409 at the route, a world holding an `entity_type` or its own
   `prompt_template` — TICKET-0096, BRIEF-0096-B);
   `purge_world_link_batches` / `purge_world_npc_batches` (TICKET-0096,
   BRIEF-0096-B — a deleted world's ephemeral staging rows, called only by
   the world delete route, after the cascade);
   ```
   No other line of that file changes.

   Items 1-5 are one commit:
   `fix(worlds): delete every world-scoped row, or refuse (TICKET-0096, BRIEF-0096-B)`.

6. **Decision entry.** In `tooling/standards/ARCHITECTURE_DECISIONS.md`,
   insert the following block right after BRIEF-0096-A's entry and above
   the closing `---` line, one blank line before and after:

```markdown
## THE WORLD CASCADE (TICKET-0096) -- EVERY WORLD-SCOPED ROW IS DELETED, OR THE WORLD IS REFUSED (BRIEF-0096-b, no schema change)

**Three kinds of world-scoped table.** `writes/worlds.py` now accounts for
every table `world_cascade.py` derives from the schema:

- *deleted by the cascade* -- `_DIRECT_WORLD_SCOPED_DELETES` (a `world_id`
  column) and `_SUBQUERY_SCOPED_DELETES` (a child reached through a direct
  parent; every parent is a direct table, so one level of subquery is
  enough and runs before any direct delete);
- *refused* -- `_REFUSING_TABLES`: a world holding an `entity_type` (E1) or
  its own `prompt_template` (D1) raises `WorldDeleteRefused` before the
  first statement, and the route answers 409 with the French message, which
  the delete modal already displays (`worldCrud.svelte.js` reads `detail`);
- *purged by their owner* -- the four staging tables (G1).

**C1 -- the BRIEF-54 exception covers append-only tables.** `ledger`
already fell under it; `rencontre`, `skill_resolution`, `visit`
history and the day-chain tables now do too. A deleted world leaves no
reader for its history, and an "archive before delete" is a ticket of its
own (C2's reactivation). The text-regex guards (`encounter_registry` R2,
`prompt_version` rule 5) never see the cascade's f-string SQL; the only
thing that keeps a table out of this exception is its absence from the
lists, which `world_cascade.py` W1 makes explicit.

**E1 -- a runtime type makes its world undeletable, for now.** Deleting the
`entity_type` row would leave its `ext_*` table registered nowhere, and the
boot guard (`schema_reconcile.unaccounted_tables`) would refuse to start
the cockpit -- measured. Dropping the table breaks Ddrop1. Quarantine
(E2, the `rollback_quarantine.py` shape) is its own ticket.

**D1 -- a world's own prompt template refuses the delete.** Its versions
are append-only with no allow-list (`prompt_version.py` rule 5). No code or
seed creates one today, so the refusal costs nothing now. The cascade's
former `DELETE FROM prompt_template WHERE world_id = :wid` statement is
gone: a world that reaches it is refused first.

**G1 -- the staging strata purge themselves.** `link_agent_strata.py` and
`npc_agent_strata.py` forbid those table names in any `writes/` module.
`link_author.purge_world_link_batches` and
`npc_group_author.purge_world_npc_batches` delete a world's batches and
rows (children first, BRIEF-0037-e), never commit, and are called only by
`DELETE /api/worlds/{id}`, after the cascade, in its transaction; a refusal
raises before them. Neither strata check learned an exception (G2).
```

   Run `python tooling/glue/gen_decisions_index.py`; stage
   `DECISIONS_INDEX.md`. Commit:
   `docs(decisions): the world cascade (TICKET-0096, BRIEF-0096-B)`.

## Scope OUT

- `tooling/verify/checks/world_cascade.py`: not edited. If it disagrees with
  the code of items 1-4, the code is wrong or the lot is: STOP.
- Any edit to `link_agent_strata.py`, `npc_agent_strata.py`,
  `prompt_version.py`, `encounter_registry.py`, `runtime_ddl_guard.py` or
  `canon_write_policy.txt` (G2 rejected; D1; C1 recorded in the entry).
- Deleting, dropping, renaming or quarantining any `entity_type`, `ext_*`
  table, `entity_trait` or `entity_type_history` row (E1; E2 is a later
  ticket).
- Deleting any `prompt_template`, `prompt_version` or `prompt_variable` row
  (D1).
- Any frontend file, and any frontend rebuild: the modal already shows the
  409 `detail` (R-08).
- `routes/mutations.py`'s unused import (R-10); the `pipeline_state.py`
  docstring.
- Moving the purges into `cockpit/app.py` (a cycle, R-12) or into any
  `writes/` module (R-07).
- Running anything against Nia's prod DB. The live gate is hers.

## Invariants to defend

- **Hard deletes are a closed, named list** (`single_canon_write.py`): the
  two new purges are hard deletes; item 5 names them in the same commit.
- **History is sacred**: C1 extends the BRIEF-54 exception to the world's
  append-only tables — and only through `delete_world_cascade` on a whole
  world. No other function gains a delete of `ledger`, `rencontre`,
  `skill_resolution`, `visit` or a day-chain table.
- **`prompt_version` is append-only, no allow-list**: nothing deletes it
  (D1).
- **Ddrop1 / the boot guard**: no DDL; a world with a runtime type is
  refused before any statement (E1).
- **The staging strata** (TICKET-0036/0037): no `writes/` module names a
  staging table; the purges live in the allow-listed agent modules (G1).

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- after items 1-5, `world_cascade.py` still fails on anything;
- any check other than `world_cascade.py` turns red, or `corpus_gate.py`
  reports a failure;
- a table appears in `SQLModel.metadata` that reaches `world` and is not in
  case table (b1) (a schema change landed since the lot was drafted);
- the only way to make a gate pass is to edit a check other than item 5's
  docstring lines.

ADAPT:
- the import block of `creator.py`, `link_author.py` or
  `npc_group_author.py` has drifted so the anchor line exists at another
  place: insert relative to that line, report.
- `import_cycle.py` reports a cycle through `creator.py` → an agent module:
  STOP is the default; but if the cycle is only because the agent module
  imports something that imports `routes/creator.py` at module level, move
  the two imports inside `delete_world` (function-level), one commit, report.

REPORT-ONLY:
- line counts of `link_author.py` (expected 925) and `npc_group_author.py`
  (expected 507);
- the wall time of `world_cascade.py`;
- anything else that imports `delete_world_cascade` (expected: `creator.py`,
  `mutations.py` unused).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/world_cascade.py`
      prints `PASS: world_cascade -- every world-scoped table is deleted or
      guarded; a populated world deletes under FK enforcement; refusals
      delete nothing` and exits 0.
- [ ] `grep -nE "link_batch|npc_batch|DELETE FROM (rencontre|prompt_version)" src/world_engine/writes/*.py`
      prints nothing.
- [ ] `link_agent_strata.py`, `npc_agent_strata.py`, `single_canon_write.py`,
      `prompt_version.py`, `encounter_registry.py`, `purge_fk_ordering.py`,
      `runtime_ddl_guard.py`, `import_cycle.py`, `undefined_names.py`,
      `module_budget.py`, `function_length.py`, `decisions_index.py`,
      `pipeline_state.py` → pass.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/run.py --ticket TICKET-0096-world-cascade`
      → `"green": true`, 15 checks PASS.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is
      green (125 checks on the lot's base).
- [ ] On a scratch DB (`WORLD_ENGINE_DATABASE_URL` pointing at a temp file):
      `scripts/init_db.py`, `scripts/seed_pilot.py`, then
      `delete_world("verkhaal", db)` from `routes/creator.py` returns
      `{"ok": True, "remaining": 0, "active_world_id": None}`.
- [ ] `/review-step` then `/close-step`; then `/verify`. The ticket stops at
      `live-gate` (danger class `destructive_data`: Nia's gate, no
      auto-merge).

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 6);
`single_canon_write.py`'s named list (item 5). No schema change, no
CLAUDE.md edit (R-14).
