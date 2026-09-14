# AMENDMENT-0087-1 — "fact_participant is keyed (fact_id, entity_id); the role discriminator is dropped"

Amends: LOT-0087-knowledge-subject-participants.md
Raised by: Claude Code, opening BRIEF-0087-a, as a STOP on a Mini-RECON anchor
Decided by: Nia, 2026-09-14, code `J2`
Status: applied to the header; embedded copies regenerated in all five briefs

## What deviated

BRIEF-0087-a's Mini-RECON carried this anchor:

> `src/world_engine/models/canon_knowledge.py` -> `FactParticipant` carries
> `world_id`, `fact_id`, `entity_id`, `role`, `position`, and has no
> uniqueness constraint across them.

The second half is false. `canon_knowledge.py:119-122`:

```python
    __table_args__ = (
        Index("idx_fact_participant_unique", "fact_id", "entity_id", unique=True),
        Index("idx_fact_participant_entity", "entity_id"),
    )
```

Confirmed in the production database:

```
CREATE UNIQUE INDEX idx_fact_participant_unique ON fact_participant (fact_id, entity_id)
```

The constraint was added at TICKET-0082 / BRIEF-0082-b and predates the
RECON. Nothing moved; the RECON's claim was wrong. It was wrong because the
finding behind it (R-02) was traced from `writes/facts.py` — the module that
writes the table — while the anchor asserted a property of the model that
declares it. Indexes on `fact_participant` were never listed.

## Why it was not cosmetic

The unique key is `(fact_id, entity_id)` and deliberately excludes `role`.
So `C-01`'s stated idempotency — "idempotent per `(fact_id, entity_id,
role)`" — was not enforceable as written: a second `attach_participants`
call for a pair already present under a different role would raise
`IntegrityError` at commit and abort the surrounding transaction, whatever
the brief's read-before-write guard checked for.

It is latent rather than live: R-02 measured zero `fact_participant` rows in
production, so no existing data collides.

## What the decision session concluded

Two facts the escalation did not have.

`canon_knowledge.py:113` states the table's intent verbatim: *"fact_participant
(arity for a free-standing fact — never for a typed one)"*. An entity
participates in a fact once.

`fact_default`, declared immediately below in the same module, carries
`idx_fact_default_unique ON (fact_id, scope_type, scope_id)` — a three-column
unique key that does include its discriminator. TICKET-0082 puts a
discriminator in a unique key where it wants one. On `fact_participant` it
did not.

Options put to Nia: J1 keep `role="subject"` with the guard widened to the
pair; J2 drop the discriminator entirely; J3 widen the index to
`(fact_id, entity_id, role)`.

**Nia chose J2.**

The deciding argument was semantic, not mechanical. A free-standing fact
"Maelis conspires with Vance" carries Maelis and Vance as participants, and
"qui sait quoi sur Maelis" must return the knowledge hanging off it. Under
J1 it would return it only if someone had separately marked Maelis
`role="subject"` — so J1 misses the right answer in exactly the case where
TICKET-0082 arity is in use. A participant already is an aboutness claim.

J3 was rejected firmly: it is DDL, it would restore `danger_class:
[migration]` and a version bump that A2 removed, and it would weaken
TICKET-0082's arity invariant by admitting the same entity twice in one
fact — to recover a distinction for which no case exists.

Deferred, with a grep-verifiable reactivation condition: a role discriminator
returns the first time a fact carries a participant that is **not** a subject
of the knowledge attached to it.

## Amended R-02, verbatim

### R-02 — `fact_participant` exists, is sanctioned, is checked, is uniquely keyed, and is empty

Opened: `src/world_engine/writes/facts.py:57-83`; `src/world_engine/models/canon_knowledge.py:112-129`; `tooling/verify/checks/fact_spine.py:1-22`; `sqlite_master` indexes and row counts on the production database.

Finding: `attach_participants(db, *, fact, entity_ids, role=None)` is the
single sanctioned write site for `fact_participant`. It raises `ValueError`
if the fact carries any typed FK, and assigns `position` in list order from
0. `fact_spine.py` enforces the spine by AST scan plus three DB assertions,
each vacuity-guarded.

The model declares two indexes (`canon_knowledge.py:119-122`):
`idx_fact_participant_unique` on `(fact_id, entity_id)`, **unique**, and
`idx_fact_participant_entity` on `entity_id`. Both are present in the
production database. `role` is `Optional[str] = None` and is **not** part of
the unique key. The module comment states the intent: *"fact_participant
(arity for a free-standing fact — never for a typed one; enforced in code by
writes/facts.py, spans two tables so SQLite cannot express it as a CHECK)"*
(`canon_knowledge.py:113-115`). For contrast, `fact_default` in the same
module carries a three-column unique key that does include its discriminator.

Row count in production: **0**.

Consequence: an entity participates in a fact at most once, by construction.
`attach_participants` performs a plain `db.add`, so a second attach for an
existing pair raises `IntegrityError` at commit and aborts the surrounding
transaction — every caller reads before it writes. The constraint also
guarantees `who_knows_about` can never return the same knowledge row twice
for one asked entity.

## Amended C-01, verbatim

### C-01 — `write_knowledge(..., subject_entity_ids=None)`

Produced by: BRIEF-0087-a   Consumed by: BRIEF-0087-b, c, d

Signature, the existing one with one added keyword-only parameter:

```python
def write_knowledge(
    db: Session, *, mode: str = "update", knowledge_id: Optional[str] = None,
    entity_id: Optional[str] = None, subject: Optional[str] = None,
    level: Optional[str] = None, content: Optional[Any] = None,
    source: Optional[Any] = None, is_incorrect: bool = False,
    is_secret: bool = False, share_threshold: int = 50,
    session_id: Optional[str] = None, changed_by: str = "creator_crud",
    fact_id: Optional[str] = None,
    subject_entity_ids: Optional[list[str]] = None,
) -> Knowledge
```

Behaviour: on a create (`knowledge_id is None`, `mode != "level_change"`),
after the fact is resolved — attached via `fact_id` or auto-created — every
id in `subject_entity_ids` is attached to that fact through
`attach_participants(db, fact=fact, entity_ids=[...])`.

- **No `role` argument is passed.** `attach_participants`'s default (`None`) stands. `role` keeps its TICKET-0082 meaning — free text describing *how* an entity participates — and is never a filter, never a marker, and never written by this path.
- Idempotent per `(fact_id, entity_id)`, which is what `idx_fact_participant_unique` enforces. An id already present on that fact **under any role, or none** is skipped. The guard is a read before the write, and it is mandatory rather than defensive: `attach_participants` does a plain `db.add`, so a collision raises `IntegrityError` at commit and aborts the surrounding transaction.
- Ignored entirely when `knowledge_id` is set, and when `mode="level_change"`. Passing it in either case is not an error and changes nothing.
- `None` and `[]` both mean "no subject" and are the default. Behaviour with the parameter absent is byte-for-byte the behaviour before this lot.
- Validation is the caller's. `write_knowledge` does not re-check that the ids are active entities of the fact's world; `attach_participants` still raises on a typed fact.

Error and empty cases: `attach_participants` raises `ValueError` on a typed
fact — unreachable on this path, since every fact `write_knowledge` touches
on a create is free-standing (R-03), but not defended against here.

## Amended C-04, the two clauses that change

The rest of `C-04` stands. Two clauses are replaced.

`section="knowers"` — zero or more. One per `knowledge` row whose fact carries
a `fact_participant` with `entity_id == <the asked entity>`, **with no role
filter**, the knowing entity being world-scoped at query construction.
`idx_fact_participant_unique` guarantees at most one participant row per
`(fact, entity)`, so no knowledge row can appear twice.

`coverage.uncounted_rows` — the number of `knowledge` rows in this world whose
fact carries **no participant at all** — the rows this selector structurally
cannot see.

## Amended C-06, the clause that changes

One row per distinct `knowledge.subject` in `world_id` whose fact carries
**no participant at all**. Every other clause of `C-06` stands.

## Downstream briefs touched

All five. Regenerate every embedded copy before sending any of them.

- **BRIEF-0087-a** — the false anchor; the `R-02` and `C-01` copies; Scope IN item 3 (attach without role, guard on the pair); Scope IN item 5 (docstring language); the Scope OUT line that read *"A uniqueness constraint on `fact_participant`. The idempotency guard is a read, not a DDL change."*, which asserted the constraint's absence and now forbids touching it; four done-means lines; the `ARCHITECTURE_DECISIONS.md` entry.
- **BRIEF-0087-b** — done-means lines asserting `role == "subject"`.
- **BRIEF-0087-c** — the `R-02` and `C-06` copies; Scope IN item 2 (attach without role); two done-means lines.
- **BRIEF-0087-d** — the `C-06` copy; Scope IN item 3 (`Bind` posts no role); the Scope OUT role-vocabulary line; three done-means lines.
- **BRIEF-0087-e** — the `C-04` copy; Scope IN item 2 (no role filter in the join); Scope IN item 5 (`uncounted_rows`); three done-means lines, including the one asserting that a non-`subject` participant contributes no row, which is now false by design.

## Gate checks re-run

- **(a) Unverified symbol** — re-run. `idx_fact_participant_unique` and `idx_fact_participant_entity` now appear in R-02. The check is also **tightened**: see below.
- **(b) Unwalked rule** — both case tables re-walked. The `C-01` table's "id already attached as subject" row becomes "id already attached under any role". The `who_knows_about` table gains the row a non-subject participant now produces, and loses nothing: every outcome stays reachable and correct.
- **(c) Unenumerated generalization** — the index enumeration for `fact_participant` is pasted into the header. No measured number changes: the 98-row / 42-entity baseline never depended on `role`.
- **(d) Un-rederived contract** — `C-04` re-read after `C-05`. Unchanged by this amendment.
- **(e) Unsatisfiable check** — unchanged. `fact_spine.py` asserts participants attach only to free-standing facts; it makes no claim about `role`.

## The process defect, and the proposed protocol change

Check (a) passed on the defective lot. It asks that every symbol the lot
names appear in a RECON finding, and `fact_participant` did. What would have
caught this is step 1's **depth** rule: *"tracing that a column exists is not
enough. Trace what it is keyed by and what it means."* The RECON traced the
columns of `fact_participant` and never traced its key.

Proposed amendment to `brief-generation-protocol.md`, §5(a), to be decided
separately from this lot: every **property** an anchor asserts must trace to
a finding that opened the file where that property is declared — a table
constraint to the model module, not to the module that writes the table. A
finding about a writer does not license a claim about a schema.
