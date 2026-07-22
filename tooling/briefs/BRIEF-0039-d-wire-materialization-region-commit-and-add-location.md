# BRIEF - Step "wire materialization: region commit + add-location (connect_locations, J1)"

## Context
BRIEF-0039-c built `materialize_doors` in isolation. This step fires it at the two
moments Nia named - region creation and adding a location to an existing region -
implemented via the single point where a `connects_to` edge is actually born:
`write_relation`. Per J1, a thin `connect_locations` helper wraps
"write the edge + materialize both endpoints", so region commit, the manual
relation-CRUD path, and any future edge creator all yield doors. This makes door
coverage a build-time invariant (its fail-closed check lands in BRIEF-0039-e).

## Scope IN
1. NEW helper `connect_locations` in `src/world_engine/spatial_author.py`:
   `connect_locations(db, *, world_id, entity_a_id, entity_b_id, changed_by) -> dict`
   - Calls `write_relation(db, mode="set", world_id=world_id,
     entity_a_id=entity_a_id, entity_b_id=entity_b_id, type="connects_to",
     value=50, direction="mutual")` (exact args as regions.py:279-283 today).
   - Then calls `materialize_doors(db, world_id=world_id,
     location_ids=[entity_a_id, entity_b_id], changed_by=changed_by)`.
   - Returns a merged summary. Does NOT commit (caller owns the commit).
2. Region commit (routes/regions.py). Two acceptable shapes - pick the one that
   keeps `_commit_region_links` within R1 (80-line ceiling); state which you chose:
   - (preferred) Leave `_commit_region_links` writing edges via `write_relation` as
     today, and AFTER it returns, in `commit_region`, collect the set of location
     ids touched by `written_links` and call `materialize_doors(db,
     world_id=..., location_ids=<that set>, changed_by=...)` ONCE, before the single
     `db.commit()`. This is the bulk path: every location's door set is recomputed
     exactly once regardless of edge count.
   - (alternative) Route the `kind == "connection"` branch of `_commit_region_links`
     through `connect_locations`. Correct but recomputes a node's doors once per
     incident edge; only choose this if the bulk collection would push commit_region
     over budget.
   Faction `controls` links are UNCHANGED - materialization is connects_to only.
3. Add-location / manual adjacency path. Find the creator route that creates a
   `connects_to` relation between two locations (the POST behind index.html:9316,
   in the relations CRUD). Route its connects_to creation through
   `connect_locations` so adding a location and wiring it materializes doors for the
   new node AND its neighbour. Non-connects_to relation types are untouched.
4. Thread `changed_by` from each call-site's existing creator identity into
   `connect_locations` / `materialize_doors`. Do not invent an identity.

## Scope OUT
- Do NOT embed materialization inside `write_relation` itself. Keep write_relation a
  pure relation writer; coupling door writes into it would blur the single canon
  writers and hit every relation type, not just connects_to.
- Do NOT materialize on faction `controls` or any relation type other than
  connects_to.
- NO verify checks in this brief (they are BRIEF-0039-e). Wiring only.
- NO E1 street-access note here (BRIEF-0039-e).
- Do NOT change the region draft/manifest schema or the graph-editing UI - this
  brief consumes the connects_to edges the creator already draws; it does not add a
  new way to draw them.
- Do NOT re-materialize on location DELETE in this brief (a deleted location's doors
  are already dropped for surviving neighbours on their next materialize; a dedicated
  delete-time sweep, if wanted, is a separate ticket). REPORT if a dangling door
  surfaces in the live gate; do not fix it here.

## Invariants to defend
- "single db.commit() per region commit" (regions.py contract): the bulk
  materialize call must sit INSIDE the same session/transaction, before the one
  commit. Do not add a second commit.
- single_canon_write.py stays green (doors still only via write_location_doors,
  reached through materialize_doors).
- R1 (80-line function): commit_region is already large. If adding the bulk call
  pushes it over, extract the id-collection into a small named helper
  (`_touched_location_ids(written_links)`) rather than inlining - do NOT exempt.
- Structural exclusion / world scoping unchanged - connect_locations passes world_id
  through; it does not widen any query.

## RECON needed at exec time (verify before writing)
- Read `commit_region` fully (routes/regions.py:303-end) to confirm the single
  `db.commit()` location and that `written_links` carries both endpoint ids
  (regions.py:286-289 shows entity_a_id/entity_b_id) - use those to build the
  touched-id set.
- Locate the manual connects_to creation route in the relations CRUD
  (`crud/relations.py`) that index.html:9316 posts to; confirm it currently calls
  `write_relation` and that connects_to is the only type it needs re-routing for.
- Confirm no other production call-site creates connects_to besides these two; if a
  third exists, REPORT it - it likely also wants connect_locations, but adding it is
  out of scope without a decision.

## Done means
- [ ] Live: create a region with an exterior street + a building + a room, draw
      street<->building and building<->room adjacencies, commit -> door rows exist
      for all four directions with NO manual door placement; TICKET-0034 traversal
      walks them.
- [ ] Live: add a new room to the committed building, wire room<->building -> doors
      materialize for the new room and the building; a door the creator hand-placed
      earlier on the building keeps its coordinate.
- [ ] Region commit still performs exactly one db.commit(); commit of a region with
      many edges materializes each node's doors once (spot-check no duplicate work
      errors).
- [ ] `/review-step` clean; single_canon_write.py, door_terminal.py green.

## Docs to update
- ARCHITECTURE_DECISIONS.md: append J1 (materialization fires at every connects_to
  birth via connect_locations; region commit uses the bulk path) with the rejected
  J2 noted.
- CLAUDE.md: note that connects_to creation on the creator paths flows through
  connect_locations (pointer-fresh).
