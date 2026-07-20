---
id: TICKET-0034
title: Spatial doors — inter-location passage from the Play canvas
type: feature
status: escalated
created: 2026-07-17
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]   # v1.81 additive migration; door-travel calls _perform_travel (closes conversations + memberships, moves the player)
blast_radius: medium
brief_ids: [BRIEF-0034-a, BRIEF-0034-b, BRIEF-0034-c, BRIEF-0034-d]
schema_version_touched: v1.81
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket 0034 : je veux ajouter des portes a mon play spacial qui me
> permettent de changer de lieux. J'apparais toujours a la porte.

## Clarifications resolved (intake)

Fifth step of the spatial / Play mode workstream (0029 geometry -> 0030
collision -> 0031 presence/proximity -> 0032 canvas/WASD -> **0034 doors**).
It lifts the dette named verbatim at `cockpit/index.html:3311`: *"TRANSITIONAL
SPAWN (TICKET-0032): fixed center until the door chantier introduces
spawn-at-door"*.

- **A1 — one row per side.** `door(id, world_id, location_id,
  target_location_id, x, y, created_at)` with UNIQUE index
  `(location_id, target_location_id)`. Pairing is DERIVED at arrival
  (`where location_id = B and target_location_id = A`) and made unambiguous
  BY THE INDEX, not by a defended invariant. Full-replace per location —
  the `write_location_obstacles` shape, copied.
- **A1 escalation guard (locked with A1).** A2 (one `passage` row carrying
  both endpoints) stays available: the data migration is a mechanical
  self-join, the real cost is reshaping the per-location write. That
  remains true only while `door` is **terminal**: *no other table may take
  an FK on `door.id` while A1 stands.* The day a canon row references a
  door by id, A1 -> A2 stops being mechanical. Recorded in
  ARCHITECTURE_DECISIONS as a named deferred escalation with its trigger
  (a second passage needed between the same pair of locations).
- **B1 — the door is the spatial manifestation of a `connects_to` edge.**
  `write_location_doors` REJECTS a target with no active `connects_to`
  edge; the play-side reader FILTERS doors whose edge later disappeared.
  No cascade, no delete. The map stays the world's traversability truth.
- **C1 — proximity affordance ("Aller à X"), pilot posture.** Chosen
  knowingly as the pilot shape. The later walk-through chantier is **C3,
  not C2**: `move-check` is zero-write by register and will never call
  `_perform_travel`; it will emit an advisory `door_crossed` and the client
  will fire the same travel endpoint this ticket builds. C1 does not
  foreclose the walk-through — it builds its endpoint.
- **D1 — doors ride the existing proximity call.** `POST /api/spatial/proximity`
  gains `doors_in_range` + `door_threshold`. Additive; no new client cadence
  (the on-stop 200 ms debounce already exists).
- **E1 + J1 — `POST /api/spatial/travel`, living in `routes/play.py`.** It
  writes (via `_perform_travel`), so it CANNOT live in `routes/spatial.py`
  (zero-write register, `routes/spatial.py:4-10`). It joins the two other
  `_perform_travel` callers (`routes/play.py:244`, `:357`) — all three
  callers in one module. URL prefix names the player surface, not the
  module (`scene/join` precedent).
  - **Gate hardness is not uniform, and this is on record.** "No travel to
    a location that is not directly linked" is a HARD guarantee: the door
    row cannot exist toward a non-neighbour (B1 write gate) and cannot
    surface toward a dead edge (B1 read filter). "The player really stood
    at the door" is a GOOD-FAITH guarantee: the position is client-declared
    and the server persists no position (Q1), so it has nothing to check it
    against. Same posture as proximity's advisory gate (G-A).
- **F1 — spawn resolved server-side.** New `GET /api/spatial/spawn`
  (read-only; this one DOES belong in `routes/spatial.py`). The inward
  offset lives in `placement.py` — sole placement authority. Documented
  fallback to today's center spawn when: no origin, no return door, or a
  degenerate anchor.
- **G1 — the origin is transient and client-carried.** `_perform_travel`
  returns `origin_location_id`; the client passes it to the spawn endpoint.
  No `character.last_location_id`, no canon write for a transient concern.
- **K1 — `cockpit/spatial_doors.py`**, on the `spatial_presence.py:39`
  precedent: it touches the DB, calls `placement` and `geometry`, and
  implements NO math. Three readers across two route modules
  (`routes/spatial.py` x2, `routes/play.py` x1) — without it, the two route
  modules import each other for the same resolution. `DOOR_RANGE` and the
  spawn offset stay in `placement.py`: two thresholds are two values to
  calibrate, not two authorities.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `door` writes exist only in `writes/config.py::write_location_doors`
      (24th sanctioned site); the `door` table is in `[CANON_TABLES]`
      -> verify/checks/single_canon_write.py
- [ ] `write_location_doors` rejects a target with no active `connects_to`
      edge, a target that is not an active location of the same world, a
      self-target, a duplicate target in one payload, a non-finite
      coordinate — nothing written in any case
      -> verify/checks/spatial_door_travel.py
- [ ] No table takes an FK on `door.id` (A1 escalation guard, enforced not
      just documented)
      -> verify/checks/door_terminal.py
- [ ] `placement.spawn_point` is deterministic across processes (pinned
      literals) and never returns a point in an obstacle or out of bounds
      when a free candidate exists
      -> verify/checks/placement_unit.py
- [ ] `POST /api/spatial/travel` rejects: unknown door (404); door not in
      the player's current location (409); door whose `connects_to` edge is
      gone or whose target is inactive (409); position beyond `DOOR_RANGE`
      (409) — zero rows written in every rejection
      -> verify/checks/spatial_door_travel.py
- [ ] `POST /api/spatial/travel` happy path moves `character.current_location_id`
      and returns `origin_location_id`
      -> verify/checks/spatial_door_travel.py
- [ ] `routes/spatial.py` still performs zero writes; `spatial_doors.py`
      implements no distance/offset math (no `math.hypot`, no `sqrt`)
      -> verify/checks/single_canon_write.py, verify/checks/door_terminal.py
- [ ] `routes/play.py`, `routes/spatial.py`, `placement.py`,
      `spatial_doors.py` stay within the module-budget cap
      -> verify/checks/module_budget.py
- [ ] v1.81 changelog entry present and consistent
      -> verify/checks/schema_partition.py

### Live  ->  human gate (Nia)

- [ ] Creator sheet of a spatial location: a "Portes" panel lists the
      `connects_to` neighbours; setting x/y on one and saving round-trips
      after reload
- [ ] Saving a door toward a non-neighbour is impossible from the panel
      (the neighbour list IS the choice surface) and rejected by the API if
      forced
- [ ] Play (spatiale): the door renders on the canvas, labelled with the
      destination name
- [ ] Walking to the door and stopping surfaces "Aller à X"; clicking it
      changes location
- [ ] Arriving in X, the player circle spawns AT the return door, not at
      the center — the ticket's stated request
- [ ] Arriving in a location with no return door (or entered by narrative
      travel / creator god-mode) spawns at the center, no error
- [ ] Stopping far from the door surfaces no "Aller à" button
- [ ] Deleting the `connects_to` relation makes the door disappear from
      the canvas and from the affordance, with no DB error and no row lost
