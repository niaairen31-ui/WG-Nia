# BRIEF-0075-b — AMENDMENT 1: `location_reachable` reader

**Amends:** `tooling/briefs/BRIEF-0075-b-plan-emission-budget.md`, Scope IN
item 2, the `_eval_location_reachable` bullet.
**Date:** 2026-08-24
**Trigger:** Claude Code escalation under STOP condition (Scope IN item 2's
"if no reusable traversal exists, STOP and report").
**Author:** Claude (design), owning the error.
**Status of the original:** unchanged on disk. This artifact supersedes one
bullet and the check that depended on it.

## The escalation was correct

The brief instructed:

> `_eval_location_reachable` — is `target_entity_id` reachable through the
> door graph from the character's `current_location_id`? Mini-RECON: reuse
> the existing traversal; do not write a second one. If no reusable traversal
> exists, STOP and report rather than authoring one here.

That instruction contradicts decision **D1 (BRIEF-19)**, which is standing
project doctrine: each new `connects_to` consumer gets its OWN reader, and a
real dedup opportunity is REPORTED but not acted on. The brief told the
executor to do the opposite of what the codebase has decided, six times over.

Claude Code stopped instead of guessing. That is the STOP protocol working
exactly as intended, and it is treated as correct behaviour, not a failure.

## Enumeration (corrected)

The escalation named two readers. The tree holds more. Measured 2026-08-24 on
`main` @ v1.93:

1. `_location_neighbours` — `src/world_engine/cockpit/play.py:854`. Direct
   neighbours, one hop, returns `(entity_id, name)` pairs.
2. `GET /api/locations/graph` — the original D1 pair with (1).
3. `_reachable_locations` — `src/world_engine/tick_context.py:405`. BFS,
   ACTIVE locations, origin EXCLUDED, `INTERVAL_HOP_RADIUS`-bounded.
   Documented in-code as *"A NEW, tick-local `connects_to` reader —
   deliberately not shared."*
4. `write_location_doors`' B1 gate — `src/world_engine/writes/config.py:275`.
   In-code: *"Not refactored to share."*
5. `spatial_doors.py:60-62`. In-code: *"This is the fifth ... connects_to
   reader; decision D1 (BRIEF-19) stands — do NOT ..."*
6. `spatial_author._live_neighbour_ids` — referenced from
   `cockpit/routes/regions.py:336` as a third sibling of the same shape.
   `room_batch_author.py:141` reads `connects_to` as well.

The day-plan reader is therefore roughly the SEVENTH. D1 has been reaffirmed
in a code comment at each addition, with a running count. The precedent is not
ambiguous.

**Why the brief got it wrong.** "Reuse the existing traversal" is a
DISCIPLINARY instruction — be tidy, avoid duplication. D1 is a STRUCTURAL
choice — independent readers cannot break each other, and a shared reader
couples callers that have no reason to move together. This project resolves
that conflict in favour of the structural choice everywhere else. The brief
inverted it.

## Corrected instruction (supersedes the original bullet)

Author a NEW, day-local `connects_to` reader in `src/world_engine/day_plan.py`.
D1 applies; the dedup opportunity is REPORTED, not acted on.

- `_day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]`.
- BFS over `Relation.type == "connects_to"` among ACTIVE locations of the
  active world, reading the relation rows in BOTH column orders (the same
  `source`/`target` symmetry every sibling reader handles — see
  `spatial_doors.py:60` for the idiom).
- **Unbounded**: the origin's connected component, in the sense already fixed
  by RECON-0015 F3 — not all locations, and no hop radius. A day is long
  enough that an interval bound has no meaning here.
- **Origin INCLUDED** in the returned set. "The player is already there"
  satisfies reachability. This is the concrete shape difference from
  `_reachable_locations`, which excludes it, and it is why sharing would have
  been wrong on the merits and not only on doctrine.
- Returns bare ids, not `(id, name)` pairs and not an ordered list. The
  evaluator needs membership, nothing else.
- Called ONCE per `evaluate_requirements` invocation and the result passed to
  every `location_reachable` verdict in that plan. Do not BFS per requirement.
- Module docstring states, verbatim in substance: that this is a new
  `connects_to` reader under decision D1 (BRIEF-19), that it is the Nth such
  reader with N as measured, and that it is deliberately not shared with
  `_location_neighbours` or `_reachable_locations` because its shape differs
  (unbounded, origin-inclusive, id-set return).

`_eval_location_reachable` then reduces to a membership test, and its verdict
carries `current` as the origin location id and `required` as the target id.

## Check change

BRIEF-0075-b item 6's checks stand, with one addition and one prohibition.

- **Do NOT** author any check asserting that `day_plan.py` reuses an existing
  traversal. Such a check would encode the superseded instruction and would
  have to be removed later.
- **Add R10** to `tooling/verify/checks/day_plan.py`: `day_plan.py` imports
  neither `_location_neighbours` nor `_reachable_locations` nor
  `_live_neighbour_ids`, and declares its own BFS. Fail-closed and
  vacuity-guarded: zero traversals found in the module is a FAILURE, not a
  pass. This turns D1 from a comment convention into a structural assertion
  for this consumer.

## Report only

Three findings to carry into the execution notes, none to act on:

1. **The dedup opportunity**, as D1 requires — now with seven readers, state
   the count and leave it.
2. **`ARCHITECTURE_DECISIONS.md` anchors are stale.** It names
   `_location_neighbours` in `cockpit/app.py` and `_reachable_locations` in
   `tick.py`; the tree has them at `cockpit/play.py:854` and
   `tick_context.py:405`. Same check-anchor relocation pattern as
   TICKET-0027's. Report the drift; retargeting the doc is TICKET-0071's
   hygiene territory, not this brief's.
3. **A coherence hazard D1 never had to consider.** Every prior reader answers
   a LOCAL question for its own caller. This one GATES A PLAN: if it says a
   location is reachable and the Play surface's travel path later says
   `[SORTIE INTROUVABLE]`, the player holds a plan they cannot execute. The
   day chain resolves travel abstractly, so the two never meet today — but
   they will if TICKET-0069 ever routes a day step through the Play surface.
   Record this as a "proves X, not Y": `_day_reachable_ids` proves a path
   exists in the graph; it does NOT prove the Play surface would let the
   player walk it. Candidate for its own ticket, not for this brief.

## Unaffected

Every other decision in BRIEF-0075-b stands: the two `agenda_step` columns,
`agenda_step_requirement` and its per-type shape CHECK, `REQUIREMENT_TYPES`
and the evaluator bijection, `budget_cut`'s sequential truncation, the F1
single emission, `DAY_BUDGET_SLOTS` derived from the phase vocabulary, and
checks R1 through R9. The positional wall and R6 in particular are untouched —
storing `location_reachable`'s target on the requirement row rather than on
`agenda_step` remains the load-bearing choice.
