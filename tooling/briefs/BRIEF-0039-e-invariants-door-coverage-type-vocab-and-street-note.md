# BRIEF - Step "invariants: fail-closed door coverage + classified-type check + E1 soft note"

## Context
With materialization wired (BRIEF-0039-d), door coverage is now a build-time
invariant and can be guarded fail-closed. This step adds the two G1 checks and the
E1 building-shell street-access SOFT note. It also adds the D1 door-kind derivation
helper - but only because the E1 note needs to read interior/exterior; no door.type
column is introduced.

## Scope IN
1. D1 derive helper (needed by the E1 note and by any future reader) in
   `src/world_engine/spatial_author.py`:
   `location_classification(db, world_id, location_id) -> Optional[str]`
   returns the `classification` ("interior"|"exterior"|None) of the location's
   `location_type` via the `location_type_catalog` (case-insensitive lookup, world
   scoped). NULL type or unclassified type -> None. This is the ONLY interior/
   exterior reader; do NOT infer from the type string.
   (Door KIND - interior-interior / boundary / exterior-exterior - is DERIVED on
   demand from two endpoints' classification wherever a reader needs it; it is NOT
   stored and NOT computed eagerly here beyond what the E1 note uses.)
2. E1 SOFT note at region commit (routes/regions.py, inside commit_region, added to
   the response `notes` list - same channel region_author uses). After
   materialization, for each committed location that is a BUILDING SHELL - defined
   as: `location_classification == "interior"` AND its parent location's
   classification is "exterior" OR it has no parent (interior root) - check whether
   it has at least one live `connects_to` neighbour whose classification is
   "exterior". If none, append a note, VERBATIM template:
   `f"Batiment '{name}' sans acces exterieur-public - aucune porte ne donne sur un lieu exterieur."`
   This is ADVISORY: it never blocks the commit, never rejects, never mutates.
3. NEW fail-closed check `tooling/verify/checks/door_coverage.py` on the
   door_terminal.py / single_canon_write.py idiom (FAILURES list, print FAIL lines,
   sys.exit(1); zero parsed criteria = FAILURE, never a vacuous pass). DB-backed.
   Assertion: for every active `connects_to` relation whose BOTH endpoints are
   active locations of a world, BOTH directed `door` rows exist
   (location_id=A,target=B and location_id=B,target=A). Any missing direction is a
   FAIL listing the pair. If there are zero connects_to edges among active
   locations, the check must print an explicit "no edges to verify" PASS reason -
   but guard it so an empty result due to a QUERY error is a FAIL, not a pass
   (vacuous-proof: assert the query ran and returned a concrete count).
4. NEW fail-closed check `tooling/verify/checks/location_type_classified.py`,
   modelled on `role_closed_vocab.py` (closed-vocab precedent). DB-backed.
   Assertion: every DISTINCT `location_type` on an ACTIVE location exists in
   `location_type_catalog` (same world) with a NON-NULL classification in
   {"interior","exterior"}. Any type missing from the catalog, or present but NULL,
   or with an out-of-vocab classification, is a FAIL listing the type. Vacuous-proof:
   if there are active locations, the parsed-criteria count must be > 0.
5. Register both checks wherever the verify toolchain enumerates its 32+ checks
   (the runner / manifest), so they run in the standard sweep.

## Scope OUT
- E1 is NOT a fail-closed check. Do NOT turn "most buildings on a street" into a
  gate - "most" != "all"; a hidden cabin or interior courtyard is legitimate. It
  stays a soft note. Do NOT add a stored `street_access` exception flag - a soft
  note needs no silencing mechanism.
- NO public/private exterior split. `location_classification == "exterior"` counts
  as exterior-public for v1. DEFERRAL (record it): the day a walled PRIVATE
  courtyard must not satisfy E1, add an exterior sub-classification and refine the
  E1 neighbour test; trigger = first private-exterior location that wrongly clears
  the note. Log this named deferral in ARCHITECTURE_DECISIONS.md.
- NO door.type / door.kind column. D1 stays derived.
- door_coverage.py must NOT try to also assert "one door per pair maximum" - the
  unique index already guarantees that; the check is about presence, not count>1.
- Do NOT make door_coverage.py depend on connects_to being created ONLY via
  connect_locations - it checks the RESULTING state, so it also catches any edge
  that somehow bypassed materialization (that is the point of a fail-closed check).

## Invariants to defend
- "Fail-closed checks over advisory rules" + vacuous-proof: both new checks must
  FAIL when they parse zero machine-checkable criteria in a world that has the
  relevant rows. Copy the explicit guard idiom from door_terminal.py's
  "_report_and_exit" and role_closed_vocab.py.
- The E1 note lives at commit only; it is NOT a verify check and must not import
  the checks. Keep the advisory (soft) and the gate (fail-closed) strictly separate.
- single_canon_write.py, door_terminal.py stay green - this brief adds readers and
  checks, no new writers.

## RECON needed at exec time (verify before writing)
- Read `role_closed_vocab.py` end to end and mirror its structure for
  location_type_classified.py (DB session acquisition, world iteration, FAILURES,
  vacuous guard, exit codes).
- Read `door_terminal.py` `_report_and_exit` and reuse the exact PASS/FAIL print +
  sys.exit contract for door_coverage.py.
- Confirm the verify runner's registration mechanism (how the 32+ checks are
  discovered/listed) and add both checks there in THIS commit; confirm whether a
  results JSON manifest (tooling/verify/results/...) must be seeded.
- Confirm the active-connects_to-among-active-locations read (crud/locations.py:246
  filters edges to active endpoints) and reuse that filtering for door_coverage.py
  so soft-deleted locations do not produce false FAILs.
- Confirm the parent lookup for the building-shell definition (Location.
  parent_location_id, canon.py:214) and that classification of the parent is read
  through `location_classification`.

## Done means
- [ ] `door_coverage.py`: green after a normal region commit; make it RED on purpose
      by deleting one `door` row of a live edge -> it FAILs naming the pair; restore
      -> green. In an empty world it prints an explicit no-edges PASS.
- [ ] `location_type_classified.py`: green when all active locations' types are
      classified; set one location's type to an unclassified/new string directly in
      the DB -> it FAILs naming the type; classify it -> green.
- [ ] Committing a region containing an interior building whose only neighbours are
      interior emits the exact `Batiment '...' sans acces exterieur-public` note and
      still commits successfully.
- [ ] A building with a street (exterior) neighbour emits NO such note.
- [ ] Both checks appear in the standard verify sweep output.
- [ ] `/review-step` and `/close-step` clean.

## Docs to update
- ARCHITECTURE_DECISIONS.md: E1-as-soft-note decision; the building-shell definition
  (interior with exterior parent / interior root); the exterior-public==exterior
  deferral with its trigger; D1 derived-not-stored confirmation.
- DECISIONS_INDEX.md: regenerate (mechanical).
- CLAUDE.md: add door_coverage.py and location_type_classified.py to the verify
  checks listing (claude_md_contract.py freshness).
- Schema changelog: no schema change in this brief (checks + note only) - state
  "no schema delta" explicitly.
