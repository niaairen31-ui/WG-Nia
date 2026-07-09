---
id: TICKET-0018
title: faction-agendas — structured intrigues the tick advances and proposes
type: feature
status: exec
created: 2026-07-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium-high
brief_ids: [BRIEF-0018-a]
schema_version_touched: v1.72 (expected — executor owns the number)
retry_count: 0
---

## Request (as agreed with Nia)

A1 + B2, locked: factions gain structured AGENDAS — ordered steps with
states — so the tick stops inventing isolated one-shots and starts
executing multi-tick storylines. The faction-scoped tick call (0017)
reads the active step and proposes its advancement (`agenda_step_change`)
or a brand-new intrigue (`agenda_creation`), through the same review
queue; the creator authors and edits agendas through a cockpit surface.
Each step carries a `visibility_trace` — what the world can perceive
while it executes — which the model is encouraged to materialize as
events (0017) so the player can FEEL a machination before its climax:
surprise earned, not arbitrary. Player interference gets a structural
target: a step can FAIL on briefing evidence.

## Clarifications resolved (intake)

- A1: owners are FACTIONS ONLY this step — column named
  `owner_entity_id` (A2-ready) but the write helper enforces
  faction-type owners; the two other briefing injections (location,
  NPC) stay unbuilt until their chantier.
- B2: the tick may propose NEW agendas (`agenda_creation`, at most one
  per scope call), creator-reviewed like everything else; creator CRUD
  is the other authoring path.
- Two tables (expected v1.72), NpcGoal as the shape precedent
  (models.py:338-359 — CheckConstraints, change_history, timestamps):
  `agenda` (id, world_id, owner_entity_id, title, status
  active|completed|failed|abandoned, change_history) and `agenda_step`
  (id, agenda_id, step_order, objective, status
  pending|active|completed|failed, outcome, visibility_trace,
  change_history). STRUCTURAL invariant: at most ONE active step per
  agenda via a partial unique index (`sqlite_where status='active'`) —
  the idx_membership_one_primary precedent (models.py:218-221).
- The model NEVER picks a step: it references an agenda BY TITLE
  (resolved against the active-agenda index shown in the briefing);
  the step id is code-derived — the agenda's single active step. Its
  proposal is only `{action: complete|fail, outcome}`.
- Advancement logic is CODE, at apply: completed -> next pending step
  (by step_order) becomes active; no next -> agenda completed; failed
  -> agenda failed (creator can revive by editing — flagged decision).
- Faction briefing gains section AGENDA EN COURS (title + active step
  objective + visibility_trace + last outcomes for continuity);
  location-scoped calls get NO agenda types — agendas are
  faction-owned (A1), enforced structurally in the normalizer.
- New prompt VERSION of `pt-world-tick-events` (usage unchanged);
  delivery script `apply_ticket_0018_prompt_updates.py`
  (append-version branch, head exists since 0017).
- Cockpit surface "Intrigues": list agendas with steps, create
  (title + ordered objectives + optional visibility traces), edit
  pending steps, manual status overrides (creator supremacy), abandon.
- danger_class migration -> live deployment sequence mandatory
  (backup -> migrate -> apply-prompt).

## Scope OUT

- Non-faction owners (locations, NPCs, world) — A2, named deferral.
- `npc_goal` <-> `agenda_step` parentage (the F2 hierarchy engagement:
  a member NPC's short goal serving the faction's active step) — the
  NEXT natural chantier, named deferral, do not pre-build columns.
- Injection of agendas into the per-NPC tick briefing or dialogue
  contexts (secret-leak surface — needs its own exclusion design).
- Automatic event generation ON step completion (the model pairs a
  step_change with an event_creation in the same reply; no code
  coupling this step).
- Branching agendas, conditional steps, deadlines/durations.
- Entity creation (H1/I2) — after this.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Agenda types normalized only in the scope path and only for scope_type=='faction'; the per-NPC contract untouched  ->  verify/checks/world_tick.py
- [ ] step_id / agenda step identity never read from model payloads  ->  verify/checks/world_tick.py
- [ ] Agenda( / AgendaStep( constructed only in writes.py  ->  verify/checks/single_canon_write.py
- [ ] Partial unique index (one active step per agenda) present in the model  ->  migration + model review
- [ ] Full suite green  ->  tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] Live sequence: backup -> `migrate_v1_72_agenda.py` -> `apply_ticket_0018_prompt_updates.py` (re-runs no-op)
- [ ] Create an agenda for a faction in the cockpit (3 steps); faction tick: briefing shows AGENDA EN COURS; a step advancement is proposed with an outcome
- [ ] Approving `complete`: step completed with outcome, next step active; completing the last step closes the agenda
- [ ] A `fail` proposal fails the step AND the agenda
- [ ] An `agenda_creation` proposal applies: agenda born active, step 1 active, visible in Intrigues
- [ ] Manually complete a step, then approve the stale proposal -> "Needs attention"; duplicate agenda_creation (same title) -> blocked
- [ ] Location-scoped tick: no agenda proposals possible
