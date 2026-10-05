# LOT — TICKET-0104 "The Lore writing panel's default scopes pick their entity from the whole world"

## Objective and cut

In the Lore writing panel (« Écrire »), « Qui le sait par défaut » lets the
creator pick the entity of a `location` or `faction` scope among every
active entity of the world of that type, not only among the entities her
text named (A1). A `rencontre` scope picks among entities of any type
(A1'a). A world entity picked for a scope joins the draft as `existing`, by
the helper a knower already uses, so the commit path and its server-side
validation do not change.

The lot stops at the picker. It does not change what a `location` default
means (presence today; learning and keeping is TICKET-0105), what the model
may propose, the server, or the schema.

## Briefs in this lot

- **A — the world-wide scope picker** (no schema change):
  `frontend/src/lore/writePanel.svelte.js`, `WritePanel.svelte`, rebuilt
  `static/`; `lore_write.py` gains F2; one decision entry.

## Dependency graph

One brief; nothing to order.

## RECON

Opened on `main` at `83a796a` (merge of PR #134, `ticket/0103`), schema
v2.13. Then prototyped on a copy (branch `proto/0104`): the brief's diff
applied with `git apply --check` on a clean `main`, the frontend rebuilt,
and the full corpus ran green, 137/137, with `WORLD_ENGINE_ENV=test`.
The new functions were also compiled with `svelte/compiler`'s
`compileModule` and exercised under Node (results under Gate output (b)).
Findings tagged [M] were measured.

### R-01 — the scope list offers only the draft's entities [M]
Opened: `frontend/src/lore/writePanel.svelte.js:31` (`SCOPE_ENTITY_TYPE =
Object.freeze({ faction: 'faction', location: 'location' })`), `:125-128`
(`liveRefs`), `:130-132` (`scopeRefs`); `frontend/src/lore/
WritePanel.svelte:141-156` (the « Qui le sait par défaut » rows).
Finding: the entity select of a non-`world` scope lists
`scopeRefs(scope.scope_type)` = `liveRefs(SCOPE_ENTITY_TYPE[type])`: the
draft's entities whose decision is set and not `text`, of the scope's
type. A text that names no place offers no place. `rencontre` has no key,
so `liveRefs(undefined)` lists every live draft entity, of any type. The
scope type is bound with `bind:value`: switching it keeps a `scope_ref` of
the wrong type, which the server then refuses (R-04).
Consequence: the list must add the world's entities; a type switch must
clear a ref the new type refuses.

### R-02 — the knower picker already adds a world entity to the draft [M]
Opened: `frontend/src/lore/writePanel.svelte.js:134-149` (`addKnower`),
`:106-108` (`worldEntity`), `:66-70` (`loadWorldEntities`), `:86-87`
(`draftNow` awaits `loadWorldEntities()` before the draft request);
`WritePanel.svelte:169-174` (the knower select lists
`writeState.entities` filtered to `character`).
Finding: `addKnower` finds the draft entity `existing` with that
`entity_id`, or pushes one (`ref: k${draft.entities.length + 1}`, `status:
'matched'`, `decision`/`action: 'existing'`, `entity_id`, `name`, `type`
from the world entity). `writeState.entities` is loaded before any draft
is shown.
Consequence: the scope picker reuses that code, extracted as
`existingRef(entityId)`; `addKnower` calls it unchanged in behaviour.

### R-03 — the world's entity list [M]
Opened: `src/world_engine/cockpit/crud/entities.py:509-518`
(`list_entities`); `writePanel.svelte.js:68-69`.
Finding: `GET /api/entities` returns every entity of the active world, all
types (runtime types included), ordered by type then name, each with `id`,
`name`, `type`, `status`; the panel keeps `status === 'active'`. Nothing
in the row says whether a place is a zone.
Consequence: no new request path; zones are not marked in the list (ticket,
Carried forward).

### R-04 — the server already validates every scope ref and type [M]
Opened: `src/world_engine/lore_write_apply.py:39-44` (`SCOPE_TYPES`,
`_SCOPE_ENTITY_TYPE` with `"rencontre": None`), `:72-94`
(`_validate_entities`: an `existing` item needs an active entity of the
proposal's world), `:96-101` (`_entity_ref`: the ref is in the proposal,
and of type `want` when `want` is not None), `:104-118`
(`_validate_scopes`); `src/world_engine/lore_write_draft.py:186-197`
(`_scopes`: a model-proposed scope is kept only if its ref is a draft
entity).
Finding: an `existing` entity added by the panel is validated like any
other; a `location`/`faction` scope must point at a ref of that type; a
`rencontre` scope at any ref. The model can propose scopes only on named
entities.
Consequence: no server change; the model side is out of scope.

### R-05 — `rencontre` is not limited to characters [M]
Opened: `src/world_engine/writes/facets.py:60-70` (`_preset_scope`:
`preset == "rencontre"` → `ScopeChoice("rencontre", entity.id)` whatever
`entity.type`), `src/world_engine/writes/relations.py:222-230`
(`_on_relation_born`: a social relation records an encounter between
`entity_a_id` and `entity_b_id`, types unchecked),
`src/world_engine/encounters.py:118-125` (`acquaintances`: every entity
paired in `rencontre`).
Finding: the creator-side preset already writes `rencontre` scopes on
places, factions and objects (the appellation preset is `rencontre` since
TICKET-0092, N14b), and the registry can pair a character with a
non-character.
Consequence: A1'a — the panel offers every type for `rencontre`;
`SCOPE_ENTITY_TYPE` keeps exactly its two keys.

### R-06 — what a `location` default means today [M]
Opened: `src/world_engine/knowledge_resolve.py:18-20` (tier 4), `:72-87`
(`_location_ancestor_chain`), `:174-184`.
Finding: a `location` default reaches an entity whose current location is
the scope's place or a descendant of it; it is not kept after leaving.
Consequence: context for the ticket only; nothing here changes it
(TICKET-0105).

### R-07 — the checks that read the panel [M]
Opened: `tooling/verify/checks/lore_write.py:624-640` (`check_f1`: F1b the
exact set of `'/api/...'` paths in `writePanel.svelte.js`; F1c
`WritePanel.svelte` has no `entity_id` once `entity.entity_id`,
`c.entity_id` and `entity_id)` are removed), `:665-691` (`main`, the PASS
line); `tooling/verify/checks/lore_usage.py` `check_u11` (static: the
attempt id in `blank()` and the three POSTs; the built bundle carries
`attempt_id`); `tooling/verify/checks/frontend_build_fresh.py:14-17`
(manifest hash of the current `frontend/` sources);
`tooling/verify/checks/effect_self_write.py` (no `$effect` is touched).
Finding: the new markup must name no `entity_id`; the new code may call no
new path; the bundle must be rebuilt.
Consequence: the option values are built in `writePanel.svelte.js`
(`ref:<ref>` / `id:<uuid>`), never in the markup; F2 joins `lore_write.py`
beside F1, the same check that governs the panel.

### R-08 — what the commit sends [M]
Opened: `frontend/src/lore/writePanel.svelte.js:159-175` (`blockers`: a
non-`world` scope without `scope_ref` blocks the commit), `:178-207`
(`toProposal`: an `existing` entity is sent as `{ref, action: 'existing',
entity_id}`; a non-`world` scope is sent as `{...d}` unless its ref is a
dropped « en texte » entity).
Finding: a scope whose `scope_ref` is `undefined` is shown as a blocker
and never sent; a ref added by `existingRef` is sent as an `existing`
entity.
Consequence: clearing `scope_ref` to `undefined` on a type switch is safe.

### R-09 — the decision registry [M]
Opened: `CLAUDE.md`, « Numbering & decisions governance »;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last entry: `THE LORE USAGE
JOURNAL HAS ONE READER (TICKET-0103) ...`, then the `---` /
`*Co-built with Claude, June 2026.*` footer);
`tooling/glue/gen_decisions_index.py`; `tooling/verify/checks/
decisions_index.py`.
Finding: a new entry goes above the footer with the header form `## TITLE
(BRIEF-NNNN[-x], no schema change)`; the index is regenerated, never
edited.
Consequence: the brief's diff carries the entry; the index is regenerated.

## Contract sheet

No interface crosses briefs (one brief). The names F2 reads —
`existingRef`, `scopeOptions`, `scopeValue`, `pickScope`, `setScopeType`,
`SCOPE_ENTITY_TYPE` — are fixed verbatim in the brief's diff.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| the scope list = live draft refs of the scope's type; `rencontre` unkeyed | R-01 | `writePanel.svelte.js` |
| the scope type is `bind:value`, a ref survives a type switch | R-01 | `WritePanel.svelte` |
| `addKnower` pushes an `existing` draft entity with a `k<n>` ref | R-02 | `writePanel.svelte.js` |
| world entities are loaded before a draft is shown | R-02 | `writePanel.svelte.js` (`draftNow`) |
| `/api/entities` = active world, all types, no zone flag | R-03 | `cockpit/crud/entities.py` |
| the server validates `existing` items, scope refs and their types; `rencontre` any type | R-04 | `lore_write_apply.py` |
| the model proposes scopes on draft refs only | R-04 | `lore_write_draft.py` |
| the `rencontre` preset takes any entity type | R-05 | `writes/facets.py` |
| a social relation records an encounter, types unchecked | R-05 | `writes/relations.py` |
| a `location` default is presence over the ancestor chain | R-06 | `knowledge_resolve.py` |
| F1b path set; F1c no `entity_id` in the markup | R-07 | `lore_write.py` (implementation `check_f1`) |
| U11c bundle carries `attempt_id`; build hash | R-07 | `lore_usage.py` (implementation `check_u11`), `frontend_build_fresh.py` |
| a scope with no ref blocks; an `existing` entity is sent with its id | R-08 | `writePanel.svelte.js` (`blockers`, `toProposal`) |
| decision header form; index generated | R-09 | `CLAUDE.md`, `decisions_index.py` |

Presuppositions: the brief names `addKnower` (R-02) as the code it
extracts, with its file and lines; no « follow the existing pattern ».

### (b) Case tables

**What the entity select offers, by scope type** (draft entities first,
in draft order, then world entities by name, French collation):

| Scope type | Draft entities offered (`ref:`) | World entities offered (`id:`) |
|---|---|---|
| `world` | no select | no select |
| `location` | live, type `location` (`existing` or `create`) | active, type `location`, not already held as `existing` |
| `faction` | live, type `faction` | active, type `faction`, not already held |
| `rencontre` | live, any type | active, any type, not already held |

« Live » = decision set and not `text` (R-01). An entity kept « en texte »
is offered in neither column.

**Picking and switching:**

| Action | Result |
|---|---|
| pick `ref:<r>` | `scope_ref = r` |
| pick `id:<u>` | `existingRef(u)`: the held `existing` ref, or a new `k<n>` entity; `scope_ref` = that ref |
| pick « — choisir — » | `scope_ref = undefined` (commit blocked, R-08) |
| switch to `world` | `scope_ref = undefined` |
| switch to `location`/`faction`, ref of another type or none | `scope_ref = undefined` |
| switch to `location`/`faction`, ref of that type | kept |
| switch to `rencontre`, ref set | kept (any type) |
| add a knower already picked for a scope (or the reverse) | same ref, one draft entity |

Prototype run under Node (`compileModule`), world = Taverne and Secte du
Phoenix (places), Gardes (faction), Millys (character); draft = Taverne
`existing` (`e1`), Cave `create` place (`e2`), vimm « en texte » (`e3`):

```
location : ref:e1 ref:e2 id:Z1
faction  : id:F1
rencontre: ref:e1 ref:e2 id:F1 id:C1 id:Z1
picked   : k4 ref:k4 existing Z1
location2: ref:e1 ref:e2 ref:k4
to faction clears: undefined
to rencontre keeps: e1
knower reuses ref: k4 4
```

Every row of both tables is reached except « pick « — choisir — » », which
is the one-line `else` of `pickScope`.

### (c) Enumerations

```
--- E1 users of scopeRefs / addKnower / SCOPE_ENTITY_TYPE outside the two panel files
$ grep -rn "scopeRefs\|addKnower\|SCOPE_ENTITY_TYPE" frontend/src tooling src \
    --include=*.js --include=*.svelte --include=*.py \
  | grep -v "^frontend/src/lore/writePanel.svelte.js\|^frontend/src/lore/WritePanel.svelte"
src/world_engine/lore_write_apply.py:42:_SCOPE_ENTITY_TYPE: dict[str, Optional[str]] = {
src/world_engine/lore_write_apply.py:114:            _entity_ref(refs, scope.get("scope_ref"), where, _SCOPE_ENTITY_TYPE[scope_type])
src/world_engine/cockpit/crud/knowledge.py:114:_FACT_DEFAULT_SCOPE_ENTITY_TYPE = {"faction": "faction", "location": "location"}
src/world_engine/cockpit/crud/knowledge.py:295:        expected_type = _FACT_DEFAULT_SCOPE_ENTITY_TYPE[body.scope_type]
```
Only server-side homonyms: `scopeRefs` and `addKnower` have no consumer
outside `writePanel.svelte.js` / `WritePanel.svelte`, so removing
`scopeRefs` breaks nothing.

```
--- E2 rencontre preset (writes/facets.py:60-70)
def _preset_scope(preset: str, entity: Entity) -> ScopeChoice:
    ...
    if preset == "location":
        return ScopeChoice("location", entity.id) if entity.type == "location" else ScopeChoice("none")
    if preset == "rencontre":
        return ScopeChoice("rencontre", entity.id)
```

### (d) Family contracts

Not applicable: no family in this lot.

### (e) Gates and the modules that satisfy them

| Gate | Module that satisfies it | What it needs that the gate forbids |
|---|---|---|
| `lore_write.py` F2 (proposed) | `writePanel.svelte.js`, `WritePanel.svelte` as in the diff | nothing |
| `lore_write.py` F1b (passed) | `writePanel.svelte.js`: no new path (`/api/entities` already listed) | nothing |
| `lore_write.py` F1c (passed) | `WritePanel.svelte`: option values built in JS, no `entity_id` in the markup | nothing |
| `lore_usage.py` U11 (passed) | unchanged POSTs; rebuilt bundle | a rebuild |
| `frontend_build_fresh.py` (passed) | rebuilt `static/` | a rebuild |
| `decisions_index.py` (passed) | regenerated `DECISIONS_INDEX.md` | a regeneration |
| `effect_self_write.py` (passed) | no `$effect` touched | nothing |

Named mutations run on the prototype, each red then reverted:
- `scopeOptions` reads `[]` instead of `writeState.entities` → `F2a`.
- `SCOPE_ENTITY_TYPE` gains `rencontre: 'character'` → `F2b`.
- `addKnower` takes `worldEntity(entityId)?.id` instead of `existingRef(entityId)` → `F2c`.

## Amendments

(none)
