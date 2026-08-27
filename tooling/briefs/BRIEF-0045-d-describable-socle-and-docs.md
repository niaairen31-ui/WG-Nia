# BRIEF — Step "describable socle wiring + docs consolidation"

## Context

TICKET-0045 final step. Decision B1 + Nia's design ("what an entity should
have, no exception": name + description): `describable` is the non-checkable
socle — always present on every entity_type, never a palette checkbox. The
registry (BRIEF-0045-b) already marks it `checkable=False`; this brief makes
that structurally true by ensuring every entity_type carries describable as an
implicit projection, and closes the ticket's documentation. No new tables, no
new checks, no UI.

## Scope IN

1. **Socle-presence helper in traits.py (thin).** Add a public accessor
   `socle_traits() -> tuple[TraitDef, ...]` returning the non-checkable traits
   (describable today). Single authority for "which traits are implicit". This
   is the counterpart to `checkable_traits()` from BRIEF-0045-b; together they
   partition TRAITS. Add an assertion (module-level or in a tiny self-test the
   check already covers): `set(socle_traits()) | set(checkable_traits()) ==
   set(TRAITS)` and the two are disjoint — the partition is total and
   non-overlapping.

2. **Projection semantics for the socle — DECISION TO CONFIRM (see flag).**
   describable is implicit: it is NOT written as an entity_trait row per type
   (it would be redundant on every row and invite drift), OR it IS seeded as a
   row per entity_type for uniformity. Recommended: **implicit, no row** —
   describable is guaranteed by `socle_traits()` at read time; the projection
   table holds only checkable selections. Wire this by: the (future, 0046)
   constructor reads `socle_traits()` + the type's entity_trait rows; describable
   is always in the effective set without a row. This brief documents the
   contract and adds a one-line assertion to trait_registry_projection.py (from
   -c): no entity_trait row may carry a socle trait_key (describable is implicit,
   never projected). A describable row present in the projection = FAIL.

3. **Extend trait_registry_projection.py (from BRIEF-0045-c)** with the volet
   from item 2: DISTINCT trait_key in entity_trait INTERSECT socle keys must be
   empty. Naming a socle trait in the projection is a FAIL ("socle traits are
   implicit, never projected"). Vacuous-proof already satisfied by -c's
   completeness volet.

4. **Docs consolidation (the substance of this brief).**
   - **ARCHITECTURE_DECISIONS.md**: ensure the -b entry is complete and add the
     socle-is-implicit decision (describable non-checkable, guaranteed at read
     time via socle_traits(), never a projection row) with its rationale
     (redundancy + drift avoidance).
   - **DECISIONS_INDEX.md**: regenerate mechanically so the new entries are
     indexed (do not hand-edit; run the generator).
   - **CLAUDE.md**: confirm the trait-registry convention block (from -b) is
     present and pointer-fresh; add the socle/checkable partition rule
     (socle_traits() + checkable_traits() partition TRAITS; socle traits are
     implicit and never projected). Update the verify-check count to 57.
   - **world-engine-schema.md**: confirm the entity_trait NOTE (from -a) states
     socle traits are never projected rows.

## Scope OUT

- **The constructor UI reading socle + checkable** — TICKET-0046. This brief
  declares `socle_traits()` and documents the read-time contract but ships no
  UI, no HTMX, no palette rendering.
- **Emitting describable's name/description columns as DDL** — those columns are
  the base entity shape; 0044/0046 own runtime DDL. This brief does not ALTER
  anything.
- **New migration** — none. describable-implicit needs no schema change (it is a
  read-time guarantee, not a stored row).
- **Canon-write / mutable_by_ai reader** — TICKET-0047.
- **Derived traits** — deferral D-derived.
- **Any new verify check file** — this brief only EXTENDS
  trait_registry_projection.py with one volet; it authors no new check.

## Invariants to defend

- **No structure without a reader.** socle_traits() reader is the same identity
  block as describable's declared reader (context.py:_npc_context_identity,
  from -b) plus the (0046) constructor. No new unread structure ships.
- **Structural over disciplinary.** The socle guarantee is a total+disjoint
  partition assertion in code and a fail-closed projection volet — not a
  CLAUDE.md sentence alone.
- **S-norme.** socle_traits() / checkable_traits() / trait_keys() are three
  views over ONE TRAITS tuple; no second list of "which traits are implicit"
  may exist anywhere.
- **History is sacred.** No change to the append-only entity_type_history grain;
  socle-implicit means fewer rows, never a destructive write.

## Done means

- [ ] `python -c "from world_engine.traits import socle_traits, checkable_traits,
      TRAITS; assert set(socle_traits()) | set(checkable_traits()) == set(TRAITS);
      assert not (set(socle_traits()) & set(checkable_traits()))"` passes.
- [ ] `socle_traits()` returns exactly (describable,).
- [ ] trait_registry_projection.py FAILs when a describable row is planted in the
      temp-fixture entity_trait table (socle-never-projected volet works).
- [ ] `python tooling/verify/run.py --ticket TICKET-0045` returns green with all
      five machine checks passing.
- [ ] DECISIONS_INDEX.md regenerated (mechanical), includes the 0045 entries;
      decisions_index.py check passes.
- [ ] CLAUDE.md verify-check count reads 57; claude_md_contract.py passes.
- [ ] /review-step and /close-step run.

## Docs to update

- ARCHITECTURE_DECISIONS.md (socle-implicit decision appended).
- DECISIONS_INDEX.md (mechanically regenerated).
- CLAUDE.md (socle/checkable partition rule; check count 57; pointer-fresh).
- world-engine-schema.md (entity_trait NOTE confirms socle-never-projected).
- This brief IS substantially the ticket's doc-closure step.
