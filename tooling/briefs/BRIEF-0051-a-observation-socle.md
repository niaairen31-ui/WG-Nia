# BRIEF — Step "observation socle"

## Context

TICKET-0051 builds a scene the creator watches rather than plays: NPCs act
among themselves, every present NPC gets an opportunity each beat, and every
agent decision is recorded. This first step ships **structure and write
chokepoints only** — no loop, no model call, no UI. It exists first because a
loop that runs before the decision tables exist produces unmeasured runs that
must be re-executed.

Decision A3 (RECON-confirmed): observed scenes do NOT reuse `conversation`.
`Conversation.player_id` is `nullable=False` (`models/ephemeral.py:94`) with 49
read sites, several using it as a DEFAULT identity (`analyzer.py:258`,
`analyzer.py:275`) — making it nullable would push `None` through those paths
silently. Observed runs get their own tables instead.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. Take NO action on findings beyond what
Scope IN authorizes. If any finding contradicts this brief, STOP and escalate
rather than adapting the design.

1. **`ProposedMutation`** — which module defines it, whether `proposed_by` is
   nullable, and the exhaustive set of values currently written to it
   (grep the writers, do not infer from the queue reader).
2. **Readers of the proposal queue** — `list_mutations`
   (`cockpit/routes/mutations.py:480-488`) is the reader this brief filters.
   Enumerate EVERY other query selecting `ProposedMutation` by `status`,
   specifically the batch-review path and `_find_applied_duplicate*`
   (`routes/mutations.py:252`, `:291`). Report which ones must NOT be filtered.
   Duplicate detection must keep seeing observed rows; only the creator-facing
   queue is filtered.
3. **DDL atomicity helper** — how the three most recent migration scripts
   (`scripts/migrate_v1_87_*.py`, `_v1_88_*.py`, `_v1_89_*.py`) open their
   transaction, i.e. how the TICKET-0044-f SQLite transactional-DDL fix is
   invoked in practice. Quote the exact idiom. Do NOT restate driver behavior
   from memory — read it.
4. **`gathering`** — exact table name and primary key column, for the FK.
5. **Model package registration** — how `models/__init__.py` exposes table
   classes, and whether `create_db_and_tables` discovers a new module
   automatically or requires an explicit import.
6. **Verify check idiom** — confirm `tooling/verify/checks/schema_0025.py` is
   the closest template (fresh temp-file SQLite DB, `WORLD_ENGINE_DATABASE_URL`
   set before any `world_engine` import, column presence AND CHECK DDL text).
7. **Check registration** — how a new check under `tooling/verify/checks/` is
   picked up by the runner.

## Scope IN

### 1. New model module `src/world_engine/models/observation.py`

Five table classes. NOT added to `ephemeral.py` (that module is documented as
session/scene-lifetime bookkeeping; observation archives outlive a session) and
NOT to `canon.py` (these are not canon). New module, R7 domain-prefixed.

Module docstring, verbatim:

```
"""Observation SQLModel table classes (TICKET-0051, schema v1.90).

Observed-scene instrumentation: a creator watches NPCs act among themselves
and every agent decision is recorded. None of these tables appear in
``canon_write_policy.txt``'s ``[CANON_TABLES]`` — they are observation
telemetry, never durable world canon. A lasting consequence of an observed
run reaches the world only through ``proposed_mutation`` under creator
approval, exactly like a played scene.

Append-only: no row in this module is ever updated in place except
``observation_run``'s terminal ``status`` / ``stop_reason`` / ``ended_at``.
"""
```

**`observation_run`**

| column | type | constraint |
|---|---|---|
| `id` | TEXT | PK, `_uuid` |
| `world_id` | TEXT | NOT NULL, FK `world(id)` |
| `location_id` | TEXT | NOT NULL, FK `entity(id)` |
| `gathering_id` | TEXT | NULL, FK `gathering(id)` |
| `player_presence` | TEXT | NOT NULL DEFAULT `'absent'`, CHECK IN (`'absent'`,`'silent'`,`'active'`) |
| `max_beats` | INTEGER | NOT NULL |
| `quiescence_limit` | INTEGER | NOT NULL |
| `mj_narration` | BOOLEAN | NOT NULL DEFAULT FALSE |
| `cooldown_beats` | INTEGER | NOT NULL |
| `debt_weight` | REAL | NOT NULL |
| `propensity_mode` | TEXT | NOT NULL, CHECK IN (`'flat'`,`'relation_weighted'`) |
| `model` | TEXT | NOT NULL |
| `status` | TEXT | NOT NULL DEFAULT `'running'`, CHECK IN (`'running'`,`'completed'`,`'stopped'`,`'failed'`) |
| `stop_reason` | TEXT | NULL, CHECK (`stop_reason IS NULL OR stop_reason IN ('max_beats','quiescence','creator_stop','error')`) |
| `started_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| `ended_at` | DATETIME | NULL |

Schema NOTE, verbatim:

```
-- NOTE: player_presence is a closed vocabulary, not a boolean, because a
--       SILENT player is still an AUDITOR for disclosure gating (E2) while
--       an ABSENT one is not. Only 'absent' is implemented at v1.90;
--       'silent' and 'active' are named deferrals (TICKET-0051, H2) and the
--       runner refuses them explicitly rather than silently treating them
--       as 'absent'.
-- NOTE: cooldown_beats / debt_weight / propensity_mode are pinned PER RUN,
--       not read from code constants, so that two runs separated by a tuning
--       pass remain attributable. They are not a replay mechanism: the world
--       mutates under play and bit-exact replay is out of scope by decision.
```

**`observation_run_template`** — per-usage prompt pinning (L).

`id` PK; `run_id` NOT NULL FK `observation_run(id)`; `usage` TEXT NOT NULL;
`template_id` TEXT NOT NULL; `version` INTEGER NOT NULL.
UNIQUE (`run_id`, `usage`).

**`observation_beat`**

| column | type | constraint |
|---|---|---|
| `id` | TEXT | PK |
| `run_id` | TEXT | NOT NULL, FK `observation_run(id)` |
| `beat_index` | INTEGER | NOT NULL |
| `outcome` | TEXT | NOT NULL, CHECK IN (`'acted'`,`'silence'`,`'degraded'`,`'event'`) |
| `actor_id` | TEXT | NULL, FK `entity(id)` |
| `line` | TEXT | NULL |
| `mj_narration` | TEXT | NULL |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP |

UNIQUE (`run_id`, `beat_index`).

Schema NOTE, verbatim:

```
-- NOTE: outcome is explicit and never inferred from actor_id being NULL.
--       'silence'  = every candidate declined (a datum: passivity mode (a))
--       'degraded' = every intent call failed (a bug, not a datum)
--       'event'    = a creator-injected event line (no NPC actor)
--       Conflating the first two would let a JSON parse failure be read as
--       "the NPCs are passive" — the exact misreading this table exists to
--       prevent.
```

**`observation_intent`** — one row per NPC per beat, ALWAYS written, including
on failure.

| column | type | constraint |
|---|---|---|
| `id` | TEXT | PK |
| `run_id` | TEXT | NOT NULL, FK `observation_run(id)` |
| `beat_id` | TEXT | NOT NULL, FK `observation_beat(id)` |
| `npc_id` | TEXT | NOT NULL, FK `entity(id)` |
| `act` | BOOLEAN | NOT NULL DEFAULT FALSE |
| `urgency` | INTEGER | NULL |
| `target_id` | TEXT | NULL, FK `entity(id)` |
| `why` | TEXT | NULL |
| `propensity` | REAL | NOT NULL |
| `cooldown_active` | BOOLEAN | NOT NULL |
| `debt_score` | REAL | NOT NULL |
| `final_score` | REAL | NOT NULL |
| `selected` | BOOLEAN | NOT NULL DEFAULT FALSE |
| `call_status` | TEXT | NOT NULL, CHECK IN (`'ok'`,`'parse_error'`,`'timeout'`,`'error'`) |
| `latency_ms` | INTEGER | NULL |
| `raw_response` | TEXT | NULL |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP |

UNIQUE (`beat_id`, `npc_id`).

Schema NOTE, verbatim:

```
-- NOTE: there is deliberately NO not_selected_reason column. A candidate can
--       be excluded by cooldown AND by debt AND by arbitration at once; a
--       single-valued reason would force a precedence and destroy the rest of
--       the information. The COMPONENTS are stored (propensity,
--       cooldown_active, debt_score, final_score) and the reason is DERIVED
--       at read time by a documented precedence:
--         act = FALSE                       -> no_intent
--         cooldown_active = TRUE            -> cooldown
--         selected = FALSE, debt_score < 0  -> debt
--         otherwise                         -> lost_arbitration
--       The arbitration is therefore reconstructible, not merely reported.
-- NOTE: a row is written for every candidate on every beat, including when
--       the model call fails (call_status != 'ok'). A missing row is a bug,
--       never a silent decline.
-- NOTE: latency_ms and raw_response have a DIFFERENT reader from the rest of
--       this table: run feasibility (does a 5-NPC / 30-beat run stay
--       tractable) and parse diagnosis. They are not scene-analysis columns.
```

**`observation_mutation_link`** — provenance without altering a canon table.

`id` PK; `run_id` NOT NULL FK `observation_run(id)`; `beat_id` NULL FK
`observation_beat(id)`; `mutation_id` TEXT NOT NULL FK `proposed_mutation(id)`.
UNIQUE (`mutation_id`).

Schema NOTE, verbatim:

```
-- NOTE: provenance lives here rather than as a column on proposed_mutation
--       so that a canon table is not altered to serve observation telemetry.
--       proposed_by = 'observed_scene' carries the FILTER; this table carries
--       the JOIN back to the run and beat that produced the proposal.
```

### 2. Write chokepoint `src/world_engine/observation_writes.py`

The ONLY module allowed to write `observation_*` rows. Functions:

- `write_observation_run(...)` — inserts the run plus its
  `observation_run_template` rows in ONE transaction. Raises `ValueError` if
  `player_presence != 'absent'` (H2 deferral, refused explicitly, never
  downgraded to `'absent'`).
- `close_observation_run(run_id, status, stop_reason, session)` — the ONLY path
  that sets a terminal `status` / `stop_reason` / `ended_at`. Allows exactly
  `running -> completed | stopped | failed`; any other transition, including
  reopening, raises `ValueError`.
- `write_observation_beat(...)` — insert only. Raises `ValueError` if
  `outcome == 'acted'` and `actor_id` is None, or if `outcome != 'acted'` and
  `actor_id` is not None.
- `write_observation_intent(...)` — insert only.
- `link_observation_mutation(...)` — insert only.

Module-level constant, defined ONCE here and imported everywhere else:

```python
OBSERVED_PROPOSED_BY = "observed_scene"
```

### 3. `canon_write_policy.txt`

Add to the comment block (NOT to `[CANON_TABLES]`, NOT to `[ALLOWED_SITES]`),
verbatim:

```
# TICKET-0051, BRIEF-0051-a: observation_run, observation_run_template,
# observation_beat, observation_intent and observation_mutation_link are
# DELIBERATELY absent from [CANON_TABLES]. They are observation telemetry,
# not durable world canon — same posture as gathering/conversation. Their
# single write chokepoint is src/world_engine/observation_writes.py,
# enforced by tooling/verify/checks/observation_socle.py rather than by this
# file. An observed run reaches canon only through proposed_mutation under
# creator approval.
```

### 4. F3 structural isolation in the queue reader

In `list_mutations` (`cockpit/routes/mutations.py:480-488`), add a NULL-safe
exclusion. `proposed_by != 'observed_scene'` alone is WRONG in SQL: a NULL
`proposed_by` yields NULL, and the row is dropped. Required predicate:

```python
.where(
    (ProposedMutation.proposed_by.is_(None))
    | (ProposedMutation.proposed_by != OBSERVED_PROPOSED_BY)
)
```

Apply to the creator-facing queue reader ONLY. Duplicate-detection paths
(`_find_applied_duplicate*`) must keep seeing observed rows — a filter there
would let an observed proposal be re-proposed as new. If mini-RECON item 2
finds additional creator-facing queue readers, report them and STOP; do not
filter them on your own initiative.

### 5. Migration `scripts/migrate_v1_90_observation_socle.py`

Creates the five tables, using the transactional-DDL idiom found by mini-RECON
item 3. Idempotent: a second run makes no change and reports so. No
`guard-by-table-existence` antipattern.

### 6. Verify check `tooling/verify/checks/observation_socle.py`

Clone the `schema_0025.py` idiom (fresh temp-file SQLite DB, never Nia's real
DB). `FAILURES` list + `_report_and_exit`, `ROOT` via `parents[3]`.

- **Rule 1** — the five tables exist with exactly the columns above.
- **Rule 2** — every CHECK constraint above is asserted against
  `sqlite_master` DDL TEXT, not by column presence. Closed vocabularies:
  `player_presence`, `propensity_mode`, `status`, `stop_reason`, `outcome`,
  `call_status`.
- **Rule 3** — no `observation_*` table name appears in
  `canon_write_policy.txt` `[CANON_TABLES]`.
- **Rule 4** — the identifiers `ObservationRun`, `ObservationRunTemplate`,
  `ObservationBeat`, `ObservationIntent`, `ObservationMutationLink` appear ONLY
  in `models/observation.py`, `models/__init__.py`, `observation_writes.py`,
  the migration script, and this check (stdlib `ast`, module allowlist, same
  shape as `npc_goal_read.py` rule 1).
- **Rule 5** — no `observation_*` model class carries a `not_selected_reason`
  attribute, and the string appears in no table definition (M1 is enforced, not
  merely documented).
- **Rule 6** — `tick.py`, `tick_context.py`, `tick_normalize.py` and
  `context.py` contain zero references to any `Observation*` identifier
  (the "the tick is not this" boundary made mechanical).
- **Rule 7** — `list_mutations` contains a NULL-safe exclusion: its function
  body references `OBSERVED_PROPOSED_BY` AND an `is_(None)` call. Assert BOTH;
  the `is_(None)` half is the whole point of the rule.
- **Rule 8, vacuous-proof guard** — if fewer than 5 tables were inspected or
  fewer than 6 CHECK constraints asserted, FAIL. Zero results is a failure, not
  a pass.

### 7. Docs

- `world-engine-schema.md` — the five table definitions with every NOTE above,
  verbatim. Header bumped to v1.90.
- `world-engine-schema-changelog.md` — newest-first entry for v1.90.
- `ARCHITECTURE_DECISIONS.md` — new section "OBSERVED SCENE — socle and
  decision instrumentation (TICKET-0051, BRIEF-0051-a, schema v1.90)",
  recording A3 (with the RECON evidence that superseded A2), M1, M2, H2's
  closed vocabulary, F3's structural isolation, L reduced to attribution, and
  the named deferral **D-J1** (LLM novelty judge) with its reactivation
  condition.
- `DECISIONS_INDEX.md` — index entries for the above.

## Scope OUT

Name each temptation explicitly. All of these are LATER briefs or standing
deferrals; none is built here.

- **The loop itself.** No runner, no beat execution, no stop condition.
  (BRIEF-0051-d)
- **Any model call.** No intent prompt, no `pt-*` template, no prompt registry
  entry, no arbitration code. (BRIEF-0051-c)
- **Arbitration logic.** `propensity` / `debt_score` / `final_score` are
  COLUMNS here; the formulas that fill them are -c. Do not invent a formula to
  "test" the schema.
- **`context.py`.** E2's decoupling of disclosure intensity from interlocutor
  intensity is BRIEF-0051-b. Do not touch `assemble_npc_context`
  (`context.py:460`) or `_npc_context_speak` (`context.py:314`).
- **`play_initiative.py`.** The existing player-turn initiative vote is NOT
  refactored, generalized, or shared. RECON established it is unusable as-is
  (`_initiative_candidate_data`, `play_initiative.py:415-421`, queries
  relations strictly against `player_id`). A shared abstraction may be
  proposed in -c; it is not created here.
- **`tick.py` / `tick_context.py` / `tick_normalize.py`.** Untouched. The
  observed beat is not a world tick.
- **`conversation` / `conversation_message`.** Untouched. No nullable
  migration, no `mode` column. A3 exists precisely to avoid this.
- **Proposal production.** No observed run emits a `proposed_mutation` yet;
  `observation_mutation_link` ships empty. The filter at item 4 is
  intentionally a filter over an empty set — fail-closed BEFORE a producer
  exists, so no window exists in which a run can pollute the queue.
- **Any cockpit surface.** No route, no tab, no `index.html` change.
  (BRIEF-0051-e)
- **Metrics.** No n-gram overlap, no export script. (BRIEF-0051-f)
- **`player_presence = 'silent'` / `'active'`.** Vocabulary only; the writer
  refuses them. Named deferral H2. `_npc_context_company`
  (`context.py:391`) filters `Character.character_type != "player"` and is the
  site a future `silent` implementation must revisit — recorded, not changed.
- **D-J1**, the LLM novelty judge. Named deferral.
- **D4**, stochastic arbitration weighting. Not taken; no RNG anywhere.
- **The index.html split** and any frontend framework migration.
- **Retention / purge** of observation rows. Append-only, nothing deleted, no
  purge path.

## Invariants to defend

- **Single canon-write authority.** The likeliest failure here is
  over-correction: registering `observation_*` in `canon_write_policy.txt` to
  "be safe". That would be WRONG — it would declare telemetry to be canon.
  The correct posture is absence from `[CANON_TABLES]` plus an explicit comment
  saying why, plus a check enforcing the chokepoint.
- **History is sacred.** Append-only. The only in-place update authorized
  anywhere in this brief is `close_observation_run`'s one-way terminal
  transition.
- **No structure without a reader.** Five tables ship before their consumers.
  Every column's reader is named in the ticket's brief sequence; `latency_ms`
  and `raw_response` are explicitly declared to have a DIFFERENT reader
  (feasibility and parse diagnosis) rather than being passed off as scene
  analysis.
- **Fail-closed over advisory.** The queue filter (item 4) and the writer's
  refusal of unimplemented `player_presence` values both refuse rather than
  degrade.
- **Closed vocabularies need DDL assertions.** A column-presence check passes
  even if the CHECK was dropped (TICKET-0044 lesson). Rule 2 is not optional.
- **JSON storage for UI-visible data is prohibited.** Arbitration parameters
  are real columns, not a JSON blob — they will be displayed and edited in -e.

## Done means

- [ ] `python scripts/migrate_v1_90_observation_socle.py` creates the five
      tables; a second run reports no change.
- [ ] `sqlite3 <db> ".schema observation_intent"` shows the `call_status` CHECK
      with its four values and NO `not_selected_reason` column.
- [ ] `sqlite3 <db> ".schema observation_run"` shows the `player_presence`
      CHECK with its three values.
- [ ] `python tooling/verify/checks/observation_socle.py` exits 0; its output
      names the number of tables inspected and CHECK constraints asserted, and
      both counts are non-zero.
- [ ] Deliberately breaking one CHECK in `models/observation.py` makes the
      check FAIL (the vacuous-pass guard is demonstrated, not assumed). Revert
      after demonstrating.
- [ ] `write_observation_run(..., player_presence="silent")` raises
      `ValueError`.
- [ ] `close_observation_run` twice on the same run raises `ValueError` on the
      second call.
- [ ] `write_observation_beat(outcome="silence", actor_id=<id>)` raises
      `ValueError`.
- [ ] `grep -rn "observation_" src/ --include=*.py` returns hits ONLY in
      `models/observation.py`, `models/__init__.py`, `observation_writes.py`,
      and the `OBSERVED_PROPOSED_BY` import site in `routes/mutations.py`.
- [ ] `GET /api/mutations?status=proposed` returns unchanged results on the
      current DB (the filter is NULL-safe and drops nothing that existed
      before).
- [ ] `world-engine-schema.md` header reads v1.90 and the changelog's newest
      entry is v1.90.
- [ ] `/review-step` and `/close-step` run clean; full-tree verify passes.

## Docs to update

Schema v1.90 entry (changelog) + the five table definitions with verbatim
NOTEs (`world-engine-schema.md`); a new `ARCHITECTURE_DECISIONS.md` section as
specified in Scope IN item 7, including the D-J1 named deferral;
`DECISIONS_INDEX.md` entries. `CLAUDE.md` unchanged — no new invariant, no new
canon-write path.
