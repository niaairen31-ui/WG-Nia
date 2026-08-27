# BRIEF — Step "context.py scene-format extraction"

TICKET-0073, brief -a. Behaviour-free. No schema change, no prompt change.

## Context

`src/world_engine/context.py` measures 979 physical lines against the
1000-line module budget (`tooling/verify/checks/module_budget.py`,
`MAX_LINES = 1000`). BRIEF-0073-b must add a new prompt section constant, a
new sub-assembler, and a call from `assemble_npc_context` — roughly 30 lines
that do not fit in the 21 remaining.

This brief buys the margin by moving three player-facing formatting helpers
out of `context.py`. They are not context assembly: they render signposts and
inventory for the play surface, they are imported by play modules rather than
called from any assembler in this file, and they sit after the MJ block.

Nothing about their behaviour changes. This is a relocation.

## Mini-RECON — measured, re-verify before editing

All anchors measured against `main` fetched 2026-08-23, schema v1.90.

- **[M]** `src/world_engine/context.py` = 979 lines, 31 top-level functions
  (budget: 1000 lines / 40 functions). `tooling/verify/baselines/module_budget.json`
  is EMPTY — no module is baselined, the cap applies unconditionally.
- **[M]** The three functions to move, contiguous at the end of the file:
  - `active_signposts` — `context.py:889`, ends at 951
  - `format_inventory_line` — `context.py:952`, ends at 972
  - `format_item_list_for_interpretation` — `context.py:973`, ends at 979 (EOF)
  Total 91 lines.
- **[M]** Their only dependencies are `Session`, `select`, and the models
  `DiscoverableDetail`, `Knowledge`, `Item`, `Entity`. They call NO helper
  defined in `context.py` (no `_section`, no `_knowledge_line`, nothing).
  `format_item_list_for_interpretation` calls `format_inventory_line`, which
  moves with it.
- **[M]** None of the three references `NpcGoal` or the literal `"npc_goal"`.
- **[M]** Importers of the three symbols, measured by
  `grep -rn "active_signposts\|format_inventory_line\|format_item_list_for_interpretation" --include=*.py src/ tooling/ scripts/`:
  - `src/world_engine/cockpit/play_physical.py:21,24` (imports), `:720`, `:427` (calls)
  - `src/world_engine/cockpit/play.py:29,30` (imports), `:457`, `:657`, `:306` (calls)
  - `src/world_engine/cockpit/routes/mutations.py:46,50` (imports)
  - `src/world_engine/cockpit/routes/scene.py:28` (import), `:257` (call)
  That is FOUR importing modules.
- **[M]** `tooling/verify/checks/npc_goal_read.py` enforces three rules that
  constrain any edit to `context.py`:
  - `check_mj_boundary` locates `assemble_mj_context` by name **in context.py**
    and FAILS with "assemble_mj_context not found" if it is absent. It may not
    be moved out of this file.
  - `check_dialogue_provenance_gate` locates `_goal_provenance_suffix` by name
    **in context.py** and FAILS if absent. It may not be moved out either.
  - Rule 2 forbids any `NpcGoal` / `"npc_goal"` reference in a top-level node
    at or after `assemble_mj_context`'s line number.

### STOP conditions

Stop and escalate rather than proceeding if any of these holds:

1. The importer enumeration above is incomplete — a fifth module imports any
   of the three symbols, or a symbol is referenced through
   `context.active_signposts` attribute access rather than a `from` import.
   Measure it; do not assume the list is right.
2. Any of the three functions turns out to reference a helper defined in
   `context.py` (the measurement says none does; verify before cutting).
3. `context.py` no longer measures 979 lines, or the three functions are no
   longer the last three in the file.
4. `tooling/verify/baselines/module_budget.json` is non-empty and contains an
   entry for `context.py`.

## Scope IN

1. **Create `src/world_engine/scene_format.py`.** Module docstring, verbatim:

   ```
   """Player-facing scene and inventory formatters (TICKET-0073, BRIEF-0073-a).

   Extracted verbatim from `context.py`, which was at 979/1000 lines and had
   no room for BRIEF-0073-b's new prompt section. These three functions are
   not context assembly: no assembler in `context.py` calls them, and their
   callers are all on the play surface. Behaviour is unchanged from the
   pre-extraction code — this module is a relocation, not a rewrite.
   """
   ```

2. **Move the three functions verbatim** from `context.py` into
   `scene_format.py`, in their current order: `active_signposts`,
   `format_inventory_line`, `format_item_list_for_interpretation`. Docstrings
   and comments move with them, unchanged. Do not reformat, rename, re-order
   arguments, or "improve" anything inside them.

3. **Carry the imports they need** into `scene_format.py` (`Session`,
   `select`, and the four models). Remove from `context.py` any import that
   becomes unused as a result — and ONLY those. Verify each removal against
   the remaining body of `context.py`; do not remove an import on the
   assumption it was only used by a moved function.

4. **Update the four importing modules** to import from
   `world_engine.scene_format` instead of `world_engine.context`. Where a
   module imports other symbols from `context` in the same statement, split
   the statement — keep the `context` import for the remaining symbols and add
   a new `scene_format` import. `routes/scene.py:28` is such a case: it
   imports `assemble_mj_context` and `format_item_list_for_interpretation`
   together.

5. **No re-export shim.** `context.py` must NOT re-export the three symbols.
   A shim would keep a dead indirection alive and hide the relocation from
   every future reader.

## Scope OUT

- **The `kind` column, the standing goal, and every part of the feature.**
  That is BRIEF-0073-b. This brief adds no column, no constant, no prompt
  section, no CHECK.
- **Moving `assemble_mj_context` or `_goal_provenance_suffix`.** Both are
  located by name in `context.py` by `npc_goal_read.py` and their absence is
  a check failure. Do not touch them.
- **Moving the MJ block** (`H_MJ_*` constants, `_mj_context_*`,
  `format_mj_context`, `_mj_knowledge_line`). It is a tempting larger
  extraction and it is not this brief. If more margin is wanted later it is
  its own step, with its own reckoning against the two name-located
  functions above.
- **Moving the `_npc_context_*` sub-assemblers.** Also tempting (231 lines),
  also not this brief: `_npc_context_goals` references `NpcGoal`, so the move
  would require a new `ALLOWED_MODULES` entry in `npc_goal_read.py` and a
  doctrine argument. Deferred; reactivation condition: *a later step needs
  more than 80 lines of margin in `context.py`.*
- **Any behaviour change inside the three moved functions.** The signpost
  cluster predicate, the inventory line wording, and the
  `format_item_list_for_interpretation` delegation stay exactly as they are.
- **Renaming any of the three functions.**
- **Touching `tooling/verify/baselines/module_budget.json`.** It is empty and
  stays empty; `module_budget.py` never rewrites the baseline and neither
  does this step.

## Invariants to defend

- **Module budget (R5, code_standards.md section 4).** The failing check IS
  the mechanism forcing a split — this brief is that split executed, not a
  route around it. No baseline entry is added.
- **N1 goal-read doctrine** (`npc_goal_read.py`). The extraction cuts AFTER
  `assemble_mj_context`, so Rule 2's window shrinks rather than grows, and
  neither name-located function moves. All three rules must still pass.
- **Relocation-not-broadening.** The precedent the check itself documents
  twice (models.py -> models/ package; play_stream.py -> play_initiative.py):
  code moves verbatim, the allowlist grows by the new module only when the
  moved code actually needs it. Here nothing moved touches `NpcGoal`, so
  `ALLOWED_MODULES` gains NO entry. If a draft of this step finds itself
  wanting to add `scene_format.py` to that allowlist, the cut line is wrong —
  stop and escalate.

## Done means

- [ ] `src/world_engine/scene_format.py` exists and contains exactly three
      top-level functions: `active_signposts`, `format_inventory_line`,
      `format_item_list_for_interpretation`.
- [ ] `wc -l src/world_engine/context.py` returns at most 920 (target ~888;
      the 80-line margin required by the ticket's first machine criterion).
- [ ] `grep -n "active_signposts\|format_inventory_line\|format_item_list_for_interpretation" src/world_engine/context.py`
      returns nothing.
- [ ] `python tooling/verify/checks/module_budget.py` exits green.
- [ ] `python tooling/verify/checks/npc_goal_read.py` exits green.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits green.
- [ ] The app starts (`WORLD_ENGINE_ENV` set, `PYTHONPATH=src`) and a play
      turn that narrates an entry into a location with at least one ambient
      signpost still shows that signpost, and the inventory line still renders.
- [ ] `/review-step` and `/close-step` run (engine code touched).
- [ ] One commit, message referencing TICKET-0073 / BRIEF-0073-a and stating
      that no behaviour changed.

## Docs to update

- No schema changelog entry — no schema change in this step.
- `ARCHITECTURE_DECISIONS.md`: no new decision. If the file carries a module
  map, add `scene_format.py` to it; otherwise nothing.
- `CLAUDE.md`: nothing. This step does not change a convention.
