---
id: TICKET-0052
title: Observation context window parity - shared window seam for the observed lane
type: feature
status: live-gate
created: 2026-07-29
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0052-a, BRIEF-0052-b, BRIEF-0052-c]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je veux que la fenetre d'observation reflete la verite du jeu. Je veux qu'on inclus la
> fenetre, meme si elle ne reglera pas mon probleme de repetions.

Preceded by the observation that motivated the investigation:

> dans mes observations, il commence a y avoir des reponses qui se ressemble a partir du beat 8

**English gloss.** The observed lane (TICKET-0051) assembles its NPC context by a path of
its own, unrelated to the sliding window TICKET-0050 built for the played lane. This ticket
makes the two lanes share one window, so that anything measured in an observed run describes
the game as actually played. It is explicitly NOT a repetition fix.

## Findings that motivated the ticket (RECON against `main`, fresh tarball)

1. **No coupling exists today.** `conversation_window` has exactly two importers:
   `cockpit/play.py:32` (`resolve_npc_message_list`) and `cockpit/crud/prompts.py:19` (the
   config surface). No `observation_*` module references it.
2. **The observed lane builds an uncapped transcript.** `_intent_transcript`
   (`observation_runner.py:283-300`) concatenates every prior beat via `_prior_beats`
   (`observation_runner.py:242`, no LIMIT) into a flat `"Name : line"` string, injected at
   three sites per beat: the intent call (`observation_engine.py:329`), the act-line call
   (`observation_runner.py:360`), and the MJ narration (`observation_runner.py:394`).
3. **No artifact of TICKET-0051 references TICKET-0050.** This was an unnamed gap, not a
   recorded deferral.
4. **The window will rarely fire under E1, and that is accepted.** An acted beat is capped at
   "1 a 2 phrases" (`observation_runner.py:62-63`), roughly 25-35 words; `word_budget` is 1200
   (`models/config.py:36`). A 30-beat run (`max_beats` default, `observation_runner.py:202`)
   lands near 750-1200 words. Fidelity, not triggering frequency, is the goal - see E1.
5. **The played MJ narrator has no history at all.** `_say_stream_mj_narration`
   (`play_stream.py:51-54`) sends `[system, one user message]`; `_build_mj_user`
   (`play_stream.py`) composes the current turn only. There is no MJ window in the played
   lane to mirror. The observed lane's MJ narration currently receives MORE than the played
   one - see H1.

## Clarifications resolved (intake)

| Code | Decision |
|---|---|
| **A3** | Full parity: K-verbatim cap AND the sliding summary, not the cap alone. |
| **B1** | Generalize the existing module into a lane-agnostic seam rather than have the observed lane import a conversation-named module. |
| **C1** | One `conversation_window_config` row per world serves both lanes. No observation-specific config values. The table keeps its name - renaming it would be a migration with no reader. |
| **E1** | Word budget only, exactly as the played lane. No composite `OR beats > K` trigger. Rationale on record: the window must fire when the game's window fires, and not otherwise; a lane-specific trigger would reintroduce the divergence the ticket exists to remove. Accepted consequence: the compression branch is dormant in a default 30-beat run. |
| **F1** | The repetition onset is investigated by MEASUREMENT first (`scripts/observation_metrics.py`, `per_beat_overlap`), in a separate workstream. This ticket does not attempt a repetition fix and must not be evaluated as one. |
| **D** | Metrics already produced by BRIEF-0051-g are NOT re-run. They are labelled "sans fenetre" as an assumed baseline. |
| **G2** | Per-NPC resolution, mirroring the played lane, not one shared resolution per beat. Coupled to J1: `assemble_scene_tail` takes `npc_id` and produces a per-NPC tail, which a shared resolution could not produce. Accepted cost: N summary calls per over-budget beat. |
| **I2** | The seam operates on a lane-neutral line form carrying an explicit label; both lanes adapt to it. Forced by the fact that `_render_older_transcript` labels by `role` alone and states it "carries no per-NPC name" - the observed lane has names and no player. |
| **J1** | `assemble_scene_tail` is reused; `player_condition=""` when `player_presence='absent'`. No observation-specific tail. |
| **H1** | The window applies to the intent call and the act-line call ONLY. `_generate_mj_narration` keeps its raw transcript, untouched. Rationale: the played MJ has no history, so there is no MJ window to mirror; and `mj_narration` is opt-in (`observation_runner.py:204`, default `False`), display-only (`observation_reads.py:135`), and feeds no measured path. |
| **K2** | The observed prompts keep their current SHAPE - a single `{transcript}` blob in one user message. The window applies to the lines composing that blob. Full shape parity (a role-alternating message list, own lines as `assistant`) is deferred: adopting it here would change model behaviour for reasons unrelated to windowing and confound F1's repetition measurement. |

## Named deferrals opened by this ticket

- **D-0052-shape** - full prompt-shape parity for the observed lane (K1: role-alternating
  message list instead of a single blob). Reactivate only after F1's measurement has isolated
  the repetition cause, so the two changes are never confounded.
- **D-0052-mj** - the observed MJ narrator receives the full transcript while the played MJ
  narrator receives none. Deliberately unchanged (H1). Reactivate if `mj_narration` ever
  becomes an input to a measured path.
- **D-0052-repetition** - the beat-8 repetition onset itself. Fed by F1. `repeat_last_n=256`
  (`ollama_client.py:30`) was calibrated for played turns (its own comment says "3-4 turns")
  and has never been revisited for 25-35 word beats; this is a hypothesis for that workstream,
  not a decision here.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `src/world_engine/conversation_window.py` no longer exists; `context_window.py` exists
      and exposes the neutral seam  -> verify/checks/observation_window_parity.py
- [ ] Every consumer anchored on the old module path is updated: `prompt_registry.py:39`
      (WIRED_FILES), `prompt_registry.py:264` (call_sites), `summary_not_persisted.py:17`
      (MODULE)  -> existing prompt_registry.py + summary_not_persisted.py, both must still pass
- [ ] `summary_not_persisted.py` is vacuous-proof: a missing MODULE file fails, never passes
      silently  -> verify/checks/summary_not_persisted.py (red-tested)
- [ ] The observed lane's intent and act calls resolve their transcript through the shared
      seam; no second cap/summary implementation exists under `src/`
      -> verify/checks/observation_window_parity.py
- [ ] `_generate_mj_narration` does NOT call the seam (H1 asserted structurally, not by
      comment)  -> verify/checks/observation_window_parity.py
- [ ] `context.py` gains no new lines (currently 979 of the 1000 hard cap);
      `observation_runner.py` stays under budget  -> existing module_budget.py
- [ ] Played-lane behaviour is byte-identical: the message list produced for a given
      `npc_history` before and after the seam extraction is equal
      -> verify/checks/observation_window_parity.py round-trip assertion

### Live  ->  human gate (Nia)
- [ ] A default run (`max_beats=30`) behaves exactly as before this ticket - the window is
      below budget and changes nothing observable.
- [ ] A deliberately over-budget run (`max_beats=60`, no code change needed -
      `routes/observation.py:37` has no upper bound) shows the cap engaging: the transcript
      reaching the intent call is the summary note plus the last K lines, not the full run.
- [ ] A played conversation still behaves as before: NPC replies, summary fires above budget
      exactly as it did on TICKET-0050's live gate.
- [ ] The metrics report for pre-0052 runs is labelled "sans fenetre" (D).
