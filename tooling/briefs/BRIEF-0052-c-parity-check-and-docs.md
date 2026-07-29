# BRIEF-0052-c — Step "parity check, live gate, docs"

## Context

TICKET-0052, closing step. Briefs -a and -b built the shared seam and wired the observed
lane onto it. Nothing yet PREVENTS the divergence from reappearing: a future brief could add
a second cap in `observation_runner.py`, or route the MJ narration through the seam, and
every existing check would stay green. This step makes the parity structural, runs the
over-budget live gate, and records the decisions — including the three named deferrals, which
must be written down rather than remembered.

## Mini-RECON (report before changing anything)

1. Report the idiom of `tooling/verify/checks/import_cycle.py` as the check template — the
   `FAILURES` list, `_report_and_exit`, `ROOT` via `parents[3]` — and confirm it is still the
   current shape (it is the standing reference; confirm rather than assume).
2. Report which existing check, if any, already asserts something about
   `observation_runner.py`'s call graph (`tooling/verify/checks/observation_runner.py`
   exists). Report its rules so the new check ADDS rather than duplicates. If an existing rule
   already covers one of the assertions below, extend that check instead of writing a second
   one, and say which.
3. Report the current line/function counts of `context_window.py`, `observation_window.py`,
   and `observation_runner.py` against the 40/1000 budget.

## Scope IN

1. **New check `tooling/verify/checks/observation_window_parity.py`** (stdlib `ast` only, no
   DB), or the equivalent rules folded into the existing `observation_runner.py` check if
   mini-RECON (2) says that is the right home. Vacuous-proof throughout: a rule that finds
   zero candidates FAILS, it does not pass.

   - **Rule 1 — the old module is gone.** `src/world_engine/conversation_window.py` must not
     exist, and no file under `src/`, `scripts/`, or `tooling/` may reference the bare
     identifier `conversation_window` (the substrings `conversation_window_config`,
     `load_conversation_window_config`, `upsert_conversation_window_config` are permitted and
     must be excluded from the match, not caught by it).
   - **Rule 2 — single window implementation.** The identifiers `split_verbatim_tail`,
     `line_word_count`, `summarize_older_lines`, and `format_summary_note` may be DEFINED only
     in `src/world_engine/context_window.py`. A definition anywhere else under `src/` fails.
     This is what makes a second, drifting cap impossible rather than merely discouraged.
   - **Rule 3 — the observed lane consumes the seam.**
     `observation_window.resolve_observation_transcript` must be referenced in
     `observation_runner.py`, and `observation_window.py` must import from `context_window`.
     Zero references fails.
   - **Rule 4 — H1 asserted structurally.** Within `observation_runner.py`, the function
     `_generate_mj_narration` must contain no reference to `resolve_observation_transcript`,
     and no caller may pass that resolution to it. Attribute at function grain, lexically —
     the same attribution model `single_canon_write.py` uses. The check must locate
     `_generate_mj_narration` and fail if it cannot (vacuous-proof), rather than passing
     because the function was renamed away.
   - **Rule 5 — the observed lane imports no cockpit module.**
     `src/world_engine/observation_window.py` must not import from `world_engine.cockpit`.

2. **Played-lane round-trip assertion.** Add to the same check, or as a small test the check
   invokes: for a fixed synthetic `npc_history` of 12 messages alternating `user`/`assistant`,
   `_lines_to_played(_played_to_lines(h))` equals `h` (role and content, element for element).
   This is the machine-checkable form of "byte-identical played lane". Hard-code the fixture in
   the check; no DB.

3. **Over-budget live gate procedure**, written into the brief's Done means and executed:
   start an observation run with `max_beats=60` and `mj_narration=true` on the active world,
   with at least 3 present NPCs. Capture, for one beat above budget:
   - the transcript handed to `request_intent` (summary note + last K lines + scene tail);
   - the transcript handed to `_generate_mj_narration` (full, unwindowed);
   - the `conversation_summary` call count for that beat — expected N, one per present NPC
     (G2's accepted cost). If it is 1, G2 was not implemented as specified; report it.

4. **Label the pre-0052 metrics (D).** In `scripts/observation_metrics.py`, extend the
   interpretation guard already printed before any figure (the module docstring describes this
   pattern) with, verbatim:

   ```
   Fenetre de contexte : les runs anterieurs a TICKET-0052 ont ete produites SANS
   fenetre glissante cote observation (transcript integral a chaque beat). Leurs
   chiffres de repetition (metrique 8) constituent une baseline "sans fenetre" et
   ne sont pas comparables terme a terme aux runs posterieures. Ils ne sont pas
   rejoues (TICKET-0052, decision D).
   ```

   Print it unconditionally, for every run. Do NOT attempt to detect per-run whether the
   window was active — no column records it, and inventing one would be a schema change
   smuggled into a docs brief.

5. **`ARCHITECTURE_DECISIONS.md` section.** Append, in the established style, a section
   titled `OBSERVATION CONTEXT WINDOW PARITY (TICKET-0052, no schema change)` covering: B1/I2
   (the neutral seam and why `_render_older_transcript`'s role-only labelling forced it);
   C1 + E1 (one config row, word budget only, and the accepted consequence that the branch is
   dormant in a 30-beat run — with the reasoning that fidelity, not trigger frequency, is the
   objective); G2 coupled to J1 (per-NPC resolution is required by the per-NPC scene tail);
   H1 with the `play_stream.py:51-54` evidence that the played MJ has no history at all; K2
   and why shape parity was deferred rather than taken.

6. **Deferred-decisions register.** Add D-0052-shape, D-0052-mj, and D-0052-repetition to the
   `## Deferred decisions` list in `ARCHITECTURE_DECISIONS.md`, each with its reactivation
   trigger as stated in TICKET-0052. Update `DECISIONS_INDEX.md` accordingly.

## Scope OUT

- **Acting on any of the three deferrals.** Naming them is the whole of the job here.
- **Adding a `window_active` column** to `observation_run` to make old and new runs
  distinguishable. Tempting, and wrong for this brief: it is a schema change, it has no reader
  beyond a report footnote, and D already settled the question by labelling instead.
- **Re-running the pre-0052 metrics.** D.
- **Changing `NGRAM_N` / `NGRAM_WINDOW`** (`scripts/observation_metrics.py:69-72`) or any
  metric definition. Changing the instrument in the same chantier that changes the system
  makes both unmeasurable.
- **Widening the new check to assert anything about the played lane's prompt shape.** Rule 2
  bounds where the window may be implemented; it does not police how `play.py` composes its
  turn.

## Invariants to defend

- **Fail-closed over advisory.** Every rule fails on zero candidates. A check that passes
  because it found nothing to look at is the failure mode this project has hit before
  (`function_length.py` at TICKET-0038, the comment-anchored slices at TICKET-0043). Rule 4 in
  particular must fail if `_generate_mj_narration` cannot be located.
- **Structural over disciplinary.** H1 is currently a comment. After this brief it is a check.
  The difference is the point of the brief.
- **History is sacred.** The metrics labelling adds context to past runs; it does not delete,
  rewrite, or recompute them.

## Done means

- [ ] Mini-RECON (1)-(3) reported with `file:line`, including the decision on whether the new
      rules live in a new check or extend the existing `observation_runner.py` check.
- [ ] Every rule red-tested individually: paste the FAIL verdict produced by deliberately
      breaking each of rules 1-5 in a scratch copy, then confirm green after reverting. Five
      red verdicts, five reverts.
- [ ] The round-trip assertion (item 2) fails when `_lines_to_played` is made lossy in a
      scratch copy.
- [ ] `python -m tooling.verify.run` green on the full tree — not just the new check.
- [ ] Live gate executed per item 3, with all three captures pasted, including the
      `conversation_summary` call count.
- [ ] A default 30-beat run still behaves as before 0052.
- [ ] `scripts/observation_metrics.py` prints the "sans fenetre" guard on every run.
- [ ] `ARCHITECTURE_DECISIONS.md` section and the three deferrals present;
      `DECISIONS_INDEX.md` updated.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — items 5 and 6 above.
- `DECISIONS_INDEX.md` — the three D-0052 entries.
- `CLAUDE.md` — one line naming `observation_window_parity.py` and what it guarantees
  (single window implementation; the MJ narration is structurally excluded).
- No schema changelog entry (no schema change anywhere in TICKET-0052).
