---
id: TICKET-0039
title: Spatial Creation - door materialization + location_type classification at region commit and add-location
type: feature
status: exec
created: 2026-07-21
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0039-a, BRIEF-0039-b, BRIEF-0039-c, BRIEF-0039-d, BRIEF-0039-e]
schema_version_touched: vX.YY   # registry table; exec assigns the next number after v1.81
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"j'ai besoin de quelque chose qui me permet de genere mes lieux correctement (avec
les informations speciales et les portes). Je veux qu'il y ai toujours une porte
minimum entre deux lieux adjacents, je veux qu'ils soit sur le bord sur batiment si
le lieux est a l'exterieurs. La plupart des batiments doivent donner sur une rue.
Comment peut-on gere les rues ? Les pieces peuvent avoir des portes dans le batiment
directement."

Follow-up decisions:
- Type picker: keep the free list; a type chosen outside the list prompts
  interior/exterior once, and the choice is persisted for reuse (registry, G).
- Door placeholder point = center of bounds if present, else (0,0) (H1).
- Generation must fire inside region creation AND when adding a location to an
  existing region. NOT via `_apply_mutation` - world creation is creator direct
  authority, never an AI proposal.
- TICKET-0033 is closed and untouched.

## Clarifications resolved (intake)

- A1 (topological): adjacency = a `connects_to` Relation. A door is the spatial
  manifestation of that edge, never its source (already the codebase doctrine:
  canon.py door docstring, writes/config.py:251-276, spatial_doors.py:60-73).
- B1: a "street" is an ordinary exterior location. "gives onto a street" =
  "connects_to an exterior-public location". For v1, exterior-public == exterior
  (interior/exterior is the only classification axis). A private-vs-public split
  on exterior is a NAMED DEFERRAL (see Scope OUT of BRIEF-0039-e), triggered the
  day a walled private courtyard must not count as street access.
- C (resolved by RECON): no `building` table. A building = a location with an
  interior `location_type` and nested children (parent_location_id). Location model
  already carries parent_location_id (canon.py:214) and location_type (canon.py:217).
- D1: door "type" (interior-interior / boundary / exterior-exterior) is DERIVED
  from the two endpoints' classification, never stored. No door.type column.
- E1: "most buildings on a street" is a SOFT commit-time note, not a hard reject
  ("most" != "all"). Subject = building shell (interior location whose parent is
  exterior, or interior root). No stored exception needed while it is a soft note.
- F: generation is folded into the creator-authority write path. RECON confirms
  `_commit_region_links` (routes/regions.py:229-287) already writes `connects_to`
  via `write_relation`; TICKET-0039 adds door materialization at that site and at
  the add-location path. `_apply_mutation` is NOT touched.
- G: `location_type` becomes a classified registry (interior|exterior), extensible
  from the picker. Seeded from live DISTINCT values (G-seed-1).
- H1: placeholder door point = center of bounds if bounds present, else (0,0).
- J1 (drafting decision, reversible): materialization fires wherever a `connects_to`
  edge is born (region commit bulk + `connect_locations` helper on the manual
  relation-CRUD path), so door coverage is a build-time invariant and its verify
  check is fail-closed. J2 (two named sites only, advisory check) is the fallback.

Hard constraint surfaced by RECON (report, do not "fix"): `idx_door_target` is
UNIQUE(location_id, target_location_id) (canon.py:344-348) -> exactly one door per
ordered pair. The "front + back door" case (Nia Q2) stays BLOCKED at the schema
level for now; the A1 -> A2 escalation is already designed and guarded by
tooling/verify/checks/door_terminal.py. TICKET-0039 materializes one door per
edge; it must NOT add a second door per pair and must NOT relax the unique index.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every active `connects_to` edge between two active locations has BOTH door
      rows (A->B and B->A) after a region commit / add-location  -> verify/checks/door_coverage.py
- [ ] Every `location.location_type` value on an active location exists in the
      registry with a non-NULL classification  -> verify/checks/location_type_classified.py
- [ ] Door writes still route only through `write_location_doors`; no new
      canon-write path introduced  -> existing verify/checks/single_canon_write.py stays green
- [ ] `door` remains terminal; no new FK on door.id; no math added to
      spatial_doors.py  -> existing verify/checks/door_terminal.py stays green

### Live  ->  human gate (Nia)
- [ ] Create a region with an exterior "street", a building, and a room; commit;
      confirm doors appear automatically both directions for every drawn adjacency,
      and the play-side traversal (TICKET-0034) uses them.
- [ ] The street<->building edge reads as a boundary (interior<->exterior); the
      room<->room edge reads as interior; no manual door placement was needed.
- [ ] Add a new location to the existing region and wire one adjacency; confirm
      doors materialize for the new node AND its neighbor without clobbering any
      door the creator had hand-placed earlier.
- [ ] Choosing a location_type not in the list prompts interior/exterior once; the
      new type is reusable next time with its classification remembered.
- [ ] A building shell with no exterior neighbor produces a soft note at commit,
      not a rejection.
