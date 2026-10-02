# AMENDMENT-0101-01 — a zone child receives nothing

Ticket: TICKET-0101 "Zones and visitable places"   Lot: LOT-0101-zones.md
Brief in flight: BRIEF-0101-C (stopped by the executor before its commit)
Decision: P2-1, Nia, 2026-10-01

## What deviated

C-08 lets `promote_for_child` promote a parent whenever a location becomes
its first active child — created, re-parented or reactivated. A location
that is re-parented or reactivated may already be a zone (it has active
children of its own). `apply_promotion` then moved the parent's contents
into that zone: characters through `write_character_location` (no guard),
items and details by assignment — a breach of B1 — and schedules through
`write_npc_schedule`, whose B guard raised `ZoneRefusal`, a 500. A created
location is never a zone, which is why the lot's tests did not see it. The
executor stopped on it as an invariant finding.

## Amended contracts (verbatim; the lot header carries the same text)

**C-06** gains one key: `"target_is_zone": bool` = `is_zone(child_id)`
(False without a `child_id`).

**C-08** gains one row, judged before the confirmation:
| preview | `confirmed` | result |
|---|---|---|
| `needs_confirmation` True, `target_is_zone` True | any | 409, detail a string: « « {child} » est déjà une zone : le contenu de « {parent} » ne peut pas y être déplacé. Rattachez d'abord un lieu visitable à « {parent} », ou videz « {parent} ». »; nothing written |

`PromotionModal.gate` opens no dialog when `target_is_zone`: the save goes
through and the 409 message reaches the fiche's status line. A promotion
that moves nothing stays silent, even towards a zone.

## Touched briefs

- **C** — regenerated: contracts C-06 and C-08, the diff
  (`writes/zone_promotion.py`, `crud/zone_hooks.py`, `PromotionModal.svelte`,
  the decision entry, `zone_promotion.py` assertion (f)), a fifth named
  mutation, Done means (`(f) a zone child receives nothing [5]`).
- **D, E, F** — diffs regenerated only: their decision-registry hunks carry
  C's entry as context, which grew. No contract or Scope IN line changed.

## Gate checks re-run

(a) property trace: unchanged findings (R-10, R-11); `is_zone` is C-01.
(b) C-08's trigger table: two rows added (the location itself a zone, with
and without contents). (d) C-06/C-08 re-read after the change. (e)
`zone_promotion.py` satisfied by `crud/zone_hooks.promote_parent`.
Re-measured: the six briefs re-applied from their fences on a clean `main`,
`run.py --ticket TICKET-0101-zones` green, corpus 135/135.
