<!-- slug: skill-ranks-schema -->
# BRIEF 0106-A — "v2.15: a skill has a rank and points, the dice read the rank's modifier"

Lot: LOT-0106-skill-progression.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0106-a, schema v2.15)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0106`, cut from `main` at `a5fbc1e` or later, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.14"`; `world-engine-schema.md:3` → `Current schema version: v2.14`; the changelog's newest entry is `- **v2.14**`.
- `src/world_engine/models/canon.py:639` → `        CheckConstraint("tier BETWEEN -1 AND 2", name="ck_skill_tier"),` inside `class Skill(SQLModel, table=True):` (`:636`); `:574` → `BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")`; `:581` → `class SkillSystem(SQLModel, table=True):`; `:599` → `class SkillDefinition(SQLModel, table=True):`; `wc -l` → 911.
- `src/world_engine/models/config.py` → 147 lines, no `SkillRank`; no `src/world_engine/skill_ranks.py`, no `scripts/migrate_v2_15_*.py`, no `tooling/verify/checks/skill_progression.py`.
- `src/world_engine/writes/characters.py:53` → `def write_skill_tier(`; `tooling/verify/canon_write_policy.txt:24` → `src/world_engine/writes/characters.py::write_skill_tier        skill`.
- `src/world_engine/cockpit/crud/skills.py:90` → `SKILL_TIERS = (-1, 0, 1, 2)`; `:133` → `class SkillTierBody(BaseModel):`; `:386` → `            tier=0,`.
- `src/world_engine/cockpit/play_physical.py:18` → `from .. import llm_parse, ollama_client, skill_lexicon`; `:195` → `    player_tier = skill_row.tier if skill_row else 0`; `wc -l` → 996.
- `src/world_engine/day_resolve.py:177` → `    return skill_row.tier if skill_row else 0`; `:86` → `from .resolution import Verdict, resolve_physical`.
- `src/world_engine/cockpit/routes/creator.py:691` → `            db.add(Skill(character_id=entity.id, domain=domain, tier=0))`.
- `scripts/seed_pilot.py:3430` and `:3464` → `            tier=0,`.
- `frontend/src/creation/PjSkillFiche.svelte:39` → `  const SKILL_TIER_LABELS = {`.
- `src/world_engine/writes/worlds.py:76` → `    "skill_resolution", "skill_system", "unresolved_mention", "visit",`.
- `tooling/verify/checks/skill_system_shape.py:30-32` → `EXPECTED_SKILL_SYSTEM_COLUMNS = {` with exactly the six columns.
- `CLAUDE.md:310` → `- **A new \`skill_definition\` backfills a tier-0 \`skill\` row onto every`.
- The AST enumeration E1 of the lot header (`.tier` attributes, `tier=` keywords under `src/` and `scripts/`) yields exactly its fifteen lines.

## Facts carried

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

### R-05 — `play_physical.py` at its cap [M]
Opened: `tooling/verify/checks/module_budget.py:56-59` (`MAX_LINES = 1000`);
`wc -l src/world_engine/cockpit/play_physical.py` → 996;
`play_physical.py:18` (`from .. import llm_parse, ollama_client,
skill_lexicon`), `:54` (`from .play_discovery import ...`), `:152-215`
(`_say_physical_resolve_verdict`, `:195` the tier read, `:214` the verdict
event line).
Consequence: A changes two lines in place (imports joined to `:18`); B adds
two (one import, one call) — 998 lines. Any other growth is a STOP.

### R-09 — sanctioned canon writes [M]
Opened: `tooling/verify/canon_write_policy.txt:1-7` (`[CANON_TABLES]`),
`:24` (`write_skill_tier skill`), the `crud/skills.py` entries;
`tooling/verify/checks/single_canon_write.py:1-60, 180-206`.
Consequence: `write_skill_tier` is renamed `write_skill_rank`;
`write_skill_progress` and `upsert_skill_rank` are new allowed sites;
`skill_rank` joins `[CANON_TABLES]`.

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

### R-19 — a migration converges to the code's version [M]
Opened: `scripts/migrate_v2_14_passage.py:355-369`
(`_converge_schema_meta` writes `EXPECTED_STATIC_SCHEMA_VERSION`, whatever
it is).
Finding: run on v2.15 code against a v2.13 database, the v2.14 migration
would mark it v2.15 without the skill rebuild. Production is at v2.14.
Consequence: REPORT only; the live gate runs v2.15 alone.

## Contracts

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

## Context

Nia locked six ranks fixed in the engine (G1), a modifier table that keeps every former tier's roll (L1), points counted within a rank (U2), and thresholds per world with overrides per system and per skill (O1, V). This brief replaces `skill.tier` with `rank` and `xp` everywhere at once — dropping the column breaks every reader — and adds the columns and the table the later briefs write. Nothing earns a point yet (B) and nobody edits the ladder yet (C); the fiche already speaks ranks.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `models/canon.py`, gives `Skill` `rank` (default 1) and `xp` (default 0) with `ck_skill_rank` and `ck_skill_xp` in place of `tier`; adds `RANK_POINTS_CHECK` and the five `points_to_rank_<n>` columns with their CHECK to `SkillSystem` and `SkillDefinition` (C-01);
   - in `models/config.py`, adds `SkillRank` (C-01); exports it from `models`;
   - creates `src/world_engine/skill_ranks.py` (C-02);
   - renames `writes.write_skill_tier` to `write_skill_rank` (C-03) in `writes/characters.py`, `writes/__init__.py`, the import block of eleven `cockpit/crud/*.py` modules and `canon_write_policy.txt`; adds `skill_rank` to `[CANON_TABLES]`;
   - in `cockpit/crud/skills.py`, replaces `SKILL_TIERS`/`SkillTierBody`/`update_skill_tier` with `SkillRankBody`/`update_skill_rank`, adds `GET /api/skill-ranks`, serves `rank`, `rank_label`, `xp`, `points_to_next` (C-04), and seeds a new definition's PC rows at `DEFAULT_RANK`; `crud/__init__.py` re-exports follow;
   - makes both rolls read `rank_modifier`: `play_physical.py:195` (import joined to `:18`, the file stays at 996 lines) and `day_resolve._step_player_tier`;
   - drops the `tier=0` keyword from PC creation (`routes/creator.py`) and writes `rank=1` in `seed_pilot.py`;
   - in `PjSkillFiche.svelte`, the rank select lists the world's names (`GET /api/skill-ranks`) and PATCHes `{rank}`;
   - bumps the version to v2.15 (constant, schema doc header); documents the three changed tables and `skill_rank` in `world-engine-schema.md`; adds the v2.15 changelog entry;
   - adds `skill_rank` to `_DIRECT_WORLD_SCOPED_DELETES` and to `world_cascade.py`'s fixture; adds the five columns to `skill_system_shape.py`'s expected set;
   - creates `scripts/migrate_v2_15_skill_ranks.py` (the v2.14 migration's shape: env guard, refusal below v2.14, post-checks, `schema_meta` convergence; the three tables rebuilt from the models on a raw connection, `migrate_v1_95_parked_plans.py`'s recipe, tier mapped through `TIER_TO_RANK`; `skill_rank` created empty);
   - creates `tooling/verify/checks/skill_progression.py` with A1-A4 (A2 follows `fact_learning.py` A2: a previous-shaped database, refusal, shape equality, second run);
   - changes CLAUDE.md's backfill wording (« a default-rank `skill` row »);
   - appends the decision entry above the `---` / `*Co-built…*` footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build`.
4. Commit message: `feat(skills): rank and points replace the tier, schema v2.15 (BRIEF-0106-a)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index d62394e..ec6cff5 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -307,7 +307,7 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   no `change_history` snapshot): dependent PC `skill` rows then the
   definition, one transaction. The type-"Oui" modal is the sole safeguard —
   a named exception to "History is sacred", scoped to one row.
-- **A new `skill_definition` backfills a tier-0 `skill` row onto every
+- **A new `skill_definition` backfills a default-rank `skill` row onto every
   existing PC of its world, in the create's own transaction** — the
   catalogue<->PC alignment is never partial. Renaming touches no `skill`
   row (FK-by-id); re-basing (`base_domain` change) updates `domain` on
diff --git a/frontend/src/creation/PjSkillFiche.svelte b/frontend/src/creation/PjSkillFiche.svelte
index cfde7a8..7198031 100644
--- a/frontend/src/creation/PjSkillFiche.svelte
+++ b/frontend/src/creation/PjSkillFiche.svelte
@@ -16,8 +16,8 @@
      (sheetState.svelte.js's selectEntity writes it), the same
      already-established channel a cross-component "onSelect" needs.
 
-     skillSaveTier's route (PATCH /api/skills/{id}) is untouched by this
-     port -- confirmed neither role_capacity_chokepoint.py nor
+     skillSaveTier's route (PATCH /api/skills/{id}, body {rank} since
+     TICKET-0106) was untouched by this port -- confirmed neither role_capacity_chokepoint.py nor
      role_closed_vocab.py greps index.html or mentions "skill", so no
      re-homing is triggered.
 
@@ -31,10 +31,10 @@
     physical: 'Physical', agility: 'Agility',
     perception: 'Perception', composure: 'Composure',
   };
-  const SKILL_TIER_LABELS = {
-    '-1': '-1 · Weak', '0': '0 · Average', '1': '+1 · Trained', '2': '+2 · Exceptional',
-  };
+  // TICKET-0106 (BRIEF-0106-A): a skill row carries a rank (0-5); its
+  // name is the world's (GET /api/skill-ranks), never a literal here.
 
+  let ranks = $state([]);
   let characters = $state([]);
   let characterId = $state(null);
   let loadError = $state('');
@@ -59,6 +59,7 @@
   async function loadCharacters() {
     let fetched;
     try {
+      ranks = await api('/api/skill-ranks');
       fetched = await api('/api/skills/player-characters');
       loadError = '';
     } catch (e) {
@@ -103,12 +104,12 @@
     selectCharacter(ev.currentTarget.value);
   }
 
-  async function saveTier(skillId, tier) {
+  async function saveRank(skillId, rank) {
     try {
       const updated = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
         method: 'PATCH',
         headers: { 'Content-Type': 'application/json' },
-        body: JSON.stringify({ tier: Number(tier) }),
+        body: JSON.stringify({ rank: Number(rank) }),
       });
       const idx = rows.findIndex((s) => s.id === skillId);
       if (idx !== -1) rows[idx] = updated;
@@ -153,11 +154,11 @@
             {/if}
           </label>
           {#if playerMode}
-            <input type="text" value={SKILL_TIER_LABELS[String(s.tier)] || s.tier} disabled>
+            <input type="text" value={s.rank_label} disabled>
           {:else}
-            <select onchange={(ev) => saveTier(s.id, ev.currentTarget.value)}>
-              {#each [-1, 0, 1, 2] as t}
-                <option value={t} selected={t === s.tier}>{SKILL_TIER_LABELS[String(t)]}</option>
+            <select onchange={(ev) => saveRank(s.id, ev.currentTarget.value)}>
+              {#each ranks as r (r.rank)}
+                <option value={r.rank} selected={r.rank === s.rank}>{r.label}</option>
               {/each}
             </select>
           {/if}
diff --git a/scripts/migrate_v2_15_skill_ranks.py b/scripts/migrate_v2_15_skill_ranks.py
new file mode 100644
index 0000000..a0c0438
--- /dev/null
+++ b/scripts/migrate_v2_15_skill_ranks.py
@@ -0,0 +1,237 @@
+"""Migration v2.15 — a skill has a rank and points (TICKET-0106, BRIEF-0106-A,
+decisions G1, L1, O1, P2, T1, U2).
+
+1. `skill_system` and `skill_definition` gain five nullable columns,
+   `points_to_rank_1` .. `points_to_rank_5` (a positive count, or NULL to
+   inherit), and `skill` loses `tier` for `rank` (0-5) and `xp` (>= 0). SQLite
+   cannot add a table CHECK nor drop a column a CHECK names, so the three
+   tables are rebuilt from the models (`migrate_v1_95_parked_plans.py`
+   precedent: raw DBAPI connection, `PRAGMA foreign_keys=OFF` and
+   `legacy_alter_table=ON` before `BEGIN`, rename, create from the model,
+   copy, drop), in one transaction. Every row is kept; each former tier
+   becomes its rank through `skill_ranks.TIER_TO_RANK` (-1/0/1/2 ->
+   0/1/2/3), so no roll changes (L1); `xp` starts at 0. A `change_history`
+   entry written before this migration keeps its `tier` key: history is
+   never rewritten.
+2. Creates `skill_rank` (a world's rank names and default points, O1/P2)
+   empty: a world without rows reads the engine defaults
+   (`skill_ranks.world_ladder`), so nothing is seeded.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.14 (the migrations are sequential), and on a `skill.tier` value
+outside -1..2 (nothing to map it to), before any change.
+
+Idempotent: each table is rebuilt only while it lacks its new columns;
+`skill_rank` is created only when missing.
+
+Post-checks, before `schema_meta` converges: row counts kept, `skill` has no
+`tier` column and every rank is within 0-5, the three tables carry the
+models' CHECK constraints, `skill_rank` exists, and
+`PRAGMA foreign_key_check` is empty.
+
+Run from the project root:
+
+    python scripts/migrate_v2_15_skill_ranks.py
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
+        "migrate_v2_15_skill_ranks.py refuses to run without WORLD_ENGINE_ENV "
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
+from world_engine.skill_ranks import RANK_POINTS_COLUMNS, TIER_TO_RANK  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.14"
+
+_SYSTEM_COLUMNS = "id, world_id, name, description, created_at, updated_at"
+_DEFINITION_COLUMNS = (
+    "id, world_id, name, base_domain, system_id, description, created_at, updated_at"
+)
+_SKILL_KEPT = "id, character_id, domain, change_history, skill_definition_id, created_at, updated_at"
+_RANK_OF_TIER = "CASE tier " + " ".join(
+    f"WHEN {tier} THEN {rank}" for tier, rank in sorted(TIER_TO_RANK.items())
+) + " END"
+
+_EXPECTED_CHECKS = {
+    "skill_system": {"ck_skill_system_rank_points"},
+    "skill_definition": {"ck_skill_definition_base_domain", "ck_skill_definition_rank_points"},
+    "skill": {"ck_skill_rank", "ck_skill_xp"},
+}
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse_if_behind() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.15 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _columns(table: str) -> set[str]:
+    return {c["name"] for c in inspect(engine).get_columns(table)}
+
+
+def _refuse_unmapped_tiers() -> None:
+    if "tier" not in _columns("skill"):
+        return
+    allowed = ", ".join(str(t) for t in sorted(TIER_TO_RANK))
+    with engine.connect() as conn:
+        bad = conn.execute(text(f"SELECT id, tier FROM skill WHERE tier NOT IN ({allowed})")).fetchall()
+    if bad:
+        raise SystemExit(f"Migration v2.15 refused: skill row(s) with a tier outside -1..2: {bad}.")
+
+
+def _counts() -> dict[str, int]:
+    with engine.connect() as conn:
+        return {
+            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
+            for table in ("skill_system", "skill_definition", "skill")
+        }
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _rebuild(cursor, model, insert_columns: str, select_columns: str) -> None:
+    table = model.__tablename__
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
+        (table,),
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
+    _create_from_model(cursor, model)
+    cursor.execute(f"INSERT INTO {table} ({insert_columns}) SELECT {select_columns} FROM {table}_old")
+    cursor.execute(f"DROP TABLE {table}_old")
+
+
+def _rebuild_plan() -> list[tuple]:
+    """(model, insert columns, select expression) per table still missing its
+    new columns, parents first."""
+    plan: list[tuple] = []
+    for model, kept in ((models.SkillSystem, _SYSTEM_COLUMNS), (models.SkillDefinition, _DEFINITION_COLUMNS)):
+        if RANK_POINTS_COLUMNS[0] not in _columns(model.__tablename__):
+            plan.append((model, kept, kept))
+    if "tier" in _columns("skill"):
+        plan.append((models.Skill, f"{_SKILL_KEPT}, rank, xp", f"{_SKILL_KEPT}, {_RANK_OF_TIER}, 0"))
+    return plan
+
+
+def _apply_ddl() -> list[str]:
+    """One raw transaction (see the module docstring): the rebuilds, then
+    `skill_rank` when missing."""
+    plan = _rebuild_plan()
+    create_ladder = "skill_rank" not in set(inspect(engine).get_table_names())
+    if not plan and not create_ladder:
+        return []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        for model, insert_columns, select_columns in plan:
+            _rebuild(cursor, model, insert_columns, select_columns)
+        if create_ladder:
+            _create_from_model(cursor, models.SkillRank)
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    applied = [f"{model.__tablename__} rebuilt" for model, _, _ in plan]
+    return applied + (["skill_rank table"] if create_ladder else [])
+
+
+def _post_checks(before: dict[str, int]) -> None:
+    after = _counts()
+    if after != before:
+        raise SystemExit(f"Migration v2.15 aborted, post-check failed: row counts {before} -> {after}.")
+    if "tier" in _columns("skill") or not {"rank", "xp"} <= _columns("skill"):
+        raise SystemExit("Migration v2.15 aborted, post-check failed: skill still has tier, or lacks rank/xp.")
+    inspector = inspect(engine)
+    for table, expected in _EXPECTED_CHECKS.items():
+        present = {ck["name"] for ck in inspector.get_check_constraints(table)}
+        if not expected <= present:
+            raise SystemExit(f"Migration v2.15 aborted, post-check failed: {table} lacks {expected - present}.")
+    if "skill_rank" not in set(inspector.get_table_names()):
+        raise SystemExit("Migration v2.15 aborted, post-check failed: skill_rank is missing.")
+    with engine.connect() as conn:
+        out_of_range = conn.execute(text("SELECT COUNT(*) FROM skill WHERE rank NOT BETWEEN 0 AND 5")).scalar_one()
+        dangling = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+    if out_of_range or dangling:
+        raise SystemExit(
+            f"Migration v2.15 aborted, post-check failed: {out_of_range} rank(s) out of range, "
+            f"foreign_key_check {dangling}."
+        )
+    print(f"Post-check: rows kept {after}; ranks within 0-5; constraints present; skill_rank exists.")
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
+    print("Migration v2.15 — skill rank and points, rank thresholds, skill_rank")
+    _refuse_if_behind()
+    _refuse_unmapped_tiers()
+    before = _counts()
+    applied = _apply_ddl()
+    print("Applied: " + ", ".join(applied) + "." if applied else "DDL already applied.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.15 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 9ce91a5..acdecc4 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -3400,8 +3400,8 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
 
     # ----- skill sheet test player character (entity + character + skill) ----
     # BRIEF-10: dedicated test character for the skill sheet, separate from
-    # char-player. Four skill rows at tier 0 — the creator edits tiers via the
-    # cockpit "Fiche" view afterwards.
+    # char-player. Four skill rows at rank 1 (Initié) — the creator edits ranks via
+    # the cockpit "Fiche" view afterwards.
     get_or_create(
         session,
         m.Entity,
@@ -3427,7 +3427,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
             f"skill-{SKILL_SHEET_PC_ID}-{domain}",
             character_id=SKILL_SHEET_PC_ID,
             domain=domain,
-            tier=0,
+            rank=1,
         )
 
     # ----- world-scoped custom skill catalogue (BRIEF-55, schema v1.63) -----
@@ -3450,7 +3450,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         base_domain="perception",
     )
     # B1: the pilot PC seeds every custom skill of its world too, flat at
-    # tier 0, mirroring create_player_character's seed loop.
+    # rank 1, mirroring create_player_character's seed loop.
     for def_id, def_domain in (
         (SKILL_DEF_DIPLOMATIE_ID, "composure"),
         (SKILL_DEF_PISTAGE_ID, "perception"),
@@ -3461,7 +3461,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
             f"skill-{SKILL_SHEET_PC_ID}-custom-{def_id}",
             character_id=SKILL_SHEET_PC_ID,
             domain=def_domain,
-            tier=0,
+            rank=1,
             skill_definition_id=def_id,
         )
 
diff --git a/src/world_engine/cockpit/crud/__init__.py b/src/world_engine/cockpit/crud/__init__.py
index fa6a324..fa521cd 100644
--- a/src/world_engine/cockpit/crud/__init__.py
+++ b/src/world_engine/cockpit/crud/__init__.py
@@ -207,18 +207,18 @@ from .factions import (
 )
 from .skills import (
     SKILL_DOMAINS,
-    SKILL_TIERS,
     SkillDefinitionWriteBody,
-    SkillTierBody,
+    SkillRankBody,
     _skill_definition_dict,
     _skill_dict,
     create_skill_definition,
     delete_skill_definition,
     list_skill_definitions,
     list_skill_player_characters,
+    list_skill_ranks,
     list_skills,
     update_skill_definition,
-    update_skill_tier,
+    update_skill_rank,
 )
 from .locations import (
     ACCESS_LEVELS,
diff --git a/src/world_engine/cockpit/crud/agendas.py b/src/world_engine/cockpit/crud/agendas.py
index 734d1bf..c575e12 100644
--- a/src/world_engine/cockpit/crud/agendas.py
+++ b/src/world_engine/cockpit/crud/agendas.py
@@ -74,7 +74,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index d5a8221..534ec33 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -85,7 +85,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/events.py b/src/world_engine/cockpit/crud/events.py
index acfc5ec..62ce270 100644
--- a/src/world_engine/cockpit/crud/events.py
+++ b/src/world_engine/cockpit/crud/events.py
@@ -72,7 +72,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/factions.py b/src/world_engine/cockpit/crud/factions.py
index ad7d41f..7505c3b 100644
--- a/src/world_engine/cockpit/crud/factions.py
+++ b/src/world_engine/cockpit/crud/factions.py
@@ -75,7 +75,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/goals.py b/src/world_engine/cockpit/crud/goals.py
index 1030f89..17211c7 100644
--- a/src/world_engine/cockpit/crud/goals.py
+++ b/src/world_engine/cockpit/crud/goals.py
@@ -79,7 +79,7 @@ from ...writes import (
     write_npc_schedule,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/knowledge.py b/src/world_engine/cockpit/crud/knowledge.py
index a4c1482..bdb6159 100644
--- a/src/world_engine/cockpit/crud/knowledge.py
+++ b/src/world_engine/cockpit/crud/knowledge.py
@@ -80,7 +80,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/ledger.py b/src/world_engine/cockpit/crud/ledger.py
index 0ecbdf5..04bdb90 100644
--- a/src/world_engine/cockpit/crud/ledger.py
+++ b/src/world_engine/cockpit/crud/ledger.py
@@ -76,7 +76,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index 494923b..c72b619 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -81,7 +81,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/prompts.py b/src/world_engine/cockpit/crud/prompts.py
index 249fc13..c05fc5e 100644
--- a/src/world_engine/cockpit/crud/prompts.py
+++ b/src/world_engine/cockpit/crud/prompts.py
@@ -76,7 +76,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/relations.py b/src/world_engine/cockpit/crud/relations.py
index b45d991..532a268 100644
--- a/src/world_engine/cockpit/crud/relations.py
+++ b/src/world_engine/cockpit/crud/relations.py
@@ -82,7 +82,7 @@ from ...writes import (
     write_oriented_relations,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
diff --git a/src/world_engine/cockpit/crud/skills.py b/src/world_engine/cockpit/crud/skills.py
index 6b80e98..04fdedf 100644
--- a/src/world_engine/cockpit/crud/skills.py
+++ b/src/world_engine/cockpit/crud/skills.py
@@ -53,6 +53,7 @@ from ...models import (
 )
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
+from ...skill_ranks import DEFAULT_RANK, RANKS, RankStep, points_to_next, skill_owners, world_ladder
 from ...tick_normalize import _EVENT_TYPES
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -77,7 +78,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
-    write_skill_tier,
+    write_skill_rank,
 )
 
 from ._router import router
@@ -87,22 +88,36 @@ from ._shared import _get_entity, _iso, _world_id
 SKILL_DOMAINS = BASE_SKILL_DOMAINS
 
 
-SKILL_TIERS = (-1, 0, 1, 2)
-
-
-def _skill_dict(s: Skill, definition_name: str | None = None) -> dict:
+def _skill_dict(
+    s: Skill, ladder: tuple[RankStep, ...], definition: SkillDefinition | None = None,
+    system: SkillSystem | None = None,
+) -> dict:
     return {
         "id": s.id,
         "character_id": s.character_id,
         "domain": s.domain,
         "skill_definition_id": s.skill_definition_id,
-        "definition_name": definition_name,
-        "tier": s.tier,
+        "definition_name": definition.name if definition else None,
+        "rank": s.rank,
+        "rank_label": ladder[s.rank].label,
+        "xp": s.xp,
+        "points_to_next": points_to_next(s.rank, ladder, system=system, definition=definition),
         "change_history": s.change_history,
         "updated_at": _iso(s.updated_at),
     }
 
 
+def _rank_step_dict(step: RankStep) -> dict:
+    return {"rank": step.rank, "label": step.label, "points_to_next": step.points_to_next}
+
+
+@router.get("/skill-ranks")
+def list_skill_ranks(db: DbSession = Depends(get_session)) -> list[dict]:
+    """The active world's six ranks, index = rank (`skill_ranks.world_ladder`:
+    its `skill_rank` rows over the engine defaults). Read-only."""
+    return [_rank_step_dict(step) for step in world_ladder(db, _world_id(db))]
+
+
 @router.get("/skills/player-characters")
 def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[dict]:
     """Player characters (`character_type = 'player'`), for the Fiche selector."""
@@ -118,41 +133,47 @@ def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[d
 
 @router.get("/skills")
 def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
-    """A player character's skill sheet, in fixed domain order."""
-    _get_entity(db, character_id)
-    pairs = db.exec(
-        select(Skill, SkillDefinition)
+    """A player character's skill sheet, in fixed domain order, each row with
+    its rank's name and the points it needs to leave that rank."""
+    entity = _get_entity(db, character_id)
+    ladder = world_ladder(db, entity.world_id)
+    rows = db.exec(
+        select(Skill, SkillDefinition, SkillSystem)
         .outerjoin(SkillDefinition, Skill.skill_definition_id == SkillDefinition.id)
+        .outerjoin(SkillSystem, SkillDefinition.system_id == SkillSystem.id)
         .where(Skill.character_id == character_id)
     ).all()
     order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
-    pairs.sort(key=lambda p: order.get(p[0].domain, len(SKILL_DOMAINS)))
-    return [_skill_dict(s, d.name if d else None) for s, d in pairs]
+    rows.sort(key=lambda r: order.get(r[0].domain, len(SKILL_DOMAINS)))
+    return [_skill_dict(s, ladder, d, sys) for s, d, sys in rows]
 
 
-class SkillTierBody(BaseModel):
-    tier: int
+class SkillRankBody(BaseModel):
+    rank: int
 
 
 @router.patch("/skills/{skill_id}")
-def update_skill_tier(skill_id: str, body: SkillTierBody, db: DbSession = Depends(get_session)) -> dict:
-    """Creator edit: set a skill's tier directly (canon write, no checkpoint).
+def update_skill_rank(skill_id: str, body: SkillRankBody, db: DbSession = Depends(get_session)) -> dict:
+    """Creator edit: set a skill's rank directly (canon write, no checkpoint).
 
-    Archives the previous tier into `change_history` and bumps `updated_at`
-    — but only on an actual change, so resubmitting the same tier is a no-op.
+    Archives the previous rank and points into `change_history`, restarts the
+    points at 0 (U2) and bumps `updated_at` — but only on an actual change,
+    so resubmitting the same rank is a no-op.
     """
     skill = db.get(Skill, skill_id)
     if skill is None:
         raise HTTPException(404, f"Skill {skill_id!r} not found")
-    if body.tier not in SKILL_TIERS:
-        raise HTTPException(422, f"tier must be one of {SKILL_TIERS}")
+    if body.rank not in RANKS:
+        raise HTTPException(422, f"rank must be one of {RANKS}")
 
-    if body.tier != skill.tier:
-        write_skill_tier(db, skill_id=skill_id, tier=body.tier, changed_by="creator")
+    if body.rank != skill.rank:
+        write_skill_rank(db, skill_id=skill_id, rank=body.rank, changed_by="creator")
         db.commit()
         db.refresh(skill)
 
-    return _skill_dict(skill)
+    entity = _get_entity(db, skill.character_id)
+    system, definition = skill_owners(db, skill.skill_definition_id)
+    return _skill_dict(skill, world_ladder(db, entity.world_id), definition, system)
 
 
 def _skill_system_dict(s: SkillSystem, db: DbSession) -> dict:
@@ -342,7 +363,7 @@ def create_skill_definition(
 ) -> dict:
     """Add a custom skill to the active world's catalogue (D2-backfill-yes).
 
-    Backfills: inserts a tier-0 `skill` row for this definition onto every
+    Backfills: inserts a `skill` row at `DEFAULT_RANK` (Initié) for this definition onto every
     existing player character of the world, in the SAME transaction, so the
     catalogue<->PC alignment that makes the arbiter lookup total never
     lapses (BRIEF-55's invariant — every PC always has every world skill).
@@ -383,7 +404,7 @@ def create_skill_definition(
         db.add(Skill(
             character_id=character_id,
             domain=definition.base_domain,
-            tier=0,
+            rank=DEFAULT_RANK,
             skill_definition_id=definition.id,
         ))
 
diff --git a/src/world_engine/cockpit/play_physical.py b/src/world_engine/cockpit/play_physical.py
index a127739..1bdd2b0 100644
--- a/src/world_engine/cockpit/play_physical.py
+++ b/src/world_engine/cockpit/play_physical.py
@@ -15,7 +15,7 @@ from typing import Any, Iterator, Optional
 from fastapi import HTTPException
 from sqlmodel import Session, select
 
-from .. import llm_parse, ollama_client, skill_lexicon
+from .. import llm_parse, ollama_client, skill_lexicon, skill_ranks
 from ..context import (
     assemble_mj_context,
     assemble_npc_context,
@@ -190,9 +190,9 @@ def _say_physical_resolve_verdict(
             ).first()
 
     # Player-roll rule (resolution.py): the roll always belongs to the
-    # player — player_tier from the skill sheet, npc_tier (if opposed)
-    # from character.physical_tier, default 0 either way.
-    player_tier = skill_row.tier if skill_row else 0
+    # player — player_tier is its skill row's rank modifier (TICKET-0106),
+    # npc_tier (if opposed) character.physical_tier, default 0 either way.
+    player_tier = skill_ranks.rank_modifier(skill_row.rank) if skill_row else 0
 
     opposed_entity: Optional[Entity] = None
     # npc_tier already set for gated turns above; normal turns start at 0.
diff --git a/src/world_engine/cockpit/routes/creator.py b/src/world_engine/cockpit/routes/creator.py
index 8d996ab..0e04993 100644
--- a/src/world_engine/cockpit/routes/creator.py
+++ b/src/world_engine/cockpit/routes/creator.py
@@ -650,7 +650,7 @@ def create_player_character(
     Binds to the lone creator user (`role='creator'`) — there is no real
     multiplayer user identity yet. Mirrors `seed_pilot.py`'s `char-player`
     creation: entity + `character` row + the four `skill` rows (physical,
-    agility, perception, composure) at `tier=0`, since the skill sheet and
+    agility, perception, composure) at the model's default rank (Initié), since the skill sheet and
     physical-resolution arbiter both read those rows off a PC. One PC per
     user per world is defended by `idx_character_one_pc_per_user_world`
     (partial unique index) — a collision surfaces as a clean `{"ok": false}`,
@@ -660,10 +660,10 @@ def create_player_character(
     descriptive lore as `facets`, written as facts after the entity flush
     (TICKET-0091, BRIEF-0091-E), and `knowledge` written per
     `_write_pc_knowledge`. The base-domain skill
-    seed stays untouched (B1, no proposed tiers).
+    seed stays untouched (B1, no proposed ranks).
 
     BRIEF-55 (B1, schema v1.63): after the four base-domain rows, also seeds
-    one `skill` row per `skill_definition` of the PC's world, at `tier=0`,
+    one `skill` row per `skill_definition` of the PC's world, at the default rank,
     `domain=<definition.base_domain>`, `skill_definition_id=<definition.id>`
     — never proposed by a model.
     """
@@ -688,15 +688,14 @@ def create_player_character(
         db.flush()
         write_entity_facets(db, entity_id=entity.id, facets=body.facets or {}, created_by="creator_crud")
         for domain in BASE_SKILL_DOMAINS:
-            db.add(Skill(character_id=entity.id, domain=domain, tier=0))
-        # B1 (schema v1.63): flat tier-0 seed for every custom skill of the
+            db.add(Skill(character_id=entity.id, domain=domain))
+        # B1 (schema v1.63): flat default-rank seed for every custom skill of the
         # PC's world — never proposed by a model, set here after the draft
         # is accepted.
         for definition in _pc_custom_skill_defs(world_id, db):
             db.add(Skill(
                 character_id=entity.id,
                 domain=definition.base_domain,
-                tier=0,
                 skill_definition_id=definition.id,
             ))
         _write_pc_knowledge(entity.id, body.knowledge, db)
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index d65aa4c..4fe1b0d 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -84,6 +84,7 @@ from .models import (
     Skill,
 )
 from .resolution import Verdict, resolve_physical
+from .skill_ranks import rank_modifier
 
 _log = logging.getLogger(__name__)
 
@@ -163,7 +164,9 @@ class _RolledStep:
 
 
 def _step_player_tier(character: Character, domain: str, db: Session) -> int:
-    """`play_physical.py`'s base-domain derivation (D1), verbatim: a day
+    """The dice modifier of the step's base-domain skill row, through
+    `skill_ranks.rank_modifier` (TICKET-0106, L1); 0 without a row.
+    `play_physical.py`'s base-domain derivation (D1), verbatim: a day
     step's `domain` is always a base domain (`day_plan._validate_step`
     rejects anything else) — the custom-skill branch that precedent also
     has never applies here, so it is not reproduced."""
@@ -174,7 +177,7 @@ def _step_player_tier(character: Character, domain: str, db: Session) -> int:
             Skill.skill_definition_id.is_(None),
         )
     ).first()
-    return skill_row.tier if skill_row else 0
+    return rank_modifier(skill_row.rank) if skill_row else 0
 
 
 _TERMINAL_AGENDA_STEP_STATUSES = ("completed", "failed")
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 8812f84..b5f510a 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -79,7 +79,7 @@ from .canon_faction import (
     FactionRole,
 )
 from .canon_knowledge import Fact, FactDefault, FactParticipant, Knowledge, Relation
-from .config import AgendaStep, AgendaStepRequirement, ConversationWindowConfig
+from .config import AgendaStep, AgendaStepRequirement, ConversationWindowConfig, SkillRank
 from .schedule import SCHEDULE_PHASES, NpcSchedule
 from .ephemeral import (
     ENCOUNTER_SOURCES,
@@ -171,6 +171,7 @@ __all__ = [
     "Item",
     "SkillDefinition",
     "SkillSystem",
+    "SkillRank",
     "Skill",
     "DiscoverableDetail",
     "User",
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index 9b79e2e..5acd0fd 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -573,6 +573,12 @@ class Item(SQLModel, table=True):
 # `SKILL_DOMAINS`); all three now import this constant instead.
 BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")
 
+# A rank threshold is a positive count of points, or NULL to inherit (v2.15,
+# TICKET-0106). One literal for the two tables that carry the five columns.
+RANK_POINTS_CHECK = " AND ".join(
+    f"(points_to_rank_{n} IS NULL OR points_to_rank_{n} >= 1)" for n in range(1, 6)
+)
+
 
 # -----------------------------------------------------------------------------
 # skill_system  (world-authored body of skill rules — magic, technology,
@@ -581,6 +587,7 @@ BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")
 class SkillSystem(SQLModel, table=True):
     __tablename__ = "skill_system"
     __table_args__ = (
+        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_system_rank_points"),
         Index("idx_skill_system_world_name", "world_id", "name", unique=True),
         Index("idx_skill_system_world", "world_id"),
     )
@@ -589,6 +596,13 @@ class SkillSystem(SQLModel, table=True):
     world_id: str = Field(foreign_key="world.id", nullable=False)
     name: str
     description: Optional[str] = None  # rendered as the group subtitle (F2)
+    # Points to reach each rank, for every skill of this system (v2.15,
+    # TICKET-0106). NULL = the world's default (`skill_ranks.points_to_next`).
+    points_to_rank_1: Optional[int] = None
+    points_to_rank_2: Optional[int] = None
+    points_to_rank_3: Optional[int] = None
+    points_to_rank_4: Optional[int] = None
+    points_to_rank_5: Optional[int] = None
     created_at: datetime = _created_ts()
     updated_at: datetime = _created_ts()
 
@@ -603,6 +617,7 @@ class SkillDefinition(SQLModel, table=True):
             "base_domain IN ('physical','agility','perception','composure')",
             name="ck_skill_definition_base_domain",
         ),  # canonical list: BASE_SKILL_DOMAINS above
+        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_definition_rank_points"),
         Index("idx_skill_definition_world_name", "world_id", "name", unique=True),
         Index("idx_skill_definition_world", "world_id"),
         Index("idx_skill_definition_system", "system_id"),
@@ -625,27 +640,35 @@ class SkillDefinition(SQLModel, table=True):
         ),
     )
     description: Optional[str] = None  # authored in chantier 2, not read this round
+    # Points to reach each rank for this skill (v2.15, TICKET-0106). NULL =
+    # its system's value, then the world's (`skill_ranks.points_to_next`).
+    points_to_rank_1: Optional[int] = None
+    points_to_rank_2: Optional[int] = None
+    points_to_rank_3: Optional[int] = None
+    points_to_rank_4: Optional[int] = None
+    points_to_rank_5: Optional[int] = None
     created_at: datetime = _created_ts()
     updated_at: datetime = _created_ts()
 
 
 # -----------------------------------------------------------------------------
 # skill  (player character skill sheet — physical/sensory domains, schema v1.22;
-# skill_definition_id added schema v1.63)
+# skill_definition_id added schema v1.63; `rank` and `xp` replace `tier` at
+# v2.15, TICKET-0106 — the dice modifier is `skill_ranks.rank_modifier(rank)`)
 # -----------------------------------------------------------------------------
 class Skill(SQLModel, table=True):
     __tablename__ = "skill"
     __table_args__ = (
-        CheckConstraint("tier BETWEEN -1 AND 2", name="ck_skill_tier"),
+        CheckConstraint("rank BETWEEN 0 AND 5", name="ck_skill_rank"),
+        CheckConstraint("xp >= 0", name="ck_skill_xp"),
         Index("idx_skill_character", "character_id"),
     )
 
     id: str = Field(default_factory=_uuid, primary_key=True)
     character_id: str = Field(foreign_key="entity.id", nullable=False)
     domain: str  # physical | agility | perception | composure
-    tier: int = Field(
-        default=0, sa_column_kwargs={"server_default": text("0")}
-    )
+    rank: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
+    xp: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
     change_history: list = Field(
         default_factory=list,
         sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index a6794f6..07cfb27 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -9,7 +9,9 @@ family as `Agenda` (still in `canon.py`) — only its FILE moved, not its
 identity, and every existing `from ..models import AgendaStep` import is
 unaffected (resolved through `models/__init__.py`). `agenda_step_requirement`
 is canon curated-config, same family as `location_type_catalog` / `world_law`
-(metadata-config category, no `change_history`).
+(metadata-config category, no `change_history`). `skill_rank` (TICKET-0106,
+BRIEF-0106-A) is the same curated-config family, placed here for the same
+module budget.
 """
 
 from __future__ import annotations
@@ -145,3 +147,32 @@ class AgendaStepRequirement(SQLModel, table=True):
     target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     target_key: Optional[str] = None
     threshold: Optional[int] = None
+
+
+# -----------------------------------------------------------------------------
+# skill_rank  (a world's rank ladder — schema v2.15, TICKET-0106, BRIEF-0106-A)
+#
+# At most one row per (world, rank): the name the world gives that rank and
+# the points a skill needs to leave it (`points_to_next`, NULL only for the
+# top rank). Absence of a row is legal: the reader (`skill_ranks.world_ladder`)
+# applies `skill_ranks.DEFAULT_RANK_LABELS` / `DEFAULT_POINTS_TO_NEXT` and
+# never writes on read (`conversation_window_config` precedent). Curated
+# config, no `change_history`; written only by `writes.upsert_skill_rank`.
+# -----------------------------------------------------------------------------
+class SkillRank(SQLModel, table=True):
+    __tablename__ = "skill_rank"
+    __table_args__ = (
+        CheckConstraint("rank BETWEEN 0 AND 5", name="ck_skill_rank_rank"),
+        CheckConstraint(
+            "(rank = 5 AND points_to_next IS NULL) OR (rank < 5 AND points_to_next >= 1)",
+            name="ck_skill_rank_points",
+        ),
+        Index("idx_skill_rank_world_rank", "world_id", "rank", unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    rank: int
+    label: str
+    points_to_next: Optional[int] = None
+    updated_at: datetime = _created_ts()
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 35b9ccf..aa94ef5 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.14"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.15"
diff --git a/src/world_engine/skill_ranks.py b/src/world_engine/skill_ranks.py
new file mode 100644
index 0000000..3852121
--- /dev/null
+++ b/src/world_engine/skill_ranks.py
@@ -0,0 +1,111 @@
+"""A skill's rank ladder (TICKET-0106, BRIEF-0106-A, decisions G1, L1, O1, P2,
+U2, V).
+
+Six ranks, fixed in the engine and read as numbers by the code (G1):
+0 Inexpérimenté, 1 Initié, 2 Apprenti, 3 Confirmé, 4 Expert, 5 Maître. A
+world renames them (P2) and sets the default points needed to leave each
+rank (O1) in `skill_rank`; a skill system and a skill definition may each
+override any of those points in their five `points_to_rank_<n>` columns.
+The most specific value wins: the skill definition, then its system, then
+the world, then the engine default below.
+
+The dice modifier is NOT the rank (L1): `RANK_MODIFIERS` maps it, so the
+four former tiers keep their exact modifier (tier -1/0/1/2 became rank
+0/1/2/3 at v2.15) and a Maître rolls +3 at most.
+
+Reads only: this module never writes. `world_ladder` applies the engine
+defaults to a world with no `skill_rank` row, without writing them.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+from sqlmodel import Session, select
+
+from .models import SkillDefinition, SkillRank, SkillSystem
+
+RANKS: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
+MAX_RANK: int = 5
+# A new skill row starts here: Initié, modifier 0 -- the former tier 0.
+DEFAULT_RANK: int = 1
+# Index = rank (L1).
+RANK_MODIFIERS: tuple[int, ...] = (-1, 0, 1, 2, 2, 3)
+DEFAULT_RANK_LABELS: tuple[str, ...] = (
+    "Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître",
+)
+# Index = rank left; the top rank has no next (V).
+DEFAULT_POINTS_TO_NEXT: tuple[int, ...] = (5, 10, 20, 40, 80)
+# Migration v2.15 only: the former `skill.tier` value -> its rank.
+TIER_TO_RANK: dict[int, int] = {-1: 0, 0: 1, 1: 2, 2: 3}
+# Index = rank left: `points_to_rank_<rank + 1>` holds the points to leave it.
+RANK_POINTS_COLUMNS: tuple[str, ...] = tuple(f"points_to_rank_{n}" for n in range(1, 6))
+
+
+@dataclass(frozen=True)
+class RankStep:
+    rank: int
+    label: str
+    points_to_next: Optional[int]  # None for MAX_RANK only
+
+
+def rank_modifier(rank: int) -> int:
+    """The dice modifier of a rank (L1). `ValueError` outside 0-5."""
+    if rank not in RANKS:
+        raise ValueError(f"rank_modifier: rank {rank!r} is not one of {RANKS}")
+    return RANK_MODIFIERS[rank]
+
+
+def default_ladder() -> tuple[RankStep, ...]:
+    return tuple(
+        RankStep(rank=r, label=DEFAULT_RANK_LABELS[r],
+                 points_to_next=DEFAULT_POINTS_TO_NEXT[r] if r < MAX_RANK else None)
+        for r in RANKS
+    )
+
+
+def world_ladder(db: Session, world_id: str) -> tuple[RankStep, ...]:
+    """The world's six ranks, index = rank: its `skill_rank` rows over the
+    engine defaults. Never writes."""
+    stored = {row.rank: row for row in db.exec(select(SkillRank).where(SkillRank.world_id == world_id)).all()}
+    steps: list[RankStep] = []
+    for step in default_ladder():
+        row = stored.get(step.rank)
+        steps.append(step if row is None else RankStep(
+            rank=step.rank, label=row.label,
+            points_to_next=row.points_to_next if step.rank < MAX_RANK else None,
+        ))
+    return tuple(steps)
+
+
+def points_to_next(
+    rank: int, ladder: tuple[RankStep, ...], *, system: Any = None, definition: Any = None,
+) -> Optional[int]:
+    """Points needed to leave `rank`: `definition`'s column, else `system`'s,
+    else the ladder's (O1). None at MAX_RANK. `system`/`definition` are any
+    objects carrying the five `points_to_rank_<n>` attributes, or None."""
+    if rank >= MAX_RANK:
+        return None
+    column = RANK_POINTS_COLUMNS[rank]
+    for owner in (definition, system):
+        value = getattr(owner, column, None) if owner is not None else None
+        if value is not None:
+            return value
+    return ladder[rank].points_to_next
+
+
+def skill_owners(db: Session, skill_definition_id: Optional[str]) -> tuple[Optional[SkillSystem], Optional[SkillDefinition]]:
+    """(system, definition) of a skill row; (None, None) for a base domain."""
+    if skill_definition_id is None:
+        return None, None
+    definition = db.get(SkillDefinition, skill_definition_id)
+    if definition is None or definition.system_id is None:
+        return None, definition
+    return db.get(SkillSystem, definition.system_id), definition
+
+
+def skill_points_to_next(db: Session, *, world_id: str, rank: int, skill_definition_id: Optional[str]) -> Optional[int]:
+    """`points_to_next` for one skill row, its owners and ladder read here."""
+    system, definition = skill_owners(db, skill_definition_id)
+    return points_to_next(rank, world_ladder(db, world_id), system=system, definition=definition)
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index a70b56d..c615207 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -50,7 +50,7 @@ _find_relation_pair`, etc.) is untouched, byte for byte, by this split.
 from __future__ import annotations
 
 from ._shared import _append_history_snapshot, _clamp
-from .characters import write_character_location, write_ledger_entry, write_skill_tier
+from .characters import write_character_location, write_ledger_entry, write_skill_rank
 from .config import (
     upsert_conversation_window_config,
     upsert_location_type,
@@ -148,7 +148,7 @@ __all__ = [
     "create_fact",
     "create_fact_default",
     "attach_participants",
-    "write_skill_tier",
+    "write_skill_rank",
     "write_ledger_entry",
     "write_membership",
     "write_event",
diff --git a/src/world_engine/writes/characters.py b/src/world_engine/writes/characters.py
index 676225f..7c1c469 100644
--- a/src/world_engine/writes/characters.py
+++ b/src/world_engine/writes/characters.py
@@ -4,9 +4,11 @@ none of these three functions were baselined.
 
 - `write_character_location(...)`      : write a character's
   `current_location_id` (TICKET-0015, BRIEF-0015-a).
-- `write_skill_tier(...)`               : set a `skill` row's tier,
-  appending the previous tier to `change_history` first (history is sacred
-  on this path too). The sole write shape for `skill` tier changes.
+- `write_skill_rank(...)`               : set a `skill` row's rank,
+  appending the previous rank and points to `change_history` first
+  (history is sacred on this path too) and restarting its points at 0
+  (U2). The sole write shape for a creator's rank edit (TICKET-0106,
+  BRIEF-0106-A; formerly `write_skill_tier`).
 - `write_ledger_entry(...)`             : pure INSERT into the append-only
   `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
   new compensating line. The single chokepoint for ledger writes, shared by
@@ -23,6 +25,7 @@ from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session
 
 from ..models import Character, Ledger, Skill
+from ..skill_ranks import RANKS
 
 
 def write_character_location(
@@ -50,35 +53,40 @@ def write_character_location(
     return character
 
 
-def write_skill_tier(
+def write_skill_rank(
     db: Session,
     *,
     skill_id: str,
-    tier: int,
+    rank: int,
     changed_by: str = "creator",
 ) -> Skill:
-    """Set a `skill` row's tier. Caller adds the row to the session.
+    """Set a `skill` row's rank. Caller adds the row to the session.
 
-    The sole write shape for `skill` tier changes (`cockpit/crud.py`'s
-    `update_skill_tier` is its only caller). Appends the previous tier to
-    `change_history` first (history is sacred), then sets `tier` and bumps
+    The sole write shape for a creator's rank edit (`cockpit/crud/skills.py`'s
+    `update_skill_rank` is its only caller). Appends the previous rank and
+    points to `change_history` first (history is sacred), then sets `rank`,
+    restarts `xp` at 0 (U2: points count within a rank) and bumps
     `updated_at`. The caller decides whether to call this at all — a
-    resubmission of the same tier should be a no-op, not an empty history
-    entry.
+    resubmission of the same rank should be a no-op, not an empty history
+    entry. `ValueError` outside `skill_ranks.RANKS`, before any write.
     """
+    if rank not in RANKS:
+        raise ValueError(f"write_skill_rank: rank {rank!r} is not one of {RANKS}")
     skill = db.get(Skill, skill_id)
     if skill is None:
-        raise ValueError(f"write_skill_tier: skill {skill_id!r} not found")
+        raise ValueError(f"write_skill_rank: skill {skill_id!r} not found")
 
     history = list(skill.change_history or [])
     history.append({
-        "tier": skill.tier,
+        "rank": skill.rank,
+        "xp": skill.xp,
         "changed_at": datetime.now(UTC).isoformat(),
         "by": changed_by,
     })
     skill.change_history = history
     sa_attrs.flag_modified(skill, "change_history")
-    skill.tier = tier
+    skill.rank = rank
+    skill.xp = 0
     skill.updated_at = datetime.now(UTC)
 
     db.add(skill)
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 24059cf..17634d7 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -73,7 +73,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "faction_role", "goal_agenda_link", "goal_prerequisite",
     "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
     "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
-    "skill_resolution", "skill_system", "unresolved_mention", "visit",
+    "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
     "world_law",
 )
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index dff431f..46781b0 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17875,6 +17875,33 @@ in the dossier (it lists stored rows); showing it is its own ticket.
 **Rejected.** T2, a rule in the Lore prompt (a new prompt version) for a
 mark the code already writes.
 
+
+## A SKILL HAS A RANK AND POINTS (TICKET-0106) -- SIX RANKS, A MODIFIER TABLE, THRESHOLDS AT THREE LEVELS (BRIEF-0106-a, schema v2.15)
+
+**G1, L1.** `skill.tier` (-1..2) becomes `skill.rank`: six ranks fixed in
+the engine (0 Inexpérimenté, 1 Initié, 2 Apprenti, 3 Confirmé, 4 Expert,
+5 Maître), read as numbers by the code. The dice modifier is not the rank:
+`skill_ranks.RANK_MODIFIERS` maps it (-1, 0, +1, +2, +2, +3), so the four
+former tiers keep their exact roll (tier -1/0/1/2 became rank 0/1/2/3) and
+a Maître can still fail. Both rolls (`play_physical`, `day_resolve`) read
+`rank_modifier`. A new skill row starts at Initié, the former tier 0. NPCs
+keep `character.physical_tier` until they have skill sheets.
+
+**U2, O1, P2.** `skill.xp` counts the points earned within the current
+rank; a creator's rank edit restarts it at 0 and archives the previous rank
+and points. A world names its ranks and sets the default points to leave
+each one in `skill_rank` (absent rows read the engine defaults: 5, 10, 20,
+40, 80); a skill system and a skill definition may each override any of
+the five thresholds (`points_to_rank_<n>`, NULL = inherit). The most
+specific value wins: definition, system, world, engine
+(`skill_ranks.points_to_next`).
+
+**Rejected.** G2, a ladder whose length each world chooses: every reader
+would carry a variable scale; reactivates when a world needs it. G3, rank =
+modifier: a Maître against an untrained NPC could almost never fail. T2,
+widening `tier` to 0..5: a misleading name forever. Override rows in a
+separate table: a cleared override would be a hard delete.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index d2f076c..da7eb25 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -5,6 +5,7 @@ event artifact npc_goal agenda agenda_step goal_agenda_link
 npc_price world_law obstacle obstacle_vertex door
 location_type_catalog entity_type entity_type_history conversation_window_config
 npc_schedule agenda_step_requirement fact fact_participant fact_default
+skill_rank
 
 [ALLOWED_SITES]
 # path::function                                              tables
@@ -21,7 +22,7 @@ src/world_engine/writes/characters.py::write_character_location character
 src/world_engine/writes/knowledge.py::write_knowledge          knowledge
 src/world_engine/writes/characters.py::write_ledger_entry      ledger
 src/world_engine/writes/factions.py::write_membership          faction_membership
-src/world_engine/writes/characters.py::write_skill_tier        skill
+src/world_engine/writes/characters.py::write_skill_rank        skill
 src/world_engine/writes/goals_agendas.py::write_npc_goal       npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_status npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_prerequisites npc_goal
diff --git a/tooling/verify/checks/skill_progression.py b/tooling/verify/checks/skill_progression.py
new file mode 100644
index 0000000..10380d9
--- /dev/null
+++ b/tooling/verify/checks/skill_progression.py
@@ -0,0 +1,415 @@
+"""G1 check for TICKET-0106 -- a skill progresses from Inexpérimenté to Maître.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`fact_learning.py` precedent, TICKET-0105). Each brief adds its rules here in
+the same commit.
+
+A1 -- schema (BRIEF-0106-A, v2.15). `skill` declares `rank` (default
+   `skill_ranks.DEFAULT_RANK`) and `xp` (default 0), the CHECKs
+   `ck_skill_rank` (`rank BETWEEN 0 AND 5`) and `ck_skill_xp` (`xp >= 0`), and
+   no `tier`; `skill_system` and `skill_definition` each declare the five
+   nullable `points_to_rank_1..5` and a `ck_*_rank_points` CHECK;
+   `skill_rank` declares exactly `id, world_id, rank, label, points_to_next,
+   updated_at`, the CHECKs `ck_skill_rank_rank`, `ck_skill_rank_points` and
+   the UNIQUE index `idx_skill_rank_world_rank (world_id, rank)`.
+   `skill_ranks` carries six ranks, the modifiers (-1, 0, 1, 2, 2, 3), the
+   labels Inexpérimenté .. Maître, the default points (5, 10, 20, 40, 80),
+   and `TIER_TO_RANK` keeps every former tier's modifier.
+A2 -- migration `scripts/migrate_v2_15_skill_ranks.py`, on a v2.14-shaped
+   database (the three skill tables in their v2.14 DDL, verbatim below,
+   `skill_rank` absent), holding a system, a definition attached to it, and
+   four skill rows at tiers -1, 0, 1, 2:
+   a. at v2.13 it refuses (non-zero exit) and changes nothing;
+   b. at v2.14 it gives ranks 0, 1, 2, 3 and xp 0 to the four rows (ids,
+      domains, definitions and histories kept), keeps the system and the
+      definition, rebuilds the three tables with the models' shape and
+      CHECKs, creates `skill_rank` empty, leaves `PRAGMA foreign_key_check`
+      empty and moves `schema_meta` to the code's version;
+   c. a second run exits zero and changes no row.
+A3 -- the ladder and its readers (fixture). `world_ladder` of a world with
+   no row is the engine default; a `skill_rank` row renames its rank and
+   changes its points; `points_to_next` takes the definition's column, else
+   its system's, else the ladder's (a system and a definition both setting
+   rank 3: the definition wins), and is None at rank 5. `GET
+   /api/skill-ranks` serves the six steps; `GET /api/skills` serves `rank`,
+   `rank_label`, `xp`, `points_to_next`; `PATCH /api/skills/{id}` with
+   `{rank}` appends the previous rank and points to `change_history` and
+   restarts `xp` at 0, refuses rank 6 with 422, and is a no-op on the same
+   rank. Both rolls read the rank's modifier: a rank-4 base row gives
+   `day_resolve._step_player_tier` 2.
+A4 -- no tier left (AST and static). No `.tier` attribute and no `tier=`
+   keyword argument under `src/` or in `scripts/seed_pilot.py`;
+   `PjSkillFiche.svelte` and `cockpit/crud/skills.py` do not contain the
+   word `tier`; `play_physical.py` calls `rank_modifier(`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that examines zero rows is a
+FAILURE.
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
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_15_skill_ranks.py"
+
+FAILURES: list[str] = []
+
+# The three tables as v2.14 created them (dumped from `main` at a5fbc1e).
+_V214_DDL = (
+    """CREATE TABLE skill_system (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
+	description VARCHAR,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id), FOREIGN KEY(world_id) REFERENCES world (id))""",
+    "CREATE UNIQUE INDEX idx_skill_system_world_name ON skill_system (world_id, name)",
+    "CREATE INDEX idx_skill_system_world ON skill_system (world_id)",
+    """CREATE TABLE skill_definition (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
+	base_domain VARCHAR NOT NULL, system_id VARCHAR, description VARCHAR,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT)""",
+    "CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name)",
+    "CREATE INDEX idx_skill_definition_system ON skill_definition (system_id)",
+    "CREATE INDEX idx_skill_definition_world ON skill_definition (world_id)",
+    """CREATE TABLE skill (
+	id VARCHAR NOT NULL, character_id VARCHAR NOT NULL, domain VARCHAR NOT NULL,
+	tier INTEGER DEFAULT 0 NOT NULL, change_history JSON DEFAULT '[]' NOT NULL,
+	skill_definition_id VARCHAR,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id), CONSTRAINT ck_skill_tier CHECK (tier BETWEEN -1 AND 2),
+	FOREIGN KEY(character_id) REFERENCES entity (id),
+	FOREIGN KEY(skill_definition_id) REFERENCES skill_definition (id) ON DELETE RESTRICT)""",
+    "CREATE INDEX idx_skill_character ON skill (character_id)",
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
+def _checks_of(table) -> dict[str, str]:
+    from sqlalchemy import CheckConstraint
+    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+
+
+# --- A1 ------------------------------------------------------------------------
+
+def check_a1() -> None:
+    from world_engine import skill_ranks
+    from world_engine.models import Skill, SkillDefinition, SkillRank, SkillSystem
+
+    skill = {c.name: c for c in Skill.__table__.columns}
+    if "tier" in skill or not {"rank", "xp"} <= set(skill):
+        fail(f"A1: skill columns are {sorted(skill)}")
+    else:
+        if str(skill["rank"].server_default.arg) != str(skill_ranks.DEFAULT_RANK):
+            fail(f"A1: skill.rank defaults to {skill['rank'].server_default.arg!r}")
+        if str(skill["xp"].server_default.arg) != "0":
+            fail(f"A1: skill.xp defaults to {skill['xp'].server_default.arg!r}")
+    checks = _checks_of(Skill.__table__)
+    if checks.get("ck_skill_rank") != "rank BETWEEN 0 AND 5" or checks.get("ck_skill_xp") != "xp >= 0" \
+            or "ck_skill_tier" in checks:
+        fail(f"A1: skill CHECKs are {checks}")
+    for model, name in ((SkillSystem, "ck_skill_system_rank_points"),
+                        (SkillDefinition, "ck_skill_definition_rank_points")):
+        columns = {c.name: c for c in model.__table__.columns}
+        for column in skill_ranks.RANK_POINTS_COLUMNS:
+            if column not in columns or not columns[column].nullable:
+                fail(f"A1: {model.__tablename__}.{column} is missing or NOT NULL")
+        text = _checks_of(model.__table__).get(name, "")
+        if any(f"{c} >= 1" not in text for c in skill_ranks.RANK_POINTS_COLUMNS):
+            fail(f"A1: {model.__tablename__} {name} is {text!r}")
+    ladder = SkillRank.__table__
+    if {c.name for c in ladder.columns} != {"id", "world_id", "rank", "label", "points_to_next", "updated_at"}:
+        fail(f"A1: skill_rank columns are {sorted(c.name for c in ladder.columns)}")
+    if set(_checks_of(ladder)) != {"ck_skill_rank_rank", "ck_skill_rank_points"}:
+        fail(f"A1: skill_rank CHECKs are {_checks_of(ladder)}")
+    indexes = {i.name: ([c.name for c in i.columns], bool(i.unique)) for i in ladder.indexes}
+    if indexes != {"idx_skill_rank_world_rank": (["world_id", "rank"], True)}:
+        fail(f"A1: skill_rank indexes are {indexes}")
+    expected = (
+        (skill_ranks.RANKS, (0, 1, 2, 3, 4, 5)),
+        (skill_ranks.RANK_MODIFIERS, (-1, 0, 1, 2, 2, 3)),
+        (skill_ranks.DEFAULT_RANK_LABELS,
+         ("Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître")),
+        (skill_ranks.DEFAULT_POINTS_TO_NEXT, (5, 10, 20, 40, 80)),
+    )
+    for got, want in expected:
+        if tuple(got) != want:
+            fail(f"A1: skill_ranks carries {got}, expected {want}")
+    if sorted(skill_ranks.TIER_TO_RANK) != [-1, 0, 1, 2] or any(
+            skill_ranks.RANK_MODIFIERS[r] != t for t, r in skill_ranks.TIER_TO_RANK.items()):
+        fail(f"A1: TIER_TO_RANK {skill_ranks.TIER_TO_RANK} changes a former tier's modifier")
+
+
+# --- A2 ------------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _shape(conn, table: str) -> list[tuple]:
+    return [(r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})")]
+
+
+def _seed_v214(db_path: str) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import Character, Entity, SchemaMeta, World
+
+    create_db_and_tables()
+    with Session(engine) as session:
+        world = World(name="Ranks A2", is_active=True)
+        session.add(world)
+        session.flush()
+        pc = Entity(world_id=world.id, type="character", name="PC")
+        session.add(pc)
+        session.flush()
+        session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.14"))
+        session.commit()
+        ids = {"world": world.id, "pc": pc.id}
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        model_shapes = {t: _shape(conn, t) for t in ("skill_system", "skill_definition", "skill", "skill_rank")}
+        conn.execute("PRAGMA foreign_keys=OFF")
+        for table in ("skill", "skill_definition", "skill_system", "skill_rank"):
+            conn.execute(f"DROP TABLE {table}")
+        for statement in _V214_DDL:
+            conn.execute(statement)
+        conn.execute("INSERT INTO skill_system (id, world_id, name) VALUES ('sys', ?, 'Magie')", (ids["world"],))
+        conn.execute("INSERT INTO skill_definition (id, world_id, name, base_domain, system_id) "
+                     "VALUES ('def', ?, 'Feu', 'composure', 'sys')", (ids["world"],))
+        for tier, domain, definition in ((-1, "physical", None), (0, "agility", None),
+                                         (1, "perception", None), (2, "composure", "def")):
+            conn.execute("INSERT INTO skill (id, character_id, domain, tier, change_history, "
+                         "skill_definition_id) VALUES (?, ?, ?, ?, ?, ?)",
+                         (f"t{tier}", ids["pc"], domain, tier, '[{"tier": 0}]', definition))
+    ids["model_shapes"] = model_shapes
+    return ids
+
+
+def _set_version(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        skill_columns = {r[1] for r in conn.execute("PRAGMA table_info(skill)")}
+        state = {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "shapes": {t: _shape(conn, t) for t in ("skill_system", "skill_definition", "skill", "skill_rank")
+                       if t in tables},
+            "systems": conn.execute("SELECT id, name FROM skill_system").fetchall(),
+            "definitions": conn.execute("SELECT id, system_id FROM skill_definition").fetchall(),
+            "fk": conn.execute("PRAGMA foreign_key_check").fetchall(),
+            "ladder": conn.execute("SELECT COUNT(*) FROM skill_rank").fetchone()[0] if "skill_rank" in tables else None,
+            "ddl": sorted(r[0] for r in conn.execute(
+                "SELECT sql FROM sqlite_master WHERE tbl_name IN ('skill','skill_system','skill_definition') "
+                "AND sql IS NOT NULL")),
+        }
+        state["skills"] = sorted(conn.execute(
+            "SELECT id, domain, rank, xp, change_history, skill_definition_id FROM skill").fetchall()
+        ) if "rank" in skill_columns else None
+    return state
+
+
+def check_a2(db_path: str) -> None:
+    ids = _seed_v214(db_path)
+    _set_version(db_path, "v2.13")
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail(f"A2a: v2.13 was not refused, or changed rows (exit {result.returncode})")
+    _set_version(db_path, "v2.14")
+    result = _run_migration(db_path)
+    after = _state(db_path)
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: {result.stderr.strip()[-400:]}")
+        return
+    want = [("t-1", "physical", 0, 0, '[{"tier": 0}]', None), ("t0", "agility", 1, 0, '[{"tier": 0}]', None),
+            ("t1", "perception", 2, 0, '[{"tier": 0}]', None), ("t2", "composure", 3, 0, '[{"tier": 0}]', "def")]
+    if after["skills"] != want:
+        fail(f"A2b: skills are {after['skills']}")
+    if after["systems"] != [("sys", "Magie")] or after["definitions"] != [("def", "sys")]:
+        fail(f"A2b: systems {after['systems']}, definitions {after['definitions']}")
+    if after["shapes"] != ids["model_shapes"]:
+        fail(f"A2b: shapes {after['shapes']} differ from the models {ids['model_shapes']}")
+    if after["ladder"] != 0 or after["fk"]:
+        fail(f"A2b: skill_rank rows {after['ladder']}, foreign_key_check {after['fk']}")
+    ddl = " ".join(after["ddl"])
+    for name in ("ck_skill_rank", "ck_skill_xp", "ck_skill_system_rank_points",
+                 "ck_skill_definition_rank_points", "ck_skill_definition_base_domain"):
+        if name not in ddl:
+            fail(f"A2b: {name} missing after the rebuild")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or _state(db_path) != after:
+        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")
+
+
+# --- A3 ------------------------------------------------------------------------
+
+def _a3_world(session) -> dict:
+    from world_engine.models import Character, Entity, Skill, SkillDefinition, SkillSystem, World
+
+    for world in session.exec(__import__("sqlmodel").select(World)).all():
+        world.is_active = False
+        session.add(world)
+    world = World(name="Ranks A3", is_active=True)
+    session.add(world)
+    session.flush()
+    pc = Entity(world_id=world.id, type="character", name="Millys")
+    session.add(pc)
+    session.flush()
+    session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
+    system = SkillSystem(world_id=world.id, name="Alchimie", points_to_rank_2=7, points_to_rank_3=9)
+    session.add(system)
+    session.flush()
+    definition = SkillDefinition(world_id=world.id, name="Distillation", base_domain="composure",
+                                 system_id=system.id, points_to_rank_3=3)
+    session.add(definition)
+    session.flush()
+    base = Skill(character_id=pc.id, domain="physical", rank=4)
+    custom = Skill(character_id=pc.id, domain="composure", rank=1, skill_definition_id=definition.id)
+    session.add(base)
+    session.add(custom)
+    session.commit()
+    return {"world": world.id, "pc": pc.id, "system": system, "definition": definition,
+            "base": base.id, "custom": custom.id}
+
+
+def check_a3(engine) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine import skill_ranks
+    from world_engine.cockpit.crud.skills import (
+        SkillRankBody, list_skill_ranks, list_skills, update_skill_rank,
+    )
+    from world_engine.day_resolve import _step_player_tier
+    from world_engine.models import Character, Skill, SkillRank
+
+    with Session(engine) as session:
+        ids = _a3_world(session)
+        ladder = skill_ranks.world_ladder(session, ids["world"])
+        if ladder != skill_ranks.default_ladder():
+            fail(f"A3: an empty world's ladder is {ladder}")
+        session.add(SkillRank(world_id=ids["world"], rank=2, label="Disciple", points_to_next=30))
+        session.commit()
+        ladder = skill_ranks.world_ladder(session, ids["world"])
+        if (ladder[2].label, ladder[2].points_to_next) != ("Disciple", 30) or ladder[1] != skill_ranks.default_ladder()[1]:
+            fail(f"A3: the ladder with one row is {ladder}")
+        system, definition = ids["system"], ids["definition"]
+        cases = (
+            ((2, None, None), 30), ((2, system, None), 9), ((1, system, None), 7),
+            ((2, system, definition), 3), ((1, None, definition), 10), ((5, system, definition), None),
+        )
+        for (rank, sys_, def_), want in cases:
+            got = skill_ranks.points_to_next(rank, ladder, system=sys_, definition=def_)
+            if got != want:
+                fail(f"A3: points_to_next(rank {rank}, system {bool(sys_)}, definition {bool(def_)}) = {got}, want {want}")
+        served = list_skill_ranks(session)
+        if [s["label"] for s in served] != [st.label for st in ladder] or len(served) != 6:
+            fail(f"A3: GET /api/skill-ranks served {served}")
+        sheet = {row["id"]: row for row in list_skills(character_id=ids["pc"], db=session)}
+        base = sheet.get(ids["base"], {})
+        if (base.get("rank"), base.get("rank_label"), base.get("xp"), base.get("points_to_next")) != (4, "Expert", 0, 80):
+            fail(f"A3: GET /api/skills served {base}")
+        custom = sheet.get(ids["custom"], {})
+        if custom.get("points_to_next") != 7:
+            fail(f"A3: the custom row's points_to_next is {custom.get('points_to_next')} (system override 7)")
+        if _step_player_tier(session.get(Character, ids["pc"]), "physical", session) != 2:
+            fail("A3: a rank-4 base row does not roll +2 in a day step")
+        row = session.get(Skill, ids["base"])
+        row.xp = 12
+        session.add(row)
+        session.commit()
+        served = update_skill_rank(ids["base"], SkillRankBody(rank=5), session)
+        row = session.get(Skill, ids["base"])
+        if (row.rank, row.xp) != (5, 0) or row.change_history[-1].get("rank") != 4 \
+                or row.change_history[-1].get("xp") != 12 or served.get("rank_label") != "Maître":
+            fail(f"A3: PATCH rank 5 left rank {row.rank}, xp {row.xp}, history {row.change_history}, served {served}")
+        length = len(row.change_history)
+        update_skill_rank(ids["base"], SkillRankBody(rank=5), session)
+        if len(session.get(Skill, ids["base"]).change_history) != length:
+            fail("A3: the same rank appended a history entry")
+        try:
+            update_skill_rank(ids["base"], SkillRankBody(rank=6), session)
+            fail("A3: rank 6 was accepted")
+        except HTTPException as exc:
+            if exc.status_code != 422:
+                fail(f"A3: rank 6 answered {exc.status_code}")
+
+
+# --- A4 ------------------------------------------------------------------------
+
+def check_a4() -> None:
+    import ast
+
+    scanned = 0
+    for path in sorted((ROOT / "src").rglob("*.py")) + [ROOT / "scripts" / "seed_pilot.py"]:
+        scanned += 1
+        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+            if isinstance(node, ast.Attribute) and node.attr == "tier":
+                fail(f"A4: .tier read at {path.relative_to(ROOT)}:{node.lineno}")
+            if isinstance(node, ast.keyword) and node.arg == "tier":
+                fail(f"A4: tier= written at {path.relative_to(ROOT)}:{node.value.lineno}")
+    if scanned == 0:
+        fail("A4: no file scanned")
+    for rel in ("frontend/src/creation/PjSkillFiche.svelte", "src/world_engine/cockpit/crud/skills.py"):
+        if re.search(r"\btier\b", (ROOT / rel).read_text(encoding="utf-8")):
+            fail(f"A4: {rel} still names a tier")
+    if "rank_modifier(" not in (SRC / "cockpit" / "play_physical.py").read_text(encoding="utf-8"):
+        fail("A4: play_physical.py does not call rank_modifier(")
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_a1()
+    check_a2(db_path)
+    # The migrated database is the v2.15 one the later rules write into.
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_a3(engine)
+    check_a4()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: skill_progression -- v2.15 gives a skill a rank (0-5) and points in place of "
+          "its tier, keeps every former tier's roll, lets a world, a system and a skill set "
+          "the points of each rank, and migrates from v2.14 only")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/skill_system_shape.py b/tooling/verify/checks/skill_system_shape.py
index 41de2c8..9823818 100644
--- a/tooling/verify/checks/skill_system_shape.py
+++ b/tooling/verify/checks/skill_system_shape.py
@@ -7,7 +7,8 @@ never a vacuous pass (known_reachability.py rule).
 
 Four assertions:
   1. `skill_system` exists with exactly the columns `id, world_id, name,
-     description, created_at, updated_at` — no extras.
+     description, created_at, updated_at` and, since v2.15 (TICKET-0106),
+     `points_to_rank_1` .. `points_to_rank_5` — no extras.
   2. `skill_definition.system_id` exists and is nullable.
   3. `BASE_SKILL_DOMAINS` has exactly four members.
   4. `ck_skill_definition_base_domain`'s constraint text still names exactly
@@ -28,6 +29,9 @@ FAILURES: list[str] = []
 
 EXPECTED_SKILL_SYSTEM_COLUMNS = {
     "id", "world_id", "name", "description", "created_at", "updated_at",
+    # TICKET-0106 (BRIEF-0106-A, v2.15): the system's rank thresholds.
+    "points_to_rank_1", "points_to_rank_2", "points_to_rank_3",
+    "points_to_rank_4", "points_to_rank_5",
 }
 EXPECTED_BASE_DOMAINS = {"physical", "agility", "perception", "composure"}
 
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 26ae6fb..ea238a3 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -108,6 +108,8 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                    "last_at": "2026-01-01 00:00:00", "source": "fixture"}),
     ("session", {"id": "ses-{w}", "world_id": "{w}", "number": 1}),
     ("skill_system", {"id": "ss-{w}", "world_id": "{w}", "name": "s"}),
+    ("skill_rank", {"id": "srk-{w}", "world_id": "{w}", "rank": 2, "label": "Apprenti",
+                    "points_to_next": 20}),
     ("visit", {"id": "vis-{w}", "world_id": "{w}", "player_id": "{w}-char",
                "location_id": "{w}-loc"}),
     ("world_law", {"id": "wl-{w}", "world_id": "{w}", "text": "t"}),
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index eabcb3a..9b34e35 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,15 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.15** — TICKET-0106, BRIEF-0106-A: a skill has a rank and points.
+  `skill.tier` (-1..2) becomes `skill.rank` (0..5: Inexpérimenté, Initié,
+  Apprenti, Confirmé, Expert, Maître) plus `skill.xp`; the dice modifier is
+  `skill_ranks.RANK_MODIFIERS[rank]` (-1, 0, +1, +2, +2, +3), so each
+  former tier keeps its roll. `skill_system` and `skill_definition` gain
+  `points_to_rank_1..5` (NULL = inherit); `skill_rank` holds a world's rank
+  names and default points. `migrate_v2_15_skill_ranks.py` rebuilds the
+  three skill tables from the models (tier -1/0/1/2 -> rank 0/1/2/3, xp 0),
+  creates `skill_rank` empty, and refuses a database older than v2.14.
 - **v2.14** — TICKET-0105, BRIEF-0105-A: what a character keeps of a fact.
   `passage` (one row per character and location, with the last time the
   character was there) and `rencontre.last_at` (the last contact of a pair,
diff --git a/world-engine-schema.md b/world-engine-schema.md
index db203f2..5a54577 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.14
+Current schema version: v2.15
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1663,8 +1663,17 @@ CREATE TABLE skill_system (
   world_id     TEXT NOT NULL REFERENCES world(id),
   name         TEXT NOT NULL,
   description  TEXT,                   -- rendered as the group subtitle (F2)
+  points_to_rank_1  INTEGER,           -- points to reach rank n, for every skill
+  points_to_rank_2  INTEGER,           -- of this system (v2.15); NULL = the
+  points_to_rank_3  INTEGER,           -- world's default (skill_rank)
+  points_to_rank_4  INTEGER,
+  points_to_rank_5  INTEGER,
   created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
-  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
+  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
+  CONSTRAINT ck_skill_system_rank_points CHECK (
+    (points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1)
+    AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1)
+    AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1))
 );
 CREATE UNIQUE INDEX idx_skill_system_world_name
   ON skill_system(world_id, name);
@@ -1696,8 +1705,17 @@ CREATE TABLE skill_definition (
   system_id    TEXT REFERENCES skill_system(id) ON DELETE RESTRICT,
   description  TEXT,                   -- prose; authored in chantier 2, NOT
                                        -- read by any consumer this round
+  points_to_rank_1  INTEGER,           -- points to reach rank n for this skill
+  points_to_rank_2  INTEGER,           -- (v2.15); NULL = its system's value,
+  points_to_rank_3  INTEGER,           -- then the world's (skill_rank)
+  points_to_rank_4  INTEGER,
+  points_to_rank_5  INTEGER,
   created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
-  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
+  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
+  CONSTRAINT ck_skill_definition_rank_points CHECK (
+    (points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1)
+    AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1)
+    AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1))
 );
 CREATE UNIQUE INDEX idx_skill_definition_world_name
   ON skill_definition(world_id, name);
@@ -1724,7 +1742,8 @@ CREATE INDEX idx_skill_definition_system ON skill_definition(system_id);
 ### `skill`
 
 The player character's skill sheet (schema v1.22) — physical/sensory domains
-with a tier value and full change history. `skill_definition_id` added
+with a rank, the points earned within it (v2.15, replacing `tier`) and full
+change history. `skill_definition_id` added
 schema v1.63 distinguishes a base-domain row (NULL) from a custom-skill row
 (set).
 
@@ -1734,9 +1753,13 @@ CREATE TABLE skill (
   character_id          TEXT NOT NULL REFERENCES entity(id),
   domain                TEXT NOT NULL,
                         -- physical | agility | perception | composure
-  tier                  INTEGER NOT NULL DEFAULT 0 CHECK (tier BETWEEN -1 AND 2),
-                        -- -1 weak | 0 average | +1 trained | +2 exceptional
-                        -- translated directly into the 2d6 modifier (later step)
+  rank                  INTEGER NOT NULL DEFAULT 1 CHECK (rank BETWEEN 0 AND 5),
+                        -- 0 Inexpérimenté | 1 Initié | 2 Apprenti |
+                        -- 3 Confirmé | 4 Expert | 5 Maître (names: skill_rank);
+                        -- 2d6 modifier = skill_ranks.RANK_MODIFIERS[rank]
+                        -- (-1, 0, +1, +2, +2, +3) -- v2.15, replaces tier
+  xp                    INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
+                        -- points earned within the current rank (U2)
   change_history        JSON DEFAULT '[]',  -- archived previous states, same
                                              -- pattern as relation.change_history
   skill_definition_id    TEXT REFERENCES skill_definition(id) ON DELETE RESTRICT,
@@ -1762,6 +1785,35 @@ CREATE INDEX idx_skill_character ON skill(character_id);
 -- belong to the free-dialogue layer and the relation graph. This is a
 -- standing design guard, not a deferral.
 
+
+-----
+
+### `skill_rank`
+
+A world's rank ladder (schema v2.15, TICKET-0106): the name the world gives
+each of the six ranks and the default points a skill needs to leave it.
+At most one row per (world, rank); a missing row reads the engine default
+(`skill_ranks.DEFAULT_RANK_LABELS`, `DEFAULT_POINTS_TO_NEXT`: 5, 10, 20, 40,
+80). A skill system's or a skill definition's `points_to_rank_<n>` overrides
+it, the most specific value winning.
+
+```sql
+CREATE TABLE skill_rank (
+  id              TEXT PRIMARY KEY,
+  world_id        TEXT NOT NULL REFERENCES world(id),
+  rank            INTEGER NOT NULL CHECK (rank BETWEEN 0 AND 5),
+  label           TEXT NOT NULL,
+  points_to_next  INTEGER,              -- NULL only for rank 5
+  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
+  CONSTRAINT ck_skill_rank_points CHECK (
+    (rank = 5 AND points_to_next IS NULL) OR (rank < 5 AND points_to_next >= 1))
+);
+CREATE UNIQUE INDEX idx_skill_rank_world_rank ON skill_rank(world_id, rank);
+```
+
+-- NOTE: curated config, no change_history; written only by
+-- `writes.upsert_skill_rank` (creator CRUD), read by
+-- `skill_ranks.world_ladder`, which never writes on read.
 -----
 
 ### `discoverable_detail`
````

## Scope OUT

- Earning points, ranking up, the `skill_progress` mutation (B).
- Writing `skill_rank` or the threshold columns from any route (C); `skill_rank` has no writer in this brief.
- Showing points on the fiche or in the day's account (D).
- NPC skill sheets, `character.physical_tier` (I1, its own ticket); `npc_group_author.py`'s `physical_tier` clamp.
- Rewriting the `tier` keys of `change_history` entries written before v2.15 (history is never rewritten).
- `scripts/migrate_v1_65_pc_skill_backfill.py` (historical).
- `legacy.html` (Play is sealed).
- Every later brief of this lot.

## Invariants to defend

**History is sacred:** the rebuild copies every row and every `change_history` untouched; `write_skill_rank` archives before it overwrites. **The schema is authoritative:** model, schema doc, changelog, constant and migration move together. **Custom skill lookups filter `skill_definition_id`:** both rolls keep their base-domain filter; only the attribute read changes. **Hard deletes are a closed list:** the migration's `DROP TABLE <name>_old` is part of a rebuild inside one transaction, the `migrate_v1_95` precedent, not a new delete path.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `play_physical.py` is not exactly 996 lines after the commit.
- The A2 rule of `skill_progression.py` fails (the migration on a v2.14-shaped database).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `CLAUDE.md` because a neighbouring line moved: make the one wording change (« a tier-0 » → « a default-rank ») by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `scripts/migrate_v1_65_pc_skill_backfill.py` still naming `tier` (historical, left alone).
- `npm ci` engine warnings (`EBADENGINE`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/skill_progression.py` → `PASS: skill_progression -- v2.15 gives a skill a rank (0-5) and points in place of its tier, …, and migrates from v2.14 only`.
- `single_canon_write.py`, `world_cascade.py`, `skill_system_shape.py`, `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py`, `module_budget.py`, `pipeline_state.py`, `decisions_index.py`, `claude_md_contract.py`, `frontend_build_fresh.py` → `PASS`.
- Mutation tests, each red then reverted: in `skill_ranks.py`, `TIER_TO_RANK: dict[int, int] = {-1: 0, 0: 1, 1: 2, 2: 3}` → `{-1: 0, 0: 2, 1: 2, 2: 3}` → `A1`, `A2b`; `    for owner in (definition, system):` → `    for owner in (system, definition):` → `A3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 139/139.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema changelog v2.15, schema doc header and sections, CLAUDE.md's backfill wording, decision entry `A SKILL HAS A RANK AND POINTS (TICKET-0106) -- SIX RANKS, A MODIFIER TABLE, THRESHOLDS AT THREE LEVELS (BRIEF-0106-a, schema v2.15)` — all in the diff.
