# BRIEF — Step "Extract the NPC-initiative cluster" (TICKET-0035, BRIEF-0035-a)

## Context

`play_stream.py` sits at exactly 1000 lines — the `module_budget.py` cap —
before TICKET-0034 touches it. BRIEF-0034-c must add an `origin_location_id`
capture and a mandated verbatim comment inside `_perform_travel`, pushing the
file over. The baseline mechanism was retired at TICKET-0028, and shortening
the comment is the check-dodge the budget check explicitly warns against. This
ticket makes room the only sound way: it relocates the self-contained
NPC-initiative cluster into its own module, on the `play_physical.py` split
precedent (BRIEF-0027-b/-d).

**This is a pure relocation. No function body changes. No canon-write site
moves. No schema, no migration.** The single measure of success is that the
same behavior runs from two files instead of one, both under budget.

The dependency map (verified at RECON on the extraction branch):
- The cluster to move depends INWARD on `_TurnCtx` (defined in `play.py`,
  already imported by `play_stream.py`), `assemble_npc_context` /
  `format_mj_context` (`context.py`), `_analyze_window` / `_analyze_overhearing`
  (`analyzer.py`), and a few `_load_*_template` helpers.
- The one edge crossing the new boundary is OUTWARD from what STAYS to what
  LEAVES: `_say_narrate_and_finish` (stays) calls `_say_initiative_phase`
  (leaves) once (`play_stream.py:347`). After the split, `play_stream.py`
  imports the initiative entrypoint from `play_initiative.py` — a one-way
  edge, no cycle.
- The cluster calls NOTHING that stays behind (verified: no call to
  `_say_narrate_and_finish`, `_scene_response`, `_build_mj_user`,
  `_perform_travel`, `_propose_engine_injury` from within the moved range).
- External caller to preserve: `play.py:506/521` calls
  `_play_stream._select_group_speaker`. `_select_group_speaker` moves; that
  call site repoints to the new module.

## Scope IN

1. **New module — `src/world_engine/cockpit/play_initiative.py`.** Move the
   following top-level functions OUT of `play_stream.py`, VERBATIM (bodies
   byte-for-byte unchanged), in their current relative order:

   - `_say_initiative_vote` (`play_stream.py:76`)
   - `_say_initiative_context` (`:126`)
   - `_say_initiative_generate` (`:161`)
   - `_say_initiative_apply` (`:215`)
   - `_say_initiative_narrate` (`:248`)
   - `_say_initiative_phase` (`:291`)
   - `_select_group_speaker` (`:395`)
   - `_build_join_narration_user` (`:444`)
   - `_load_mj_initiative_template` (`:478`)
   - `_load_npc_initiative_act_template` (`:495`)
   - `_initiative_candidate_data` (`:523`)
   - `_initiative_signal_lines` (`:541`, with its nested `_npc_rel` /
     `_signal_line`)
   - `_initiative_vote_call` (`:569`)
   - `_npc_initiative_vote` (`:622`)
   - `_build_initiative_trigger` (`:650`)
   - `_build_initiative_mj_user` (`:677`)

   Confirm against the live file before moving — line numbers will have
   drifted after 0034-a/-b landed. The selection criterion is definitional,
   not positional: **every function whose name contains `initiative`, plus
   `_select_group_speaker` and `_build_join_narration_user`** (the two
   speaker/join helpers that form one cluster with it and are called only
   from the initiative path and `play.py`). If a function in the list turns
   out to be called by something that STAYS (other than the single
   `_say_initiative_phase` edge named above), STOP and REPORT — do not move it
   and do not invent a shared helper.

   Module docstring, verbatim, matching the `play_physical.py` precedent:

   ```
   """NPC-initiative branch of the `say` play path (TICKET-0035, extracted
   from play_stream.py at BRIEF-0027-b/-d's module boundary). Initiative
   vote, candidate signal assembly, self-initiated NPC action, group
   speaker selection, join narration. Imported lazily from
   play_stream._say_narrate_and_finish and from play._say_run_turn; see
   play.py's module docstring for the split rationale.

   RELOCATION ONLY (TICKET-0035): every function here moved verbatim out of
   play_stream.py to clear the 1000-line module_budget cap. No behavior
   changed in the move.
   """
   ```

2. **Imports on the new module.** Give `play_initiative.py` exactly the
   imports its moved bodies reference — a subset of `play_stream.py`'s current
   import block (Scope IN reference: `play_stream.py:1-48`). Do NOT copy the
   whole block wholesale; include only what the moved functions use
   (`_TurnCtx`, `ResponseMode` and the other `from .play import (...)` names
   they touch; `assemble_npc_context`, `format_mj_context`; the `analyzer`
   aliases; the model classes actually referenced; `current_prompt`;
   `logging`, `json`, typing). `pyflakes` (R8 / F821) is the arbiter — the
   verify suite catches both an undefined name and an unused import.

3. **`play_stream.py` after removal.**
   - Delete the moved functions.
   - At the single call site `_say_narrate_and_finish` -> `_say_initiative_phase`
     (`play_stream.py:347`), add a lazy import in the same idiom the file
     already uses for cross-module calls
     (`from . import play_initiative as _play_initiative`) and repoint the
     call to `_play_initiative._say_initiative_phase(...)`. Match the existing
     lazy-import placement convention (inside the function, as
     `play.py:201/361/385` do) — this is also what keeps the import edge
     one-way and cycle-free.
   - Drop any import lines in `play_stream.py`'s top block that are now unused
     after the functions left (pyflakes will name them).
   - Update `play_stream.py`'s module docstring: its current line names "NPC
     initiative, speaker selection" as part of this file — remove those two,
     add a one-line pointer that they now live in `play_initiative.py`.

4. **External caller — `src/world_engine/cockpit/play.py`.** At `:506` and
   `:521`, `_play_stream._select_group_speaker(...)` becomes
   `_play_initiative._select_group_speaker(...)`. Add the
   `from . import play_initiative as _play_initiative` lazy import in those
   functions, same idiom as the existing `_play_stream` lazy imports right
   beside them. Update the comment at `play.py:224-225` that lists
   `_select_group_speaker` among play_stream's members if it names the module.

5. **Canon-write policy — `tooling/verify/canon_write_policy.txt`.** NO CHANGE.
   `_perform_travel` (the one sanctioned canon-write site in this file) STAYS
   in `play_stream.py`. If this brief's execution produces a diff on
   `canon_write_policy.txt`, something moved that should not have — STOP and
   REPORT.

6. **Docs** (see Docs to update).

## Scope OUT

- **Any behavior change.** No function body is edited — not a rename, not a
  reordering of statements, not a "while I'm here" cleanup. `git diff` must
  read as: lines deleted from one file, appearing unchanged in another, plus
  import/call repointing. Anything else is out of scope; REPORT it.
- **Moving `_perform_travel`, `_scene_response`, `_build_mj_user`,
  `_mj_user_physical`, `_propose_engine_injury`, `_find_player_item`,
  `_build_refusal_instruction`, or the `_say_*` narration tail** — they stay.
  This ticket moves the initiative cluster only.
- **The BRIEF-0034-c changes** (endpoint, `origin_location_id` capture,
  `spatial_door_travel.py`) — they are already done on the branch and are NOT
  touched here. This ticket lands between 0034-b and 0034-c; it does not
  re-open 0034-c's work.
- **Splitting `play.py` or `play_physical.py`** — neither is at the cap; not
  this ticket.
- **Extracting a shared `_initiative` helper, deduplicating, or "improving"
  the initiative logic** — pure relocation. No refactor.
- **Re-adding a `module_budget.json` baseline** — the split is the mechanism;
  an exemption is the anti-pattern.
- **Touching the `context builder` classes** deferred in the OOP analysis —
  unrelated.

## Invariants to defend

- **Relocation is not broadening** — the governing principle of every
  `canon_write_policy.txt` comment since TICKET-0027. The count of sanctioned
  canon-write sites is unchanged because `_perform_travel` does not move. The
  count of anything is unchanged; only the file boundary moves.
- **One-way import edge, no cycle.** `play_stream.py` -> `play_initiative.py`
  (for `_say_initiative_phase`), never the reverse. The lazy-import-inside-
  the-function idiom that `play.py`/`play_physical.py` already use is what
  enforces it; keep it.
- **`pyflakes` F821 (R8) is the import arbiter** — no undefined name, no
  unused import, in either file after the move.
- **Module budget is the point of this ticket** — both files must land under
  1000/40. If the initiative cluster alone approaches the cap, that is a
  finding to REPORT, not to baseline around.
- **No canon path touched** — `single_canon_write.py` must be green with a
  zero-line diff on its policy file.

## Done means

- [ ] `wc -l src/world_engine/cockpit/play_stream.py
      src/world_engine/cockpit/play_initiative.py` — both < 1000; their sum is
      ~ the original 1000 plus the two new docstrings and repointed imports
      (no large delta = no accidental duplication).
- [ ] `module_budget.py` green on both files.
- [ ] Full verify suite green — including `single_canon_write.py` with a
      ZERO-line diff on `tooling/verify/canon_write_policy.txt`, and pyflakes
      (R8) clean on both files.
- [ ] `git diff` inspection: no function body changed; only deletions,
      verbatim re-additions, docstring edits, and import/call repointing.
- [ ] `python -c "from world_engine.cockpit import play_initiative, play_stream, play"`
      imports clean (no circular import at module load).
- [ ] Live smoke (danger class none; a normal Play session, no migration):
      - In a gathering with 2+ NPCs, the player says something -> an NPC
        initiative turn fires (vote -> self-initiated action -> MJ narration),
        same as before.
      - Group speaker selection still picks a responder (the `play.py` ->
        `_select_group_speaker` path).
      - Join narration on entering a gathering still renders.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` / changelog: **no schema change** — no entry, no
  version bump. Say so explicitly in the close note.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append a short TICKET-0035
  block — the initiative cluster extracted to `play_initiative.py` on the
  `play_physical.py` precedent to clear the module-budget cap; relocation-not-
  broadening; the one-way import edge; and the note that this sits between
  0034-b and 0034-c in the execution order because BRIEF-0034-c's mandated
  comment needs the headroom.
- `CLAUDE.md`: the "Where things live" / module-map area gains
  `play_initiative.py` beside `play_stream.py` / `play_physical.py` with a
  one-line description. No new standing rule expected; REPORT if execution
  reveals one.
- No change to `canon_write_policy.txt` (Scope IN 5).
