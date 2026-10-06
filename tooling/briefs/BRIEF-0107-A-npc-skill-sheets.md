<!-- slug: npc-skill-sheets -->
# BRIEF 0107-A — "v2.16: NPCs hold skill rows, their opposition reads them, the carrure becomes a row"

Lot: LOT-0107-npc-skills-masters.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0107-a, schema v2.16)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0107`, cut from `main` at `7b1ef23` or later, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.15"`; `world-engine-schema.md:3` -> `Current schema version: v2.15`; the changelog's newest entry is `- **v2.15**`.
- `src/world_engine/models/canon.py:177` -> `    physical_tier: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})`; `:681` -> `    skill_definition_id: Optional[str] = Field(` (in `Skill`).
- `src/world_engine/cockpit/play_physical.py:18` -> `from .. import llm_parse, ollama_client, skill_lexicon, skill_ranks`; `:184` -> `            # Defensive fallback: the PC somehow lacks the custom row.`; `:206` -> `            npc_tier = opposed_character.physical_tier if opposed_character is not None else 0`; `wc -l` -> 998.
- `src/world_engine/cockpit/crud/entities.py:139` -> the `physical_tier` registry field (« Physical tier (Carrure) »); `:406` -> `    link_to: list[str] = []`.
- `src/world_engine/cockpit/routes/npc_agent.py:214` -> `        ext_data["physical_tier"] = pub["physical_tier"]`.
- `src/world_engine/lore_selectors.py:101` -> `                physical_tier=character.physical_tier,`.
- `frontend/src/creation/generatePanel.svelte.js:60` -> `  setVal(legacyDoc, 'author-x-physical_tier', draft.public.physical_tier);`.
- `tooling/verify/checks/stream_session_readonly.py:122` -> `    ("scene_format", SRC / "world_engine" / "scene_format.py"),` (the last entry of `DECLARED_MODULES`).
- `tooling/verify/canon_write_policy.txt:27` -> `src/world_engine/writes/characters.py::write_skill_progress    skill`.
- `CLAUDE.md:307` -> `  custom \`skill\` rows are PC-only and MJ-narration-only this phase: no`; `wc -c` -> 37 647.
- No `src/world_engine/skill_access.py`, no `scripts/migrate_v2_16_*.py`, no `tooling/verify/checks/npc_skills.py`.

## Facts carried

### R-01 — NPCs have no skill rows [M]
Opened: `src/world_engine/models/canon.py:177` (`Character.physical_tier`,
server default 0), `:655-690` (`Skill`: `character_id` FK `entity`, no
character-type restriction); `src/world_engine/cockpit/routes/creator.py:
690-701` (only PC creation seeds rows).
Finding: the table can hold NPC rows; nothing writes one.
Consequence: no schema change for NPC rows; one writer (`write_skill_row`).

### R-03 — Play's row lookup and opposition [M]
Opened: `src/world_engine/cockpit/play_physical.py:62-150` (the arbiter is
handed the whole catalogue; `_judge_and_record_domain`), `:152-215`
(`_say_physical_resolve_verdict`: base row, else definition row, else
« Defensive fallback » to the base row `:184`; opposition from
`physical_tier` `:206`); `wc -l` → 998 of 1000.
Consequence: the lookup and the opposition move to `skill_access.py`
(reads only; the file falls to 966), which gains the lock in B.

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

### R-08 — dropping a column [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py` (the previous migration's
shape); SQLite's `ALTER TABLE DROP COLUMN` (3.35+; refused on a column in
an index, a CHECK or a foreign key — `physical_tier` is in none, E2); the
v2.15 DDL of `skill` and `skill_definition`, dumped from a database
created on `main` (embedded in `npc_skills.py`, `_V215_DDL`).
Consequence: two `ADD COLUMN`s and one `DROP COLUMN`, no rebuild; the
migration refuses a SQLite older than 3.35.

### R-10 — the checks the lot passes [M]
Opened: E3; `single_canon_write.py` and `canon_write_policy.txt`;
`page_contract.py` (« Ajouter une compétence » must appear once — the NPC
section is titled « Compétences à donner »); `creation_island.py`;
`effect_self_write.py`; `claude_md_contract.py` (CLAUDE.md 37 647 of 38
000 characters); `skill_progression.py` (TICKET-0106's A2 rebuilds the
skill tables from the current models, so it keeps passing).

## Contracts

### C-01 — the schema (v2.16)
Produced by: BRIEF-0107-A   Consumed by: B, C
`skill_definition.requires_master BOOLEAN NOT NULL DEFAULT 0`;
`skill.taught_by_id` nullable FK `entity`; `character.physical_tier` gone.
Migration: refuses below v2.15, on SQLite < 3.35, on a tier outside -1..2;
every NPC with a non-zero tier and no `physical` base row gets one at
`TIER_TO_RANK[tier]`; players ignored; column dropped.

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

## Context

Nia locked D1 and E1: an NPC holds only the skill rows she gives it, every base domain it lacks reads Initié, an opposing NPC rolls its row for the skill, else its base domain, and `physical_tier` gives way to a `physical` row. This brief adds the v2.16 columns the lock needs (read from B on), moves Play's row lookup and opposition into `skill_access.py` (which also frees `play_physical.py` from its 998-line edge), and routes every carrure — generated, staged or migrated — into a row.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `models/canon.py`, drops `Character.physical_tier`, adds `SkillDefinition.requires_master` and `Skill.taught_by_id` (C-01);
   - creates `src/world_engine/skill_access.py` (C-02 without the lock) and declares it in `stream_session_readonly.py`;
   - in `play_physical.py`, replaces the row lookup and the opposition with two `skill_access` calls (the file falls to 966 lines; `Skill` is no longer imported);
   - adds `writes.write_skill_row` (C-03), exported by `writes`, allow-listed in `canon_write_policy.txt`;
   - in `crud/entities.py`, retires the « Carrure » registry field and adds `EntityWriteBody.carrure`, turned into a `physical` row at the end of `_create_static_entity_core` (C-04); `npc_agent.py` passes it; the generator panel keeps it in `pendingDraftsState.carrure` (a note « Carrure proposée »), `Sheet.svelte` sends it on a new character; `NpcAgent.svelte`'s field is retitled;
   - removes `physical_tier` from the Lore dossier row (`lore_selectors.py`);
   - bumps the version to v2.16 (constant, schema doc header), documents the three columns, adds the v2.16 changelog entry;
   - creates `scripts/migrate_v2_16_npc_skills.py` (the v2.15 migration's shape: env guard, refusals, post-checks, `schema_meta` convergence; two `ADD COLUMN`s, the carrures through `write_skill_row`, one `DROP COLUMN`);
   - creates `tooling/verify/checks/npc_skills.py` with A1-A4;
   - rewrites one CLAUDE.md line (NPC rows, `skill_access`);
   - appends the decision entry above the `---` / `*Co-built…*` footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build`.
4. Commit message: `feat(skills): NPC skill sheets replace physical_tier, schema v2.16 (BRIEF-0107-a)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index ed10391..fee3857 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -303,9 +303,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   base-domain `skill` lookup MUST include `AND skill_definition_id IS NULL`.
   A custom skill resolves via its `skill_definition.base_domain` — never
   its own `domain` column — and that resolved `base_domain` is what every
-  base-domain-keyed downstream branch keys off. `skill_definition` and
-  custom `skill` rows are PC-only and MJ-narration-only this phase: no
-  NPC-side read (named deferral).
+  base-domain-keyed downstream branch keys off. An NPC holds only the rows it
+  was given; Play's roll reads both sides through `skill_access` (NPC: skill,
+  else base domain, else Initié) -- enforced by `npc_skills.py`.
 - **A `skill_definition` delete always succeeds** (no `ON DELETE RESTRICT`,
   no `change_history` snapshot): dependent PC `skill` rows then the
   definition, one transaction. The type-"Oui" modal is the sole safeguard —
diff --git a/frontend/src/creation/NpcAgent.svelte b/frontend/src/creation/NpcAgent.svelte
index ae09689..d44dd00 100644
--- a/frontend/src/creation/NpcAgent.svelte
+++ b/frontend/src/creation/NpcAgent.svelte
@@ -128,7 +128,7 @@
                   onchange={(e) => editField(row.id, 'name', e.currentTarget.value)}>
                 <input type="text" placeholder="description" style="flex:1; min-width:140px" value={fac.description || ''} disabled={rejected}
                   onchange={(e) => editField(row.id, 'description', e.currentTarget.value)}>
-                <input type="number" min="-1" max="2" title="physical_tier" style="width:52px" value={pub.physical_tier ?? ''} disabled={rejected}
+                <input type="number" min="-1" max="2" title="Carrure (devient la compétence Physique)" style="width:52px" value={pub.physical_tier ?? ''} disabled={rejected}
                   onchange={(e) => editField(row.id, 'physical_tier', Number(e.currentTarget.value))}>
                 <select disabled={rejected} onchange={(e) => editField(row.id, 'faction_id', e.currentTarget.value || null)}>
                   <option value="">(aucune)</option>
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 9b45918..686c10d 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -94,7 +94,7 @@
   import PricingEditor from './PricingEditor.svelte';
   import LedgerPanel from './LedgerPanel.svelte';
   import ItemsPanel from './ItemsPanel.svelte';
-  import { resetPendingDrafts, knowledgeForCreate, goalsForCreate } from './pendingDrafts.svelte.js';
+  import { resetPendingDrafts, knowledgeForCreate, goalsForCreate, carrureForCreate } from './pendingDrafts.svelte.js';
   import PendingKnowledgeEditor from './PendingKnowledgeEditor.svelte';
   import PendingGoalsEditor from './PendingGoalsEditor.svelte';
   import { resetGeneratePanel, applyGeneratedDraft } from './generatePanel.svelte.js';
@@ -589,6 +589,7 @@
         ...(isNewSave && mutationId ? { mutation_id: mutationId } : {}),
         ...(confirmPromotion ? { confirm_promotion: true } : {}),
         ...(isNewSave && type === 'location' ? { link_to: neighboursForCreate() } : {}),
+        ...(isNewSave && type === 'character' && carrureForCreate() ? { carrure: carrureForCreate() } : {}),
       });
       let detail = isNewSave
         ? await api('/api/entities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
diff --git a/frontend/src/creation/generatePanel.svelte.js b/frontend/src/creation/generatePanel.svelte.js
index 154316f..7540139 100644
--- a/frontend/src/creation/generatePanel.svelte.js
+++ b/frontend/src/creation/generatePanel.svelte.js
@@ -57,7 +57,6 @@ function applyFacets(draft) {
 function applyCharacterDraft(legacyDoc, result) {
   const draft = result.draft;
   setVal(legacyDoc, 'author-f-name', draft.public.name);
-  setVal(legacyDoc, 'author-x-physical_tier', draft.public.physical_tier);
   setVal(legacyDoc, 'author-x-faction_id', draft.public.faction_id || '');
   applyFacets(draft);
 
@@ -78,6 +77,8 @@ function applyCharacterDraft(legacyDoc, result) {
   const shorts = (goals && Array.isArray(goals.shorts)) ? goals.shorts : [];
   pendingDraftsState.knowledge = (draft.secret.knowledge || []).map((k) => ({ ...k }));
   pendingDraftsState.goals = { long: (goals && goals.long) || '', shorts: [shorts[0] || '', shorts[1] || ''] };
+  pendingDraftsState.carrure = draft.public.physical_tier ?? null;
+  if (draft.public.physical_tier) notes.push(`Carrure proposée : ${draft.public.physical_tier} (devient la compétence Physique)`);
 
   return notes;
 }
diff --git a/frontend/src/creation/pendingDrafts.svelte.js b/frontend/src/creation/pendingDrafts.svelte.js
index 32f093c..257181b 100644
--- a/frontend/src/creation/pendingDrafts.svelte.js
+++ b/frontend/src/creation/pendingDrafts.svelte.js
@@ -15,11 +15,19 @@
 export const pendingDraftsState = $state({
   knowledge: [],
   goals: { long: '', shorts: ['', ''] },
+  // TICKET-0107 (E1): the generator's carrure (-1..2), sent as the create
+  // body's `carrure`; the server makes it the NPC's physical skill row.
+  carrure: null,
 });
 
 export function resetPendingDrafts() {
   pendingDraftsState.knowledge = [];
   pendingDraftsState.goals = { long: '', shorts: ['', ''] };
+  pendingDraftsState.carrure = null;
+}
+
+export function carrureForCreate() {
+  return pendingDraftsState.carrure;
 }
 
 export function knowledgeForCreate() {
diff --git a/scripts/migrate_v2_16_npc_skills.py b/scripts/migrate_v2_16_npc_skills.py
new file mode 100644
index 0000000..710340d
--- /dev/null
+++ b/scripts/migrate_v2_16_npc_skills.py
@@ -0,0 +1,188 @@
+"""Migration v2.16 — NPC skill sheets and skills learned from a master
+(TICKET-0107, BRIEF-0107-A, decisions A2, C1, D1, E1).
+
+1. DDL. Adds `skill_definition.requires_master` (BOOLEAN NOT NULL DEFAULT 0:
+   no existing skill requires a master) and the nullable
+   `skill.taught_by_id` (FK `entity`; every existing row was seeded, taught
+   by nobody).
+2. Carrures (E1). Every NPC whose `character.physical_tier` is not 0, and
+   who holds no `physical` base row, receives one at
+   `skill_ranks.TIER_TO_RANK[physical_tier]` (the former tier's exact
+   modifier), through `writes.write_skill_row`. A player character's
+   `physical_tier` is ignored (counted): its roll always read its own rows.
+3. Drops `character.physical_tier` (`ALTER TABLE ... DROP COLUMN`, SQLite
+   3.35 or later; refused below, before any change).
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.15 (the migrations are sequential), and on a `physical_tier` outside
+-1..2 (nothing to map it to), before any change.
+
+Idempotent: each column is added only when missing; step 2 and 3 run only
+while `character.physical_tier` exists.
+
+Post-checks, before `schema_meta` converges: both new columns exist,
+`character.physical_tier` is gone, every converted NPC holds its `physical`
+row at the mapped rank, and `PRAGMA foreign_key_check` is empty.
+
+Run from the project root:
+
+    python scripts/migrate_v2_16_npc_skills.py
+"""
+
+from __future__ import annotations
+
+import os
+import sqlite3
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
+        "migrate_v2_16_npc_skills.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlmodel import Session, select  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import Skill  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+from world_engine.skill_ranks import TIER_TO_RANK  # noqa: E402
+from world_engine.writes import write_skill_row  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.15"
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _columns(table: str) -> set[str]:
+    return {c["name"] for c in inspect(engine).get_columns(table)}
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.16 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+    if sqlite3.sqlite_version_info < (3, 35, 0):
+        raise SystemExit(f"Migration v2.16 refused: SQLite {sqlite3.sqlite_version} cannot drop a column (3.35+).")
+    if "physical_tier" in _columns("character"):
+        allowed = ", ".join(str(t) for t in sorted(TIER_TO_RANK))
+        with engine.connect() as conn:
+            bad = conn.execute(text(f"SELECT id, physical_tier FROM character WHERE physical_tier NOT IN ({allowed})")).fetchall()
+        if bad:
+            raise SystemExit(f"Migration v2.16 refused: physical_tier outside -1..2: {bad}.")
+
+
+def _add_columns() -> list[str]:
+    applied: list[str] = []
+    with engine.begin() as conn:
+        if "requires_master" not in _columns("skill_definition"):
+            conn.execute(text("ALTER TABLE skill_definition ADD COLUMN requires_master BOOLEAN NOT NULL DEFAULT 0"))
+            applied.append("skill_definition.requires_master")
+        if "taught_by_id" not in _columns("skill"):
+            conn.execute(text("ALTER TABLE skill ADD COLUMN taught_by_id VARCHAR REFERENCES entity (id)"))
+            applied.append("skill.taught_by_id")
+    return applied
+
+
+def _convert_carrures() -> dict[str, int]:
+    """{npc_id: rank} written; prints the players' non-zero tiers it ignores."""
+    with engine.connect() as conn:
+        tiers = conn.execute(text(
+            "SELECT id, character_type, physical_tier FROM character WHERE physical_tier <> 0"
+        )).fetchall()
+    converted: dict[str, int] = {}
+    with Session(engine) as session:
+        for character_id, character_type, tier in tiers:
+            if character_type != "npc":
+                print(f"  player {character_id}: physical_tier {tier} ignored (its own rows are rolled).")
+                continue
+            held = session.exec(select(Skill).where(
+                Skill.character_id == character_id, Skill.domain == "physical",
+                Skill.skill_definition_id.is_(None))).first()
+            if held is not None:
+                continue
+            write_skill_row(session, character_id=character_id, domain="physical", rank=TIER_TO_RANK[tier])
+            converted[character_id] = TIER_TO_RANK[tier]
+        session.commit()
+    return converted
+
+
+def _drop_physical_tier() -> None:
+    with engine.begin() as conn:
+        conn.execute(text("ALTER TABLE character DROP COLUMN physical_tier"))
+
+
+def _post_checks(converted: dict[str, int]) -> None:
+    if "requires_master" not in _columns("skill_definition") or "taught_by_id" not in _columns("skill"):
+        raise SystemExit("Migration v2.16 aborted, post-check failed: a new column is missing.")
+    if "physical_tier" in _columns("character"):
+        raise SystemExit("Migration v2.16 aborted, post-check failed: character.physical_tier still exists.")
+    with Session(engine) as session:
+        for npc_id, rank in converted.items():
+            row = session.exec(select(Skill).where(
+                Skill.character_id == npc_id, Skill.domain == "physical",
+                Skill.skill_definition_id.is_(None))).first()
+            if row is None or row.rank != rank:
+                raise SystemExit(f"Migration v2.16 aborted, post-check failed: NPC {npc_id} physical row {row}.")
+    with engine.connect() as conn:
+        dangling = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+    if dangling:
+        raise SystemExit(f"Migration v2.16 aborted, post-check failed: foreign_key_check {dangling}.")
+    print(f"Post-check: columns in place; physical_tier dropped; {len(converted)} carrure(s) converted.")
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
+    print("Migration v2.16 — NPC skill sheets, requires_master, taught_by_id, physical_tier dropped")
+    _refuse()
+    applied = _add_columns()
+    print("Applied: " + ", ".join(applied) + "." if applied else "Columns already present.")
+    converted: dict[str, int] = {}
+    if "physical_tier" in _columns("character"):
+        converted = _convert_carrures()
+        _drop_physical_tier()
+        print(f"Carrures converted: {len(converted)}. character.physical_tier dropped.")
+    else:
+        print("character.physical_tier already dropped — no conversion.")
+    _post_checks(converted)
+    _converge_schema_meta()
+    print("\nMigration v2.16 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index 534ec33..a4459b4 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -61,6 +61,7 @@ from ...tick_normalize import _EVENT_TYPES
 from ...traits import checkable_traits, ext_columns_for, form_fields_for
 from ...writes.schema import create_entity_type
 from ...zone_rules import ZoneRefusal, require_visitable
+from ...skill_ranks import DEFAULT_RANK, TIER_TO_RANK
 from ...writes import (
     KNOWLEDGE_LEVELS,
     NPC_GOAL_HORIZONS,
@@ -79,6 +80,7 @@ from ...writes import (
     write_knowledge,
     write_ledger_entry,
     write_membership,
+    write_skill_row,
     write_npc_goal,
     write_npc_goal_prerequisites,
     write_npc_goal_status,
@@ -136,7 +138,6 @@ ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
                 "name": "vital_status", "label": "Vital status", "kind": "select",
                 "options": ["alive", "dead", "missing", "unknown"], "default": "alive",
             },
-            {"name": "physical_tier", "label": "Physical tier (Carrure)", "kind": "number", "min": -1, "max": 2, "default": 0},
         ],
     },
     "location": {
@@ -404,6 +405,10 @@ class EntityWriteBody(BaseModel):
     # TICKET-0101 (K): on a location create, the parent's neighbours the
     # creator ticked; each is linked with its derived type.
     link_to: list[str] = []
+    # TICKET-0107 (E1): a generator's carrure (-1..2, clamped), on a
+    # character create only; it becomes the `physical` skill row
+    # (`skill_ranks.TIER_TO_RANK`), none at 0.
+    carrure: Optional[int] = None
 
 
 class NpcPricesBody(BaseModel):
@@ -667,6 +672,10 @@ def _create_static_entity_core(body: EntityWriteBody, db: DbSession, entity_type
             is_primary=True,
             is_secret=False,
         )
+    if entity_type == "character" and body.carrure:
+        rank = TIER_TO_RANK[max(-1, min(2, body.carrure))]
+        if rank != DEFAULT_RANK:
+            write_skill_row(db, character_id=entity.id, domain="physical", rank=rank)
 
     return entity
 
diff --git a/src/world_engine/cockpit/play_physical.py b/src/world_engine/cockpit/play_physical.py
index 5c61036..12e927d 100644
--- a/src/world_engine/cockpit/play_physical.py
+++ b/src/world_engine/cockpit/play_physical.py
@@ -15,7 +15,7 @@ from typing import Any, Iterator, Optional
 from fastapi import HTTPException
 from sqlmodel import Session, select
 
-from .. import llm_parse, ollama_client, skill_lexicon, skill_ranks
+from .. import llm_parse, ollama_client, skill_access, skill_lexicon, skill_ranks
 from ..context import (
     assemble_mj_context,
     assemble_npc_context,
@@ -34,7 +34,6 @@ from ..models import (
     Gathering,
     Location,
     PromptTemplate,
-    Skill,
     SkillDefinition,
     Visit,
 )
@@ -158,41 +157,11 @@ def _say_physical_resolve_verdict(
     the dice verdict. Returns (resolved_base_domain, verdict, opposed_entity,
     verdict_sse_line)."""
     db = ctx.db
-    # BRIEF-55 (5d, schema v1.63): resolution mapping. `domain` may now
-    # be a base domain OR a custom skill name (constraint-gated turns
-    # above only ever set a base domain, so they fall in the first
-    # branch). `resolved_base_domain` is what bands/discovery key off.
-    custom_def = world_skill_defs_by_name.get(domain)
-    if custom_def is None:
-        resolved_base_domain = domain
-        skill_row = db.exec(
-            select(Skill).where(
-                Skill.character_id == ctx.conv.player_id,
-                Skill.domain == domain,
-                Skill.skill_definition_id.is_(None),
-            )
-        ).first()
-    else:
-        resolved_base_domain = custom_def.base_domain
-        skill_row = db.exec(
-            select(Skill).where(
-                Skill.character_id == ctx.conv.player_id,
-                Skill.skill_definition_id == custom_def.id,
-            )
-        ).first()
-        if skill_row is None:
-            # Defensive fallback: the PC somehow lacks the custom row.
-            skill_row = db.exec(
-                select(Skill).where(
-                    Skill.character_id == ctx.conv.player_id,
-                    Skill.domain == resolved_base_domain,
-                    Skill.skill_definition_id.is_(None),
-                )
-            ).first()
-
-    # Player-roll rule (resolution.py): the roll always belongs to the
-    # player — player_tier is its skill row's rank modifier (TICKET-0106),
-    # npc_tier (if opposed) character.physical_tier, default 0 either way.
+    # BRIEF-55 (5d): `domain` is a base domain OR a custom skill name;
+    # `skill_access` (TICKET-0107) picks the player's row and the opposing
+    # NPC's modifier (D1). `resolved_base_domain` is what bands/discovery key off.
+    rolled = skill_access.player_skill(db, ctx.conv.player_id, domain, world_skill_defs_by_name)
+    resolved_base_domain, skill_row = rolled.base_domain, rolled.row
     player_tier = skill_ranks.rank_modifier(skill_row.rank) if skill_row else 0
 
     opposed_entity: Optional[Entity] = None
@@ -202,8 +171,7 @@ def _say_physical_resolve_verdict(
     if opposed_npc_id:
         opposed_entity = db.get(Entity, opposed_npc_id)
         if opposed_entity is not None:
-            opposed_character = db.get(Character, opposed_npc_id)
-            npc_tier = opposed_character.physical_tier if opposed_character is not None else 0
+            npc_tier = skill_access.opposition_modifier(db, opposed_npc_id, resolved_base_domain, rolled.definition)
 
     verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
     _log.info(
diff --git a/src/world_engine/cockpit/routes/npc_agent.py b/src/world_engine/cockpit/routes/npc_agent.py
index a47095e..206b790 100644
--- a/src/world_engine/cockpit/routes/npc_agent.py
+++ b/src/world_engine/cockpit/routes/npc_agent.py
@@ -210,13 +210,13 @@ def _commit_npc_row(row: NpcBatchRow, batch: NpcBatch, db: Session) -> dict:
         "character_type": "npc",
         "current_location_id": row.payload["location_id"],
     }
-    if pub.get("physical_tier") is not None:
-        ext_data["physical_tier"] = pub["physical_tier"]
     faction_id = pub.get("faction_id")
     if faction_id is not None:
         ext_data["faction_id"] = faction_id
 
-    npc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data, facets=draft["facets"])
+    # The draft's carrure becomes the NPC's physical skill row (TICKET-0107, E1).
+    npc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data, facets=draft["facets"],
+                                     carrure=pub.get("physical_tier"))
     npc_entity = _crud._create_entity_core(npc_body, db)
 
     for k in (sec.get("knowledge") or []):
diff --git a/src/world_engine/lore_selectors.py b/src/world_engine/lore_selectors.py
index 990563d..1557e07 100644
--- a/src/world_engine/lore_selectors.py
+++ b/src/world_engine/lore_selectors.py
@@ -98,7 +98,6 @@ def _identity_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
                 character_type=character.character_type,
                 current_location_id=character.current_location_id,
                 vital_status=character.vital_status,
-                physical_tier=character.physical_tier,
             )
     return [row]
 
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index 5acd0fd..9d14ce1 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -170,11 +170,8 @@ class Character(SQLModel, table=True):
     )
     # appearance/backstory/aversion/secrets moved to facts (TICKET-0091,
     # schema v2.06): physique, histoire, aversion, creator_meta histoire.
-    # Schema v1.77, TICKET-0025, BRIEF-0025-a: physical resistance tier for
-    # opposed rolls (resolution.py). Migrated from entity.metadata
-    # ['physical_tier'] — UI-visible data is never stored in JSON
-    # (json_ui_boundary). 0 = untrained default.
-    physical_tier: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+    # `physical_tier` (v1.77) became the NPC's `physical` skill row at v2.16
+    # (TICKET-0107): an NPC's opposition reads its skill rows.
 
 
 # -----------------------------------------------------------------------------
@@ -647,12 +644,16 @@ class SkillDefinition(SQLModel, table=True):
     points_to_rank_3: Optional[int] = None
     points_to_rank_4: Optional[int] = None
     points_to_rank_5: Optional[int] = None
+    # Learned only from a master (v2.16, TICKET-0107, A2): a player
+    # character holds no row for it until taught, and cannot roll it.
+    requires_master: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
     created_at: datetime = _created_ts()
     updated_at: datetime = _created_ts()
 
 
 # -----------------------------------------------------------------------------
-# skill  (player character skill sheet — physical/sensory domains, schema v1.22;
+# skill  (a character's skill sheet — physical/sensory domains, schema v1.22;
+# NPC rows too since v2.16, TICKET-0107;
 # skill_definition_id added schema v1.63; `rank` and `xp` replace `tier` at
 # v2.15, TICKET-0106 — the dice modifier is `skill_ranks.rank_modifier(rank)`)
 # -----------------------------------------------------------------------------
@@ -685,6 +686,10 @@ class Skill(SQLModel, table=True):
             nullable=True,
         ),
     )
+    # Who taught this skill (v2.16, TICKET-0107, C1): a character at Maître in
+    # it when the row was learned; NULL for a row seeded or granted without
+    # a master.
+    taught_by_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     created_at: datetime = _created_ts()
     updated_at: datetime = _created_ts()
 
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index aa94ef5..db940d3 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.15"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.16"
diff --git a/src/world_engine/skill_access.py b/src/world_engine/skill_access.py
new file mode 100644
index 0000000..4fb70b9
--- /dev/null
+++ b/src/world_engine/skill_access.py
@@ -0,0 +1,68 @@
+"""Which skill row a roll reads, for the player and for the NPC opposing him
+(TICKET-0107, BRIEF-0107-A, decision D1).
+
+Reads only: this module never writes.
+
+The player's row: the arbiter named a base domain or a skill definition of
+the world. A base domain reads the player's base row for it
+(`skill_definition_id IS NULL`, CLAUDE.md « Custom skill lookups »). A
+definition reads the player's row for it; when the player has none, the
+roll falls back to his base row for the definition's domain.
+
+The opposing NPC's modifier (D1): its row for the same definition, else its
+base row for the roll's base domain, else the rank every character holds in
+a base domain by default -- `skill_ranks.DEFAULT_RANK` (Initié, +0): every
+character has the four base domains, an NPC just has no row for one it was
+never given. The modifier is always `skill_ranks.rank_modifier(rank)`.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .models import Skill, SkillDefinition
+from .skill_ranks import DEFAULT_RANK, rank_modifier
+
+
+@dataclass(frozen=True)
+class RolledSkill:
+    base_domain: str  # what bands, discovery and the dice key off
+    row: Optional[Skill]  # the player's row rolled; None when he has none at all
+    definition: Optional[SkillDefinition]  # set when the arbiter named a definition
+
+
+def _base_row(db: Session, character_id: str, domain: str) -> Optional[Skill]:
+    return db.exec(
+        select(Skill).where(
+            Skill.character_id == character_id,
+            Skill.domain == domain,
+            Skill.skill_definition_id.is_(None),
+        )
+    ).first()
+
+
+def _definition_row(db: Session, character_id: str, definition_id: str) -> Optional[Skill]:
+    return db.exec(
+        select(Skill).where(Skill.character_id == character_id, Skill.skill_definition_id == definition_id)
+    ).first()
+
+
+def player_skill(db: Session, player_id: str, token: str, definitions_by_name: dict) -> RolledSkill:
+    """The row the player rolls for `token` (a base domain, or a definition
+    name of `definitions_by_name`)."""
+    definition = definitions_by_name.get(token)
+    if definition is None:
+        return RolledSkill(base_domain=token, row=_base_row(db, player_id, token), definition=None)
+    row = _definition_row(db, player_id, definition.id) or _base_row(db, player_id, definition.base_domain)
+    return RolledSkill(base_domain=definition.base_domain, row=row, definition=definition)
+
+
+def opposition_modifier(db: Session, npc_id: str, base_domain: str, definition: Optional[SkillDefinition]) -> int:
+    """D1: the opposing NPC's modifier for this roll."""
+    row = _definition_row(db, npc_id, definition.id) if definition is not None else None
+    if row is None:
+        row = _base_row(db, npc_id, base_domain)
+    return rank_modifier(row.rank if row is not None else DEFAULT_RANK)
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index e87eccc..fd0b054 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -52,6 +52,7 @@ from __future__ import annotations
 from ._shared import _append_history_snapshot, _clamp
 from .characters import (
     SkillProgress, write_character_location, write_ledger_entry, write_skill_progress, write_skill_rank,
+    write_skill_row,
 )
 from .config import (
     upsert_conversation_window_config,
@@ -153,6 +154,7 @@ __all__ = [
     "attach_participants",
     "write_skill_rank",
     "write_skill_progress",
+    "write_skill_row",
     "SkillProgress",
     "write_ledger_entry",
     "write_membership",
diff --git a/src/world_engine/writes/characters.py b/src/world_engine/writes/characters.py
index a78604a..4ca9e6f 100644
--- a/src/world_engine/writes/characters.py
+++ b/src/world_engine/writes/characters.py
@@ -9,6 +9,10 @@ none of these three functions were baselined.
   (history is sacred on this path too) and restarting its points at 0
   (U2). The sole write shape for a creator's rank edit (TICKET-0106,
   BRIEF-0106-A; formerly `write_skill_tier`).
+- `write_skill_row(...)`                : create one `skill` row for a
+  character -- an NPC's skill, a carrure, a skill learned (TICKET-0107,
+  BRIEF-0107-A). The sole creator of a row outside the PC seed and the
+  catalogue backfill.
 - `write_skill_progress(...)`           : add points to a `skill` row and
   move its rank when a threshold is crossed (TICKET-0106, BRIEF-0106-B).
   The sole write shape for points; called by the `skill_progress` applier
@@ -27,9 +31,9 @@ from datetime import UTC, datetime
 from typing import Optional
 
 from sqlalchemy.orm import attributes as sa_attrs
-from sqlmodel import Session
+from sqlmodel import Session, select
 
-from ..models import Character, Ledger, Skill
+from ..models import BASE_SKILL_DOMAINS, Character, Ledger, Skill, SkillDefinition
 from ..skill_ranks import MAX_RANK, RANKS, skill_points_to_next
 
 
@@ -98,6 +102,46 @@ def write_skill_rank(
     return skill
 
 
+def write_skill_row(
+    db: Session,
+    *,
+    character_id: str,
+    rank: int,
+    domain: Optional[str] = None,
+    skill_definition_id: Optional[str] = None,
+    taught_by_id: Optional[str] = None,
+) -> Skill:
+    """Create one `skill` row: a base domain (`domain`, no definition) or a
+    skill definition (`skill_definition_id`; the row's `domain` is the
+    definition's base domain, never the caller's). Caller adds nothing and
+    commits. `ValueError` before any write on a rank outside `RANKS`, both
+    or neither of `domain`/`skill_definition_id`, an unknown definition, a
+    base domain outside `BASE_SKILL_DOMAINS`, or a row the character already
+    holds for that skill (one row per character and skill)."""
+    if rank not in RANKS:
+        raise ValueError(f"write_skill_row: rank {rank!r} is not one of {RANKS}")
+    if (domain is None) == (skill_definition_id is None):
+        raise ValueError("write_skill_row: exactly one of domain and skill_definition_id")
+    if skill_definition_id is not None:
+        definition = db.get(SkillDefinition, skill_definition_id)
+        if definition is None:
+            raise ValueError(f"write_skill_row: skill definition {skill_definition_id!r} not found")
+        domain = definition.base_domain
+        clash = select(Skill).where(Skill.character_id == character_id,
+                                    Skill.skill_definition_id == skill_definition_id)
+    else:
+        if domain not in BASE_SKILL_DOMAINS:
+            raise ValueError(f"write_skill_row: {domain!r} is not a base domain")
+        clash = select(Skill).where(Skill.character_id == character_id, Skill.domain == domain,
+                                    Skill.skill_definition_id.is_(None))
+    if db.exec(clash).first() is not None:
+        raise ValueError("write_skill_row: the character already holds this skill")
+    row = Skill(character_id=character_id, domain=domain, rank=rank,
+                skill_definition_id=skill_definition_id, taught_by_id=taught_by_id)
+    db.add(row)
+    return row
+
+
 @dataclass(frozen=True)
 class SkillProgress:
     rank_before: int
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 3e52fbc..c735e76 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17971,6 +17971,31 @@ an `agenda_step_change` whose step has a `domain` -- with that mutation's
 status: proposed, the point waits for the approval; applied, it is earned.
 The former « pas encore de gain de compétence » note is retired.
 
+
+## AN NPC HAS A SKILL SHEET (TICKET-0107) -- ITS ROWS OPPOSE THE ROLL, THE CARRURE BECOMES A ROW (BRIEF-0107-a, schema v2.16)
+
+**D1.** An NPC holds only the skill rows the creator gives it; every
+character has the four base domains, so a base domain an NPC holds no row
+for reads Initié (+0). An opposing NPC's modifier is its row for the skill
+rolled, else its base row for that skill's domain, else Initié
+(`skill_access.opposition_modifier`). `skill_access` also picks the
+player's row; both moved out of `play_physical.py` and joined
+`stream_session_readonly.py`'s declared set (reads only).
+
+**E1.** `character.physical_tier` is gone. A generator's carrure (-1..2,
+the prompt unchanged) becomes, at creation, the NPC's `physical` row through
+`skill_ranks.TIER_TO_RANK` -- none when it maps to Initié; the migration
+does the same for every NPC's non-zero tier and drops the column. A
+player's tier is ignored: its roll always read its own rows. The fiche's
+« Carrure » field is retired.
+
+**Schema for the lock (BRIEF-0107-b).** `skill_definition.requires_master`
+and `skill.taught_by_id` are added here, read from the next brief on.
+
+**Rejected.** Four seeded base rows per NPC on every creation path: the
+same reading as an absent row, through many more writes. Keeping
+`physical_tier` beside the rows: two sources for one modifier.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index d8a8e21..3ec1723 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -25,6 +25,8 @@ src/world_engine/writes/factions.py::write_membership          faction_membershi
 src/world_engine/writes/characters.py::write_skill_rank        skill
 # TICKET-0106, BRIEF-0106-B: write_skill_progress adds a roll's points to a skill row and moves its rank at a threshold; called only from inside _apply_mutation (the skill_progress applier and the agenda_step_change applier).
 src/world_engine/writes/characters.py::write_skill_progress    skill
+# TICKET-0107, BRIEF-0107-A: write_skill_row creates one skill row for a character -- an NPC's skill, a carrure at creation, a skill learned -- refusing a second row for the same character and skill.
+src/world_engine/writes/characters.py::write_skill_row         skill
 src/world_engine/writes/goals_agendas.py::write_npc_goal       npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_status npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_prerequisites npc_goal
diff --git a/tooling/verify/checks/npc_skills.py b/tooling/verify/checks/npc_skills.py
new file mode 100644
index 0000000..1007ac3
--- /dev/null
+++ b/tooling/verify/checks/npc_skills.py
@@ -0,0 +1,361 @@
+"""G1 check for TICKET-0107 -- NPC skill sheets, and skills learned from a
+master.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`skill_progression.py` precedent, TICKET-0106). Each brief adds its rules
+here in the same commit.
+
+A1 -- schema (BRIEF-0107-A, v2.16). `skill_definition.requires_master` is a
+   NOT NULL boolean defaulting to 0; `skill.taught_by_id` is a nullable
+   foreign key to `entity`; `character` has no `physical_tier`; the
+   `character` registry fields (`ENTITY_TYPE_REGISTRY`) name no
+   `physical_tier`.
+A2 -- migration `scripts/migrate_v2_16_npc_skills.py`, on a v2.15-shaped
+   database (`character.physical_tier` present, `skill_definition` and
+   `skill` in their v2.15 DDL, verbatim below), holding NPCs at tiers -1, 0
+   and 2, an NPC at tier 2 that already holds a `physical` row at rank 4, a
+   player at tier 1, and a definition:
+   a. at v2.14 it refuses (non-zero exit) and changes nothing; with a tier
+      of 5 it refuses and changes nothing;
+   b. at v2.15 it gives the tier -1 NPC a `physical` row at rank 0 and the
+      tier 2 NPC one at rank 3; the tier 0 NPC and the player get none; the
+      NPC that held a row keeps it at rank 4, alone; `physical_tier` is
+      gone, both new columns exist (the definition's `requires_master` 0),
+      the three tables have the models' columns, `PRAGMA
+      foreign_key_check` is empty and `schema_meta` is the code's version;
+   c. a second run exits zero and changes no row.
+A3 -- the rows a roll reads (fixture, D1). For the player:
+   `skill_access.player_skill` on a base domain reads the base row; on a
+   definition the player holds, that row; on a definition he lacks, his base
+   row for its domain. For an opposing NPC: `opposition_modifier` reads its
+   row for the definition (rank 5: +3), else its base row for the domain
+   (rank 3: +2), else 0.
+A4 -- the carrure at creation (fixture and static). Creating a character
+   with `carrure` 2 writes its `physical` row at rank 3, with 0 or none
+   writes no row, with 9 clamps to rank 3; `write_skill_row` refuses a
+   second row for the same skill, both or neither of domain/definition, and
+   rank 6, each before any write. No `.physical_tier` attribute under `src/`
+   (AST); `npc_agent.py` passes `carrure=`; `play_physical.py` calls
+   `skill_access.opposition_modifier(` and `skill_access.player_skill(`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that examines zero rows is a
+FAILURE.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_16_npc_skills.py"
+
+FAILURES: list[str] = []
+
+# The two tables as v2.15 created them (dumped from `main` at 7b1ef23).
+_V215_DDL = (
+    """CREATE TABLE skill_definition (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
+	base_domain VARCHAR NOT NULL, system_id VARCHAR, description VARCHAR,
+	points_to_rank_1 INTEGER, points_to_rank_2 INTEGER, points_to_rank_3 INTEGER,
+	points_to_rank_4 INTEGER, points_to_rank_5 INTEGER,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
+	CONSTRAINT ck_skill_definition_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT)""",
+    "CREATE INDEX idx_skill_definition_world ON skill_definition (world_id)",
+    "CREATE INDEX idx_skill_definition_system ON skill_definition (system_id)",
+    "CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name)",
+    """CREATE TABLE skill (
+	id VARCHAR NOT NULL, character_id VARCHAR NOT NULL, domain VARCHAR NOT NULL,
+	rank INTEGER DEFAULT 1 NOT NULL, xp INTEGER DEFAULT 0 NOT NULL,
+	change_history JSON DEFAULT '[]' NOT NULL, skill_definition_id VARCHAR,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_skill_rank CHECK (rank BETWEEN 0 AND 5),
+	CONSTRAINT ck_skill_xp CHECK (xp >= 0),
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
+# --- A1 ------------------------------------------------------------------------
+
+def check_a1() -> None:
+    from world_engine.cockpit.crud.entities import ENTITY_TYPE_REGISTRY
+    from world_engine.models import Character, Skill, SkillDefinition
+
+    flag = SkillDefinition.__table__.columns.get("requires_master")
+    if flag is None or flag.nullable or str(flag.server_default.arg) != "0":
+        fail(f"A1: skill_definition.requires_master is {flag!r}")
+    teacher = Skill.__table__.columns.get("taught_by_id")
+    if teacher is None or not teacher.nullable or [fk.target_fullname for fk in teacher.foreign_keys] != ["entity.id"]:
+        fail(f"A1: skill.taught_by_id is {teacher!r}")
+    if "physical_tier" in Character.__table__.columns:
+        fail("A1: character still declares physical_tier")
+    names = [f["name"] for f in ENTITY_TYPE_REGISTRY["character"]["fields"]]
+    if not names or "physical_tier" in names:
+        fail(f"A1: the character registry fields are {names}")
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
+    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))
+
+
+def _seed_v215(db_path: str) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import Character, Entity, SchemaMeta, World
+
+    create_db_and_tables()
+    ids: dict = {}
+    with Session(engine) as session:
+        world = World(name="NPC skills A2", is_active=True)
+        session.add(world)
+        session.flush()
+        ids["world"] = world.id
+        for key, kind in (("m1", "npc"), ("z", "npc"), ("p2", "npc"), ("held", "npc"), ("pc", "player")):
+            row = Entity(world_id=world.id, type="character", name=key)
+            session.add(row)
+            session.flush()
+            session.add(Character(id=row.id, world_id=world.id, character_type=kind))
+            ids[key] = row.id
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.15"))
+        session.commit()
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        ids["model_shapes"] = {t: _shape(conn, t) for t in ("skill", "skill_definition", "character")}
+        conn.execute("PRAGMA foreign_keys=OFF")
+        conn.execute("DROP TABLE skill")
+        conn.execute("DROP TABLE skill_definition")
+        for statement in _V215_DDL:
+            conn.execute(statement)
+        conn.execute("ALTER TABLE character ADD COLUMN physical_tier INTEGER DEFAULT 0 NOT NULL")
+        for key, tier in (("m1", -1), ("z", 0), ("p2", 2), ("held", 2), ("pc", 1)):
+            conn.execute("UPDATE character SET physical_tier = ? WHERE id = ?", (tier, ids[key]))
+        conn.execute("INSERT INTO skill_definition (id, world_id, name, base_domain) VALUES ('def', ?, 'Feu', 'composure')",
+                     (ids["world"],))
+        conn.execute("INSERT INTO skill (id, character_id, domain, rank) VALUES ('held-phys', ?, 'physical', 4)",
+                     (ids["held"],))
+    return ids
+
+
+def _set(db_path: str, sql: str, params: tuple = ()) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute(sql, params)
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "shapes": {t: _shape(conn, t) for t in ("skill", "skill_definition", "character")},
+            "skills": sorted(conn.execute("SELECT character_id, domain, rank, skill_definition_id FROM skill").fetchall()),
+            "definitions": conn.execute("SELECT * FROM skill_definition").fetchall(),
+            "fk": conn.execute("PRAGMA foreign_key_check").fetchall(),
+        }
+
+
+def check_a2(db_path: str) -> None:
+    ids = _seed_v215(db_path)
+    _set(db_path, "UPDATE schema_meta SET static_version = 'v2.14' WHERE id = 1")
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail(f"A2a: v2.14 was not refused, or changed rows (exit {result.returncode})")
+    _set(db_path, "UPDATE schema_meta SET static_version = 'v2.15' WHERE id = 1")
+    _set(db_path, "UPDATE character SET physical_tier = 5 WHERE id = ?", (ids["z"],))
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail(f"A2a: a tier of 5 was not refused, or changed rows (exit {result.returncode})")
+    _set(db_path, "UPDATE character SET physical_tier = 0 WHERE id = ?", (ids["z"],))
+    result = _run_migration(db_path)
+    after = _state(db_path)
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: {result.stderr.strip()[-400:]}")
+        return
+    want = sorted([(ids["m1"], "physical", 0, None), (ids["p2"], "physical", 3, None),
+                   (ids["held"], "physical", 4, None)])
+    if after["skills"] != want:
+        fail(f"A2b: skill rows are {after['skills']}, want {want}")
+    if after["shapes"] != ids["model_shapes"]:
+        fail(f"A2b: shapes {after['shapes']} differ from the models {ids['model_shapes']}")
+    with sqlite3.connect(db_path) as conn:
+        flag = conn.execute("SELECT requires_master FROM skill_definition WHERE id = 'def'").fetchone()
+    if flag != (0,) or after["fk"]:
+        fail(f"A2b: requires_master {flag}, foreign_key_check {after['fk']}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or _state(db_path) != after:
+        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")
+
+
+# --- A3-A4 ---------------------------------------------------------------------
+
+def _a_world(session) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Character, Entity, Skill, SkillDefinition, World
+
+    for world in session.exec(select(World)).all():
+        world.is_active = False
+        session.add(world)
+    world = World(name="NPC skills A3", is_active=True)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind in (("pc", "player"), ("master", "npc"), ("brute", "npc"), ("plain", "npc")):
+        row = Entity(world_id=world.id, type="character", name=key)
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
+        ids[key] = row.id
+    for key, domain in (("escrime", "physical"), ("feu", "composure")):
+        d = SkillDefinition(world_id=world.id, name=key, base_domain=domain)
+        session.add(d)
+        session.flush()
+        ids[key] = d
+    rows = {
+        "pc_phys": Skill(character_id=ids["pc"], domain="physical", rank=2),
+        "pc_comp": Skill(character_id=ids["pc"], domain="composure", rank=0),
+        "pc_escrime": Skill(character_id=ids["pc"], domain="physical", rank=4, skill_definition_id=ids["escrime"].id),
+        "master_escrime": Skill(character_id=ids["master"], domain="physical", rank=5,
+                                skill_definition_id=ids["escrime"].id),
+        "brute_phys": Skill(character_id=ids["brute"], domain="physical", rank=3),
+    }
+    for row in rows.values():
+        session.add(row)
+    session.commit()
+    ids.update({k: r.id for k, r in rows.items()})
+    session.exec(select(World))  # keep the session usable
+    return ids
+
+
+def check_a3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.skill_access import opposition_modifier, player_skill
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+        defs = {"escrime": ids["escrime"], "feu": ids["feu"]}
+        cases = (("physical", ids["pc_phys"], "physical"), ("escrime", ids["pc_escrime"], "physical"),
+                 ("feu", ids["pc_comp"], "composure"))
+        for token, row_id, base in cases:
+            got = player_skill(session, ids["pc"], token, defs)
+            if (got.row.id if got.row else None, got.base_domain) != (row_id, base):
+                fail(f"A3: player_skill({token!r}) read {got.row.id if got.row else None}/{got.base_domain}")
+        modifiers = (("master", "physical", ids["escrime"], 3), ("brute", "physical", ids["escrime"], 2),
+                     ("plain", "physical", ids["escrime"], 0), ("brute", "physical", None, 2),
+                     ("master", "physical", None, 0))
+        for npc, base, definition, want in modifiers:
+            got = opposition_modifier(session, ids[npc], base, definition)
+            if got != want:
+                fail(f"A3: opposition_modifier({npc}, {base}, {definition.name if definition else None}) = {got}, want {want}")
+
+
+def check_a4(engine) -> None:
+    import ast
+
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.crud.entities import EntityWriteBody, _create_entity_core
+    from world_engine.models import Skill
+    from world_engine.writes import write_skill_row
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+        for name, carrure, want in (("c2", 2, [3]), ("c0", 0, []), ("cnone", None, []), ("c9", 9, [3])):
+            body = EntityWriteBody(entity={"name": name, "type": "character"},
+                                   extension={"character_type": "npc"}, carrure=carrure)
+            entity = _create_entity_core(body, session)
+            session.commit()
+            ranks = [r.rank for r in session.exec(select(Skill).where(Skill.character_id == entity.id)).all()]
+            if ranks != want:
+                fail(f"A4: carrure {carrure} wrote ranks {ranks}, want {want}")
+        bad_calls = (
+            dict(character_id=ids["brute"], domain="physical", rank=1),
+            dict(character_id=ids["master"], skill_definition_id=ids["escrime"].id, rank=1),
+            dict(character_id=ids["plain"], rank=1),
+            dict(character_id=ids["plain"], domain="physical", skill_definition_id=ids["feu"].id, rank=1),
+            dict(character_id=ids["plain"], domain="physical", rank=6),
+        )
+        for kwargs in bad_calls:
+            count = len(session.exec(select(Skill)).all())
+            try:
+                write_skill_row(session, **kwargs)
+                fail(f"A4: write_skill_row accepted {kwargs}")
+            except ValueError:
+                pass
+            session.flush()
+            if len(session.exec(select(Skill)).all()) != count:
+                fail(f"A4: a refused write_skill_row wrote a row ({kwargs})")
+        session.rollback()
+    scanned = 0
+    for path in sorted((ROOT / "src").rglob("*.py")):
+        scanned += 1
+        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+            if isinstance(node, ast.Attribute) and node.attr == "physical_tier":
+                fail(f"A4: .physical_tier read at {path.relative_to(ROOT)}:{node.lineno}")
+    if scanned == 0:
+        fail("A4: no file scanned")
+    if "carrure=" not in (SRC / "cockpit" / "routes" / "npc_agent.py").read_text(encoding="utf-8"):
+        fail("A4: npc_agent.py does not pass the carrure")
+    play = (SRC / "cockpit" / "play_physical.py").read_text(encoding="utf-8")
+    if "skill_access.opposition_modifier(" not in play or "skill_access.player_skill(" not in play:
+        fail("A4: play_physical.py does not read its rows through skill_access")
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_a1()
+    check_a2(db_path)
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_a3(engine)
+    check_a4(engine)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: npc_skills -- v2.16 gives NPCs skill rows in place of physical_tier, migrates "
+          "every carrure to a physical row from v2.15 only, and an opposing NPC rolls its own "
+          "row for the skill, else its base domain, else Initié")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/stream_session_readonly.py b/tooling/verify/checks/stream_session_readonly.py
index ed81f99..6d8ced7 100644
--- a/tooling/verify/checks/stream_session_readonly.py
+++ b/tooling/verify/checks/stream_session_readonly.py
@@ -25,14 +25,17 @@ subprocess.
 rather than inferred): the four Play modules --
 `src/world_engine/cockpit/{play,play_stream,play_physical,play_initiative}.py`
 -- plus every module they hand a session to --
-`src/world_engine/{context,context_window,analyzer,gathering,prompt_store,scene_format}.py`.
+`src/world_engine/{context,context_window,analyzer,gathering,prompt_store,scene_format,skill_access}.py`.
 A named module missing from disk is a FAILURE. `scene_format` joined the set
 in TICKET-0073/BRIEF-0073-a, a verbatim relocation of three read-only
 formatters (`active_signposts`, `format_inventory_line`,
 `format_item_list_for_interpretation`) out of `context.py` -- same
 relocation-not-broadening precedent as `models.py` -> `models/` and
 `play_stream.py` -> `play_initiative.py`; the moved code has zero writers,
-so the set grows by exactly the new module, nothing else.
+so the set grows by exactly the new module, nothing else. `skill_access`
+joined in TICKET-0107/BRIEF-0107-A: the skill-row lookup and the opposition
+modifier moved out of `play_physical.py` (reads only), handed the request
+session by `_say_physical_resolve_verdict`.
 
 **WRITERS** -- every function defined anywhere in the declared set whose
 body calls `.add(`, `.delete(`, `.merge(`, `.commit(` or `.flush(` on a
@@ -120,6 +123,7 @@ DECLARED_MODULES: tuple[tuple[str, Path], ...] = (
     ("gathering", SRC / "world_engine" / "gathering.py"),
     ("prompt_store", SRC / "world_engine" / "prompt_store.py"),
     ("scene_format", SRC / "world_engine" / "scene_format.py"),
+    ("skill_access", SRC / "world_engine" / "skill_access.py"),
 )
 DECLARED_NAMES = {name for name, _ in DECLARED_MODULES}
 PLAY_MODULES = ("play", "play_stream", "play_physical", "play_initiative")
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 9b34e35..1f39d16 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,13 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.16** — TICKET-0107, BRIEF-0107-A: NPC skill sheets and skills
+  learned from a master. `skill_definition.requires_master` (default 0) and
+  `skill.taught_by_id` (FK `entity`, nullable) are added; an NPC holds skill
+  rows. `character.physical_tier` is dropped: `migrate_v2_16_npc_skills.py`
+  turns every NPC's non-zero tier into its `physical` row
+  (`TIER_TO_RANK`), refuses a database older than v2.15 or a SQLite older
+  than 3.35.
 - **v2.15** — TICKET-0106, BRIEF-0106-A: a skill has a rank and points.
   `skill.tier` (-1..2) becomes `skill.rank` (0..5: Inexpérimenté, Initié,
   Apprenti, Confirmé, Expert, Maître) plus `skill.xp`; the dice modifier is
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 5a54577..d4dc703 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.15
+Current schema version: v2.16
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -110,15 +110,10 @@ CREATE TABLE character (
   character_type  TEXT NOT NULL,                -- player | npc
   user_id         TEXT,                         -- NULL for NPCs
   current_location_id TEXT REFERENCES entity(id),
-  vital_status    TEXT DEFAULT 'alive',         -- alive | dead | missing | unknown
-  physical_tier   INTEGER NOT NULL DEFAULT 0     -- opposed-roll resistance
-                                                  -- tier, -1..2 (schema
-                                                  -- v1.77, TICKET-0025,
-                                                  -- BRIEF-0025-a). Migrated
-                                                  -- from entity.metadata
-                                                  -- ['physical_tier'].
-                                                  -- 0 = ordinaire default.
+  vital_status    TEXT DEFAULT 'alive'          -- alive | dead | missing | unknown
 );
+-- physical_tier (v1.77) was dropped at v2.16 (TICKET-0107): an NPC's
+-- non-zero tier became its `physical` skill row.
 ```
 -- Descriptive prose is not a column (schema v2.06, TICKET-0091):
 -- appearance -> `physique` fact, backstory -> `histoire`, aversion ->
@@ -1710,6 +1705,7 @@ CREATE TABLE skill_definition (
   points_to_rank_3  INTEGER,           -- then the world's (skill_rank)
   points_to_rank_4  INTEGER,
   points_to_rank_5  INTEGER,
+  requires_master   BOOLEAN NOT NULL DEFAULT 0,  -- learned only from a master (v2.16)
   created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
   updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
   CONSTRAINT ck_skill_definition_rank_points CHECK (
@@ -1771,16 +1767,20 @@ CREATE TABLE skill (
                         -- row — rename-safe by construction. ON DELETE
                         -- RESTRICT is a structural floor only (chantier 2
                         -- owns the real delete/cascade UX).
+  taught_by_id          TEXT REFERENCES entity(id),
+                        -- the master who taught it (v2.16); NULL when
+                        -- seeded or granted without a master
   created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
   updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
 );
 CREATE INDEX idx_skill_character ON skill(character_id);
 ```
 
--- NOTE: skill rows exist ONLY for player characters in this phase. NPC
--- physical capability is a single tier in character.physical_tier
--- (-1..2, default 0; schema v1.77, TICKET-0025 — moved off
--- entity.metadata). Domains are strictly physical/sensory: social
+-- NOTE: a player character holds the four base rows and one row per
+-- skill definition that does not require a master; a row for a
+-- requires_master definition exists only once taught (v2.16). An NPC holds
+-- only the rows the creator gives it; a base domain it has no row for
+-- reads Initié (+0) (skill_access.py). Domains are strictly physical/sensory: social
 -- abilities (persuasion, deception, charm) are NEVER skill domains — they
 -- belong to the free-dialogue layer and the relation graph. This is a
 -- standing design guard, not a deferral.
````

## Scope OUT

- The master lock, the flag on the catalogue routes, learning (B).
- The fiche on the NPC tab, « Exige un maître » (C).
- Changing the generators' prompt text: `public.physical_tier` stays their output (E1).
- Seeding four base rows on NPC creation (an absent base row reads Initié).
- Points for NPCs; the constraint-gated rolls' fixed difficulty.
- `scripts/migrate_v1_77_metadata_extraction.py` (historical).
- Every later brief of this lot.

## Invariants to defend

**The Play stream's request session is read-only:** `skill_access` reads only and is declared. **Custom skill lookups filter `skill_definition_id`:** `skill_access` keeps both filters. **Two canon-write paths:** the carrure is written by the creator CRUD's create core, through `write_skill_row`. **The schema is authoritative:** model, schema doc, changelog, constant and migration move together.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `play_physical.py` is not exactly 966 lines after the commit.
- The A2 rule of `npc_skills.py` fails (the migration on a v2.15-shaped database).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `CLAUDE.md` because a neighbouring line moved: replace the three lines ending « no NPC-side read (named deferral). » by the diff's three lines by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `npm ci` engine warnings (`EBADENGINE`); the pre-existing Svelte warning on `<option value="">`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/npc_skills.py` -> `PASS: npc_skills -- v2.16 gives NPCs skill rows in place of physical_tier, …, else Initié`.
- `stream_session_readonly.py`, `single_canon_write.py`, `skill_progression.py`, `world_cascade.py`, `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py`, `module_budget.py`, `function_length.py`, `pipeline_state.py`, `decisions_index.py`, `claude_md_contract.py`, `frontend_build_fresh.py` -> `PASS`.
- Mutation tests, each red then reverted: in `opposition_modifier`, `    row = _definition_row(db, npc_id, definition.id) if definition is not None else None` -> `    row = None` -> `A3`; in `_create_static_entity_core`, the `write_skill_row(db, character_id=entity.id, domain="physical", rank=rank)` call -> `pass` -> `A4`; in the migration, `            if character_type != "npc":` -> `            if character_type != "npc" or tier < 0:` -> `A2b`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 140/140.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema changelog v2.16, schema doc header and sections, one CLAUDE.md invariant line, decision entry `AN NPC HAS A SKILL SHEET (TICKET-0107) -- ITS ROWS OPPOSE THE ROLL, THE CARRURE BECOMES A ROW (BRIEF-0107-a, schema v2.16)` — all in the diff.
