# AMENDMENT-0091-01 — creator-only facts excluded from `facts_of`

Ticket: TICKET-0091   Lot: LOT-0091-lore-as-facts.md   Brief in flight: G
Decided by Nia: Q21b (2026-09-22)

## What deviated

BRIEF-0091-G's review (uncommitted diff) found a secrets leak that the lot
itself specified. C-05 stores the creator's note (`creator_meta`) and C-18
stores `character.secrets` as a `histoire` fact whose only protection is a
stored knowledge row of the entity itself at `level='unaware'`,
`is_secret=True`. G prescribed `facts_of` with no perceiver on `histoire`
for the tick identity block ("the tick is omniscient") and the link-agent
sheet. The scratch fixture showed the note reaching both prompts
(`TICK_LEAK True SHEET_LEAK True`). BRIEF-0091-H, not yet executed, had the
same defect in `creator.py::generate_agenda` and
`crud/goals.py::_backfill_one_npc`. The pre-delivery gate checked each
brief alone and missed the E × G interaction.

Invariant touched: secrets are excluded by query construction at every
assembler; `character.secrets` is never read by a context assembler.

## Amended contract (verbatim, replaces C-10)

```python
def facts_of(db, *, entity_id, facets: tuple[str, ...], aspect=None,
             notorious_at_location: str | None = None,
             include_creator_only: bool = False) -> list[FactRow]
def creator_only_fact_ids(db, fact_ids) -> set[str]
def known_facts_of(db, *, perceiver_id, entity_id, facets: tuple[str, ...],
                   aspect=None) -> list[FactRow]
def joined(rows: list[FactRow], sep: str = "\n") -> str | None
```

A fact is **creator-only** when a stored `knowledge` row on it belongs to
one of its own participants with `level = 'unaware'` and `is_secret = 1`.
`facts_of` excludes creator-only facts by query construction unless
`include_creator_only=True`, which is legal only in `lore_selectors.py`.
`known_facts_of` always excludes them (no override).
`creator_only_fact_ids` returns the creator-only subset of `fact_ids` in
one query. Everything else in C-10 is unchanged.

## Gate checks added

`tooling/verify/checks/fact_facets.py`:
- R7 (AST) — a keyword `include_creator_only` whose value is not the
  literal `False` appears only in `src/world_engine/lore_selectors.py`.
- R8 (fixture) — a creator-only fact is absent from `facts_of` and
  `known_facts_of`, and present with `include_creator_only=True`.

## Downstream briefs

- D: landed; its embedded C-10 copy is regenerated for the record only.
- G (in flight): new Scope IN item 0 implements the amendment in
  `facet_reads.py` plus R7/R8, **as its own commit before the reader
  commit**. The reader code already written stays as is. The tick keeps
  `facts_of` (omniscient except for the creator's notes). Two new Done means
  cover the leak fixture and R7/R8.
- H: `_facet_rows` is the only call site with `include_creator_only=True`
  and computes `secret` via `creator_only_fact_ids`; two new Done means.
- K: does not read facts; unchanged.

## Gate checks re-run

(a) C-10's property trace gains one line: "creator-only predicate —
C-05 and C-18 (lot contracts), `models/canon_knowledge.py` `Knowledge`
(`level`, `is_secret`, `entity_id`, `fact_id`)". (d) Readers family
re-read: C-09, C-10, C-13 remain reads; C-10's exclusion lives in the query.
(e) `fact_facets.py` R7 is satisfied by `lore_selectors.py` alone; R8 is
satisfied by `facet_reads.py`.
