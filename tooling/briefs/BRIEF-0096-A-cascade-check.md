<!-- slug: cascade-check -->
# BRIEF 0096-A — "the world cascade gate, red first"

Lot: LOT-0096-world-cascade.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `tooling/tickets/TICKET-0095-choice-review.md:5` reads `status: live-gate`.
- `src/world_engine/writes/worlds.py` is 91 lines; `_SUBQUERY_SCOPED_DELETES`
  (line 24) holds 10 triples ending `("item", "id", "entity")`;
  `_DIRECT_WORLD_SCOPED_DELETES` (line 41) holds 12 names ending `"entity"`;
  line 88 deletes `prompt_template WHERE world_id = :wid`.
- `src/world_engine/writes/__init__.py:143` reads
  `from .worlds import delete_world_cascade`; no name `WorldDeleteRefused`
  exists anywhere under `src/`.
- `src/world_engine/cockpit/routes/creator.py:461`
  `def delete_world(world_id: str, db: Session = Depends(get_session)) -> dict:`;
  its only `except` is `except Exception as exc:` returning
  `{"ok": False, "error": str(exc)}`.
- `src/world_engine/schema_reconcile.py:46`
  `def unaccounted_tables(engine, session: Session) -> list[str]:`.
- `src/world_engine/db.py:117` `def _enable_sqlite_foreign_keys(`.
- Neither `purge_world_link_batches` nor `purge_world_npc_batches` exists
  under `src/`.
- `tooling/verify/checks/world_cascade.py` does not exist.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is
  green on your checkout before any edit (124 checks on `03cd252`; a
  different count is drift if all pass).

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

#### R-03 — FK enforcement and the deferral
Opened: `src/world_engine/db.py:117-126`
Finding [M]: `_enable_sqlite_foreign_keys` runs `PRAGMA foreign_keys=ON` on
every connection. Under `defer_foreign_keys`, a failed COMMIT leaves the
SQLite transaction open: measured, the next `Session` on the same engine
fails `BEGIN` with `cannot start a transaction within a transaction` unless
the failing session called `db.rollback()`.
Consequence: the route already rolls back (R-08). The check (C-05) rolls
back after a failed cascade before opening its next session.

#### R-05 — the boot guard's accounting
Opened: `src/world_engine/schema_reconcile.py:46-52`
Finding [M]: `unaccounted_tables(engine, session) -> list[str]`: physical
tables minus `static_table_names()`, minus `registered_runtime_tables(session)`,
minus `_orphan_*`; sorted.
Consequence: C-05 W4 asserts it is `[]` after a delete.

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

## Contracts

Verbatim from the lot header.

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

Verbatim from the lot header's gate output: (b1) is what W1 and W3 enforce
once B lands; (b3) is this brief's expected outcome.

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

**(b3) C-05 outcomes by state (measured).** `main` + A: the FAIL list in
C-05, exit 1, every other check of the corpus green. A + B: `PASS:`, exit
0, corpus 125/125 green, `run.py --ticket TICKET-0096-world-cascade` green
(15/15).

## Context

`delete_world_cascade` fails on every world holding a fact (R-01): more than
forty world-scoped tables were added since BRIEF-54 and none joined its
hand-written lists. This ticket keeps the lists hand-written and adds a G1
check that derives the truth from the schema (B2) and proves the delete on a
fully populated fixture (F1). This brief ships that check alone, so it is
red on `main` by design and proves it detects the defect; BRIEF-0096-B
fixes the code. It also closes TICKET-0095, whose live gate passed.

## Scope IN

1. **Close TICKET-0095, in its own first commit.** In
   `tooling/tickets/TICKET-0095-choice-review.md`, `status: live-gate`
   becomes `status: done`. Nothing else in that file. Commit message:
   `chore(tickets): close TICKET-0095 — live gate passed (Nia, 2026-09-28)`.

2. **Create `tooling/verify/checks/world_cascade.py`** with exactly this
   content (copy it; do not reformat, reorder or "improve" it — its
   expected output on `main` is measured, C-05):

```python
"""G1 check for TICKET-0096 (BRIEF-0096-A) -- the world cascade deletes every
world-scoped row, or refuses before deleting anything.

`writes/worlds.py::delete_world_cascade` is the one sanctioned hard delete
of a whole world. Its table lists are hand-written; this check keeps them
equal to the schema and proves, on a populated fixture, that the delete
commits under real FK enforcement.

W1 -- coverage (metadata). The world-reaching tables of
   `SQLModel.metadata` (a `world_id` column, or a foreign key to a
   world-reaching table) equal exactly the tables the module names:
   `_DIRECT_WORLD_SCOPED_DELETES`, the children of
   `_SUBQUERY_SCOPED_DELETES`, the roots and guarded children of
   `_REFUSING_TABLES`. No table is named twice; every named table exists.
W2 -- shape. Every direct table has a `world_id` column. Every subquery
   triple `(child, column, parent)` has `child.column` declared as a
   foreign key to `parent`, and `parent` is a direct table.
W3 -- fixture completeness. `_FIXTURE` names exactly the cascaded tables
   (direct plus subquery children), each once.
W4 -- delete. Two worlds carry one fixture row per cascaded table. The
   cascade on one world commits; `PRAGMA foreign_key_check` is empty;
   every table is back to the counts it had before the doomed world was
   built; `schema_reconcile.unaccounted_tables` is empty.
W5 -- refusal. A fixture world that also holds an `entity_type` row, and
   one that also holds its own `prompt_template` with a `prompt_version`,
   each make the cascade raise `WorldDeleteRefused` with the exact message
   below, and no row of any table has changed at that point.
W6 -- route. `DELETE /api/worlds/{id}` (the route function, called
   directly) answers 409 with that message on a refused world, and
   `{"ok": True, ...}` on a populated world.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. Zero cascaded tables, or a W4
count that did not grow when the doomed world was built, is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []

ENTITY_TYPE_MESSAGE = (
    "Suppression refusée : ce monde porte des types d'entité personnalisés "
    "(Navire). Leur suppression n'est pas encore prise en charge."
)
# The ephemeral staging tables (TICKET-0036/0037 strata): no `writes/` module
# may name them, so each agent's own module deletes its world's rows, called
# by the delete route after the cascade (TICKET-0096, G1).
_STAGING_TABLES: tuple[str, ...] = ("link_batch", "link_batch_row", "npc_batch", "npc_batch_row")

PROMPT_MESSAGE = (
    "Suppression refusée : ce monde possède des gabarits de prompt propres "
    "(pt-{w}), dont les versions ne sont jamais effacées."
)

# One row per cascaded table, in insertion order (parents first). `{w}` is
# the world id. Values satisfy every NOT NULL column without a default and
# every CHECK of the schema. `skill.skill_definition_id` and
# `skill_definition.system_id` are set on purpose: they are the schema's two
# ON DELETE RESTRICT keys, so the fixture exercises them too.
_FIXTURE: tuple[tuple[str, dict], ...] = (
    ("entity", {"id": "{w}-char", "world_id": "{w}", "type": "character", "name": "A"}),
    ("entity", {"id": "{w}-loc", "world_id": "{w}", "type": "location", "name": "L"}),
    ("entity", {"id": "{w}-fac", "world_id": "{w}", "type": "faction", "name": "F"}),
    ("entity", {"id": "{w}-art", "world_id": "{w}", "type": "artifact", "name": "R"}),
    ("entity", {"id": "{w}-item", "world_id": "{w}", "type": "item", "name": "I"}),
    ("character", {"id": "{w}-char", "world_id": "{w}", "character_type": "npc"}),
    ("location", {"id": "{w}-loc"}),
    ("faction", {"id": "{w}-fac"}),
    ("artifact", {"id": "{w}-art"}),
    ("item", {"id": "{w}-item"}),
    ("conversation_window_config", {"id": "cwc-{w}", "world_id": "{w}"}),
    ("faction_membership", {"id": "fm-{w}", "world_id": "{w}", "entity_id": "{w}-char",
                            "faction_id": "{w}-fac"}),
    ("faction_role", {"id": "fr-{w}", "world_id": "{w}", "faction_id": "{w}-fac",
                      "name": "r", "created_by": "creator_crud"}),
    ("link_batch", {"id": "lb-{w}", "world_id": "{w}", "scope": "{{}}"}),
    ("link_batch_row", {"id": "lbr-{w}", "batch_id": "lb-{w}", "pair_a_id": "{w}-char",
                        "pair_b_id": "{w}-loc", "kind": "no_links", "payload": "{{}}"}),
    ("location_type_catalog", {"id": "ltc-{w}", "world_id": "{w}", "name": "t"}),
    ("npc_batch", {"id": "nb-{w}", "world_id": "{w}", "scope": "{{}}"}),
    ("npc_batch_row", {"id": "nbr-{w}", "batch_id": "nb-{w}", "line_index": 0,
                       "kind": "draft", "payload": "{{}}"}),
    ("npc_goal", {"id": "ng-{w}", "world_id": "{w}", "npc_id": "{w}-char",
                  "description": "d", "horizon": "short"}),
    ("npc_price", {"id": "np-{w}", "world_id": "{w}", "entity_id": "{w}-char",
                   "tag": "t", "amount": 1}),
    ("npc_schedule", {"id": "ns-{w}", "world_id": "{w}", "npc_id": "{w}-char",
                      "phase": "matin", "location_id": "{w}-loc"}),
    ("obstacle", {"id": "ob-{w}", "world_id": "{w}", "location_id": "{w}-loc"}),
    ("obstacle_vertex", {"id": "obv-{w}", "obstacle_id": "ob-{w}", "vertex_order": 0,
                         "x": 0.0, "y": 0.0}),
    ("relation", {"id": "rel-{w}", "world_id": "{w}", "entity_a_id": "{w}-char",
                  "entity_b_id": "{w}-loc", "type": "knows"}),
    ("rencontre", {"id": "ren-{w}", "world_id": "{w}", "entity_lo_id": "{w}-char",
                   "entity_hi_id": "{w}-loc", "first_at": "2026-01-01 00:00:00",
                   "source": "fixture"}),
    ("session", {"id": "ses-{w}", "world_id": "{w}", "number": 1}),
    ("skill_system", {"id": "ss-{w}", "world_id": "{w}", "name": "s"}),
    ("visit", {"id": "vis-{w}", "world_id": "{w}", "player_id": "{w}-char",
               "location_id": "{w}-loc"}),
    ("world_law", {"id": "wl-{w}", "world_id": "{w}", "text": "t"}),
    ("agenda", {"id": "ag-{w}", "world_id": "{w}", "owner_entity_id": "{w}-char",
                "title": "t"}),
    ("agenda_step", {"id": "ags-{w}", "agenda_id": "ag-{w}", "step_order": 1,
                     "objective": "o"}),
    ("agenda_step_requirement", {"id": "agr-{w}", "world_id": "{w}", "step_id": "ags-{w}",
                                 "type": "knowledge", "target_key": "k"}),
    ("batch", {"id": "bat-{w}", "session_id": "ses-{w}"}),
    ("discoverable_detail", {"id": "dd-{w}", "world_id": "{w}", "location_id": "{w}-loc",
                             "subject": "s", "content": "c"}),
    ("door", {"id": "door-{w}", "world_id": "{w}", "location_id": "{w}-loc",
              "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
    ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t"}),
    ("event_entity", {"id": "eve-{w}", "event_id": "ev-{w}", "entity_id": "{w}-char"}),
    ("fact", {"id": "fa-{w}", "world_id": "{w}", "content": "c",
              "created_by": "creator_crud"}),
    ("fact_default", {"id": "fd-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
                      "scope_type": "world", "level": "knows", "created_by": "creator_crud"}),
    ("fact_participant", {"id": "fp-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
                          "entity_id": "{w}-char"}),
    ("gathering", {"id": "ga-{w}", "world_id": "{w}", "session_id": "ses-{w}",
                   "location_id": "{w}-loc"}),
    ("gathering_member", {"id": "gm-{w}", "gathering_id": "ga-{w}", "entity_id": "{w}-char"}),
    ("goal_agenda_link", {"id": "gal-{w}", "world_id": "{w}", "goal_id": "ng-{w}",
                          "agenda_id": "ag-{w}", "created_by": "creator_crud"}),
    ("goal_prerequisite", {"id": "gp-{w}", "world_id": "{w}", "goal_id": "ng-{w}",
                           "type": "relation_gte", "target_entity_id": "{w}-loc",
                           "threshold": 50}),
    ("knowledge", {"id": "kn-{w}", "entity_id": "{w}-char", "fact_id": "fa-{w}",
                   "subject": "s", "level": "knows"}),
    ("observation_run", {"id": "or-{w}", "world_id": "{w}", "location_id": "{w}-loc",
                         "max_beats": 1, "quiescence_limit": 1, "cooldown_beats": 1,
                         "debt_weight": 1.0, "propensity_mode": "flat", "model": "m"}),
    ("observation_run_template", {"id": "ort-{w}", "run_id": "or-{w}", "usage": "u",
                                  "template_id": "t", "version": 1}),
    ("pass_play", {"id": "pp-{w}", "batch_id": "bat-{w}", "session_id": "ses-{w}",
                   "character_id": "{w}-char", "declared_action": "a"}),
    ("skill_definition", {"id": "sd-{w}", "world_id": "{w}", "name": "Escrime",
                          "base_domain": "agility", "system_id": "ss-{w}"}),
    ("unresolved_mention", {"id": "um-{w}", "world_id": "{w}", "surface": "s",
                            "reason": "r"}),
    ("conversation", {"id": "co-{w}", "world_id": "{w}", "session_id": "ses-{w}",
                      "player_id": "{w}-char"}),
    ("conversation_message", {"id": "cm-{w}", "conversation_id": "co-{w}",
                              "turn_order": 1, "speaker": "s", "content": "c"}),
    ("day_mention_choice", {"id": "dmc-{w}", "world_id": "{w}", "pass_play_id": "pp-{w}",
                            "category": "person", "surface_form": "s",
                            "trigger": "near", "candidate_ids": "[]",
                            "evidence_fact_ids": "[]", "verdict": "accepted",
                            "chosen_entity_id": "{w}-char", "attempts": 1}),
    ("day_mention_choice_candidate", {"id": "dmcc-{w}", "choice_id": "dmc-{w}",
                                      "ordinal": 1, "entity_id": "{w}-char"}),
    ("day_mention_choice_evidence", {"id": "dmce-{w}", "choice_id": "dmc-{w}",
                                     "ordinal": 1, "fact_id": "fa-{w}"}),
    ("day_mention_review", {"id": "dmr-{w}", "world_id": "{w}", "choice_id": "dmc-{w}",
                            "verdict": "agreed", "entity_id": "{w}-char"}),
    ("day_rewrite", {"id": "drw-{w}", "world_id": "{w}", "pass_play_id": "pp-{w}",
                     "generation": 1, "rendered_text": "t"}),
    ("day_mention_resolution", {"id": "dmres-{w}", "world_id": "{w}", "rewrite_id": "drw-{w}",
                                "ordinal": 1, "category": "person", "surface_form": "s",
                                "kind": "named", "verdict": "unmatched"}),
    ("ledger", {"id": "led-{w}", "world_id": "{w}", "entity_id": "{w}-char", "amount": 1}),
    ("observation_beat", {"id": "obb-{w}", "run_id": "or-{w}", "beat_index": 0,
                          "outcome": "silence"}),
    ("observation_intent", {"id": "obi-{w}", "run_id": "or-{w}", "beat_id": "obb-{w}",
                            "npc_id": "{w}-char", "propensity": 0.0,
                            "cooldown_active": 0, "debt_score": 0.0,
                            "final_score": 0.0, "call_status": "ok"}),
    ("proposed_mutation", {"id": "pm-{w}", "world_id": "{w}", "source_type": "fixture",
                           "mutation_type": "fixture", "payload": "{{}}"}),
    ("observation_mutation_link", {"id": "oml-{w}", "run_id": "or-{w}",
                                   "mutation_id": "pm-{w}"}),
    ("skill", {"id": "sk-{w}", "character_id": "{w}-char", "domain": "agility",
               "skill_definition_id": "sd-{w}"}),
    ("skill_resolution", {"id": "sr-{w}", "world_id": "{w}", "conversation_id": "co-{w}",
                          "surface_form": "s", "verdict": "unmatched"}),
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _reaching_tables(tables) -> set[str]:
    reach: dict[str, bool] = {}

    def walk(name: str, seen: frozenset) -> bool:
        if name == "world":
            return True
        if name in seen:
            return False
        table = tables[name]
        if "world_id" in table.c:
            return True
        return any(walk(fk.column.table.name, seen | {name}) for fk in table.foreign_keys)

    for name in tables:
        reach[name] = name != "world" and walk(name, frozenset())
    return {name for name, hit in reach.items() if hit}


def _named_tables(worlds) -> list[str]:
    named = list(worlds._DIRECT_WORLD_SCOPED_DELETES) + list(_STAGING_TABLES)
    named += [child for child, _col, _parent in worlds._SUBQUERY_SCOPED_DELETES]
    for root, _label, children, _message in getattr(worlds, "_REFUSING_TABLES", ()):
        named += [root, *children]
    return named


def rule_w1_w2(tables, worlds) -> None:
    named = _named_tables(worlds)
    for name in sorted({n for n in named if named.count(n) > 1}):
        fail(f"W1 table named twice: {name}")
    for name in sorted(set(named) - set(tables)):
        fail(f"W1 named table does not exist: {name}")
    reaching = _reaching_tables(tables)
    for name in sorted(reaching - set(named)):
        fail(f"W1 world-reaching table not named by the cascade: {name}")
    for name in sorted(set(named) & set(tables) - reaching):
        fail(f"W1 named table does not reach world: {name}")
    for name in worlds._DIRECT_WORLD_SCOPED_DELETES:
        if name in tables and "world_id" not in tables[name].c:
            fail(f"W2 direct table has no world_id column: {name}")
    for child, column, parent in worlds._SUBQUERY_SCOPED_DELETES:
        if child not in tables or column not in tables[child].c:
            fail(f"W2 subquery column missing: {child}.{column}")
            continue
        targets = {fk.column.table.name for fk in tables[child].c[column].foreign_keys}
        if parent not in targets:
            fail(f"W2 {child}.{column} is not a foreign key to {parent}")
        if parent not in worlds._DIRECT_WORLD_SCOPED_DELETES:
            fail(f"W2 subquery parent is not a direct table: {parent}")


def rule_w3(worlds) -> None:
    cascaded = set(worlds._DIRECT_WORLD_SCOPED_DELETES)
    cascaded |= {child for child, _col, _parent in worlds._SUBQUERY_SCOPED_DELETES}
    cascaded |= set(_STAGING_TABLES)
    fixture = {table for table, _row in _FIXTURE}
    if not cascaded:
        fail("W3 vacuous: the cascade names no table")
    for name in sorted(cascaded - fixture):
        fail(f"W3 cascaded table has no fixture row: {name}")
    for name in sorted(fixture - cascaded):
        fail(f"W3 fixture row for a table the cascade does not delete: {name}")


def _insert(db, table: str, row: dict, world_id: str) -> None:
    from sqlalchemy import text

    values = {k: (v.format(w=world_id) if isinstance(v, str) else v) for k, v in row.items()}
    cols = ", ".join(values)
    marks = ", ".join(f":{k}" for k in values)
    db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({marks})"), values)


def _build_world(engine, world_id: str) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    with Session(engine) as db:
        db.execute(text("INSERT INTO world (id, name, is_active) VALUES (:w, :w, 0)"),
                   {"w": world_id})
        for table, row in _FIXTURE:
            _insert(db, table, row, world_id)
        db.commit()


def _counts(db, names) -> dict[str, int]:
    from sqlalchemy import text

    return {n: db.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar_one() for n in names}


def rule_w4(engine, tables) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    import world_engine.link_author as link_author
    import world_engine.npc_group_author as npc_group_author
    from world_engine.schema_reconcile import unaccounted_tables
    from world_engine.writes import delete_world_cascade

    purge_link = getattr(link_author, "purge_world_link_batches", None)
    purge_npc = getattr(npc_group_author, "purge_world_npc_batches", None)
    if purge_link is None or purge_npc is None:
        fail("W4 purge_world_link_batches / purge_world_npc_batches missing")

    names = sorted(tables)
    _build_world(engine, "keep")
    with Session(engine) as db:
        before = _counts(db, names)
    _build_world(engine, "doom")
    with Session(engine) as db:
        grown = _counts(db, names)
    for table in sorted({t for t, _row in _FIXTURE}):
        if grown[table] <= before[table]:
            fail(f"W4 vacuous: fixture added no row to {table}")
    with Session(engine) as db:
        try:
            delete_world_cascade("doom", db)
            for purge in (purge_link, purge_npc):
                if purge is not None:
                    purge("doom", db)
            violations = db.execute(text("PRAGMA foreign_key_check")).fetchall()
            db.commit()
        except Exception as exc:  # noqa: BLE001 -- the regression is an exception
            db.rollback()
            fail(f"W4 cascade on a populated world raised {type(exc).__name__}")
            return
    for row in violations:
        fail(f"W4 foreign_key_check violation: {tuple(row)}")
    with Session(engine) as db:
        after = _counts(db, names)
        for table in names:
            if after[table] != before[table]:
                fail(f"W4 {table}: {after[table]} rows after the cascade, "
                     f"expected {before[table]}")
        leftover = unaccounted_tables(engine, db)
        if leftover:
            fail(f"W4 unaccounted tables after the cascade: {leftover}")


def _refused_world(engine, world_id: str, kind: str) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    _build_world(engine, world_id)
    with Session(engine) as db:
        if kind == "entity_type":
            db.execute(text(
                "INSERT INTO entity_type (id, world_id, name, slug, physical_table) "
                "VALUES (:i, :w, 'Navire', :s, :p)"
            ), {"i": f"et-{world_id}", "w": world_id, "s": f"navire_{world_id}",
                "p": f"ext_navire_{world_id}"})
        else:
            db.execute(text(
                "INSERT INTO prompt_template (id, name, usage, world_id) "
                "VALUES (:i, 'p', 'fixture', :w)"
            ), {"i": f"pt-{world_id}", "w": world_id})
            db.execute(text(
                "INSERT INTO prompt_version (id, prompt_template_id, version_number, "
                "system_prompt, user_template) VALUES (:i, :t, 1, 's', 'u')"
            ), {"i": f"pv-{world_id}", "t": f"pt-{world_id}"})
        db.commit()


def rule_w5(engine, tables) -> None:
    from sqlmodel import Session

    import world_engine.writes as writes

    refused = getattr(writes, "WorldDeleteRefused", None)
    if refused is None:
        fail("W5 world_engine.writes exports no WorldDeleteRefused")
        return

    names = sorted(tables)
    cases = (("refuse_type", "entity_type", ENTITY_TYPE_MESSAGE),
             ("refuse_prompt", "prompt_template", PROMPT_MESSAGE.format(w="refuse_prompt")))
    for world_id, kind, message in cases:
        _refused_world(engine, world_id, kind)
        with Session(engine) as db:
            before = _counts(db, names)
            try:
                writes.delete_world_cascade(world_id, db)
            except refused as exc:
                if str(exc) != message:
                    fail(f"W5 {kind}: message {str(exc)!r}, expected {message!r}")
            except Exception as exc:  # noqa: BLE001 -- any other outcome is the defect
                fail(f"W5 {kind}: the cascade raised {type(exc).__name__} instead of refusing")
            else:
                fail(f"W5 {kind}: the cascade did not refuse")
            if _counts(db, names) != before:
                fail(f"W5 {kind}: rows changed before the refusal")
            db.rollback()


def rule_w6(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import delete_world

    _refused_world(engine, "route_refuse", "entity_type")
    with Session(engine) as db:
        try:
            delete_world("route_refuse", db)
        except HTTPException as exc:
            if exc.status_code != 409 or exc.detail != ENTITY_TYPE_MESSAGE:
                fail(f"W6 refused world answered {exc.status_code} {exc.detail!r}")
        else:
            fail("W6 refused world did not answer 409")
    _build_world(engine, "route_ok")
    with Session(engine) as db:
        result = delete_world("route_ok", db)
    if not (isinstance(result, dict) and result.get("ok") is True):
        fail(f"W6 populated world: route answered {result!r}")


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.writes import worlds

    tables = SQLModel.metadata.tables
    if not hasattr(worlds, "_REFUSING_TABLES"):
        fail("W1 writes/worlds.py declares no _REFUSING_TABLES")
    rule_w1_w2(tables, worlds)
    rule_w3(worlds)
    rule_w4(engine, tables)
    rule_w5(engine, tables)
    rule_w6(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_cascade -- every world-scoped table is deleted or guarded; "
          "a populated world deletes under FK enforcement; refusals delete nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

3. **Decision entry.** In `tooling/standards/ARCHITECTURE_DECISIONS.md`,
   insert the following block above the closing `---` line that precedes
   `*Co-built with Claude, June 2026.*`, with one blank line before it and
   one after it:

```markdown
## THE WORLD CASCADE GATE (TICKET-0096) -- A WORLD-SCOPED TABLE THE CASCADE DOES NOT ACCOUNT FOR IS RED (BRIEF-0096-a, no schema change)

**The defect.** `delete_world_cascade` names its tables by hand. Since
BRIEF-54 more than forty world-scoped tables were added and none joined its
lists, so every world holding a fact failed its commit with `FOREIGN KEY
constraint failed` (measured on a fresh pilot seed: `fact`,
`fact_participant`, `fact_default`, `npc_price`). The route rolled back, so
nothing was ever half-deleted; nothing could be deleted either.

**B2 -- the lists stay hand-written, the gate derives the truth.**
`tooling/verify/checks/world_cascade.py` reads `SQLModel.metadata`: a table
reaches `world` when it has a `world_id` column or a foreign key to a table
that does. That set must equal what the delete accounts for -- the direct
and subquery lists of `writes/worlds.py`, its refusing tables and their
guarded children, and the four staging tables the agents purge. A new
world-scoped table is red until someone decides which of those it is. The
order of statements stays readable in one file; deriving it (B3) was
rejected as implicit behaviour on an irreversible path.

**F1 -- the fixture is a second registry.** One row per covered table, in
two worlds; one world is deleted, the other must be untouched to the row,
`PRAGMA foreign_key_check` must be empty and the boot guard's
`unaccounted_tables` must be empty. A covered table without a fixture row
is red, so the fixture cannot fall behind the lists.

**Created red.** This brief ships the gate before the fix, on purpose: on
`main` it names every missing table (W1, W3), reproduces the IntegrityError
(W4) and finds no refusal (W5, W6). BRIEF-0096-b turns it green.

**Also closed here.** TICKET-0095 (K1) passed its live gate (Nia,
2026-09-28); its front matter moves to `done` in its own commit.
```

   Then run `python tooling/glue/gen_decisions_index.py` and stage
   `tooling/standards/DECISIONS_INDEX.md`.

   Items 2 and 3 are one commit:
   `test(verify): world_cascade gate — red on main by design (TICKET-0096, BRIEF-0096-A)`.

## Scope OUT

- Any edit to `src/` — `writes/worlds.py`, `writes/__init__.py`,
  `routes/creator.py`, `link_author.py`, `npc_group_author.py`: BRIEF-0096-B.
- Any edit to `single_canon_write.py`, either strata check, `prompt_version.py`,
  `encounter_registry.py` or `canon_write_policy.txt`.
- Making `world_cascade.py` pass on `main` by editing its rules, its fixture
  or its expected messages.
- `routes/mutations.py`'s unused import of the cascade (R-10): not touched.
- The `pipeline_state.py` docstring mismatch (R-13): not touched.
- Deleting a world that holds a runtime entity type (E2): a later ticket.
- CLAUDE.md: no edit (R-14).

## Invariants to defend

- "History is sacred" / hard deletes are a closed list: this brief deletes
  nothing and adds no delete path; the check's fixture runs only on a
  temp-file DB it creates (`WORLD_ENGINE_DATABASE_URL` set before import).
  If you find the check touching any other DB, STOP.
- The corpus gate stays the proof that every check runs: `world_cascade.py`
  is picked up by discovery, no registration needed.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `world_cascade.py` on your checkout PASSES, or fails with a W-line absent
  from C-05's list, or with a count other than 42 `W1` lines and 35 `W3`
  lines — the lot's measurement no longer describes `main`;
- `world_cascade.py` raises (a Python traceback instead of `FAIL:` lines);
- any check other than `world_cascade.py` and `corpus_gate.py` turns red.

ADAPT:
- the check runs longer than 5 s on your machine but under the 15 s
  corpus timeout: proceed, report the time.
- `gen_decisions_index.py` reports a record count other than the previous
  count + 1: proceed if `decisions_index.py` passes, report both counts.

REPORT-ONLY:
- the wall time of `world_cascade.py`;
- any table you notice in `models/` that you believe is world-scoped and
  absent from case table (b1).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `git log --format=%s -3` shows item 1's message on its own commit, then
      item 2-3's; `grep -n "^status:" tooling/tickets/TICKET-0095-*.md`
      prints `5:status: done`.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/world_cascade.py`
      exits 1 and prints exactly: 42 lines starting `FAIL: W1 `, 35 starting
      `FAIL: W3 `, and these five lines:
      `FAIL: W4 purge_world_link_batches / purge_world_npc_batches missing`,
      `FAIL: W4 cascade on a populated world raised IntegrityError`,
      `FAIL: W5 world_engine.writes exports no WorldDeleteRefused`,
      `FAIL: W6 refused world did not answer 409`,
      `FAIL: W6 populated world: route answered {'ok': False, ...`.
- [ ] `python tooling/verify/checks/pipeline_state.py` passes (every arrow of
      TICKET-0096 resolves).
- [ ] `python tooling/verify/checks/decisions_index.py` passes.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py`
      reports exactly one failed check: `world_cascade.py`.
- [ ] No file under `src/` differs from `main`
      (`git diff --stat main -- src` is empty).
- [ ] `/review-step` then `/close-step` (no engine code touched: the review
      covers the check and the registry entry).

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 3). No schema
change, no CLAUDE.md edit.
