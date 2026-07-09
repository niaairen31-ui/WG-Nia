---
id: TICKET-0020
title: agenda-parentage-and-npc-owners — goal<->agenda links, NPC-owned intrigues, delegation
type: feature
status: live-gate
created: 2026-07-09
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium-high
brief_ids: [BRIEF-0020-a, BRIEF-0020-b, BRIEF-0020-c]
schema_version_touched: v1.73 (expected — executor owns the number)
retry_count: 0
---

## Request (as agreed with Nia)

Locked: A1, B3 (last-parent rule), C4, D1, E2+M1, F1, plus four drafting
decisions (1: per-NPC agenda_creation allowed, ONE active personal agenda
per NPC max; 2: delegated-goal horizon model-chosen, default short; 3:
goal_change gains an optional own-agenda reference; 4: creator detach in
CRUD, soft).

Agendas stop being faction-only and goals stop being orphans. A
many-to-many `goal_agenda_link` table (B3) ties NpcGoals to the intrigues
they serve — the F2 hierarchy deferral, reactivated because readers now
exist on both sides. NPCs may OWN one personal intrigue (A1), advanced by
their own tick call. Factions gain `agenda_delegation`: the faction-scoped
tick proposes creating a goal ON a member NPC, linked to the intrigue —
the mechanism by which a faction recruits its members' behaviour. When an
agenda closes, linked goals mechanically share its fate (E2+M1,
last-parent rule) — sanctioned because every link passed creator review.
Provenance in dialogue prompts is gated structurally by public membership
(D1). New faction intrigues must be anchored in posture (F1).

## Clarifications resolved (intake)

- B3 grain: link target is the AGENDA (not the step); a goal may serve
  several intrigues; cascade fires only when the goal's LAST active
  parent closes (last-parent rule).
- E2+M1 mapping (goal vocabulary has no 'failed'): agenda completed ->
  goal completed; agenda failed|abandoned -> goal abandoned. Snapshot
  with provenance `cascade:agenda:<id>:<status>` — history is sacred.
  Cascade fires on ANY exit from 'active', including creator CRUD
  overrides (creator supremacy is consistent: her close cascades too).
- A1 owners: `write_agenda` accepts ACTIVE `character`-type owners in
  addition to factions; a character owner may hold AT MOST ONE active
  agenda (code guard in the helper + canon-existence dedup at
  proposal/approval, 0014 tick-guard doctrine). Factions keep their
  existing multi-agenda freedom. Location owners stay out.
- Per-NPC tick contract DELIBERATELY extended: `_TICK_MUTATION_TYPES`
  gains `agenda_step_change` + `agenda_creation`, restricted to agendas
  the NPC OWNS (its own agendas_index; owner_entity_id FORCED to npc_id
  on creation — the H1/O1 forcing precedent). Logged in
  ARCHITECTURE_DECISIONS.md as an evolution of the 0017 contract, not
  drift.
- `agenda_delegation` (faction scope only): payload {npc (roster name),
  goal (text), horizon (optional short|long, clamp->short), agenda
  (title)}; apply validates ACTIVE membership of the NPC in the agenda's
  owner faction, then creates goal + link atomically. O1 relaxation
  (model-chosen horizon) is scoped to THIS type only and logged.
- D1: dialogue provenance `(sert : « <titre> »)` rendered only when the
  agenda owner is the NPC itself, or a faction whose membership survives
  the public-membership choke-point. New companion accessor
  `read_public_membership_faction_ids` (same WHERE triplet). The per-NPC
  TICK briefing shows all provenance — full-interiority T1, same tier as
  the existing affiliation block.
- F1: verbatim anchoring directive in the faction scope prompt (new
  version of `pt-world-tick-events`); per-NPC directives in a new
  version of `pt-world-tick`; one apply script, append-version branch.
- Soft detach: `detached_at`/`detached_by` on the link row, partial
  unique index on active pairs — the FactionMembership.left_at
  precedent. No DELETE path exists.

## Scope OUT

- Location-owned agendas (A2/A3 rejected at intake).
- Cross-faction delegation (goal on a non-member NPC).
- Cascade on STEP closure — the B3 grain is the agenda.
- `failed` added to the goal vocabulary (M3 rejected).
- F2 faction-posture-in-dialogue and visibility_trace-in-dialogue —
  separate deferred brief, creator-triggered.
- Injecting the NPC's own intrigue into DIALOGUE context (tick only
  this chantier).
- Analyzer/conversation path proposing links or delegations — tick only.
- Branching agendas, shared multi-NPC intrigues, agenda deadlines.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] GoalAgendaLink( constructed only in writes.py  ->  verify/checks/single_canon_write.py
- [ ] Partial unique active-pair index present on the model  ->  migration + model review
- [ ] agenda_delegation normalized only in the scope path, scope_type=='faction' only  ->  verify/checks/world_tick.py
- [ ] Per-NPC agenda types resolve exclusively against owner-restricted agendas_index; owner_entity_id never read from a per-NPC payload  ->  verify/checks/world_tick.py
- [ ] Dialogue provenance rendered only through read_public_membership_faction_ids or owner==npc  ->  verify/checks/npc_goal_read.py
- [ ] Cascade writes pass through write_npc_goal_status with cascade provenance  ->  verify/checks/single_canon_write.py
- [ ] Full suite green  ->  tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] Live sequence: backup -> `migrate_v1_73_goal_agenda_link.py` -> `apply_ticket_0020_prompt_updates.py` (re-runs no-op)
- [ ] Faction tick proposes an `agenda_delegation` on a member; approving it creates the goal AND the link; the member's next per-NPC briefing shows the goal with `(sert : ...)`
- [ ] A per-NPC tick call proposes `agenda_creation`; approved: the NPC owns a personal intrigue, visible in Intrigues; a SECOND creation proposal for the same NPC is dropped/blocked (one-personal-agenda invariant)
- [ ] The NPC's own tick call advances its personal intrigue (`agenda_step_change` complete/fail through the queue)
- [ ] Closing an agenda (via tick OR manual override) cascades: linked single-parent goals share its fate (M1 mapping); a goal with a second still-active parent SURVIVES
- [ ] Dialogue with a SECRET member whose goal serves the faction's intrigue: the goal shows, the provenance does NOT; same goal on a public member: provenance shows
- [ ] Creator: attach and detach a link in the cockpit; detached pair can be re-attached (partial index proof)
