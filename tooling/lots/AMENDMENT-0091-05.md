# AMENDMENT-0091-05 — the seed's knowledge upsert moves into writes/

Ticket: TICKET-0091   Lot: LOT-0091-lore-as-facts.md   Brief in flight: J
(stopped before any edit; the step-3 enumeration of `src/` matched
AMENDMENT-0091-04 exactly)
Decided by Nia (2026-09-22): option (a).

## What deviated

The lot never enumerated `scripts/`. `scripts/seed_pilot.py::upsert_knowledge`
(`:101-140`) builds `m.Knowledge(id=…, **fields)` with a `content` key and
converges existing rows by `getattr` / `setattr`. It is a writer outside
`writes/` that reads raw text in order to write it back, which is the STOP
of AMENDMENT-0091-04. After the rename, its `content` key maps to nothing,
and `identity_tokens.py` R1 forbids `content_raw` in the seed.

Also found, and not blocking:
- **`seed_pilot.py:262` (`_seed_customs`).** Its idempotence check compares
  `m.Fact.content`. Once tokens exist, a re-seed would duplicate customs.
- **Readers outside `src/`.** `scripts/test_context.py:87,96,106,112,120`,
  `checks/fact_facets.py:285,301,413` and
  `checks/relation_orientation.py:156-157`.

## Decision

**(a)** The create-or-converge logic moves, unchanged in logic, into
`writes/knowledge.py::upsert_knowledge_row(db, *, id, **fields)`. It maps
`content` to `content_raw` and returns `"created"`, `"updated"` or
`"existing"`. The seed keeps its bookkeeping from that status. Seed text is
**not tokenized**: like migrated text (L2), it is a reproducible dataset,
and tokenizing it would break idempotence and fill `unresolved_mention` at
every seed.

Rejected alternatives:
- (b) Allow-list the seed in R1. This widens the raw-text perimeter to a
  script. Reactivation: none.
- (c) Send the seed through `write_knowledge`. This changes behaviour:
  tokens, `change_history` entries and mention rows at seed time.
  Reactivation: Nia wants the pilot world's knowledge tokenized, in which
  case a one-shot tokenizing pass in a later ticket is the vehicle.

## Amended BRIEF-0091-J (regenerated)

- **Item 3c.** `upsert_knowledge_row`; `_seed_customs` compares
  `fact_text(db, fact)`.
- **Item 3d.** The `scripts/` and check readers go through the render.

## Gate checks re-run

- (c) The `scripts/` enumeration is now on record (the executor's step-3
  report).
- (e) `identity_tokens.py` R1 is satisfied: raw text is read only in
  `writes/`, `prose_render.py`, `knowledge_resolve.py`, models and the
  migrations.
