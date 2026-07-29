# BRIEF-0052-b — Step "observation window adapter"

## Context

TICKET-0052, decisions G2 + I2 + J1 + H1 + K2. BRIEF-0052-a made the window seam
lane-neutral. This step gives the observed lane a window: beats are projected onto `TurnLine`,
resolved PER NPC (G2, mirroring the played lane, and required by J1's per-NPC scene tail), and
the resulting transcript replaces the raw one at the intent call and the act-line call only
(H1). The prompt SHAPE does not change (K2) — the observed prompts keep their single
`{transcript}` blob; only the lines composing it are windowed.

`observation_runner.py` is at 658 lines against a 1000 hard cap and the adapter is a
distinct concern, so it lands in a new module rather than growing the runner — the same
reasoning that put the window in its own module at TICKET-0050 (G1).

## Mini-RECON (report before changing anything)

Report findings with `file:line`. Report only; fix nothing outside Scope IN.

1. `assemble_scene_tail` (`context.py:580`) — confirm empirically what it produces when
   called with `player_condition=""` and `gathering_id=None`, for an NPC in an observed run's
   location. Construct the call in a scratch script against the live DB (read-only) and paste
   the ACTUAL rendered string. Specifically: does `_npc_context_setting` emit a dangling
   player-condition label, or nothing, when the condition is empty? Do not answer from reading
   the code alone.
2. Confirm whether an observed run has a `gathering` at all. `run_one_beat` never passes a
   `gathering_id` to `assemble_npc_context` (`observation_runner.py:435`, `:466`). Report
   whether `ObservationRun` carries any gathering reference, and confirm `None` is the correct
   argument.
3. Report the exact per-beat token/word profile of a real run: for the most recent
   `observation_run`, the word count of `_intent_transcript` at each beat index. This is the
   empirical anchor for the E1 dormancy claim (the ticket estimates 25-35 words per beat from
   the prompt constraint at `observation_runner.py:62-63` — confirm or correct it).
4. Confirm the current call signature and call sites of `_intent_transcript`
   (`observation_runner.py:283`), and that `observation_runner.py:427` is its only producer
   per beat.

## Scope IN

1. **New module `src/world_engine/observation_window.py`.** Docstring: this is the observed
   lane's adapter onto `context_window`'s shared seam (TICKET-0052, G2/I2/K2). It reads and
   computes only — it writes no row, canon or otherwise. It must not import any `cockpit`
   module (core never imports the UI layer, the rule already stated at
   `observation_runner.py:334-339`).

2. **Beat projection, per NPC (G2).**

   ```python
   def beats_to_lines(beats, viewer_npc_id: str, db: Session) -> list[TurnLine]:
       """Project prior beats onto the neutral line form FROM ONE NPC'S POINT
       OF VIEW (TICKET-0052, G2 — the played lane resolves per NPC, so the
       observed lane does too).

       Role mirrors the played lane's convention: the viewer's own prior
       lines are 'assistant', every other line is 'user'. Label is the
       speaker's entity name followed by ' :', matching the existing
       _intent_transcript rendering byte for byte. An injected event beat
       (outcome == 'event') keeps its raw line with an empty label and role
       'user' — it is creator narration, not an NPC speaking.
       """
   ```

   Skip beats with `line is None`, exactly as `_intent_transcript` does. Resolve entity names
   with the same per-call memo dict the current function uses, so a run with many beats does
   not re-query one name per beat.

   **Byte-identity requirement:** for a viewer with no prior lines of its own,
   `render_transcript(beats_to_lines(beats, viewer, db))` must equal
   `_intent_transcript(beats, db)` exactly. That equality is the proof the projection changed
   nothing but the shape. Assert it in the verify check (BRIEF-0052-c).

3. **The windowed resolver.**

   ```python
   def resolve_observation_transcript(
       *, world_id: str, npc_id: str, location_id: str,
       beats, db: Session,
   ) -> str:
       """The observed lane's counterpart to context_window.
       resolve_npc_message_list. Returns a STRING (K2 — the observed prompts
       keep their single {transcript} blob shape; only the lines composing it
       are windowed). Same config row, same budget, same K, same
       summary_enabled gate as the played lane (C1, E1)."""
   ```

   Body, mirroring `resolve_npc_message_list` step for step:
   - `cfg = load_conversation_window_config(world_id, db)`
   - `lines = beats_to_lines(beats, npc_id, db)`
   - below `cfg.word_budget` (`line_word_count(lines)`), return `render_transcript(lines)`
     unchanged — pre-0052 behaviour exactly;
   - above budget: `older, recent = split_verbatim_tail(lines, cfg.verbatim_turns)`; render
     `recent`; if `cfg.summary_enabled`, prepend
     `format_summary_note(summarize_older_lines(older, world_id, db))` plus a blank line
     when the note is not `None`;
   - then append the scene tail (item 4) as a final block, separated by a blank line — the
     played lane's tail is the model's LAST read, so the observed one must be too.

   The cap and the tail apply on the over-budget condition alone, independent of
   `summary_enabled`; the summary is an additional recovery layer on top. This is
   BRIEF-0050-b/-d's split, restated, not re-decided.

4. **Scene tail (J1).** Call `assemble_scene_tail(npc_id, location_id, gathering_id=None,
   player_condition="", session=db)`. `player_condition=""` is correct because
   `player_presence` is `absent` — the only implemented value (TICKET-0051, H2). If mini-RECON
   (1) shows an empty condition produces a dangling label, REPORT IT and stop: that is a
   `context.py` change, and `context.py` is at 979 of its 1000-line cap. Do not fix it here.

5. **Wire the two sanctioned sites, and only those (H1).** In `observation_runner.py`,
   `run_one_beat`:
   - the intent loop (`observation_runner.py:435`) — each NPC's `request_intent` receives
     `resolve_observation_transcript(world_id=run.world_id, npc_id=npc_id,
     location_id=run.location_id, beats=prior_beats, db=db)` instead of the shared
     `transcript`. One resolution per NPC per beat (G2).
   - the act-line call (`observation_runner.py:465-469`) — `_generate_act_line` receives the
     resolution computed for `arb.selected_npc_id`. Reuse the value already computed for that
     NPC in the intent loop rather than recomputing it; a second resolution would mean a
     second summary call for the same input in the same beat.

6. **`_generate_mj_narration` is NOT wired (H1).** It keeps the raw `_intent_transcript`
   value. Add one comment above the call at `observation_runner.py:468`:

   ```
   # H1 (TICKET-0052): the MJ narration deliberately keeps the RAW transcript.
   # The played MJ narrator has no history at all (play_stream.py:51-54 sends
   # [system, one user message]), so there is no MJ window to mirror. Named
   # deferral D-0052-mj. Do not "fix" this by routing it through the seam.
   ```

   `_intent_transcript` therefore stays in `observation_runner.py` and keeps its single
   remaining reader. Do not delete it.

## Scope OUT

- **Changing the observed prompt shape.** K2 stands: no role-alternating message list, no
  splitting the blob into per-line messages. That is D-0052-shape, deferred until F1's
  measurement has isolated the repetition cause — adopting it now would confound that
  measurement. This is the single most likely temptation in this brief.
- **Any repetition remedy.** No `repeat_last_n` change, no anti-repetition instruction added
  to `_NPC_INITIATIVE_ACT_FALLBACK` or the `observation_intent` / `npc_initiative_act`
  templates, no "tu t'es deja exprime ainsi" note. D-0052-repetition. The ticket is explicit
  that it does not fix repetition.
- **Lane-specific config.** No new column, no observation row, no composite trigger. C1 + E1.
- **`context.py`.** 979 of 1000 lines. `assemble_scene_tail` is consumed as-is.
- **`analyzer_transcript.py` and `_analysis_transcript`** (`observation_runner.py:567`). The
  analysis pass reads the FULL run by design (it is a post-hoc judge, not a model context) and
  its `[PNJ]` contract is frozen. Do not window it.
- **`max_beats` default.** Stays 30 (`observation_runner.py:202`). The over-budget live gate
  is obtained by passing a larger value per run, not by changing the default.
- **Deleting `_intent_transcript`.** It still serves the MJ narration.

## Invariants to defend

- **Exclusion is structural, never instructional.** `assemble_npc_context` remains the sole
  disclosure authority for what an NPC knows; the windowed transcript carries only lines that
  were already spoken in the open, in front of the whole present audience. The window narrows
  what reaches the model — it must never widen it. In particular, `beats_to_lines` must not
  reach for anything beyond `beat.line`, `beat.actor_id`, and `beat.outcome`.
- **E2 (worst-case listener) is untouched.** Disclosure gating stays where TICKET-0051 put it,
  in the audience computation feeding `assemble_npc_context`. Nothing in this brief may
  compute an audience.
- **Model proposes, code judges.** The summary is a prompt artifact. It reaches no
  `proposed_mutation`, no canon row, and is never persisted (C1) — `summary_not_persisted.py`
  guards the seam module; this module must stay equally write-free.
- **No structure without a reader.** `beats_to_lines`' `role` field has a reader only under
  K1 (deferred). Under K2 the rendered blob ignores `role`. State this explicitly in the
  module docstring: `role` is populated for the played lane's converters and for D-0052-shape,
  and is currently unread on the observed path. If that reads as speculative structure, say so
  in the report rather than deciding unilaterally.

## Done means

- [ ] Mini-RECON findings (1)-(4) reported with `file:line`, including the pasted rendered
      scene tail from (1) and the per-beat word profile from (3).
- [ ] `observation_window.py` exists, imports `context_window`, imports no `cockpit` module.
- [ ] Byte-identity holds: for a run's beats and a viewer with no own lines,
      `render_transcript(beats_to_lines(...)) == _intent_transcript(...)`. Demonstrated by a
      scratch run against a real `observation_run`, verdict pasted.
- [ ] `python -m tooling.verify.run` green.
- [ ] Live, default run (`max_beats=30`): behaviour indistinguishable from before. Beats
      still act, intents still log, no summary call fires. Confirm by the absence of a
      `conversation_summary` call in the log.
- [ ] Live, over-budget run (`max_beats=60`): the cap engages. Paste, for one beat above
      budget, the transcript actually handed to `request_intent` — it must show the summary
      note, the last K lines, and the scene tail last.
- [ ] The MJ narration on that same over-budget run (started with `mj_narration=true`) still
      receives the full transcript — H1 confirmed by observation, not by reading the comment.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `CLAUDE.md`: one line — the observed lane windows its transcript through
  `observation_window.resolve_observation_transcript`, sharing the played lane's config row;
  the MJ narration is deliberately excluded.
- No schema changelog entry.
- `ARCHITECTURE_DECISIONS.md`: BRIEF-0052-c writes the section.
