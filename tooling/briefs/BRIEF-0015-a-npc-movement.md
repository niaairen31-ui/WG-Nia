# BRIEF — Step "npc-move mutation: interval-scaled off-screen movement (BRIEF-0015-a-npc-movement)"

## Context

TICKET-0014 shipped the world tick (schema v1.70, live-gate validated) with
movement explicitly deferred (L3). This chantier lifts that deferral: a new
tick-only mutation type `npc_move` lets a ticked NPC relocate along the
`connects_to` graph, with the reachable radius scaled STRUCTURALLY by the
invocation's interval label — code-side hop limits, never a prompt
instruction (Nia's rationale on record: when ticks later become automatic,
the radius is what guarantees a session-close tick cannot move an NPC across
a continent). Grounding: RECON-0015 (F1-F10). Locked: E3; co-located NPCs
are NOT excluded — an approved move closes the NPC's open
`gathering_member` row even when the player shares the gathering.
danger_class: db_write only — no migration (`proposed_mutation.mutation_type`
is unconstrained TEXT; `tick_id` exists since v1.70).

## Scope IN

1. **Radius constant + reachability helper (`src/world_engine/tick.py`).**
   - `INTERVAL_HOP_RADIUS: dict[str, int | None] = {"quelques heures": 1,
     "quelques jours": 3, "quelques semaines": None}` — keys are the
     VERBATIM labels of `cockpit/app.py:4752` (`_VALID_TICK_INTERVALS`);
     `None` = unbounded. Module-level, adjustable without touching logic.
   - `_reachable_locations(db, from_location_id: str, interval_label: str)
     -> list[tuple[str, str]]` — BFS over `Relation.type == "connects_to"`
     rows among ACTIVE locations (`Entity.status == "active"`), starting at
     `from_location_id`, bounded by `INTERVAL_HOP_RADIUS[interval_label]`
     (`None` -> exhaust the connected component), origin EXCLUDED from the
     result. Returns `(entity_id, name)` pairs. This is a NEW, tick-local
     `connects_to` reader — do NOT import or refactor
     `_location_neighbours` (cockpit/app.py:1713; decision D1 stands: the
     readers stay separate). Unknown interval label -> raise `ValueError`
     (the endpoint's 422 gate makes this unreachable in production;
     fail loud, not silent, if a future caller bypasses it).

2. **Briefing section `OÙ TU PEUX ALLER` (tick.py).**
   - New header constant `H_DESTINATIONS = "OÙ TU PEUX ALLER"`, rendered
     between `H_SETTING` and `H_COMPANY` (tick.py:246-266 assembly).
   - `assemble_tick_context` gains a keyword-only parameter
     `destinations: list[tuple[str, str]] | None = None`. Body lines:
     `- <name>` plus the location entity's `description` when non-empty
     (`- <name> : <description>`). `None` or empty ->
     placeholder `(nulle part — aucun lieu accessible)`; the header ALWAYS
     renders (T1 contract: every section header in every briefing).
   - The candidate set is computed ONCE per NPC in `run_world_tick` (which
     already loads `npc_char.current_location_id`, tick.py:507-510) and
     passed BOTH to `assemble_tick_context` and to `_normalize_tick_item`
     — a single set, no drift between what the model saw and what
     resolution accepts (RECON F2). NPC with NULL location -> empty set.

3. **Type acceptance + normalizer branch (tick.py).**
   - Tick-local alias map `_TICK_TYPE_ALIASES = {**_MUTATION_TYPE_MAP,
     "npc_move": "npc_move", "move": "npc_move", "movement": "npc_move"}`;
     `_normalize_tick_item`'s lookup (tick.py:351) switches to it.
     `_TICK_MUTATION_TYPES` (tick.py:274) gains `"npc_move"`.
     `analyzer._MUTATION_TYPE_MAP` stays BYTE-IDENTICAL — conversation
     analysis and overhearing must never propose movement (RECON F4).
   - `_normalize_tick_item` gains keyword-only
     `destinations: dict[str, str]` (name.casefold() -> id, built by the
     caller from the pair list) and `from_location_id: str | None`, plus a
     `from_name: str` / `to name` lookup for display fields. New branch:
     - `mutation_type == "npc_move"`: read `payload_in["destination"]`
       (str, stripped); resolve `.casefold()` against `destinations` ONLY
       — never against all locations. Unresolved (invented name, or a real
       location outside the radius: identical failure, the model cannot
       distinguish them) -> drop with note. NPC with no
       `from_location_id` -> drop with note.
     - Payload EXACTLY: `{"npc_id": npc_id, "from_location_id":
       from_location_id, "to_location_id": <resolved id>, "from_name":
       <origin name>, "to_name": <destination name>}` — `npc_id` and
       `from_location_id` written as bare Names from the parameters
       (forced attribution, rule-3 pattern; RECON F5);
       `to_location_id` is resolved, not forced. Display names ride in
       the payload because the queue UI renders payloads verbatim
       (`_mutation_dict`, cockpit/app.py:681; RECON F9).
       `target_table = "character"`.
   - Emit-time dedup in `run_world_tick`: `seen_move: bool` per NPC — at
     most ONE `npc_move` per NPC per invocation; the first occurrence
     wins, later ones dropped with a note (same idiom as
     `seen_goal`/`seen_knowledge`/`seen_relation`, tick.py:520-560).

4. **Canon-write helper (`src/world_engine/writes.py`).**
   `write_character_location(db, *, entity_id: str, to_location_id: str,
   mutation_id: Optional[str] = None) -> Character` — loads the
   `Character` row, sets `current_location_id`, `db.add`s, returns it.
   Caller owns the transaction (module convention, `write_relation`
   precedent writes.py:172). No `change_history`: `character` has no such
   column and the creator-CRUD location edit snapshots nothing — the
   `proposed_mutation` row (from/to payload, `tick_id`, `applied_at`) is
   the durable audit trail (RECON F7). Docstring says so explicitly.

5. **Apply branch (`cockpit/app.py`, `_apply_mutation`).**
   New `npc_move` branch (and the docstring's "Implemented types" list
   gains it; "Unimplemented" keeps event_creation/entity_creation/other):
   - Load `Character` by `payload["npc_id"]`; missing row -> error string
     ("Needs attention"), nothing written.
   - **Stale-from gate (the guard for this type):**
     `character.current_location_id != payload["from_location_id"]` ->
     return an explicit error ("NPC no longer at the proposal's origin —
     world moved since the tick"). This single canon check covers the
     duplicate re-approval, the cross-run re-run duplicate, AND the
     manually-moved-since case, and correctly ALLOWS a later legitimate
     A->B->A move — per the 0014 tick-guard doctrine (canon-existence,
     never tick_id equality; RECON F6).
   - Validate `payload["to_location_id"]` resolves to an ACTIVE location
     entity of the same world; failure -> error string, nothing written.
   - Apply: `write_character_location(...)` then
     `close_open_memberships(payload["npc_id"], db)` (gathering.py:261 —
     BRIEF-53 seam; closes the NPC's open `gathering_member` rows, PLAYER
     PRESENT OR NOT — Nia's locked decision; neither call commits, the
     existing per-row SAVEPOINT owns the transaction).
   - `_find_applied_duplicate`'s tick branch (cockpit/app.py:777+) gains a
     mirror `npc_move` clause returning the same stale-from verdict, so
     the pre-write guard path and the apply path agree (symmetry with the
     other tick types' pre-write canon checks).

6. **Runner plumbing (tick.py, `run_world_tick`).**
   Per NPC, after the existing `npc_char` load: compute
   `reachable = _reachable_locations(db, npc_char.current_location_id,
   interval_label)` when the NPC has a location, else `[]`; pass it to
   `assemble_tick_context(npc_id, db, destinations=reachable)` and derive
   the normalizer's `destinations` dict + `from_location_id`/`from_name`
   from it. NOTE: `assemble_tick_context` currently runs BEFORE the model
   call and `_build_roster` after it — the reachable computation joins the
   pre-call block since the briefing needs it.

7. **Prompt version (`scripts/seed_pilot.py` +
   `scripts/apply_ticket_0015_prompt_updates.py`).**
   New `WORLD_TICK_SYSTEM_PROMPT` version: `npc_move` joins the
   mutation_type enumeration and the payload shapes
   (`npc_move -> {"destination":"<name from OÙ TU PEUX ALLER>"}`,
   target_table `character`), plus a `=== NPC_MOVE RULES ===` block:
   at most ONE npc_move for the entire interval; the destination MUST be a
   name from `OÙ TU PEUX ALLER`, nothing else; staying put is legitimate
   and is expressed by emitting NO npc_move; a move needs a motive rooted
   in the briefing (a goal, a relation, a known fact) stated in
   `rationale`. Seed text updated in place (idempotent upsert unchanged);
   live delivery via `scripts/apply_ticket_0015_prompt_updates.py` —
   0013/0014 script pattern, append-a-version branch ONLY (the
   `pt-world-tick` head exists since 0014; no head-absent branch), no-op
   when the head's current text already matches.

8. **Preview script (`scripts/preview_tick_context.py`).**
   Gains `--interval` (choices = the three verbatim labels, default
   `"quelques jours"`); computes the reachable set exactly as the runner
   does and passes it through, so the printed T1 briefing shows
   `OÙ TU PEUX ALLER` as the model will see it.

9. **Verify checks (`tooling/verify/checks/world_tick.py`).**
   - `_FORCED_FIELDS` gains `"from_location_id"` (rule 3 then bans
     `.get("from_location_id")` anywhere in tick.py and enforces
     bare-Name dict values — RECON F5; `to_location_id` deliberately NOT
     added).
   - New rule 6: `analyzer.py`'s `_MUTATION_TYPE_MAP` dict literal
     contains no key mapping to `"npc_move"` (AST walk over the literal).
   - New rule 7: `tick.py` defines `INTERVAL_HOP_RADIUS` with EXACTLY the
     three verbatim label keys, and the identifier is referenced inside
     `_reachable_locations`.
   - New rule 8: `cockpit/app.py`'s `_apply_mutation` contains no direct
     `current_location_id` attribute assignment (the write must route
     through `write_character_location`); and the `npc_move` region of
     the function references both `write_character_location` and
     `close_open_memberships` (function-scope AST scan, same idiom as
     `check_guard_branch`).

## Scope OUT

- `status_change` emission from the tick (the other half of 0014's L3) —
  still deferred.
- Automatic triggers / in-game time (I3) — untouched; the radius map is
  built FOR that future, it does not build it. No `last_tick_at` storage
  (M3 stands: the interval is passed, never persisted).
- Any analyzer/overhearing producer for `npc_move` — permanently out, not
  merely deferred: movement is a tick-only concept.
- Player movement via the tick; NPC schedules/routines; travel-time or
  multi-hop journey simulation (after apply the NPC simply IS at the
  destination); pathfinding beyond the BFS radius bound.
- Return-visit delta narration / `visit` table (G2) — next ticket.
- Endpoint/UI changes to the tick invocation surface (scope selector,
  interval selector) — none needed (RECON F10); queue UI changes — none
  needed (names ride in the payload, RECON F9).
- Refactoring `_location_neighbours` or `GET /api/locations/graph` to
  share the new BFS — D1 stands; report a real dedup opportunity if seen,
  act on nothing.

## Invariants to defend

- **Model proposes, code judges** — the destination is resolved against a
  code-computed candidate set; `npc_id` and `from_location_id` are forced
  from parameters; the model never authors ids.
- **Structural over disciplinary** — the radius is a code bound
  (dropped-with-note on violation), never a prompt request; the prompt's
  MOVE RULES are ergonomics on top of the bound, not the bound.
- **Single canon-write path** — the location write happens only inside
  `_apply_mutation`, routed through the new `writes.py` helper; the tick
  itself writes `ProposedMutation` rows only (C2 unchanged).
- **History is sacred** — `close_open_memberships` closes rows
  (`left_at = now`), never deletes; the `proposed_mutation` row is the
  movement's audit trail; no row deletion anywhere in this chantier.
- **Analyzer boundary** — `analyzer._MUTATION_TYPE_MAP` byte-identical;
  conversation analysis and overhearing gain no movement vocabulary.
- **T1 briefing contract** — every section header (now including
  `OÙ TU PEUX ALLER`) appears in every briefing, placeholder when empty.
- **Tick-guard doctrine (0014)** — duplicate protection asks the canon
  (stale-from), never compares tick_id equality.
- **`gathering_member.left_at IS NULL` single-source** — the roster reacts
  to an applied move through the existing seam; no snapshot, no parallel
  presence state.

## Done means

Machine gate (`python tooling/verify/run.py`, fail-closed):
- [ ] world_tick.py rules 1-5 still pass with the new code -> tooling/verify/checks/world_tick.py
- [ ] rule 3 extended: no `.get("from_location_id")` in tick.py; forced dict keys are bare Names -> tooling/verify/checks/world_tick.py
- [ ] rule 6: analyzer._MUTATION_TYPE_MAP carries no npc_move mapping -> tooling/verify/checks/world_tick.py
- [ ] rule 7: INTERVAL_HOP_RADIUS has exactly the three verbatim label keys and is read by _reachable_locations -> tooling/verify/checks/world_tick.py
- [ ] rule 8: _apply_mutation has no direct current_location_id assignment and its npc_move region calls write_character_location + close_open_memberships -> tooling/verify/checks/world_tick.py
- [ ] single-canon-write scan passes with the new writes.py helper -> tooling/verify/checks/single_canon_write.py
- [ ] npc_goal_read boundary untouched -> tooling/verify/checks/npc_goal_read.py

Live gate (Nia):
- [ ] `scripts/preview_tick_context.py --npc <id> --interval "quelques heures"` shows OÙ TU PEUX ALLER limited to direct neighbours; `--interval "quelques semaines"` lists the whole connected component
- [ ] A tick on an NPC yields an npc_move proposal whose queue payload shows from_name -> to_name; an invented or out-of-radius destination appears as a dropped note in the R3 summary
- [ ] Approving the npc_move: the NPC's Fiche shows the new location, its open gathering_member row is closed, and the Play roster reflects the departure — including when the player character was in the same gathering
- [ ] Move the NPC manually (creator CRUD), then approve the stale proposal -> "Needs attention", nothing applied; re-approving an already-applied move -> same verdict
- [ ] `scripts/apply_ticket_0015_prompt_updates.py` run against the live DB (append-version; immediate re-run is a no-op)

## Docs to update

- `world-engine-schema.md` — `proposed_mutation` source/type commentary
  gains `npc_move` (tick-only producer; payload shape; no schema bump —
  note "no migration" explicitly in the changelog entry).
- `world-engine-schema-changelog.md` — entry for the application-layer
  change (no version bump; precedent: BRIEF-53 entry style).
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new section "WORLD TICK
  — NPC movement (BRIEF-0015-a)": E3 radius doctrine + verbatim label
  keys, connected-component semantics, stale-from guard rationale (F6),
  the co-located decision verbatim, D1 third-reader note, display-name
  payload convention (F9).
- `CLAUDE.md` — only if its law list enumerates tick mutation types or
  `_FORCED_FIELDS`; otherwise untouched (freshness contract decides).

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **"quelques semaines" = the connected component, not all locations**
   (RECON F3). An island with no `connects_to` path stays unreachable at
   any interval — the map is the traversability truth. Reverse = radius
   `None` falls back to "all ACTIVE locations of the world".
2. **Out-of-radius and invented destinations fail identically** (one
   dropped note, no distinction). The model only ever sees in-radius
   names, so distinguishing the two cases would only ever label model
   hallucination more precisely — not worth a second code path.
3. **At most ONE npc_move per NPC per invocation**, first occurrence wins
   (mirrors the prompt's "at most one move" rule structurally). Reverse =
   last-wins or judge-both.
4. **The stale-from gate replaces the intake ticket's "tick_id + entity"
   guard** (RECON F6) — canon-existence per 0014 doctrine, strictly
   stronger. The ticket's acceptance criterion is amended accordingly.
5. **No `change_history` for the location change** (RECON F7) — the
   character table has none and the CRUD edit path snapshots nothing; the
   mutation row is the audit. Reverse = add a snapshot mechanism (bigger
   chantier, schema touch).
