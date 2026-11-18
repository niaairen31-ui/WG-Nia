<!-- slug: active-pc-selector -->
# BRIEF 0128-C — "The « PJ actif » selector in the cockpit header"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-B (C-06: `/api/active-pc`)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/cockpit/routes/active_pc.py` exists with `GET` and
  `PUT /api/active-pc` (B).
- `frontend/src/Header.svelte` is 145 lines; `:83` is `<select
  id="world-selector" onchange={onWorldChange} title="Monde actif">`, inside
  `{#if !serverState.error}` (:82-88); `:1-7` imports `onMount`,
  `serverState`, `refreshServerState`, `activateWorldCascade`, the world
  modals, `navigate`, the schedule constants.
- `frontend/src/lib/serverState.svelte.js` exports `serverState` and
  `refreshServerState`.
- `frontend/src/creation/tabs.js:825` is `export async function
  handleWorldChanged()`.
- `frontend/src/creation/sheetRequest.svelte.js:32` is `export async
  function api(path, options)` (it throws `errorMessage(...)`, INV-69).
- `frontend/src/journee/Journee.svelte:42-50` is the `$effect` that starts
  with `void serverState.worldId;` and calls `reloadForWorld()`.
- `ls frontend/src/lib` -> `errorMessage.js router.js serverState.svelte.js`;
  `frontend/src/ActivePcSelector.svelte` does not exist.

Halt if any anchor has moved.

## Facts carried

### R-13 -- the bootstrap and the shell's server mirror
Opened: `src/world_engine/cockpit/routes/creator.py:753-776`;
`src/world_engine/cockpit/legacy.html:1742-1760, 2752`;
`frontend/src/lib/serverState.svelte.js:1-35`;
`frontend/src/Header.svelte:1-98`; `frontend/src/creation/tabs.js:825-850`;
`frontend/src/creation/PjCreatePanel.svelte:130-138`;
`tooling/verify/checks/legacy_call.py:1-50`;
`tooling/verify/checks/module_budget.py:28-65`.
Finding: `get_bootstrap` returns `{world_id, player_id,
current_location_id}`; `player_id` comes from
`_crud._player_character_id` with `except HTTPException: player_id = None`
(:767-771). The legacy document reads `/api/bootstrap` once, at boot
(`loadBootstrap`, :1743-1749, called at :2752), into `PLAYER_ID`, used to
leave the PC out of member lists and to show his name. The shell's
`refreshServerState()` reads `/api/bootstrap` and `/api/worlds` into
`serverState.{worldId, playerId, worlds}`; `serverState.playerId`'s only
other reader is `PjCreatePanel.svelte:133-137`. `Header.svelte` (145
lines) holds the world `<select id="world-selector">` (:83) whose change
runs `activateWorldCascade(id, refreshServerState)`, which ends with
`handleWorldChanged()` (Création's refresh, `tabs.js:825-833`). The bridge
census (`legacy_call.py`) may only shrink: no new call into the legacy
window. `legacy.html` is held by a line ratchet (`module_budget.py`,
`LEGACY_DOCUMENT_LINE_CEILING = 2762`).
Consequence: the selector refreshes the shell mirror and Création; the
legacy document is not touched (its `PLAYER_ID` follows at its next load;
Play is out of scope). The bootstrap keeps its three keys.

### R-20 -- module budgets of the files this lot edits
Opened: `wc -l` and an `ast` function count of each file;
`tooling/verify/checks/module_budget.py:1-65`.
Finding (lines / top-level functions + methods):
`cockpit/routes/day.py` 903 / 28 (caps 1000 / 40, also JI7);
`cockpit/crud/entities.py` 932; `cockpit/routes/creator.py` 913;
`cockpit/crud/_shared.py` 296; `models/pipeline.py` 816;
`models/canon.py` 822; `writes/pipeline.py` 380; `cockpit/app.py` 360;
`dashboard_metrics.py` 372; `cockpit/routes/player.py` 192;
`frontend/src/journee/Journee.svelte` 263;
`frontend/src/Header.svelte` 145; `frontend/src/creation/tabs.js` 899
(frontend cap 1000 lines). `routes/day.py`'s functions are listed in R-15,
R-16 and :96-208.
Consequence: no logic beyond the P1 edits enters `routes/day.py`; every new
route or worker lives in a new module (C-06, C-10, C-11, C-12, C-13).

### R-23 -- the quest pin in Journée
Opened: `frontend/src/journee/quests.svelte.js:1-45`;
`frontend/src/journee/journee.svelte.js:1-135`;
`frontend/src/journee/Journee.svelte:1-263`.
Finding: `questState.pin` (:15) is the quest a planned day advances, ''
for « le jeu choisit »; `apply()` clears a pin that is no longer an open
quest. `planDay(id, questId)` posts `{quest_id}` when pinned (:74-90);
`resolveDay(id)` (:92-104); `submitDeclaration()` posts `{declared_action}`
(:106-125). `Journee.svelte` shows the pin `<select>` and « Émettre le
plan » for a `submitted` day, « Résoudre la journée » for a `resolving`
day (:127-143), and the account of a resolved day (:169-235).
Consequence: D moves the pin to the declaration panel; E removes the plan
and resolve buttons (the worker runs them) and adds the failure panel; F
adds the publish panel.

### R-32 -- the arrow floor and the gate
Opened: `tooling/verify/checks/pipeline_state.py:54, 113-120`;
`tooling/verify/checks/corpus_gate.py:20-60`.
Finding: for a ticket in `brief`, `exec`, `verify`, `live-gate` or `done`,
every Machine-checkable arrow must name an existing file under
`tooling/verify/checks/`; `corpus_gate.py` runs each check with a 15 s
timeout (`TIMEOUT_SECONDS`) unless listed in `SLOW_CHECK_TIMEOUTS`.
Consequence: while 0128 is in `exec`, `pipeline_state.py` (and with it
`corpus_gate.py`) is red for each arrow whose check a later brief creates:
`day_schema.py` until A, `active_pc_selector.py` until C,
`day_chain_world.py` until D, `day_runs.py` until E, `day_publication.py`
until F, `player_journee.py` until G. Every Done means names that red.

### R-33 -- the module map and the build
Opened: `tooling/verify/checks/file_map.py:1-40`;
`tooling/verify/checks/frontend_build_fresh.py` (run: PASS, 168 sources,
3 assets).
Finding: `FILE_MAP.md` must equal a fresh render of every module's first
docstring sentence (`python tooling/glue/gen_file_map.py`); the committed
frontend build must match its sources' hash.
Consequence: every brief that adds a Python module regenerates the map;
every brief that edits `frontend/src` runs `npm run build` in `frontend/`
and commits the output.

## Contracts

### C-06 -- the active-PC routes
Produced by: B   Consumed by: C
Module `src/world_engine/cockpit/routes/active_pc.py`, included in
`cockpit/app.py` after `_routes_day`. Both routes act on the active world
(`_crud._world_id`).
- `GET /api/active-pc` -> `{"world_id": str, "active_pc_id": str | None,
  "chosen": bool, "characters": [{"id": str, "name": str}]}`;
  `active_pc_id` is `active_pc_id_or_none`; `chosen` is
  `world.active_pc_id is not None and world.active_pc_id ==
  active_pc_id`; `characters` is `world_player_characters` as `{id,
  name}`, in its order.
- `PUT /api/active-pc` with body `{"character_id": str | None}` ->
  `write_active_pc`; `ValueError` -> 422 with its message, nothing
  committed; else one commit and the GET shape.
- No active world -> `_world_id`'s 400.

## Context

B gave the cockpit one resolver and the routes to choose the active PC.
This brief puts the choice where every surface sees it, in the header,
next to the world (A1). After a choice the shell re-reads the server
state, Création refreshes, Journée reloads its quests and debts.

## Scope IN

1. New `frontend/src/lib/activePc.svelte.js` (comment header « TICKET-0128
   (BRIEF-0128-C, A1). The active player character of the active world:
   the header's selector reads and sets it through /api/active-pc. »):
   ```
   import { api } from '../creation/sheetRequest.svelte.js';
   import { refreshServerState } from './serverState.svelte.js';
   import { handleWorldChanged } from '../creation/tabs.js';

   export const activePcState = $state({ characters: [], activeId: null, chosen: false, error: '' });

   function apply(body) { ... }            // characters, activeId (body.active_pc_id), chosen, error ''
   export async function loadActivePc() { ... }   // GET '/api/active-pc'; on error: characters [], error = e.message
   export async function chooseActivePc(id) {      // PUT then refresh
     ... api('/api/active-pc', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                                 body: JSON.stringify({ character_id: id || null }) }) ...
     apply(result); await refreshServerState(); await handleWorldChanged();
   }
   ```
   (`...` is the executor's code; every request goes through `api`.)
2. New `frontend/src/ActivePcSelector.svelte`: a label « PJ actif » and a
   `<select id="active-pc-selector" title="Le personnage joueur pour lequel
   agit le cockpit">`:
   - no character -> one disabled option « Aucun PJ » and the select
     disabled;
   - several and `!activePcState.chosen` -> a first option « — Choisissez
     le PJ actif — » (value `''`, selected), then one option per character;
   - otherwise one option per character, the one whose id is
     `activePcState.activeId` selected;
   - `onchange` -> `chooseActivePc(event.target.value)`.
   A `$effect` whose body is `void serverState.worldId; loadActivePc();`.
   `activePcState.error` shows as a short red text after the select.
3. `frontend/src/Header.svelte`: `import ActivePcSelector from
   './ActivePcSelector.svelte';` and `<ActivePcSelector />` right after
   the world `<select>`, inside the same `{#if !serverState.error}` block.
   Nothing else in the header changes.
4. `frontend/src/journee/Journee.svelte`, the `$effect` of `:42-50`: a
   second line `void serverState.playerId;` right after `void
   serverState.worldId;` (a new active PC reloads the days, the quests and
   the debts).
5. `cd frontend && npm run build`; commit the output.
6. New check `tooling/verify/checks/active_pc_selector.py`, first sentence
   « G1 check for TICKET-0128 (BRIEF-0128-C) -- the cockpit header carries
   the « PJ actif » selector. », static (file reads, no DB):
   - **AS1** `Header.svelte` imports `ActivePcSelector` from
     `./ActivePcSelector.svelte` and holds `<ActivePcSelector />` after
     `id="world-selector"`;
   - **AS2** `ActivePcSelector.svelte` holds `id="active-pc-selector"`,
     `Choisissez le PJ actif`, `Aucun PJ`, `chooseActivePc(` and
     `loadActivePc(`;
   - **AS3** `lib/activePc.svelte.js` holds `'/api/active-pc'`, `method:
     'PUT'`, `character_id`, `refreshServerState()`, `handleWorldChanged()`,
     imports `api` from `../creation/sheetRequest.svelte.js`, and holds no
     `fetch(` and no `detail`;
   - **AS4** `Journee.svelte` holds `void serverState.playerId;`;
   - **AS5** a built asset under `src/world_engine/cockpit/static/assets`
     carries `Choisissez le PJ actif`.
   A missing file is a FAILURE.

## Scope OUT

- `legacy.html` and any bridge call (`legacy_call.py` only shrinks):
  Play's `PLAYER_ID` follows at its next load (drafting decision 2).
- The server routes (B), Journée's day panels (D, E, F).
- Showing the active PC anywhere else in the UI.

## Invariants to defend

- **INV-69**: every request of the new files goes through `api`
  (`frontend_error_message.py`).
- **INV-55**: the new `$effect` reads `serverState.worldId` and calls a
  function; it assigns nothing it reads (`effect_self_write.py`).

## Decision rights

STOP: an anchor that does not hold; `handleWorldChanged` throwing on a
world whose Création is not loaded yet (report the trace).
ADAPT: the header overflows at 1280 px with the new select -> shorten the
label to « PJ » and keep the title; report it.
REPORT-ONLY: Play still shows the former PC's name until the page reloads.
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/active_pc_selector.py` -> PASS (AS1-AS5).
- [ ] `frontend_build_fresh.py`, `frontend_error_message.py`,
      `effect_self_write.py`, `legacy_call.py`, `module_budget.py`,
      `debts.py`, `quests.py`, `skill_progression.py`, `day_mutations.py`
      -> PASS.
- [ ] `pipeline_state.py` / `corpus_gate.py` red only for the arrows of D,
      E, F, G.
- [ ] Live, test database, a world with two PCs: the header shows « —
      Choisissez le PJ actif — »; Journée › Quêtes shows « Choisissez le PJ
      actif. »; picking one lists his quests and debts; picking the other
      switches them.
- [ ] /review-step, then /close-step.

## Docs to update

None (no rule, no schema). The ticket's ARCHITECTURE_DECISIONS entry is G's.
