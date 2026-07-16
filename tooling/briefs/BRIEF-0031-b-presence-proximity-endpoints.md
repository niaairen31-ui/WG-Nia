# BRIEF — Step "Presence + proximity endpoints" (TICKET-0031, BRIEF-0031-b)

## Context

BRIEF-0031-a shipped `placement.py` (pure placement + the sole
`distance`) and `cockpit/spatial_presence.py::npc_positions` (the sole
assembler). This brief exposes the two read surfaces in
`routes/spatial.py` — whose 0030 docstring already reserves the seat —
and writes the TICKET-0031 decision record. No frontend ships here
(0032's job); the dialogue flow is NOT modified (G-A advisory gate).

Locked decisions (intake, TICKET-0031):
- **E2** — two endpoints, one derivation. Presence (GET) is what the
  0032 canvas draws; proximity (POST) is what the client calls when the
  player slows/stops near a circle. Draw cadence and interaction
  cadence never share an endpoint. Both are thin callers of
  `npc_positions` — `routes/spatial.py` stays a caller only (D1-0030).
- **G-A** — advisory gate. The proximity result enables the client-side
  talk affordance; `POST /api/conversations/start` and
  `/api/scene/join` are byte-for-byte untouched. G-B (optional
  `position` re-judged in start_conversation when the location has
  spatial mode) is recorded as a compatible evolution, not built.
- **Threshold** — `placement.INTERACTION_RANGE = 2.0`, echoed in every
  proximity response so 0032 never hardcodes it.
- **Guards mirror move-check (D2-0030)** — role doctrine: a player
  client must not probe presence or distances of a location the PC is
  not in.

## Scope IN

1. **`GET /api/spatial/presence`** in `routes/spatial.py`, query params
   `location_id: str`, `player_id: Optional[str]` (same default
   resolution as move-check).
   - Guards, in order (move-check parity): 404 unknown player; 409
     `location_id` != player's `current_location_id`; 404 unknown
     location; 409 no spatial mode (NULL bounds).
   - Response: `{"npcs": [{"id", "name", "x", "y"}]}` — straight from
     `npc_positions`. Empty list is a valid response (nobody present).
   - Handler docstring re-states the transient-adjudication register:
     read-only, zero writes of any kind.
   - Deliberately does NOT return wall geometry: 0030 deferred the
     play-facing geometry READ endpoint to 0032's intake. One endpoint,
     one reader.

2. **`POST /api/spatial/proximity`** in `routes/spatial.py`, body:

   ```python
   class ProximityBody(BaseModel):
       location_id: str
       position: PointBody          # reuse 0030's PointBody
   ```
   - Guards: the four above, plus 422 non-finite position
     (move-check parity, `math.isfinite`).
   - Logic: `npcs = npc_positions(...)`; for each,
     `d = placement.distance(position, (npc.x, npc.y))`; keep
     `d <= placement.INTERACTION_RANGE`; sort ascending by distance.
   - Response:
     `{"in_range": [{"npc_id", "name", "distance"}],
       "threshold": placement.INTERACTION_RANGE}` —
     distances rounded to 3 decimals (mm grain, EPS_METERS kinship).
     Empty `in_range` is a normal answer, never an error.
   - The handler contains NO distance math of its own — it calls
     `placement.distance` (single-site rule); a second Euclidean
     inline here is the exact defect the earshot rail forbids.

3. **Client handoff contract (documented, not implemented)** — a short
   comment block above the proximity route records the G-A handoff for
   0032: the client maps returned `npc_id`s onto the rosters already
   present in `_scene_response`, enables "Parler" for in-range NPCs,
   and fires the EXISTING `POST /api/conversations/start`. Zero server
   coupling.

4. **`ARCHITECTURE_DECISIONS.md`** — single block for the ticket
   (0030 precedent), header
   `## NPC SPATIAL PRESENCE + PROXIMITY ENDPOINT (BRIEF-0031-a, BRIEF-0031-b, no schema change)`,
   covering: A (deterministic pure derivation, zero storage; B/C/D
   rejected with reasons), A-i (placement.py pure sibling +
   spatial_presence.py sole assembler; player exclusion at assembler
   level), the sha256-never-hash() determinism doctrine, E2 (two
   endpoints, one derivation), G-A (advisory gate; G-B recorded as
   compatible evolution), threshold constant, and the **earshot rail**:
   "`placement.distance` and `spatial_presence.npc_positions` are the
   sole spatial-distance site; any future audibility reader imports
   them, never recomputes" — gate-guarded by `placement_unit.py` the
   way `geometry_unit.py` guards the collision authority. Scope OUT
   list: canvas/WASD/frontend (0032), geometry READ endpoint (0032
   intake), earshot implementation, spawn zones, per-location
   threshold, persistent NPC coordinates (workstream-wide never for
   this ticket), G-B structural gate.
   `DECISIONS_INDEX.md` regenerated via `gen_decisions_index.py`, never
   hand-edited.

5. **CLAUDE.md** — no new section; if the File structure tree is
   touched to add the two modules' one-line roles, `claude_md_contract`
   must stay green.

## Scope OUT (this brief)

- Any change to `start_conversation`, `scene_join`, `/say`, or any
  dialogue path — G-A locked.
- Canvas rendering, WASD, call cadence, client slide — ticket 0032.
- Wall-geometry read endpoint — 0032 intake decides its shape.
- Rate limiting — 0032 owns call cadence.

## Verify

- Full suite green: `module_budget.py` (spatial.py stays small),
  `single_canon_write.py` (zero new write sites),
  `decisions_index.py` (block header + regenerated index),
  `claude_md_contract.py`, `placement_unit.py` (from -a, still green).
- Live smoke (ticket's human gate): presence circles on the 0029 demo
  location, F5 + restart stability, proximity in/out of the 2.0 m
  threshold, the four guards on both endpoints, dialogue unchanged.
