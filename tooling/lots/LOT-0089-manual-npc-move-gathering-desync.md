# LOT — TICKET-0089 "Manual NPC move leaves the gathering roster behind"

Drafted 2026-09-18 against a fresh `main` tarball
(`codeload.github.com/niaairen31-ui/WG-Nia/tar.gz/refs/heads/main`), the
production measurement returned by seven read-only queries, and two
experiments on throwaway SQLite carriers. Authoritative on any conflict with
a brief's embedded copy.

Tags: **[M]** opened and measured in the file that DECLARES the property;
**[E]** measured by execution on a throwaway carrier, never the real one;
**[P]** measured on the production database by read-only SELECT, reported by
Claude Code 2026-09-18; **[I]** inferred.

## Objective and cut

Make a manually moved NPC visible again in Play, at both ends of the move,
and close the two paths by which the desynchronisation forms. The lot stops
at: no production data repair, no change to how presence is derived, no
placement or flagging of the six NPCs with a NULL location.

## Briefs in this lot

| letter | slug | one line |
|---|---|---|
| A | live-gathering-enter-guard | The entry guard counts only gatherings with an active member. Unblocks the live partie on its own. |
| B | entity-geometry-extraction | Pure move: the two location geometry/doors write routes leave `crud/entities.py`, which is at its 1000-line cap. |
| C | dissolve-emptied-gathering | `dissolve_emptied` extracted from `migrate_npc`; a gathering left with no active member is dissolved where it is emptied. |
| D | creator-move-arrival | A creator-side location change attaches the NPC at the destination when that location is live in the open session. |
| E | partial-extension-write | A `PUT` whose extension omits a key no longer erases the stored value. |
| F | entity-ref-current-value | The sheet's `entity_ref` select carries an option for the current value even when absent from its candidate list. |
| G | gathering-lifecycle-check | The G1 gate for A, C and D, plus the decision-registry entry and the invariant update. |

## Dependency graph

- A: nothing in this lot. Runs first by locked decision A1, not by dependency:
  it is the brief that makes the current session playable again.
- B: nothing in this lot.
- C: nothing in this lot.
- D: strictly after B (budget: `crud/entities.py` has zero free lines) and
  after C (consumes `C-02`).
- E: strictly after B (same budget reason).
- F: nothing in this lot.
- G: strictly after A, C and D — it asserts the shape all three leave behind.

A, B, C and F may run in any order relative to each other.

---

## RECON

### R-01 — Play-side presence is derived from gathering membership, never from `current_location_id`
Opened: `cockpit/spatial_presence.py:20-53`, `cockpit/play.py:496-554`,
`cockpit/play_initiative.py:46-93`. [M]
Finding: `npc_positions` builds its rosters from `_play._open_gatherings` and
`_play._active_members` and reads no location column. `_say_resolve_speaker`
selects a responder from `_active_members` and downgrades to
`ResponseMode.scene` when none is available (`play.py:548-553`).
`_say_initiative_vote` draws its candidates from the player's gathering and
from the active members of the other open gatherings at the location.
Consequence: an NPC whose `current_location_id` is X but which holds no open
`gathering_member` row is invisible to every Play-side reader. No brief in
this lot changes that derivation.

### R-02 — `_present_npcs` is the only reader that turns a location into a roster
Opened: `gathering.py:57-73`, `gathering.py:183-257`. [M]
Finding: `_present_npcs` selects `Character.current_location_id == location_id`
with `character_type='npc'`, `vital_status='alive'`, `Entity.status='active'`.
Its only caller is `generate_gatherings`, whose only caller is
`enter_location`.
Consequence: regenerating the partition is the only mechanism that converts a
location into memberships. Everything else in the lot is about making that
mechanism reachable.

### R-03 — `enter_location` has exactly one live caller, and it is guarded
Opened: `cockpit/routes/scene.py:81-157`, `gathering.py:359-401`. [M]
Enumeration (gate (c), E1 below): two hits, one of which is the definition.
Finding: `enter_scene` computes `open_g = _open_gatherings(location_id,
sess.id, db)` at `:112` and calls `_enter_location` at `:139` only inside
`if not open_g:` (`:114`). `routes/mutations.py:37-38` imports
`enter_location` and `migrate_npc` and calls neither.
Consequence: one open gathering at the location, of any composition, freezes
the partition for the rest of the session. Brief A changes the predicate at
`:112`, nothing else.

### R-04 — `_open_gatherings` does not look at membership
Opened: `cockpit/play.py:790-797`. [M]
Finding: it selects `Gathering` on `location_id`, `session_id` and
`status == 'open'`. A gathering with zero active members is returned.
Consequence: the guard in R-03 cannot distinguish a live location from a
location holding only shells.

### R-05 — `_active_members` is the single roster authority, with its own filters
Opened: `cockpit/play.py:800-823`. [M]
Finding: it joins `GatheringMember`, `Entity` and `Character` and filters
`left_at IS NULL`, `Entity.status == 'active'`, `Character.vital_status ==
'alive'`. Its docstring designates it the single source of truth for roster
reads: "All roster reads -- initiative vote, speaker selection, context
assembly -- must go through this function".
Consequence: the "has an active member" predicate of brief A must call this
function, not re-express its filters. That is what fixes the helper's home
in `routes/scene.py` (see R-15).

### R-06 — `close_open_memberships` closes rows and dissolves nothing
Opened: `gathering.py:260-282`. [M]
Finding: it sets `left_at = now` on every open row for the entity, never
deletes, does not commit ("the caller owns the transaction"), and contains no
`Gathering` write of any kind.
Consequence: every caller of it can leave an open gathering with zero active
members. This is the production defect.

### R-07 — `migrate_npc` carries the auto-dissolve, after its own commit
Opened: `gathering.py:285-356`. [M]
Finding: after `db.commit()` at `:327`, it iterates the source gathering ids,
skips `target_gathering_id`, and for each source with no remaining active
member: runs `analyze_window` on every open conversation of that gathering
(`:342-352`, each call wrapped in `try/except (Exception, SystemExit)`), then
sets `status='dissolved'` and `dissolved_at=now`, then commits at `:356`.
Consequence: this is the block brief C extracts verbatim. The post-commit
position and the analysis step are both part of the behaviour being moved.

### R-08 — `enter_location` dissolves gatherings without closing their member rows
Opened: `gathering.py:359-401`. [M]
Finding: it sets `status='dissolved'` and `dissolved_at` on each open
gathering at the location+session, after running `analyze_window` on their
open conversations, then calls `generate_gatherings`. It writes no
`GatheringMember.left_at`.
Consequence: member rows survive with `left_at IS NULL` inside dissolved
gatherings. Harmless to every reader in R-01 and R-05, all of which filter
`status == 'open'` first. No brief in this lot changes it; it is recorded so
that a later reader does not mistake such a row for a live membership.

### R-09 — the creator CRUD closes memberships at three sites
Opened: `cockpit/crud/entities.py:787-794`, `:822-830`. [M]
Finding, verbatim at `:787-794`:
```
    # BRIEF-53 A1: a character's location change, or any transition to a
    # non-active entity.status, closes its open gathering_member rows
    # (gatherings are not canon -- no proposed_mutation, no change_history).
    # Re-saving with the same current_location_id must not close anything.
    if entity.type == "character" and ext is not None and ext.current_location_id != prior_location_id:
        close_open_memberships(entity_id, db)
    if prior_status == "active" and entity.status != "active":
        close_open_memberships(entity_id, db)
```
plus `delete_entity` at `:829`. `prior_location_id` is captured at `:771`.
`db.commit()` follows at `:796`.
Consequence: briefs C and D attach to this exact branch. The equality guard
at `:791` is what keeps a re-save from closing anything, and it stays.

### R-10 — an absent extension key writes NULL, silently
Opened: `cockpit/crud/entities.py:359-364`, `cockpit/crud/_shared.py:64-131`. [M]
Finding: `_build_extension_kwargs` returns
`{f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in spec["fields"]}`
-- one entry per registry field, `data.get` yielding `None` for an absent key.
`_coerce_field`'s `entity_ref` branch calls `_validate_entity_ref`, which
returns `None` for any falsy value without raising. `update_entity` then
`setattr`s every returned key.
Consequence: a `PUT` with a partial extension erases the omitted columns, with
a 200 response. Brief E closes this.

### R-11 — the sheet sends the complete registry field set, or fails before sending
Opened: `frontend/src/creation/Sheet.svelte:391-427`, `:478-497`,
`frontend/src/creation/fields.js:15-29`. [M]
Finding: `saveSheet` loops over `registry.entity_base_fields` and
`registry.types[type].fields` calling `readFieldValue`, inside a `try` whose
`catch` aborts the save with a status message. `readFieldValue` reads
`doc.getElementById(...)` and dereferences `.value`/`.checked` with no null
guard, so a missing element raises and the save never happens.
Consequence: the sheet is not the source of a partial payload. Its failure
mode is an empty-valued present key, not an absent key -- which is R-12.

### R-12 — the `entity_ref` select has no option for a current value absent from its candidates
Opened: `frontend/src/creation/Field.svelte`, `entity_ref` branch. [M]
Finding, verbatim:
```
{:else if field.kind === 'entity_ref'}
  {@const candidates = (ctx.entities || []).filter((e) => e.type === field.ref_type && !(field.exclude_self && ctx.entityId && e.id === ctx.entityId))}
  <div class="field-row"><label for={id}>{label}</label>
    <select {id} data-field={field.name} data-kind="entity_ref" disabled={!!field.readonly}>
      <option value="">—</option>
      {#each candidates as e (e.id)}
        <option value={e.id} selected={e.id === resolvedValue}>{e.name}</option>
      {/each}
    </select>
  </div>
```
`ctx.entities` is `creationState.entities`, populated by
`EntityList.svelte:87-96` from an unfiltered `GET /api/entities`.
Consequence: when `resolvedValue` matches no candidate, no option is selected,
the browser keeps the first one (`value=""`), and the next save writes NULL
through R-10's path. Brief F closes this.

### R-13 — `crud/entities.py` is at exactly its line cap, with no baseline
Opened: `tooling/verify/checks/module_budget.py:57-58`, `:186-211`;
directory listing of `tooling/verify/baselines/`. [M]
Finding: `MAX_LINES = 1000`; a file passes on `lines <= MAX_LINES`; a file
over cap with no baseline entry is a FAIL; `_load_baseline` returns `{}` when
the baseline file is absent. `tooling/verify/baselines/` holds
`decisions_headers.baseline`, `graph_impls.baseline`, `graph_impls.retired`,
`legacy_calls.baseline`, `legacy_mounts.baseline` -- no `module_budget.json`,
no `function_length.json`. `len(text.splitlines())` for
`src/world_engine/cockpit/crud/entities.py` is exactly 1000.
Consequence: one added line turns the corpus red. Brief B is a precondition
for D and E, not a tidy-up.

### R-14 — function length ceilings on the functions this lot edits
Opened: `tooling/verify/checks/function_length.py:1-30`; `ast` measurement of
each file. [M]
Finding: `MAX_LINES = 80`, no baseline file, cap enforced on every function.
Current physical lengths: `enter_scene` 76 (`routes/scene.py:82-157`),
`update_entity` 71 (`crud/entities.py:749-819`), `migrate_npc` 72
(`gathering.py:285-356`), `close_open_memberships` 23,
`_build_extension_kwargs` 6.
Consequence: brief A must not add a line inside `enter_scene` (4 free);
brief D and brief E share 9 free lines inside `update_entity`.

### R-15 — `play.py` cannot host a new helper
Opened: `ast`/`wc` measurement of `src/world_engine/cockpit/play.py`. [M]
Finding: 997 lines, 29 functions, against the 1000/40 cap of R-13.
Consequence: the "has an active member" predicate, which must call
`_active_members` (R-05), lives in `routes/scene.py` (427 lines), which
already imports `_active_members` from `..play` (`routes/scene.py:33-42`).

### R-16 — `json_ui_boundary` pins the type registry to `crud/entities.py`, and its two end markers do not exist
Opened: `tooling/verify/checks/json_ui_boundary.py:31-33`, `:108-136`;
`cockpit/crud/entities.py` searched for both markers. [M]
Finding: `CRUD_PY = SRC / "world_engine" / "cockpit" / "crud" / "entities.py"`.
`_extract_between(src, start, end)` returns `src[start:]` when `end` is not
found. `_check_crud_registry_volet` calls it with the end markers `"# -- Type"`
and `"# -- Relation / knowledge field specs"` (box-drawing dashes), and
**neither string occurs anywhere in `crud/entities.py`** -- `str.find` returns
-1 for both, and the file contains no box-drawing comment at all. The two
"blocks" the check inspects therefore each run from their start marker
(`ENTITY_BASE_FIELDS:` at `:118`, `ENTITY_TYPE_REGISTRY:` at `:127`) to end of
file, and the volet passes today because the file tail holds field specs and
no `"kind": "json"`.
Consequence for brief B: the moved span contains no `"name": "` field spec and
no `"kind": "json"`, so both of the check's counts are unchanged by the
extraction. The registry and base field list still may not move (the start
markers must stay in this file), and the brief must NOT add the missing end
markers -- narrowing that scan is a change of gate behaviour, not part of a
pure move.
Recorded as a latent gate weakness in the ticket's carried-forward section:
volet (a) is scanning the whole file tail rather than two bounded blocks, so a
`"kind": "json"` added anywhere below line 118 would be caught, and one added
above it would not.

### R-17 — the route table, as a pure-move witness
Ran: `WORLD_ENGINE_ENV=test PYTHONPATH=src python -c "from
world_engine.cockpit.app import app; ..."` over `app.openapi()["paths"]`. [E]
Finding: 182 `(path, method)` pairs, including
`('/api/entities/{entity_id}/doors', 'put')` and
`('/api/entities/{entity_id}/geometry', 'put')`.
Consequence: brief B's proof of a pure move is set-identity of those 182
pairs before and after. `app.routes` is not usable for this on the installed
FastAPI (included routers are lazy wrappers); the OpenAPI path map is.

### R-18 — the two moved routes are not re-exported, so the package `__init__` must import the new module
Opened: `cockpit/crud/__init__.py:62-96`, `cockpit/crud/_router.py`. [M]
Enumeration (gate (c), E5 below): the `from .entities import (...)` block
names `set_location_subculture`, `set_npc_prices`, `update_entity` and 28
other symbols; it names neither `set_location_geometry` nor
`set_location_doors` nor `_location_doors_rows`.
`_router.py` declares one shared `APIRouter(prefix="/api", tags=["author-crud"])`
which every domain module decorates.
Consequence: route registration happens by module import. A new module that
`__init__.py` never imports registers nothing and its two routes 404, with no
existing check catching it -- which is why R-17's identity check is brief B's
done-means and not a nicety.

### R-19 — what the extracted routes depend on
Opened: `cockpit/crud/entities.py:241-260`, `:268-275`, `:384-404`, `:883-974`. [M]
Finding: `set_location_geometry` and `set_location_doors` call `_get_entity`,
`_entity_dict`, `_extension_dict`, `_list_relations`, `_list_knowledge`,
`_location_subculture_rows`, `_location_geometry_dict`, `_location_doors_rows`,
`write_location_obstacles`, `write_location_doors`, and use `Location`,
`HTTPException`, `Depends`, `get_session`, and the four Pydantic bodies
`ObstacleIn` (`:384-388`), `LocationGeometryBody` (`:391-394`), `DoorIn`
(`:397-400`), `LocationDoorsBody` (`:403-404`).
`_entity_dict`, `_extension_dict` and `_location_subculture_rows` are declared
in `entities.py` and consumed by `entities.py`'s own `get_entity`,
`create_entity` and `update_entity`.
Consequence: only the routes and their four body models can move. Moving
`_location_geometry_dict`/`_location_doors_rows` as well would make
`entities.py` import the new module while the new module imports
`entities.py` -- a module-level cycle, which `import_cycle.py` fails. The
extraction is therefore a strict subset of what F1 named; see drafting
decision 1.

### R-20 — gathering rows are outside the canon-write policy
Opened: `tooling/verify/canon_write_policy.txt`, `[CANON_TABLES]` block and
line 145. [M]
Finding: the canon table list names 38 tables and includes neither `gathering`
nor `gathering_member`; line 145 states, of another pair of tables, "not
durable world canon -- same posture as gathering/conversation".
Consequence: briefs C and D add no `[ALLOWED_SITES]` entry and trip no
`single_canon_write.py` rule. The writes they add are ephemeral-state writes.

### R-21 — what the ticket artifact itself must satisfy
Opened: `tooling/verify/checks/pipeline_state.py:52-115`,
`tooling/verify/run.py:10-23`. [M]
Finding: required front-matter fields are `id, title, type, status, created,
model_lane, danger_class, blast_radius, brief_ids, schema_version_touched,
retry_count`; `status` must be in the nine-value enum; `retry_count` an
integer 0-2; exactly one `### Machine` header and exactly one `### Live`
header, in that order; and for a status in `{brief, exec, verify, live-gate,
done}`, at least one arrow, every arrow resolving to an existing file under
`tooling/verify/checks/`. `LINK.search` takes the first arrow per line only.
Consequence: TICKET-0089 ships at status `brief` linking only checks that
exist today. The arrow for the check created by brief G is added by brief G's
own commit, never before.

### R-22 — the CLAUDE.md clauses this lot touches, verbatim, and its budget
Opened: `CLAUDE.md:134-139`, `:269-274`;
`tooling/verify/checks/claude_md_contract.py:69-71`; `wc` of CLAUDE.md. [M]
Finding, verbatim:
```
- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. Per-NPC, NOT per-location (multiple open gatherings in one
  location are legal). Defended on every join/migrate path.
- **Dissolve-before-create lives in the caller** (`enter_location`), never
  inside `generate_gatherings`.
```
and
```
- **Creator-CRUD edits that change a character's `current_location_id`, or
  set an entity's `status` to a non-active value, MUST close that entity's
  open `gathering_member` rows via `close_open_memberships`** (gatherings
  are not canon -- no `_apply_mutation`, no `change_history`). Roster and
  co-present reads gate on `entity.status='active' AND
  vital_status='alive'` in addition to `gathering_member.left_at IS NULL`.
```
Budgets: total file <= 38 000 characters (currently 34 752), no line over 100
characters, and the Invariants section must contain zero `TICKET-\d` or
`BRIEF-\d` matches.
Consequence: brief G extends the third clause and adds one; it has roughly
3 200 characters of headroom and may cite no ticket or brief id in that
section.

### R-23 — the decision registry's header contract
Opened: `tooling/verify/checks/decisions_index.py:15-17`,
`tooling/glue/gen_decisions_index.py:7-9`, `:46-49`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:15438-15501`. [M]
Finding: a header added after the baseline must match
`^## .+ \(BRIEF-\d{4}(-[a-z])?(, BRIEF-\d{4}(-[a-z])?)*, (schema v\d+\.\d+|no schema change)\)$`,
and `tooling/standards/DECISIONS_INDEX.md` must equal a fresh
`python tooling/glue/gen_decisions_index.py` regeneration. The most recent
entries follow `## TITLE IN CAPS (BRIEF-0087-d, no schema change)`.
Consequence: brief G appends one entry in that exact shape and regenerates
the index in the same commit.

### R-24 — what the new check must be
Opened: `tooling/verify/checks/corpus_gate.py:1-40`, `:62`;
`tooling/verify/checks/world_tick.py:470-497`. [M]
Finding: `corpus_gate` discovers every `*.py` in the checks directory except
itself and runs each as a subprocess; a check that cannot import is an
ENVIRONMENT failure, never a skip; `REQUIRED_TOOLS = ("fastapi", "httpx",
"pyflakes", "sqlalchemy", "sqlmodel")`. `world_tick.py`'s precedent for this
exact class of assertion parses the module with `ast`, finds the function by
name, collects `{node.func.id for node in ast.walk(func) if isinstance(node,
ast.Call) and isinstance(node.func, ast.Name)}` and fails on a missing call
name.
Consequence: brief G's check is stdlib-`ast` only, imports no application
module, and follows the `FAILURES`/`fail`/`main` idiom of its siblings.

### R-25 — `analyze_window` is a no-op without a model call when nothing is new
Opened: `analyzer.py:240-269`. [M]
Finding: it loads the conversation, calls `_window_unanalyzed_rows`, and
returns `[]` before any model call, marker change or commit when that is
empty. Its docstring states it explicitly.
Consequence: G1's single behaviour costs nothing on the common creator path;
the rare cost is a genuine unanalysed window, which is the case where the
analysis is wanted.

### R-26 — `_perform_travel` moves the player and leaves NPC gatherings alone
Opened: `cockpit/play_stream.py:383-461`. [M]
Finding: it closes the player's open conversations (running `analyze_window`
first), closes the player's own open `gathering_member` rows, and writes
`char.current_location_id`. Its comment at `:443-445` states that NPC members
are untouched and that `enter_location`'s dissolve-before-create handles the
location when it is next entered.
Consequence: the player's own departure is not a source of empty gatherings
by itself; it becomes one in combination with R-06 at the location left
behind. Brief C covers that case too, since the player's closed membership
can be the last active one.

### R-27 — production state, measured
Source: seven read-only SELECTs run by Claude Code on
`~/.world_engine/world_engine.db`, reported 2026-09-18. [P]
Finding: `La Reine des ombres` (`e47ac015...`) and `Lily` (npc,
`2d4b8259...`) are `active`/`alive` with
`current_location_id = 4db135ba...` whose entity name is `"Chambre "` with a
trailing space; the open session is `16bd5153...` (number 1, started
2026-09-16 19:50:20); neither NPC holds a `gathering_member` row with
`left_at IS NULL`; gathering `81d51618...` ("Reine des ombres en solitude",
location `"Chambre "`) is `open` with zero active members, as is
`30728665...` ("Solitaires dans l'ombre", location "Chambre noir"), among
seven open-and-empty gatherings; six live NPCs carry a NULL
`current_location_id`; zero `proposed_mutation` rows with
`mutation_type = 'npc_move'` name either NPC.
Consequence: the defect in production is R-03 plus R-06, not R-10. The lot
repairs no row: brief A makes the two shells dissolve on the next entry.

### R-28 — the frontend build is committed and hash-checked
Opened: `tooling/verify/checks/frontend_build_fresh.py:1-40`. [M]
Finding: four vacuous-proof assertions -- sources exist; output exists under
`src/world_engine/cockpit/static/` with at least one `*.js` and an
`index.html`; `.build-manifest.json` parses and carries a 64-hex
`source_hash`; and the recomputed source hash equals the manifest's.
Consequence: brief F is not done when `Field.svelte` changes; it is done when
the rebuilt output and manifest are committed with it.

### R-29 — joining an empty gathering is accepted
Opened: `cockpit/routes/scene.py:313-362`, `cockpit/play.py:826-835`. [M]
Finding: `scene_join` with `target_gathering_id` validates that the gathering
exists, that `status == 'open'`, and that its `location_id`/`session_id`
match the player's; it never inspects the roster. `_gathering_brief` returns
`{"id", "label", "members": [...]}` with an empty `members` list for a
gathering with no active member.
Consequence: this is the surface Nia sees -- a joinable group with a label and
no names. No brief changes `scene_join`: once A, C and D hold, an empty open
gathering no longer exists to be joined.

### R-30 — `_get_or_open_session` creates a session when none is open
Opened: `cockpit/play.py:733-756`. [M]
Finding: it returns the world's open session or creates and commits one.
Consequence: brief D must NOT call it. A creator-side sheet save may not open
a play session; `C-03` therefore performs its own read-only session lookup and
no-ops when there is none.

---

## Contract sheet

Family contract, written before its three members and re-read after the last
one (gate (d)): **the gathering lifecycle has three write verbs, all declared
in `src/world_engine/gathering.py`, all operating on ephemeral state, none of
them a canon write (R-20).** `close_open_memberships` ends memberships,
`dissolve_emptied` ends gatherings, `attach_on_arrival` begins one. Each takes
a `Session` and writes through the ORM; each states explicitly whether it
commits; none of them raises on a missing row, because every caller is a
creator-facing or play-facing path where a failed edit must not 500.

### C-01 — `_live_gatherings`
Produced by: BRIEF-0089-a   Consumed by: BRIEF-0089-a, BRIEF-0089-g
Declared in: `src/world_engine/cockpit/routes/scene.py`, module level.
Signature: `_live_gatherings(location_id: str, session_id: str, db: Session) -> list[Gathering]`
Return shape: the subset of `_open_gatherings(location_id, session_id, db)`
for which `_active_members(g.id, db)` is non-empty, in the order
`_open_gatherings` returned them.
Error and empty cases: never raises. Returns `[]` when there are no open
gatherings, and `[]` when every open gathering has zero active members. It
does not write, and it does not dissolve anything.

### C-02 — `dissolve_emptied`
Produced by: BRIEF-0089-c   Consumed by: BRIEF-0089-c, BRIEF-0089-d, BRIEF-0089-g
Declared in: `src/world_engine/gathering.py`.
Signature: `dissolve_emptied(gathering_ids: Iterable[str], db: Session, model: str = ollama_client.DEFAULT_MODEL, host: str = ollama_client.OLLAMA_HOST) -> list[str]`
Behaviour: for each distinct id, if the gathering exists, has
`status == 'open'`, and has no `GatheringMember` row with `left_at IS NULL`:
run `analyze_window` on each of its open conversations, each call wrapped in
`try/except (Exception, SystemExit)` with `_log.exception`; then set
`status='dissolved'` and `dissolved_at=now`. Commits once at the end.
Return shape: the list of ids actually dissolved, in input order.
Error and empty cases: an empty or exhausted iterable commits and returns
`[]`. An unknown id, a dissolved gathering and a gathering still holding an
active member are each skipped without error. Never raises.

### C-03 — `attach_on_arrival`
Produced by: BRIEF-0089-d   Consumed by: BRIEF-0089-d, BRIEF-0089-g
Declared in: `src/world_engine/gathering.py`.
Signature: `attach_on_arrival(entity_id: str, location_id: Optional[str], db: Session) -> Optional[str]`
Behaviour, in order, returning `None` at the first miss:
1. `location_id` is not `None`.
2. `db.get(Entity, entity_id)` exists and has `status == 'active'`.
3. `db.get(Character, entity_id)` exists, `character_type == 'npc'`,
   `vital_status == 'alive'`.
4. `db.get(Entity, location_id)` exists and is a `location`.
5. A play-session row (`models.Session`, imported into `gathering.py` as
   `Session as PlaySession` because `sqlmodel.Session` already owns the bare
   name there) for that location's `world_id` with `status == 'open'` exists
   -- found by a read-only `select`, never by `_get_or_open_session` (R-30).
6. At least one `Gathering` with that `session_id`, that `location_id` and
   `status == 'open'` exists.
Then: insert one `Gathering` with `world_id` taken from the LOCATION entity
(matching `generate_gatherings:237`, which reads `location.world_id`),
`session_id`, `location_id`, `label = f"{entity.name}, seul\u00b7e"` (the exact
shape of `_solo_partition`, `gathering.py:178`), `status='open'`,
`created_at=now`; and one `GatheringMember` (`gathering_id`, `entity_id`,
`joined_at=now`, `left_at=None`); then return the new gathering id.
Return shape: the new gathering id, or `None`.
Error and empty cases: does NOT commit -- the caller owns the transaction,
same convention as `close_open_memberships` (R-06). Never raises. Never opens
a session. Never joins an existing gathering: the label shape is
`_solo_partition`'s (`gathering.py:175-180`), and the MJ partition remains the
only authority on who clusters with whom.

### C-04 — `_build_extension_kwargs`, extended
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Declared in: `src/world_engine/cockpit/crud/entities.py`.
Signature: `_build_extension_kwargs(db: DbSession, entity_type: str, data: dict, *, present_only: bool = False) -> dict`
Behaviour: unchanged when `present_only` is `False` -- one entry per registry
field, absent keys coerced from `None`. When `present_only` is `True`, only
fields whose name is a key of `data` appear in the result; the coercion of
each present field is unchanged, so an explicit `""` still clears an
`entity_ref` and an explicit `null` still clears a text field.
Return shape: `{field_name: coerced_value}`.
Error and empty cases: with `present_only=True` and no registry field present
in `data`, returns `{}`. The `item`/`equipped` guard at `:362-363` applies
only to the keys present in the result.

### C-05 — `_build_runtime_ext_kwargs`, extended
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Declared in: `src/world_engine/cockpit/crud/entity_runtime.py`.
Signature: `_build_runtime_ext_kwargs(db: DbSession, fields: list[dict], data: dict, *, present_only: bool = False) -> dict`
Behaviour: identical rule to `C-04`, over the runtime spec's field list.
Error and empty cases: returns `{}` when nothing is present. `C-06` is what
makes an empty result safe.

### C-06 — `_update_runtime_ext_row`, guarded
Produced by: BRIEF-0089-e   Consumed by: BRIEF-0089-e
Declared in: `src/world_engine/cockpit/crud/entity_runtime.py`.
Signature: unchanged --
`_update_runtime_ext_row(db: DbSession, runtime_spec: dict, entity_id: str, ext_kwargs: dict) -> None`
Behaviour: returns immediately without executing a statement when
`ext_kwargs` is empty; otherwise unchanged.
Error and empty cases: this is the whole point -- a SQLAlchemy `update()` with
no `values()` is an error, and `C-05` can now legitimately produce `{}`.

### C-07 — `gathering_lifecycle.py`
Produced by: BRIEF-0089-g   Consumed by: TICKET-0089 acceptance criteria
Declared in: `tooling/verify/checks/gathering_lifecycle.py`.
Contract: stdlib `ast` only, imports no application module, `FAILURES`/`fail`/
`main` idiom, vacuous-proof (an empty collection is a FAILURE). Asserts, each
failing independently:
1. `routes/scene.py` declares `_live_gatherings`, and `enter_scene`'s body
   calls it and does not call `_open_gatherings`.
2. `_live_gatherings`'s own body calls `_active_members`, so the roster
   predicate is not re-expressed (R-05).
3. `gathering.py` declares `dissolve_emptied` and `attach_on_arrival`.
4. `migrate_npc` calls `dissolve_emptied` and contains no
   `status = "dissolved"` assignment of its own.
5. `crud/entities.py`'s `update_entity` calls `close_open_memberships`,
   `dissolve_emptied` and `attach_on_arrival`.
6. `attach_on_arrival`'s body does not call `_get_or_open_session` (R-30).
PASS line names the counts it collected.

---

## Gate output

### (a) Property trace

| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| presence is read from gathering membership | R-01 | `cockpit/spatial_presence.py`, `cockpit/play.py`, `cockpit/play_initiative.py` |
| `_present_npcs` is the only location-to-roster reader | R-02 | `gathering.py` |
| the entry guard is `if not open_g` and `enter_location` has one live caller | R-03 | `cockpit/routes/scene.py`, `gathering.py` |
| `_open_gatherings` ignores membership | R-04 | `cockpit/play.py` |
| `_active_members` is the roster authority and its filters | R-05 | `cockpit/play.py` |
| `close_open_memberships` dissolves nothing and does not commit | R-06 | `gathering.py` |
| `migrate_npc`'s auto-dissolve runs post-commit and analyses first | R-07 | `gathering.py` |
| `enter_location` dissolves without closing member rows | R-08 | `gathering.py` |
| the creator CRUD closes memberships at three sites, with the equality guard | R-09 | `cockpit/crud/entities.py` |
| an absent extension key writes NULL | R-10 | `cockpit/crud/entities.py`, `cockpit/crud/_shared.py` |
| the sheet sends the full field set or aborts | R-11 | `Sheet.svelte`, `fields.js` |
| the `entity_ref` select has no option for an unlisted current value | R-12 | `Field.svelte` |
| `crud/entities.py` is at 1000 lines and no baseline exists | R-13 | `module_budget.py`, `tooling/verify/baselines/` |
| function lengths of the four edited functions | R-14 | `function_length.py` plus `ast` measurement |
| `play.py` is at 997 lines | R-15 | `ast` measurement |
| `json_ui_boundary` pins the registry to `entities.py` | R-16 | `json_ui_boundary.py` |
| the route table holds 182 pairs including the two moved routes | R-17 | executed against `app.openapi()` |
| `__init__.py` does not re-export the two routes; import is registration | R-18 | `crud/__init__.py`, `crud/_router.py` |
| what the extracted routes depend on, and why the readers stay | R-19 | `cockpit/crud/entities.py` |
| gathering tables are not canon tables | R-20 | `canon_write_policy.txt` |
| ticket front-matter and arrow rules | R-21 | `pipeline_state.py`, `run.py` |
| the CLAUDE.md clauses and the character budget | R-22 | `CLAUDE.md`, `claude_md_contract.py` |
| the decision-registry header pattern and regeneration | R-23 | `decisions_index.py`, `gen_decisions_index.py` |
| corpus_gate discovery rules and the AST assertion precedent | R-24 | `corpus_gate.py`, `world_tick.py` |
| `analyze_window` is a no-op without a model call when nothing is new | R-25 | `analyzer.py` |
| `_perform_travel` leaves NPC gatherings alone | R-26 | `cockpit/play_stream.py` |
| production state of the two NPCs and the shells | R-27 | production DB, read-only |
| the build freshness contract | R-28 | `frontend_build_fresh.py` |
| joining an empty gathering is accepted | R-29 | `cockpit/routes/scene.py`, `cockpit/play.py` |
| `_get_or_open_session` creates a session | R-30 | `cockpit/play.py` |

No brief asserts a property absent from this table.

### (b) Case tables

**b1 -- the entry guard (`C-01`, brief A).** Rows are the composition of the
open gatherings at the player's location for the open session.

| open gatherings at loc+session | any with an active member | `_live_gatherings` | `enter_location` runs | outcome |
|---|---|---|---|---|
| none | n/a | `[]` | yes | first entry: partition generated from `current_location_id` |
| one or more, all empty | no | `[]` | yes | shells dissolved by `enter_location`, partition regenerated -- the production repair |
| one or more, at least one non-empty | yes | non-empty | no | re-render or F5: partition preserved, invariant C1 held |
| mixed empty and non-empty | yes | the non-empty subset | no | preserved; the empty ones are dissolved by brief C at the moment they are emptied, not here |

Every outcome is reachable and correct. Row 3 is the one that must not
change: it is what stops a refresh from reshuffling a live scene.

**b2 -- `attach_on_arrival` (`C-03`, brief D).** Rows are the five ordered
conditions; the first miss returns `None`.

| case | result |
|---|---|
| destination is NULL (field cleared) | `None` -- nothing to attach to |
| entity is not active, or not an alive NPC (player, dead, inactive) | `None` |
| world has no open session | `None` -- a sheet save never opens one (R-30) |
| open session, but no open gathering at the destination | `None` -- the location is cold; the normal entry path will generate |
| open session and at least one open gathering at the destination | new solo gathering, id returned |

**b3 -- `_build_extension_kwargs(present_only=True)` (`C-04`, brief E).**

| key in `data` | value | result |
|---|---|---|
| absent | -- | field omitted; stored column untouched |
| present | `""` | coerced by the field's kind; `entity_ref` clears to NULL |
| present | `null` | same as today -- text clears, bool takes its default |
| present | a value | coerced and written as today |
| no registry field present at all | -- | `{}`; static branch sets nothing, runtime branch short-circuits (`C-06`) |

### (c) Enumerations

**E1 -- every caller of `enter_location`** (supports R-03):
```
$ grep -rn "enter_location(" --include=*.py src/
cockpit/routes/scene.py:139:        _enter_location(location_id, sess.id, db)
gathering.py:359:def enter_location(
```
Two hits, one of them the definition. `routes/mutations.py:37` imports it;
`grep -rn "_enter_location(\|_migrate_npc(" src/world_engine/cockpit/routes/mutations.py`
returns nothing.

**E2 -- every check naming the two routes brief B moves** (supports R-19, and
gate (e) for brief B):
```
$ grep -rln "set_location_geometry\|set_location_doors" tooling/verify/checks/
tooling/verify/checks/single_canon_write.py
$ grep -n "set_location_geometry\|set_location_doors" tooling/verify/checks/single_canon_write.py
71:`set_location_subculture`, `create_world`, `set_location_geometry`,
72:`set_location_doors`), never reachable from any AI or play path. These
```
Both hits are docstring prose naming the functions, not a path binding. No
check resolves either route by file path.

**E3 -- every baseline file on disk** (supports R-13, R-14):
```
$ ls tooling/verify/baselines/
decisions_headers.baseline
graph_impls.baseline
graph_impls.retired
legacy_calls.baseline
legacy_mounts.baseline
```
Neither `module_budget.json` nor `function_length.json` exists, so both caps
are absolute.

**E4 -- the canon table list** (supports R-20):
```
[CANON_TABLES]
world entity character location faction faction_membership faction_role relation
knowledge ledger item skill skill_definition skill_system discoverable_detail
event artifact npc_goal agenda agenda_step goal_agenda_link
npc_price location_subculture world_law obstacle obstacle_vertex door
location_type_catalog entity_type entity_type_history conversation_window_config
npc_schedule agenda_step_requirement fact fact_participant fact_default
```
`gathering` and `gathering_member` are absent. The single other occurrence of
the word in the file is line 145, a comment reading "not durable world canon
-- same posture as gathering/conversation".

**E5 -- what `crud/__init__.py` imports from `.entities`** (supports R-18):
```
from .entities import ( ENTITY_BASE_FIELDS, ENTITY_STATUSES,
ENTITY_TYPE_REGISTRY, EntityWriteBody, LocationSubcultureBody, NpcPricesBody,
_apply_base_fields, _build_extension_kwargs, _coerce_field,
_create_entity_core, _entity_dict, _entity_summary, _extension_dict,
_get_entity, _iso, _link_entity_creation, _location_geometry_dict,
_location_subculture_rows, _npc_prices_dict, _player_character_id,
_validate_entity_ref, _world_id, create_entity, delete_entity, get_entity,
get_entity_types, list_entities, list_entity_items, set_location_subculture,
set_npc_prices, update_entity, )
```
31 names; neither route brief B moves is among them.

**E6 -- the route table as a set** (supports R-17):
```
$ WORLD_ENGINE_ENV=test PYTHONPATH=src python -c "from world_engine.cockpit.app \
import app; spec=app.openapi()['paths']; rows=sorted((p,m) for p,ops in \
spec.items() for m in ops); print(len(rows))"
182
```
with `('/api/entities/{entity_id}/doors', 'put')` and
`('/api/entities/{entity_id}/geometry', 'put')` present.

**E7 -- the reproduction** (supports the whole diagnosis), throwaway carrier,
`WORLD_ENGINE_DATABASE_URL` pointed at a scratch file: [E]
- entry with two NPCs present: two solo gatherings, one active member each;
- `PUT /api/entities/{npc}` moving one out: its gathering stays `open` with
  `active_members=[]`;
- moving it back, `current_location_id` correct, then
  `POST /api/scene/enter`: the response still reads
  `[('Alma, seul\u00b7e', []), ('Boran, seul\u00b7e', ['Boran'])]` -- the NPC never
  returns;
- with `_open_gatherings` replaced by the `C-01` predicate at the guard and
  nothing else changed, the same call returns
  `[('Alma, seul\u00b7e', ['Alma']), ('Boran, seul\u00b7e', ['Boran'])]` and the two
  stale rows read `dissolved`;
- a `PUT` whose extension omits `current_location_id` returns 200 and leaves
  the column `None`.

### (d) Un-rederived contract

The gathering-lifecycle family contract was written before `C-02` and `C-03`
and re-read after `C-03` was added. The re-read produced two corrections that
are now in the contracts: `dissolve_emptied` commits and `attach_on_arrival`
does not (the family rule is that each verb states it, and the two differ
because one runs after the caller's commit and the other before it), and
`attach_on_arrival` returns an id rather than a `Gathering` so that no caller
holds an ORM object across the caller's own commit. The `C-04`/`C-05`/`C-06`
trio is the second family -- the same `present_only` rule stated once and
applied to both field builders, with `C-06` as the consequence that makes the
empty case legal.

### (e) Unsatisfiable check

| gate | proposed or merely passed | module that satisfies it | what it needs that the check forbids |
|---|---|---|---|
| `gathering_lifecycle.py` (`C-07`) | proposed by brief G | the code of briefs A, C and D | nothing: every assertion names a symbol those briefs declare, and the check reads source with `ast` only, so it forbids no runtime behaviour |
| `module_budget.py` on `crud/entities.py` | merely passed | brief B -- the extraction is the module that satisfies it | briefs D and E each need lines in a file with zero free ones; B frees them, which is why D and E depend on B |
| `function_length.py` on `enter_scene` | merely passed | brief A, by replacing the predicate in place rather than adding a line (76 of 80 used) | nothing |
| `function_length.py` on `update_entity` | merely passed | briefs D and E share the 9 free lines: D takes at most 4, E at most 3 | nothing; if either overruns, that brief extracts its branch into a helper in the same file rather than growing the function |
| `import_cycle.py` | merely passed | brief B, by moving only the routes and their body models (R-19) | moving the two readers as well would create the cycle; that is why the extraction is a strict subset of F1 |
| `json_ui_boundary.py` | merely passed | brief B, by leaving the registry and its two marker comments untouched (R-16) | nothing |
| `undefined_names.py` | merely passed | brief B, by importing into `entity_geometry.py` every symbol listed in R-19 | nothing |
| `frontend_build_fresh.py` and `static_asset_freshness.py` | merely passed | brief F, by committing the rebuilt output and manifest (R-28) | nothing |
| `claude_md_contract.py` | merely passed | brief G, within the ~3 200 free characters, no `TICKET-\d`/`BRIEF-\d` in the Invariants section, no line over 100 characters (R-22) | nothing |
| `decisions_index.py` | merely passed | brief G, one header in the strict pattern plus a regeneration of the index (R-23) | nothing |
| `pipeline_state.py` | merely passed | TICKET-0089 itself, which links only checks that exist at deposit time; brief G adds the arrow for `gathering_lifecycle.py` in the commit that creates it (R-21) | a ticket at status `brief` may not name a check that does not exist yet |

## Drafting decisions flagged for Nia

1. **The F1 extraction is narrower than the decision named.** F1 named the
   geometry/doors readers as well as their routes. `_location_geometry_dict`
   and `_location_doors_rows` are consumed by `entities.py`'s own
   `get_entity`/`create_entity`/`update_entity`, while the routes consume
   `_entity_dict`/`_extension_dict`/`_location_subculture_rows` from
   `entities.py` (R-19). Moving the readers makes the two modules import each
   other, which `import_cycle.py` fails. Brief B therefore moves the two
   routes and their four Pydantic bodies only -- about 110 lines against the
   173 F1 named, which is ten times what briefs D and E need.
2. **`dissolve_emptied` is called by the callers, after their commit, not from
   inside `close_open_memberships`.** Folding it in would put an
   `analyze_window` call -- which commits -- inside the creator CRUD's open
   transaction, committing a half-applied sheet edit. The cost is that each
   close site gains a call; the benefit is that no path commits early.
3. **An arriving NPC always gets its own solo gathering.** Joining an existing
   group would be a narrative claim; the MJ partition at entry is the only
   authority for clustering. The label reuses `_solo_partition`'s shape so the
   two sources are indistinguishable to the reader.
4. **Brief A does not touch `scene_join`.** An empty gathering stays joinable
   in code; after A, C and D there is none to join. Hardening `scene_join`
   would be defence in depth against a state the lot removes.
5. **The six NULL-location NPCs and the untrimmed entity names are recorded in
   the ticket's carried-forward section, not fixed.** D1 for the first; the
   second touches every entity write path and deserves its own ticket.

## Amendments

(none)
