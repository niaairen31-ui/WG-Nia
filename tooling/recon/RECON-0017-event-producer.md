# RECON-0017 — event-producer (scope-level event_creation + apply branch)

Date: 2026-07-08
Branch inspected: `main` (post TICKET-0016 merge; TICKET-0015/0016 closed,
live-gates validated)
Mode: report-only. No actions taken.

Locked decisions in force: F as reformulated (events decoupled from
factions; the SCOPE of the tick determines the briefing, not the nature of
the event; npc-scoped invocations produce no events), quota J1-style,
0014 guard doctrine, full-interiority tick surface.

---

## F1 — A SECOND, DORMANT producer already exists: the analyzer emits
## event_creation from conversations, unapplied since the founding schema

`analyzer.py:56` lists `event_creation` among accepted types; the alias map
carries `"event": "event_creation"` (analyzer.py:94-95) and target-table
mapping `"event_creation": "event"` (analyzer.py:122). The normalization
branch (analyzer.py:324-330) builds a MINIMAL payload:
`{title: item.title | content[:60] | "Event", description: content,
type: item.event_type | "social", involved_entities: [conv.player_id,
conv.npc_id]}` — note: raw ids (the analyzer resolves nothing here), NO
`knowledge_status`, NO `location_id`. Meanwhile `_apply_mutation`'s
docstring (cockpit/app.py:971) leaves event_creation explicitly
unimplemented ("left as 'approved' with a note — better un-applied than
wrongly applied"). CONSEQUENCE: the new apply branch must tolerate BOTH
payload generations — the analyzer's minimal shape (ids already resolved,
no status -> the column's server_default 'secret' applies, models.py:618-621)
and the tick's richer closed shape. Any event_creation rows sitting
'approved' in the live queue become applicable the moment the branch lands.

## F2 — Event table: no schema change needed; the vocabulary and the one
## reader define the payload contract

`models.py:607-631` — all needed columns exist: `title` (required),
`description`, `type` (free text; the schema doc enumerates
political|magical|criminal|military|social|mystery|other),
`knowledge_status` TEXT DEFAULT 'secret' (world-engine-schema.md:675),
`involved_entities` JSON, `location_id` FK nullable, `occurred_at`
nullable, `recorded_at` auto (`_created_ts`), `session_id`/`batch_id`
nullable FKs (both stay NULL for tick events — neither a play session
artifact nor a pass-play batch; the mutation row's `tick_id` is the
provenance anchor). Readers: `context.py:533-538` filters
`knowledge_status IN ('public','confirmed')`; the 0016 return delta
applies the same filter with `Event.location_id == location` — so an
approved PUBLIC event at a location is player-perceivable on next
re-entry with ZERO additional work (the forward-reader planned in
BRIEF-0016-a). `confirmed` must stay creator-reserved: the model may
propose secret|public only, code-clamped.

## F3 — The endpoint already carries the scope identity the event call needs

`cockpit/app.py:4780-4841` (world_tick_endpoint) resolves scope_type/
scope_id BEFORE calling `_run_world_tick(db, npc_ids, body.interval)` —
but the runner currently receives only the flattened npc_ids: the scope
identity is LOST at the boundary. `run_world_tick` (tick.py, post-0015
signature `db, npc_ids, interval_label, model, host`) must gain
`scope_type: str = "npcs"` and `scope_id: Optional[str] = None`, and the
endpoint passes them through. The scope-level event call then runs INSIDE
the runner — sharing the invocation's `tick_id`, the single end-of-run
transaction (tick.py commit discipline: one commit for all surviving rows;
a crashed invocation writes nothing), and the R3 summary dict (new
`scope_events` key alongside `npcs`).

## F4 — Briefing builders: tick.py already owns the location-composition
## idiom and deliberately reads RAW memberships

- Location material: tick.py:212-224 composes the setting from
  `Entity.name/description` + `location.subculture["values"]` (tick.py is
  banned from importing cockpit's `_SAFE_SUBCULTURE_KEYS`; it already
  reads the "values" key directly — the location briefing reuses this
  idiom). Public occupants: the QUI EST AUTOUR query (tick.py:228-236).
  Connected neighbours: `_reachable_locations(db, loc, interval)` from
  0015 — the event briefing can name the surroundings for free. Recent
  public events here: the F2 filter, last N by recorded_at.
- Faction material: `Faction` posture fields philosophy /
  internal_tensions / goals / aversion / faction_type /
  magic_knowledge_level (models.py:167-185+); members via RAW
  `FactionMembership` `left_at IS NULL` — tick.py:189 records the
  standing exception: the tick surface reads FactionMembership directly,
  NEVER read_public_memberships (context.py:131), because output passes
  creator review. The faction-level call sits on the SAME creator-gated
  surface: extending the exception is coherent but must be RE-LOGGED as
  a conscious extension (the 0014 log scoped it to the per-NPC briefing).
- Treasury: faction ledger balance — cite the ledger accessor found in
  the economy chantier at brief time (grep `ledger` in writes.py/crud.py;
  report-only note: exact symbol to be pinned by the executor, the
  accessor exists since the treasury chantier).

## F5 — Guard and quota mechanics

Duplicate guard (0014 doctrine, canon-existence): duplicate iff an `Event`
row exists with the same casefolded/stripped title AND the same
`location_id` (IS-NULL-matching for locationless events, same world).
Title normalization mirrors `_normalize_goal_text` (tick.py:277+). Both
the `_find_applied_duplicate` tick branch and pre-write symmetry apply as
in 0015. Emit quota: a module constant (e.g. `SCOPE_EVENT_QUOTA = 3`)
bounds the accepted items per scope call — J1 volume by construction,
machine-checkable like INTERVAL_HOP_RADIUS (rule-7 idiom,
verify/checks/world_tick.py).

## F6 — Prompt: a NEW head, not a new version — and the head-absent branch

The per-NPC `pt-world-tick` contract is entity-interiority ("You advance
ONE NPC's life"); the event call is world-authorship — different briefing,
different output contract, different usage. Precedent for distinct heads
per usage: `mj_establishment` vs `world_tick` etc.; usage values must be
UNIQUE (cockpit editor groups by usage — standing collision rule). New
head `pt-world-tick-events`, usage `world_tick_events`, world_id=NULL, no
world-specific examples (universal-template rule). Delivery script
`apply_ticket_0017_prompt_updates.py` needs the HEAD-ABSENT branch
(0014's shape at apply_ticket_0014_prompt_updates.py), unlike 0015/0016
which were append-only.

## F7 — Verify surface

world_tick.py currently checks: allowlist (45-49), boundary files,
forced attribution (118-147, `_FORCED_FIELDS` incl. from_location_id
since 0015), guard branch, Z3 floor, analyzer-map isolation, radius
constant. Extensions needed: (rule) event_creation normalization lives
only in the scope-level path — the per-NPC `_normalize_tick_item` must
NOT map it (its closed frozenset stays `goal_change | relation_change |
new_knowledge | npc_move`); (rule) location scope's `location_id` is a
forced bare Name; (rule) `SCOPE_EVENT_QUOTA` exists and is referenced by
the scope emit loop; (single_canon_write) `Event(` construction only in
writes.py (`write_event`).

---

## Notes for the brief

1. The apply branch awakens the dormant conversation channel (F1) — the
   live gate should include applying one if any sit in the queue.
2. `knowledge_status` clamp: model proposes secret|public; anything else
   (incl. 'confirmed') -> coerced to 'secret' with a note, never dropped
   (the creator can flip at review or via SQL).
3. No migration: danger_class db_write only; the live sequence is
   backup -> apply-prompt (script) as hygiene, no DDL.
