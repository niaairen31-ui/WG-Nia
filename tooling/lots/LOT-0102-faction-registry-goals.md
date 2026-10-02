# LOT — TICKET-0102 "Factions cannot be created, opened or edited"

## Objective and cut

Since TICKET-0091 (BRIEF-0091-i, commit `fa78c49`, 2026-09-23), every
faction answers 500 on create, read and update. The creator-CRUD registry
still declares a `goals` field the `faction` table no longer has (R-01,
R-02); the response builder reads every declared field off the row (R-03).
A create commits before it raises, so Nia saw the faction appear after a
refresh and could not open it.

The lot removes the dead field (A1) and adds the structural guard that
would have caught it (B1). It stops there: no data repair (C1), no live
round-trip check per type (B2 rejected), no change to the region commit,
the facts editor, or any reader of `visee`.

## Briefs in this lot

- **A — faction registry goals** (no schema change):
  `cockpit/crud/entities.py` drops the faction `goals` field and says why in
  a comment; new `tooling/verify/checks/registry_model_columns.py` (C-01);
  the decision entry.

## Dependency graph

One brief, nothing to order. Brief A appends an entry just above the footer
of `tooling/standards/ARCHITECTURE_DECISIONS.md`.

## RECON

Opened on `main` at `3eda315` (merge of PR #132, `ticket/0101`): corpus
135/135 green. Defect reproduced through `TestClient(app)` on a freshly
initialized and seeded scratch database. Then prototyped on a copy (branch
`proto/0102`), one commit, corpus 136/136 green; the fiche's create flow
replayed against the fixed branch (R-06). Last, this ticket, this header
and the brief were placed in the copy and `pipeline_state.py` run; the
brief's diff was extracted from the prototype commit and `git apply
--check`ed against a clean `3eda315`.

### R-01 — the faction registry entry [M]
Opened: `src/world_engine/cockpit/crud/entities.py:125-201`
(`ENTITY_TYPE_REGISTRY`, the declaring file), whole file 915 lines.
Finding: `"faction"` declares six fields: `faction_type`,
`magic_knowledge_level`, `parent_faction_id`, `scope` (`:183-188`, its
`"options"` line at `:187`), then `{"name": "goals", "label": "Goals",
"kind": "textarea"}` at `:189`. `GET /api/entity-types` serves these fields
verbatim (`get_entity_types`, `:418-461`), and the Création form renders
them.
Consequence: removing `:189` removes the « Goals » field from the form; no
frontend edit (A1).

### R-02 — the `Faction` model [M]
Opened: `src/world_engine/models/canon_faction.py:22-44` (the model, the
declaring file).
Finding: columns `id`, `faction_type`, `magic_knowledge_level`,
`parent_faction_id`, `scope`. A comment at `:28-30` records that
`internal_structure/philosophy/internal_tensions/goals/aversion` moved to
facts in TICKET-0091, schema v2.06 (`visee` for goals). Measured: `PRAGMA
table_info(faction)` on a fresh `init_db.py` database lists the same five.
Consequence: the registry field has no column (A2 rejected: restoring it
reverses TICKET-0091).

### R-03 — where the 500 is raised, and why the row survives [M]
Opened: `src/world_engine/cockpit/crud/entities.py` (`_extension_dict`
`:245-247`; `get_entity` `:520-541`; `create_entity` `:726-771`;
`update_entity` `:774-` ; `_create_static_entity_core` `:596-670`).
Finding: `_extension_dict` returns `{f["name"]: getattr(ext, f["name"])
for f in spec["fields"]}` (`:247`); its three static-type callers are
`get_entity` (`:525`), `create_entity` (`:749`) and `update_entity`
(`:836`). On a `Faction` row, `getattr(ext, "goals")` raises
`AttributeError: 'Faction' object has no attribute 'goals'` (traceback
captured for GET and POST). `create_entity` commits at `:732`, before
building its response, so the faction and its facets persist. On create,
`ext_model(id=entity.id, **ext_kwargs)` (`:640`) receives `goals` and
discards it: a create with `{"goals": "Dominer le port"}` leaves no column
and no fact (measured: zero `fact_participant` rows for that entity).
Measured on `main`: POST 500, GET 500 on every seeded faction, PUT 500 with
or without `goals` in the extension.
Consequence: removing the field fixes all three routes; nothing else in
the response path changes.

### R-04 — where a faction's goals live now [M]
Opened: `src/world_engine/facets.py:20-90` (the facet registry, declaring
file); readers by grep of `"visee"` over `src/`.
Finding: `FacetSpec("visee", "collectif", "affirmation", "none", "Visées",
…)` (`:64`); `DESCRIPTIVE_FACETS` (`:80`) contains `visee`, so `GET
/api/facets` and the sheet's facts editor offer it. Readers: `tick_context.py:338`,
`:666`; `cockpit/routes/creator.py:83`; `cockpit/crud/goals.py:258`;
`npc_group_author.py:322`; `entity_author.py:531` (the faction generator
writes `visee`). `grep -rn "faction.goals\|Faction.goals" src` matches
nothing.
Consequence: Nia keeps her faction goals (clarification); no reader
changes.

### R-05 — the registry against its models, enumerated [M]
Opened: an import of `ENTITY_TYPE_REGISTRY`, `ENTITY_BASE_FIELDS` and
`Entity`, comparing each `field["name"]` to `model.__table__.columns`.
Finding (raw output, `main`):
```
character missing in model: []
location missing in model: []
faction missing in model: ['goals']
item missing in model: []
base fields: ['name', 'internal_name', 'is_public', 'status'] missing: []
```
`_apply_base_fields` (`:331-335`) sets each base field on the `Entity` by
name (`setattr(entity, name, value)`, `:335`), so a base field has the same
failure mode.
Consequence: one defect only; C-01 covers both lists.

### R-06 — the fiche's create flow [M]
Opened: `frontend/src/creation/Sheet.svelte:576-660` (`submitEntity`).
Finding: `rolesToCreate` is collected for a new faction (`:579`); the
entity POST (`:594`) must succeed before the role POSTs run (`:619-625`);
on a throw the `catch` writes the error to `#author-status` and the drafts
are not reset. Replayed on `proto/0102`: POST with `faction_type` and a
`visee` facet → 201 (extension keys `faction_type`,
`magic_knowledge_level`, `parent_faction_id`, `scope`); role POST → 201;
GET → 200; PUT → 200; facts list `['visee']`; every faction of the
scratch database → 200; `GET /api/entity-types` has no `goals` field.
Consequence: on `main` the roles in draft were never posted and a second
save created a duplicate faction (C1: Nia repairs by hand).

### R-07 — how the defect shipped [M]
Opened: `tooling/briefs/BRIEF-0091-E-fact-writers.md:60-75` (R-13), `:366-370`
(Scope IN item 3); `git show 924825c` and `git show fa78c49`.
Finding: BRIEF-0091-E removed the registry fields "of the anchors" and left
`goals` (its R-13 recorded `faction.goals` as DORMANT); BRIEF-0091-I
(`fa78c49`) dropped the column and removed `goals` from the model, without
touching the registry.
Consequence: a registry/model mismatch is not caught by any check (R-08):
B1.

### R-08 — the verify corpus [M]
Opened: `tooling/verify/checks/corpus_gate.py` (run on `main`: 135/135),
`json_ui_boundary.py:1-30` (scans the registry text for `"kind": "json"`
only), `dynamic_ext_crud.py:44-62` and `trait_ext_columns.py:24-50` (the
import idiom), `src/world_engine/db.py:1-12, 50-60` (`WORLD_ENGINE_DATABASE_URL`
wins; with neither variable set, importing raises `RuntimeError`).
Finding: no check reads a faction through the CRUD; no check compares the
registry to its models. A check importing `cockpit.crud.entities` must set
`WORLD_ENGINE_DATABASE_URL` first (`dynamic_ext_crud.py:51`).
Consequence: C-01 sets the URL to a throwaway path and creates nothing.

### R-09 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:10-17` (the strict
header pattern); `tooling/standards/ARCHITECTURE_DECISIONS.md` (17 597
lines on `main`, last three `---`, blank, `*Co-built with Claude, June
2026.*`).
Consequence: the entry header is `## … (BRIEF-0102-a, no schema change)`,
inserted above the footer; `DECISIONS_INDEX.md` is regenerated, never
hand-edited.

## Contract sheet

### C-01 — `registry_model_columns.py`
Produced by: A   Consumed by: the corpus gate, every later ticket
A stdlib + `world_engine` import check, no table created, no row read.
Sets `WORLD_ENGINE_DATABASE_URL` to `sqlite:///<tempdir>/check.db` before
importing `world_engine.cockpit.crud.entities` (`ENTITY_TYPE_REGISTRY`,
`ENTITY_BASE_FIELDS`) and `world_engine.models` (`Entity`).
- Extension volet: for every registry entry, every `field["name"]` is in
  `spec["model"].__table__.columns.keys()`; else `FAIL:
  ENTITY_TYPE_REGISTRY[<type>] declares field <name>, which is not a column
  of <Model> (<table>); the create discards it and every read of that type
  raises`.
- Base volet: every `ENTITY_BASE_FIELDS` name is in
  `Entity.__table__.columns.keys()`; else `FAIL: ENTITY_BASE_FIELDS declares
  field <name>, which is not a column of Entity`.
- Vacuous-proof: zero types, zero extension fields or zero base fields
  collected is a FAIL.
- An import failure is a FAIL naming the exception.
- PASS line: `PASS: registry_model_columns -- 4 registry type(s), 18
  extension field(s), 4 base field(s), each a column of its model`.

## Gate output

### (a) Property trace
| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| the faction registry declares `goals` at `:189` | R-01 | `crud/entities.py:125-201` |
| the form renders the registry's fields | R-01 | `crud/entities.py:418-461` |
| `Faction` has no `goals` column | R-02 | `models/canon_faction.py:22-44` |
| goals moved to `visee` facts in v2.06 | R-02, R-04 | `canon_faction.py:28-30`, `facets.py:64` |
| `_extension_dict` reads every declared field | R-03 | `crud/entities.py:245-247` |
| its three callers; create commits first | R-03 | `crud/entities.py:525, 732, 749, 836` |
| a create discards an undeclared column | R-03 | `crud/entities.py:640` (measured) |
| `visee` is offered by the facts editor | R-04 | `facets.py:80` |
| every goals reader reads `visee` | R-04 | the six reader sites, opened |
| only `faction.goals` mismatches | R-05 | enumeration (pasted) |
| base fields are set on `Entity` by name | R-05 | `crud/entities.py:331-335` |
| role drafts post after the create response | R-06 | `Sheet.svelte:576-660` |
| no check compares registry and model | R-08 | `corpus_gate.py` run; `json_ui_boundary.py:1-30` |
| importing `db` without a URL raises | R-08 | `db.py:1-12, 50-60` |
| decision header pattern and footer | R-09 | `decisions_index.py:10-17`, `ARCHITECTURE_DECISIONS.md` tail |

Presupposition sweep: the brief invokes one existing idiom, the temp-URL
import, and names its source (`dynamic_ext_crud.py:51`).

### (b) Case table — the faction routes, before and after A
| route | `main` | after A |
|---|---|---|
| `POST /api/entities` faction, no `goals` | row committed, 500 | 201, four extension keys |
| `POST` with `extension.goals` | row committed, text discarded, 500 | 201, `goals` ignored (not a registry field) |
| `GET /api/entities/{faction}` | 500 | 200 |
| `PUT /api/entities/{faction}` | 500 | 200 |
| `GET /api/entity-types` faction fields | six, `goals` last | five |
| `POST /api/regions/commit` | unchanged (never calls `_extension_dict`) | unchanged |
| any other static type | 200 | 200 (fields unchanged) |

C-01 verdicts:
| registry state | verdict |
|---|---|
| after A | PASS, 4 / 18 / 4 |
| `goals` restored to the faction entry | FAIL, extension volet |
| `description` added to `ENTITY_BASE_FIELDS` | FAIL, base volet |
| registry emptied | FAIL, zero types |

### (c) Enumerations
R-05's raw output is pasted above. The negative claim « no reader reads
`faction.goals` » rests on `grep -rn "faction.goals\|Faction.goals" src`
returning nothing (R-04).

### (d) Families
No family in this lot: one contract. ✓

### (e) Gates
- `registry_model_columns.py` (proposed): satisfied by
  `cockpit/crud/entities.py` after A; needs nothing the check forbids.
- `module_budget.py`, `function_length.py` (passed): `entities.py` gains a
  net two lines, 915 → 917; no function changes length.
- `decisions_index.py` (passed): satisfied by the entry plus the
  regenerated `DECISIONS_INDEX.md`.
- `json_ui_boundary.py` (passed): the registry still carries no `json`
  kind.
- `pipeline_state.py` (passed): run with this ticket placed in
  `tooling/tickets/`.

## Amendments

(none)
