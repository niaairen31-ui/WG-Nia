# BRIEF — Step "Création tab registry, generic dispatcher, state contract, entity archetype"

Ticket: TICKET-0005. Brief a of c. All `file:line` anchors from
RECON-0005 result (verified against `src/world_engine/cockpit/index.html`,
`app.py`, `crud.py`).

## Context

The Création surface has ten sub-tabs rendered through a hand-maintained
dispatcher (`showCreationSubTab`, index.html:2961-3026) with per-tab
conditionals, three divergent layout idioms, and a partial, ad hoc state
reset (only 4 of ~20 tab-scoped globals cleared on world switch —
index.html:5842-5845). Locked decisions: D′2-shell (two-level registry, all
ten tabs, entity archetype now), F1 (stay in index.html, vanilla JS, no new
dependency), G1 (declared per-tab state contract), H1 (remove the duplicate
Lieux create button). This brief installs the registry, the generic
dispatcher, the state contract, and applies the entity archetype to the
four already-near-conforming tabs plus Artefacts. PJ migration is brief -b;
bespoke-page shell migration is brief -c.

## Scope IN

1. **`CREATION_TABS` registry** (new module-level const in index.html, near
   the existing state declarations ~index.html:2855). One entry per tab, ten
   entries total, keyed by the existing tab ids used by
   `showCreationSubTab`. Entry shape (documented in a comment block above
   the const, verbatim):
   ```
   // CREATION_TABS entry contract (TICKET-0005):
   // { label:        string, tab title shown in the shell header
   //   archetype:    'entity' | 'bespoke'
   //   containers:   [element ids to show when active; all others hidden]
   //   loader:       function called on activation
   //   state:        { onTabEnter: fn|null, onWorldSwitch: fn|null }
   //                 each fn resets ALL state this tab owns for that event
   //   // entity archetype only:
   //   listLoader:   fn (default authorLoadEntityList)
   //   listRenderer: fn|null (null = flat list; lieux = renderLieuxBrowse)
   //   createPanel:  fn|null (null = no + Nouveau rendered; default =
   //                 () => authorRenderSheet({}, true, <type>))
   //   slots:        [{ id, containerId, loader, onSelect: fn|null }]
   // }
   // Every Création page is a registry entry. No page renders outside it.
   ```
2. **Generic dispatcher.** Rewrite `showCreationSubTab(tab)`
   (index.html:2961-3026) to: look up `CREATION_TABS[tab]`; hide the union
   of all entries' containers; show the entry's `containers`; run
   `state.onTabEnter` if present; call `loader`; for entity entries, render
   the standard layout (item 4). The function body must contain **no tab-id
   string literals and no per-tab conditionals** — all variation lives in
   registry data. Current per-tab reset behavior is preserved by moving it
   into the entries' `onTabEnter`: editor-tab detail reset
   (index.html:2988-3002) becomes a shared helper referenced by the five
   entity entries; Lieux browse reset (index.html:2991-2994,
   `lieuxBrowseParentId`/`lieuxBreadcrumb`) goes into the lieux entry;
   PJ's `pjCreateOpen` reset (index.html:3007-3010) goes into the pj entry
   unchanged (its replacement is brief -b's job, not this one's).
3. **World-switch state contract (G1).** In `activateWorld()`
   (index.html:5824-5855), replace the four hardcoded resets
   (index.html:5842-5845) with a loop over `CREATION_TABS` calling each
   entry's `state.onWorldSwitch`. The declared resets must cover, at
   minimum, every variable RECON question 6 lists as currently NOT reset:
   `lieuxBrowseParentId`, `lieuxBreadcrumb`, `lieuxActiveOnly`,
   `regionDraft`, `regionManifest`, `regionManifestNotes`,
   `regionManifestSkipped`, `regionAccepted`, `regionConfirmedLinks`,
   `competencesDraft`, `authorFactionRolesDraft`, `graphData`,
   `pendingDraftKnowledge`, `pcDraftKnowledge` — plus the four already
   reset (`authorAllEntities`, `playerCharIds`, `skillCharacters`,
   `_registreEntitiesLoaded`). `worldDeleteConfirm()`
   (~index.html:5973-6003) reuses the same loop.
4. **Entity archetype standard layout.** For `archetype: 'entity'` entries:
   shell header band (tab `label` + the single `+ Nouveau` control,
   `#creation-new-btn` in `#creation-new-row`, index.html:1182-1183, always
   top of sidebar) rendered from the registry — `+ Nouveau` appears iff
   `createPanel` is non-null and invokes it; list region via
   `listRenderer` (flat default index.html:3809-3815, lieux override
   `renderLieuxBrowse` index.html:3872); detail region via the existing
   `authorRenderSheet` path (index.html:4024, internals untouched); slots
   region: after activation and after `authorSelectEntity` resolves, each
   slot's `loader`/`onSelect(id)` runs. Applied in this brief to entries:
   **npc, factions, objets, lieux, artefacts**.
5. **H1 — Lieux duplicate button removed.** Delete the "Ajouter un lieu"
   control from the graph panel header (index.html:1169). Lieux creation
   goes through the standard `#creation-new-btn` only (handler chain
   `creationNewEntity()` index.html:3753 unchanged).
6. **Graph as declared slot.** The Lieux graph panel
   (`#creation-lieux-graph`, index.html:1165, loader `graphLoad`
   index.html:5680) stops being special-cased in the dispatcher
   (index.html:2976) and becomes `slots: [{ id: 'graph', containerId:
   'creation-lieux-graph', loader: graphLoad, onSelect: null }]` on the
   lieux entry. Component code (`graphLoad` and its render) unchanged.
7. **Artefacts as degenerate entity entry.** `archetype: 'entity'`,
   `createPanel: null` (no `+ Nouveau` rendered), list from the existing
   fetch (index.html:3316, `GET /api/entities?type=artifact`), no detail
   selection (list items non-clickable, as today), the existing static
   notice (index.html:1282-1283) kept as the list's empty-state/footer text.
8. **Bespoke entries registered, bodies untouched.** competences, region,
   registre, queue: registry entries with `archetype: 'bespoke'`,
   `containers`, existing `loader` (`competencesLoadList` index.html:3132,
   `regionRenderAll` call site index.html:3022, `loadRegistre`
   index.html:3274, `loadQueue` index.html:2489), and `state` per item 3.
   Their layout/markup is NOT modified in this brief (brief -c).
9. **Verify check** `verify/checks/page_contract.py` (deterministic, exit
   code 0/1): (a) `CREATION_TABS` literal exists in index.html and contains
   all ten tab keys; (b) the `showCreationSubTab` function body contains
   none of the ten tab-id string literals; (c) the string
   `Ajouter un lieu` is absent from index.html. Wire it into the standard
   verify run alongside existing checks.

## Scope OUT

- **PJ migration entirely** (Fiche slot, create form behind the standard
  button, removal of `pjCreateNew`/`pjCreateOpen`/`#pj-create-block`, the
  `currentCreationSubTab === 'pj'` branch in `authorSelectEntity`
  index.html:4945-4949) — brief -b. In this brief the pj entry is
  registered `archetype: 'entity'` but keeps its current special blocks
  wired exactly as today via its `onTabEnter`/`containers`.
- **Shell header for bespoke tabs** (moving Compétences' add-row control,
  collapsing Registre's form, Région primary action, queue filter band) —
  brief -c.
- **Generalizing the graph component** to NPC or any other entity type
  (relation graph, configurable data sources). One reader exists today
  (Lieux); the slot declaration is the extension point, nothing more.
- **Converting intra-sheet panels to slots** (relations, knowledge, items,
  memberships, roles, discoverable details — all rendered inside
  `authorRenderSheet`, index.html:4084-4142). The sheet's internals are a
  single unit for now; splitting them waits for a concrete second consumer.
- **Any backend change.** Endpoint heterogeneity (generic entity CRUD vs
  dedicated PJ/skill-definition/ledger routes) is legitimate and stays.
- **Splitting index.html into modules/files** (rejected F2).
- **Any styling redesign** beyond what the standard layout positions
  require.

## Invariants to defend

- **No canon-write path touched**: this is frontend-only; `writes.py`,
  `_apply_mutation`, all CRUD routes, and the schema are untouched. The
  diff must contain no change under `src/world_engine/` outside
  `cockpit/index.html` plus the new verify check.
- **Structural over disciplinary**: after this brief, a page cannot exist
  outside the registry and a tab cannot special-case itself inside the
  dispatcher — enforced by the verify check, not by convention.
- **World scoping (BRIEF-48)**: the world-switch refresh must remain at
  least as thorough as today; the G1 loop strictly widens the reset set,
  never narrows it.

## Done means

- [ ] All ten Création sub-tabs activate correctly via the registry; no
      visual/behavioral regression on NPC, Factions, Objets create/edit
      flows in a live session
- [ ] Lieux shows exactly one create control, `+ Nouveau`, top of sidebar;
      the graph panel still renders and loads for Lieux only
- [ ] Artefacts shows no create control and its list + notice as before
- [ ] Live: open Région, generate a manifest, switch active world → the
      Région tab shows a fresh (empty) state, not the previous world's
      draft; same spot-check for Compétences draft and Lieux breadcrumb
- [ ] Live: PJ tab behaves exactly as before this brief (its migration is
      -b)
- [ ] `verify/checks/page_contract.py` passes; deliberately re-adding the
      string `Ajouter un lieu` or a tab-id literal into
      `showCreationSubTab` makes it fail (negative test, then revert)
- [ ] Full verify suite green; /review-step and /close-step run

## Docs to update

- ARCHITECTURE_DECISIONS.md: new section "CRÉATION PAGE CONTRACT
  (TICKET-0005, briefs a-c)" recording D′2-shell, F1, G1, H1, the registry
  entry contract verbatim, and the graph-as-slot posture (declarable now,
  generalized only on a second concrete reader).
- CLAUDE.md: one standing convention line — "Every Création page is a
  `CREATION_TABS` registry entry rendered by the generic dispatcher; no
  page or tab-specific branch may exist outside the registry
  (`page_contract.py` enforces)."
- No schema change; no changelog entry.
