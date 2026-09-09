---
id: TICKET-0083
title: Creation sub-tab switch loses the sheet reset
type: bug
status: exec
created: 2026-09-08
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0083-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"j'ai un bug qui fait que lorsque je rentre dans un intrigue (cote createur ) et
que je veux changer pour aller aux NPC par exemple, om m'affiche encore le
contenu de l'instigue que j'ai ouvert avec la liste des intrigues a gauche. Rien
ne devrais changer sauf la reparation du bug"

## Clarifications resolved (intake)

- Reproduced end to end in a headless harness (jsdom + the real Vite bundle,
  `Creation.svelte` mounted, `fetch` stubbed). Every fact below is measured,
  not inferred. [M]

- The defect chain, five measured links:

  1. `frontend/src/creation/tabs.js:461` -- `showCreationSubTab()` writes
     `creationState.activeTabKey = tab` BEFORE any sheet reset. [M]

  2. `frontend/src/creation/Sheet.svelte:612,615` -- the two record-tab render
     branches are gated on `tabKey` (`activeTabKey`), while the DATA those
     branches consume comes from `sheetType`/`sheetDetail`. Two facts, two
     writers, no ordering contract between them. [M]

  3. `frontend/node_modules/svelte/src/internal/client/reactivity/batch.js:1020-1024`
     -- `flushSync(fn)` flushes the PENDING batch before running `fn`. The
     reset itself is therefore what forces the inconsistent frame. [M]

  4. `frontend/src/creation/Sheet.svelte:641` -- the generic entity branch
     reads `registry.types[type].label` unguarded. With `type === 'intrigues'`
     (a tab id, absent from `ENTITY_TYPE_REGISTRY`) this raises
     `TypeError: Cannot read properties of undefined (reading 'label')`. [M]

  5. The throw happens inside a `dispatchEvent` listener, so it surfaces as an
     uncaught error and `showCreationSubTab` keeps running (URL and sub-tab
     button both update) while the `flushSync` callback never executes: the
     sheet reset is silently lost, and every DOM update queued in the aborted
     batch -- the sheet's AND the sidebar's -- is dropped. That is exactly the
     reported symptom. [M]

- Blast radius, measured as a full transition matrix (one process per pair,
  record open on the source tab):

  | Source | Destinations | Verdict |
  |---|---|---|
  | `intrigues` | npc, pj, lieux, factions, objets, competences, region, constructeur, artefacts, registre, queue, prompts | 12/13 FAIL |
  | `intrigues` | `evenements` | pass (its branch precedes intrigues' and tolerates the agenda shape) |
  | `evenements` | npc, pj, lieux, factions, objets, competences, registre, prompts | FAIL, same signature |
  | either, with NO record open | all | pass (`mode=empty`, the generic branch is never rendered) |

  So this is the "record tab with an open record" class, not an intrigues
  quirk. The seven bespoke entries (`onTabEnter: null`) are worse: nothing
  catches the throw at all. [M]

- Two independent faults, both required to produce the symptom:
  - F1 (ordering): `activeTabKey` moves before the reset -- and for bespoke
    tabs there is no reset at any point.
  - F2 (unguarded read): the generic branch has no `registry.types[type]`
    existence guard, so a transient mismatch is a hard throw rather than a
    blank frame.

- Both candidate fixes were applied to a scratch tree, rebuilt, and re-measured
  against the same matrix. Ordering fix alone: 16/16 green. Type-gating alone:
  no crash, but the sheet stays `view/intrigues` under bespoke tabs (inside a
  `display:none` container -- harmless, not clean). Both together: 18/18
  transitions land on `mode=empty type=null`, zero uncaught errors, and all
  five create modes (`intrigues`, `evenements`, `npc`, `pj`, `factions`) render
  byte-for-byte as before. [M]

- Decisions locked by Nia: A1 (hoist the reset into `showCreationSubTab`,
  before the key move, and delete the now-redundant per-entry dispatches),
  B1 (gate the record branches on `type`, guard the generic branch),
  C1 (new `creation_tab_switch.py` rather than extending `creation_island.py`).

- Not a build-staleness problem: the committed bundle
  (`index-CmOQTqiy.js`) rebuilds to an identical hash. [M]

- No schema change. Frontend only.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `showCreationSubTab` dispatches `creation:sheet-reset` at an offset strictly BEFORE its `creationState.activeTabKey = tab` assignment  -> verify/checks/creation_tab_switch.py
- [ ] `creation:sheet-reset` is dispatched from exactly one site in `frontend/src/`, and that site is in `tabs.js`  -> verify/checks/creation_tab_switch.py
- [ ] `Sheet.svelte` gates its record branches on `type`, never on `tabKey`, and guards the generic branch with `registry.types[type]`  -> verify/checks/creation_tab_switch.py
- [ ] `_entityTabEnterReset` / `_intriguesTabEnterReset` / `_evenementsTabEnterReset` no longer exist in `tabs.js`  -> verify/checks/creation_tab_switch.py
- [ ] The Creation island seam is intact (every declared containerId still resolves, registry still many-to-many)  -> verify/checks/creation_island.py
- [ ] Every Creation page is still a `CREATION_TABS` entry rendered by the generic dispatcher  -> verify/checks/page_contract.py
- [ ] `tabs.js` and `Sheet.svelte` stay under the 1000-line frontend ceiling  -> verify/checks/module_budget.py
- [ ] The committed `src/world_engine/cockpit/static/` output is a fresh build of `frontend/src/`  -> verify/checks/frontend_build_fresh.py
- [ ] The served static assets match the manifest  -> verify/checks/static_asset_freshness.py

### Live  ->  human gate (Nia)
- [ ] Open Creation -> Intrigues, click an intrigue, then click NPC: the sidebar shows the NPC list and the sheet shows "Selectionnez une entite depuis la liste, ou creez-en une nouvelle."
- [ ] Same from Intrigues to each of Lieux, Factions, Objets, Competences, Prompts, Review Queue: no frozen content, no console error.
- [ ] Same starting from Evenements with an event open.
- [ ] Browser console is clean across all of the above -- no `Cannot read properties of undefined`.
- [ ] Create modes still work unchanged: "+ Nouvelle intrigue", "+ Nouvel evenement", "+ Nouveau" on NPC / PJ / Factions each render their own panel with the correct header title.
- [ ] Cross-tab navigation still works: open an NPC, follow an entity_ref into another tab, then use the return crumb to come back.
