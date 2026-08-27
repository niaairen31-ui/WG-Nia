# BRIEF - Step "atomic batch commit route"

## Context
TICKET-0042, step 5 of 5. Generation and review exist (BRIEF-0042-a..d). This
step is the single canon-write path for a batch: a server-authoritative,
atomic commit that creates the accepted rooms (bounds from their manifest type
template), re-derives the parent cascade server-side (never trusting the client),
writes each confirmed edge through `connect_locations` so doors materialize on
the perimeter (N1), and commits ONCE with full rollback on any exception. Posture
is identical to `commit_region`: the client is untrusted, the cascade is
re-derived, no half-batch is ever observable.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors on live `main`, schema v1.85.
- Commit precedent, copy the POSTURE not the code: `cockpit/routes/regions.py:91
  commit_region`. Cascade re-derivation `_region_resolve_location_parent:81`
  (ignores the client's accept map for parent choice; recomputes). Commit-free
  cores in a shared session `_commit_region_locations:188` calling
  `_crud._create_entity_core`. Link stage `_commit_region_links:230`. Door
  materialization: `_touched_location_ids` + a SINGLE `materialize_doors` sweep
  before the one `db.commit()` (`:156` region tail). Rollback on HTTPException /
  IntegrityError / Exception (`:157-164`).
- Edge birth: `spatial_author.py:110 connect_locations(db, *, world_id,
  entity_a_id, entity_b_id, changed_by)` -- writes the `connects_to` relation AND
  materializes doors for BOTH endpoints, does NOT commit (caller owns the
  commit). `materialize_doors:58` is idempotent, full-replace per location.
- Birth bounds: `cockpit/crud/entities.py:520 _apply_birth_bounds` runs inside
  `_create_entity_core:534`, reading `spatial_author.location_type_template:166`
  from the location's `location_type`. Because P1 kept the manifest type verbatim
  (BRIEF-0042-a/b), a room typed "room" gets the 6.0x5.0 template automatically
  here -- NO extra bounds code in this route.
- T1 degradation: `placement.py:49 door_placeholder_point` returns `(0,0)` for a
  NULL/invalid-bounds endpoint (`:68`). So a NULL-bounds anchor does not break
  materialization; its door lands at the origin.
- `canon_write_policy` AST check + `json_ui_boundary` allow-list: the new route
  is a canon-write path and must be added to whatever allow-list / registry those
  checks read, or they fail closed.

## Scope IN

1. **New route module `src/world_engine/cockpit/routes/room_batch.py`.** Register
   its router in the app the same way `regions.py` is. Header comment noting it is
   the SOLE canon-write path for the batch (creator-authority CRUD analogue),
   posture identical to `commit_region`.

2. **Thin read routes** (if not already added in BRIEF-0042-d):
   `POST /api/room-batch/manifest` -> `generate_room_batch_manifest`;
   `POST /api/room-batch/draft` -> `generate_room_batch_draft`;
   `POST /api/room-batch/coherence` -> `propose_batch_coherence`. These write no
   canon.

3. **`POST /api/room-batch/commit`** -- the atomic commit. Body: `{anchor_id,
   rooms: [<fiche entry>...], accepted: {local_id -> bool}, edges: [<resolved
   supplementary>...], confirmed_edges: {edge_id -> bool}}`. Steps, all in ONE
   session, ONE `db.commit()` at the end:
   - Resolve the world id; verify `anchor_id` is a real location in it (404 /
     `{ok:false}` if not).
   - **Accepted rooms only.** Filter `rooms` by `accepted.get(local_id, True)`
     (default-accept, matching the review default).
   - **Server-authoritative cascade** (mirror `_region_resolve_location_parent`):
     for each accepted room, resolve its `parent_room` to a committed room id IF
     that parent is itself accepted-and-committed; otherwise fall back to the
     ANCHOR id. NEVER trust a client-sent effective-parent. Build the id map as
     rooms are created (create parents before children, or two-pass: create all,
     then set `parent_location_id`).
   - **Create rooms commit-free** via `_create_entity_core` (which runs
     `_apply_birth_bounds` -> template bounds from the manifest type). Set
     `parent_location_id` from the re-derived cascade.
   - **Edges.** For each supplementary edge with `confirmed_edges.get(id)` True
     AND both endpoints committed-or-canon (a batch endpoint must be an accepted,
     committed room; a canon endpoint must still exist): resolve both to entity
     ids and call `connect_locations(db, world_id=..., entity_a_id=...,
     entity_b_id=..., changed_by="creator")`. ALSO write the SPANNING-TREE edges:
     every committed room gets a `connects_to` to its committed parent (the
     parent-child adjacency IS a passage) via `connect_locations`. An edge whose
     endpoint was rejected/failed -> `unresolved` note, no write (L1 posture).
   - **T1 note.** If the anchor has NULL bounds or NULL classification, append an
     advisory note to the result (`"Ancre sans bounds -- portes cote ancre a
     l'origine jusqu'a classification"`); do NOT block.
   - `db.commit()` exactly once. Wrap the whole body in try/except:
     HTTPException / IntegrityError / Exception -> `db.rollback()` +
     `{ok:false, error}`. No half-batch observable.
   - Return `{ok:true, committed: {rooms:[{local_id,id,name}...]},
     edges_written:n, doors: <sweep summary>, unresolved:[...], notes:[...]}`.

4. **Door materialization choice (drafting decision, flagged):** use
   `connect_locations` PER confirmed edge (the ticket's named anchor). This
   materializes doors for both endpoints on each call; a room touched by k edges
   is re-swept k times. `materialize_doors` is idempotent and full-replace per
   location, so this is correct, just O(k) redundant. The alternative (region's
   `write_relation` + a single end-of-commit `materialize_doors` sweep over
   touched ids) is more efficient but diverges from the ticket's "commit must go
   through connect_locations". DEFAULT: `connect_locations` per edge, for
   single-point-of-edge-birth clarity. If the redundant sweeps show up at 25
   rooms, switch to the region sweep pattern -- REPORT before switching.

## Scope OUT
- Generation (BRIEF-0042-a/b/c). This route consumes their output.
- Frontend (BRIEF-0042-d).
- Any schema change / migration. Bounds, doors, and `connects_to` all use
  existing tables (v1.85 template columns, v1.81 door, relation). `danger_class`
  is `db_write`, NOT `migration`.
- Persisting the manifest/draft. Only the commit writes canon.
- L2 (unknown name -> room). Unresolved edges/parents fall to notes / the anchor.
- Trusting any client-sent cascade or effective-parent. Re-derive server-side.
- Envelope / geometry validation at write time (C1, proscribed).

## Invariants to defend
- **Single canon-write authority.** This route is creator-authority CRUD; it
  shares `writes.py` helpers (`_create_entity_core`, `connect_locations` ->
  `write_relation` + `materialize_doors`). It must NOT open a second write idiom.
  Add it to the `canon_write_policy` allow-list, do not exempt it.
- **History is sacred / append-only.** `_create_entity_core` and
  `connect_locations` already honor this; do not add a destructive path.
- **Atomicity.** Exactly one `db.commit()`, full rollback on any exception. This
  is the single most important behavior of the step -- a half-committed batch is
  a defect.
- **Server-authoritative cascade.** The parent resolution is re-derived here; the
  client's accept map informs WHICH rooms commit, never the parent topology.
- **N1 -- doors on the perimeter, never the center, never model-proposed.**
  Guaranteed by routing through `connect_locations`/`materialize_doors`; this
  route computes no point.

## Done means
- [ ] Committing a 5-room batch under an anchor creates 5 locations with
      `parent_location_id` set per the tree, each with template bounds
      (a "room" -> 6.0 x 5.0), and materialized doors on both sides of every
      tree edge and every confirmed supplementary edge.
- [ ] Rejecting an internal room and committing: that room is absent, its
      children are parented to the anchor (server re-derived), and no edge to the
      rejected room exists.
- [ ] A confirmed supplementary edge to a real canon sibling under the anchor
      creates a `connects_to` + doors between the batch room and that sibling.
- [ ] An edge whose endpoint was rejected produces an `unresolved` note and no
      write.
- [ ] Forcing an exception mid-commit (e.g. a bad room) rolls back the WHOLE
      batch -- zero locations, zero doors, zero relations persist.
- [ ] Committing under a NULL-bounds anchor succeeds; the anchor-side doors sit
      at (0,0) and the T1 note is returned.
- [ ] `canon_write_policy` and `json_ui_boundary` verify checks pass with the new
      route in their allow-lists.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- CLAUDE.md: register `routes/room_batch.py` as a canon-write path (File
  structure + any canon-write pointer).
- ARCHITECTURE_DECISIONS.md: append the door-materialization choice
  (`connect_locations` per edge vs region's single sweep) with the trigger for
  switching.
- No schema changelog entry (`schema_version_touched: none`).
