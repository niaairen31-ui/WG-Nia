# AMENDMENT-0124-02 — `prompt_version.py` rule 7 calls the guarded routes

Ticket: TICKET-0124   Lot: LOT-0124-world-premise.md (header authoritative)
Brief in flight: D -- implemented, WP4 green, nothing committed; `/review-step`, `/close-step`, `/verify` not run.
Branch: `ticket/0124`. Base: `origin/main` (`386c01a`).

## What deviated

P1-g (C-08) makes `update_prompt_text` and `restore_prompt_version` refuse a
creator or player text without `{world_premise}`. `prompt_version.py` -- the
check behind INV-48 -- rule 7 (`:236-296`) creates a fixture head of usage
`npc_dialogue` (`:246`, a `player` usage since BRIEF-0124-B) and calls both
routes on texts without the placeholder (`:278-296`). The guard refuses them;
the check crashes with « Le cadre du monde {world_premise} est obligatoire
pour ce prompt. ».

R-12 recorded this check for its direct `write_prompt_version` calls only,
not its route calls: a RECON miss. Enumerated now on `386c01a`:
`grep -rn "update_prompt_text\|restore_prompt_version" tooling/verify/checks/`
-> `prompt_version.py` only. No other check calls the guarded routes.

Decision recorded: **K1** -- the fixture head's usage becomes
`conversation_summary`, a `none` usage (C-03). Rule 7 tests what it always
tested (a version appended, C1's 422 on `{oops}`, a verbatim restore), now
for the right reason; the guard stays tested by WP4. Rejected: K2 (keep
`npc_dialogue`, put the placeholder in its five texts -- the `{oops}` case
would then have to fail on C1 and not on the guard; reactivation: a rule of
`prompt_version.py` needs a creator or player head), K3 (the guard in
`write_prompt_version` -- the five checks of R-12).

## Amended RECON

R-12 opens with the line « Amended (AMENDMENT-0124-02) » in the lot header,
naming rule 7's route calls and K1.

## Amended brief

BRIEF-0124-D, regenerated:
- Mini-RECON gains the `prompt_version.py:246` and `:278-296` anchors, and the note that a resuming session keeps its uncommitted `apply_ticket_0124_world_premise.py`.
- Decision rights gain K1: one line at `prompt_version.py:246` (`usage="conversation_summary"`, with its comment), in a separate commit before the `rank_trials.py` stub commit.
- Done means gain: `prompt_version.py` -> `PASS` after K1; the named mutation (back to `npc_dialogue` -> rule 7 red with the guard's message, reverted).

No contract changes. No other brief is touched.

## How D resumes

The session keeps its uncommitted work (seed, script, guard, WP4) and adds
nothing to it. Commit order: (1) BRIEF-0124-D's own commit; (2) K1 in
`prompt_version.py`; (3) the `rank_trials.py` stub, `startswith` -> `in`
(AMENDMENT-0124-01's ADAPT). Then `/review-step` and `/close-step` per
commit; `/close-step` regenerates `FILE_MAP.md` (`file_map.py` red until
then). `corpus_gate.py` is then red only on `pipeline_state.py`'s arrows to
the checks of briefs E-I.

## Gate checks re-run

(a) R-12's new property traced to `prompt_version.py:246, :278-296` (the
check's implementation); (c) the enumeration above pasted; (e) rule 7
satisfied by `prompt_version.py` itself after K1, with `crud/prompts.py`'s
guard unchanged.
