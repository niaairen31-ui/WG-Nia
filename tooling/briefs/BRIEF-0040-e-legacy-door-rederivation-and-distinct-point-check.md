# BRIEF - Step "re-derive stacked legacy doors + distinct-point invariant"

## Context
BRIEF-0040-d replaced the center placeholder with a perimeter walk, but changed
nothing for doors that already exist: `materialize_doors`
(spatial_author.py:82-90) reuses `existing_points` for every surviving edge, so
every door materialized before TICKET-0040 stays stacked at the room center
forever. This step re-derives those, and locks the result with a fail-closed
check. Last step of TICKET-0040.

## Scope IN

1. **G1 - legacy-center detection, in `placement.py`.** New predicate beside
   `door_placeholder_point`:

   ```
   def is_legacy_center(location, point: Point) -> bool
   ```

   True when the location has usable bounds (both non-None, finite, > 0) AND
   `point` equals `(width / 2.0, height / 2.0)` within `1e-9` on both axes. False
   in every other case, including NULL bounds - a location with no bounds has no
   center to compare against and its `(0, 0)` doors must NOT be disturbed.
   Docstring, verbatim:

   ```
   G1, TICKET-0040: recognises a door still sitting at the H1 placeholder
   point (the exact bounds center), so materialize_doors can re-derive it
   onto the perimeter. A door the creator hand-placed at the exact center
   is statistically null, and the worst case is that it moves to a wall.
   The comparison lives here, not in spatial_author.py, for the same
   reason the placement does: coordinate math has one authority.
   ```

2. **Targeted re-derivation in `materialize_doors`**
   (spatial_author.py:84-91). The per-neighbour branch becomes:
   - no existing door for this target -> `placement.door_placeholder_point(location, neighbour_id)`,
     `summary["placeholders"] += 1` (unchanged behaviour, new position);
   - existing door AND `placement.is_legacy_center(location, (x, y))` ->
     `placement.door_placeholder_point(location, neighbour_id)`,
     `summary["rederived"] += 1`;
   - existing door otherwise -> reuse `(x, y)` verbatim (hand-placed doors are
     preserved, unchanged).

   `summary` gains the `"rederived": 0` key at initialisation (:72). `spatial_author.py`
   still performs zero coordinate arithmetic of its own - it calls the two
   `placement` functions and builds dicts.

   Update the `materialize_doors` docstring: after "Preserves any existing (x, y)
   for a surviving edge", add `- except a point still sitting at the exact H1
   bounds center, which is re-derived onto the perimeter (G1, TICKET-0040)`.
   Update the module docstring's "only invents a placeholder point ... for an edge
   that has no door yet" sentence the same way.

3. **Idempotence must survive.** Re-running `materialize_doors` on the same
   locations must reproduce the same door set AND the same coordinates: a
   re-derived point is a perimeter point, `is_legacy_center` returns False for it
   on the second pass, so it is then reused verbatim. Assert this explicitly (see
   Done means) - it is the property most likely to break.

4. **L1 - new fail-closed check**
   `tooling/verify/checks/door_distinct_points.py`, built on the
   `door_coverage.py` idiom (fresh temp-file SQLite via
   `WORLD_ENGINE_DATABASE_URL` set BEFORE any `world_engine` import, `FAILURES`
   list, print FAIL lines, `sys.exit(1)`):
   - **Assertion**: for every active location of a world carrying non-NULL,
     positive bounds, no two of its `door` rows share the same `(x, y)` within
     `1e-9`. Locations with NULL bounds are EXCLUDED (their doors are legitimately
     all at `(0, 0)` - I1).
   - **Fixture, through the real production writers**: build one location with
     bounds and three active neighbours, wire the three edges via
     `spatial_author.connect_locations`, assert three distinct points.
   - **Prove the FAIL path**: force two of its doors onto the same coordinates via
     `writes.write_location_doors`, re-run the scan, assert it names the offending
     pair.
   - **Prove recovery**: `materialize_doors` alone does NOT heal that (both points
     are off-center, so both are preserved) - so heal by deleting the doors and
     re-materializing, and assert three distinct points again. Do not add a heal
     path to production code to make the check convenient.
   - **Prove the G1 path**: build a location with bounds and two neighbours,
     write both doors at the exact bounds center by hand, run `materialize_doors`
     once, assert both moved to distinct perimeter points and
     `summary["rederived"] == 2`.
   - **Vacuous-proof**: zero qualifying locations scanned is a FAIL, not a pass.
     The "no qualifying location" PASS line is reachable only after the fixture
     concretely ran; any exception during the scan crashes the check non-zero.

5. **Ticket wiring.** The new check must appear in `TICKET-0040`'s
   `### Machine-checkable` section with the exact arrow form
   `-> verify/checks/door_distinct_points.py`, or `tooling/verify/run.py` will not
   run it (`run.py:10`, `LINK` regex).

## Scope OUT
- Do NOT add a `door.is_placeholder` column, or any column to `door`. The center
  comparison is the whole mechanism; `door` stays terminal and gains nothing
  (`door_terminal.py`: no table may take a FK on `door.id`).
- Do NOT write a one-shot retro-derivation script in `scripts/`. Re-derivation
  lives on the materialization path so that a world loaded later cannot revert to
  stacked doors.
- Do NOT re-derive a door whose point is anything other than the exact center,
  however "suspicious" it looks. No proximity threshold, no heuristic beyond exact
  equality within `1e-9`.
- Do NOT touch a door of a location with NULL bounds.
- Do NOT relax `idx_door_target`, do NOT add a second door per ordered pair.
- Do NOT put the center comparison in `spatial_author.py` or `spatial_doors.py`.
- Do NOT change `connect_locations`, `write_location_doors`, the region commit's
  bulk materialization call, or `_perform_travel`.
- Do NOT add door coordinate editing to the frontend. The doors panel stays as
  TICKET-0034 left it.
- Do NOT implement B4, the geometric floor plan, or door-alignment between the two
  sides of a shared wall.

## Invariants to defend
- **`door_terminal.py`**: no FK on `door.id`, and no math in `spatial_doors.py`.
  This brief adds math only to `placement.py`.
- **`write_location_doors` is the SOLE door-write path** - `materialize_doors`
  still calls it with a full payload; nothing here writes a `Door` row directly
  (the check's fixture goes through the writer too).
- **`materialize_doors` never commits.** The caller owns the transaction.
- **Not reachable from `_apply_mutation`.** World creation is creator direct
  authority; `single_canon_write.py` must stay green.
- **Idempotence** of `materialize_doors` - re-running reproduces the same door set
  AND the same coordinates.
- **`door_coverage.py` stays green**: coverage is about existence, and this brief
  moves points without adding or dropping a row.
- **Fail-closed checks**: zero parsed criteria is a failure, never a vacuous pass
  (`run.py:33-48` idiom, `door_terminal.py` / `single_canon_write.py` precedent).

## RECON needed at exec time (verify before writing)
- Enumerate every consumer of `materialize_doors`'s return dict before adding the
  `"rederived"` key: `grep -rn "materialize_doors\|placeholders" src/ tooling/`.
  `routes/regions.py` and `crud/relations.py` are the expected callers. A consumer
  that iterates the summary's keys, or asserts its length, must be updated in THIS
  commit; a consumer that reads named keys needs nothing.
- Confirm `door_coverage.py`'s fixture helpers (`_fresh_engine`, `_make_location`)
  and copy their shape rather than inventing new ones; confirm whether they are
  importable or must be duplicated per the checks' standalone-script convention.
- Confirm `materialize_doors`'s current physical line count (45) and that the
  change keeps it under 80.
- Confirm how many `door` rows currently sit at their location's exact bounds
  center in the live DB, BEFORE running anything: a read-only query, reported as a
  number in the step summary. That number is what the live gate should expect to
  see move.
- Confirm `write_location_doors`'s B1 gate (a target without a live `connects_to`
  edge is rejected) so the check's fixture wires edges before writing doors.
- Confirm `spatial_doors.resolve_spawn`'s degenerate-anchor fallback
  (`spatial_doors.py:112-160`) still covers a perimeter door that a later obstacle
  edit buries in a wall - report only, change nothing.

## Done means
- [ ] `python tooling/verify/checks/door_distinct_points.py` exits 0 and prints a
      PASS line naming the number of locations scanned.
- [ ] Deliberately reverting `door_placeholder_point` to the center makes the new
      check FAIL and name the duplicated pair - demonstrate once, then revert.
- [ ] `python tooling/verify/run.py --ticket TICKET-0040` is green across all
      linked checks.
- [ ] Deployment sequence, in this order: `python scripts/backup.py` -> confirm
      the backup file -> then any live re-materialization below.
- [ ] Live: pick an existing location whose doors were all stacked at the center.
      Wire or re-save one adjacency so `materialize_doors` runs on it. Every one of
      its previously-centered doors is now on a distinct perimeter point.
- [ ] Live: on that same location, drag/set one door to a deliberately off-center
      point, re-run materialization: that door does NOT move; the others do not
      move either (all already off-center after the previous step).
- [ ] Live: run materialization twice in a row on the same location and compare
      the door coordinates - byte-identical (idempotence).
- [ ] Live: Play mode - enter the location through each of its doors in turn. Each
      arrival spawns inside the room, near a different wall, never inside an
      obstacle, and the "Aller a X" proximity affordance appears at a different
      spot for each door.
- [ ] Live: a location with NULL bounds and two neighbours still has both doors at
      `(0, 0)` and no error anywhere.
- [ ] `/review-step` clean, `/close-step` run.

## Docs to update
- `ARCHITECTURE_DECISIONS.md`: extend the N1 evolution paragraph appended by
  BRIEF-0040-d with the G1 mechanism - why replacing the function was not enough
  (`materialize_doors` preserves existing points, so no legacy door would ever
  have moved), the exact-center-equality rule and its accepted false-positive (a
  hand-placed door exactly at the center moves to a wall), the explicit rejection
  of a `door.is_placeholder` column and of a one-shot script, and the L1 invariant
  now guarding the result.
- `CLAUDE.md`: add `door_distinct_points.py` to the enumerated fail-closed door
  gates beside `door_coverage.py`, and one clause on the re-derivation rule.
- `DECISIONS_INDEX.md`: regenerate mechanically after the
  `ARCHITECTURE_DECISIONS.md` edits.
- `TICKET-0040`: flip `status:` to `verify`, and confirm the
  `### Machine-checkable` section carries the `door_distinct_points.py` arrow.
