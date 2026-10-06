# LOT — TICKET-0106 "A skill progresses from Inexpérimenté to Maître, a point per roll"

## Objective and cut

A player's skill has a rank among six fixed in the engine (Inexpérimenté,
Initié, Apprenti, Confirmé, Expert, Maître) and the points earned within it,
in place of today's tier (G1, T1, U2). The dice read the rank through a
modifier table that keeps every former tier's roll (L1). Every roll earns one
point (M2, N2): in Play through an auto-applied `skill_progress` mutation, in
a day when Nia approves the step (Q1, S1). Reaching a threshold moves the
skill up one rank (K1). A world names its ranks and sets the default points
to leave each one; a system and a skill may override any of them, the most
specific winning (O1, P2, V). The points are shown on the PC's fiche and in
the day's account; Play stays sealed and carries them on its verdict event
only (Y1b).

The lot stops before: NPC skill sheets and teaching (I1), rank trials with
requirements (K1's quest half), quests, debts, any cap on points (N2), and
any change to `legacy.html`.

## Briefs in this lot

- **A — schema v2.15, rank replaces tier**: `skill.rank`/`skill.xp`,
  `points_to_rank_1..5` on `skill_system` and `skill_definition`,
  `skill_rank`; `skill_ranks.py`; both rolls read `rank_modifier`; the PC
  sheet routes and fiche speak ranks; `migrate_v2_15_skill_ranks.py`; check
  `skill_progression.py` created (A1-A4).
- **B — a roll earns a point** (no schema change): `write_skill_progress`;
  `cockpit/skill_progress.py` (applier, `record_roll`, `grant_step_roll`);
  `_apply_mutation` dispatches `skill_progress`; Play's verdict carries
  `progress`; the step change applier grants the day's point (B1-B4).
- **C — the creator sets the ranks** (no schema change): `upsert_skill_rank`,
  `PUT /api/skill-ranks`, thresholds on the system and skill routes; the
  « Rangs du monde » record and the threshold fields in Création ›
  Compétences (C1-C3).
- **D — the points are shown** (no schema change): the day's account lists
  the points of rolled steps; the PC fiche shows points out of the threshold
  (D1-D2).

## Dependency graph

Strictly sequential, A → B → C → D.

- B writes `skill.xp`/`skill.rank` (A) through `skill_ranks.points_to_next`
  (A).
- C writes `skill_rank` (A) and the threshold columns (A); C's precedence
  reads A's `points_to_next`.
- D reads the day's step changes B grants, and the sheet fields A serves.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/skill_progression.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A, C and D each rebuild
  `static/`.
- A creates `skill_progression.py` because every Machine arrow of the ticket
  must resolve from `brief` status on (`pipeline_state.py`).
- C before D is an order chosen, not a dependency: D's displays would work
  on A and B alone.

## RECON

Opened on `main` at `a5fbc1e` (merge of PR #136, `ticket/0105`), schema
v2.14. Then prototyped on a copy (branch `proto/0106`): every brief's commit
ran the full corpus green (138/138 on `main`, 139/139 from A on, with
`WORLD_ENGINE_ENV=test`), and the four diffs replayed in order on a clean
worktree of `main` reproduce the prototype tree exactly (generated files —
the decision index and the built frontend — regenerated; only the build
manifest's `built_at` differs). Findings tagged [M] were measured.

### R-01 — the skill row and the NPC's tier [M]
Opened: `src/world_engine/models/canon.py:633-666` (`Skill`: `tier`
`CheckConstraint("tier BETWEEN -1 AND 2", name="ck_skill_tier")`, server
default 0, `change_history` JSON, `skill_definition_id` FK RESTRICT);
`:574` (`BASE_SKILL_DOMAINS`); `:581-593` (`SkillSystem`: exactly `id,
world_id, name, description, created_at, updated_at`); `:599-630`
(`SkillDefinition`, `ck_skill_definition_base_domain`); `:175-177`
(`Character.physical_tier`); `src/world_engine/cockpit/routes/creator.py:
690-701` (PC creation seeds the four base rows and one row per definition,
`tier=0`).
Finding: the tier is the 2d6 modifier itself (R-03); only player characters
have skill rows; an NPC has one `physical_tier` (-1..2).
Consequence: `rank` (0-5) and `xp` replace `tier`; a new row starts at rank
1, the former tier 0; NPCs are untouched (I1 is its own ticket).

### R-02 — every reader and writer of the tier [M]
Opened: enumeration E1; `src/world_engine/writes/characters.py:53-85`
(`write_skill_tier`, history entry `{tier, changed_at, by}`);
`src/world_engine/cockpit/crud/skills.py:90-153` (`SKILL_TIERS`,
`_skill_dict`, `list_skills`, `SkillTierBody`, `update_skill_tier`),
`:375-392` (`create_skill_definition`'s backfill, `tier=0`);
`src/world_engine/cockpit/crud/__init__.py:208-222` (re-exports);
`frontend/src/creation/PjSkillFiche.svelte:39-41, 106-121, 155-162`;
`scripts/seed_pilot.py:3401-3466`; enumeration E5.
Finding: seven Python sites, the seed script, the PC fiche, and an import of
`write_skill_tier` in eleven `crud/*.py` modules (an unused shared import
block). `scripts/migrate_v1_65_pc_skill_backfill.py` inserts a `tier` by raw
SQL: a one-time historical migration (allow-listed in `env_guard.py`).
Consequence: A rewrites every live site in one commit (dropping the column
breaks them all at once); the historical migration is left alone.

### R-03 — the dice [M]
Opened: `src/world_engine/resolution.py:29-45` (`resolve_physical`: 2d6 +
`player_tier - npc_tier`; <=6 failure, 7-9 partial, >=10 success); E3.
Finding: two callers — `play_physical.py:207` (opposition from
`physical_tier`) and `day_resolve.py:224` (`npc_tier=0`).
Consequence: both read `rank_modifier(rank)`; `resolution.py` is not
touched.

### R-04 — the Play stream is read-only [M]
Opened: `tooling/verify/checks/stream_session_readonly.py:1-80` (rules 1-3:
no write on, and no delegation of, the request session `ctx.db`);
`src/world_engine/cockpit/play_physical.py:137-150` (`skill_lexicon.record`
on its own `Session(engine)`, the precedent).
Consequence: `record_roll` takes ids, never `ctx.db`, and opens its own
session.

### R-05 — `play_physical.py` at its cap [M]
Opened: `tooling/verify/checks/module_budget.py:56-59` (`MAX_LINES = 1000`);
`wc -l src/world_engine/cockpit/play_physical.py` → 996;
`play_physical.py:18` (`from .. import llm_parse, ollama_client,
skill_lexicon`), `:54` (`from .play_discovery import ...`), `:152-215`
(`_say_physical_resolve_verdict`, `:195` the tier read, `:214` the verdict
event line).
Consequence: A changes two lines in place (imports joined to `:18`); B adds
two (one import, one call) — 998 lines. Any other growth is a STOP.

### R-06 — a day writes no canon until approved [M]
Opened: `src/world_engine/day_resolve.py:1-56` (module docstring: REPLAY
re-rolls, V1 no canon), `:165-177` (`_step_player_tier`), `:206-228`;
`src/world_engine/day_mutations.py:106-145` (`_step_action`: a blocked step
emits no `agenda_step_change`; failure → `fail`, else `complete`);
`src/world_engine/cockpit/mutations.py:827-884`
(`_mutation_apply_agenda_step_change`: stale guard `step.status ==
"active"`, then status writes).
Finding: every emitted `agenda_step_change` whose step has a `domain` was
rolled; replays re-propose, and the stale guard applies one per step.
Consequence: the day's point is granted inside that applier, from
`step.domain`, never at the roll and never from the payload.

### R-07 — the dispatcher and the approval path [M]
Opened: `src/world_engine/cockpit/routes/mutations.py:420-470`
(`_apply_mutation`, lazy `from .. import mutations as _mutations`,
`appliers` dict), `:600-630` (`_approve_apply_and_commit`: SAVEPOINT, status
`applied` + `applied_at`, else `approved` with the error in
`creator_notes`), `:300-400` (`_find_applied_duplicate`: types without a
branch fall through unguarded, the docstring lists them);
`src/world_engine/models/pipeline.py:99-144` (`ProposedMutation`).
Consequence: `skill_progress` joins the `appliers` dict and the docstring's
accumulating list; `record_roll` reuses `_approve_apply_and_commit`.

### R-08 — auto-applied mutations [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:439-456` (four
conditions; `item_update` the sole, dormant member; « Any extension of this
category is a creator decision, recorded here. »); `:1134-1135` and
`CLAUDE.md:196-198` (`proposed_by='engine'` proposals are never
auto-applied); `CLAUDE.md:163-164` (two canon-write paths).
Consequence: Q1 is recorded in that section; the tag is `engine_roll`,
never `engine`; one CLAUDE.md invariant names it.

### R-09 — sanctioned canon writes [M]
Opened: `tooling/verify/canon_write_policy.txt:1-7` (`[CANON_TABLES]`),
`:24` (`write_skill_tier skill`), the `crud/skills.py` entries;
`tooling/verify/checks/single_canon_write.py:1-60, 180-206`.
Consequence: `write_skill_tier` is renamed `write_skill_rank`;
`write_skill_progress` and `upsert_skill_rank` are new allowed sites;
`skill_rank` joins `[CANON_TABLES]`.

### R-10 — Play is sealed [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:12263-12267` (A3:
`legacy.html` byte-untouched); `tooling/verify/checks/module_budget.py:61-65`
(`LEGACY_DOCUMENT_LINE_CEILING = 2762`, fails on growth and on shrinkage);
`src/world_engine/cockpit/legacy.html:1269-1273` (stores `token.verdict`),
`:1408-1421` (`_appendVerdict` reads `domain, dice, modifier, total,
band`).
Finding: an extra key on the verdict object is ignored by the client.
Consequence: Y1b — `progress` rides on the verdict event; `legacy.html` is
not in any diff.

### R-11 — the shape check of `skill_system` [M]
Opened: `tooling/verify/checks/skill_system_shape.py:1-35`
(`EXPECTED_SKILL_SYSTEM_COLUMNS`, « no extras »).
Consequence: A adds the five threshold columns to that set, by name.

### R-12 — the world cascade [M]
Opened: `src/world_engine/writes/worlds.py:35-77`
(`_DIRECT_WORLD_SCOPED_DELETES`, `skill` deleted by subquery before
`skill_definition`); `tooling/verify/checks/world_cascade.py:1-40` (W1
coverage, W3 fixture), `:110` (`skill_system` fixture row), `:185-186`
(`skill` fixture row, no `tier`).
Consequence: `skill_rank` joins the direct list and the fixture; the
threshold columns ride with their parents.

### R-13 — rebuilding three tables [M]
Opened: E2 (no FK references `skill.id`; `skill.skill_definition_id` and
`skill_resolution.skill_definition_id` reference `skill_definition`;
`skill_definition.system_id` references `skill_system`);
`scripts/migrate_v1_95_parked_plans.py:59-102` (rebuild on a raw DBAPI
connection, `PRAGMA foreign_keys=OFF` and `legacy_alter_table=ON` before
`BEGIN`, rename, create from the model, copy, drop);
`scripts/migrate_v2_14_passage.py` (env guard, refusal below the previous
version, post-checks, `schema_meta` convergence); the v2.14 DDL of the
three tables, dumped from a database created on `main` (embedded verbatim in
`skill_progression.py`, `_V214_DDL`).
Finding: SQLite adds no table CHECK and drops no column a table CHECK names.
Consequence: the three tables are rebuilt from the models in one raw
transaction, parents first, by column name (never by DDL text, which may
differ on an older production file).

### R-14 — Création › Compétences [M]
Opened: `frontend/src/creation/competences.svelte.js:1-251` (record
factories, `loadCatalogue`, `saveCompetenceRecord` routing by `kind`);
`CompetencesList.svelte:1-121`; `CompetencesSheet.svelte:1-182`;
`frontend/src/creation/Sheet.svelte:508-525` (`saveCompetenceSheet`: every
record of the tab goes through `saveCompetenceRecord`, then
`enterViewMode(saved)` and a selection of `saved.id`).
Consequence: a third record kind, `ranks`, needs no shell change.

### R-15 — the day's account [M]
Opened: `src/world_engine/cockpit/routes/day.py:231-266` (`_account_gains`,
skill block `produced: []` and the « pas encore » note), `:309-347`
(`_day_account_dict`, the one caller, holds `db`);
`frontend/src/journee/Journee.svelte:145-160`.
Consequence: `_account_gains` takes `db` and reads each step's `domain`.

### R-16 — where a curated-config table lives [M]
Opened: `src/world_engine/models/config.py:1-34` (split out of `canon.py`
for its budget; `conversation_window_config`: absence of a row is legal,
the reader applies defaults and never writes on read);
`src/world_engine/writes/config.py:1-40` (`upsert_*` family, never a
DELETE).
Consequence: `SkillRank` goes to `models/config.py`; `upsert_skill_rank`
to `writes/config.py`; no ladder row is seeded.

### R-17 — documentation contracts [M]
Opened: `tooling/verify/checks/decisions_index.py:15-40` (strict header:
lowercase brief letter, `(BRIEF-0106-a, schema v2.15)`);
`tooling/standards/ARCHITECTURE_DECISIONS.md` tail (the `---` /
`*Co-built…*` footer stays last); `CLAUDE.md` 37 401 characters of 38 000
(`claude_md_contract.py`); `world-engine-schema.md:3`,
`src/world_engine/schema_version.py:15`.
Consequence: four decision entries above the footer; CLAUDE.md gains one
invariant (+240 characters) and one wording change.

### R-18 — the checks the lot passes [M]
Opened: E4 and the corpus on `main` (138/138); `single_canon_write.py`,
`stream_session_readonly.py`, `import_cycle.py`, `module_budget.py`,
`function_length.py`, `undefined_names.py`, `world_cascade.py`,
`skill_system_shape.py`, `json_ui_boundary.py` (`Skill.change_history`
allowed), `effects_vocab.py`, `day_mutations.py`, `frontend_build_fresh.py`,
`schema_version_agreement.py`, `schema_partition.py`, `env_guard.py`,
`pipeline_state.py`, `decisions_index.py`, `claude_md_contract.py`.
Consequence: named per brief in its Done means.

### R-19 — a migration converges to the code's version [M]
Opened: `scripts/migrate_v2_14_passage.py:355-369`
(`_converge_schema_meta` writes `EXPECTED_STATIC_SCHEMA_VERSION`, whatever
it is).
Finding: run on v2.15 code against a v2.13 database, the v2.14 migration
would mark it v2.15 without the skill rebuild. Production is at v2.14.
Consequence: REPORT only; the live gate runs v2.15 alone.

## Contract sheet

### C-01 — the schema (v2.15)
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-B, C, D
`skill`: `rank INTEGER NOT NULL DEFAULT 1` (`ck_skill_rank`: `rank BETWEEN
0 AND 5`), `xp INTEGER NOT NULL DEFAULT 0` (`ck_skill_xp`: `xp >= 0`), no
`tier`. `skill_system` and `skill_definition`: `points_to_rank_1` ..
`points_to_rank_5` nullable INTEGER, one CHECK each
(`ck_skill_system_rank_points`, `ck_skill_definition_rank_points`, text
`models.canon.RANK_POINTS_CHECK`: each NULL or >= 1). `skill_rank(id,
world_id FK world NOT NULL, rank INTEGER NOT NULL, label TEXT NOT NULL,
points_to_next INTEGER, updated_at)`, `ck_skill_rank_rank` (0-5),
`ck_skill_rank_points` (`(rank = 5 AND points_to_next IS NULL) OR (rank < 5
AND points_to_next >= 1)`), UNIQUE `idx_skill_rank_world_rank(world_id,
rank)`; model `SkillRank` in `models/config.py`, exported by `models`;
cascaded with the world.
Error and empty cases: the migration refuses below v2.14 and on a tier
outside -1..2, before any change.

### C-02 — the ladder (`skill_ranks.py`)
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-B, C, D
`RANKS = (0..5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`, `RANK_MODIFIERS =
(-1, 0, 1, 2, 2, 3)`, `DEFAULT_RANK_LABELS = ("Inexpérimenté", "Initié",
"Apprenti", "Confirmé", "Expert", "Maître")`, `DEFAULT_POINTS_TO_NEXT = (5,
10, 20, 40, 80)`, `TIER_TO_RANK = {-1: 0, 0: 1, 1: 2, 2: 3}`,
`RANK_POINTS_COLUMNS` (index = rank left). `RankStep(rank, label,
points_to_next)` frozen. `rank_modifier(rank) -> int` (`ValueError` outside
0-5). `default_ladder() -> tuple[RankStep, ...]`. `world_ladder(db,
world_id) -> tuple[RankStep, ...]` (six, index = rank; rows over defaults;
never writes). `points_to_next(rank, ladder, *, system=None,
definition=None) -> Optional[int]` (definition's column, else system's,
else the ladder's; None at MAX_RANK). `skill_owners(db, skill_definition_id)
-> (system | None, definition | None)`. `skill_points_to_next(db, *,
world_id, rank, skill_definition_id) -> Optional[int]`.

### C-03 — a creator's rank edit
Produced by: BRIEF-0106-A   Consumed by: the PC fiche
`writes.write_skill_rank(db, *, skill_id, rank, changed_by="creator") ->
Skill`: `ValueError` outside `RANKS` or on an unknown row, before any
write; appends `{rank, xp, changed_at, by}` (the previous values), sets
`rank`, `xp = 0`, `updated_at`. `PATCH /api/skills/{id}` body `{rank}`
(`SkillRankBody`): 404 unknown, 422 outside `RANKS`, no-op on the same
rank; serves the row (C-04).

### C-04 — the PC sheet API
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-D, the PC fiche
`GET /api/skill-ranks` → six `{rank, label, points_to_next}` of the active
world. `GET /api/skills?character_id=` → per row `{id, character_id,
domain, skill_definition_id, definition_name, rank, rank_label, xp,
points_to_next, change_history, updated_at}`, ladder of the character's
world, `points_to_next` per C-02.

### C-05 — the points writer
Produced by: BRIEF-0106-B   Consumed by: BRIEF-0106-B (C-06, C-07)
`writes.write_skill_progress(db, *, skill_id, world_id, points, changed_by)
-> SkillProgress(rank_before, rank, xp, points_to_next)`. `points` a
non-zero int (`ValueError` otherwise, and on an unknown row, before any
write). Gain: `xp += points`; if `xp >=` the current rank's threshold (C-02)
the rank rises by one and `xp = 0` (at most one rank per call); at MAX_RANK
points accumulate. Loss: below 0, the rank falls by one and `xp =
threshold(lower rank) + remainder` (so -1 undoes a +1 that ranked up); at
rank 0 `xp` stops at 0. History `{rank, xp, changed_at, by}` appended only
when the rank moves. Caller commits.

### C-06 — the `skill_progress` mutation (family: auto-applied mutations)
Produced by: BRIEF-0106-B   Consumed by: Play, the review cockpit
Payload `{"skill_id": str, "points": int != 0, "band": str | None}`,
`target_table="skill"`, `target_id=skill_id`, `proposed_by="engine_roll"`
(`skill_progress.SKILL_PROGRESS_PROPOSED_BY`), `source_type="conversation"`.
Applier `cockpit/skill_progress.apply_skill_progress(mut, payload, db) ->
Optional[str]` (error string on a missing id, zero/non-int points, unknown
row; else C-05 with `changed_by="mutation:<id>"`). `record_roll(*,
world_id, conversation_id, skill_id, band) -> Optional[dict]`: None for
`skill_id` None, an unknown row, a Maître, an apply refused, or any
exception (logged, swallowed); else one mutation applied through
`routes/mutations._approve_apply_and_commit` on its own session, and
`{skill, rank, rank_label, ranked_up, xp, points_to_next}`. Play's verdict
event carries it as `verdict.progress` (None when nothing earned).

### C-07 — the day's point
Produced by: BRIEF-0106-B   Consumed by: `_mutation_apply_agenda_step_change`
`cockpit/skill_progress.grant_step_roll(db, *, step, owner_id, world_id,
mutation_id) -> None`: nothing when `step.domain` is None, the owner has no
base row for it (`skill_definition_id IS NULL`), or the row is at MAX_RANK;
else C-05 with 1 point. Called for `complete` and `fail`, after the stale
guard, before the status writes.

### C-08 — the ladder's writer and route
Produced by: BRIEF-0106-C   Consumed by: the Compétences UI (C-10)
`writes.upsert_skill_rank(db, *, world_id, rank, label, points_to_next) ->
SkillRank`: `ValueError` before any write on a rank outside 0-5, an empty
label, points at rank 5, or points missing / < 1 below rank 5;
fetch-or-create, never a DELETE; caller commits. `PUT /api/skill-ranks`
body `{"ranks": [{rank, label, points_to_next}] }`: 422 unless each rank
appears exactly once; 422 (rolled back, nothing written) on any invalid
step; serves C-04's ladder.

### C-09 — thresholds on the catalogue routes (family: rank thresholds)
Produced by: BRIEF-0106-C   Consumed by: C-10, C-02
`RankPointsBody`: `points_to_rank_1..5: Optional[int] = Field(None, ge=1)`;
`SkillSystemWriteBody` and `SkillDefinitionWriteBody` extend it. POST and
PUT of `/api/skill-systems` and `/api/skill-definitions` set all five (a
PUT without them clears them); `_skill_system_dict` and
`_skill_definition_dict` serve all five.
Members, re-read after the last: the world's ladder (C-08), a system
(C-09), a skill (C-09); one resolution order (C-02), one input per rank
reached in the UI (C-10).

### C-10 — the Compétences records
Produced by: BRIEF-0106-C   Consumed by: Nia
`competences.svelte.js`: `competencesState.ranks` (C-04, loaded by
`loadCatalogue`); `RANKS_RECORD_ID = 'ranks'`; `RANK_POINT_KEYS`;
`ranksRecord()` (`{kind: 'ranks', persisted: true, id: 'ranks', steps}`);
skill and system records carry the five keys; `inheritedPoints(record, n)`
(a skill: its system's value, then the world's; a system: the world's);
`saveCompetenceRecord` routes `ranks` to a PUT (C-08) and sends
`pointsBody(record)` with a skill and a system. `CompetencesList.svelte`: a
« Rangs » section with « Rangs du monde ». `CompetencesSheet.svelte`: the
`ranks` fiche (six names, five points), and a `thresholds()` block on the
skill and the system fiches (blank = inherited, the inherited value as
placeholder).

### C-11 — the displays
Produced by: BRIEF-0106-D   Consumed by: Nia
`routes/day._account_gains(mutations, db)`: `skill.produced` = one
`{mutation_id, status, domain, points: 1}` per `agenda_step_change` whose
step has a `domain`; `skill.note` = « Un point par jet, donné à
l'approbation de l'étape. ». `Journee.svelte` lists them (« acquis » /
« à l'approbation »). `PjSkillFiche.svelte`: `xp / points_to_next pts`, or
`xp pt · rang maximal`.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| `skill.tier` CHECK -1..2, default 0; rows for PCs only; NPC `physical_tier` | R-01 | `models/canon.py`, `routes/creator.py` |
| `skill_system` has exactly six columns | R-01, R-11 | `models/canon.py`, `skill_system_shape.py` |
| every tier site; the unused crud import block; v1.65 migration historical | R-02 | E1, E5, `writes/characters.py`, `crud/skills.py`, `crud/__init__.py`, `PjSkillFiche.svelte`, `seed_pilot.py`, `env_guard.py` |
| 2d6 + player - npc, bands; two callers | R-03 | `resolution.py`, E3 |
| the stream session is read-only; own-session precedent | R-04 | `stream_session_readonly.py` (rules 1-3), `play_physical.py` |
| `play_physical.py` 996 / 1000 lines | R-05 | `module_budget.py` (`MAX_LINES`), `wc -l` |
| a day writes no canon; blocked steps emit nothing; stale guard | R-06 | `day_resolve.py`, `day_mutations.py`, `cockpit/mutations.py` |
| dispatcher dict, approve-and-commit shape, duplicate guard falls through | R-07 | `routes/mutations.py`, `models/pipeline.py` |
| auto-applied conditions; `engine` never auto-applied; two write paths | R-08 | `ARCHITECTURE_DECISIONS.md`, `CLAUDE.md` |
| canon tables and allowed sites | R-09 | `canon_write_policy.txt`, `single_canon_write.py` (implementation) |
| legacy seal, ratchet, client ignores unknown verdict keys | R-10 | `ARCHITECTURE_DECISIONS.md`, `module_budget.py`, `legacy.html` |
| cascade lists and fixture | R-12 | `writes/worlds.py`, `world_cascade.py` |
| FKs onto the three tables; rebuild recipe; v2.14 DDL | R-13 | E2, `migrate_v1_95_parked_plans.py`, `migrate_v2_14_passage.py`, a database built from `main`'s models |
| `kind`-routed save, no shell change | R-14 | `competences.svelte.js`, `Sheet.svelte`, `CompetencesList.svelte`, `CompetencesSheet.svelte` |
| `_account_gains` signature, sole caller holds `db` | R-15 | `routes/day.py`, `Journee.svelte` |
| curated-config placement; absent row = defaults | R-16 | `models/config.py`, `writes/config.py` |
| header pattern, footer, CLAUDE.md budget | R-17 | `decisions_index.py` (implementation), `ARCHITECTURE_DECISIONS.md`, `claude_md_contract.py` |
| migrations converge to the code's version | R-19 | `migrate_v2_14_passage.py` |

Presuppositions: no brief says « follow the existing convention »; each
pattern reused is named with its file (`migrate_v1_95_parked_plans.py`'s
rebuild, `migrate_v2_14_passage.py`'s shape, `fact_learning.py`'s A2 rule,
`skill_lexicon.record`'s own session, `upsert_conversation_window_config`'s
fetch-or-create, `fact_learning.py`'s growing check).

### (b) Case tables

**Tier → rank → modifier** (C-02, migration):

| tier | rank | name | modifier |
|---|---|---|---|
| -1 | 0 | Inexpérimenté | -1 |
| 0 | 1 | Initié | 0 |
| 1 | 2 | Apprenti | +1 |
| 2 | 3 | Confirmé | +2 |
| — | 4 | Expert | +2 |
| — | 5 | Maître | +3 |

**Threshold to leave rank r** (C-02; A3 and C2 rows):

| definition col | system col | world row | result |
|---|---|---|---|
| set (3) | set (9) | 30 | 3 |
| unset | set (7) | 10 | 7 |
| unset | set (9) | 30 | 9 |
| unset | unset | 30 | 30 |
| unset | unset | none | engine default |
| any | any | rank 5 | None |

**Points writer** (C-05; B1 rows), default ladder:

| row before | points | after (rank, xp) | history entries |
|---|---|---|---|
| rank 1, 8 | +1 | 1, 9 | 0 |
| rank 1, 9 | +1 | 2, 0 | 1 `{rank 1, xp 9}` |
| rank 2, 0 | -1 | 1, 9 | 2 |
| rank 0, 0 | -1 | 0, 0 | 0 |
| rank 5, 3 | +1 | 5, 4 | 0 |
| custom, system `points_to_rank_2 = 2`, rank 1, 1 | +1 | 2, 0 | 1 |
| any | 0 | `ValueError` | — |

**Who earns a point** (C-06, C-07):

| Roll | Carrier | Point to | Written when |
|---|---|---|---|
| Play, base domain | `skill_progress`, auto-applied | the base row | at the roll |
| Play, custom skill named | `skill_progress`, auto-applied | the custom row (S1) | at the roll |
| Play, no skill row | — | nobody | — |
| Play, Maître | — (no mutation) | nobody | — |
| Day step with a domain, `complete` or `fail` | the step's `agenda_step_change` | the owner's base row | at approval |
| Day step without a domain | — | nobody | — |
| Faction or NPC agenda step | — | nobody (no rows) | — |
| Blocked day step | — (no step change) | nobody | — |

**Ladder PUT** (C-08; C1 rows): five steps → 422; six with rank 5 points →
422, nothing written; six valid → stored and served.

### (c) Enumerations

```
--- E1 reads and writes of skill.tier on main (AST: .tier attributes, tier= keywords; src/ and scripts/)
src/world_engine/cockpit/crud/skills.py:100: .tier
src/world_engine/cockpit/crud/skills.py:147: .tier
src/world_engine/cockpit/crud/skills.py:150: .tier
src/world_engine/cockpit/crud/skills.py:150: .tier
src/world_engine/cockpit/crud/skills.py:151: tier=
src/world_engine/cockpit/crud/skills.py:151: .tier
src/world_engine/cockpit/crud/skills.py:386: tier=
src/world_engine/cockpit/play_physical.py:195: .tier
src/world_engine/cockpit/routes/creator.py:691: tier=
src/world_engine/cockpit/routes/creator.py:699: tier=
src/world_engine/day_resolve.py:177: .tier
src/world_engine/writes/characters.py:81: .tier
src/world_engine/writes/characters.py:75: .tier
scripts/seed_pilot.py:3430: tier=
scripts/seed_pilot.py:3464: tier=
(scripts/migrate_v1_65_pc_skill_backfill.py inserts `tier` by raw SQL text — historical)
$ grep -rn "tier" frontend/src --include=*.svelte --include=*.js | grep -i "skill\|SKILL_TIER\|s\.tier\|tier:"
frontend/src/creation/PjSkillFiche.svelte:106:  async function saveTier(skillId, tier) {
frontend/src/creation/PjSkillFiche.svelte:111:        body: JSON.stringify({ tier: Number(tier) }),
frontend/src/creation/PjSkillFiche.svelte:156:            <input type="text" value={SKILL_TIER_LABELS[String(s.tier)] || s.tier} disabled>
frontend/src/creation/PjSkillFiche.svelte:160:                <option value={t} selected={t === s.tier}>{SKILL_TIER_LABELS[String(t)]}</option>

--- E2 foreign keys onto skill, skill_definition, skill_system
$ grep -rn 'ForeignKey("skill\.\|foreign_key="skill\.\|ForeignKey("skill_definition\|foreign_key="skill_definition\|ForeignKey("skill_system\|foreign_key="skill_system' src/world_engine/models/
src/world_engine/models/canon.py:623:            ForeignKey("skill_system.id", ondelete="RESTRICT"),
src/world_engine/models/canon.py:661:            ForeignKey("skill_definition.id", ondelete="RESTRICT"),
src/world_engine/models/pipeline.py:451:    skill_definition_id: Optional[str] = Field(default=None, foreign_key="skill_definition.id")
(nothing references skill.id)

--- E3 callers of the dice
$ grep -rn "resolve_physical(" src --include=*.py | grep -v "def resolve_physical"
src/world_engine/day_resolve.py:224:            verdict = resolve_physical(evaluated.step.domain, player_tier, npc_tier=0)
src/world_engine/cockpit/play_physical.py:207:    verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
src/world_engine/cockpit/play.py:944:                                    # to _arbitrate() + resolve_physical() (BRIEF-11)
(play.py:944 is a comment)

--- E4 checks naming the skill tables
$ grep -ln '\bSkill\b\|skill_system\|skill_definition\|"skill"' tooling/verify/checks/*.py
tooling/verify/checks/json_ui_boundary.py
tooling/verify/checks/no_world_magic_status.py
tooling/verify/checks/single_canon_write.py
tooling/verify/checks/skill_lexicon_clamp.py
tooling/verify/checks/skill_resolution_append_only.py
tooling/verify/checks/skill_system_shape.py
tooling/verify/checks/world_cascade.py

--- E5 names of the tier API
$ grep -rn "write_skill_tier\|SKILL_TIERS\|update_skill_tier\|SkillTierBody" src --include=*.py
src/world_engine/writes/__init__.py:53, :151; src/world_engine/writes/characters.py:7, :53, :63, :71;
src/world_engine/cockpit/crud/__init__.py:210, :212, :221; src/world_engine/cockpit/crud/skills.py:80, :90, :133, :138, :147, :148, :151;
the import block of crud/{ledger,prompts,goals,entities,knowledge,factions,events,agendas,relations,locations}.py (one line each)
```

### (d) Family contracts

C-06 (auto-applied mutations) was written before `record_roll` and re-read
against R-08's four conditions after B's day path was added: the day's point
is not auto-applied (it rides an approved mutation), so the family has one
live member. C-09 (rank thresholds) was written before its three members and
re-read after the UI (C-10): one resolution order, one input per rank
reached, the same `>= 1` rule in the CHECK, the body model and the UI.

### (e) Gates and the modules that satisfy them

| Gate | Module that satisfies it | What it needs that the gate forbids |
|---|---|---|
| `skill_progression.py` A1-D2 (proposed) | the modules each brief names | nothing |
| `single_canon_write.py` (passed) | `write_skill_rank`, `write_skill_progress`, `upsert_skill_rank` allow-listed; `skill_rank` canon | nothing; policy lines in A, B, C |
| `stream_session_readonly.py` (passed) | `record_roll` takes ids, own session | nothing |
| `module_budget.py` (passed) | `play_physical.py` 998, `mutations.py` 969, `day.py` 979, `canon.py` 934 | nothing |
| `function_length.py` (passed) | `_say_physical_resolve_verdict`, `_mutation_apply_agenda_step_change` stay under 80 | nothing |
| `import_cycle.py` (passed) | `skill_progress` imports `routes.mutations` lazily; `mutations.py` imports `skill_progress` at module level, which imports no cockpit module | nothing |
| `skill_system_shape.py` (passed, amended in A) | `models/canon.py` | five columns added to its expected set |
| `world_cascade.py` (passed, amended in A) | `writes/worlds.py` lists `skill_rank`; fixture row | specified in A |
| `schema_version_agreement.py`, `schema_partition.py` (passed) | constant, header, changelog at v2.15 | specified in A |
| `env_guard.py` (passed) | the v2.15 migration's fail-closed guard | nothing |
| `pipeline_state.py` (passed) | `skill_progression.py` exists from A | created in A |
| `decisions_index.py`, `claude_md_contract.py` (passed) | lowercase brief letter; CLAUDE.md at 37 647 | nothing |
| `frontend_build_fresh.py` (passed) | rebuilt `static/` in A, C, D | a rebuild |
| `legacy.html` ratchet (passed) | not touched | nothing |

Named mutations run on the prototype, each red then reverted: tier map
`0: 2` → A1, A2b; definition/system precedence swapped → A3; rank-up line
removed in `write_skill_progress` → B1, B2, B3; tag `engine` → B2; Maître
guard removed in `record_roll` → B2; `grant_step_roll` call removed → B3;
PUT rank-set guard removed → C1; `_set_rank_points` emptied → C2; day
`produced` emptied → D1.

## Amendments

(none)
