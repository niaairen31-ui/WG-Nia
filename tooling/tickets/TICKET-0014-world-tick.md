---
id: TICKET-0014
title: world-tick — off-screen NPC advancement between visits
type: feature
status: exec
created: 2026-07-07
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0014-a, BRIEF-0014-b]
schema_version_touched: next (executor assigns; expected v1.70 — tick_id, lands in BRIEF-0014-b)
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« j'aimerais pouvoir laisser le monde avancer après sa génération » — NPCs
act off-screen; the world moves between visits. Amendments during intake:
« on veut que le NPC en tick ait tout le contexte nécessaire sur le monde /
les lieux / factions et pas juste la situation spécifique pour prendre sa
décision » ; « est-ce possible d'avoir un tag qui me dit que ce knowledge
provient d'un secret ? » ; « ce n'est pas parce que c'est un secret à la
source que c'est un secret pour celui qui reçoit le knowledge ».

## Clarifications resolved (intake)

- C2 — the tick emits `proposed_mutation` rows under creator approval;
  J3 (auto-apply) stays rejected/named-deferred.
- I1 — trigger is a MANUAL cockpit button ("Faire avancer le monde");
  no automatic trigger, no in-game time system (I3 deferred).
- J1 — each invocation is SCOPED (NPC(s), a location, a faction);
  volume controlled by construction.
- K2 — dedicated `assemble_tick_context` builder in a NEW module
  `src/world_engine/tick.py` (not the dialogue assembler, not context.py —
  see RECON-0014 F6 positional fragility).
- L3 — mutation types in scope v1: goal_change + relation_change +
  new_knowledge. Movement/status_change deferred.
- M3 — elapsed interval chosen by the creator at invocation
  (hours / days / weeks label); stored nowhere.
- P1 — proposals land flat in the existing queue; label via
  source_type="world_tick" + proposed_by="local_ai_tick"; no dedicated
  review screen.
- Q1 — gameplay model (`ollama_client.DEFAULT_MODEL`), one call per NPC
  in scope; per-template override possible via `PromptTemplate.model`.
- R3 — per-NPC degradation with notes + per-tick summary (n proposed /
  n failed / n dropped).
- T1 (amended) — full-interiority briefing: ALL own knowledge including
  `is_secret` rows (marked), TRUE roles and secret memberships (marked),
  relations, all active goals, location, faction posture, co-located
  characters. Conscious, logged exception to the secrets-excluded-at-query
  doctrine, scoped to the tick surface (creator-gated output only).
- Y2 — `tick_id` column (nullable, indexed) on `proposed_mutation`; one
  UUID per invocation; readers in the SAME brief: the duplicate-application
  guard's tick branch and the queue label. Closes RECON-0014 F2.
- E1 — the model references entities by NAME; code resolves against a
  roster (scope NPCs + the ticked NPC's relation targets), case-insensitive;
  unresolved -> dropped with a note. `npc_id` (goal_change) and
  `entity_a_id` (relation_change) FORCED code-side to the ticked NPC.
- Z3 (decoupled) — `secret_derived` provenance tag on new_knowledge
  payloads: model-declared AND code-forced at emit when the proposal's
  subject/content matches a secret knowledge row of the ticked NPC.
  STRICTLY DECOUPLED from `is_secret` on the propagated row: provenance is
  mechanical, confidentiality is the receiving NPC's disposition (model
  proposes, creator judges). The rubric must never couple the two.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] npc_goal read boundary intact with src/world_engine/tick.py added to ALLOWED_MODULES  ->  verify/checks/npc_goal_read.py
- [ ] assemble_tick_context referenced only from its allowlisted call sites (tick.py, cockpit/app.py, scripts/preview_tick_context.py); never from context.py, gathering.py, or any MJ path  ->  verify/checks/world_tick.py
- [ ] tick emit path forces npc_id and entity_a_id from the ticked NPC parameter, never from model payload; goal creation is short-horizon only  ->  verify/checks/world_tick.py
- [ ] proposed_mutation.tick_id exists (nullable, indexed) and _find_applied_duplicate contains a tick-scoped match branch keyed on tick_id  ->  verify/checks/world_tick.py
- [ ] secret_derived floor: emit path contains the code-side subject/content match against the ticked NPC's secret knowledge rows  ->  verify/checks/world_tick.py
- [ ] canon write paths unchanged (tick writes ProposedMutation rows only)  ->  verify/checks/single_canon_write.py

### Live  ->  human gate (Nia)
- [ ] Cockpit shows "Faire avancer le monde" with scope selector (NPC(s) / lieu / faction) and interval selector (heures / jours / semaines)
- [ ] Running a tick on a scoped location yields proposals in the queue labeled world_tick, grouped by tick invocation
- [ ] A proposal propagating a [SECRET] briefing item shows the secret_derived badge; its is_secret value is independently settable/judgeable
- [ ] Re-running the same tick and approving a duplicate create_short or new_knowledge is blocked by the guard (Needs attention), while relation_change deltas surface as accumulating (visible, not blocked)
- [ ] scripts/preview_tick_context.py prints a full T1 briefing for a chosen NPC (secrets and true roles marked)
- [ ] Live deployment sequence executed for BRIEF-0014-b (danger_class migration): python backup.py -> migration script -> scripts/apply_ticket_0014_prompt_updates.py
