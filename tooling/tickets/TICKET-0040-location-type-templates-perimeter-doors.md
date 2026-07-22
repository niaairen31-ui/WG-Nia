---
id: TICKET-0040
title: Location type size templates + perimeter door placement
type: feature
status: live-gate
created: 2026-07-22
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0040-a, BRIEF-0040-b, BRIEF-0040-c, BRIEF-0040-d, BRIEF-0040-e]
schema_version_touched: v1.85
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"TICKET-0040 ( celui-ci) - Location type size templates + perimeter door
placement. Ajoute default_width / default_height sur location_type_catalog
(schema v1.85) pour que le code puisse deriver les bounds d'un lieu depuis son
type, sans qu'aucun modele ne produise de nombre. Remplace en meme temps
placement.door_placeholder_point, qui retourne aujourd'hui le centre de la piece
et empile donc toutes les portes au meme point, par un placement deterministe
sur le perimetre."

Framing: first of three tickets of a contextual room-batch generation chantier
(3 to 25 rooms under an existing anchor location). 0040 is autonomous and
generates nothing: it lays down the two primitives the generator will need.
TICKET-0041 (shared review-tree component extraction) and TICKET-0042 (room
batch generator) follow and are untouched here.

## Clarifications resolved (intake)

Locked in a prior design session:

- **A1** - the model produces NO number. Sizes come from the code.
- **B1** - templates live on `location_type_catalog` (columns `default_width`,
  `default_height`), not in Python constants: the registry is already per-world
  and upsert-per-row, hence reusable across worlds. A type with no template ->
  bounds NULL -> no spatial mode. Fail-closed, no invention.
- **B4 DEFERRED** (named deferral) - template override by the median of sibling
  locations when >= 3 exist. Trigger: worlds populated enough for a median to
  mean something.
- **C1** - no parent/child envelope constraint. `parent_location_id` is logical
  containment, not geometric nesting.
- **N1** - `placement.door_placeholder_point` today returns the CENTER of the
  room, so every door of a room sits at exactly the same point. Replaced by a
  deterministic PERIMETER placement: a position derived from
  `_unit_floats(seed=f"{location_id}:{target_location_id}")` - the pseudo-random
  source already present in `placement.py` - projected onto the bounds border.
  Deterministic, reproducible, never two doors confounded, and replaceable
  wholesale the day the geometric floor plan lands, since that function is
  already the single placement authority.

Locked in this session (RECON-0040, live `main` at schema v1.84):

- **E1** - the template is applied at `_create_entity_core`
  (`cockpit/crud/entities.py:518`) ONLY. Not a registry form field, not a second
  site. The region/batch commit path already calls that core
  (`routes/regions.py:223`), so both surfaces are covered by one site.
  Explicitly NOT in `_build_extension_kwargs` (`entities.py:415`): that helper is
  shared with the UPDATE path (`entities.py:678`) and would re-stamp bounds on
  every location edit.
- **F1** - a template change is NEVER retroactive: the template is a value at
  BIRTH, never a live link. Paired with a bounds-preservation fix, because
  "nothing changes" is currently false in two places: `set_location_geometry`
  (`entities.py:815-816`) assigns unconditionally, `None` included; and
  `create_entity` (`entities.py:648`) hardcodes a NULL geometry stub in its
  response, which after E1 would make the client render an empty bounds editor
  whose next save wipes the template.
- **G1** - N1 is declared as an assumed contract evolution in
  `ARCHITECTURE_DECISIONS.md` (amending the `DOOR MATERIALIZATION CORE
  (BRIEF-0039-c)` entry, which graves H1 verbatim), AND carries a targeted
  re-derivation: `materialize_doors` (`spatial_author.py:82-90`) reuses an
  existing door point for any surviving edge, so without it N1 would never fix a
  single already-materialized door. A point equal to the exact bounds center is
  treated as an untouched placeholder and re-derived. A hand-placed door exactly
  at the center is statistically null, and the worst case is that it moves to the
  perimeter. No new column.
- **H1** - perimeter parametrization by ARC LENGTH, walking clockwise from the
  top-left corner (same convention as the rect -> vertices expansion,
  `entities.py:800`). Uniform along the walls whatever the elongation. Rejected:
  uniform-angle ray-casting from the center, which clusters points toward the
  corners as soon as a room is elongated - the very defect being fixed.
- **I1** - NULL bounds -> `(0.0, 0.0)` preserved verbatim. A location with no
  bounds has no spatial mode (B1); the door exists for the edge, not for the
  geometry. `write_location_doors` requires NOT NULL `x`,`y`, so the function
  stays total.
- **J1** - the two existing case-fold catalog scans
  (`spatial_author.location_classification:139-144`,
  `writes/config.upsert_location_type:362-369`) become one read accessor in
  `spatial_author.py`; the template reader is its second caller.
  `upsert_location_type` stays isolated in the writes layer (the write layer
  never climbs into the read layer).
- **K2** - the v1.85 migration seeds `room` ONLY, with `default_width = 6.0`,
  `default_height = 5.0`, and only where both columns are currently NULL. No
  other type is seeded. This is the value that unblocks TICKET-0042 without
  inventing a width for "city".
- **L1** - new fail-closed check `door_distinct_points.py`: within one active
  location carrying non-NULL bounds, no two `door` rows share the same `(x, y)`.
  Encodes N1's reason for existing and catches a seed regression.

Hard constraints surfaced by RECON (report, do not "fix" outside the named
briefs):

- `bounds_width`/`bounds_height` are NOT in `ENTITY_TYPE_REGISTRY["location"]`
  (`entities.py:135-158`). Their only writer is `PUT /api/entities/{id}/geometry`
  (`entities.py:775-827`), whose editor is reachable for EXISTING locations only
  (`index.html:7475`). Every location created today is born with bounds NULL.
- `idx_door_target` is UNIQUE(location_id, target_location_id)
  (`world-engine-schema.md:323-324`): exactly one door per ordered pair. 0040
  must NOT add a second door per pair and must NOT relax the index. The A1 -> A2
  escalation stays guarded by `door_terminal.py`.
- `door` is DIRECTED. The seed `f"{location_id}:{target_location_id}"` is
  asymmetric on purpose: A->B and B->A get different angles because each door
  lives in its own location's local space, with different bounds and a different
  origin. A symmetric (sorted-pair) seed would be a bug.
- `_create_entity_core` is 73 physical lines against an 80-line ceiling
  (`function_length.py:29`). E1's call site must be 2 lines, logic in a helper.
  Adding an entry to the function_length baseline is forbidden.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Within one active location with non-NULL bounds, no two `door` rows share
      the same `(x, y)`  -> verify/checks/door_distinct_points.py
- [ ] `door_placeholder_point` returns a point ON the bounds perimeter, is
      deterministic across processes, and yields different points for two
      different targets of the same location; NULL bounds still yield
      `(0.0, 0.0)`  -> verify/checks/placement_unit.py
- [ ] Every active `connects_to` edge between two active locations still has BOTH
      door rows  -> verify/checks/door_coverage.py
- [ ] `door` remains terminal; no new FK on door.id; no coordinate math added
      outside placement.py  -> verify/checks/door_terminal.py
- [ ] Door writes still route only through `write_location_doors`; no new
      canon-write path  -> verify/checks/single_canon_write.py
- [ ] Every active location's `location_type` is catalogued with a non-NULL
      classification  -> verify/checks/location_type_classified.py
- [ ] No function crosses the 80-line ceiling and no baseline entry is added
      -> verify/checks/function_length.py
- [ ] No module crosses the 1000-line / 40-function budget
      -> verify/checks/module_budget.py

### Live  ->  human gate (Nia)
- [ ] Backup, run the v1.85 migration, re-run it: the second run reports nothing
      to do. `room` carries 6.0 x 5.0 in every world; no other type gained a
      template; a type whose template was already set by hand is untouched.
- [ ] Create a location of type `room` from the Creation surface: it is born with
      bounds 6 x 5, the sheet's geometry editor shows 6 and 5 immediately after
      creation (not empty), and Play mode enters it spatially with no manual
      geometry step.
- [ ] Create a location of a type with no template: bounds stay NULL, no spatial
      mode, nothing invented, no error.
- [ ] Edit the `room` template to 10 x 8: the location created above still reads
      6 x 5. Create a new one: it reads 10 x 8.
- [ ] Open a location's geometry editor, add an obstacle, save without touching
      the bounds fields: the bounds survive. Clear a bounds field explicitly and
      save: the bounds clear (explicit creator intent).
- [ ] Wire three adjacencies onto one room: its three doors sit at three distinct
      points on the walls, and re-running a commit reproduces the same three
      points exactly.
- [ ] An existing location whose doors were all stacked at the center before this
      ticket: after any re-materialization, its doors are spread on the
      perimeter. A door the creator had hand-placed off-center is untouched.
- [ ] Arriving through a door in Play mode still spawns inside the room, against
      the wall the door sits on, never inside an obstacle.
