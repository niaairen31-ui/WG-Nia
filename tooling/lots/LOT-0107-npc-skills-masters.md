# LOT — TICKET-0107 "NPCs have skill sheets; a skill may require a master, and cannot be rolled until taught"

## Objective and cut

An NPC holds skill rows like a player, only those the creator gives it; a
base domain it holds no row for reads Initié (+0) (D1). An opposing NPC
rolls its row for the skill, else its base domain. `physical_tier` is
dropped: a carrure becomes the NPC's `physical` row (E1). A skill
definition may require a master (A2): a player holds no row for it until
taught, and Play does not roll it until then — no dice, no point, the MJ
narrates that he cannot (B1). The creator teaches it from a character at
Maître in it, or grants it without one, at Inexpérimenté (C1). One skill
fiche serves players and NPCs (F1).

The lot stops before: learning proposed from play (C2, quests), removing a
row from a character, points earned by NPCs, the constraint-gated rolls'
fixed difficulty, and any change to `legacy.html`.

## Briefs in this lot

- **A — schema v2.16, NPC skill sheets**: `skill_definition.requires_master`,
  `skill.taught_by_id`, `character.physical_tier` dropped;
  `migrate_v2_16_npc_skills.py`; `skill_access.py` (the player's row and the
  opposition, D1) out of `play_physical.py`; `writes.write_skill_row`; the
  carrure at creation (E1); check `npc_skills.py` created (A1-A4).
- **B — the master lock** (no schema change): the flag on the catalogue
  routes and the PC seed; Play's `locked` band; `GET /api/skills/learnable`
  and `POST /api/skills` (B1-B4).
- **C — one skill fiche** (no schema change): the fiche on the `npc` tab,
  « À apprendre » / « Compétences à donner », « Exige un maître » (C1-C2).

## Dependency graph

Strictly sequential, A → B → C.

- B reads A's `requires_master` and writes rows through A's
  `write_skill_row`; B's lock extends A's `skill_access.player_skill`.
- C calls B's routes and reads A's `taught_by_id`.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/npc_skills.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A and C rebuild `static/`.
- A creates `npc_skills.py` because every Machine arrow of the ticket must
  resolve from `brief` status on (`pipeline_state.py`).

## RECON

Opened on `main` at `7b1ef23` (merge of PR #137, `ticket/0106`), schema
v2.15. Then prototyped on a copy (branch `proto/0107`): every brief's
commit ran the full corpus green (139/139 on `main`, 140/140 from A on,
with `WORLD_ENGINE_ENV=test`), and the three diffs replayed in order on a
clean worktree of `main` reproduce the prototype tree exactly (generated
files regenerated). Findings tagged [M] were measured.

### R-01 — NPCs have no skill rows [M]
Opened: `src/world_engine/models/canon.py:177` (`Character.physical_tier`,
server default 0), `:655-690` (`Skill`: `character_id` FK `entity`, no
character-type restriction); `src/world_engine/cockpit/routes/creator.py:
690-701` (only PC creation seeds rows).
Finding: the table can hold NPC rows; nothing writes one.
Consequence: no schema change for NPC rows; one writer (`write_skill_row`).

### R-02 — every PC holds every skill [M]
Opened: `src/world_engine/cockpit/crud/skills.py:454-465`
(`create_skill_definition` backfills every PC), `:501-517`
(`update_skill_definition`); `routes/creator.py:618-621`
(`_pc_custom_skill_defs`: every definition); `CLAUDE.md:313-317` (« the
catalogue<->PC alignment is never partial »).
Consequence: A2 restricts the backfill and the seed to open skills; turning
the flag off backfills; the CLAUDE.md line is rewritten in B.

### R-03 — Play's row lookup and opposition [M]
Opened: `src/world_engine/cockpit/play_physical.py:62-150` (the arbiter is
handed the whole catalogue; `_judge_and_record_domain`), `:152-215`
(`_say_physical_resolve_verdict`: base row, else definition row, else
« Defensive fallback » to the base row `:184`; opposition from
`physical_tier` `:206`); `wc -l` → 998 of 1000.
Consequence: the lookup and the opposition move to `skill_access.py`
(reads only; the file falls to 966), which gains the lock in B.

### R-04 — day steps roll base domains [M]
Opened: `src/world_engine/day_plan.py` (`_validate_step`: a step's
`domain` is a base domain); `src/world_engine/day_resolve.py:165-180`.
Consequence: the lock is Play-only.

### R-05 — the readers of `physical_tier` [M]
Opened: enumeration E1; `src/world_engine/entity_author.py:52` (in the
generator's field list), `:193-198`, `:552`;
`src/world_engine/npc_group_author.py:425-430`;
`src/world_engine/cockpit/routes/npc_agent.py:213-214`;
`src/world_engine/cockpit/crud/entities.py:139` (registry « Carrure »);
`src/world_engine/lore_selectors.py:101`;
`frontend/src/creation/NpcAgent.svelte:131-132`;
`frontend/src/creation/generatePanel.svelte.js:60`.
Consequence: E1 — the generators keep proposing `public.physical_tier`
(prompt text unchanged); the create body carries it as `carrure`
(`faction_id`'s separate-key precedent, `crud/entities.py:619-630`); the
registry field and the dossier key go.

### R-06 — the request session is read-only [M]
Opened: `tooling/verify/checks/stream_session_readonly.py:112-123`
(`DECLARED_MODULES`), rule 3 (a callee outside the set handed the request
session is a failure).
Consequence: `skill_access` joins the declared set.

### R-07 — the MJ message of a physical turn [M]
Opened: `src/world_engine/cockpit/play_stream.py:239-262`
(`_mj_user_physical`: the verdict block keyed on `verdict_band`, a
`search_rubric` appended); `play_physical.py:296-357` (scene-state writes
on `failure`/`success` only), `:360-424` (`_say_physical_discovery`).
Consequence: a `locked` band moves no scene state; discovery returns the
locked rubric; the MJ message drops the verdict block for it.

### R-08 — dropping a column [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py` (the previous migration's
shape); SQLite's `ALTER TABLE DROP COLUMN` (3.35+; refused on a column in
an index, a CHECK or a foreign key — `physical_tier` is in none, E2); the
v2.15 DDL of `skill` and `skill_definition`, dumped from a database
created on `main` (embedded in `npc_skills.py`, `_V215_DDL`).
Consequence: two `ADD COLUMN`s and one `DROP COLUMN`, no rebuild; the
migration refuses a SQLite older than 3.35.

### R-09 — the skill fiche island [M]
Opened: `frontend/src/creation/tabs.js:199-229` (`npc` and `pj` entries;
the fiche is an island and a slot of `pj` only); `mount.js:68-95` (an
island mounts once and is shared across tabs, `entityList` the precedent);
`tabs.js:409-419` (`containerVisible` reads the active entry's slots);
`frontend/src/creation/PjSkillFiche.svelte`.
Consequence: the `npc` entry declares the same island and slot; the
component follows `activeTabKey`.

### R-10 — the checks the lot passes [M]
Opened: E3; `single_canon_write.py` and `canon_write_policy.txt`;
`page_contract.py` (« Ajouter une compétence » must appear once — the NPC
section is titled « Compétences à donner »); `creation_island.py`;
`effect_self_write.py`; `claude_md_contract.py` (CLAUDE.md 37 647 of 38
000 characters); `skill_progression.py` (TICKET-0106's A2 rebuilds the
skill tables from the current models, so it keeps passing).

## Contract sheet

### C-01 — the schema (v2.16)
Produced by: BRIEF-0107-A   Consumed by: B, C
`skill_definition.requires_master BOOLEAN NOT NULL DEFAULT 0`;
`skill.taught_by_id` nullable FK `entity`; `character.physical_tier` gone.
Migration: refuses below v2.15, on SQLite < 3.35, on a tier outside -1..2;
every NPC with a non-zero tier and no `physical` base row gets one at
`TIER_TO_RANK[tier]`; players ignored; column dropped. Post-check
(AMENDMENT-0107-01): `PRAGMA foreign_key_check` empty on `skill`,
`skill_definition`, `character`; a dangling row elsewhere is printed as a
note, never a reason to stop.

### C-02 — the rows a roll reads (`skill_access.py`)
Produced by: BRIEF-0107-A (lock: B)   Consumed by: Play
`RolledSkill(base_domain, row, definition, locked=False)`.
`player_skill(db, player_id, token, definitions_by_name)`: a base domain →
the base row; a definition → its row, else (not `requires_master`) the base
row for its domain; else (B) `locked=True`, row None.
`opposition_modifier(db, npc_id, base_domain, definition) -> int`: the
NPC's row for the definition, else its base row, else `DEFAULT_RANK`;
through `rank_modifier`. (B) `LOCKED_BAND = "locked"`,
`locked_verdict(name) -> Verdict` (dice (0, 0), total 0, `domain` = the
name), `locked_rubric(name) -> str`.

### C-03 — one skill row (`writes.write_skill_row`)
Produced by: BRIEF-0107-A   Consumed by: A (carrure, migration), B (grant,
backfill)
`write_skill_row(db, *, character_id, rank, domain=None,
skill_definition_id=None, taught_by_id=None) -> Skill`: exactly one of
`domain`/`skill_definition_id` (a definition sets `domain` to its base
domain); `ValueError` before any write on a rank outside `RANKS`, an
unknown definition, a non-base domain, or a row the character already
holds for that skill. Caller commits.

### C-04 — the carrure (E1)
Produced by: BRIEF-0107-A   Consumed by: the generators
`EntityWriteBody.carrure: Optional[int]`: on a character create, clamped
to -1..2, `TIER_TO_RANK` → a `physical` base row unless it is
`DEFAULT_RANK`. `npc_agent` passes `carrure=pub.get("physical_tier")`;
the generator panel keeps it in `pendingDraftsState.carrure` and sends it.

### C-05 — the lock in the catalogue (A2)
Produced by: BRIEF-0107-B   Consumed by: C
`SkillDefinitionWriteBody.requires_master: bool = False`, served by
`_skill_definition_dict`. Create: open → `_backfill_open_skill` (every PC
lacking it, `DEFAULT_RANK`, through C-03); master → nothing. Update: off →
backfill; on → rows kept. `_pc_custom_skill_defs` lists open definitions
only.

### C-06 — Play's locked turn (B1)
Produced by: BRIEF-0107-B   Consumed by: the MJ
`_say_physical_resolve_verdict`: when locked, `locked_verdict(token)`, no
`resolve_physical`, no `record_roll` (`progress` None).
`_say_physical_discovery` returns `locked_rubric(verdict.domain)` first.
`_mj_user_physical` with `LOCKED_BAND`: context, place, action, NPC
reaction, the rubric — no verdict block.

### C-07 — learning (C1)
Produced by: BRIEF-0107-B   Consumed by: C
`GET /api/skills/learnable?character_id=` → `[{domain,
skill_definition_id, name, requires_master, masters: [{id, name}]}]`: a
player's master skills he lacks; an NPC's missing base domains and
definitions. `POST /api/skills` body `{character_id, skill_definition_id |
domain, rank = 0, taught_by_id?}` → the row (C-08 shape) 201; 422 on a
character or definition outside the world, a teacher who is the learner or
not at Maître in that skill; 409 on a skill held. `GET /api/skills` rows
add `requires_master`, `taught_by_id`.

### C-08 — the fiche (F1)
Produced by: BRIEF-0107-C   Consumed by: Nia
`GET /api/skills/player-characters?character_type=player|npc` (default
`player`, 422 otherwise); `GET /api/skills` rows add `taught_by_name`.
`PjSkillFiche.svelte` on `pj` and `npc` (C-07 routes; a player's grant at
rank 0); `CompetencesSheet.svelte` « Exige un maître »;
`competences.svelte.js` sends `requires_master`.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| `skill` can hold NPC rows; `physical_tier` default 0 | R-01 | `models/canon.py` |
| the backfill, the PC seed, the alignment invariant | R-02 | `crud/skills.py`, `routes/creator.py`, `CLAUDE.md` |
| the whole catalogue reaches the arbiter; the base fallback; opposition from `physical_tier`; 998 lines | R-03 | `play_physical.py`, `module_budget.py` |
| day steps roll base domains | R-04 | `day_plan.py`, `day_resolve.py` |
| seven `physical_tier` readers; `faction_id` rides outside the registry | R-05 | E1, `entity_author.py`, `npc_group_author.py`, `npc_agent.py`, `crud/entities.py`, `lore_selectors.py`, `NpcAgent.svelte`, `generatePanel.svelte.js` |
| declared module set, rule 3 | R-06 | `stream_session_readonly.py` (implementation) |
| verdict block and rubric; scene state on failure/success only | R-07 | `play_stream.py`, `play_physical.py` |
| `physical_tier` in no index/CHECK/FK; v2.15 DDL | R-08 | E2, a database built from `main`'s models |
| island shared across tabs; visibility by slot | R-09 | `tabs.js`, `mount.js` |
| « Ajouter une compétence » once; CLAUDE.md budget | R-10 | `page_contract.py`, `claude_md_contract.py` (implementations) |

Presuppositions: none unnamed — `faction_id`'s separate-key handling, the
v2.15 migration's shape, `skill_lexicon.record`'s own session and
`skill_progression.py`'s growing check are each named with their file.

### (b) Case tables

**Opposition** (C-02, D1; A3 rows):

| NPC holds | roll | modifier |
|---|---|---|
| the skill's row, Maître | that skill | +3 |
| base `physical` at Confirmé only | a physical skill | +2 |
| nothing | any | 0 (Initié) |
| a skill row only | a base-domain roll | its base row, else 0 |

**Player's row** (C-02; A3, B2 rows):

| token | player holds | read |
|---|---|---|
| base domain | base row | base row |
| open skill | its row | its row |
| open skill | none | base row |
| master skill | its row | its row |
| master skill | none | locked: no dice, no point |

**Carrure** (C-04; A4, A2b rows): -1 → rank 0; 0 → no row; 1 → rank 2;
2 → rank 3; 9 → clamped, rank 3; an NPC already holding `physical` keeps
its row (migration).

**Catalogue flag** (C-05; B1 rows): create master → no PC row; create open
→ every PC at Initié; open → master: rows kept; master → open: backfill.

**Grant** (C-07; B3 rows): from a Maître → row with `taught_by_id`; from a
non-master or oneself → 422; held → 409; without a master → row, no
teacher; NPC base domain at rank 4 → row.

### (c) Enumerations

```
--- E1 physical_tier under src/ and frontend/src (main 7b1ef23)
src/world_engine/day_resolve.py:56            (docstring)
src/world_engine/lore_selectors.py:101        physical_tier=character.physical_tier,
src/world_engine/entity_author.py:52          'public.physical_tier (entier -1..2 : ...' (generator field list)
src/world_engine/entity_author.py:193         def _clamp_physical_tier(raw: Any) -> int:
src/world_engine/entity_author.py:552         "physical_tier": _clamp_physical_tier(public_in.get("physical_tier")),
src/world_engine/cockpit/crud/entities.py:139 {"name": "physical_tier", "label": "Physical tier (Carrure)", ...}
src/world_engine/cockpit/play_physical.py:104, :195  (comments)
src/world_engine/cockpit/play_physical.py:206 npc_tier = opposed_character.physical_tier if ...
src/world_engine/cockpit/routes/npc_agent.py:213-214  ext_data["physical_tier"] = pub["physical_tier"]
src/world_engine/models/canon.py:177          physical_tier: int = Field(...)
src/world_engine/npc_group_author.py:425-429  (batch row field validation)
frontend/src/creation/NpcAgent.svelte:131-132 (batch row input)
frontend/src/creation/generatePanel.svelte.js:60  setVal(legacyDoc, 'author-x-physical_tier', ...)
(scripts/migrate_v1_77_metadata_extraction.py: historical)

--- E2 physical_tier in the character DDL (v2.15, from a database built on main)
physical_tier INTEGER DEFAULT 0 NOT NULL   -- no index, no CHECK, no FK names it

--- E3 checks naming skills or characters' skill rows
json_ui_boundary.py, no_world_magic_status.py, single_canon_write.py, skill_lexicon_clamp.py,
skill_resolution_append_only.py, skill_system_shape.py, world_cascade.py, skill_progression.py
```

### (d) Family contracts

C-02 (the rows a roll reads) was written before its two consumers in Play
and re-read after B's lock: the lock lives in the same function as the
fallback it suspends, so no caller can roll a locked skill through another
path. C-03 (one skill row) was re-read after its four callers (carrure,
migration, backfill, grant): each passes a rank and one key; none adds a
`Skill(` itself outside the PC seed of `create_player_character`, which
the policy already sanctions.

### (e) Gates and the modules that satisfy them

| Gate | Module that satisfies it | What it needs that the gate forbids |
|---|---|---|
| `npc_skills.py` A1-C2 (proposed) | the modules each brief names | nothing |
| `stream_session_readonly.py` (amended in A) | `skill_access.py` declared | one tuple entry |
| `single_canon_write.py` (passed) | `write_skill_row` allow-listed | one policy line |
| `module_budget.py` (passed) | `play_physical.py` 998 → 966 (A) → 972 (B) | nothing |
| `function_length.py` (passed) | `_create_static_entity_core`, `_say_physical_resolve_verdict` | nothing |
| `page_contract.py` (passed) | the NPC heading is « Compétences à donner » | nothing |
| `creation_island.py`, `creation_tab_switch.py`, `effect_self_write.py` (passed) | `tabs.js`, `PjSkillFiche.svelte` | nothing |
| `skill_progression.py` (passed) | the v2.15 rebuild reads current models | nothing |
| `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py` (passed) | v2.16 constant, header, changelog; the migration's guard | specified in A |
| `claude_md_contract.py` (passed) | CLAUDE.md at 37 838 | nothing |
| `frontend_build_fresh.py` (passed) | rebuilt `static/` in A and C | a rebuild |

Named mutations run on the prototype, each red then reverted: opposition
ignoring the skill row → A3; carrure write removed → A4; migration skipping
negative tiers → A2b; lock disabled in `player_skill` → B2; backfill of
master skills → B1; any teacher accepted → B3; `taught_by_name` emptied →
C1.

## Amendments

- **AMENDMENT-0107-01** (live gate, 2026-10-06) — the v2.16 post-check
  judged the whole database and stopped on a `session` row whose world is
  gone, after the DDL had committed. C-01's post-check now judges the three
  tables the migration writes; A2 carries a dangling `session` row.
