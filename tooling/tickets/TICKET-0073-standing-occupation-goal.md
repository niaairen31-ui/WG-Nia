---
id: TICKET-0073
title: Standing occupation goals — npc_goal.kind, the POURQUOI TU ES ICI section, and the Creation-side editor
type: feature
status: live-gate
created: 2026-08-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0073-a, BRIEF-0073-b, BRIEF-0073-c]
schema_version_touched: v1.90 -> v1.91
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je pense que D2 est mieux, mais pas seulement pour le createur. Je pense que
> la partie activite devrais etre un objectif du NPC. Je m'explique : Lorsque
> je joue au jeu et que les NPC ont des objectifs qui ne sont pas ''normal'' ou
> ''social'', ils ont tendence a vouloir reussir a influance quelqu'un ou faire
> un traite commerciale ou... Je pense qu'il devrais y avoir un type d'objectif
> qui est lie a leurs occupations. Lorsque tu discute avec un NPC qui est a un
> endroit en raison de son horraire/calandrier, cette objectif devrais figure
> dans les prompts de ce NPC.

> pourquoi veux tu l'exclure de l'initiative? si le NPC est dans sa chambre a
> couche pour se detendre, est-ce que cela ne devrais pas influance directement
> comment il se comporte? Une occupation n'est pas forcement un travail, cela
> peut-etre son passe temps.

> on l'essaye comme cela mais j'ai l'impression que lorsqu'un scene va se
> prolonge, cela va nous creer des problemes. Si on dit a chaque prompt ce que
> tu fait en ce moment : XYZ et que la scene avance, le NPC ne fait plus cela
> en ce moment et on va boucle au lieu de faire avance la scene.

> Assure toi que l'information s'affiche dans la fiche du NPC dans le cote
> creation et que je puisse l'edite pour faire mes tests.

> l'extraction sera le brief a du ticket 0073.

Decision codes returned during intake:

> A1a, B1, C1 (schedule design, carried to TICKET-0074)
> D2/G2, E1, F1
> J1, K1, L1, I2
> M1, N1
> O1, P1

## Clarifications resolved (intake)

**The problem.** NPC dialogue drifts toward intrigue. Every active `npc_goal`
is a volition aimed at a change of state (influence someone, land a treaty),
so an NPC with nothing else in its briefing plays every scene as an operator.
There is no representation of what an NPC simply *does* — its trade, its
pastime, the thing that explains its presence somewhere.

**The shape (G2).** A standing occupation is not a second table. It is a
`kind` discriminator on `npc_goal`: `volition` (in-scene volition, everything
that exists today) versus `standing` (background volition). This mirrors the
J1 doctrine carried in from the schedule design — schedule is to agenda what
standing is to volition: background versus foreground. Rejected: G1 (a third
`horizon` value — `horizon` is a temporal reach, not a nature, and both
existing readers query it by explicit equality so a third value would be
silently invisible); G3 (a separate `npc_occupation` table — two tables
meaning "what this NPC wants", two write paths, two prompt renders,
guaranteed divergence).

**Coherence (G2).** `kind='standing'` implies `horizon='long'`, enforced by a
CHECK. This is defence in depth, not the primary mechanism: after this ticket
all three readers filter on `kind` explicitly, and the CHECK protects against
a future reader that forgets to.

**Initiative (N1).** The standing goal DOES reach the initiative vote. The
vote decides who speaks up among those present; an NPC on guard duty is held
by its post, an NPC whittling wood in its own room is not — that is exactly
the signal the vote lacks today. It reaches the vote as its OWN fragment,
never by joining the existing `short`-horizon pool: `_initiative_candidate_data`
collapses that pool with `setdefault` to one string per NPC, so admitting the
occupation there would silently suppress one of the two by creation date.

**Scene progression (M1).** Nia's objection: a briefing that asserts "what you
are doing right now" is re-injected verbatim on every turn, while the scene
moves on — the NPC is told it is still whittling at turn 14 and loops instead
of advancing. The objection is correct. `assemble_npc_context` receives no
history and is rebuilt from canon on every call, so a `kind='standing'` row is
stable across a whole scene by construction. The fix is the framing, not the
field: the section states a REASON FOR PRESENCE, which stays true all scene,
and the moment-to-moment gesture stays where it already lives — the
conversation history the model already receives. Rejected: M2 (first-turn-only
injection — `assemble_npc_context` has no turn index and seven call sites,
two of which have no notion of a turn); M3 (continuously rewritten activity —
requires either a model call per NPC per turn or a parse pass over generated
prose, and a WRITE inside the stream, which is the exact shape of the
TICKET-0072 `database is locked` regression; and it would build a second
source of truth about what an NPC is doing, in competition with the scene
history that already tracks it for free).

**Authorship (E1).** Creator CRUD only. No model proposes a standing goal in
v1: `generate_npc_goals` is not extended, no new mutation type is added, and
`goal_change` cannot reach a standing row (see BRIEF-0073-b, Scope IN 6).

**Editing surface (O1, P1).** One selector with three options in the existing
`GoalsEditor` island; the backend derives the `(kind, horizon)` pair from the
single choice, so the incoherent combination is unreachable from the sheet
rather than rejected after the fact. Standing rows render in their own
`OCCUPATIONS` group above the two horizon groups.

**Sequencing (I2).** This ticket ships BEFORE TICKET-0074 (NPC schedules). The
premise — that an occupation goal reduces intrigue drift — is a hypothesis
about model behaviour. One column tests it. If it holds, TICKET-0074 builds
the schedule on a validated foundation and adds `npc_schedule.standing_goal_id`
plus the L1 concordance trigger as a purely additive change. If it does not
hold, the cost of learning that was one column instead of a table, an
accessor and a Svelte panel.

**Extraction (brief -a).** `context.py` is at 979/1000 lines (measured, see
BRIEF-0073-a mini-RECON). No new prompt section fits. Brief -a is a
behaviour-free extraction that buys the margin; brief -b then lands the
feature.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `src/world_engine/context.py` is under the 1000-line module budget with at least 80 lines of margin after brief -a  -> verify/checks/module_budget.py
- [ ] `assemble_mj_context` and `_goal_provenance_suffix` are still defined in `context.py`, and no `NpcGoal` / `"npc_goal"` reference appears at or after `assemble_mj_context`  -> verify/checks/npc_goal_read.py
- [ ] Every `NpcGoal` select in the four in-scene readers (`context.py::_npc_context_goals`, `tick_context.py::_tick_goals_block`, `play_initiative.py::_initiative_candidate_data`, `mutations.py::_mutation_goal_change_close`) carries an explicit `NpcGoal.kind` filter; zero readers found is a FAILURE  -> verify/checks/standing_goal.py
- [ ] The `NpcGoal` model declares both `ck_npc_goal_kind` and `ck_npc_goal_standing_horizon`, and `NPC_GOAL_KINDS` is defined in `writes/goals_agendas.py` and re-exported from `writes/__init__.py`  -> verify/checks/standing_goal.py
- [ ] The standing render is reachable from `assemble_npc_context` and from `_initiative_signal_lines`, and the literal `H_GOALS` is never used to render a standing row  -> verify/checks/standing_goal.py
- [ ] `create_goal` rejects every `(kind, horizon)` pair outside the O1 triple, and `GoalsEditor.svelte` never posts `kind` and `horizon` as two independently chosen values  -> verify/checks/standing_goal.py
- [ ] Every frontend file stays under the 1000-line budget  -> verify/checks/module_budget.py
- [ ] `corpus_gate.py` is green on the whole corpus at the close of each brief  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] In the Creation tab, on an NPC sheet, the goals panel offers OCCUPATION as a third option next to COURT TERME and LONG TERME, and adding one succeeds.
- [ ] A standing row appears in its own OCCUPATIONS group above the two horizon groups, and can be closed (Accompli / Abandonne) like any other goal.
- [ ] `GET /api/entities/{id}/goals` returns `kind` on every row, and pre-existing goals come back as `volition`.
- [ ] In a live session, an NPC carrying a standing occupation shows a `POURQUOI TU ES ICI` section in its assembled context (visible via the prompt inspection route), and the section is absent for an NPC with no standing row.
- [ ] Over a session of at least fifteen turns with one NPC, the standing occupation does not cause the NPC to restate the same activity turn after turn instead of advancing the scene. This is the M1 hypothesis under test; a failure here reactivates M2, it does not invalidate the column.
- [ ] Subjectively, across at least two NPCs, dialogue drift toward intrigue is reduced compared to the same NPCs without a standing occupation. This is the I2 pilot verdict and gates whether TICKET-0074 proceeds as designed.
