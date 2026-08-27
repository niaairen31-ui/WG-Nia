# BRIEF — Step "Door-travel endpoint" (TICKET-0034, BRIEF-0034-c)

## Context

BRIEF-0034-b can say which doors are within reach of a transient position and
where a player should stand on arrival. Nothing moves the player yet: the two
existing `_perform_travel` callers both refuse this case — the in-fiction one
(`routes/play.py:244`) requires an open conversation, and the creator one
(`routes/play.py:357`) is god-mode with no neighbour restriction. This step
adds the third caller: the door-gated travel the Play canvas fires.

Locked decisions carried here: E1 + J1 — `POST /api/spatial/travel`, living in
`routes/play.py` because it WRITES (`_perform_travel` closes conversations,
closes `gathering_member` rows and moves the character) and
`routes/spatial.py`'s zero-write register (`routes/spatial.py:4-10`) forbids
it there; the URL prefix names the player surface, not the module (the
`scene/join`-in-`routes/scene.py` precedent). G1 — the origin is transient and
client-carried: `_perform_travel` returns it, the client passes it to the
spawn endpoint, nothing is persisted.

**Gate hardness is not uniform, and the brief says so on purpose.** "No travel
to a location that is not directly linked" is HARD: the door row cannot exist
toward a non-neighbour (B1's write gate) and cannot resolve toward a dead edge
(B1's read filter), so `door_id` alone carries the neighbour restriction — the
same predicate that surfaced the affordance is the one that authorises the
move. "The player really stood at the door" is GOOD-FAITH: the position is
client-declared, the server persists no position (Q1), and it has nothing to
check it against. Same posture as proximity's advisory gate (G-A). Do not
paper over the difference, and do not "fix" it by persisting a position.

## Scope IN

1. **Origin in the travel result — `src/world_engine/cockpit/play_stream.py`**,
   in `_perform_travel` (`play_stream.py:930`).

   Capture the character's current location BEFORE step 3 mutates it, and add
   one key to the `ok` return (`play_stream.py:999`):

   ```python
   return {"status": "ok", "location_id": location_id, "origin_location_id": origin_location_id}
   ```

   Additive only: the `noop` branch is untouched (origin equals destination
   there; no reader wants it), and both existing callers pass the dict through
   unchanged. Comment at the capture site, verbatim:

   ```
   # Captured before the mutation below: the caller's ONLY way back to
   # where the player came from (G1, TICKET-0034). The origin is transient
   # by decision — no character.last_location_id column exists and none
   # will: a transient concern never earns a canon write. The spatial
   # client carries this value to GET /api/spatial/spawn to be placed at
   # the return door.
   ```

2. **Endpoint — `src/world_engine/cockpit/routes/play.py`**, placed directly
   after the creator travel route (`routes/play.py:357`), so all three
   `_perform_travel` callers sit in one module.

   ```python
   class SpatialTravelPosition(BaseModel):
       x: float
       y: float


   class SpatialTravelBody(BaseModel):
       door_id: str
       position: SpatialTravelPosition
       player_id: Optional[str] = None


   @router.post("/api/spatial/travel")
   def spatial_travel(body: SpatialTravelBody, db: Session = Depends(get_session)) -> dict:
       """Door-gated in-fiction travel from the Play canvas (TICKET-0034,
       E1/J1).

       Lives HERE, not in routes/spatial.py, because it writes: it is the
       third caller of _perform_travel, beside the conversation route and
       the creator route above. routes/spatial.py is a zero-write register
       (routes/spatial.py:4-10); the /api/spatial/ URL prefix names the
       player-facing surface, not the module (scene/join precedent).

       The neighbour restriction is a property of the in-fiction callers
       (C1, BRIEF-16), and here it is carried by `door_id` itself: a door
       toward a non-neighbour cannot be written (write_location_doors) and
       a door toward a dead edge does not resolve (spatial_doors.
       location_doors). This handler re-judges that same predicate rather
       than trusting the client's earlier proximity call.

       GATE HARDNESS IS NOT UNIFORM. Checks 1-3 are structural: judged
       against canon, a client cannot bypass them. Check 4 is good faith:
       `position` is client-declared and the server persists no position
       (Q1), so it has nothing to verify it against — the same advisory
       posture as proximity's G-A gate. Persisting a position to harden it
       is NOT the fix; it is the decision Q1 rejected.
       """
   ```

   Body of the handler, in this order, writing nothing before every check has
   passed:
   a. Resolve the player: `body.player_id` if given, else
      `_crud._player_character_id(db)`; 404 `"no player character"` if none.
      Load the `Character`; 404 if absent.
   b. Load the `Door` by `body.door_id`; **404** if absent.
   c. **409** `"door is not in the player's current location"` if
      `door.location_id != char.current_location_id`.
   d. **409** `"door does not resolve"` if `door.id` is not in
      `spatial_doors.location_doors(char.current_location_id, char.world_id, db)`
      — this is the B1 read filter and the neighbour restriction, in one
      predicate. Do NOT re-implement the filter here; call the module.
   e. **409** `"out of door range"` if
      `placement.distance((body.position.x, body.position.y), (door.x, door.y)) > placement.DOOR_RANGE`.
      Distance via `placement.distance` only — never an inline `math.hypot`.
   f. `return _perform_travel(char.id, door.target_location_id, db)` — the
      result dict, `origin_location_id` included, passed through unchanged.

   No new guard chain: do NOT import `_resolve_spatial_location` from
   `routes/spatial.py` (a routes -> routes import is exactly what K1's seam
   exists to prevent), and do NOT check `bounds_width is not null`. A door
   only exists where a creator authored one; the spatial-mode check belongs
   to the read endpoints that draw the room, not to a move whose legitimacy
   is already established by (c) + (d).

3. **Verify — new check `tooling/verify/checks/spatial_door_travel.py`**, on
   the `tooling/verify/checks/scene_join_target.py` shape: fresh temp-file
   SQLite (`WORLD_ENGINE_DATABASE_URL` set BEFORE any `world_engine` import,
   `world_engine*` modules purged from `sys.modules`), `TestClient`, hard
   asserts, one summary PASS line. No Ollama, no monkeypatch needed — this
   path makes zero model calls.

   Fixture (`_seed_fixture`): one world, one player character in A, locations
   A and B both with bounds `40 x 30`, an active mutual `connects_to`
   relation between them, A's door toward B at `(2, 15)`, B's door toward A
   at `(38, 15)`, plus a third location C with NO `connects_to` edge to A and
   a `door` row A -> C forced in directly (bypassing the write path, which
   would reject it — this is the fixture proving the READ filter is
   load-bearing on its own, not merely a second opinion on the write gate).

   Cases, each asserting the HTTP status AND that
   `character.current_location_id` is unchanged and `Conversation` /
   `GatheringMember` row counts are unchanged on every rejection:
   1. Unknown `door_id` -> 404, zero rows written.
   2. Door whose `location_id` is B while the player is in A -> 409.
   3. Door A -> C (no `connects_to` edge) -> 409. **This is the hard
      guarantee under test**: the client asked for a real door row, in the
      player's real location, from a legitimate position — and the move is
      refused because the map does not link A to C.
   4. Same as 3 after creating the A -> C `connects_to` relation -> 200 and
      the player is in C. Then delete the relation and travel back -> 409.
      (The filter is live state, not a snapshot.)
   5. Target soft-deleted (`entity.status = 'archived'`) -> 409.
   6. Position `(10, 15)` against A's door at `(2, 15)` -> 409 `out of door
      range`; position `(2.5, 15)` -> 200.
   7. Happy path: `character.current_location_id == B`, response
      `status == "ok"`, `location_id == B`, `origin_location_id == A`.
   8. Regression on the shared helper: the creator travel route
      (`POST /api/travel`) still returns `status`/`location_id` and now also
      carries `origin_location_id`; the key is additive, nothing else in the
      shape moved.

   Also assert, AST-side (or by `grep` on the source text, in the check's own
   idiom): `routes/play.py`'s `spatial_travel` contains no `math.` call and
   no `import` of `routes.spatial`.

4. **Docs** (see Docs to update).

## Scope OUT

- **Canvas rendering, the "Aller à X" button, spawn-at-door on the client** —
  BRIEF-0034-d. This endpoint ships with no caller; the Play tab still spawns
  at the raw center after this step (`index.html:3311` untouched).
- **Walk-through / automatic door crossing (C2)** — permanently out: it would
  force `move-check` to write. The later chantier is C3 — `move-check` emits
  an advisory `door_crossed`, the client fires THIS endpoint, which does not
  move. Do not add a `door_crossed` key to `move-check` here.
- **Persisting the player's position** to harden check (e) — decision Q1
  rejected it; the good-faith gate is the accepted consequence, on record in
  the ticket. Not a bug to fix.
- **Persisting the origin** (`character.last_location_id`) — G1 rejected it.
- **A `noop` branch origin key** — no reader.
- **Touching `_perform_travel`'s behavior** — this step adds one key to one
  return dict. Its transaction, its `analyze_window` call, its membership
  closing and its `noop` semantics are untouched. Any smell found in it:
  REPORT ONLY.
- **Refactoring the two existing travel routes** to share a helper with this
  one — they gate differently on purpose (conversation-bound, god-mode,
  door-bound). REPORT ONLY.
- **Widening or moving `_resolve_spatial_location`** — Scope IN 2 deliberately
  does not use it.
- **Locked doors / `access_level` checks in the gate** — named deferral of
  TICKET-0034; the gate has four checks and no fifth.
- **Rate-limiting or debouncing travel server-side** — no reader, no
  requirement.

## Invariants to defend

- **Two sanctioned canon-write paths, no others** (CLAUDE.md:158). This
  endpoint writes nothing itself: `character` moves via `_perform_travel`,
  already the sanctioned site in `canon_write_policy.txt`. The temptation is
  a "quick" `char.current_location_id = ...; db.commit()` in the handler
  instead of delegating. `single_canon_write.py` must stay green with **no
  new site** — if this step adds a line to `canon_write_policy.txt`,
  something went wrong.
- **Commit before touching any canon-writing path** (CLAUDE.md:166) —
  `_perform_travel` is one.
- **`routes/spatial.py` stays zero-write.** The endpoint's URL says
  `/api/spatial/`; the pull to file it next to its siblings will be strong.
  It goes in `routes/play.py`. That is the whole point of J1.
- **Sole distance authority** (`placement.py:1-6`) — check (e) calls
  `placement.distance`.
- **Creator-CRUD edits that change `current_location_id` must close open
  `gathering_member` rows** (CLAUDE.md) — `_perform_travel` already does this;
  delegating is what keeps the invariant free.
- **`connects_to` is location map topology, never a social signal**
  (CLAUDE.md:210) — check (d) reads it as topology, via the module.
- **Module budget** — `routes/play.py` is at 649/1000 lines after the
  TICKET-0032 split; this addition has room. If it does not, the failing check
  IS the mechanism: REPORT, do not baseline.

## Done means

- [ ] Full verify suite green, including the new `spatial_door_travel.py`.
- [ ] `single_canon_write.py` green with **zero new sites** in
      `canon_write_policy.txt` (diff on that file is empty for this step).
- [ ] `spatial_door_travel.py` red-tested: temporarily make check (d) return
      early -> case 3 FAILS. Reverted.
- [ ] Live smoke (danger class `db_write`; fixture from BRIEF-0034-a/-b, A and
      B linked and both spatial with doors on both sides):
      - `POST /api/spatial/travel` with A's `door_id` and position
        `(2.5, 15)` -> 200, `{"status": "ok", "location_id": "<B>",
        "origin_location_id": "<A>"}`; the player's `current_location_id` is B
        in the DB.
      - The player's open `gathering_member` rows in A are closed and open
        conversations are closed — `_perform_travel`'s existing behavior,
        unchanged by delegation.
      - Same call from `(10, 15)` -> 409, player still in A.
      - Same call with B's `door_id` while in A -> 409.
      - `POST /api/travel` (creator god-mode) still works and now returns
        `origin_location_id` — no regression on the shared helper.
      - In-fiction narrative travel through a conversation still works —
        second caller, no regression.
- [ ] Hard-gate spot check, nominative, against the live DB: delete the
      `connects_to` relation between A and B, retry the same
      `POST /api/spatial/travel` with the same `door_id` and the same
      in-range position -> 409, player still in A, the `door` row still
      present. Re-create the relation -> 200. This is the ticket's stated
      constraint — *"je ne veux pas qu'en mode spacial je puisse me déplacer
      de lieux qui ne sont pas directement liés ensemble"* — verified live, at
      the endpoint, not only at the panel.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` / changelog: **no schema change this step** — no
  entry, no version bump. Say so explicitly in the close note.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append the 0034 decision
  block for this step — E1/J1 and the module-vs-URL split (writes cannot live
  in `routes/spatial.py`; the prefix names the surface); `door_id` as the
  carrier of the neighbour restriction; the four-check gate; and, explicitly,
  the **hardness asymmetry**: checks 1-3 structural, check 4 good-faith, with
  Q1 named as the reason and the note that persisting a position is the
  rejected fix, not the pending one. G1's transient origin and why
  `character.last_location_id` does not exist.
- `CLAUDE.md`: extend the travel/`_perform_travel` area with one standing
  line — *"`_perform_travel` has three callers, all in `routes/play.py`:
  conversation-bound (in-fiction), creator god-mode, and door-gated
  (`/api/spatial/travel`, TICKET-0034). The neighbour restriction is a
  property of the in-fiction callers (C1, BRIEF-16); the door-gated caller
  carries it through `door_id`. `/api/spatial/travel` lives in
  `routes/play.py`, not `routes/spatial.py`, because it writes."*
