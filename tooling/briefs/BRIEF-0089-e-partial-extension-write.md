# BRIEF 0089-E — "A partial extension no longer erases what it omits"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: BRIEF-0089-b (line budget in `crud/entities.py`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/cockpit/crud/entities.py` -> `_build_extension_kwargs`,
  verbatim:
  ```
  def _build_extension_kwargs(db: DbSession, entity_type: str, data: dict) -> dict:
      spec = ENTITY_TYPE_REGISTRY[entity_type]
      ext_kwargs = {f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in spec["fields"]}
      if entity_type == "item" and ext_kwargs.get("equipped") and not ext_kwargs.get("owner_id"):
          raise HTTPException(422, "Equipping an item requires an owner")
      return ext_kwargs
  ```
- It has exactly two call sites: `:611` inside `_create_static_entity_core`
  and `:772` inside `update_entity`.
- `src/world_engine/cockpit/crud/entity_runtime.py:60-61` ->
  `_build_runtime_ext_kwargs(db, fields, data)` returns
  `{f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in fields}`.
  It has exactly two call sites: `:664` and `:784` of `entities.py`.
- `entity_runtime.py:91-93` -> `_update_runtime_ext_row` executes
  `sa_update(table).where(table.c.id == entity_id).values(**ext_kwargs)`
  with no empty-kwargs guard.
- `src/world_engine/cockpit/crud/_shared.py` -> `_validate_entity_ref` returns
  `None` for any falsy value without raising; `_coerce_field`'s text branch
  returns `field.get("default")` for `None` or `""`.
- `crud/__init__.py` re-exports `_build_extension_kwargs` from `.entities`.
- `update_entity` is at most 76 physical lines after BRIEF-0089-d, against an
  80-line cap; `crud/entities.py` is at most 894 lines.

## Facts carried

**R-10 — an absent extension key writes NULL, silently.**
`_build_extension_kwargs` returns one entry per registry field, `data.get`
yielding `None` for an absent key; `_coerce_field`'s `entity_ref` branch calls
`_validate_entity_ref`, which returns `None` for any falsy value without
raising; `update_entity` then `setattr`s every returned key. Consequence: a
`PUT` with a partial extension erases the omitted columns, with a 200
response.

**R-11 — the sheet sends the complete registry field set, or fails before
sending.** `saveSheet` loops over the base fields and the type's fields
calling `readFieldValue` inside a `try` whose `catch` aborts the save;
`readFieldValue` dereferences `.value`/`.checked` with no null guard, so a
missing element raises and the save never happens. Consequence: the sheet is
not the source of a partial payload; its failure mode is an empty-valued
present key, which is brief F's subject.

**R-27 — production state, measured.** Six live NPCs carry a NULL
`current_location_id`. Nothing establishes they were erased rather than
authored that way; D1 leaves them alone. This brief closes the path, it does
not attribute the six.

**R-14 — function length ceilings.** `MAX_LINES = 80`, no baseline. This brief
takes at most 3 of `update_entity`'s remaining free lines.

## Contracts

**C-04 — `_build_extension_kwargs`, extended**
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Signature: `_build_extension_kwargs(db: DbSession, entity_type: str, data: dict, *, present_only: bool = False, current: Any = None) -> dict`
Behaviour: unchanged when `present_only` is `False` -- one entry per registry
field, absent keys coerced from `None`. When `present_only` is `True`, only
fields whose name is a key of `data` appear in the result; the coercion of
each present field is unchanged, so an explicit `""` still clears an
`entity_ref` and an explicit `null` still clears a text field. The `item` /
`equipped` guard is evaluated against the EFFECTIVE value of each of its two
inputs: the built value when the key is present, otherwise
`getattr(current, name, None)`.
Return shape: `{field_name: coerced_value}`.
Error and empty cases: with `present_only=True` and no registry field present
in `data`, returns `{}`. With `present_only=False`, `current` is ignored.

**C-05 — `_build_runtime_ext_kwargs`, extended**
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Signature: `_build_runtime_ext_kwargs(db: DbSession, fields: list[dict], data: dict, *, present_only: bool = False) -> dict`
Behaviour: identical rule to `C-04`, over the runtime spec's field list. No
guard clause exists on this path.
Error and empty cases: returns `{}` when nothing is present.

**C-06 — `_update_runtime_ext_row`, guarded**
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Signature: unchanged.
Behaviour: returns immediately without executing a statement when
`ext_kwargs` is empty; otherwise unchanged.
Error and empty cases: this is the whole point -- a SQLAlchemy `update()` with
no `values()` is an error, and `C-05` can now legitimately produce `{}`.

## Context

`PUT /api/entities/{id}` treats its `extension` object as the whole truth: a
key the client did not send is coerced from `None` and written over the stored
column. The cockpit sheet always sends the full set, so the path is not proven
to have fired in production -- but it is reachable by construction from any
other client, and an `entity_ref` erased this way is exactly the state that
makes an NPC unfindable. This brief makes the write additive: a key you do not
send is a key you do not change.

## Scope IN

1. Extend `_build_extension_kwargs` to `C-04`. Keep the comprehension for the
   `present_only=False` path unchanged; for the `True` path, iterate the same
   `spec["fields"]` and skip any field whose `name` is not a key of `data`.
2. Rewrite the `item` / `equipped` guard to read effective values, so that
   equipping an item while sending only `{"equipped": true}` still raises 422
   when the stored `owner_id` is NULL, and does NOT raise when the stored
   `owner_id` is set. Use `current` when the key is absent from the result.
3. Extend `_build_runtime_ext_kwargs` to `C-05` with the same rule.
4. Guard `_update_runtime_ext_row` per `C-06`: return before building the
   statement when `ext_kwargs` is empty.
5. In `update_entity`, and only there, pass the new arguments:
   `ext_kwargs = _build_extension_kwargs(db, entity.type, body.extension, present_only=True, current=ext)`
   and
   `runtime_ext_kwargs = _build_runtime_ext_kwargs(db, runtime_spec["fields"], body.extension, present_only=True)`.
   Both are edits to existing lines, not new lines.
6. Add a comment above the static call stating the rule in one sentence: a key
   absent from the payload preserves the stored column; clearing a field
   requires sending it explicitly empty. Name the precedent already in the
   codebase: `set_location_geometry` uses `body.model_fields_set` for exactly
   this distinction on the two bounds columns.
7. Update `update_entity`'s and both builders' docstrings to state the update
   path's semantics. `update_entity` has no docstring today; give it a
   two-line one saying the entity block is whole-replace and the extension
   block is key-present-wins.

## Scope OUT

- The create paths (`:611`, `:664`). They must keep receiving the full field
  set with defaults applied: creating a row with only the keys the client
  happened to send would leave the rest unset rather than defaulted.
- `_apply_base_fields` and `ENTITY_BASE_FIELDS`. The entity block keeps
  whole-replace semantics; only the extension block changes. Changing both in
  one brief would make a regression impossible to bisect.
- `_coerce_field`, `_validate_entity_ref`, and every other validation rule.
  An explicitly sent empty value still clears, exactly as today.
- Trimming entity names. Recorded in the ticket's carried-forward section.
- The six NPCs with a NULL `current_location_id`. D1: left alone.
- The frontend. Brief F.
- Every other brief in this lot: A, B, C, D, F, G.

## Invariants to defend

- **Fail-closed over advisory.** The `item` / `equipped` 422 must still fire
  on a partial payload; a guard that silently stops applying because its
  input was not sent is the exact failure mode this brief is meant to remove,
  reintroduced one level up.
- **No structure without a reader.** The `present_only` parameter has exactly
  one caller and is not added to the create path "for symmetry".
- **Minimal first, expand later.** The extension block only; the base block
  keeps its semantics.

## Decision rights

STOP:
- `_build_extension_kwargs` or `_build_runtime_ext_kwargs` has acquired a
  third call site since drafting. The blast radius of the semantic change is
  then larger than the contract describes.
- `update_entity` would exceed 80 lines.

ADAPT:
- `crud/__init__.py`'s re-export breaks because of the keyword-only
  parameters: keep the re-export as it is (a default-valued keyword-only
  parameter does not change the import), and if something genuinely breaks,
  report it rather than removing the export.
- The `item` guard needs the stored row and `ext` is `None` at that point on
  some path: treat a missing `current` as "value absent", which reproduces
  today's behaviour, and report.

REPORT-ONLY:
- Any other client of `PUT /api/entities/{id}` you find in the repo, with the
  shape of the payload it sends.
- Whether `_apply_base_fields` has the same erase-on-absence property.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Against a scratch carrier (`WORLD_ENGINE_DATABASE_URL` pointed at a
      throwaway SQLite file, never `~/.world_engine/`), all five rows of the
      lot's case table b3 observed on a character with a set
      `current_location_id`: a `PUT` omitting the key leaves the column
      unchanged; a `PUT` sending `""` clears it; a `PUT` sending `null` clears
      it; a `PUT` sending a valid id sets it; a `PUT` whose extension is `{}`
      changes no extension column and returns 200.
- [ ] Same carrier, the create path is untouched: creating a character with a
      partial extension still applies every registry default.
- [ ] Same carrier, the guard still fires: `PUT` on an item with
      `{"equipped": true}` and a stored `owner_id` of NULL returns 422; the
      same `PUT` with a stored `owner_id` set returns 200.
- [ ] Same carrier, the runtime branch: a `PUT` on a governed runtime type
      with an extension of `{}` returns 200 and executes no `UPDATE` against
      the reflected table.
- [ ] `update_entity` is at most 79 physical lines.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/function_length.py` passes.
- [ ] `python tooling/verify/checks/json_ui_boundary.py` passes.
- [ ] `python tooling/verify/checks/undefined_names.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: append one entry in the strict header shape
`## THE EXTENSION BLOCK OF A PUT IS KEY-PRESENT-WINS (BRIEF-0089-e, no schema change)`,
recording that the entity block stays whole-replace, that the create paths
keep full-field semantics, and that `set_location_geometry`'s
`model_fields_set` handling is the precedent. Regenerate
`tooling/standards/DECISIONS_INDEX.md` with
`python tooling/glue/gen_decisions_index.py` in the same commit.
