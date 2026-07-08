---
id: TICKET-0017
title: event-producer — scope-level event_creation in the world tick + apply branch
type: feature
status: exec
created: 2026-07-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium-high
brief_ids: [BRIEF-0017-a]
schema_version_touched: none expected (event table exists since the founding schema)
retry_count: 0
---

## Request (as agreed with Nia)

F, locked in the post-0014 planning session and reframed on Nia's
correction: events are NOT creatures of factions — a storm or a festival
has no factional author. The scope of the tick determines the briefing,
not the nature of the event. Location- and faction-scoped tick invocations
gain ONE scope-level model call proposing `event_creation` mutations
(quota-bounded), reviewed in the same queue; `_apply_mutation` finally
implements the `event_creation` branch, which also awakens the DORMANT
conversation-sourced event proposals the analyzer has emitted since its
founding (analyzer.py:324-330, left "approved with a note" until now).
Public events at a location become perceivable on the player's next
return through the TICKET-0016 delta — the forward-reader lights up.

## Clarifications resolved (intake)

- Scope semantics: `scope_type == "location"` -> per-NPC interiority
  ticks (unchanged) PLUS one location-level event call (briefing = the
  place: description, subculture, public occupants, recent public events
  here, connected neighbours). `scope_type == "faction"` -> per-NPC ticks
  PLUS one faction-level event call (briefing = posture: philosophy,
  goals, internal_tensions, aversion, treasury, members). `scope_type ==
  "npcs"` -> NO event call: an NPC does things; it does not author world
  events. One button, two granularities (F1 as reformulated).
- The scope-level call shares the invocation's `tick_id` and its single
  transaction; its results join the same R3 summary under a new
  `scope_events` entry.
- New prompt head `pt-world-tick-events` (usage `world_tick_events` —
  unique usage value, cockpit editor groups by usage), seeded +
  delivered via `apply_ticket_0017_prompt_updates.py` with the
  HEAD-ABSENT branch (0014 pattern, unlike 0015/0016).
- `event_creation` payload, tick-side (closed shape): `title` (required),
  `description`, `type` validated against the schema vocabulary
  (`political | magical | criminal | military | social | mystery |
  other`, fallback `other`), `knowledge_status` proposed as
  `secret | public` only (`confirmed` is reserved to the creator),
  `involved_entities` resolved by name against the scope roster
  (occupants / members + the faction itself) — an unresolved name is
  dropped FROM THE LIST with a note, never the whole event.
  `location_id` FORCED code-side for location scope; for faction scope,
  resolved from an optional payload location name against ACTIVE
  locations, else NULL.
- Emit quota: at most 3 event_creation per scope call (J1 volume by
  construction).
- Apply branch: routes through a new `writes.py` helper (`write_event`);
  tolerant of BOTH payload generations (the analyzer's older minimal
  shape carries no knowledge_status -> column default 'secret' applies).
  `occurred_at` stays NULL (in-fiction time unknown); `recorded_at`
  auto.
- Duplicate guard (0014 tick doctrine — canon-existence, never tick_id
  equality): duplicate iff an Event row exists with the same normalized
  title AND the same location_id (or same world when locationless).
- Full-interiority exception EXTENDED, consciously: the NPC tick briefing
  already reads raw FactionMembership (tick.py:189, never
  read_public_memberships); the faction-level briefing sits on the SAME
  creator-gated surface and receives the same treatment, secret
  memberships and internal_tensions included. Logged as an exception
  extension in ARCHITECTURE_DECISIONS.md.

## Scope OUT

- Agendas (A1/B2) — next chantier; this ticket produces one-shot events,
  the agenda gives them memory.
- Entity creation (H1/I2) — after agendas.
- Event -> knowledge propagation to NPCs (beyond the 0016 return delta);
  a world-scope tick lane; automatic triggers (I3).
- Creator CRUD surface for events (create/edit events by hand) — only if
  RECON finds none exists AND the live gate needs one to test
  secret/public flipping; otherwise deferred and tested via SQL.
- Any change to the per-NPC tick contract (npc_move etc. untouched).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] event_creation is emitted ONLY by the scope-level path, never by the per-NPC normalizer  ->  verify/checks/world_tick.py extension
- [ ] location scope forces location_id code-side (no payload .get); quota constant exists and bounds the emit loop  ->  verify/checks/world_tick.py
- [ ] _apply_mutation's event_creation branch routes through write_event; no direct Event( construction in cockpit/app.py  ->  verify/checks/single_canon_write.py
- [ ] analyzer._MUTATION_TYPE_MAP unchanged (event aliases were already there; no tick aliases leak back)  ->  existing rule
- [ ] Existing suites green  ->  tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] Location-scoped tick on the tavern: R3 summary shows a scope_events entry; 0-3 event proposals in the queue labeled TICK, alongside the per-NPC proposals
- [ ] Faction-scoped tick on a faction: same, with faction-flavored events; involved_entities resolve to member ids
- [ ] Approving a public event at a location, leaving, re-entering: the 0016 return delta names it — the forward-reader lights up
- [ ] Approving a secret event: absent from the return delta
- [ ] A dormant conversation-sourced event_creation (if any exist in the live queue) now applies cleanly
- [ ] Re-approving the same event -> "Needs attention" (canon-existence guard)
- [ ] `apply_ticket_0017_prompt_updates.py` run against the live DB (head created; immediate re-run is a no-op)
