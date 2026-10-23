<!-- slug: world-sheet-page -->
# BRIEF 0124-J — "The « Monde » page -- name, description, tone and laws of the active world, edited in Création; the tone in the world-create modal (W1, B2) (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: BRIEF-0124-A (`GET`/`PUT /api/worlds/{world_id}`, `WorldCreateBody.tone`, C-02)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot) plus BRIEF-0124-A to I.

- `src/world_engine/cockpit/routes/creator.py` -> `get_world`, `update_world`, `WorldCreateBody.tone` (BRIEF-0124-A).
- `frontend/src/creation/tabs.js:363-371` -> the `vocabulaire` entry; `:383-391` -> `suivi` with `primaryAction: null`; key order of R-32.
- `frontend/public/creation.css:314-315` -> `#creation-vocabulaire` and `#creation-suivi` rules.
- `frontend/src/creation/Creation.svelte` -> `<div id="creation-vocabulaire" ...></div>` then `<div id="creation-subjects" ...></div>` (the Vocabulaire container block).
- `frontend/src/creation/registry.js` -> last entry `germPanel` (BRIEF-0124-H); `mount.js` -> `COMPONENTS` ending `germPanel: GermPanel`.
- `frontend/src/creation/WorldCrud.svelte:38-51` and `worldCrud.svelte.js:34-36, :66-71, :95-100, :107-125` (R-31).
- `frontend/src/lib/serverState.svelte.js` -> `serverState.worldId`, `export async function refreshServerState()` (`:14`).
- `tooling/verify/checks/event_journal.py:678` -> the regex `\n  vocabulaire: \{(.*?)\n  \},`.
- No `frontend/src/creation/WorldSheet.svelte`.

## Facts carried

### R-28 — the island registry [M]
Opened: `frontend/src/creation/registry.js:481-490` (`pjSkillFiche`, origin `migration`), `:574-588` (`vocabulary`, `dashboard`: origin `new`, `createdBy`); `mount.js:50` (`COMPONENTS`); `tooling/verify/checks/creation_island.py:164` (`NEW_ALLOWED = {"containerId", "component", "origin", "createdBy"}`), `:52-131` (docstring of rule 2: a `new` entry has exactly those fields, `createdBy` matching `^TICKET-\d{4}$`; rule 4: every `containerId` is an element id of `Creation.svelte`; rule 5: every registry key is declared by an `islands` entry and back; rule 13: `Creation.svelte` imports and mounts no component).
Consequence: the germ panel and the world sheet are `new` islands (`germPanel`, `worldSheet`), each in `COMPONENTS`, each declared by the tabs that show it.

### R-31 — the world-create modal [M]
Opened: `frontend/src/creation/WorldCrud.svelte:38-51` (name, description, laws fields); `worldCrud.svelte.js:34-36` (`createName`, `createDescription`, `createLaws`), `:66-71` (reset), `:95-100` (AI draft fill), `:107-125` (`worldCreateSubmit` posts `name, description, fundamental_laws`).
Consequence: brief J adds `createTone` beside them.

### R-32 — the Création tab registry [M]
Opened: `frontend/src/creation/tabs.js` (keys in order: `npc, pj, lieux, factions, objets, competences, region, constructeur, artefacts, registre, intrigues, evenements, quetes, dettes, vocabulaire, subjects, suivi, queue, prompts`), `:363-371` (`vocabulaire`: `archetype: 'bespoke'`, one container, one island, a `primaryAction`), `:383-391` (`suivi`: `primaryAction: null`); `frontend/public/creation.css:314-315` (`#creation-vocabulaire`, `#creation-suivi` `{ flex: 1; min-height: 0; overflow: auto; }`).
Consequence: `monde` is inserted after `vocabulaire`, shaped like `suivi`.

## Contracts

### C-02 — one world, read and edited
Produced by: BRIEF-0124-A   Consumed by: BRIEF-0124-J
`GET /api/worlds/{world_id}` -> `{"id", "name", "description", "tone", "laws": [str, ...], "is_active"}` (`description`/`tone` as stored, `None` allowed; `laws` the `WorldLaw.text_` values by `position`). 404 unknown id.
`PUT /api/worlds/{world_id}` body `WorldUpdateBody(name: str, description: str = "", tone: str = "", laws: list[str] = [])` -> the same shape as GET. Writes `name` (stripped; empty -> 422 « Le nom est requis. »), `description` and `tone` (stripped; empty -> `None`), `updated_at`, then `write_world_laws(db, world=world, laws=body.laws, changed_by="creator")`; one commit. 404 unknown id. Does not touch `is_active` or `current_phase`. Any world, active or not.
`WorldCreateBody` gains `tone: str = ""`; `create_world` writes it (stripped; empty -> `None`).

### C-15 — the « Monde » page
Produced by: BRIEF-0124-J   Consumed by: nothing in this lot
`CREATION_TABS.monde = { label: 'Monde', archetype: 'bespoke', containers: ['creation-monde'], loader: null, state: { onTabEnter: null, onWorldSwitch: null }, islands: [{ key: 'worldSheet', containerId: 'creation-monde' }], primaryAction: null }`, inserted after `vocabulaire`; registry `worldSheet` (`WorldSheet.svelte`, origin `new`, `createdBy: 'TICKET-0124'`); `#creation-monde { flex: 1; min-height: 0; overflow: auto; }`.

## Context

Nia asked where she can edit the world's laws: nowhere after creation
(R-03). Brief A opened the routes; this brief is the page, and the tone
field of the create modal.

## Scope IN

1. `tabs.js`: C-15's `monde` entry, inserted right after the `vocabulaire` entry's closing `},` (so `event_journal.py`'s regex still finds `vocabulaire` closed by `\n  },`), with the comment « TICKET-0124 (BRIEF-0124-J, W1): the world's name, description, tone and laws. »
2. `registry.js`: `worldSheet: Object.freeze({ containerId: 'creation-monde', component: 'WorldSheet.svelte', origin: 'new', createdBy: 'TICKET-0124' })` after `germPanel`, with a one-line comment; `mount.js`: `import WorldSheet from './WorldSheet.svelte';` and `worldSheet: WorldSheet` in `COMPONENTS`.
3. `Creation.svelte`: after the `creation-vocabulaire` container, `<!-- ── Monde sub-tab -- Svelte island (TICKET-0124): empty by construction ── -->` and `<div id="creation-monde" style:display={containerVisible('creation-monde') ? '' : 'none'}></div>`.
4. `creation.css`: `#creation-monde        { flex: 1; min-height: 0; overflow: auto; }` after `#creation-suivi`.
5. New `frontend/src/creation/WorldSheet.svelte` (no scoped `<style>`; `field-grid`, `field-row`, `btn-send`, `btn-ghost`): on mount and whenever `serverState.worldId` changes, `GET /api/worlds/{worldId}`; fields « Nom * » (input), « Contexte du monde » (textarea, 4 rows), « Ton et style » (textarea, 3 rows, placeholder « Registre, genre, conventions de noms… »), « Lois fondamentales — vraies partout, connues de tous » (one input per law with « ↑ », « ↓ », « ✕ », and « + Ajouter une loi »); « Enregistrer » sends `PUT /api/worlds/{worldId}` with `{ name, description, tone, laws }` (empty law inputs dropped), then `await refreshServerState()` and shows « Enregistré. » or the error; « Aucun monde actif. » without one. No `alert`, `confirm`, `prompt`.
6. `WorldCrud.svelte`: after the description field, a field `world-create-tone` « Ton et style (optionnel) » (textarea, 2 rows) bound to `worldCrudState.createTone`. `worldCrud.svelte.js`: `createTone: ''` beside `createDescription`; reset with the others; the AI draft leaves it as is; `worldCreateSubmit` sends `tone: worldCrudState.createTone.trim()`.
7. Rebuild and commit `src/world_engine/cockpit/static/`.
8. Extend `tooling/verify/checks/world_sheet.py` with **WG1** (static): `tabs.js` holds the `monde` entry with `containers: ['creation-monde']` and `{ key: 'worldSheet', containerId: 'creation-monde' }` after the `vocabulaire` entry; `registry.js` the `worldSheet` entry; `mount.js` `worldSheet: WorldSheet`; `WorldSheet.svelte` holds `/api/worlds/`, `method: 'PUT'`, `Ton et style`, `refreshServerState` and none of `alert(`, `confirm(`, `prompt(`; `WorldCrud.svelte` holds `world-create-tone`; `worldCrud.svelte.js` holds `tone: worldCrudState.createTone`.

## Scope OUT

- Generating a tone with the AI (`world_generation` is `none`).
- Editing another world than the active one from this page (the route allows it; the page edits the active one).
- Law history, hidden laws (W2, D2).
- `list_worlds` and the header's world selector.

## Invariants to defend

- creation_island rules 2, 4, 5, 13 -- `worldSheet` is `new`, its container an id of `Creation.svelte`, declared by `monde`, mounted by `mount.js` only.
- creation_container_sizing rule 2 -- `monde` is a single-container entry: its `#creation-monde` rule declares `flex: 1` and `min-height: 0`.
- The no-dialog rule.

## Decision rights

STOP: a Mini-RECON anchor that does not hold; `event_journal.py` or `creation_island.py` goes red.
ADAPT: `serverState.worldId` is not reactive in a component -> read it through the same import `KnowledgeEditor.svelte` uses, report.
REPORT-ONLY: layout tuning.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/world_sheet.py` -> `PASS` (WS1-WS3, WG1).
- [ ] Named mutation, turning WG1 red, then reverted: remove `tone:` from `worldCreateSubmit`.
- [ ] `creation_island.py`, `creation_container_sizing.py`, `event_journal.py`, `stylesheet_partition.py`, `static_asset_freshness.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS` (the lot's last brief).
- [ ] Live (Nia): « Monde » shows Aestia; its tone and a new law saved; reloading shows them; the create modal has the tone field.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## THE « MONDE » PAGE (TICKET-0124) -- WorldSheet.svelte, the tone in the create modal (BRIEF-0124-J, no schema change)` -- W1.
