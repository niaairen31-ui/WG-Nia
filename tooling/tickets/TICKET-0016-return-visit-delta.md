---
id: TICKET-0016
title: return-visit-delta — visit table + "what changed here" narrated at enter_scene
type: feature
status: exec
created: 2026-07-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
brief_ids: [BRIEF-0016-a]
schema_version_touched: v1.71 (expected — executor owns the number)
retry_count: 0
---

## Request (as agreed with Nia)

G2, locked in the post-0014 planning session: the world tick now changes the
world off-screen (NPC interiority since 0014, NPC movement since 0015), but
nothing tells the player what changed when they return to a location. This
ticket makes off-screen change PERCEIVABLE: a small append-only `visit`
table anchors the player's last entry per location, and `enter_scene`
injects a code-computed diff (NPCs arrived/departed, public events occurred
here) into the existing establishment narration. G2 was chosen over the
no-table derivation (G1) because "visited without conversing" is a normal
play pattern the conversation-derived anchor would miss.

## Clarifications resolved (intake)

- New table `visit` (expected v1.71): `id, world_id, player_id,
  location_id, entered_at, present_npc_ids (JSON)`. Append-only — history
  is sacred; no update or delete path exists.
- Written by `enter_scene` ONLY on genuine location transitions (inside
  the existing idempotent guard that distinguishes a real entry from an
  F5 re-render — `cockpit/app.py:4189` `if not open_g:`). A refresh
  writes nothing and gets no delta; the establishment narration itself
  still fires on every entry, unchanged.
- The delta is computed IN CODE before the new visit row is written:
  previous latest visit for (player, location) -> departed / arrived NPC
  name lists by set-diff of public presence
  (`Character.current_location_id`, same alive/active predicate as the
  tick's location scope), plus public events at this location since the
  previous visit. First-ever visit -> no delta block.
- STRUCTURAL EXCLUSION carried over: the event leg filters
  `knowledge_status IN ('public','confirmed')` at query construction —
  the same filter as the only existing Event reader (context.py:533-538).
  Secret events can never surface in a return delta. (The event leg is a
  forward-reader: it renders empty until the event producer ships —
  TICKET-0017 territory — and gives that producer a perception channel
  on day one.)
- The model narrates the delta: the `mj_establishment` prompt gains a
  `{changes}` block via a NEW VERSION, with a scoped exception to its
  "no named NPC" rule — NPCs named in the CHANGES block (departures /
  arrivals) may be named, presently-present NPCs still may not; an empty
  block must produce zero invented change.
- Presence snapshot = public presence at the moment of entry, exactly
  what QUI EST AUTOUR would show — no secret leak surface; a departed
  NPC's name still resolves even if its entity has since gone inactive
  (the player saw them; naming their absence reveals nothing new).
- danger_class includes `migration` -> the brief's Done means carries
  the explicit live deployment sequence (backup -> migration ->
  apply-prompt), executed at live gate.

## Scope OUT

- Any event PRODUCER (tick lane, creator CRUD for events) — next ticket.
- Deltas for signposts / discoverable details (already re-narrated fresh
  on every entry through `active_signposts`).
- Player-facing journal/history UI; multi-location "world news" digests.
- Tracking visits for NPCs or for anything but the player character.
- Retention/pruning of visit rows (append-only, small rows, revisit only
  if measured).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `visit` rows are created only inside enter_scene's genuine-transition path; no UPDATE/DELETE on Visit anywhere  ->  new verify check
- [ ] The delta's Event query textually constrains `knowledge_status` (structural exclusion)  ->  new verify check
- [ ] Existing check suites still pass (world_tick, single_canon_write, page_contract, prompt checks)  ->  tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] Enter a location, tick an NPC away from it (0015), re-enter: the establishment narration mentions the departure by name; the `visit` table shows both rows
- [ ] First visit to a location produces a normal establishment narration with no invented "changes"
- [ ] F5 on the scene re-renders without writing a visit row and without a delta block
- [ ] A creator-inserted `event` at the location with `knowledge_status='secret'` never appears in the delta; flipped to `'public'`, it appears on next re-entry
- [ ] Live deployment sequence executed: backup -> `migrate_v1_71_visit.py` -> `apply_ticket_0016_prompt_updates.py` (re-runs are no-ops)
