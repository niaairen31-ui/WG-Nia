---
id: TICKET-0087
title: Knowledge subject as fact participants, and the who_knows_about selector
type: feature
status: brief
created: 2026-09-14
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0087-a, BRIEF-0087-b, BRIEF-0087-c, BRIEF-0087-d, BRIEF-0087-e]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> On travail pour répondre a la question qui connais quoi dans mon interface de
> lore.

Queue item 4 from TICKET-0085. It unlocks the `who_knows_about` selector --
"qui sait quoi sur X" -- which was in the original TICKET-0085 request and
which the consultation surface still cannot answer.

## Clarifications resolved (intake)

Decision session of 2026-09-14, against a fresh RECON of `main` and a
measurement of the production database. Locked codes: `A2, B2, C2, D1, E2,
F1b, H`.

**J2 -- a participant IS the aboutness claim; there is no role discriminator.**
Amended after Claude Code raised a STOP on a Mini-RECON anchor, before any
code was touched: `fact_participant` carries `idx_fact_participant_unique` on
`(fact_id, entity_id)`, unique, from TICKET-0082, and the lot's original
`role="subject"` marker was not enforceable against it. `role` keeps its
TICKET-0082 meaning as free text and is never a filter;
`who_knows_about` matches any participant row for the asked entity. Rejected:
widening the index to include `role` (DDL, would restore the `migration`
danger class and weaken TICKET-0082's arity invariant). *Reactivation of a
discriminator*: a fact carries a participant that is not a subject of the
knowledge attached to it. Full text:
`AMENDMENT-0087-1-participant-unique-key.md`.

**A2 -- the subject lives in `fact_participant`, not in a new column.** The
inbound handover proposed a nullable `knowledge.subject_entity_id`. RECON
showed `fact_participant` already exists for exactly this purpose, with its
own sanctioned write site and its own G1 check, and holds zero rows. A new
column would be a third notion of "what this row is about" beside `subject`
and `fact_participant`. Rejected in favour of populating the table that
TICKET-0082 built. *Reactivation of the column*: a `knowledge` row must carry
a subject that differs from its fact's subject.

**No schema change.** `danger_class` is `db_write`, not `migration`. No
version bump, no migration script, no `world-engine-schema-changelog.md`
column entry. This is the direct consequence of A2 and is the largest
difference between this ticket and the handover that proposed it.

**B2 -- the model names the subject entity; code validates it.** The
proposal payload gains an optional `subject_entity_id`. Nothing is trusted:
the id is re-looked-up against active entities of the mutation's world before
any write. Rejected: B1 (resolver rungs only at write time) -- measured to
fill 16% of rows and no more, because subjects are propositions, not names.
Rejected: the handover's ambiguity journal -- zero ambiguous subjects exist
in the whole production database across eleven worlds (R-09), so its review
surface would have nothing to show. *Reactivation of the journal*: a
measured ambiguity count above zero.

**C2 -- one backfill pass over existing rows**, through the sanctioned
writer, unambiguous matches only. Under A2 this is a data pass, not a
migration.

**D1 -- the selector declares its own coverage.** `who_knows_about` always
emits a `coverage` row saying how many knowledge rows it counted and how many
it could not, because their fact carries no subject participant. With 84% of
existing rows unresolved, this is what separates a partial answer from a lie.

**E2 -- close the coverage gap before shipping the selector.** The selector
brief runs last, after the write path, the backfill and the creator surface.
This is an ordering choice, not a technical dependency: BRIEF-0087-e depends
only on BRIEF-0087-a.

**F1b -- secret knowledge is returned and marked**, matching the precedent
already set by `entity_dossier`, whose `knowledge` section returns
`is_secret` unfiltered (R-11). This surface is the creator's, not a player's.
The MJ context assembler's exclusion invariant is untouched and out of scope.

**F2 -- an incorrect belief appears, marked**, per the TICKET-0085 lock.

**F3 -- `level` is returned and rows sort by level rank, descending.**

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

*(Repaired by AMENDMENT-0087-3, code `G1`: one arrow per line, since
`run.py` keeps only the first arrow of a line, and `corpus_gate.py` linked.
Before the repair this section ran six checks and never `function_length.py`.)*

- [ ] No `fact_participant` row whose fact carries a typed FK; no `knowledge` row with NULL `fact_id`; the AST chokepoint holds  -> verify/checks/fact_spine.py
- [ ] `write_knowledge` reads before it attaches a subject participant, so re-attaching one entity to one fact writes one row and never trips `idx_fact_participant_unique`  -> verify/checks/subject_resolution.py
- [ ] `subject_resolve.py` reaches canon only through `lore_resolve` rungs and contains no `chat(`  -> verify/checks/subject_resolution.py
- [ ] A `subject_entity_id` naming an entity outside the mutation's world is refused at apply, not written  -> verify/checks/subject_resolution.py
- [ ] `SELECTORS` and `_SELECTOR_LOOKUPS` are in bijection; row caps, `context_sections` vocabulary and the five closed verdicts hold  -> verify/checks/lore_selectors.py
- [ ] No selector function is named in `lore_query.py`, the names being read from every `SelectorSpec(fn=...)` rather than from a hand-kept list  -> verify/checks/lore_selectors.py
- [ ] `_SELECTOR_DESCRIPTIONS` has exactly the keys of `SELECTORS`; every `select(` in `lore_selectors.py` is world-scoped at construction; the lore read path stays free of writes and model calls  -> verify/checks/lore_isolation.py
- [ ] Every `knowledge` write path still routes through `writes/knowledge.py::write_knowledge`  -> verify/checks/single_canon_write.py
- [ ] No module-level import cycle under `src/world_engine`  -> verify/checks/import_cycle.py
- [ ] No undefined name under `src/`  -> verify/checks/undefined_names.py
- [ ] No module over its line or function budget  -> verify/checks/module_budget.py
- [ ] No function over 80 lines  -> verify/checks/function_length.py
- [ ] Every new decision-record header matches the strict pattern and the index is regenerated  -> verify/checks/decisions_index.py
- [ ] This ticket's front matter and section shape parse  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus passes  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] On Verkhaal, "qui sait quoi sur Maelis" returns her six knowers, each with a level, and the trace states the coverage.
- [ ] A question about an entity with no knower returns `silent_canon` with the coverage row present, never an empty silence.
- [ ] A secret knowledge row appears in the answer, visibly marked as secret.
- [ ] An incorrect belief appears, visibly marked as a false belief.
- [ ] The creator surface lists unresolved subjects for the active world and lets a subject be bound to an entity in one action; the coverage number moves after binding.
- [ ] The backfill run reports filled and left-null counts matching R-06.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0087-1 | BRIEF-0087-a | `fact_participant` is uniquely keyed on `(fact_id, entity_id)`; the role discriminator is dropped (`J2`) | a, b, c, d, e |
| AMENDMENT-0087-2 | BRIEF-0087-d | the residue worklist has no greenfield island path; deferred to TICKET-0088 (`K3`) | d; e (ordering line) |
| AMENDMENT-0087-3 | none, before BRIEF-0087-e | Machine section ran 6 checks; `coverage` last could be truncated; R2 read a hand-kept literal; `e` cannot start through `/pipeline` (`G1`, `L1`, `M1`, `N1`, `P1`) | e |
