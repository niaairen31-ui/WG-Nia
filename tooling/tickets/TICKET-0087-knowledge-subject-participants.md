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

- [ ] No `fact_participant` row whose fact carries a typed FK; no `knowledge` row with NULL `fact_id`; the AST chokepoint holds  -> verify/checks/fact_spine.py
- [ ] Every writer of `fact_participant` reads before it writes, so `idx_fact_participant_unique` is never tripped and no transaction is aborted by an `IntegrityError`  -> verify/checks/subject_resolution.py
- [ ] `SELECTORS`, `_SELECTOR_LOOKUPS` and `_SELECTOR_DESCRIPTIONS` agree on a three-name set including `who_knows_about`  -> verify/checks/lore_isolation.py
- [ ] `SELECTOR_FUNCTION_NAMES` in the check names all three selectors; bijection, caps, context_sections vocabulary and the five closed verdicts hold  -> verify/checks/lore_selectors.py
- [ ] `subject_resolve.py` reaches canon only through `lore_resolve` rungs and contains no `chat(`  -> verify/checks/subject_resolution.py
- [ ] A `subject_entity_id` naming an entity outside the mutation's world is refused at apply, not written  -> verify/checks/subject_resolution.py
- [ ] Every `knowledge` write path still routes through `writes/knowledge.py::write_knowledge`  -> verify/checks/single_canon_write.py
- [ ] No file over 1000 lines, no function over 80  -> verify/checks/module_budget.py, verify/checks/function_length.py

### Live  ->  human gate (Nia)

- [ ] On Verkhaal, "qui sait quoi sur Maelis" returns her six knowers, each with a level, and the trace states the coverage.
- [ ] A question about an entity with no knower returns `silent_canon` with the coverage row present, never an empty silence.
- [ ] A secret knowledge row appears in the answer, visibly marked as secret.
- [ ] An incorrect belief appears, visibly marked as a false belief.
- [ ] The creator surface lists unresolved subjects for the active world and lets a subject be bound to an entity in one action; the coverage number moves after binding.
- [ ] The backfill run reports filled and left-null counts matching R-06.
