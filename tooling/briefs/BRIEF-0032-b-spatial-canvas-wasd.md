# BRIEF — Step "Play (spatiale) tab: canvas, WASD lockstep movement, zoom"

Ticket: TICKET-0032 · Brief: BRIEF-0032-b · v1.00
Execution order: independent of BRIEF-0032-a (parallelizable); must land
before BRIEF-0032-c.

## Context

Tickets 0029–0031 shipped the full server surface: wall geometry readable via
`GET /api/entities/{id}` (`geometry: {bounds_width, bounds_height, obstacles}`),
movement adjudication via `POST /api/spatial/move-check` -> `{x, y, blocked}`,
and NPC circles via `GET /api/spatial/presence` -> `{npcs:[{id,name,x,y}]}`.
Nothing draws them yet. This brief grafts the standalone canvas surface onto
the cockpit: a new tab, server-lockstep WASD movement (A1/B1), wheel zoom.
Talk affordance and proximity calls are BRIEF-0032-c.

## Scope IN

All client work in `src/world_engine/cockpit/index.html`, one contiguous new
section commented
`/* ── Play (spatiale) — TICKET-0032, BRIEF-0032-b — standalone canvas,`
`outside HTMX; server-lockstep movement (A1), transient only (Q1) ── */`.

1. **New tab "Play (spatiale)"** following the cockpit's existing tab
   pattern (executor: locate the tab bar and view-switch mechanism and mirror
   it exactly — same classes, same show/hide convention). Tab body contains:
   a `<canvas id="spatial-canvas">`, a one-line status strip
   `<div id="spatial-status">` (location name, zoom level, transient notice
   verbatim: `Position transitoire — rien n'est écrit au canon.`), and an
   error container `<div id="spatial-error">`.

2. **Activation flow**: on tab activation, `GET /api/scene` for
   `location_id`/`location_name`, then `GET /api/entities/{location_id}`.
   If `geometry.bounds_width` or `bounds_height` is null -> hide canvas, show
   in `#spatial-error` verbatim:
   `Ce lieu n'a pas de mode spatial. Définissez ses dimensions dans l'éditeur de géométrie (onglet Auteur).`
   Otherwise store `{bounds, obstacles}` in module state and start the loop.
   Then `GET /api/spatial/presence?location_id=` and store NPC list.
   Deactivating the tab stops the rAF loop and the movement ticker (no
   background requests from a hidden tab).

3. **Coordinate transform & zoom**: world-meters -> pixels, y downward
   (server convention, `geometry.py:12-13`). Default scale 24 px/m. Wheel
   zoom multiplies scale by 1.1 / 0.9 per notch, clamped [8, 64] px/m,
   anchored on the cursor's world point (the world point under the cursor
   stays under the cursor). Canvas sized to its container; view centered on
   the bounds when content is smaller than the canvas, otherwise centered on
   the player.

4. **Rendering (requestAnimationFrame loop)**: each frame draw — bounds
   rectangle (wall stroke), obstacle polygons (filled, using existing cockpit
   CSS variable colors — executor picks from the `:root` palette already in
   the file, no new colors), NPC circles radius 0.35 m with name label above,
   player circle radius 0.35 m visually distinct. Idle scene must not spin
   CPU: when nothing moved and no zoom/pan changed, skip redraw (dirty flag).

5. **WASD input (H1)**: `keydown`/`keyup` listeners on `document`; ignore
   events when `document.activeElement` is an `input`, `textarea`, or
   `[contenteditable]`, or when the tab is not active. Clicking the canvas
   focuses it; Esc blurs. W/A/S/D (and arrow keys) set a direction vector,
   normalized on diagonals. Speed constant `SPATIAL_SPEED_MPS = 3.0`
   (world-m/s, walking pace; comment: `calibrate at live gate`).

6. **Server-lockstep movement (A1/B1)**: a 100 ms ticker runs ONLY while at
   least one movement key is down (plus one final tick on release).
   Each tick: `intended = confirmed + direction * SPATIAL_SPEED_MPS * 0.1`;
   `POST /api/spatial/move-check {location_id, origin: confirmed, destination: intended}`;
   on response, set `confirmed = {x, y}` from the server. The DRAWN position
   interpolates linearly toward `confirmed` (reach it in ~100 ms) — the drawn
   circle never leads the confirmed point beyond interpolation, and the
   client performs NO collision math (C3 rejected, `geometry.py:9-10`).
   In-flight guard: never more than one move-check outstanding; if the tick
   fires while one is pending, coalesce (recompute intended from the latest
   confirmed on next send). On HTTP error: freeze movement, show the error in
   `#spatial-status`, resume on next keypress.
   `blocked: true` responses need no special UI — the confirmed point simply
   stops at the wall.

7. **Spawn (transitional)**: on activation, player confirmed position :=
   `(bounds_width/2, bounds_height/2)`. Comment verbatim:
   `// TRANSITIONAL SPAWN (TICKET-0032): fixed center until the door chantier`
   `// introduces spawn-at-door. If the center lies inside an obstacle, the`
   `// judge blocks all movement by design (geometry.py degenerate origin —`
   `// the judge never rescues); fix the location's geometry, not this code.`

8. **Travel/refresh coherence**: re-run the activation flow (geometry +
   presence re-fetch, spawn reset) whenever the tab is activated or the
   player's location changes while the tab is active (reuse the existing
   scene-reload hook the travel flow already calls; executor: locate
   `loadScene`'s call sites and trigger the spatial reload from the same
   place rather than polling).

## Scope OUT

- NO proximity calls, NO "Parler" affordance, NO join/leave wiring
  (BRIEF-0032-c).
- NO server changes of any kind.
- NO client-side collision or distance math — not even "just for smoothing".
- NO building entry/exit, doors, or multi-room anything (next chantier).
- NO persistence of position, zoom, or camera (Q1: fully transient).
- NO pan gestures / minimap / touch support.
- NO modification of the existing scene text view, geometry editor, or any
  HTMX-adjacent flow.
- NO presence re-polling loop (one fetch per activation/travel; live NPC
  movement is out of scope for the whole ticket).

## Invariants to defend

- **Model proposes, code judges / server is sole judge**: every movement
  judgment flows through `move-check`; the client draws only confirmed
  positions.
- **Q1 transience**: zero writes from this surface — it calls only GET
  endpoints and the read-only `move-check` POST.
- **Advisory frontend rules (H1/0027)**: keep the new code in one contiguous
  commented section; respect the file's existing vanilla-JS conventions
  (`api()` helper, `esc()`; no frameworks, no build step).

## Done means

- [ ] Live: spatial location -> tab shows bounds, obstacles, NPC circles with
      names, player circle at center; status strip shows the transient
      notice.
- [ ] Live: non-spatial location -> exact error message, no canvas, no
      requests to spatial endpoints.
- [ ] Live: WASD moves the circle at walking pace; running into a wall stops
      it flush with no pass-through at any zoom; diagonals are not faster.
- [ ] Live: typing in the chat/join inputs never moves the player; clicking
      canvas then WASD works; Esc releases.
- [ ] Live: wheel zoom anchors on cursor, clamps at 8 and 64 px/m.
- [ ] Live: network tab shows move-check only while keys are held (~10/s),
      zero requests when idle or when the tab is inactive.
- [ ] Live: traveling to another spatial location re-renders its geometry
      and NPCs, player back at center.
- [ ] `tooling/verify` suite green.
- [ ] /review-step and /close-step run.

## Docs to update

None (no schema change, no decision change — G2-b's decision log lives in
BRIEF-0032-a). This brief's section comment is its own doc.
