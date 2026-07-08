# BRIEF — Step "scope-level event producer + event_creation apply branch (BRIEF-0017-a-event-producer)"

## Context

The `event` table has existed since the founding schema with no producer
and no apply branch — the analyzer even emits conversation-sourced
`event_creation` proposals that sit 'approved, unapplied' by design
(cockpit/app.py:971). This chantier gives the world events: location- and
faction-scoped tick invocations gain ONE scope-level model call proposing
up to `SCOPE_EVENT_QUOTA` events (new head `pt-world-tick-events`), and
`_apply_mutation` implements `event_creation` — awakening both producers
at once. Approved PUBLIC events at a location surface automatically in
the 0016 return delta (the forward-reader). Events are decoupled from
factions by design (Nia's correction on record): the SCOPE shapes the
briefing, not the nature of the event. Grounding: RECON-0017 (F1-F7).
danger_class: db_write — no migration.

## Scope IN

1. **Runner signature + scope call (`src/world_engine/tick.py`).**
   `run_world_tick` gains `scope_type: str = "npcs"` and
   `scope_id: Optional[str] = None`; `world_tick_endpoint`
   (cockpit/app.py:4841) passes `body.scope_type` / `body.scope_id`
   through (RECON F3). After the per-NPC loop, when `scope_type` is
   `"location"` or `"faction"` (never `"npcs"`): assemble the scope
   briefing (item 2), load `usage="world_tick_events"`, one chat call
   (`format="json"`, same degrade-don't-abort envelope: failure -> note
   in the summary, per-NPC results still commit), normalize items
   (item 3), cap at `SCOPE_EVENT_QUOTA = 3` (module constant; items
   beyond the cap dropped with a note), append rows sharing the
   invocation's `tick_id` / `source_type="world_tick"` /
   `proposed_by="local_ai_tick"` into the SAME single end-of-run
   transaction. R3 summary gains
   `"scope_events": {"proposed": n, "dropped": n, "notes": [...]}`
   (present only for location/faction scopes).

2. **Briefing builders (tick.py).**
   - `assemble_location_event_context(location_id, session, *,
     interval_label) -> str` — French, T1 section discipline (headers
     always present, placeholders when empty): LE LIEU (Entity
     name/description + `location.subculture["values"]`, the tick.py:212
     idiom — never import cockpit's key allowlist), QUI S'Y TROUVE
     (public occupants, the tick.py:228-236 query), LES ENVIRONS
     (`_reachable_locations(db, location_id, interval_label)` names —
     0015 reuse), ÉVÉNEMENTS RÉCENTS ICI (last 5 Events at this
     location, `knowledge_status IN ('public','confirmed')` — the
     context.py:533-538 structural filter; placeholder when empty).
   - `assemble_faction_event_context(faction_id, session) -> str` —
     LA FACTION (Entity name/description, faction_type, philosophy),
     POSTURE (goals, internal_tensions, aversion,
     magic_knowledge_level), MEMBRES (RAW FactionMembership,
     `left_at IS NULL`, names + roles — the full-interiority tick
     exception EXTENDED to this surface; same creator gate, re-logged,
     RECON F4), TRÉSORERIE (faction ledger balance via the existing
     treasury accessor — executor pins the exact symbol; if none is
     importable without a cockpit import, compute the sum locally with
     a comment citing the treasury chantier), ÉVÉNEMENTS RÉCENTS
     (last 5 public/confirmed Events whose involved_entities contains
     the faction id, placeholder when empty).
   - Both are tick.py-local; `assemble_tick_context`'s allowlist check
     is untouched (these are NEW symbols — add them to the
     verify-check's awareness only if the executor extends the
     allowlist rule to them; minimal: they live and are called only in
     tick.py, no new allowlist needed).

3. **Normalizer `_normalize_scope_event(raw_item, *, scope_type,
   scope_id, roster, locations) -> dict | None` (tick.py).**
   Separate from `_normalize_tick_item` — the per-NPC closed frozenset
   is UNTOUCHED (event_creation never enters it; machine-checked).
   - `title`: required, stripped; empty -> drop with note.
   - `description`: optional string.
   - `type`: casefolded, validated against
     `{"political","magical","criminal","military","social","mystery",
     "other"}` -> fallback `"other"`.
   - `knowledge_status`: model may propose `secret | public`; anything
     else (including `confirmed` — creator-reserved) coerced to
     `"secret"` with a note, never dropped (RECON note 2).
   - `involved_entities`: list of NAMES resolved against the scope
     roster (location: public occupants; faction: members) — the
     faction id itself is APPENDED code-side for faction scope; an
     unresolved name is dropped FROM THE LIST with a note, never the
     whole event.
   - `location_id`: FORCED code-side to `scope_id` for location scope
     (bare Name — joins `_FORCED_FIELDS` semantics, see item 6); for
     faction scope, resolved from optional `payload["location"]` name
     against ACTIVE locations of the world, else None.
   - Payload:
     `{"title", "description", "type", "knowledge_status",
     "involved_entities", "location_id"}`; `target_table="event"`;
     `target_id=None`; rationale defaulting as tick.py's existing idiom.
   - Emit dedup within the call: casefolded title seen twice -> second
     dropped with note; then the quota cap.

4. **Canon-write helper (`src/world_engine/writes.py`).**
   `write_event(db, *, world_id, title, description=None, type=None,
   knowledge_status=None, involved_entities=None, location_id=None,
   mutation_id=None) -> Event` — constructs and `db.add`s the row;
   `knowledge_status=None` lets the column default 'secret' apply
   (models.py:618-621 — the analyzer's minimal payload path, RECON F1);
   `occurred_at` stays None, `recorded_at` auto; `session_id`/`batch_id`
   stay None (the mutation row's `tick_id`/`conversation_id` is the
   provenance anchor). Caller owns the transaction. The ONLY place
   `Event(` is constructed in gameplay code.

5. **Apply branch (`cockpit/app.py`, `_apply_mutation`).**
   New `event_creation` branch; docstring's "Implemented types" gains
   it, "Unimplemented" shrinks to `entity_creation, other`:
   - Tolerant of BOTH payload generations (RECON F1): `title` required
     (missing -> error string, Needs attention); analyzer-shaped
     payloads carry raw ids in `involved_entities` and no
     status/location — passed through as-is (write_event defaults
     apply).
   - `knowledge_status` clamp repeated at apply (defense in depth):
     anything outside `{"secret","public","confirmed"}` -> 'secret';
     'confirmed' ACCEPTED here (a creator may have edited the payload
     at review — the review surface is the creator's hand).
   - `location_id`, when present, must resolve to an ACTIVE location
     entity of the world -> else error string, nothing written.
   - Write via `write_event(...)`, inside the existing per-row
     SAVEPOINT.
   - `_find_applied_duplicate` tick branch gains `event_creation`:
     duplicate iff an Event row exists with the same normalized
     (casefold/strip) title AND same `location_id` (NULL matches NULL),
     same world (RECON F5) — canon-existence, never tick_id equality.
     Conversation-sourced event_creation keeps its historical
     no-guard behavior? NO — the same canon check applies regardless of
     source (the guard's tick branch keys on `conversation_id IS NULL`;
     ALSO add the same title+location existence check to the
     conversation branch for event_creation, so a --force re-analysis
     cannot double-apply an event either).

6. **Verify checks (`tooling/verify/checks/world_tick.py` +
   `single_canon_write.py`).**
   - Rule 9: the string `"event_creation"` does not appear inside
     `_normalize_tick_item` nor in `_TICK_MUTATION_TYPES` /
     `_TICK_TYPE_ALIASES` values (the per-NPC contract stays closed).
   - Rule 10: `SCOPE_EVENT_QUOTA` module constant exists and is
     referenced in the scope emit path (rule-7 idiom).
   - Rule 11: in `_normalize_scope_event`, no `.get("location_id")` on
     the model payload; the location-scope payload dict's
     `"location_id"` value is a bare Name (extend `_FORCED_FIELDS`
     handling or a dedicated scan — executor picks the lighter, the
     existing rule-3 walker already covers dict-literal shape checks).
   - single_canon_write: `Event(` constructed only in
     `src/world_engine/writes.py` (seed scripts exempt, same exemption
     idiom as the other constructors).

7. **Prompt head (`scripts/seed_pilot.py` +
   `scripts/apply_ticket_0017_prompt_updates.py`).**
   `WORLD_TICK_EVENTS_SYSTEM_PROMPT` / `..._USER_TEMPLATE`, registered
   `id="pt-world-tick-events"`, `usage="world_tick_events"` (unique),
   `world_id=None`, `destination="local"`, variables
   `["event_context", "interval_label"]`. Contract: JSON array only,
   `[]` legitimate ("a quiet interval is a legitimate answer" — 0014
   wording); max 3 items; EXACT keys `mutation_type`
   ("event_creation"), `target_table` ("event"), `target_id` (null),
   `payload` (`{"title","description","type","knowledge_status",
   "involved_entities":[names],"location":<optional name, faction
   scope only>}`), `rationale`; type vocabulary enumerated;
   knowledge_status: `secret` for covert happenings, `public` for
   openly visible ones — never `confirmed`; reference people/places by
   NAME from the briefing only; no world-specific examples (universal
   template rule). Scale block reuses «{interval_label}». Delivery
   script: HEAD-ABSENT branch (0014 shape) + append-version on re-run
   drift; idempotent.

## Scope OUT

- Agendas (A1/B2) and entity creation (H1/I2) — the next chantiers.
- Event -> NPC knowledge propagation (beyond the 0016 return delta);
  world-scope tick lane; automatic triggers (I3); in-game time.
- Creator CRUD/UI for events — the live gate flips knowledge_status via
  SQL if needed; a cockpit surface is its own future chantier.
- Any change to the per-NPC contract, briefing, or prompt
  (`pt-world-tick` untouched — no new version this ticket).
- `batch_id`/`session_id` semantics for tick events (stay NULL).

## Invariants to defend

- **Model proposes, code judges** — names resolved against
  code-computed rosters; ids never model-authored; location_id forced
  for location scope; status clamped.
- **Exclusion is structural** — both briefings' recent-events sections
  filter `knowledge_status IN ('public','confirmed')` at query
  construction; the full-interiority exception (secret memberships in
  the FACTION briefing) is the logged, creator-gated exception — its
  extension is re-logged this chantier, never silently widened.
- **Single canon-write path** — `Event(` only in `write_event`;
  `_apply_mutation` is the sole apply path for both producers.
- **One transaction per invocation** — scope events join the per-NPC
  rows in the single end-of-run commit; a crashed invocation writes
  nothing.
- **Closed contracts stay closed** — the per-NPC frozenset is untouched;
  the scope call has its OWN closed shape.
- **C2** — everything lands as `proposed`; nothing auto-applies.
- **Tick-guard doctrine** — canon-existence (title+location), never
  tick_id equality; extended to the conversation branch for this type.

## Done means

Machine gate (`python tooling/verify/run.py`, fail-closed):
- [ ] Rules 9-11 pass; rules 1-8 still green -> tooling/verify/checks/world_tick.py
- [ ] Event constructed only in writes.py -> tooling/verify/checks/single_canon_write.py
- [ ] Full suite green -> tooling/verify/run.py

Live gate (Nia):
- [ ] Backup; `python scripts/apply_ticket_0017_prompt_updates.py` (head created; immediate re-run: no-op)
- [ ] Location-scoped tick on the tavern: R3 summary shows `scope_events`; event proposals in the queue (TICK badge) alongside per-NPC ones; a 4th+ event or duplicate title appears as a dropped note
- [ ] Faction-scoped tick: faction-flavored proposals; involved_entities resolve to member ids + the faction id; an invented name is dropped from the list, event kept
- [ ] npcs-scoped tick: NO scope_events entry, behavior identical to 0015
- [ ] Approve a `public` event at the tavern, leave, re-enter: the 0016 delta names it; approve a `secret` one: absent from the delta
- [ ] Re-approve the same event -> "Needs attention" (canon guard); a dormant conversation-sourced event_creation in the queue (if any) applies cleanly
- [ ] Preview/inspect: the faction briefing shows secret memberships (full-interiority extension) and never appears anywhere but the tick surface

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new section "WORLD TICK
  — scope-level event producer (BRIEF-0017-a)": scope-shapes-the-briefing
  doctrine (Nia's decoupling correction verbatim), quota J1, the
  knowledge_status clamp (confirmed creator-reserved), the guard
  extension to the conversation branch, and the RE-LOGGED
  full-interiority extension to the faction briefing.
- `world-engine-schema.md` — `event` section gains its producers note
  (tick scope call + awakened analyzer channel) and the payload shapes;
  changelog entry (no version bump) in
  `world-engine-schema-changelog.md`.
- `CLAUDE.md` — freshness contract decides (tick mutation-type
  enumerations, if listed).

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **The scope event call runs IN ADDITION to the per-NPC ticks** on
   location/faction scopes (one button, two granularities). Reverse = a
   separate cockpit button "Générer des événements" decoupled from NPC
   ticking.
2. **Quota = 3 events per scope call.** Reverse = any other constant;
   it is one named constant.
3. **The guard's title+location canon check is extended to
   conversation-sourced event_creation too** (a --force re-analysis
   must not double an event). Reverse = tick-only guard, conversation
   channel stays historically unguarded for this type.
4. **Faction briefing gets full interiority (secret memberships,
   tensions)** — the 0014 exception extended to the same creator-gated
   surface, re-logged. Reverse = faction briefing routes through
   read_public_memberships and drops internal_tensions (events become
   blinder but the exception stays narrow).
5. **`confirmed` is creator-reserved** — the model can propose
   secret|public only; the apply branch accepts confirmed (creator may
   edit at review). Reverse = model may propose all three.
6. **Tick events carry `session_id=NULL`/`batch_id=NULL`** — the
   mutation row is the provenance. Reverse = link the open session id
   when one exists (couples off-screen events to play sessions;
   recommended against).
