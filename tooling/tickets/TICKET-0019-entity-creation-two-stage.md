---
id: TICKET-0019
title: entity-creation-two-stage — the tick proposes the need, the authoring chain produces the sheet
type: feature
status: live-gate
created: 2026-07-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0019-a]
schema_version_touched: none expected (no new tables — the germ lives in proposed_mutation)
retry_count: 0
---

## Request (as agreed with Nia)

H1 + I2, locked — the last chantier of the post-0014 sequence. The world
can now move, be felt, produce events and pursue intrigues; it must also
be able to GROW: « je voulais d'ailleurs qu'il ait la possibilité de
créer des npc et des lieux au besoin » — and, per Nia's own reasoning,
factions too (« s'il peut proposer la chute d'une faction, il peut aussi
en créer une »). Two stages, two checkpoints: the tick proposes the NEED
(a thin `entity_creation` germ in the same queue); approval does NOT
write the entity — it parks the need as validated; the Création tab
gains a "Créations en attente" list where Nia triggers the sheet
generation ON HER OWN TIME (I2: no synchronous authoring call blocking
batch review), the existing authoring chain (`generate_entity_draft`,
AUTHOR_MODEL, goals L1) pre-fills the existing creation form, and her
commit realizes the entity — flipping the mutation to `applied` with
`created_entity_id` stamped in its payload: "this NPC was born from
tick X" stays readable forever.

## Clarifications resolved (intake)

- Germ payload (closed, thin): `entity_type`
  (`character | location | faction` — exactly `_TYPE_FIELDS`' keys),
  `name` (required), `concept` (one-liner, required), `anchor`
  (optional prose: near / within / serves — never resolved to ids;
  the germ is text destined for a text brief).
- Both scope calls (location AND faction) may propose it; per-NPC
  ticks never do. Quota: at most ONE entity_creation per scope call
  (own constant, outside SCOPE_EVENT_QUOTA and the agenda caps).
- Name-collision guard IN CODE, twice: at emit (casefolded name equals
  an ACTIVE entity of the world -> drop with note) and at approval
  (canon re-check, 0014 doctrine -> Needs attention if the world moved).
- Approval short-circuits `_apply_mutation`: status stays `approved`
  with the note "en attente de réalisation — onglet Création", response
  status `pending_realization` — NOT the "[apply error]" framing.
  Rejection stays the normal queue rejection.
- Realization: `GET /api/creations/pending` (approved entity_creation
  lacking `created_entity_id`, ALL sources — the dormant
  conversation-sourced channel joins the list, 0017-style awakening);
  `POST /api/creations/{mutation_id}/generate` composes a French brief
  from the germ IN CODE and reuses the existing write-free generation
  flow (app.py:127-150, L1 goals included for characters); the
  pre-filled form carries `mutation_id`; `create_entity` (crud.py:690)
  gains the optional linkage — on commit it stamps
  `payload.created_entity_id`, `status="applied"`, `applied_at`.
- An abandoned draft costs nothing: the mutation stays `approved` and
  re-generatable (generation is pure; only the commit realizes).
- New locations: NO auto-wired `connects_to` — `anchor` is prose in the
  brief; the creator wires edges manually after commit (region
  chantier 2 precedent: links are confirmed by the creator, never
  auto-created).
- Prompt: new VERSION of `pt-world-tick-events` (germ shape + rules),
  delivered via `apply_ticket_0019_prompt_updates.py` (append-version).
- No migration: the germ lives in `proposed_mutation.payload`; the
  pending list is a query. danger_class: db_write only.

## Scope OUT

- Tick-authored FULL sheets (H2 rejected: the 8b gameplay model never
  authors entity sheets; the authoring chain keeps that job).
- Auto-application of drafts; any write in the generation path.
- connects_to auto-wiring; automatic faction memberships for created
  NPCs (the form's normal fields serve; germ anchors are prose).
- entity types beyond the three (`object`, `world` etc.).
- Deletion/expiry of stale pending creations (reject in the queue is
  the existing path; revisit if the list ever clutters).
- Any change to the per-NPC tick contract or the analyzer.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] entity_creation normalized only in the scope path; per-NPC contract untouched; quota constant exists and bounds the emit  ->  verify/checks/world_tick.py
- [ ] _apply_mutation writes no canon for entity_creation (no Entity( construction; the approve endpoint short-circuits)  ->  verify/checks + code review
- [ ] The realization flip (applied + created_entity_id) happens only in create_entity's guarded linkage  ->  new verify rule
- [ ] Full suite green  ->  tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] Backup; `python scripts/apply_ticket_0019_prompt_updates.py` (re-run: no-op)
- [ ] Faction tick: an entity_creation germ appears in the queue (thin payload visible); approving it returns "en attente de réalisation", status approved
- [ ] Création tab lists it; "Générer la fiche" pre-fills the creation form from the germ (character germ includes generated goals — L1); commit creates the entity, the mutation shows applied + created_entity_id
- [ ] Abandon a generated draft (navigate away), regenerate later: works; the mutation stayed approved
- [ ] Germ whose name matches an existing active entity: dropped at emit with a note; create the collision manually AFTER approval, then generate+commit -> the approval-time guard path is exercised on a fresh germ (Needs attention)
- [ ] A location germ commits with zero connects_to edges; wiring them manually in the cockpit works as usual
- [ ] Location-scoped tick can also propose a germ (e.g. a new occupant); npcs-scoped tick never does
