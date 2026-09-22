# BRIEF 0090-A — "oriented core"

Lot: LOT-0090-oriented-relations.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `writes/relations.py:36-51` — `_find_relation_pair` matches both orders,
  no world or type filter, `.first()`.
- `writes/relations.py:62-79` — delta mode changes only `intensity` and
  `last_evolved_at` on an existing row; `type` is used only when creating.
- `writes/relations.py:123-124` — new rows default to `direction="mutual"`
  and `visible_to_b=True`.
- `context.py:108-110` — `RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to",
  "controls")`, imported by `crud/relations.py:18`, `link_context.py:21`,
  `link_author.py:34`.
- `writes/facts.py:22-46` — `create_fact(db, *, world_id, content,
  created_by, default_level="unaware", relation_id=None, event_id=None,
  world_law_id=None)`.
- `writes/knowledge.py:226-254` — `write_knowledge` accepts `fact_id` and
  calls `db.add` itself.
- `checks/known_reachability.py:277-283` — an edge deliberately created
  with no fact, to prove the fail-closed rule.
- `checks/fact_spine.py:126-135` — a social `ally` relation written with
  `direction="mutual"`, then a manual `create_fact(relation_id=…)`.
- `tooling/verify/canon_write_policy.txt:19` —
  `src/world_engine/writes/relations.py::write_relation  relation`.

## Facts carried

**R-01** — `models/canon_knowledge.py:23-53`: the only CHECK on `relation` is
`intensity BETWEEN 1 AND 100`; the three indexes are plain; `direction`
defaults to `'mutual'` with no CHECK; `visible_to_b` defaults TRUE; `type`
is free text; `change_history` is JSON NOT NULL.

**R-02** — every perceiver reader treats `entity_a` as the perceiver under
`a_to_b`: `context.py:128-134`, `tick_context.py:112-116` (imported by
`tick_normalize.py:28`), `play_initiative.py:457-462`. Normalizing every
social row to `a_to_b` leaves them correct with no edit.

**R-04** — `writes/relations.py:1-174` is the single sanctioned `relation`
write site (`canon_write_policy.txt:19`). `_find_relation_pair` (`:36-51`)
is order-blind and type-blind. Delta (`:62-79`) uses `type` only on create.
Set with `relation_id` (`:88-100`) snapshots history, then overwrites type,
direction, visible_to_b and notes.

**R-06** — `_find_relation_pair` has four callers: `writes/relations.py:68`
(delta), `cockpit/mutations.py:556` (the `relation_gte` prerequisite judge),
`tick_context.py:171` (the briefing prerequisite line), and
`cockpit/crud/relations.py:129`, which returns the `connects_to` row just
written by `connect_locations`. The finder's docstring (`:37-45`) requires
the judge, the briefing and the write path to share one pair semantics.

**R-13** — `create_fact` accepts `relation_id`; `attach_participants`
(`writes/facts.py:66-74`) refuses a fact whose typed FKs are not all NULL.
`migrate_v2_00_connects_to_facts.py` gave each `connects_to` edge a fact with
content `"{name_a} communique avec {name_b}."` and `default_level='knows'`.

**R-17** — `checks/fact_spine.py:126-135` and `checks/known_reachability.py`
(`:122-137`, `:224-238`, `:277-283`) build relations through
`write_relation` and then create the typed fact by hand; case 3 of
`known_reachability` deliberately leaves an edge with no fact.

**R-18** — `function_length.py:29` caps a function at 80 physical lines;
`module_budget.py:58` caps a module at 1000.

**R-21** — `[ALLOWED_SITES]` lines in `canon_write_policy.txt` are
`path::function  tables`; `single_canon_write.py` is function-scoped and
attributes every `.add()`, `.delete()` and raw `execute()`.

**R-23** — `writes/_shared.py:25-41`: `_append_history_snapshot` records
`intensity`, `last_evolved_at` and `mutation_id` only.

**R-24** — `connects_to` is created at four places
(`crud/relations.py:123-130`, `room_batch.py:162`, `:186`,
`regions.py:281-286`), all crossing `write_relation`; `connect_locations`
(`spatial_author.py:124-131`) writes the relation and no fact.

## Contracts

This brief produces C-01, C-02, C-03, C-04, C-05, C-06, C-07, C-08, C-09 and
C-11, verbatim from the lot header:

### C-01 — `lien_fact_content`
Module: `src/world_engine/relation_orientation.py`
`lien_fact_content(name_a: str, relation_type: str, name_b: str) -> str`
returns `f"{name_a} éprouve « {relation_type} » envers {name_b}."`
No validation, no DB.

### C-02 — `connects_to_fact_content`
`connects_to_fact_content(name_a: str, name_b: str) -> str` returns
`f"{name_a} communique avec {name_b}."` — byte-identical to migrate_v2_00.

### C-03 — `is_social` and the excluded set
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to", "controls")`
`is_social(relation_type: str) -> bool` — `relation_type not in
RELATION_GRAPH_EXCLUDED_TYPES`; `None` returns False.
`context.py` imports the constant from here instead of declaring it.

### C-04 — `orient_legacy`
```
@dataclass(frozen=True)
class OrientedSpec:
    perceiver_id: str
    target_id: str
    target_knows: bool
    visibility_ambiguous: bool

orient_legacy(direction, entity_a_id, entity_b_id, visible_to_b) -> list[OrientedSpec]
```
| direction | visible_to_b | returns |
|---|---|---|
| `a_to_b` | True | `[(a, b, True, False)]` |
| `a_to_b` | False | `[(a, b, False, False)]` |
| `b_to_a` | True | `[(b, a, False, True)]` |
| `b_to_a` | False | `[(b, a, False, False)]` |
| `mutual` | either | `[(a, b, False, False), (b, a, False, False)]` |
| anything else | any | `ValueError` naming the value |

### C-05 — `write_relation`, amended
`direction: str = "a_to_b"` (was `"mutual"`).
- social + `direction != "a_to_b"` -> `ValueError`
  (`"write_relation: social relation <type> must be a_to_b, got <direction>"`).
- on every create, after `db.add(rel)` and `db.flush()`: social ->
  `create_fact(content=lien_fact_content(...), default_level="unaware",
  relation_id=rel.id, created_by=changed_by)`; `connects_to` -> same with
  C-02's content and `default_level="knows"`; `controls` -> no fact.
- `mode="set"` with `relation_id` on a social row whose `type` changes ->
  `update_typed_fact_content` (C-11).
- `mode="delta"`: social -> C-06; excluded types -> `_find_relation_pair`.
- unknown endpoint entity -> `ValueError` naming the id.

### C-06 — `_find_perceived_relation`
`_find_perceived_relation(db, perceiver_id, target_id) -> Optional[Relation]`
— `entity_a_id == perceiver_id`, `entity_b_id == target_id`,
`is_social(type)`, `.first()`.

### C-07 — `write_oriented_relations`
```
write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type,
                         value, direction, visible_to_b=False, notes=None,
                         changed_by, mode="set", relation_id=None) -> list[Relation]
```
Normalize with C-04, one `write_relation(mode="set", direction="a_to_b")`
per spec in order, then C-08 for each spec whose `target_knows` is True.
`mode != "set"` or `relation_id is not None` -> `ValueError`.

### C-08 — `set_target_knows`
`set_target_knows(db, *, rel, knows, changed_by) -> Optional[Knowledge]` —
social only (`ValueError` otherwise). True: create `entity_b`'s knowledge row
on the lien fact if absent (`write_knowledge(mode="update",
entity_id=rel.entity_b_id, fact_id=lien.id, subject=lien.content,
content=lien.content, level="knows", source=f"relation {rel.id}",
is_secret=False, is_incorrect=False, share_threshold=50,
changed_by=changed_by)`); idempotent. False: delete that row if present.
No lien fact -> `ValueError` naming the relation id.

### C-09 — `lien_fact_of`
`lien_fact_of(db, rel) -> Optional[Fact]` — the `fact` row whose
`relation_id` is `rel.id`, or None.

### C-11 — `update_typed_fact_content`
`update_typed_fact_content(db, *, fact, content, changed_by) -> Fact` in
`writes/facts.py`: append `{"content": <previous>, "changed_by": …,
"at": <iso>}` to `fact.change_history`, `flag_modified`, set the new
content, `db.add(fact)`.

## Context

TICKET-0090 makes every social relation one perceiver's feeling toward one
target. This brief lands the backend core only: the pure module, the writer,
the oriented finder, and the gate. The schema index and the data migration
are brief B; nothing here reads or requires migrated data.

Known intermediate state, accepted: from this commit until BRIEF-0090-C, the
creator relation form still sends `direction`, so creating a social relation
from the sheet fails. That is expected and is repaired by C.

## Scope IN

1. Create `src/world_engine/relation_orientation.py` — pure, no DB import,
   stdlib plus `dataclasses`. It holds C-01, C-02, C-03 and C-04, and
   nothing else. Module docstring states that it is the single source of the
   social/structural split and of the two fact-content templates, and that
   `context.py` re-imports the constant from here.
2. In `context.py`, replace the `RELATION_GRAPH_EXCLUDED_TYPES = (...)`
   assignment at `:110` with
   `from .relation_orientation import RELATION_GRAPH_EXCLUDED_TYPES`,
   keeping the comment at `:108-109` in place above the import. Every
   current importer (`crud/relations.py:18`, `link_context.py:21`,
   `link_author.py:34`) keeps importing from `context`; do not touch them.
3. In `writes/relations.py`, implement C-05, C-06, C-07, C-08 and C-09. The
   fact birth goes in a module-level helper `_birth_typed_fact(db, rel,
   changed_by)`, not inline in `write_relation` (R-18: 80-line cap). The
   helper reads both endpoint names with `db.get(Entity, …)` and raises
   `ValueError` naming a missing id.
4. `db.flush()` after `db.add(rel)` and before `create_fact`: there is no
   ORM `relationship()` between `Fact` and `Relation`, so the unit of work
   has no dependency edge and can flush the child first.
5. In `writes/facts.py`, add C-11.
6. Route the three social callers of `_find_relation_pair` to C-06:
   `writes/relations.py:68` (delta, social branch only),
   `cockpit/mutations.py:556`, `tick_context.py:171`. Leave
   `cockpit/crud/relations.py:129` on `_find_relation_pair` — it is the
   `connects_to` lookup. Update `_find_relation_pair`'s docstring to say it
   is now the structural-relation finder and that C-06 is the social one.
7. `tooling/verify/canon_write_policy.txt`: add, with a
   `# TICKET-0090, BRIEF-0090-a` comment above them,
   `src/world_engine/writes/relations.py::set_target_knows  knowledge` and
   `src/world_engine/writes/facts.py::update_typed_fact_content  fact`.
8. Rewrite `checks/fact_spine.py:126-135`'s fixture: `direction="a_to_b"`,
   and take the typed fact from `lien_fact_of` (or a direct select on
   `Fact.relation_id`) instead of calling `create_fact` by hand. The
   deliberate-break assertion at `:168-172` is unchanged.
9. Rewrite `checks/known_reachability.py`'s three fixtures:
   - `:122-137` — drop the manual `create_fact`; read the auto-born fact
     per edge (`select(Fact).where(Fact.relation_id == rel.id)`) into
     `fact_ids`.
   - `:224-238` — same, and put the world-scoped `rumor`
     `create_fact_default` on the auto-born fact of edge D->E.
   - `:277-283` — build the deliberately fact-less edge with
     `session.add(Relation(world_id=…, entity_a_id=…, entity_b_id=…,
     type="connects_to", direction="mutual", intensity=50))` instead of
     `write_relation`, with a comment saying why: `write_relation` now
     births the fact, and this case exists to prove the reader is
     fail-closed without one.
10. Create `tooling/verify/checks/relation_orientation.py`, a DB-backed
    check on a fresh temp-file SQLite fixture (`WORLD_ENGINE_DATABASE_URL`
    set before any `world_engine` import — the `fact_spine.py` /
    `door_coverage.py` idiom), asserting:
    a. `write_relation` refuses a social row with `direction="mutual"` and
       with `"b_to_a"`, each raising `ValueError`, and accepts `a_to_b`.
    b. after creating one social, one `connects_to` and one `controls`
       relation, exactly one `fact` row points at each of the first two and
       none at the third; the social fact's `default_level` is `unaware`
       and the `connects_to` fact's is `knows`; the social content equals
       `lien_fact_content(...)` called by the check itself, never a
       re-typed literal.
    c. with A->B and B->A both present, a delta on (B, A) moves only the
       B->A row's intensity — the other row's intensity and
       `change_history` length are unchanged.
    d. `set_target_knows` is idempotent both ways: True twice leaves one
       knowledge row, False removes it, False again is a no-op.
    Zero rows examined in any assertion is a FAIL, never a vacuous pass.
11. Update the module docstrings of `writes/relations.py` (orientation rule,
    the two finders, the typed fact at birth) and `writes/facts.py`
    (C-11).

## Scope OUT

- The partial unique index, the schema version, the migration script and
  every doc header: brief B.
- CRUD routes, `_relation_dict`, the delete cascade, the target-knows route
  and the Lore renderer: brief C.
- Every `.svelte` and `.js` file, and any frontend build: briefs D and E.
- The link agent (`link_author.py`, its whitelist, its commit): brief E.
- Dropping `relation.visible_to_b`, or making writers stop setting it — a
  named deferral of this ticket, not a step here.
- Identity tokens in the lien content (F1), facets (G2), the `rencontre`
  registry (R1) — later tickets.
- `controls` relations gain nothing: no fact, no orientation guard.
- Do not "fix" `regions.py:281-286` to call `connect_locations` (R-24); it
  is out of scope and its doors behaviour is not this ticket's subject.

## Invariants to defend

- **Two canon-write paths for rows** (CLAUDE.md): every new write goes
  through an existing chokepoint (`create_fact`, `write_knowledge`) or is
  registered in `canon_write_policy.txt` (Scope IN 7). No new
  `db.add(Fact(...))` outside `writes/facts.py` — `fact_spine.py`'s AST scan
  enforces it.
- **History is sacred on both write paths:** C-11 appends the previous
  content before overwriting; the existing relation snapshot behaviour is
  untouched.
- **`connects_to` is location map topology, never a social signal:** the new
  orientation guard must never apply to it, and `is_social` is the only
  place that decides.
- **Commit before touching a canon-writing path** — this brief touches
  `writes/relations.py`.

## Decision rights

STOP:
- Any anchor above that has moved.
- `known_reachability.py` or `fact_spine.py` cannot be made green by the
  fixture rewrites described in Scope IN 8-9 — that means the fact-at-birth
  rule conflicts with a check's rule, which is Nia's call, not a workaround.
- A fifth caller of `_find_relation_pair` exists that is neither social nor
  `connects_to`.

ADAPT (do it, then report):
- `write_relation` passes 80 lines after the change: extract a second
  private helper, keeping one public entry point.
- A docstring elsewhere in `writes/` states the old `mutual` default:
  correct it in place.
- `_find_perceived_relation` needs an explicit `world_id` filter to satisfy
  an existing query pattern: add it, keeping the signature keyword-only.
- The temp-file fixture idiom in `fact_spine.py` has drifted from
  `door_coverage.py`: follow `fact_spine.py`, the newer of the two.

REPORT-ONLY:
- The delta still ignores `type` on an existing row (lot S-2).
- Any `connects_to` relation found without a fact — brief B backfills them.
- `regions.py` writing `connects_to` directly instead of through
  `connect_locations` (R-24).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/relation_orientation.py` prints PASS and
      names the four assertions with non-zero counts.
- [ ] `python tooling/verify/checks/fact_spine.py` prints PASS.
- [ ] `python tooling/verify/checks/known_reachability.py` prints PASS,
      including its missing-fact diagnostic case.
- [ ] `python tooling/verify/checks/single_canon_write.py` prints PASS with
      the two new policy lines present.
- [ ] `python tooling/verify/checks/corpus_gate.py` reports every check
      executed and passed.
- [ ] `python tooling/verify/checks/function_length.py` and
      `module_budget.py` print PASS with no new baseline entry.
- [ ] In a Python REPL against a scratch DB: `write_relation(..., type="fear",
      direction="mutual")` raises `ValueError`; with `direction="a_to_b"` it
      returns a row and exactly one `fact` row carries its `relation_id`.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- Module docstrings listed in Scope IN 11.
- `tooling/verify/canon_write_policy.txt` (Scope IN 7).
- No schema changelog entry here — no DDL in this brief. ARCHITECTURE_
  DECISIONS gets one entry for the whole ticket, in brief B.
