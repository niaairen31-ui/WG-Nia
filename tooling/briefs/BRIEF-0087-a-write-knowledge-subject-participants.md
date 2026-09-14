# BRIEF 0087-A — "The subject attachment chokepoint"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: nothing in this lot
Regenerated after AMENDMENT-0087-1 (code `J2`). The previous issue of this
brief carried a false anchor about `fact_participant`'s uniqueness and a
`role="subject"` discriminator; both are gone.

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/writes/knowledge.py:210` -> `db.add(k)` is the only `db.add` in the module; `write_knowledge` owns it.
- `src/world_engine/writes/knowledge.py:156-163` -> on a create with `fact_id is None`, `create_fact(db, world_id=entity.world_id, content=resolved_subject, created_by=changed_by)` runs and its `fact.id` becomes the row's `fact_id`.
- `src/world_engine/writes/knowledge.py:171-187` -> `write_knowledge`'s signature ends with `changed_by: str = "creator_crud", fact_id: Optional[str] = None`.
- `src/world_engine/writes/facts.py:57-83` -> `attach_participants(db, *, fact, entity_ids, role=None)`, raising `ValueError` on a typed fact.
- `src/world_engine/writes/__init__.py:53` -> `from .facts import attach_participants, create_fact, create_fact_default`.
- `src/world_engine/lore_resolve.py:28` -> `_CATEGORY_ENTITY_TYPE = {"place": "location", "person": "character", "faction": "faction"}`.
- `src/world_engine/lore_resolve.py:112` -> `resolve_named(surface_form, category, world_id, db) -> NamedResolution`.
- `src/world_engine/models/canon_knowledge.py:117-129` -> `FactParticipant` carries `world_id`, `fact_id`, `entity_id`, `role` (`Optional[str] = None`), `position`, and declares `Index("idx_fact_participant_unique", "fact_id", "entity_id", unique=True)` plus `Index("idx_fact_participant_entity", "entity_id")`.
- `src/world_engine/models/canon_knowledge.py:113-115` -> the module comment: *"fact_participant (arity for a free-standing fact — never for a typed one; enforced in code by writes/facts.py, spans two tables so SQLite cannot express it as a CHECK)"*.
- The production database carries `CREATE UNIQUE INDEX idx_fact_participant_unique ON fact_participant (fact_id, entity_id)`.

## Facts carried

**R-02** — `attach_participants` (`writes/facts.py:57-83`) is the single
sanctioned write site for `fact_participant`. It raises `ValueError` if the
fact carries any typed FK, and assigns `position` in list order from 0. Its
docstring states the intent verbatim: *"A typed fact already IS the row it
points to; `fact_participant` exists only to carry arity for a free-standing
fact."* `fact_spine.py` enforces this by AST scan plus three vacuity-guarded
DB assertions.

The model declares `idx_fact_participant_unique` on `(fact_id, entity_id)`,
**unique**, and `idx_fact_participant_entity` on `entity_id`
(`canon_knowledge.py:119-122`); both are present in production. `role` is
`Optional[str] = None` and is **not** part of the unique key. For contrast,
`fact_default` in the same module carries a three-column unique key that does
include its discriminator — TICKET-0082 puts one in a unique key where it
wants one, and on `fact_participant` it did not.

Row count in production: 0.

Consequence: an entity participates in a fact at most once, by construction.
`attach_participants` performs a plain `db.add`, so a second attach for an
existing pair raises `IntegrityError` at commit and aborts the surrounding
transaction — every caller reads before it writes.

**R-03** — `_build_knowledge_update` auto-creates a free-standing fact with
`content = resolved_subject` whenever `fact_id` is omitted
(`writes/knowledge.py:156-163`). 615 of 615 production `knowledge` rows point
at a free-standing fact; 312 distinct `fact_id` values; 0 orphans. A fact is
shared by roughly two knowers, so a subject attaches once per fact and every
knower inherits it.

**R-04** — `write_knowledge` owns the only `db.add` for `knowledge`
(`knowledge.py:210`) and is the only place a knowledge-bearing fact is
created. The fact is created inside `_build_knowledge_update` and is **not
returned** to the caller. A caller therefore cannot attach participants to
the fact `write_knowledge` just created without re-querying it.

**R-14** — `resolve_named(surface_form, category, world_id, db)` returns
`NamedResolution(verdict, entity_id, candidate_ids, rung, rungs_tried)`;
`verdict` is one of `matched`, `ambiguous`, `unmatched`. `category` is
mandatory and `KeyError`s on anything outside `_CATEGORY_ENTITY_TYPE`.
`NAMED_RUNGS = ("named_exact", "named_token")`. `rung_named_token` matches
when the entity's normalized name tokens are a subset of the surface tokens
and at least one is three characters or longer (`lore_resolve.py:88-93`).

**R-09** — not one subject string in the production database resolves to two
or more candidate entities, in any category, in any world. The `ambiguous`
verdict is nonetheless total in `C-02`, because a world authored tomorrow can
produce one.

## Contracts

This brief produces **C-01** and **C-02**, verbatim from the lot header.

### C-01 — `write_knowledge(..., subject_entity_ids=None)`

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

On a create (`knowledge_id is None`, `mode != "level_change"`), after the fact
is resolved — attached via `fact_id` or auto-created — every id in
`subject_entity_ids` is attached to that fact through
`attach_participants(db, fact=fact, entity_ids=[...])`.

- **No `role` argument is passed.** `attach_participants`'s default (`None`) stands. `role` keeps its TICKET-0082 meaning — free text describing *how* an entity participates — and is never a filter, never a marker, and never written by this path.
- Idempotent per `(fact_id, entity_id)`, which is what `idx_fact_participant_unique` enforces. An id already present on that fact **under any role, or none** is skipped. The guard is a read before the write, and it is mandatory rather than defensive: `attach_participants` does a plain `db.add`, so a collision raises `IntegrityError` at commit and aborts the surrounding transaction.
- Ignored entirely when `knowledge_id` is set, and when `mode="level_change"`. Passing it in either case is not an error and changes nothing.
- `None` and `[]` both mean "no subject" and are the default. Behaviour with the parameter absent is byte-for-byte the behaviour before this lot.
- Validation is the caller's. `write_knowledge` does not re-check that the ids are active entities of the fact's world; `attach_participants` still raises on a typed fact.

### C-02 — `subject_resolve.resolve_subject(subject, world_id, db)`

New module `src/world_engine/subject_resolve.py`. It imports
`lore_resolve.resolve_named` and `_CATEGORY_ENTITY_TYPE`; it never
re-implements a rung and never calls a model.

```python
@dataclass(frozen=True)
class SubjectResolution:
    verdict: str                      # "matched" | "ambiguous" | "unmatched"
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]    # sorted; empty on unmatched
    category: Optional[str]           # the category that matched; None otherwise

def resolve_subject(subject: str, world_id: str, db: Session) -> SubjectResolution
```

- Walks the three categories of `_CATEGORY_ENTITY_TYPE` in sorted key order, calling `resolve_named(subject, category, world_id, db)` for each.
- Exactly one distinct `entity_id` across all `matched` categories, and no category returned `ambiguous` -> `matched`, with `entity_id` set, `candidate_ids` the one-tuple, `category` the matching category.
- Two or more distinct matched ids, or any category `ambiguous` -> `ambiguous`, `entity_id` None, `candidate_ids` the sorted union of every candidate seen, `category` None.
- No category matched -> `unmatched`, `entity_id` None, `candidate_ids` `()`, `category` None.
- An empty or whitespace-only `subject` -> `unmatched`. Never a rung call.

The function never picks between candidates. Ambiguity rises; it is not
resolved.

## Context

TICKET-0082 built the `fact` spine and `fact_participant`, and nothing ever
wrote a participant row. TICKET-0087 gives that table its reader — the
`who_knows_about` selector — and this brief gives it its writer. Decision A2
chose this over adding a `knowledge.subject_entity_id` column, so there is no
schema change anywhere in this lot.

This step is the chokepoint and the shared resolver, nothing else. Three
later briefs call into it; none of them re-derives it.

## Scope IN

1. **`src/world_engine/writes/knowledge.py`** — add the keyword-only parameter `subject_entity_ids: Optional[list[str]] = None` to `write_knowledge`, last in the signature, after `fact_id`.

2. In `_build_knowledge_update`, add the same parameter with the same default, last in the signature. The create branch already holds the `fact` object when it auto-creates one (`knowledge.py:160-163`); when `fact_id` was passed instead, fetch that fact with `db.get(Fact, fact_id)`. Either way the branch ends holding a `Fact`.

3. Attach the subjects in the create branch only, before the `Knowledge(...)` construction returns. For each id in `subject_entity_ids or []`, in list order: query `FactParticipant` for `fact_id == fact.id` and `entity_id == <id>` — **no role predicate**; if a row exists, skip it; otherwise call `attach_participants(db, fact=fact, entity_ids=[<id>])`. One call per id, so `position` reflects the order ids arrived in and a skipped duplicate does not shift the others. The same id appearing twice in one list yields one row, because the guard runs per id in order.

4. Do not touch `_build_knowledge_level_change`. Do not touch the update branch (`knowledge.py:137-151`). A `subject_entity_ids` passed on either path is silently ignored, which is `C-01`'s stated behaviour, not an oversight.

5. Extend `write_knowledge`'s docstring and the module docstring to state, verbatim: `subject_entity_ids` attaches participants to the row's fact on create only, with no `role`; a participant IS the aboutness claim, so no discriminator distinguishes a subject from TICKET-0082 arity (decision J2, AMENDMENT-0087-1); the attachment is idempotent per `(fact_id, entity_id)`, which `idx_fact_participant_unique` enforces and the read-before-write guard exists to avoid tripping; validation of the ids belongs to the caller.

6. **`src/world_engine/subject_resolve.py`** — new module implementing `C-02` exactly. Module docstring states: this module is the single place a free-text `knowledge.subject` is reconciled against entity names; it reuses `lore_resolve`'s rungs and never re-implements one; it never calls a model; it never picks between candidates.

7. Export `resolve_subject` and `SubjectResolution` from wherever the codebase's existing convention places a non-`writes` module's public names. `subject_resolve.py` is a read-only resolver and does **not** belong in `writes/__init__.py`.

8. Import direction is one-way: `subject_resolve` imports from `lore_resolve`. Nothing in `lore_*` imports `subject_resolve`.

## Scope OUT

Named temptations, every one of them discussed during planning.

- **The dedup guard.** `_find_applied_duplicate_conversation_sourced` (`routes/mutations.py:294`) and `_knowledge_leg_already_applied` (`cockpit/mutations.py:73`) keep matching on `entity_id` + `subject`. Decision A1 was rejected specifically so this stays untouched. Do not "make it consistent" while nearby.
- **Callers.** No caller passes `subject_entity_ids` in this brief. Not the creator CRUD, not `_mutation_apply_new_knowledge`, not `link_author`, not `create_player_character`. That is BRIEF-0087-b and BRIEF-0087-d.
- **Backfill.** No existing row is touched. That is BRIEF-0087-c.
- **The selector.** `lore_selectors.py`, `lore_plan.py`, `lore_render.py` and their checks are untouched here. That is BRIEF-0087-e.
- **`knowledge.subject`.** Its type, nullability, index and every read of it stay exactly as they are.
- **A `subject_entity_id` column.** Rejected at A2. Do not add one, and do not add a `subject_situation_id`.
- **`fact_default` and `knowledge_resolve.py`.** Scoped default levels are TICKET-0082's G2a resolution and have nothing to do with subjects.
- **`idx_fact_participant_unique`.** It exists, on `(fact_id, entity_id)`, from TICKET-0082. Do not widen it to include `role`, do not drop it, do not work around it. Widening it was option J3 and Nia rejected it: it is DDL, it would restore the `migration` danger class A2 removed, and it would weaken TICKET-0082's arity invariant by admitting the same entity twice in one fact. The idempotency guard is a read, not a DDL change. No schema change in this lot.
- **A role discriminator.** Dropped at J2. Do not add `role="subject"` back, in any spelling, anywhere. Reactivation condition, grep-verifiable: a fact carries a participant that is not a subject of the knowledge attached to it.
- **Widening `NAMED_RUNGS`.** A third rung would raise coverage (R-06) and is a separate decision Nia has not taken. `subject_resolve` uses the two rungs that exist.

## Invariants to defend

- **Single canon-write paths** (`CLAUDE.md:157-158`). `write_knowledge` stays the only `db.add(Knowledge(...))`; `attach_participants` stays the only `db.add(FactParticipant(...))`. This brief adds a call from the first to the second — a `writes` -> `writes` call, which is what keeps both chokepoints intact. Any construction of `FactParticipant` outside `writes/facts.py` fails `fact_spine.py`'s AST scan.
- **History is sacred** (`CLAUDE.md:159-162`). Untouched: this brief adds no path that overwrites a `knowledge` or `relation` row. A participant attachment is an index annotation on a fact, not a canon edit to a `knowledge` row, and writes no `change_history` entry.
- **`idx_fact_participant_unique`** (`canon_knowledge.py:120`). One participant row per `(fact_id, entity_id)`, from TICKET-0082. This brief is the first code that writes this table, so it is the first that can trip the constraint; the read-before-write guard is what defends it. A caught-and-swallowed `IntegrityError` is not an acceptable substitute — on SQLite it leaves the surrounding transaction in an aborted state, and `_apply_mutation` runs its knowledge write inside a SAVEPOINT (`CLAUDE.md:214-217`).
- **Commit before touching any canon-writing path** (`CLAUDE.md:163`). `writes/knowledge.py` is such a path. Commit before the first edit.
- **No structure without a reader.** `subject_resolve.py` ships with no reader in this brief. Its readers are BRIEF-0087-b, c and d, all in this lot. This is the one case the doctrine admits: a contract written once for named consumers already specified.

## Decision rights

**STOP:**
- Any anchor above has moved.
- `attach_participants` turns out to be reachable only through a path that would make the call from `write_knowledge` an import cycle (`import_cycle.py` fails).
- `write_knowledge` or `_build_knowledge_update` exceeds the 80-line ceiling after the change and cannot be brought back under it by extracting a helper into the same module.
- The codebase has no existing convention for exporting a non-`writes` resolver module's names, so Scope IN item 7 has no answer to copy.
- Any anchor about `fact_participant`'s indexes does not hold — this is the exact claim AMENDMENT-0087-1 corrected, and a second discrepancy there means the tree is not what this lot measured.
- The read-before-write guard cannot be made to work without catching `IntegrityError`.

**ADAPT:**
- `db.get(Fact, fact_id)` returns `None` for an explicitly passed `fact_id`: the existing code path already assumes that fact exists. Raise `ValueError` with the same message shape as the module's other raises, proceed, and report.
- `Fact` is not currently imported in `writes/knowledge.py`: add it to the existing `from ..models import ...` line, proceed, report.
- The docstring count changes trip a docstring-coverage check: adapt the docstrings to satisfy it, proceed, report.
- `subject_resolve.py` needs a `Session` import that duplicates an existing style choice elsewhere: copy the style of `lore_resolve.py`, proceed, report.

**REPORT-ONLY:**
- Any subject-matching weakness observed while testing `resolve_subject` (a name that ought to match and does not). Note it; do not add a rung.
- Any `fact` row whose `content` does not equal the `subject` of the `knowledge` rows pointing at it.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit exists on the branch before the first edit to `writes/knowledge.py`.
- [ ] `write_knowledge(db, entity_id=E, subject="s")` with no `subject_entity_ids` produces exactly the rows it produced before this brief: one `knowledge`, one free-standing `fact` with `content == "s"`, zero `fact_participant`.
- [ ] `write_knowledge(db, entity_id=E, subject="s", subject_entity_ids=[X])` produces one `fact_participant` with `entity_id == X`, `role IS NULL`, `position == 0`, `fact_id` equal to the new knowledge row's `fact_id`.
- [ ] Calling that same write twice with the same `X` on the same explicit `fact_id` produces exactly one `fact_participant` row, raises no `IntegrityError`, and leaves the surrounding transaction usable.
- [ ] A fact that already carries `X` under a non-NULL role (a TICKET-0082 arity row, seeded by hand in a fixture) is left exactly as it is: the guard skips it, no second row appears, and the existing row's `role` is unchanged.
- [ ] `write_knowledge(db, entity_id=E, subject="s", subject_entity_ids=[X, X])` produces one `fact_participant` row.
- [ ] `write_knowledge(db, knowledge_id=K, subject_entity_ids=[X])` writes no `fact_participant` row and raises nothing.
- [ ] `write_knowledge(db, mode="level_change", knowledge_id=K, level="knows", subject_entity_ids=[X])` writes no `fact_participant` row and raises nothing.
- [ ] `resolve_subject("Maelis", "verkhaal", db).verdict == "matched"` and its `entity_id` is Maelis's entity id.
- [ ] `resolve_subject("", "verkhaal", db).verdict == "unmatched"`, with no rung call made.
- [ ] `resolve_subject` returns `unmatched` — not an exception — for a subject naming no entity, on all three categories.
- [ ] `python tooling/run.py` — `fact_spine.py`, `single_canon_write.py`, `import_cycle.py`, `module_budget.py`, `function_length.py`, `undefined_names.py` all PASS.
- [ ] `/review-step` and `/close-step` run; engine code is touched.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: one entry recording A2 — the subject of a `knowledge` row is carried by a `fact_participant` on its fact, not by a column on `knowledge`; with the rejected alternative (a nullable `subject_entity_id`) and its reactivation condition (a `knowledge` row must carry a subject differing from its fact's subject). A second entry recording J2 (AMENDMENT-0087-1) — a participant is the aboutness claim, there is no role discriminator, `idx_fact_participant_unique` on `(fact_id, entity_id)` is the identity; with J3 (widening the index) rejected as DDL that would weaken TICKET-0082's arity invariant, and the reactivation condition for a discriminator: a fact carries a participant that is not a subject of the knowledge attached to it.
- `CLAUDE.md`: one line in the invariants section stating that a `fact_participant` row is the aboutness claim for every `knowledge` row on that fact, that `role` is descriptive and never a filter, and that `(fact_id, entity_id)` is unique so every writer reads before it writes. Respect the 500-line budget and its character-budget check; if the budget is tight, this line takes precedence over nothing and is a STOP rather than a silent drop of something else.
- No schema changelog entry. No schema version bump. There is no DDL in this brief.
