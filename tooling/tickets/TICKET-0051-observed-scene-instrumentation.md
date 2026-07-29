---
id: TICKET-0051
title: Observed NPC scene - universal opportunity loop with decision instrumentation
type: feature
status: brief
created: 2026-07-27
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0051-a, BRIEF-0051-b, BRIEF-0051-c, BRIEF-0051-d, BRIEF-0051-e, BRIEF-0051-f, BRIEF-0051-g]
schema_version_touched: v1.90
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> J'aimerais pouvoir "observer" des NPC jouer entre eux. Je pense que l'on peut
> reutiliser le tick. Je regarde dans une piece des NPC prendre des actions. J'ai
> l'impression que contrairement a ce que nous avons en ce moment (le MJ donne
> l'initiative a une seule personne), il devrait offrir l'opportunite a tous les
> NPC presents d'agir s'ils le veulent. Je pense qu'il faut faire attention a
> l'intensite des relations parce que en ce moment, un personnage avec une
> intensite tres faible ou tres forte va juste toujours prendre l'initiative au
> depend des autres NPC. Je ferais cela en trois etapes :
> 1- Mettre en place le fait que je puisse etre observateur seulement
> 2- Je voudrais pouvoir collecter les transcripts de la discussion avec
>    decisions prises par les differents agents
> 3- Analyse des transcripts
> 4- Amelioration du systeme de prompt/jeu.

Later, on scope and intent:

> Je ne joue plus le monde pilote, mon intention est d'essayer une boucle
> complete, me creer un monde, le peupler puis le jouer et le regarder jouer.
> [...] Je voudrais aussi tester s'il y a une evolution dans la scene ou
> facilement les NPC sont plus passifs.

And on mutation visibility:

> Je veux pouvoir voir les mutations que l'on me propose [...] assure-toi que je
> puisse en voir le resultat quelque part.

**English gloss.** Build a scene the creator watches rather than plays: NPCs in
one room act among themselves, every present NPC gets the opportunity to act
each beat, relation intensity no longer monopolizes initiative, and every
agent decision (acted or not, and why not) is recorded for later analysis.

## Clarifications resolved (intake)

Two reframings were accepted before any decision block:

- **The "tick" requested here is NOT `run_world_tick`.** The world tick is
  per-NPC, off-screen, interval-driven, and emits `proposed_mutation` rows. What
  is requested is the `/say` loop MINUS the player, with a clock in place of the
  input: different cadence, different output, different context builder.
  `tick.py` / `tick_context.py` / `tick_normalize.py` are NOT touched by this
  ticket. The unit of time here is a **beat**, never a tick.
- **Transcript instrumentation is not a later step.** Nia's step 2 is folded
  into step 1: a loop that runs before the decision tables exist produces
  unmeasured runs that must be re-executed. Instrumentation is a "Done means"
  of the first brief.

Locked decisions:

| Code | Decision |
|---|---|
| **A3** | Observed scenes get their OWN tables (`observation_*`). `conversation` is NOT touched. Superseded A2 (a `conversation.mode` column) after RECON: `Conversation.player_id` is `nullable=False` (`models/ephemeral.py:94`) with 49 read sites, several using it as a DEFAULT identity (`analyzer.py:258`, `analyzer.py:275`) - making it nullable would be disciplinary safety, not structural. |
| **A3-adapter** | `analyze_window` / `analyze_overhearing` are reused by projecting beats into an in-memory transcript. No `conversation_message` row is ever written by an observed run. No duplicated analysis logic. |
| **B2 + B1** | Bounded run ("execute N beats"), transcript read cold afterwards. Single-beat stepping available. No real-time auto-play. |
| **C3** | One short JSON intent call PER present NPC per beat (`{act, urgency, target, why}`), then the CODE orders and selects. Not one MJ call returning an actor. Conforms to "model proposes, code judges". |
| **D1+D2+D3** | Intensity hinting leaves the prompt and becomes a code-side propensity; a cooldown excludes/penalizes the previous beat's actor; a speaking-debt term prefers the least-recently-active NPC at comparable urgency. No RNG (D4 not taken). |
| **D-nonneg** | Silence is a LOGGED outcome, never an absence. |
| **E2** | Disclosure gating uses the WORST-CASE listener present, not the addressee alone. Fail-closed with a plural audience. |
| **F3** | Observed runs DO produce proposals, marked and structurally isolated from the normal Review Queue - never merely hidden by a UI flag. |
| **F3-visible** | Isolation is not invisibility: the creator must be able to see an observed run's proposals on a dedicated surface (BRIEF-0051-e). |
| **G1** | Runs execute against the live world DB. Justified: the pilot world is retired; the new world IS the sandbox. Consequence assumed: that world becomes the real one, so F3's isolation must be structural from the first brief. |
| **H2** | `player_presence` is a closed vocabulary (`absent` / `silent` / `active`), not a boolean. Only `absent` is implemented; `silent` and `active` are named deferrals. A silent player still counts as an AUDITOR for E2 - unrepresentable with a boolean. |
| **I** | Opportunity is universal, speech stays sequential: one actor per beat, transcript linear, each actor sees all prior lines. |
| **J2** | Deterministic instruments only (n-gram overlap against prior beats, proposal counts as an "something happened" proxy). |
| **K2** | The creator can inject an event line at a chosen beat. Same run, with and without a perturbation at beat 15, is the experimental lever. |
| **L (reduced)** | Bit-exact replay is abandoned (the world mutates under play; G1). What is KEPT is attribution: arbitration parameters and per-usage template `id` + `version` are pinned on the run, relationally, and are VISIBLE on the run detail surface. `seed` and the world fingerprint are dropped - a sensor whose verdict is always "changed" does not inform. |
| **M (corrected)** | Three tables: run / beat / intent. Two corrections applied against the drafted shape: **M1** - `not_selected_reason` is NOT stored; the arbitration COMPONENTS are stored and the reason is derived by a documented precedence, so the judgment is reconstructible and not just its verdict. **M2** - `beat_outcome` is explicit; a null actor must never conflate "nobody wanted to act" (datum) with "all intent calls failed" (bug). |
| **N** | `observation_` prefix throughout. `scene` already carries two meanings in this codebase (`conversation.scene_state`, `ResponseMode.scene`); a third would be ambiguous. |
| **O1** | Propensity ships `flat` by DEFAULT: intensity plays no part, only the model-reported urgency. `relation_weighted` exists as the second mode but is not the default. Rationale: damping the U-curve immediately would fix the bias BEFORE measuring it, leaving cooldown / debt / curve indistinguishable as causes. The A/B run decides. |
| **P1** | The observation surface is a TOP-LEVEL surface, sibling of Jouer and Creation - not a sub-surface of Play, not a separate port. |
| **Q** | Metric set locked: acted-beat share per NPC (+ entropy), intent rate per NPC, selection rate given intent, silence rate, degraded rate, correlation between `abs(intensity - 50)` and act rate, n-gram overlap of each line against the prior N beats, proposals per run, latency p50/p95. All nine are derivable from the BRIEF-0051-a socle - verified, no retroactive schema change. |
| **R1** | Observed runs reuse the SAME analysis judge as played scenes, via a transcript-shaped seam extracted into a new module. Forced by RECON: `analyze_window` (`analyzer.py:894`) and `analyze_overhearing` (`analyzer.py:679`) are conversation-bound by signature AND internals - `analyze_window` loads the `Conversation`, reads `ConversationMessage` rows and advances `conv.last_analyzed_turn`; `_overhearing_eligible_receivers` (`analyzer.py:443-456`) derives receivers from `conv.gathering_id` and `conv.player_id`. There is no transcript seam to adapt to. Rejected: a duplicate observation-side analyzer (two judges drift, and step 3's conclusions would stop describing the real game), and dropping observed proposals entirely (loses J2's "something happened" proxy and contradicts the visibility requirement). |
| **D-J1** | **Named deferral.** LLM judge scoring line novelty/quality. Reason for deferral: putting a model inside the MEASUREMENT loop while isolating causes adds a confounder. Reactivation: once J2 has shown its blind spots on passivity modes (b) and (c), not before. |

Brief sequence:

- **-a** Socle: tables, write helpers, canon-policy note, verify check, migration.
- **-b** E2: decouple disclosure intensity from interlocutor intensity in `context.py`.
- **-c** Analysis seam: extract a transcript-shaped core out of `analyzer.py` (R1).
- **-d** Engine: per-NPC intent call, code-side arbitration D1+D2+D3, score components persisted.
- **-e** Runner: bounded run, `beat_outcome`, quiescence stop, fail-closed readiness gate, F3 proposal production via the -c seam.
- **-f** Cockpit: launch, transcript reading, MJ toggle, K2 event injection, run detail (pinned params + templates) and observed-proposal surface.
- **-g** J2 metrics: export script and computation.

`-b` and `-c` are independent of `-a` and of each other; either may land first.
`-c` touches a hot canon-adjacent path: commit before starting, isolated brief,
full-tree verify after.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The five `observation_*` tables exist with their exact columns AND their CHECK constraints asserted from `sqlite_master` DDL text, not by column presence alone  -> verify/checks/observation_socle.py
- [ ] No `observation_*` table name appears in `canon_write_policy.txt` `[CANON_TABLES]`  -> verify/checks/observation_socle.py
- [ ] Every write to an `observation_*` table goes through `observation_writes.py`; the model identifiers appear in no other module outside the declared allowlist  -> verify/checks/observation_socle.py
- [ ] The normal mutation queue reader excludes observed-run proposals with a NULL-safe predicate  -> verify/checks/observation_socle.py
- [ ] `not_selected_reason` exists as no column in any `observation_*` table (M1: derived, never stored)  -> verify/checks/observation_socle.py
- [ ] An observed run writes zero `conversation_message` rows and zero `conversation` rows  -> verify/checks/observation_socle.py
- [ ] `tick.py`, `tick_context.py`, `tick_normalize.py` contain no reference to any `observation_*` identifier  -> verify/checks/observation_socle.py
- [ ] Every intent call is recorded with a `call_status`, including failures - a failed run has intent rows, not missing ones  -> verify/checks/observation_socle.py
- [ ] Schema version agreement holds at v1.90  -> verify/checks/schema_version_agreement.py
- [ ] `analyzer_transcript.py` never reads a `Conversation`/`ConversationMessage`, never commits, and carries a refusable `AttributionContext`; `analyzer.py`'s wrapper signatures are unchanged and set `conversation_id` on every returned mutation  -> verify/checks/analyzer_seam.py
- [ ] The observation runner writes only through `observation_writes.py`, never infers `outcome` from `actor_id` truthiness, produces `degraded` (not `silence`) when every intent call fails with a full intent-row set, refuses a readiness-gate failure with zero `observation_run` rows, writes zero `conversation`/`conversation_message` rows, isolates its proposals from `list_mutations` while linking them via `observation_mutation_link`, and never leaves a run `status='running'` after `run_bounded` returns (including on exception)  -> verify/checks/observation_runner.py
- [ ] Full-tree verify passes (`function_length`, `module_budget`, `import_cycle`, `json_ui_boundary`, `single_canon_write`)

### Live  ->  human gate (Nia)

- [ ] A 5-NPC / 30-beat run completes and its transcript is readable end to end.
- [ ] The run refuses to start when a present NPC has no active goal, or when fewer than 2 NPCs are present, and says which condition failed.
- [ ] For a beat where nobody acted, the intent table distinguishes "no NPC wanted to act" from "the calls failed".
- [ ] An NPC that acted at beat N does not act at beat N+1 unless every other candidate declined.
- [ ] Two NPCs with extreme relation intensity toward each other do not capture the run: no single NPC holds more than roughly half the acted beats in a scene of 5.
- [ ] Injecting an event at beat 15 visibly changes what follows.
- [ ] The run detail surface shows the arbitration parameters and the template id/version used, so two runs are comparable.
- [ ] The proposals produced by an observed run are visible on their own surface, and DO NOT appear in the normal Review Queue.
- [ ] A run executed with `mj_narration` off produces raw NPC lines only, with no MJ model call.
