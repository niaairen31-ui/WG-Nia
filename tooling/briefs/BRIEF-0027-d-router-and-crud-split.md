<!-- slug: router-and-crud-split -->
# BRIEF-0027-d — Split `app.py` into domain routers and `crud.py` into domain modules

Ticket: TICKET-0027 | Danger: none (pure relocation, route contract
frozen) | Blast radius: large by surface, low by depth | Depends on:
BRIEF-0027-c merged; own branch `ticket/0027-d`

## Context

Post stage b/c, `cockpit/app.py` is ~5.1k lines / ~100 functions with 42
routes; `cockpit/crud.py` is 2 932 lines / 109 functions. R5 caps both via
baseline; this stage brings both to compliance. Route census by first path
segment (RECON, merged branch): conversations 10, worlds 5, scene 4,
mutations 4, regions 3, creations 2, prompts 2, characters 2, plus
singletons (entities, skill-definitions, agendas, events, npcs, travel,
world-tick, bootstrap, vendor, root).

## Scope IN

1. **Routers.** Create `src/world_engine/cockpit/routes/{play,mutations,
   creator,prompts}.py` using `APIRouter`, mounted from `app.py` with
   prefixes preserving every existing path verbatim. Domain mapping:
   - play -> conversations, scene, travel, world-tick (the `/say` thin
     orchestrator moves here, calling `play*.py`)
   - mutations -> mutations (dispatcher from stage c moves here)
   - creator -> worlds, regions, creations, characters, entities, npcs,
     skill-definitions, agendas, events, bootstrap
   - prompts -> prompts
   Root `/`, `/vendor/{filename}`, static mounts, app factory, middleware,
   startup wiring stay in `app.py`. Ambiguous singletons are assigned in
   the execution notes with one-line rationale.

2. **crud split.** Convert `crud.py` into a package
   `src/world_engine/cockpit/crud/` with domain modules (indicative, from
   the function-prefix census: `entities.py`, `factions.py`, `skills.py`,
   `prompts.py`, `relations.py`, `knowledge.py`, `agendas.py`,
   `events.py`, `goals.py`, `locations.py`, ...). `crud/__init__.py`
   re-exports the public names so every existing call site imports
   unchanged — zero call-site churn in this brief. The `__init__` is a
   re-export surface, not a catch-all: no logic lives in it (R6
   respected; the domain modules are the homes).

3. **Pure moves only.** No handler body edited, no signature changed, no
   dependency-injection rework, no logic change of any kind.

4. **Baseline maintenance — declared path-rekey exception.** Moved
   functions that are > 80 lines (e.g. `commit_region` 271,
   `_find_applied_duplicate` 256) keep their `function_length.json`
   entries with the `file` field updated to the new path, `lines`
   unchanged, entry count unchanged. This is a pure re-key on move, not a
   grow — declared here so the shrink-only rule is bent openly, once,
   with Nia's sign-off, rather than silently. `module_budget.json`:
   `app.py` and `crud.py` entries are *deleted* (both compliant after the
   split); every new module fits R5 caps with no baseline entry.

## Scope OUT

- Decomposing the moved > 80-line handlers (they stay baselined; owned by
  stage g's successor decision).
- `llm_parse.py` (stage e), logging (stage f).
- Any route rename, path change, response-shape change, or frontend edit
  (`index.html` calls the same URLs).

## Invariants to defend

- Route contract byte-frozen: same paths, methods, request/response
  models, SSE shapes. Machine proof: dump of
  `[(r.methods, r.path) for r in app.routes]` sorted, identical
  before/after.
- `single_canon_write.py` sanctioned sites re-keyed to `routes/mutations.py`
  paths if the dispatcher moves (same relocation-not-broadening rule as
  stage c); suite green.
- `page_contract.py` green (frontend untouched).
- `function_length.json` entry count unchanged (re-key only);
  `module_budget.json` strictly smaller (two entries removed).

## Done means

### Machine-checkable
- [ ] Route-table dump identical pre/post (sorted methods+paths).
- [ ] `harness_say_replay.py` replay PASS post-split (reuses stage b
      fixtures; the play route moved, behavior must not).
- [ ] `module_budget.py` green with `app.py` and `crud.py` entries gone;
      `app.py` <= 40 functions / <= 1000 lines unbaselined.
- [ ] `function_length.py` green after the declared re-key; full suite
      green.
- [ ] `grep -r "from world_engine.cockpit.crud import\|from .crud import"`
      call sites unchanged (re-export surface holds).

### Live gate (Nia)
- [ ] Cockpit full smoke: load a world, open a conversation, one `/say`
      round-trip, one mutation approval, one creator CRUD action, one
      prompt view — all through the new routers.

## Docs to update

- None (no schema, no doctrine change; pipeline state only).
