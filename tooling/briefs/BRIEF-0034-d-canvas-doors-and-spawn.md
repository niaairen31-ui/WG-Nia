# BRIEF — Step "Canvas doors, spawn-at-door and the travel affordance" (TICKET-0034, BRIEF-0034-d)

## Context

Everything the server owes this ticket exists after BRIEF-0034-a/-b/-c: doors
are stored and authored, `doors_in_range` rides the proximity call,
`GET /api/spatial/spawn` resolves the arrival point, and
`POST /api/spatial/travel` moves the player behind a four-check gate. Three
server surfaces currently have no caller. This step wires the Play canvas to
them and closes the dette named verbatim at `cockpit/index.html:3311` —
*"TRANSITIONAL SPAWN (TICKET-0032): fixed center until the door chantier
introduces spawn-at-door"* — which is the ticket's stated request:
*"J'apparais toujours a la porte."*

Frontend rules are advisory tier (H1, TICKET-0027): the checks do not gate
this file. That makes Scope OUT and the live gate the protection here.

Locked decisions carried here: C1 — proximity affordance, a button, chosen
knowingly as the pilot shape; D1 — doors ride the existing on-stop proximity
call, no new cadence; F1/G1 — the server resolves the spawn, the client
carries the transient origin.

## Scope IN

All changes are in `src/world_engine/cockpit/index.html`, in the spatial Play
tab (`index.html:3237-3720`).

1. **Transient origin state**, beside the existing spatial state vars: one new
   module-scoped variable

   ```js
   let _spatialArrivalFrom = null;  // transient origin (G1): the location we door-travelled FROM, or null
   ```

   Comment above it, verbatim:

   ```
   // TICKET-0034 (G1): the origin lives HERE and only here — in a page
   // variable, for the length of one arrival. The server persists no
   // position and no last-location by decision (Q1); a reload, a narrative
   // travel or a creator god-mode move legitimately loses it and costs a
   // center spawn, never an error. Do not "fix" that by storing it
   // anywhere durable.
   ```

2. **Spawn-at-door** — replace the transitional center spawn
   (`index.html:3311-3315`). Delete the TRANSITIONAL SPAWN comment and its
   fixed-center assignment; `spatialActivate()` instead awaits

   ```
   GET /api/spatial/spawn?location_id=<id>&from_location_id=<_spatialArrivalFrom or omitted>
   ```

   and seeds `_spatialConfirmed = { x: <resp.x>, y: <resp.y> }`. Then clear
   `_spatialArrivalFrom = null` — it is consumed exactly once, by the arrival
   it describes.

   On a non-200 from the spawn endpoint: fall back to the bounds center
   client-side and render the room. The tab must never fail to open because a
   door could not be resolved. Log to the console; no user-facing error.

3. **Door rendering** — in the canvas draw pass, after obstacles and before
   NPCs/player, draw every door from the current door list (Scope IN 4):
   - a filled marker at the door's `(x, y)` in local coordinates, visually
     distinct from both obstacles and NPC dots, sized in world-meters like
     everything else on this canvas so it scales with the room;
   - the **destination entity's name** rendered beside it, from
     `target_name` — this is the reader that kept a `label` column off the
     `door` table (BRIEF-0034-a Scope OUT). Do not invent a client-side label.
   - a door within reach renders in the affordance-active style, matching
     however the existing canvas already distinguishes an in-range NPC. Reuse
     that pattern; do not introduce a second visual language for "reachable".

4. **Door list source** — the drawable doors come from the location payload
   already fetched by `spatialActivate()` if it carries them; otherwise fetch
   them once per activation from the location detail endpoint's `doors` array
   (BRIEF-0034-a Scope IN 6) and filter out `edge_live: false` rows.

   Verbatim comment at the filter:

   ```
   // edge_live:false rows are the CREATOR's view — an orphan door whose
   // connects_to relation died, surfaced in the sheet so it can be fixed
   // (BRIEF-0034-a). In play they do not exist. The server filters them
   // too (spatial_doors.location_doors, B1's read half) and re-judges at
   // the travel gate; this filter is cosmetic honesty, never the guard.
   ```

   Refresh the list on activation only. A door authored mid-session appears
   on the next tab activation — matching how the canvas already treats
   geometry.

5. **Affordance** — in the existing on-stop proximity handler (the 200 ms
   debounce that already populates the "Parler" affordance), read the new
   `doors_in_range` key from the same response (D1: no second call, no new
   cadence) and render, beside the existing NPC affordance and in the same
   pattern, one button per door in range:

   `Aller à <target_name>`

   Empty `doors_in_range` -> no button, exactly as an empty `in_range` yields
   no "Parler".

6. **Travel** — clicking `Aller à X`:
   a. disable the button (a double-click must not fire two travels);
   b. `POST /api/spatial/travel` with `{door_id, position: {x, y}}` where the
      position is the client's current confirmed position — the same value the
      proximity call used;
   c. on 200: set `_spatialArrivalFrom = <resp.origin_location_id>`, then
      re-run `spatialActivate()` — the same path a fresh tab open takes, so
      the room, the geometry, the NPCs and the spawn all come from the server
      in one place. Do not hand-patch the local state.
   d. on 409/404: re-enable the button, log to the console, and re-run the
      proximity call so the affordance re-syncs with what the server actually
      allows. No modal, no alert — a refused travel means the client's picture
      was stale, and refreshing it IS the message.

7. **Docs** (see Docs to update).

## Scope OUT

- **Walk-through / crossing the door by moving into it (C2)** — permanently
  out: it would force `move-check` to write. The later chantier is C3
  (`move-check` emits an advisory `door_crossed`, the client fires the SAME
  endpoint this step already calls). Do not add a crossing test to the move
  loop, and do not pre-build a `door_crossed` reader.
- **Punching an opening in the wall under the door** — C1 keeps the wall
  solid; the door is a marker you walk up to, not a gap.
- **A door hitbox, or blocking the player from standing on the door point** —
  no reader.
- **Any new server call cadence** — D1 rides the existing on-stop proximity
  debounce. No door polling, no per-frame door distance check, no second
  endpoint call while walking.
- **Client-side distance judging to decide the affordance** — `doors_in_range`
  comes from the server. A `Math.hypot` deciding whether to show the button
  forks the sole distance authority in the one file that is not checked for
  it (H1, advisory). Do not.
- **Client-side neighbour filtering** — the door list is already
  neighbour-restricted twice server-side.
- **Storing `_spatialArrivalFrom` in `localStorage`, `sessionStorage`, a
  cookie, or the URL** — G1. A lost origin costs a center spawn, by design.
- **Animating the transition, a fade, a loading overlay** — no requirement.
- **Rendering doors on the creator's geometry panel canvas** — the creator
  panel is numeric inputs (BRIEF-0034-a Scope IN 8); a graphical door editor
  is deferred alongside the graphical obstacle editor (D'2, TICKET-0029).
- **Showing orphan (`edge_live: false`) doors in play** — creator-only.
- **Touching the WASD move loop, `move-check`, the NPC affordance, or the
  obstacle draw pass** beyond adding the door pass — REPORT ONLY.
- **Refactoring the spatial tab** while in there (it is the ungoverned
  8,834-line frontend; the pull is real) — REPORT ONLY.

## Invariants to defend

- **The client is not the judge.** The affordance, the door list and the spawn
  point all come from the server; the client renders decisions it did not
  make. The temptation in a single-file vanilla-JS frontend with no gate is a
  local distance check "to avoid the round-trip" — it would fork the sole
  distance authority (`placement.py:1-6`) into the one file no check guards.
- **The frontend is advisory tier (H1)** — no verify check will catch a
  violation here. The live gate is the only gate. Which is why this brief
  spells out the temptations rather than trusting review.
- **Position is transient (Q1)** — the client owns it, nothing persists it,
  and the origin is a page variable with a one-arrival lifetime.
- **`index.html:3311`'s documented center-spawn behavior survives as the
  fallback**, not as the default: if the center lies inside an obstacle the
  judge blocks all movement by design — fix the location's geometry, not this
  code (`geometry.clip_segment`'s degenerate-origin rule, carried through
  `resolve_spawn`).
- **No build step, no framework, no new dependency** (CLAUDE.md:17) — vanilla
  JS, single file.

## Done means

- [ ] `grep -n "TRANSITIONAL SPAWN" src/world_engine/cockpit/index.html`
      returns nothing — the TICKET-0032 dette is closed, not merely
      superseded.
- [ ] `grep -n "Math.hypot\|localStorage\|sessionStorage" ` on the spatial tab
      region returns nothing new.
- [ ] Full verify suite green (unchanged: frontend is advisory tier, and this
      step must not move any check's verdict).
- [ ] Live gate — fixture from BRIEF-0034-a/-b (A and B linked by
      `connects_to`, both spatial with bounds `40 x 30`, A's door toward B at
      `(2, 15)`, B's door toward A at `(38, 15)`):
      - Open the Play tab in A: the door renders at `(2, 15)` labelled with
        B's name.
      - Walk to it and stop: the door switches to the reachable style and an
        `Aller à <B>` button appears beside the existing "Parler" affordance.
      - Click it: the location changes to B **and the player circle stands at
        B's door back to A — at `(38, 15)`, not at B's center.** This is the
        ticket's request, seen live.
      - Walk back through B's door: the player arrives in A at `(2, 15)`.
      - Stop far from a door: no `Aller à` button.
      - Reload the page while in B: the player spawns at B's center (origin
        lost, by design), no error.
      - Travel to B narratively (through conversation travel), then open the
        Play tab: center spawn, no error.
      - Delete the `connects_to` relation between A and B, reopen the Play tab
        in A: the door is gone from the canvas and no affordance appears. The
        `door` row still exists in the DB.
      - Re-create the relation, reopen: the door is back.
      - With the tab open in A and standing at the door, delete the relation
        server-side, then click the stale `Aller à <B>` button: 409, the
        button re-enables, the affordance disappears on the re-sync, the
        player stays in A. No alert, no broken tab.
      - Author a door in A toward B at a point inside a wall, travel B -> A:
        the player spawns at A's center, no error.
      - Double-click `Aller à X` fast: one travel, not two.
      - A location with no doors: the Play tab opens and behaves exactly as
        before this ticket.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` / changelog: **no schema change this step** — no
  entry, no version bump. Say so explicitly in the close note.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append the closing 0034
  block — C1's affordance as the deliberate pilot shape, with the note that
  the walk-through successor is C3 and that this step's `POST /api/spatial/travel`
  call site is the piece C3 reuses unchanged; D1's no-new-cadence wiring;
  G1's page-scoped origin and its one-arrival lifetime; the destination-name
  label as the reader that kept `door.label` off the schema.
- `CLAUDE.md`: no new standing rule expected — the door rules landed in
  BRIEF-0034-a/-b/-c. REPORT if execution reveals one.
- Close the TICKET-0034 file: status `live-gate`, then `done` once Nia signs
  the live checklist.
