---
id: TICKET-0015
title: npc-movement — interval-scaled off-screen movement in the world tick
type: feature
status: live-gate
created: 2026-07-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0015-a]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Lifting the L3 deferral of TICKET-0014: NPCs move between locations during a
tick. « E3 me semble plus interessant puisque je suis manuelle. Lorsque je
serai plus automatique, je voudrais qu'un tick de fermeture de session ne
permette pas de changer de continent par exemple. » On co-location with the
player: « je pense qu'il doit être possible de sortir un NPC de son
gathering. »

## Clarifications resolved (intake)

- E3 (locked) — movement range scales with the invocation's interval label,
  enforced STRUCTURALLY (code-side radius), never instructionally. Hop
  radius over the `connects_to` graph (ACTIVE locations only), BFS from the
  NPC's `current_location_id`:
  `heures -> 1 hop | jours -> 3 hops | semaines -> unbounded`.
  The three values live in one named constant map in `tick.py`
  (e.g. `INTERVAL_HOP_RADIUS`), adjustable without touching logic. Rationale
  on record: when ticks later become automatic (I3, still deferred), the
  radius is what guarantees a session-close tick cannot teleport an NPC
  across the world — structural over disciplinary.
- New mutation type `npc_move` — TICK-ONLY producer. The shared
  `analyzer._MUTATION_TYPE_MAP` must NOT gain it: conversation analysis and
  overhearing never propose movement. `tick.py` extends the imported map
  locally (tick-local dict merge); the analyzer's accepted set is
  byte-identical before/after.
- Candidate set computed in code, injected into the briefing — a new
  briefing section `OÙ TU PEUX ALLER` lists the reachable locations
  (name + one-line description) within the interval's radius, so the model
  proposes only from names it was shown. Empty-candidate case renders the
  standard French placeholder (T1 contract: every section header always
  present).
- E1-mirror resolution — the model references the destination by NAME;
  code resolves case-insensitively against the candidate set ONLY (never
  against all locations). Unresolved or out-of-radius -> dropped with a
  per-NPC note (R3 degradation pattern, same as 0014).
- Forced attribution (rule-3 pattern) — `npc_id` is forced from the ticked
  NPC parameter; `from_location_id` is stamped code-side at emit from the
  NPC's `current_location_id`. Neither is ever read from the model payload.
- Apply branch — `_apply_mutation` gains an `npc_move` branch:
  1. Stale-from guard: if the character's live `current_location_id` no
     longer equals the payload's `from_location_id`, route to
     "Needs attention" (the world moved since the proposal), apply nothing.
  2. Location write routes through a NEW `writes.py` helper (both
     sanctioned canon-write paths share `writes.py` helpers — invariant).
  3. `close_open_memberships(npc_id, db)` is called on apply (BRIEF-53
     seam, same as the creator-CRUD location edit). DECIDED: co-located
     NPCs are NOT excluded — an approved move pulls the NPC out of its
     open gathering even if the player is present in it; the Play roster
     reflects it live.
- Dedup — emit-time: at most one `npc_move` per NPC per invocation (a
  second one from the same model reply is dropped with a note).
  Apply-time: `_find_applied_duplicate`'s tick branch gains `npc_move`
  keyed on `tick_id` + entity — re-approving a duplicate is blocked
  ("Needs attention"); accumulation semantics do not apply to movement.
- Interval plumbing — `run_world_tick` already receives `interval_label`;
  it now also drives the candidate-set radius. M3 unchanged: the interval
  is passed, never persisted.
- Queue rendering — the proposal row displays origin -> destination by
  name (`_mutation_dict` extension), no dedicated review screen (P1
  unchanged).
- Prompt — `pt-world-tick` gains the `npc_move` payload shape
  (destination by name from `OÙ TU PEUX ALLER`) via a new prompt version,
  delivered by `scripts/apply_ticket_0015_prompt_updates.py`
  (append-a-version pattern, 0013/0014 precedent).
- No schema migration expected — `proposed_mutation.mutation_type` is an
  unconstrained TEXT column and `tick_id` (v1.70) already exists. If RECON
  finds otherwise, danger_class gains `migration` and the brief gains the
  live deployment sequence.

## Scope OUT (carried or newly named deferrals)

- Automatic triggers / in-game time (I3) — untouched; the radius map is
  built FOR that future but does not build it.
- `status_change` emission from the tick — still deferred (the other half
  of 0014's L3).
- Player movement via tick; NPC schedules/routines; travel-time or
  multi-hop journey simulation (after apply, the NPC simply IS at the
  destination).
- Analyzer/overhearing producers for `npc_move` — permanently out, not
  just deferred this step.
- Return-visit delta narration (`visit` table, G2) — that is the next
  ticket, not this one.
- Region/continent semantics — distance is hop count on `connects_to`,
  nothing else.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `npc_move` accepted in tick.py's local type map; `analyzer._MUTATION_TYPE_MAP` contains no `npc_move` key  ->  verify/checks/world_tick.py (new rule)
- [ ] Emit path forces `npc_id` and stamps `from_location_id` code-side; no `.get("npc_id")` / `.get("from_location_id")` on the model payload anywhere in tick.py  ->  verify/checks/world_tick.py (rule-3 extension)
- [ ] `INTERVAL_HOP_RADIUS` named constant map exists in tick.py and is referenced by the candidate-set builder; destination resolution reads ONLY the candidate set  ->  verify/checks/world_tick.py (new rule)
- [ ] `_apply_mutation`'s `npc_move` branch calls `close_open_memberships` and routes the location write through the new writes.py helper; no direct `current_location_id` assignment in cockpit/app.py's branch  ->  verify/checks/single_canon_write.py + world_tick.py
- [ ] `_find_applied_duplicate` tick branch covers `npc_move` keyed on `tick_id` + entity  ->  verify/checks/world_tick.py
- [ ] `assemble_tick_context` still referenced only from its allowlisted call sites; `npc_goal_read.py` boundary intact  ->  existing rules, unchanged

### Live  ->  human gate (Nia)
- [ ] Tick with interval `heures`: preview briefing shows `OÙ TU PEUX ALLER` limited to direct `connects_to` neighbours; interval `semaines` lists distant locations too
- [ ] A tick proposal with a destination outside the radius (or an invented name) is dropped and visible as a note in the per-tick summary
- [ ] Approving an `npc_move` updates the NPC's location (Fiche), closes its open `gathering_member` row, and the Play roster reflects the departure — including when the player was in the same gathering
- [ ] Stale-from: manually move the NPC after the proposal, then approve -> "Needs attention", nothing applied
- [ ] Re-approving a duplicate `npc_move` from the same tick is blocked ("Needs attention")
- [ ] Queue row shows origin -> destination by name, labeled world_tick, grouped by tick invocation
- [ ] `scripts/apply_ticket_0015_prompt_updates.py` executed against the live DB (append-version, idempotent re-run is a no-op)
