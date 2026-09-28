# LOT — TICKET-0096 "World cascade — deleting a world deletes every world-scoped row, or refuses"

Drafted 2026-09-28 over `main` at `03cd252` (merge of PR #125, TICKET-0095).
Every `[M]` finding was measured on a temp-file SQLite DB built from that
checkout; every `[I]` finding was read, not run.

## Objective and cut

`DELETE /api/worlds/{id}` fails on every world holding a fact (R-01). This
lot makes it delete every world-scoped row in one transaction, or refuse
before deleting anything when the world holds a row that must never be
deleted (a runtime entity type, E1; a world-owned prompt template, D1). A new
G1 check derives the world-scoped tables from the schema so the lists can
never fall behind again (B2, F1).

The lot stops there. It does not delete a world holding a runtime type (E2,
own ticket), touch any frontend file, change the schema, or touch Q1b.

## Briefs in this lot

- **A — `cascade-check`**: close TICKET-0095; create
  `tooling/verify/checks/world_cascade.py` (C-05), red on `main` by
  construction; decision entry a.
- **B — `cascade-fix`**: complete `writes/worlds.py` (C-01, C-02), the two
  staging purges (C-03), the 409 route (C-04), the `single_canon_write.py`
  docstring; decision entry b. Turns `world_cascade.py` green.

## Dependency graph

A → B, strictly. B's Done means is `world_cascade.py` passing, and that
check exists only after A. A also closes TICKET-0095, which must happen in
0096's first commit (precedent 0094-A, 0095-A).

The split is a locked choice, not a dependency of code: shipping the gate
red first proves on `main` that it detects the defect (W1, W3, W4, W5, W6
all fire, measured). An executor of B who finds A's check already green has
found a defect, not a shortcut: STOP.

## RECON

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

#### R-03 — FK enforcement and the deferral
Opened: `src/world_engine/db.py:117-126`
Finding [M]: `_enable_sqlite_foreign_keys` runs `PRAGMA foreign_keys=ON` on
every connection. Under `defer_foreign_keys`, a failed COMMIT leaves the
SQLite transaction open: measured, the next `Session` on the same engine
fails `BEGIN` with `cannot start a transaction within a transaction` unless
the failing session called `db.rollback()`.
Consequence: the route already rolls back (R-08). The check (C-05) rolls
back after a failed cascade before opening its next session.

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

#### R-05 — the boot guard's accounting
Opened: `src/world_engine/schema_reconcile.py:46-52`
Finding [M]: `unaccounted_tables(engine, session) -> list[str]`: physical
tables minus `static_table_names()`, minus `registered_runtime_tables(session)`,
minus `_orphan_*`; sorted.
Consequence: C-05 W4 asserts it is `[]` after a delete.

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

#### R-13 — the verify machinery
Opened: `tooling/verify/checks/corpus_gate.py:1-60`, `167`, `224-229`;
`tooling/verify/run.py:10-30`; `tooling/verify/checks/pipeline_state.py:1-60`,
`107-114`; `tooling/verify/checks/module_budget.py:1-14`;
`tooling/verify/checks/function_length.py:26-29`
Finding [M]: `corpus_gate` runs every `*.py` of `checks/` as a subprocess,
15 s timeout each. `run.py --ticket <stem>` reads
`tooling/tickets/<stem>.md` and follows the first arrow per line.
`pipeline_state` fails on EVERY Machine-checkable arrow that does not
resolve once `status` ∈ {brief, exec, verify, live-gate, done} (the
docstring's "at least one" is wrong, 0095 lesson). Module and function
budgets scan `src/` only. Measured on `main`: corpus 124/124 green.
Consequence: the ticket's arrows all name existing checks except
`world_cascade.py`, which A creates in its second commit; pipeline_state is
red on this ticket from deposit until then. The check is one file (a helper
module in `checks/` would itself run as a check); it runs in 1.4 s.

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

#### R-15 — only one active world
Opened: `src/world_engine/models/canon.py:66-80`
Finding [M]: `idx_world_one_active` is UNIQUE on `is_active` WHERE
`is_active = 1`.
Consequence: C-05's fixture worlds are all `is_active = 0`.

## Contract sheet

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

## Gate output

### (a) Property trace

| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| cascade lists' current contents, line 88's template delete | R-01 | `writes/worlds.py` |
| pilot world delete fails, on which tables | R-01 | measured on a temp DB |
| which tables reach `world`; only two `RESTRICT` keys; RESTRICT deferred | R-02 | `SQLModel.metadata` (models), measured |
| FK enforcement on; failed deferred COMMIT leaves txn open | R-03 | `db.py`, measured |
| `ext_*` references `entity`; Ddrop1; boot guard flags an orphan `ext_*` | R-04 | `writes/schema.py`, registry entry, measured |
| `unaccounted_tables` signature and meaning | R-05 | `schema_reconcile.py` |
| rules 3 and 5 of `prompt_version.py`; no world template seeded | R-06 | `prompt_version.py`, `scripts/` enumeration, seeded DB |
| staging names forbidden in `writes/`; allow-lists | R-07 | both strata checks |
| route shape; 409 detail shown by the modal | R-08 | `creator.py`, `worldCrud.svelte.js`, `WorldCrud.svelte` |
| which checks regex-match DELETE on which table | R-09 | enumeration of `checks/` |
| `mutations.py` imports the cascade unused | R-10 | `routes/mutations.py` |
| wildcard; attribution only for canon tables; Section 2 list | R-11 | policy file, `single_canon_write.py` |
| agent modules' size, imports, the Core-delete precedent | R-12 | `link_author.py`, `npc_group_author.py`, `cockpit/app.py` |
| corpus runs every file, 15 s; pipeline_state per-arrow rule | R-13 | `corpus_gate.py`, `run.py`, `pipeline_state.py` (code, lines 107-114) |
| 0095's status line; registry footer; header regex | R-14 | ticket, registry, `decisions_index.py` |
| partial unique index on `world.is_active` | R-15 | `models/canon.py` |

No instruction in either brief says "follow the existing pattern" without
naming the file and the pattern (the Core-delete order names
`cockpit/app.py::_purge_closed_batches`, R-12).

### (b) Case tables

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

**(b3) C-05 outcomes by state (measured).** `main` + A: the FAIL list in
C-05, exit 1, every other check of the corpus green. A + B: `PASS:`, exit
0, corpus 125/125 green, `run.py --ticket TICKET-0096-world-cascade` green
(15/15).

### (c) Enumerations

World-reaching tables (R-02), from `SQLModel.metadata` on `main` (the
command walks `world_id` columns and FKs; the class of each table is case
table b1):
```
70 tables; 67 reach world; non-reaching: ['schema_meta', 'user']
agenda                         world_id=True
agenda_step                    world_id=False
agenda_step_requirement        world_id=True
artifact                       world_id=False
batch                          world_id=False
character                      world_id=True
conversation                   world_id=True
conversation_message           world_id=False
conversation_window_config     world_id=True
day_mention_choice             world_id=True
day_mention_choice_candidate   world_id=False
day_mention_choice_evidence    world_id=False
day_mention_resolution         world_id=True
day_mention_review             world_id=True
day_rewrite                    world_id=True
discoverable_detail            world_id=True
door                           world_id=True
entity                         world_id=True
entity_trait                   world_id=False
entity_type                    world_id=True
entity_type_history            world_id=True
event                          world_id=True
event_entity                   world_id=False
fact                           world_id=True
fact_default                   world_id=True
fact_participant               world_id=True
faction                        world_id=False
faction_membership             world_id=True
faction_role                   world_id=True
gathering                      world_id=True
gathering_member               world_id=False
goal_agenda_link               world_id=True
goal_prerequisite              world_id=True
item                           world_id=False
knowledge                      world_id=False
ledger                         world_id=True
link_batch                     world_id=True
link_batch_row                 world_id=False
location                       world_id=False
location_type_catalog          world_id=True
npc_batch                      world_id=True
npc_batch_row                  world_id=False
npc_goal                       world_id=True
npc_price                      world_id=True
npc_schedule                   world_id=True
observation_beat               world_id=False
observation_intent             world_id=False
observation_mutation_link      world_id=False
observation_run                world_id=True
observation_run_template       world_id=False
obstacle                       world_id=True
obstacle_vertex                world_id=False
pass_play                      world_id=False
prompt_template                world_id=True
prompt_variable                world_id=False
prompt_version                 world_id=False
proposed_mutation              world_id=True
relation                       world_id=True
rencontre                      world_id=True
session                        world_id=True
skill                          world_id=False
skill_definition               world_id=True
skill_resolution               world_id=True
skill_system                   world_id=True
unresolved_mention             world_id=True
visit                          world_id=True
world_law                      world_id=True
```

Every FK's `ondelete` (same session):
```
$ {fk.ondelete for t in T.values() for fk in t.foreign_keys}
{None, 'RESTRICT'}
$ [(t.name, fk.parent.name, fk.column.table.name) ... if fk.ondelete]
[('skill_definition', 'system_id', 'skill_system'),
 ('skill', 'skill_definition_id', 'skill_definition')]
```

Seeded templates' `world_id` (R-06):
```
$ python - # regex over each upsert_prompt_template(...) call
seed_pilot.py: 1 × (absent), 31 × None, 1 × 'WORLD_ID' (false hit: a
  get_or_create(Entity, ...) below the last call, not a template)
apply_ticket_0076 / 0077 / 0094: 1 call each, world_id absent
$ SELECT COUNT(*) FROM prompt_template WHERE world_id IS NOT NULL  -- seeded DB
0
```

DELETE regexes in checks (R-09):
```
$ grep -n "DELETE" tooling/verify/checks/*.py | grep -i "re.compile\|pattern\|search\|findall"
encounter_registry.py:101   UPDATE rencontre | DELETE FROM rencontre
event_tab.py:34,43          @router.delete("/api/events  (route decorator)
graph_primitive.py:317      method: 'DELETE'  (frontend)
npc_schedule.py:447         method: 'DELETE'  (frontend)
prompt_version.py:166       UPDATE|DELETE FROM prompt_version
relation_graph.py:64        method: 'DELETE'  (frontend)
runtime_ddl_guard.py:40     INSERT INTO|DELETE FROM|UPDATE  (writes/schema.py only)
single_canon_write.py:166-167  policy scanner
```

Callers of the cascade (R-10):
```
$ grep -rn "delete_world_cascade" src --include=*.py
writes/worlds.py (definition, docstrings); writes/__init__.py:143,156;
cockpit/routes/creator.py:44 (import), 472 (call);
cockpit/routes/mutations.py:88 (import only)
```

### (d) Families
Refusal and staging purge: written before their members, re-read after the
last (Contract sheet header). ✓

### (e) Satisfiability — gates proposed and gates passed

| gate | module that satisfies it | what the gate forbids that the module needs | resolution |
|---|---|---|---|
| `world_cascade.py` W1-W4 (proposed) | `writes/worlds.py` + C-03 modules | nothing | lists per (b1) |
| `world_cascade.py` W5-W6 (proposed) | `writes/worlds.py`, `routes/creator.py` | nothing | C-01, C-04 |
| `link_agent_strata.py`, `npc_agent_strata.py` (passed) | `link_author.py`, `npc_group_author.py` | staging names in `writes/` | G1: the purges live in the allow-listed agent modules (measured green) |
| `prompt_version.py` rules 3, 5 (passed) | `writes/worlds.py` | `DELETE FROM prompt_version`; `text()` naming it | D1: nothing deletes it; the name appears only as a tuple string (measured green) |
| `encounter_registry.py` R2 (passed) | `writes/worlds.py` | the literal `DELETE FROM rencontre` | f-string SQL; the literal is written nowhere (measured green) |
| `single_canon_write.py` (passed) | all four src files | an undeclared canon write | wildcard for the cascade; staging not canon (measured green) |
| `runtime_ddl_guard.py` (passed) | — | DDL outside `writes/schema.py` | E1: no DDL anywhere |
| `import_cycle.py` (passed) | `routes/creator.py` | a cycle | imports agent modules, never `cockpit/app.py` (measured green) |
| `module_budget.py`, `function_length.py` (passed) | the two agent modules | > 1000 lines / 40 functions / 80-line functions | 925 / 35, 507 / 18, 9-line functions |
| `pipeline_state.py` (passed) | the ticket | an unresolved arrow | A creates `world_cascade.py` before running any gate |
| `decisions_index.py` (passed) | the registry | header drift | regenerate after each entry |

## Amendments

(none)
