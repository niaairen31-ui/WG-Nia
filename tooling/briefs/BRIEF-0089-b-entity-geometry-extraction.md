# BRIEF 0089-B — "Extract the location geometry and doors write routes"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/cockpit/crud/entities.py` is exactly 1000 lines
  (`python -c "import pathlib;print(len(pathlib.Path('src/world_engine/cockpit/crud/entities.py').read_text(encoding='utf-8').splitlines()))"`).
- `tooling/verify/baselines/` contains no `module_budget.json` and no
  `function_length.json`.
- `crud/entities.py` declares `ObstacleIn` at `:384-388`,
  `LocationGeometryBody` at `:391-394`, `DoorIn` at `:397-400`,
  `LocationDoorsBody` at `:403-404`, `set_location_geometry` at `:883-944`
  (decorator included) and `set_location_doors` at `:946-975`.
- `crud/entities.py` imports `write_location_doors` at `:80` and
  `write_location_obstacles` at `:81`, and calls them only at `:915` and
  `:958` respectively (plus two docstring mentions at `:890` and `:950`).
- `crud/entities.py` declares `_entity_dict`, `_extension_dict`,
  `_location_subculture_rows`, `_location_geometry_dict` and
  `_location_doors_rows`, and its own `get_entity`/`create_entity`/
  `update_entity` call the last three.
- `crud/__init__.py`'s `from .entities import (...)` block names neither
  `set_location_geometry` nor `set_location_doors` nor
  `_location_doors_rows`.
- `crud/_router.py` declares one shared
  `APIRouter(prefix="/api", tags=["author-crud"])`.
- `tooling/verify/checks/json_ui_boundary.py` resolves
  `CRUD_PY = SRC / "world_engine" / "cockpit" / "crud" / "entities.py"` and
  extracts from `"ENTITY_BASE_FIELDS:"` and `"ENTITY_TYPE_REGISTRY:"`.
- Neither end marker the check names -- `"# -- Type"` and
  `"# -- Relation / knowledge field specs"`, with box-drawing dashes -- exists
  anywhere in `crud/entities.py`. `str.find` returns -1 for both, and
  `_extract_between` therefore returns `src[start:]`: each block runs from its
  start marker (`:118` and `:127`) to end of file.

## Facts carried

**R-13 — `crud/entities.py` is at exactly its line cap, with no baseline.**
`MAX_LINES = 1000`; a file passes on `lines <= MAX_LINES`; a file over cap
with no baseline entry is a FAIL; `_load_baseline` returns `{}` when the
baseline file is absent. `tooling/verify/baselines/` holds
`decisions_headers.baseline`, `graph_impls.baseline`, `graph_impls.retired`,
`legacy_calls.baseline`, `legacy_mounts.baseline`. Consequence: one added line
turns the corpus red.

**R-16 — `json_ui_boundary` pins the type registry to `crud/entities.py`.**
`CRUD_PY` is that path in the check, and `_check_crud_registry_volet`
extracts between two literal marker pairs, failing if either block is empty.
Consequence: this extraction may not touch the registry, the base field list,
or the two marker comments.

**R-17 — the route table, as a pure-move witness.** 182 `(path, method)`
pairs over `app.openapi()["paths"]`, including
`('/api/entities/{entity_id}/doors', 'put')` and
`('/api/entities/{entity_id}/geometry', 'put')`. `app.routes` is not usable
for this on the installed FastAPI (included routers are lazy wrappers); the
OpenAPI path map is.

**R-18 — the two moved routes are not re-exported, so the package `__init__`
must import the new module.** The `from .entities import (...)` block names
31 symbols and neither route. `_router.py` declares one shared router which
every domain module decorates. Consequence: route registration happens by
module import; a new module `__init__.py` never imports registers nothing and
its two routes 404, with no existing check catching it.

**R-19 — what the extracted routes depend on.** `set_location_geometry` and
`set_location_doors` call `_get_entity`, `_entity_dict`, `_extension_dict`,
`_list_relations`, `_list_knowledge`, `_location_subculture_rows`,
`_location_geometry_dict`, `_location_doors_rows`, `write_location_obstacles`,
`write_location_doors`, and use `Location`, `HTTPException`, `Depends`,
`get_session`, and the four Pydantic bodies. `_entity_dict`,
`_extension_dict` and `_location_subculture_rows` are declared in
`entities.py` and consumed by `entities.py`'s own `get_entity`,
`create_entity` and `update_entity`. Consequence: only the routes and their
four body models can move; moving the two readers as well would make
`entities.py` import the new module while the new module imports
`entities.py` -- a module-level cycle.

**E2 — every check naming the two routes.** Two hits, both docstring prose in
`single_canon_write.py:71-72` naming the functions, not a path binding. No
check resolves either route by file path.

## Contracts

This brief produces and consumes no `C-NN`. Its contract is set-identity of
the route table, stated in `R-17`.

## Context

`crud/entities.py` sits exactly on the 1000-line module cap with no baseline
exemption, so briefs D and E -- which each need a handful of lines in
`update_entity` -- cannot be written until the file has headroom. This is a
pure move: no behaviour, no signature, no route path changes. It is the
precondition for two later briefs and nothing else.

## Scope IN

1. Create `src/world_engine/cockpit/crud/entity_geometry.py` with a module
   docstring stating: the location spatial write surface -- playable bounds,
   obstacle polygons and door rows -- extracted from `entities.py`
   (TICKET-0089, BRIEF-0089-b), pure move, no logic change; the readers
   (`_location_geometry_dict`, `_location_doors_rows`) stay in `entities.py`
   because `entities.py`'s own composite reads consume them, and importing
   them from here would close a module-level cycle.
2. Move into it, verbatim, in this order: `ObstacleIn`,
   `LocationGeometryBody`, `DoorIn`, `LocationDoorsBody`,
   `set_location_geometry` (with its `@router.put` decorator and its
   docstring), `set_location_doors` (same). Copy the bodies character for
   character, including the `# F1, TICKET-0040` comment inside
   `set_location_geometry`.
3. Give the new module exactly the imports its content needs:
   `from __future__ import annotations`; `from fastapi import Depends,
   HTTPException`; `from pydantic import BaseModel`;
   `from sqlmodel import Session as DbSession`; `from ...db import
   get_session`; `from ...models import Location`; `from ...writes import
   write_location_doors, write_location_obstacles`;
   `from ._router import router`; `from ._shared import _get_entity,
   _list_knowledge, _list_relations`; and from `.entities`:
   `_entity_dict`, `_extension_dict`, `_location_doors_rows`,
   `_location_geometry_dict`, `_location_subculture_rows`. Add no import the
   moved code does not use, and confirm the `Optional`/`list` annotations the
   four body models carry are satisfied by the imports you add.
4. Delete the six moved definitions from `entities.py`, and delete
   `write_location_doors` (`:80`) and `write_location_obstacles` (`:81`) from
   its `from ...writes import (...)` block -- they have no remaining call
   site there. Leave every other import alone, including `Door`, `Obstacle`,
   `ObstacleVertex` and `Location`, which the surviving readers still use.
5. In `crud/__init__.py`, add
   `from .entity_geometry import set_location_doors, set_location_geometry`
   after the `from .entities import (...)` block, keeping the existing module
   order. This import is what registers the two routes; it is not
   decoration.
6. Touch nothing else in `entities.py`. The registry and the base field list
   stay exactly where they are. Do not add the two end-marker comments
   `json_ui_boundary` names: they are absent today, so its volet (a) scans
   from each start marker to end of file, and the span you are removing
   contains no `"name": "` field spec and no `"kind": "json"` -- both of the
   check's counts are therefore unchanged by the move. Adding the markers
   would narrow a scan this brief has no mandate to change.

## Scope OUT

- `_location_geometry_dict` and `_location_doors_rows`. They stay in
  `entities.py`; moving them is the cycle described in `R-19`.
- `_npc_prices_dict`, `set_npc_prices`, `_location_subculture_rows`,
  `set_location_subculture`, `NpcPricesBody`, `LocationSubcultureBody`. The
  wider extraction was considered and rejected: it mixes the character and
  location strata in one module.
- `ENTITY_BASE_FIELDS`, `ENTITY_TYPE_REGISTRY`, `_build_extension_kwargs`,
  `_coerce_field`, `_apply_base_fields`.
- Any behaviour change, however small: no reordering of statements, no
  renamed local, no tightened validation, no docstring rewrite beyond the new
  module's own header.
- Adding the headroom to a baseline file instead of extracting. No baseline
  file exists and this lot does not create one.
- The route paths. `/api/entities/{entity_id}/geometry` and
  `/api/entities/{entity_id}/doors` keep their exact paths and methods.
- Every other brief in this lot: A, C, D, E, F, G.

## Invariants to defend

- **No catch-all modules.** `entity_geometry.py` holds one stratum -- the
  location spatial write surface -- and is named for it. Do not use it as a
  home for anything else that needs to leave `entities.py`.
- **Single canon-write paths.** Both routes keep calling
  `write_location_obstacles` and `write_location_doors`; neither gains a
  direct table write. `canon_write_policy.txt` needs no new
  `[ALLOWED_SITES]` line, because the sanctioned sites are the `writes/`
  functions and those do not move.
- **Pure-move commits precede new logic.** This commit contains the move and
  nothing else; no line of TICKET-0089's actual fix belongs in it.

## Decision rights

STOP:
- `crud/entities.py` is not at 1000 lines on `main`. The premise of the brief
  has changed and the lot's dependency graph must be re-derived.
- A symbol in the move list has acquired a caller outside `entities.py` since
  drafting.
- The route-table snapshot differs before and after by even one pair.

ADAPT:
- The four body models need a typing import (`Optional`, `Any`) the anchor
  list did not name: add it and report.
- `json_ui_boundary.py` fails: its volet (a) fails only on a zero field count
  or a surviving `"kind": "json"`. Restore whichever the move removed to its
  original position in `entities.py`, proceed, and report.
- A formatter reorders the import block you wrote: accept its order and
  report.

REPORT-ONLY:
- The number of lines `entities.py` ends at.
- Any other symbol in `entities.py` you judge a candidate for a later
  extraction.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] The route table is set-identical before and after. Capture it on the
      pre-change tree and on the post-change tree with
      `WORLD_ENGINE_ENV=test PYTHONPATH=src python -c "from world_engine.cockpit.app import app; spec=app.openapi()['paths']; print(len(sorted((p,m) for p,ops in spec.items() for m in ops)))"`
      plus the sorted list, and diff the two captures: 182 pairs, empty diff.
- [ ] `src/world_engine/cockpit/crud/entities.py` is at most 890 lines.
- [ ] `grep -n "set_location_geometry\|set_location_doors\|ObstacleIn\|DoorIn\|LocationGeometryBody\|LocationDoorsBody" src/world_engine/cockpit/crud/entities.py`
      returns nothing.
- [ ] `python tooling/verify/checks/undefined_names.py` passes.
- [ ] `python tooling/verify/checks/import_cycle.py` passes.
- [ ] `python tooling/verify/checks/json_ui_boundary.py` passes.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/single_canon_write.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] `/review-step` then `/close-step`.

## Docs to update

This step IS the doc update for itself: the new module's header docstring
records the extraction, its date and its reason, in the same shape as
`crud/entity_runtime.py`'s. No `ARCHITECTURE_DECISIONS.md` entry -- a pure
move decides nothing. No schema changelog entry -- no schema change.
