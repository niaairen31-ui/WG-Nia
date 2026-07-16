# BRIEF — Step "Move-check endpoint" (TICKET-0030, BRIEF-0030-b)

## Context

BRIEF-0030-a shipped the pure collision authority
(`src/world_engine/geometry.py::clip_segment`) and its permanent verify
guard. This brief exposes it: one endpoint that judges a transient player
movement segment against the persistent obstacle geometry of the player's
CURRENT location, and never writes position to canon. It is the first
citizen of a named third register — TRANSIENT ADJUDICATION — which is
neither `_apply_mutation` (AI proposal → creator checkpoint → canon) nor
creator CRUD (direct canon): read persistent geometry, judge transient
position, persist nothing.

Locked decisions (intake, TICKET-0030):
- **D1** — the route is a caller of `geometry.clip_segment`, never a
  co-implementer. No intersection math outside `geometry.py`.
- **D2** — request carries `location_id` + `origin` + `destination`; the
  server structurally verifies `location_id` matches the player's
  `current_location_id` (409 otherwise). Doctrine: injected context — and
  judged geometry — depends on the active role; a player client must not
  be able to probe the geometry of a location the PC is not in.
- **D3** — hard stop. Response is the authorized point plus a `blocked`
  flag; slide emerges client-side in 0032. Server-side slide is a
  recorded compatible evolution (same contract), not built.
- **D5** — the register is named "transient adjudication" in
  `ARCHITECTURE_DECISIONS.md` (this brief writes the entry).

Placement constraint (RECON): `routes/play.py` sits at exactly 1000 lines —
the G1 module-budget cap. The endpoint CANNOT land there; the budget
tripwire is functioning as designed. A new `routes/spatial.py` names the
workstream and will host 0031's proximity endpoint.

## Scope IN

1. **New module `src/world_engine/cockpit/routes/spatial.py`** — module
   docstring:

   ```
   """Spatial adjudication routes (TICKET-0030, BRIEF-0030-b).

   TRANSIENT ADJUDICATION register: these endpoints read persistent
   geometry, judge transient positions, and persist NOTHING — neither
   _apply_mutation nor creator CRUD. Player position lives client-side
   for the duration of a scene (workstream decision Q1); the server is
   judge, never registrar. All intersection math lives in
   world_engine.geometry (sole collision authority) — this module is a
   caller only. Ticket 0031's proximity endpoint joins this module.
   """
   ```

   `router = APIRouter()`, full paths on decorators (house style).

2. **Mount** — `src/world_engine/cockpit/app.py`: import
   `from .routes import spatial as _routes_spatial` (alphabetical with
   its siblings) and `app.include_router(_routes_spatial.router)`.
   Update `routes/__init__.py`'s docstring ("mounts all five" → six,
   adding spatial to the list).

3. **Reader re-export** — `src/world_engine/cockpit/crud/__init__.py`:
   add `_location_geometry_dict` to the `from .entities import (...)`
   block (alphabetical position). It is the codebase's sole geometry
   assembler (0029); reusing it avoids a second reader.

4. **Endpoint — `POST /api/spatial/move-check`**:

   Body model (pydantic, in `spatial.py`):
   ```python
   class PointBody(BaseModel):
       x: float
       y: float

   class MoveCheckBody(BaseModel):
       location_id: str
       origin: PointBody
       destination: PointBody
   ```

   Query param `player_id: Optional[str] = Query(None)`, resolved via
   `_crud._player_character_id(db, _crud._world_id(db))` — the exact
   `get_scene` pattern (`routes/play.py:290`).

   Handler sequence:
   a. Resolve player; 404 if the `Character` row is missing (get_scene
      precedent).
   b. **409** if `body.location_id != char.current_location_id` — detail
      `"location_id is not the player's current location"`. The guard is
      structural, not advisory.
   c. Load the `Location` row; **404** if missing.
   d. **409** if `bounds_width` or `bounds_height` is NULL — detail
      `"location has no spatial mode"`. A client should never have asked.
   e. **422** if any of the four coordinates is non-finite
      (`math.isfinite`, NaN/inf rejected — same fail-closed rule as
      `write_location_obstacles`).
   f. Assemble geometry via `_crud._location_geometry_dict(location_id, db)`;
      adapt `{obstacles: [{id, vertices}]}` to `list[Polygon]` and bounds
      to `(width, height)`.
   g. `point, blocked = geometry.clip_segment(origin, destination,
      polygons, bounds)`.
   h. Return `{"x": point[0], "y": point[1], "blocked": blocked}` —
      nothing else. No `obstacle_id`, no wall normal: no reader exists
      (same discipline as 0029's refusal of `kind`/`label`).

   The handler performs **zero writes** — no session mutation, no
   `db.add`, no commit. The endpoint is GET-like in effect; it is POST
   only because the segment payload is structured.

5. **Decision record — `ARCHITECTURE_DECISIONS.md`**: append ONE
   TICKET-0030 block covering both briefs, on the 0029 entry's model:
   - the register name and definition (**D5** — transient adjudication:
     read-persistent, judge-transient, persist-nothing; contrast with
     `_apply_mutation` and creator CRUD);
   - **D1** pure module as sole collision authority, gate-guarded by
     `geometry_unit.py`; rejected: math in the route module;
   - **D2** endpoint contract + structural location guard; rejected:
     free `location_id` (geometry probing against role doctrine);
   - **D3** hard stop, client-emergent slide; option B (server-computed
     slide) recorded as a compatible evolution — same endpoint, same
     response shape, only the returned point changes;
   - **D4** point player, visual-only radius; rejected: polygon
     inflation as premature (same doctrine as the rejected C3);
   - the `routes/play.py` budget tripwire as the placement rationale for
     `routes/spatial.py`.
   Regenerate `DECISIONS_INDEX.md` via `gen_decisions_index.py`.

## Scope OUT

- **Persisting any position** — Q1 locked workstream-wide: player
  position is transient, client-held per scene. No column, no row, no
  session field. If execution finds a "convenient" place to stash it,
  REPORT ONLY.
- **NPC positions and the proximity endpoint** — ticket 0031.
- **Canvas, WASD, player circle, any frontend** — ticket 0032. No
  `index.html` change in this ticket at all.
- **A play-facing geometry READ endpoint** (the client drawing walls
  needs one) — 0032's intake decides its shape; do not pre-build.
- **Server-side slide (D3-B), player radius (D4-B)** — recorded, not built.
- **Rate limiting / batching for WASD cadence** — 0032 owns call cadence;
  the endpoint judges one segment per call, period.
- **Any refactor of `routes/play.py` to free budget headroom** — the new
  module IS the answer; REPORT ONLY.
- **Schema, migrations, changelog** — zero schema surface in this ticket.

## Invariants to defend

- **Sole collision authority** — no intersection or point-in-polygon
  math in `spatial.py`; every judgment call goes through
  `geometry.clip_segment`. The `geometry_unit.py` check guards the math;
  code review guards the call-site discipline.
- **Transient adjudication persists nothing** — `single_canon_write.py`
  green with an UNCHANGED `canon_write_policy.txt`; the endpoint handler
  contains no write to any table.
- **Role doctrine** — the 409 location guard is the structural expression
  of "injected context depends on the active role"; do not soften it to
  a warning or make `location_id` optional.
- **Module budget** — `spatial.py` starts tiny and `routes/play.py`
  stays untouched at its cap.
- **Full-path decorators** — house style: the route decorator carries
  `/api/spatial/move-check` in full, no router prefix.

## Done means

- [ ] Full verify suite green, including `geometry_unit.py` (from
      BRIEF-0030-a) and `module_budget.py` with the new module.
- [ ] Live smoke against the 0029 demo location (bounds 40×30, block
      `(5, 5, 10, 2)`):
      - `POST /api/spatial/move-check` origin `(2, 2)` → destination
        `(2, 4)`: response `(2, 4)`, `blocked: false`;
      - origin `(10, 3)` → destination `(10, 6)` (crosses the block's top
        edge at y=5): response y ≈ 5 minus epsilon, `blocked: true`;
      - origin `(2, 2)` → destination `(-3, 2)` (leaves bounds): response
        x ≈ 0 plus epsilon, `blocked: true`;
      - origin `(6, 6)` (inside the block) → any destination: response
        `(6, 6)`, `blocked: true`.
- [ ] Guard checks:
      - `location_id` of another location → 409;
      - a location with NULL bounds → 409;
      - unknown location id → 404;
      - `origin.x = NaN` → 422.
- [ ] `grep -c "db.add\|commit" src/world_engine/cockpit/routes/spatial.py`
      → 0 (persist-nothing, machine-eyeball).
- [ ] `ARCHITECTURE_DECISIONS.md` block appended, `DECISIONS_INDEX.md`
      regenerated.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (Scope IN 5).
- `CLAUDE.md`: File-structure section only if it lists route modules
  individually (contract-checked — respect the section whitelist and
  budgets); no new standing rule expected, REPORT if one emerges.
- No schema docs, no changelog: schema version untouched.
