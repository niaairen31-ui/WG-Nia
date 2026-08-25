---
id: TICKET-0075
title: Day resolution chain — Batch/PassPlay reactivation
type: feature
status: escalated
created: 2026-08-24
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
brief_ids: [BRIEF-0075-a, BRIEF-0075-b-plan-emission-budget, BRIEF-0075-b-amendment-1-location-reachable-reader, BRIEF-0075-c, BRIEF-0075-d-resolution-narration, BRIEF-0075-d-amendment-1-no-direct-step-write, BRIEF-0075-e-mutation-emission-day-account, BRIEF-0075-e-amendment-1-delta-source-rendezvous, BRIEF-0075-f-reconciliation-closure, BRIEF-0075-g-feasibility-veto]
schema_version_touched: v1.93
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je veux pouvoir faire un jeu qui permet au joueur d'écrire ce qu'il veut faire
> dans la journée, il y a une phase de résolution où le prompt du ou des joueurs
> est résolu contre le lore et la réponse des autres joueurs (le cas échéant)
> pour qu'il ait une réponse. Cette réponse doit comporter les éléments
> suivants :
> - Une description en prose de ce qui s'est passé dans la journée,
> - Une liste des NPC avec lesquels tu as interagi
> - Une liste des lieux dans lesquels tu es allé.
> - Est-ce que tu as gagné des ressources, des objets ou des compétences ?
> - autres choses à ajouter plus tard (un peu tout ce qui est mutable par AI
>   j'imagine)

> Écriture initiale, des extractions analysées dans un ordre logique qui résout
> contre du code ou un autre AI, puis, s'il y a lieu, une réécriture de la prose
> pour inclure le nouvel élément. J'aimerais que la journée ne soit pas
> forcément un beat, mais se construise avec plusieurs beats consécutifs.
> [...] L'AI analyse les intentions du joueur et les étapes nécessaires pour
> faire cela. L'AI fait un plan préliminaire en étapes pour accomplir cet
> objectif. [...] Le but est de savoir combien d'étapes il peut réalistiquement
> faire avec ses connaissances, ses ressources, ses contacts... On réalise
> l'étape « trouver un contact » par exemple. Et c'est cela qui est décrit au
> joueur. Le joueur fera une petite session de discussion avec ce contact lors
> de sa prochaine connexion.

> Concernant la construction du monde et des NPC pertinents. Je peux toujours
> créer une base, mais rien ne m'oblige à avoir une liste exhaustive de NPC
> depuis le début. Par exemple si un joueur cherche un marchand de fleurs, il
> serait surprenant que j'en aie un de créé.

> Pour le moment, je suis plus intéressée par une bonne qualité de réponse
> qu'un temps de réponse acceptable. J'utilise un modèle abliterated qui
> n'apprécie pas particulièrement les contraintes négatives (ne les suit pas).

## Clarifications resolved (intake)

Design conversation, 2026-08-24. Codes are the locked form.

**Resolution posture**

- **A1** — asynchronous resolution, creator in the loop. The player submits, the
  batch resolves, it produces prose plus proposed mutations, Nia reviews, and
  only then does the player see the day. Zero new authority for the model.
- **O1** — no auto-approve in this ticket. Every mutation from a resolution
  enters the queue at `proposed`. The auto-approve mechanism and its whitelist
  are a separate, later ticket.
- **Declaration immutability** — the declaration is immutable, the resolution is
  replayable, history is append-only. Rejecting a resolution re-runs the chain
  on the same `declared_action`; the prior attempt stays in `PassPlay.history`.
  A player never replays a day, only plays the next one.

**Chain shape**

- **B4** — initial engine narration, then extraction passes analysed in a
  logical order and resolved against code or a specialised model, then a
  CONDITIONAL rewrite of the prose to seat a late-discovered element. Two
  distinct writings exist and must not be conflated: the PLAYER's declaration
  (never rewritten, it is history) and the ENGINE's narration (the only thing
  the rewrite pass touches).
- **T1** — the rewrite pass is a net, not a step. It receives a FROZEN FACT
  SHEET (rolls, ids, outcomes) plus the single authorised delta. A Python judge
  verifies the output fail-closed: proper nouns emitted are a subset of the
  authorised set, and every outcome on the fact sheet is still present. Same
  family as `llm_parse_chokepoint`.
- **Dice stay in Python.** `resolution.py` is the precedent; no model rolls.

**Plan and budget**

- **F1** — ONE plan emission. The model emits the full step list once, each step
  carrying structured `cost`, `requires` and `domain`. Python sums costs against
  the day budget and cuts. Rejected F2 (iterative "is step 1 feasible? then 1+2?"
  loop — N calls, non-deterministic cut, and the model drifts across a long
  chain) and F3 (the model cuts for itself — the model would be judging).
- **M1** — the four `SCHEDULE_PHASES` (`matin`, `apres-midi`, `soir`, `nuit`)
  ARE the budget slots. Budget unit and schedule key are the same unit, so
  "step 2 lands in the evening" answers "who is there in the evening" directly.
  Rejected M2 (separate abstract slots — a third time vocabulary) and M3
  (unifying the tick's `interval_label` too — good goal, separate ticket, it
  touches the tick).
- **P2** — every declared day gets the full four slots. `world.current_phase` is
  read for schedule resolution only; it does not shorten the budget. Chosen
  deliberately for the test phase, to see a COMPLETE day. Reactivation
  condition for P1 (budget starts at `world.current_phase`, so declaring late
  costs slots): once a full day has been observed end to end and the loop is
  trusted.
- **S1** — `requires` has exactly four forms in v1: `knowledge`, `relation_gte`,
  `resource`, `location_reachable`. `relation_gte` reuses `prereq_judge.py` as
  is; `location_reachable` reuses the door graph. The vocabulary is a Python
  constant guarded by a fail-closed check, and each form has a named evaluator.
  Rejected S2 (free-text prerequisites judged by a model) and S3 (cost only, no
  prerequisites — that would drop "do you have the contacts to find this
  person", which is the heart of the request).
- **H1** — player day-plans reuse `Agenda`/`AgendaStep`. No new plan table. The
  existing partial unique index (at most one ACTIVE step per agenda) supplies
  "the player pursues one step at a time" for free.
- **A plan covers one day.** Unconsumed steps stay `pending`; the agenda stands.
  If the player wants to continue tomorrow, they can — through R1.
- **R1** — plan reconciliation. The model classifies the new declaration against
  the standing agenda as `continue` / `modify` / `replace` and must justify by
  citing the step, but the EFFECT goes through `agenda_step_change`, hence
  through review. `replace` closes the old agenda `failed` and opens a new one;
  the old one stays. Rejected R2 (the player chooses explicitly in the UI —
  would expose the agenda) and R3 (always re-plan from scratch — no inertia,
  H1 loses its point).
- **The agenda is never exposed to the player.** The new surface must not become
  a back door to it.

**World-building during resolution**

- **C1** — the resolver never authors. Against an unresolved need, a
  concordance pass queries the registry; on a match it uses the canon id, and
  failing that the prose names a FUNCTION WITHOUT IDENTITY ("a flower seller set
  up near the east gate") and the engine emits an `entity_creation` germ
  carrying the hint. The NPC becomes canon when Nia realises it, and at that
  moment it WAS already there, which costs nothing narratively. Breaks no
  invariant; `_approve_entity_creation_shortcircuit` stays untouched.
  Rejected C2 (provisional canon sketch — an explicit exception to I2, would
  need a new entity status and a purge) and C3 (prose then find-replace as the
  PRIMARY mechanism — substituting a name does not substitute its implications;
  kept only as a net, which is what T1 is).
- **N1** — no NPC displacement prediction. The schedule IS the prediction. An
  NPC found off-schedule on arrival fails the step, and that is drama, not a
  bug. This honours the BRIEF-0074-a-amendment-1 wall: an agenda states an
  objective, never a place, and the resolution chain must never read an agenda
  for a position. Rejected N2 (the chain emits a `predicted_position` term —
  reopens a sealed accessor) and N3 (running the tick forward — expensive, and
  it would make the tick authoritative over the future).
- **K3** — the tick runs before resolution, preferentially on the locations and
  NPCs the plan touches, reusing the existing tick scoping. TICKET-0074 made
  that computable via `who_is_at`.

**Day identity**

- **L1** — the day IS the batch; the day number is its ordinal. No new world
  column, and it gives a reader to a dormant table, which is what the doctrine
  asks. Rejected L2 (`world.current_day` — a second temporal authority beside
  the deliberately inert phase) and L3 (no day counter, everything relative —
  fragile as soon as a rendezvous is at D+2).
- **Decision U (storage of that ordinal) is OPEN** and gates brief -a. `Batch`
  carries no ordinal column today, only `created_at`, with no uniqueness
  constraint. See the ticket's open-questions note below.

**Player-visible output**

- **I1** — a rendezvous is a pointer, not a scene: the day writes a `Knowledge`
  row plus an active agenda step naming the NPC and the location. On the next
  connection the UI reads the active step and OPENS the existing conversation
  surface, which the player plays at the keyboard. The day arms the scene; it
  never plays it. Rejected I2 (a `pending_scene` table — new structure for what
  an agenda already encodes) and I3 (pre-opening a `Gathering` — creates a
  meeting that has not happened yet and pollutes presence reads).
- **Q1** — a NEW, minimal Svelte surface (declare / read the account), sibling
  to `Creation` and `Observation`, following the `active`-prop mount pattern,
  independent of Play. A rendezvous conversation still runs in the legacy Play
  surface until TICKET-0069. Rejected Q2 (grafting onto legacy Play — adds
  legacy after the TICKET-0061 doctrine seal) and Q3 (API only — the chain
  could not be PLAYED).

**Mutation types emitted in v1**

`knowledge_change`, `relation_change`, `resource_change`, `agenda_creation`,
`agenda_step_change`, `entity_creation` (C1 germ). NOT `npc_move`: under N1 the
schedule is the positional truth, and a resolution-emitted move would create a
second positional authority.

**Derived, not separately decided**

A batch is created when a declaration is submitted. Solo play means one
`PassPlay` per batch.

## Scope OUT

Deviation from TEMPLATE.md, deliberate: named deferrals belong on the ticket,
not only in briefs. Flagged for reversal.

- Multiplayer. `batch_order`, cross-player resolution, and inter-player context
  partitioning are all out. One `PassPlay` per batch in v1.
- Auto-approve of any kind (O1), including a `schedule_change` mutation type.
- Player onboarding: D2 structural anchoring plus D1 Traveller-style questions,
  where every answer is a SELECTOR pointing at canon rows rather than free text.
- The 5-day playable prologue (D3). Named deferral. Reactivation condition: the
  resolution chain has resolved 20 consecutive days with no rewrite pass fired.
- P1 (budget starting at `world.current_phase`). Reactivation condition above.
- M3 (unifying the tick's `interval_label` with `SCHEDULE_PHASES`).
- TICKET-0069, the Play surface migration. Q1 must not preempt it.
- Any change to `schedule_reads.py`'s precedence tuples, to the sealed
  `where_is` dispatch, or to `PUT /api/world/phase`'s deliberately inert body.
- Prompt-injection defence. Structure only: reserve a `flagged` value on
  `PassPlay.status` and a nullable `flag_reason`, read by the existing review
  queue. No classifier, no filter, in this ticket.
- Lazy creation of LOCATIONS. NPC only in v1 — location creation carries the
  location tree, doors, geometry and four fail-closed checks. Symmetry is a
  later objective, not an assumption here.
- Comparing a played conversation against a simulated one. Cheap later
  (`analyzer.py` already extracts mutations from a played transcript), but out
  of scope.

## Invariants at risk

- **Model proposes, code judges.** F1's cut, S1's prerequisite evaluation and
  T1's judge are all Python. Any of the three drifting into a model call is the
  failure mode.
- **The resolver never authors** (C1 / I2). `entity_creation` stays a parked
  germ; approving one must still author nothing synchronously.
- **No structure without a reader.** This ticket exists partly to clear the
  standing `Batch`/`PassPlay` no-reader violation. It must not create a new one.
- **History is sacred.** `declared_action` is never updated; replays append to
  `PassPlay.history`; a replaced agenda closes `failed` rather than vanishing.
- **The positional wall** (BRIEF-0074-a-amendment-1). No agenda term reaches a
  positional read, and the chain adds no precedence term.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `Batch` and `PassPlay` each have at least one reader outside
      `models/__init__.py`; the no-reader violation is cleared
      -> verify/checks/pipeline_wiring.py
- [ ] A day has a stable, unique ordinal; two batches in one session cannot
      share it  -> verify/checks/pipeline_wiring.py
- [ ] No write path updates `PassPlay.declared_action` after insert; replays
      append to `PassPlay.history`  -> verify/checks/declaration_immutable.py
- [ ] The day budget is a declared Python constant; step costs are summed and
      cut in Python, with no model call on the cut path
      -> verify/checks/day_plan_budget.py
- [ ] The `requires` vocabulary is a closed constant of exactly four forms, each
      with a named evaluator; an unknown form fails closed
      -> verify/checks/day_plan_budget.py
- [ ] The rewrite pass is guarded: proper nouns emitted are a subset of the
      authorised set and every fact-sheet outcome survives; zero facts collected
      is a failure, not a pass  -> verify/checks/narration_guard.py
- [ ] Mutations emitted with `source_type='pass_play'` are drawn from the
      declared whitelist, `npc_move` is absent, and every row enters at
      `proposed`  -> verify/checks/passplay_mutation_types.py
- [ ] The chain reads no agenda for a position and adds no term to
      `schedule_reads.py`'s precedence tuples
      -> verify/checks/npc_schedule.py (extension)
- [ ] No API response reachable from the new surface carries an agenda payload
      -> verify/checks/day_surface_boundary.py
- [ ] Every check above is fail-closed and vacuity-guarded; zero items collected
      is a failure  -> corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] A full day, end to end: declare -> resolve -> review the queue -> read the
      account. The prose, the NPC list, the location list and the
      resource/skill deltas are all present and mutually consistent.
- [ ] The flower-seller case: a declaration needing an unknown NPC yields prose
      naming a ROLE, not a name, and an `entity_creation` germ waiting in the
      Creation tab. Realising the germ, then replaying, seats the named NPC.
- [ ] A rendezvous armed on day 1 is playable at the keyboard on day 2 through
      the existing conversation surface.
- [ ] Reconciliation, three ways: a day-2 declaration that CONTINUES the standing
      agenda, one that MODIFIES it, one that REPLACES it. The replaced agenda is
      still on file, closed `failed`.
- [ ] A plan whose prerequisites are unmet is cut short by the budget/prereq
      judge, and the account says so in prose without inventing the missing
      contact.
- [ ] An NPC found off-schedule fails the step, and it reads as drama.

## Docs to update

- `world-engine-schema-changelog.md`: entry at the next version, if U resolves
  to a schema change.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a section for the resolution
  chain, naming the two-writings distinction (player declaration vs. engine
  narration), the T1 judge, and the reaffirmed positional wall.
- `tooling/standards/DECISIONS_INDEX.md`: codes A1, B4, C1, F1, H1, I1, L1, M1,
  N1, O1, P2, Q1, R1, S1, T1, plus U once resolved.
- `CLAUDE.md`: only if the Q1 surface changes the frontend surface contract.

## Open questions gating brief -a

- **U — storage of the day ordinal.** `Batch` has `created_at` and no
  uniqueness. U1: `Batch.day_number: int NOT NULL` plus a unique index on
  `(session_id, day_number)`. U2: derive by row number over `created_at` — no
  migration, but the ordinal is never stable. U3: use `Session.number`, one
  batch per session — but a session is a period of play, not a world day, and
  `play.py:746` already creates sessions for conversations.
- Consequence: `schema_version_touched` and `danger_class` stay provisional
  until U is answered.
