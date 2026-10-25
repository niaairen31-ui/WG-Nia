# AMENDMENT-0126-01 — two name bans the lot missed: `pc_draft.story`, `backstory_terms`

Ticket: TICKET-0126   Lot: LOT-0126-character-creation.md (header authoritative)
Brief in flight: F -- three commits on `ticket/0126` (`978775b`, `5019340`, `a4cda95`), its own
checks green, stopped before `/verify`: `corpus_gate.py` red on `lore_as_facts.py` R1.
Decision: Nia, 2026-10-23, **R-a** (rename; rejected R-b, a per-file exemption in R1).

## What deviated

1. **`lore_as_facts.py` R1** fails on any attribute named `backstory` under
   `src/world_engine/` outside `models/`, whatever the object: the rule was
   written for `Character.backstory`, moved into facts at v2.06, and reads
   names, not types. v2.32 gave `pc_draft` a `backstory` column (C-02) and
   C-11 reads `draft.backstory` (`creation_designer.py:92`, `:342`). Brief G
   would add more (`DraftSaveBody.backstory`, the writer, the read shape).
2. **`knowledge_identity.py` K3** (not yet triggered) pins, per file under
   `src/world_engine/`, the count of attributes, constants, keywords and
   arguments named `subject`. C-11 names a function `subject`; brief G's
   route would call it as `creation_designer.subject(`, an attribute: K3
   red.
3. **The arrow floor** (`pipeline_state.py:54, 113-120`): while TICKET-0126
   is in `exec`, every Machine-checkable arrow must name an existing check.
   `player_creation.py` exists from G's commit 3, `submitted_drafts.py` from
   I's commit 1: until then `corpus_gate.py` is red on `pipeline_state.py`
   for those, and only those. Briefs B-H named `corpus_gate.py -> PASS`:
   unsatisfiable while a later check is missing. The same rule turned
   TICKET-0124 red (AMENDMENT-0124-01, point 4); the lot RECON did not
   carry it.
4. The lot RECON never enumerated the checks that ban a name across
   `src/`. Done now (below): only R1 and K3 touch this lot.

## Enumeration (re-run on `fb8557a`)

Checks walking `src/` and failing on an attribute name:
```
lore_as_facts.py R1        appearance backstory secrets philosophy internal_structure
                           internal_tensions aversion goals       -> `backstory` hits this lot
knowledge_identity.py K3   subject (attribute, constant, keyword, argument; census per file)
                                                                   -> `subject` would hit this lot
skill_progression.py A4    tier                                    -> none here
npc_skills.py              physical_tier                           -> none here
quest_rewards.py           owner_id location_id equipped (item reads) -> none here
event_contexts.py          knowledge_status occurred_at has_magic_impact consequences -> none here
```
Every other `.attr in` / `.attr ==` scan is scoped to one function or file
the lot does not touch (`day_narration.py`, `day_plan.py`, `conditions.py`,
`observation_socle.py`, `choice_review.py`, `world_tick.py`).

## Amended RECON

New **R-43** in the lot header (authoritative): the two name bans and the
arrow floor, with their consequence -- `pc_draft.story`, `backstory_terms`,
and `corpus_gate.py` red only on the arrows of checks a later brief creates.

## Amended contracts

- **C-02** -- `PcDraft.story: str` (default `''`) replaces `backstory`;
  `PAYLOAD_KEYS["creation_subject"]` holds `story` in place of `backstory`.
  The migration gains a rename step (Corrective step, item 2).
- **C-04** -- `DRAFT_VIOLATION_CODES` holds `story_missing` in place of
  `backstory_missing`; it tests `draft.story`; message unchanged. INV-67's
  last clause reads « no other module computes a sheet's cost or verdict »
  (the designer reads the costs through `creation_rules` to describe them,
  as C-11 says; CB5 already checks exactly that).
- **C-11** -- `subject(...)` is renamed `backstory_terms(...)`, same
  signature and behavior; `_subject_call` sends `draft.story` as the value
  of the prompt variable `backstory` (variable names, prompt texts and
  usages unchanged).
- **C-12, C-13, C-14** -- `story` in place of `backstory`: the writer's
  parameter, the read shape's key, the PUT body's field.
- **(b)-3** gains four rows, the gaps the executor filled in F (kept as
  written): a skill code given twice keeps its first valid entry; a
  membership or knowledge item that is not an object is dropped without a
  note; a membership's faction is matched under `normalize_surface`, as the
  start place; a sketch's `group` is stored as `group_label`.

## Corrective step (resumes BRIEF-0126-F, before `/verify`)

Anchors to confirm: `ticket/0126` head is `a4cda95`; `models/pc_drafts.py`
declares `backstory: str` on `PcDraft`; `creation_designer.py` defines
`def subject(` and reads `draft.backstory`; `writes/lore_usage.py`
`PAYLOAD_KEYS["creation_subject"]` holds `"backstory"`;
`.claude/rules/character-creation.md` INV-67 ends its sentence with
`no other module reads a rank's creation cost.` Halt if any has moved.

Scope IN:
1. `models/pc_drafts.py`: `backstory` -> `story` (same type, default,
   server default).
2. `scripts/migrate_v2_32_character_creation.py`: in `_plan()`, after the
   table creations, when `pc_draft` exists and its columns hold `backstory`
   and not `story`: `ALTER TABLE pc_draft RENAME COLUMN backstory TO story`
   (run in the same raw transaction); the post-checks gain « `pc_draft`
   holds `story` and not `backstory` »; the docstring names the step («
   renames `pc_draft.backstory` to `story` on a database that ran this
   script before AMENDMENT-0126-01 »). Still idempotent; still writes no
   other data.
3. `writes/lore_usage.py`: `"backstory"` -> `"story"` in
   `PAYLOAD_KEYS["creation_subject"]`.
4. `creation_designer.py`: `def subject(` -> `def backstory_terms(` (its
   docstring and every caller); `draft.backstory` -> `draft.story`.
   `creation_lore.py` unchanged.
5. `world-engine-schema.md`: the `pc_draft` block's column is `story`, with
   the comment `-- the player's story (not \`backstory\`: lore_as_facts R1)`.
   The v2.32 changelog entry is unchanged (it names no column of
   `pc_draft`).
6. `.claude/rules/character-creation.md`: in INV-67, the line
   `  \`creation_rules\`; no other module reads a rank's creation cost.`
   becomes `  \`creation_rules\`; no other module computes a sheet's cost or
   verdict.` (each line under 100 characters).
7. Checks: `creation_schema.py` -- CS1 expects `PcDraft.story`, no
   `backstory`, and C-02's amended `PAYLOAD_KEYS`; a new sub-rule **CS3d**:
   on a fixture at `schema_meta` v2.32 whose `pc_draft` is created from a
   literal DDL holding `backstory` (C-02's table at `a4cda95`) with one row,
   the script exits zero, the column is `story`, the row keeps its id and
   text, a second run changes nothing. `creation_designer.py` -- its
   fixtures write `story=`, CD4 calls `backstory_terms`.

Scope OUT: briefs G, H, I (regenerated below, not executed here); any
prompt text or variable; `lore_as_facts.py` and `knowledge_identity.py`
(their rules stand: R-a).

STOP: any other check turns red after items 1-7; the rename would lose a
row; an anchor does not hold. ADAPT: SQLite refuses `RENAME COLUMN` under
`legacy_alter_table=ON` -- run the rename after resetting it to OFF, inside
the same transaction, report.

Done means:
- [ ] `creation_schema.py` (CS1-CS3d), `creation_designer.py` (CD1-CD5),
      `lore_as_facts.py`, `knowledge_identity.py`, `lore_usage.py`,
      `claude_md_contract.py`, `creation_budget.py` PASS.
- [ ] Named mutation: CS3d -- remove the rename step from `_plan()` -> red;
      reverted.
- [ ] `corpus_gate.py`: red on nothing but `pipeline_state.py`'s arrows to
      `player_creation.py` and `submitted_drafts.py` (R-43).
- [ ] Commits: (1) items 1-5, « AMENDMENT-0126-01: pc_draft.story,
      backstory_terms »; (2) items 6-7. `/review-step` then `/close-step`
      each. Then `/verify` for F as the pipeline orders: its verdict is
      expected red on exactly the two `pipeline_state.py` arrows above.

## Briefs regenerated

- **G** -- `story` and `backstory_terms` throughout (C-11 to C-14 re-embedded);
  R-43 embedded; Invariants name R1 and K3; Done means runs `corpus_gate.py`
  after each commit, red only on the arrow to `submitted_drafts.py`.
- **H** -- R-43 embedded; the screen sends `story` (C-14); Done means as G's.
- **I** -- scope unchanged; regenerated only for its embedded C-13 (the
  `story` key) and C-04 (`story_missing`).
- A-F -- executed; their Done means' `corpus_gate.py -> PASS` is read as
  point 3 states. No other change.

## Gate checks re-run

(a) R1 and K3 traced to their implementations (`lore_as_facts.py:63-80`,
`knowledge_identity.py:842-863`), the arrow floor to `pipeline_state.py`;
(c) the enumeration above; (d) C-02, C-04, C-11-C-14 re-read for every
`backstory` and `subject` token: none left but the prompt variable
`backstory` (a string, never an attribute) and the usage `creation_subject`
(a different constant); (e) G, H, I's gates re-run with point 3.

## For Nia

- If you already ran `migrate_v2_32_character_creation.py` on your database,
  run it again after the corrective step: it renames the column and changes
  nothing else.
- Still to run after F: `python scripts/apply_ticket_0126_designer_prompts.py`.
- Proposed line for `brief-generation-protocol.md`, lot RECON section: «
  Enumerate every check that bans a name across `src/` (an `ast.Attribute`,
  `Name`, constant or keyword scan, a census by name) and test each new
  column, field, function and key the lot introduces against them. Carry
  the arrow floor of `pipeline_state.py`: a brief's Done means never claims
  `corpus_gate.py` green while a later brief's check is still missing. »
