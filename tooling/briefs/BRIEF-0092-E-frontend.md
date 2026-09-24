# BRIEF 0092-E — "frontend: Lore link, near names, appellations"

Lot: LOT-0092-names.md (authoritative on conflict)
Depends on: D

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a
few lines is drift, not a STOP — note it and proceed; different content is
always a STOP.

- `frontend/src/lore/Lore.svelte:21` `let loreTab = $state('question');`;
  `:87-88` mounts `NamesPanel` only on the names tab.
- `frontend/src/lore/NamesPanel.svelte:15` `CATEGORY_LABEL` with three keys;
  `:17-20` an `$effect` calling `reloadForWorld()`.
- `frontend/src/lore/namesPanel.svelte.js:11` `CATEGORY_TYPE` with three
  keys; `loadEntities` `:29-35`; `optionsFor` `:52-61`; `bindMention`
  `:88-92`.
- `frontend/src/creation/FactsEditor.svelte:34-38` `TYPE_FAMILIES`;
  `:40-46` shows only `description` for other types.
- D's routes answer: `GET /api/lore/names/lookup`, `POST
  /api/lore/appellations`, `near` on `/api/lore/mentions` rows and on
  `/api/lore/ask|resolve` bodies.

## Facts carried

### R-16 — entity types and categories
Opened: `src/world_engine/models/canon.py:117-137, 482-560`;
`cockpit/crud/entities.py:123-200, 475-483, 636-650` [M];
`grep -rn '"artifact"' src` [M].
Finding: `entity.type` is free text with no CHECK. The creator CRUD registry
declares `character`, `location`, `faction`, `item`
(`ENTITY_TYPE_REGISTRY`, `:123-200`). A runtime entity is created with
`entity.type = <slug>` (`:648`). `event` is its own table with a `title`
(`canon.py:482-500`), not an entity, and cannot carry a fact participant.
`artifact` extends `entity` (`canon.py:527-546`) but no writer sets
`entity.type = "artifact"` (grep: `writes/worlds.py:33` deletion order,
`analyzer_transcript.py:96` only). `GET /api/entities` without `type`
returns every entity of the active world (`:475-483`).
Consequence: `object` claims `item`; `other` is every type no other category
claims. Events stay out (N6c, named deferral).
### R-19 — the frontend
Opened: `frontend/src/lore/Lore.svelte:1-195`; `lore.svelte.js:1-88`;
`NamesPanel.svelte:1-86`; `namesPanel.svelte.js:1-104`;
`frontend/src/creation/FactsEditor.svelte:1-60`; `CLAUDE.md:532-534`;
`frontend/scripts/write-manifest.mjs:1-40` [M].
Finding: `Lore.svelte` switches tabs with `loreTab` (`:21`, `:84-85`) and
mounts `NamesPanel` only while the names tab is shown (`:87-88`).
`NamesPanel.svelte` labels categories in `CATEGORY_LABEL` (`:15`) and calls
`reloadForWorld()` in an `$effect` on `serverState.worldId` (`:17-20`), which
also runs on mount. `namesPanel.svelte.js` mirrors the categories in
`CATEGORY_TYPE` (`:11`), loads entities per type (`loadEntities`, `:29-35`),
builds options from candidates then search (`optionsFor`, `:52-61`), posts
`{entity_id}` on bind (`bindMention`, `:88-92`). `FactsEditor.svelte` shows, for a type
outside `TYPE_FAMILIES` (`:34-38`), only `description` (`:40-46`). The build
is `npm ci && npm run build` in `frontend/`, output committed
(`CLAUDE.md:532-534`); the manifest hashes the raw bytes of `frontend/src/**`
and four root files.
Consequence: E edits these files and rebuilds.
### R-20 — the build gate fails on the tarball
Opened: `python tooling/verify/checks/corpus_gate.py` on the tarball with
`requirements-dev.txt` installed [M].
Finding: two failures before any change. `frontend_build_fresh.py`: manifest
`source_hash 9f5b6c831fe5...` differs from the recomputed `34f53ebe8ed0...`.
`day_mutations.py` crashed under the corpus run; run alone with
`WORLD_ENGINE_ENV=test` it passes.
Consequence: briefs A-D verify the checks they name, not the full corpus.
E rebuilds, which clears the first; the corpus is run with
`WORLD_ENGINE_ENV=test` set. Whether the stale manifest is real on `main` or
an artifact of this environment was not decided here.

## Contracts

### C-07 — categories (`lore_resolve.py`, `lore_plan.py`)
Produced by: B (three categories), widened by C   Consumed by: B, C, D, E
After B:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
}
def category_of_type(entity_type: str) -> Optional[str]   # None when no category claims the type
```
After C:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
    "object": ("item",), "other": (),
}
OTHER_CATEGORY = "other"
CATEGORIES: tuple[str, ...] = tuple(_CATEGORY_ENTITY_TYPE)
def category_of_type(entity_type: str) -> str   # the claiming category, else "other"
```
`validate_binding(entity_id, category, world_id, db)`: for `other`, the
entity's type is claimed by no other category; otherwise its type is in the
category's tuple; always active and in `world_id`; unknown category ->
`False`.
`lore_plan._MENTION_CATEGORIES = ("place", "person", "faction", "object", "other")`
after C (R9 parity with the dict keys).
### C-10 — near candidates in the Lore answer
Produced by: D   Consumed by: E
`LoreResult` gains a last field `near: tuple[dict, ...] = ()`. Only the
`unknown_entity` construction sets it: one dict per unmatched surface form,
in plan order, `{"surface_form": str, "candidates": [{"entity_id", "name",
"type", "score"}, ...]}` from
`near_candidates(surface_form, world_id, db, scope=CREATOR)`.
`lore_render` adds one constant, verbatim:
```python
_NEAR_ITEM = "{nom} (ressemblance {pct} %)"
```
and `_render_unknown_entity` renders each block with
`_UNKNOWN_ENTITY_WITH_NEAR.format(surface_form=..., noms=", ".join(_NEAR_ITEM.format(nom=c["name"], pct=c["score"]) for c in candidates))`
when the surface's candidates are non-empty, else
`_UNKNOWN_ENTITY_WITHOUT_NEAR` as today. The six existing constants are not
edited. `/api/lore/ask` and `/api/lore/resolve` bodies gain
`"near": list(result.near)`.
### C-11 — the names panel API, amended (`cockpit/routes/lore_mentions.py`, `lore_mentions_read.py`)
Produced by: D   Consumed by: E
- `GET /api/lore/mentions`: each row gains `"near": [{"id", "name",
  "type", "score"}]` =
  `near_candidates(m.surface, world, db, scope=CREATOR, exclude_ids=<candidate ids>)`.
- `GET /api/lore/names/lookup?surface=<str>` -> 422 when the stripped
  surface is empty; else `{"surface": str, "candidates": [{"id", "name",
  "type"}], "near": [{"id", "name", "type", "score"}]}`; candidates = union
  over `CATEGORIES` of `resolve_named(surface, c, world, db,
  scope=CREATOR).candidate_ids`, sorted by name; near excludes them. Read in
  `lore_mentions_read.lookup_surface(db, world_id, surface) -> dict`.
- `POST /api/lore/appellations` body `{"entity_id": str, "surface": str,
  "scope_type": str = "rencontre"}` -> 422 when the entity is not an active
  entity of the world (`lore_mentions_read.entity_is_valid`: any category);
  `record_appellation(..., created_by="creator_crud")`; `ValueError` ->
  rollback, 422 with the message; one commit; returns `{"ok": true,
  "written": bool, "fact_id": str | null}`.
- `POST /api/lore/mentions/{id}/resolve` body gains
  `"record_appellation": bool = false` and `"scope_type": str =
  "rencontre"`. After `bind_mention`, when `record_appellation` is true,
  `record_appellation(db, entity_id=..., surface=mention.surface, ...)` in
  the same transaction; one commit; the response gains
  `"appellation_written": bool`.
Error cases: as today for 404 and bind's 422.

## Context

The backend now resolves appellations, offers near names and records
appellations from the names panel (A-D). This brief gives the creator the
three doors: a link from a Lore miss to the panel, near names and an
"also record as appellation" choice in the panel, and the `appellation`
facet on every entity sheet (B4).

## Scope IN

1. `namesPanel.svelte.js`:
   - Replace `CATEGORY_TYPE` and per-type loading by one load of
     `/api/entities` (no `type`, R-16), keeping `status === 'active'`, and
     `categoryOf(type)` = `{location: 'place', character: 'person',
     faction: 'faction', item: 'object'}[type] || 'other'` (the mirror of
     C-07; a comment names `lore_resolve.category_of_type`). Search filters
     by the mention's category when it has one, else all.
   - `optionsFor(mention)`: candidates, then `mention.near` (label suffix
     ` — ressemblance ${score} %`), then search results, no id twice.
   - State per mention: `record[id]` (bool, default false) and
     `recordScope[id]` (default `'rencontre'`). `bindMention` posts
     `{entity_id, record_appellation, scope_type}`.
   - Lookup state `namesState.lookup = null | {worldId, surface,
     candidates, near, choice, scope, busy, message}`;
     `openLookup(surface)` fetches `GET /api/lore/names/lookup?surface=`
     and stores it with `worldId = serverState.worldId`;
     `saveAppellation()` posts `/api/lore/appellations`; on
     `written: true` the message is « Appellation enregistrée. », on
     `written: false` « Déjà connue sous ce nom. »; `closeLookup()`.
   - `reloadForWorld()` clears `lookup` only when `lookup.worldId` differs
     from the current world (the panel's mount-time `$effect` must not wipe
     a lookup opened from the question tab). Respect
     `effect_self_write.py`: no `$state` assigned in an `$effect` is read
     afterwards in the same body.
2. `NamesPanel.svelte`:
   - `CATEGORY_LABEL` adds `object: 'objet'`, `other: 'autre'`.
   - When `namesState.lookup` is set, a card above the list: « « {surface} »
     — enregistrer comme appellation de : », an entity `<select>`
     (candidates, near with the resemblance suffix, then every active
     entity), a scope `<select>` with options `rencontre` « Ceux qui l'ont
     rencontré » (default), `world` « Tout le monde », `none` « Personne »,
     a button « Enregistrer » (disabled without a choice or while busy),
     the message, and « Fermer ».
   - Per mention line: a checkbox « Enregistrer aussi comme appellation »
     and, when checked, the same scope `<select>`.
3. `Lore.svelte`: when `result.verdict === 'unknown_entity'`, under the
   answer, one button per `mentionTrace` entry whose `verdict` is
   `'unmatched'`: « Lier « {surface_form} » à une entité… »; its click sets
   `loreTab = 'names'` then calls `openLookup(surface_form)`. Update the
   header comment (`:1-11`): the question view still writes nothing; this
   link only opens the panel.
4. `FactsEditor.svelte:40-46`: for a type outside `TYPE_FAMILIES`, show
   `description` and `appellation` (drafting judgment 3 of the lot
   delivery).
5. Build: `cd frontend && npm ci && npm run build`; commit the output
   (`CLAUDE.md:532-534`).
6. `ARCHITECTURE_DECISIONS.md`: append
   `## LORE MISS TO NAMES PANEL (TICKET-0092) -- THE CREATOR NAMES WHAT THE TOOL MISSED (BRIEF-0092-e, no schema change)`;
   regenerate the index.

## Scope OUT

- Any new route or backend change (D).
- A mention picker in sheet text fields (0091 Q15b deferral).
- Showing near names inside the answer prose differently from D's text.
- A scope picker for location or faction scopes in the panel.

## Invariants to defend

- "UI-visible data never lives in JSON": nothing new is stored client-side
  beyond transient state.
- The question view writes nothing (Q17d): the link only navigates.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold.
- `page_contract.py` or `effect_self_write.py` fails and the fix needs a
  change outside the four files of Scope IN 1-4.

ADAPT:
- `frontend_build_fresh.py` still fails after a clean `npm ci && npm run
  build` with LF sources: report the two hashes and the `git config
  core.autocrlf` value; do not edit the check (R-20).

REPORT-ONLY:
- Whether the pre-change manifest mismatch (R-20) reproduced in your
  environment.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] PASS: `frontend_build_fresh.py`, `static_asset_freshness.py`,
      `page_contract.py`, `effect_self_write.py`, `decisions_index.py`.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py`
      reports no failure.
- [ ] Manually on a test world: a Lore miss shows the link; the panel opens
      with the name; « Enregistrer » writes; asking again resolves.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (Scope IN 6).
