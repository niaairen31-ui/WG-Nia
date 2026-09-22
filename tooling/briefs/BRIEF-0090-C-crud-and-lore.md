# BRIEF 0090-C — "creator CRUD and Lore"

Lot: LOT-0090-oriented-relations.md (authoritative on conflict)
Depends on: BRIEF-0090-A (C-06 to C-09), BRIEF-0090-B (migrated data)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `writes/relations.py` exports `write_oriented_relations`,
  `set_target_knows` and `lien_fact_of` (brief A).
- `EXPECTED_STATIC_SCHEMA_VERSION` is `"v2.04"` and the working database
  answers `SELECT COUNT(*) FROM relation WHERE type NOT IN
  ('connects_to','controls') AND direction != 'a_to_b'` with 0 (brief B).
- `cockpit/crud/relations.py:95-104` — `RelationWriteBody` carries
  `other_entity_id`, `type`, `intensity`, `direction`, `visible_to_b`,
  `notes`.
- `cockpit/crud/relations.py:123-130` — the `connects_to` branch delegates
  to `connect_locations`, then returns `_relation_dict` for the row found by
  `_find_relation_pair`.
- `cockpit/crud/relations.py:136` — create makes the sheet entity
  `entity_a_id`.
- `cockpit/crud/relations.py:173-180` — `delete_relation` removes the
  relation row only.
- `cockpit/crud/_shared.py:141-168` — `RELATION_DIRECTIONS`,
  `RELATION_FIELDS` (which contains a `direction` and a `visible_to_b`
  field-spec), `_relation_dict` returning `role`.
- `crud/entities.py:444` serves `RELATION_FIELDS` as `relation_fields`, and
  `Sheet.svelte:699` reads only its `type` options.
- `lore_selectors.py:102-137` — `_relation_rows` excludes only
  `connects_to` and carries `subject_side`; `lore_render.py:39-44` prints
  the raw `direction`.
- `tooling/verify/canon_write_policy.txt` —
  `src/world_engine/cockpit/crud/relations.py::delete_relation  relation`.

## Facts carried

**R-07** — `cockpit/crud/relations.py:80-208`: `RelationWriteBody` carries
`direction` and `visible_to_b`; create makes the sheet entity `entity_a`
(`:136`) and delegates `connects_to` to `connect_locations` (`:123-130`);
PUT overwrites direction (`:149-170`); DELETE removes the relation row only
(`:173-180`); the graph endpoint exposes `source`, `target`, `direction`
(`:196-208`).

**R-09** — `_relation_dict` (`crud/_shared.py:153-168`) returns `role`;
`_list_relations` (`:170-177`) feeds the entity payload, which is read at
`crud/entities.py:512, 800, 850, 875` and
`crud/entity_geometry.py:111, 141`. `lore_selectors.py:121-136` carries
`subject_side`, which `lore_render.py:39-44` ignores while printing the raw
`direction`.

**R-10** — `creation/DoorsEditor.svelte:34-36` reads `type`,
`other_entity_id` and `other_entity_name` from that same payload, so the
payload change must be additive.

**R-15** — deleting a relation that carries a typed fact raises
`IntegrityError` under `PRAGMA foreign_keys=ON` (`db.py:126`), which is
already true for every `connects_to` edge v2.00 gave a fact, including from
`graph/consumers/lieux.js:41-44`.

**R-21** — `[ALLOWED_SITES]` lines are `path::function  tables`;
`single_canon_write.py` is function-scoped and attributes every `.add()`,
`.delete()` and raw `execute()`.

**R-22** — `CLAUDE.md:288-292`: a `skill_definition` delete already removes
its dependent rows then itself in one transaction, with no history snapshot
— "a named exception to History is sacred, scoped to one row".

## Contracts

Consumed (verbatim from the lot header): C-06 `_find_perceived_relation`,
C-07 `write_oriented_relations`, C-08 `set_target_knows`, C-09
`lien_fact_of`, C-12 `idx_relation_oriented_social`.

### C-07 — `write_oriented_relations` (consumed)
```
write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type,
                         value, direction, visible_to_b=False, notes=None,
                         changed_by, mode="set", relation_id=None) -> list[Relation]
```
Normalizes with C-04, one `write_relation(mode="set", direction="a_to_b")`
per spec in order, then C-08 for each spec whose `target_knows` is True.

### C-08 — `set_target_knows` (consumed)
`set_target_knows(db, *, rel, knows, changed_by) -> Optional[Knowledge]` —
social only (`ValueError` otherwise); True creates `entity_b`'s knowledge row
on the lien fact if absent, idempotent; False deletes it if present; no lien
fact raises `ValueError`.

Produced by this brief:

### C-10 — the relation payload
`_relation_dict` keeps every key it returns today (`id`, `role`,
`other_entity_id`, `other_entity_name`, `other_entity_type`, `type`,
`direction`, `intensity`, `visible_to_b`, `notes`, `last_evolved_at`) and
adds: `perceiver_id`, `perceiver_name`, `target_id`, `target_name`,
`sheet_side` (`"perceiver"` when the sheet entity is `entity_a`, else
`"target"`), `is_social` (bool), `target_knows` (bool; always False for a
structural row).

### C-13 — the target-knows route
`PUT /api/relations/{relation_id}/target-knows`, body `{"knows": bool}`.
404 on an unknown relation; 409 on a structural relation; returns
`_relation_dict(rel, rel.entity_a_id, db)`.

## Context

The data is oriented and every social relation carries its lien fact. The
creator surfaces still speak the old vocabulary: a direction select, a
"Visible to B" checkbox nobody reads, a delete that now fails on every
social relation, and a Lore dossier printing `a_to_b`. This brief fixes the
backend half; the editors follow in brief D.

## Scope IN

1. `crud/_shared.py`:
   - `_relation_dict` implements C-10. `perceiver_*`/`target_*` come from
     `entity_a`/`entity_b` (orientation is now a fact, not a computation);
     `target_knows` is `lien_fact_of(db, rel)` plus a `knowledge` lookup on
     `(fact_id, entity_id=rel.entity_b_id)`, False when the relation is
     structural.
   - Remove the `direction` and `visible_to_b` entries from
     `RELATION_FIELDS` (only its `type` options are consumed —
     `Sheet.svelte:699`). Leave `RELATION_DIRECTIONS` in place; brief E
     still needs the vocabulary for staged link rows.
2. `crud/relations.py` — create route:
   - `RelationWriteBody` gains `reciprocal: Optional[bool] = None` and keeps
     `direction`/`visible_to_b` as accepted-but-ignored fields for social
     relations (a stale client must not 422 mid-lot); document that in the
     body class docstring.
   - Social type: pre-check `_find_perceived_relation(db, entity_id,
     other_entity_id)` and return 409 naming the existing relation if it is
     there; same check for the reverse direction when `reciprocal` is true.
     Then one call to `write_oriented_relations(..., direction="mutual" if
     reciprocal else "a_to_b", visible_to_b=False)` and return
     `_relation_dict(rows[0], entity_id, db)` — the shape callers already
     expect.
   - `connects_to` branch: unchanged.
   - `controls`: `write_relation(..., direction="a_to_b")` with the sheet
     entity as the controller, unchanged behaviour.
3. `crud/relations.py` — update route: pass `direction="a_to_b"` for a
   social relation and `rel.direction` for a structural one; never read
   `body.direction`. `visible_to_b` is passed through unchanged from the row
   (the column is dead weight this ticket keeps).
4. `crud/relations.py` — delete route (T1): in one transaction, and in this
   order with a `db.flush()` between layers, delete the `knowledge` rows of
   the relation's lien fact, then its `fact_default` rows, then the fact,
   then the relation. A relation with no fact deletes as today. Docstring
   names R-22's precedent and says this is a creator correction, so the
   knowledge of a relation that never existed goes with it.
5. `crud/relations.py` — add C-13, calling `set_target_knows`.
6. `tooling/verify/canon_write_policy.txt`: `delete_relation`'s table list
   becomes `relation knowledge fact_default fact`, with a
   `# TICKET-0090, BRIEF-0090-c` comment saying the cascade is the
   creator-correction hard delete of a relation and everything that only
   existed to describe it.
7. `lore_selectors.py`: `_relation_rows` adds `subject_name` (the dossier
   entity's own name) to each row, alongside the existing `subject_side`.
   No other shape change; the selector stays read-only.
8. `lore_render.py`: `_format_relations` renders by perceiver and never
   prints `direction`:
   - `subject_side == "a"`: `f"{subject_name} → {type} → {other} (intensité {intensity})"`
   - `subject_side == "b"`: `f"{other} → {type} → {subject_name} (intensité {intensity})"`
   Keep the existing notes/secret handling of that function unchanged.
9. Update the docstrings of `_relation_dict`, the create/update/delete
   routes and `_format_relations` to state the orientation rule.

## Scope OUT

- Any `.svelte` or `.js` file, and any frontend build: briefs D and E. The
  sheet will still send `direction` until D lands; the route ignores it.
- `link_author.py`, its whitelist and its commit: brief E.
- `writes/` — brief A owns the writers. If a route needs behaviour the
  contracts do not give, that is a STOP.
- Any change to the graph edge payload (`crud/relations.py:196-208`): the
  edge keeps `direction`; brief D stops displaying it.
- Dropping `relation.visible_to_b` or removing it from the payload.
- Making the Lore dossier show `controls` differently, or excluding it.
- Any new selector, section or verdict on the Lore surface.

## Invariants to defend

- **Creator control is structural** — the Lore surface stays read-only:
  nothing in `lore_selectors.py` or `lore_render.py` may gain a `db.add`, a
  `commit`, or a writer import (`lore_isolation.py` R1).
- **Two canon-write paths for rows** — the delete cascade is registered in
  `canon_write_policy.txt` (Scope IN 6); no other new `.delete()` site
  appears.
- **History is sacred**, with the delete cascade as the named exception
  recorded in brief B's ARCHITECTURE_DECISIONS entry (R-22's family).
- **The MJ context assembler is scoped to the player's perception
  boundary** — this brief must not widen what the payload exposes to any
  player-facing path; `_relation_dict` is creator-facing only.

## Decision rights

STOP:
- Any anchor above has moved.
- A social relation is found with no lien fact (brief B did not run, or its
  post-checks lied).
- The delete cascade cannot be made to work without touching `writes/`.
- A player-facing reader of `_relation_dict` is found (today it is creator
  CRUD only).

ADAPT (do it, then report):
- `_relation_dict` passes the 80-line cap or needs a second query per row:
  extract a private helper in `_shared.py`.
- An existing consumer of `RELATION_FIELDS` needs the removed specs: put
  them back and report instead of breaking it.
- The 409 pre-check races the unique index and an `IntegrityError` still
  surfaces: catch it in the route and return the same 409.
- `_format_relations` has a second caller expecting the old string: update
  it and report.

REPORT-ONLY:
- Relations whose lien content names an entity that has since been renamed
  (F1's job).
- `controls` rows shown in the dossier with no orientation sentence.
- Any `connects_to` row still without a fact after brief B.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `GET /api/entities/{id}` returns relations carrying `perceiver_name`,
      `target_name`, `sheet_side`, `is_social` and `target_knows`, and still
      carrying `type`, `other_entity_id` and `other_entity_name`.
- [ ] `POST /api/entities/{id}/relations` with `reciprocal: true` creates two
      rows; a second identical POST returns 409 and creates nothing.
- [ ] `PUT /api/relations/{id}/target-knows` with `{"knows": true}` creates
      exactly one `knowledge` row for the target on the lien fact; with
      `{"knows": false}` it removes it; twice in a row changes nothing.
- [ ] `DELETE /api/relations/{id}` on a social relation returns 200 and
      leaves no `fact`, `fact_default` or `knowledge` row pointing at it.
- [ ] `DELETE` on a `connects_to` edge created before this ticket also
      returns 200 (R-15's latent bug is gone).
- [ ] The Lore dossier of an entity shows `X → méfiance → Y (intensité 28)`
      and no `a_to_b` anywhere.
- [ ] `python tooling/verify/checks/lore_isolation.py`,
      `single_canon_write.py`, `relation_orientation.py` and
      `corpus_gate.py` all print PASS.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/verify/canon_write_policy.txt` (Scope IN 6).
- Route and renderer docstrings (Scope IN 9).
- No schema change here; no changelog entry.
