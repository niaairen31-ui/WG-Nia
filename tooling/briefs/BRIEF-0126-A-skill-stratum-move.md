<!-- slug: skill-stratum-move -->
# BRIEF 0126-A — "The skill stratum leaves canon.py"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `src/world_engine/models/canon.py` is 964 lines; line 584 is
  `BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")`,
  line 597 `class SkillSystem(SQLModel, table=True):`, line 685 `class
  Skill(SQLModel, table=True):`, line 719 Skill's `updated_at`, line 722 the
  `discoverable_detail` header.
- `grep -n "BASE_SKILL_DOMAINS\|RANK_POINTS_CHECK\|SkillSystem\|SkillDefinition\|\bSkill\b" src/world_engine/models/canon.py | awk -F: '$1<580 || $1>719'` prints nothing.
- `src/world_engine/models/__init__.py:61-90` imports `BASE_SKILL_DOMAINS`,
  `Skill`, `SkillDefinition`, `SkillSystem` from `.canon`.
- `src/world_engine/models/canon_faction.py:16` is `from .canon import _created_ts, _uuid`.
- `src/world_engine/schema_reconcile.py:30` defines `static_table_names()`.

Halt if any anchor has moved.

## Facts carried

### R-02 -- the skill stratum in `models/canon.py`
Opened: `src/world_engine/models/canon.py:1-46, 576-724` (964 lines);
`src/world_engine/models/__init__.py:1-62, 84-86, 205-330`;
`src/world_engine/models/canon_faction.py:1-17`; the enumerations of (c).
Finding: lines 580-719 hold, in order, the comment and literal
`BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")`
(:584), `RANK_POINTS_CHECK` (:588-590), `SkillSystem` (:597-626),
`SkillDefinition` (:629-682) and `Skill` (:685-719); :720-721 are blank and
:722 opens the `discoverable_detail` header. No line of `canon.py` outside
580-719 names `BASE_SKILL_DOMAINS`, `RANK_POINTS_CHECK`, `SkillSystem`,
`SkillDefinition` or `Skill` (enumeration (c)-1). `canon.py` imports
`JSON, CheckConstraint, Column, DateTime, ForeignKey, Index, String, func,
text` from sqlalchemy (:34-44) and `Field, SQLModel` from sqlmodel (:45).
`canon_faction.py` is the extraction precedent: its own docstring, `from
.canon import _created_ts, _uuid` (:16). `models/__init__.py` imports
`BASE_SKILL_DOMAINS` (:62), `Skill`, `SkillDefinition`, `SkillSystem`
(:84-86) from `.canon` and lists them in `__all__` (:280-283, :321);
`RANK_POINTS_CHECK` is not exported and has no reader outside `canon.py`
(enumeration (c)-2). No module imports `models.canon` by path for these
names and no check reads `canon.py` for them (enumerations (c)-1, (c)-3).
Consequence: A moves lines 580-719 verbatim into `models/canon_skill.py`
and re-points the four `__init__` imports; `canon.py` drops to 822
lines, which is what lets B add columns. `static_table_names()` before and
after is the proof of a pure move (R-41).
### R-29 -- the models package layout
Opened: `src/world_engine/models/__init__.py:1-58, 109-205`.
Finding: the docstring lists each stratum module with its tables; the
import order is canon, canon_faction, canon_knowledge, canon_attribute,
canon_event, config, ephemeral, pipeline, observation, quests; each module
imports `_created_ts, _uuid` from `.canon`.
Consequence: A adds `canon_skill.py` after `canon` in the docstring and the
imports; B adds `pc_drafts.py` (non-canon, pending player drafts) last.
### R-36 -- governance texts and budgets
Opened: `CLAUDE.md:234-254` (20 589 characters);
`.claude/rules/player-surface.md` (889), `skills.md` (2 896);
`tooling/verify/checks/claude_md_contract.py:1-76`;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last 15 lines).
Finding: budgets 22 000 characters for the root, 4 000 per rule file, 100
characters per line; every invariant bullet starts `- **INV-NN**` and ends
with `-- enforced by` and checks, or `[no check]`; ids run INV-01 to the
highest with none dropped; the highest is INV-66
(`player-surface.md:17`); a rule file opens with `paths:` globs that each
match a file; the root's « Path-scoped rules » list equals the files on
disk. ARCHITECTURE_DECISIONS ends with `---` then `*Co-built with Claude,
June 2026.*`; an entry is inserted above that footer.
Consequence: C creates `.claude/rules/character-creation.md` (INV-67) and
its list line in CLAUDE.md; D and F amend INV-66 in `player-surface.md`;
I inserts the ticket's entry above the footer.
### R-40 -- module budgets of the files this lot edits
Opened: `ast` count and `wc -l` at `fb8557a`;
`tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 physical lines and 40 top-level functions plus methods
for `src/**/*.py`, 1000 lines for `frontend/src/**/*.svelte|js`.
`models/canon.py` 964; `crud/skills.py` 667 lines / 23; `models/pipeline.py`
813; `perspective_selectors.py` 281; `perspective_audit.py` 128;
`lore_render.py` 340; `world_premise.py` 131; `prompt_call.py` 47;
`prompt_registry.py` 488; `writes/worlds.py` 168; `cockpit/app.py` 343 /
12; `routes/player.py` 129; `tabs.js` 890; `EntityList.svelte` 413;
`registry.js` 604; `Creation.svelte` 250; `CompetencesSheet.svelte` 253;
`competences.svelte.js` 361; `joueur.svelte.js` 168; `WorldPage.svelte` 83.
Consequence: `canon.py` cannot take B's columns before A; every other edit
stays far under its cap; `tabs.js` takes at most 15 lines; new logic goes
to new modules.
### R-41 -- the pure-move proof
Opened: `src/world_engine/schema_reconcile.py:30`.
Finding: `static_table_names() -> set[str]` returns the table names of the
static model metadata.
Consequence: A's Done means compares its output before and after the move.

## Contracts

### C-01 -- the skill stratum module
Produced by: A   Consumed by: B, C
Module: `src/world_engine/models/canon_skill.py`. Holds, verbatim and in
this order, `canon.py` lines 580-719 at `fb8557a`: the comment and
`BASE_SKILL_DOMAINS`, the comment and `RANK_POINTS_CHECK`, `SkillSystem`,
`SkillDefinition`, `Skill`, with their section comments. Its own docstring
(the `canon_faction.py` shape: « extracted from ``canon.py`` (TICKET-0126,
BRIEF-0126-A) to keep each stratum module under the `module_budget.py`
line cap »). Imports exactly what those lines use: `datetime`, `Optional`,
`Column, CheckConstraint, ForeignKey, Index, JSON, text` from sqlalchemy,
`Field, SQLModel` from sqlmodel, `_created_ts, _uuid` from `.canon`.
`canon.py` no longer holds lines 580-719; its imports are unchanged.
`models/__init__.py` imports `BASE_SKILL_DOMAINS, Skill, SkillDefinition,
SkillSystem` from `.canon_skill`; `__all__` unchanged; the docstring lists
`canon_skill.py` after `canon.py`. Table set unchanged
(`static_table_names()` identical).

## Context

TICKET-0126 lets a player create a character. Brief B adds columns to the
skill system and skill definition models, but `canon.py` is at 964 of its
1000 lines (R-40). This step moves the skill stratum into a module of its
own, exactly as `canon_faction.py` was extracted at TICKET-0048, and
changes nothing else: one pure-move commit.

## Scope IN

1. Create `src/world_engine/models/canon_skill.py` per C-01: a docstring in
   `canon_faction.py`'s shape (« Canon SQLModel table classes — skill
   domain, extracted from ``canon.py`` (TICKET-0126, BRIEF-0126-A) to keep
   each stratum module under the `module_budget.py` line cap. Same
   schema-fidelity conventions as `canon.py`. »), `from __future__ import
   annotations`, the imports C-01 lists, then `canon.py` lines 580-719
   copied byte for byte.
2. Delete lines 580-721 from `canon.py` (the moved block and the two blank
   lines after it), so that the two blank lines 578-579 separate the
   preceding table from the `discoverable_detail` header, as between every
   other pair of blocks. Leave `canon.py`'s import block and docstring
   unchanged.
3. In `models/__init__.py`: move `BASE_SKILL_DOMAINS`, `Skill`,
   `SkillDefinition`, `SkillSystem` out of the `from .canon import (...)`
   block into a new `from .canon_skill import (BASE_SKILL_DOMAINS, Skill,
   SkillDefinition, SkillSystem)` placed right after it; leave `__all__`
   unchanged; in the docstring's layout list add, after `canon.py`'s entry:
   `canon_skill.py   — the skill domain (SkillSystem, SkillDefinition,
   Skill, BASE_SKILL_DOMAINS), extracted from canon.py at TICKET-0126 for the
   module_budget cap.`, and add `canon_skill` after `canon` in the « Import
   order » sentence.
4. One commit: « TICKET-0126 A: move the skill stratum to canon_skill.py
   (pure move) ».

## Scope OUT

- Any column, constraint, index or default change (B).
- Removing imports `canon.py` no longer uses: a pure move leaves them.
- Moving any other table out of `canon.py`.
- `creation_rules` (B).

## Invariants to defend

- INV-41 to INV-46 (`.claude/rules/skills.md`) describe these tables'
  behavior; a pure move must not alter a single declaration. The proof is
  `static_table_names()` and the unchanged `create_all` DDL.
- None of the player-surface or perspective invariants is touched.

## Decision rights

STOP:
- An anchor does not hold.
- Any module outside `models/` imports one of the four names from
  `models.canon` (the grep of R-02 says none does).
- The DDL of `skill_system`, `skill_definition` or `skill` compiled from the
  models differs before and after.

ADAPT:
- `canon_skill.py` needs an import C-01 does not list (a name the moved
  lines use): add exactly that import, report it.
- The blank-line count around the cut differs from Scope IN 2: keep two
  blank lines between top-level blocks, report it.

REPORT-ONLY:
- Imports of `canon.py` left unused by the move.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after the commit (paste both).
- [ ] For `skill_system`, `skill_definition`, `skill`: the
      `CreateTable(...).compile()` text is identical before and after
      (paste the diff: empty).
- [ ] `wc -l src/world_engine/models/canon.py` is 822 (964 minus
      lines 580-721); `canon_skill.py` exists.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/module_budget.py`,
      `skill_system_shape.py`, `rank_trial_schema.py`, `skill_progression.py`,
      `npc_skills.py` and `corpus_gate.py` PASS.
- [ ] `/review-step` then `/close-step` (FILE_MAP regenerated with
      `canon_skill.py`).

## Docs to update

- `models/__init__.py` docstring (Scope IN 3). No schema change, no
  changelog entry, no decision entry: this step is a pure move.
