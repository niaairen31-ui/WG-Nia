/* TICKET-0059 (BRIEF-0059-l, D1). Creation's chrome: the tab registry, the
   runtime tab factory, the generic tab-switch dispatcher, the shell band's
   data, on-demand slots, cross-tab navigation, pending-creation cards, and
   the world-switch cascade. Everything Creation.svelte's template renders
   or reacts to comes from this module, the same shape sheetState.svelte.js
   already established for Sheet.svelte: the plain, importable module holds
   the logic and the shared state; the component holds the template.

   Ported off index.html's `const CREATION_TABS` literal and the chrome
   function cluster RECON-0059-a M6 catalogued (`showCreationSubTab`,
   `_creationActivateTab`, `renderCreationShell`, `_islandPrimaryAction`,
   `_buildRuntimeCreationTabs`, `refreshCreationTabs`, `creationInit`,
   `creationRefreshList`, the five onTabEnter resets, the on-demand slot
   trio, the navigation cluster, the pending-creation cluster, and
   `activateWorld`), plus their necessary transitive dependencies
   (`_onDemandSlotReset` etc. are not individually named in the brief's
   item lists but are unseverable from what is).

   Three mechanical adaptations, forced by Creation no longer living inside
   the legacy iframe (BRIEF-0059-l item 5's general instruction — do not
   port a cross-document mechanism verbatim once the document boundary is
   gone):

   1. `_islandPrimaryAction`'s 'island:action' CustomEvent dispatch is a
      direct call into mount.js's `triggerPrimaryAction` (no event bus).
   2. Every DOM string-building the legacy version did via
      `insertAdjacentHTML`/`innerHTML` with inline `onclick="fnName(...)"`
      attributes (the runtime tab buttons, the on-demand toggle buttons,
      the pending-creation cards) cannot work once `fnName` is a
      module-scoped import instead of a `window` global — Creation.svelte's
      template renders these declaratively instead (`{#each}` + real event
      bindings), and this module exposes plain data
      (creationState.onDemandSlotState, creationState.pendingCreations) for
      it to bind to, rather than pre-rendered HTML strings.
   3. Container show/hide (`showCreationSubTab`'s `allContainerIds`
      sweep) is a pure function, `containerVisible(id)`, that
      Creation.svelte's template calls per container instead of this
      module writing `style.display` itself — the template owns its own
      DOM.

   `_creationRunWorldSwitchResets` does NOT port: every `onWorldSwitch` in
   CREATION_TABS (14 static entries + the runtime-tab factory's own
   template) is `null` (measured, not assumed — grep `onWorldSwitch:` over
   this file), so its `Object.values(...).forEach` loop is vacuous; its one
   real remaining effect (`creationReturnTo = null`) folds directly into
   `handleWorldChanged` below. `renderCreationShell`/`_renderOnDemandToggles`
   don't port as separate imperative functions either, for the same reason
   as point 3: the shell band's title/primaryAction/toggle buttons are
   template expressions in Creation.svelte now, derived from
   creationState + CREATION_TABS, not a function that writes them once on
   activation.

   This module does NOT `import` from `./mount.js` at the top level, even
   though CREATION_TABS entries need `triggerPrimaryAction`/`activateIsland`:
   mount.js imports every island component (EntityList.svelte, Sheet.svelte,
   ...), and several of those components import navigation functions FROM
   this module (creationSelectRecord, creationOpenEntityFrom,
   creationRefreshList -- the plain Svelte-to-Svelte calls that replaced
   their old legacyCall sites, BRIEF-0059-l commit 1) -- a static top-level
   import cycle (island -> tabs.js -> mount.js -> island). `setMountActions`
   below is wired once from Creation.svelte's own script (which imports both
   modules directly and sits outside the cycle, since nothing imports
   Creation.svelte except App.svelte), the same late-bound-seam shape this
   codebase already uses wherever a static import would otherwise cycle. */
import { creationState } from './state.svelte.js';
import { replace } from '../lib/router.js';

let _triggerPrimaryActionImpl = null;
let _activateIslandImpl = null;

/** Wires this module's two mount.js dependencies -- called once from
 *  Creation.svelte's own script, before any tab can activate or any
 *  primaryAction button can be clicked. */
export function setMountActions({ triggerPrimaryAction, activateIsland }) {
  _triggerPrimaryActionImpl = triggerPrimaryAction;
  _activateIslandImpl = activateIsland;
}

function triggerPrimaryAction(key) {
  if (_triggerPrimaryActionImpl) _triggerPrimaryActionImpl(key);
}

/** HTML-escape a value (null/undefined -> empty string) -- local copy,
 *  matching every other Creation island's own convention (no shared
 *  helper module; see Constructeur.svelte's identical local `api`). */
function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = `${path} -> ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') msg = body.detail;
    } catch (_err) {
      // response body wasn't JSON -- keep the status-based message
    }
    throw new Error(msg);
  }
  return res.json();
}

// CREATION_TABS entry contract (TICKET-0005):
// { label:        string, tab title shown in the shell header
//   archetype:    'entity' | 'bespoke'
//   containers:   [element ids to show when active; all others hidden]
//   loader:       function called on activation
//   state:        { onTabEnter: fn|null, onWorldSwitch: fn|null }
//                 each fn resets ALL state this tab owns for that event
//   // entity archetype only:
//   listLoader:   fn|undefined -- ONLY for a tab whose list isn't the
//                 default flat/lieux shape the entityList island already
//                 renders (Intrigues/Evenements): fetches and caches rows,
//                 then hands them to the island via 'creation:list-data'
//                 (TICKET-0058, BRIEF-0058-e). Absent on every tab the
//                 island renders generically off `type`/`entityFilter`.
//   sheetRenderer: fn|undefined (undefined = the entitySheet island's own
//                 core field engine, Sheet.svelte, BRIEF-0058-f; present =
//                 a bespoke legacy renderer for a tab whose record isn't a
//                 plain typed entity -- rendering into
//                 #author-legacy-sheet-slot, the island's stable leaf)
//   createPanel:  fn|null (null with primaryAction routed through
//                 triggerPrimaryAction('entitySheet') = the island's own
//                 create mode; non-null = a bespoke legacy create panel,
//                 same #author-legacy-sheet-slot target -- rule 11 pairs
//                 this with primaryAction, never mixed)
//   slots:        [{ id, containerId, loader, onSelect: fn|null,
//                    onOpen: fn|null (on_demand only; fires once, right
//                    before the first loader/graph:slot dispatch),
//                    display: 'always'|'on_demand' (default 'always'),
//                    toggleLabel: string (on_demand only; default
//                    'Voir le graphe'),
//                    graph: { consumer: string, mountId: string|undefined }
//                    (TICKET-0057/0058) -- a shell-mounted graph island;
//                    mountId defaults to containerId (lieux) but may name a
//                    narrower child element (npc) when containerId also
//                    hosts other, non-graph chrome that must survive the
//                    graph's own mount/remount cycle untouched }]
//                 'on_demand' (BRIEF-0023-a, F1): container stays hidden and
//                 loader does not fire on tab activation; the standard shell
//                 renders one toggle button per on_demand slot; first click
//                 shows the container and fires loader, later clicks only
//                 hide/show (no unload); state resets via onTabEnter/
//                 onWorldSwitch.
//   islands:      [{ key, containerId }, ...] | undefined -- each entry a
//                 mount point inside this tab whose content is a Svelte
//                 island (TICKET-0058, amended BRIEF-0058-e). Creation.svelte
//                 mounts it directly (mountIsland, frontend/src/creation/
//                 mount.js) -- ordinary same-document function calls now,
//                 not a cross-document dispatch. Declared in
//                 frontend/src/creation/registry.js. A registry key may be
//                 shared by MULTIPLE entries when one component serves
//                 several tabs through one container (the entity-list
//                 sidebar does, across all seven entity tabs) --
//                 many-to-many, never a second renderer for the same node.
//                 An entry declaring a non-empty `islands` MUST also
//                 declare loader: null and state.onWorldSwitch: null. A
//                 legacy loader or world-switch renderer targeting an
//                 island's OWN containerId would innerHTML over it
//                 (RECON-0058-a M5); that state's reset is driven by
//                 serverState in the mounted component, not a legacy
//                 callback. A tab may be island for ONE containerId and
//                 legacy for another (e.g. the list migrated, the sheet
//                 not yet) -- `islands` and a legacy `createPanel`/
//                 `listRenderer` are not mutually exclusive; only
//                 `primaryAction` and `createPanel` must stay paired on
//                 the same side (creation_island.py rule 11).
// }
// Every Création page is a registry entry. No page renders outside it.

export const CREATION_TABS = {
  npc: {
    label: 'NPC',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _npcTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }, { key: 'npcAgent', containerId: 'npcagent-panel' }, { key: 'linkAgent', containerId: 'linkagent-panel' }],
    type: 'character',
    entityFilter: (entities) => entities.filter(e => e.type === 'character' && !creationState.playerCharIds.has(e.id)),
    createPanel: null,
    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
    showPendingCreations: true,
    slots: [{ id: 'relgraph', containerId: 'creation-npc-relgraph', loader: null,
              onSelect: (id) => document.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'relations', meta: { id } } })),
              onOpen: null,
              display: 'on_demand', toggleLabel: 'Voir le graphe',
              graph: { consumer: 'relations', mountId: 'relgraph-mount' } }],
  },
  pj: {
    label: 'Personnages joueurs',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _entityTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }, { key: 'pjSkillFiche', containerId: 'creation-pj-skill' }],
    type: 'character',
    entityFilter: (entities) => entities.filter(e => e.type === 'character' && creationState.playerCharIds.has(e.id)),
    createPanel: null,
    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
    slots: [{ id: 'fiche', containerId: 'creation-pj-skill', loader: null, onSelect: null }],
  },
  lieux: {
    label: 'Lieux',
    archetype: 'entity',
    containers: ['creation-editor-area', 'batch-panel-wrap'],
    loader: null,
    state: { onTabEnter: () => _lieuxTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }, { key: 'batch', containerId: 'batch-panel-wrap' }],
    type: 'location',
    createPanel: null,
    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
    showPendingCreations: true,
    slots: [{ id: 'graph', containerId: 'creation-lieux-graph', loader: null, onSelect: null,
              display: 'on_demand', toggleLabel: 'Voir le graphe',
              graph: { consumer: 'lieux' } }],
  },
  factions: {
    label: 'Factions',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _entityTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
    type: 'faction',
    createPanel: null,
    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
    showPendingCreations: true,
    slots: [],
  },
  objets: {
    label: 'Objets',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _entityTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
    type: 'item',
    createPanel: null,
    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
    slots: [],
  },
  competences: {
    label: 'Compétences',
    archetype: 'bespoke',
    containers: ['creation-competences'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'competences', containerId: 'creation-competences' }],
    primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('competences') },
  },
  region: {
    label: 'Région',
    archetype: 'bespoke',
    containers: ['creation-region'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'region', containerId: 'creation-region' }],
    primaryAction: { label: 'Nouvelle région', handler: () => triggerPrimaryAction('region') },
  },
  constructeur: {
    label: 'Constructeur',
    archetype: 'bespoke',
    containers: ['creation-constructeur'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'constructeur', containerId: 'creation-constructeur' }],
    primaryAction: { label: 'Créer le type', handler: () => triggerPrimaryAction('constructeur') },
  },
  artefacts: {
    label: 'Artefacts',
    archetype: 'entity', // degenerate: no create control, own container/loader (BRIEF-0005-a item 7)
    containers: ['creation-artefacts'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'artefacts', containerId: 'creation-artefacts' }],
    createPanel: null,
    primaryAction: null, // enabling artifact creation later = filling this in
  },
  registre: {
    label: 'Registre',
    archetype: 'bespoke',
    containers: ['creation-registre'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'registre', containerId: 'creation-registre' }],
    primaryAction: { label: '+ Nouvelle entrée', handler: () => triggerPrimaryAction('registre') },
  },
  intrigues: {
    label: 'Intrigues',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _intriguesTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
    listLoader: null,
    sheetRenderer: null,
    createPanel: null,
    primaryAction: { label: '+ Nouvelle intrigue', handler: () => triggerPrimaryAction('entitySheet') },
  },
  evenements: {
    label: 'Événements',
    archetype: 'entity',
    containers: ['creation-editor-area'],
    loader: null,
    state: { onTabEnter: () => _evenementsTabEnterReset(), onWorldSwitch: null },
    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
    createPanel: null,
    primaryAction: { label: '+ Nouvel événement', handler: () => triggerPrimaryAction('entitySheet') },
  },
  queue: {
    label: 'Review Queue',
    archetype: 'bespoke',
    containers: ['creation-queue'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    primaryAction: null, // append-only by design -- rows never created here
    slots: [
      { id: 'filters', containerId: 'creation-shell-extra', loader: null, onSelect: null },
      { id: 'batchBar', containerId: 'creation-shell-batch-bar', loader: null, onSelect: null },
    ],
    islands: [
      { key: 'queueFilters', containerId: 'creation-shell-extra' },
      { key: 'queue', containerId: 'creation-queue' },
      { key: 'queueBatchBar', containerId: 'creation-shell-batch-bar' },
    ],
  },
  prompts: {
    label: 'Prompts',
    archetype: 'bespoke',
    containers: ['creation-prompts'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'prompts', containerId: 'creation-prompts' }],
    primaryAction: null, // read-only, creator management surface (BRIEF-0008-b)
  },
};

/* ── On-demand slots (BRIEF-0023-a, F1) ─────────────────────────────────── */

export function onDemandSlotReset(entry) {
  (entry.slots || []).forEach(s => {
    if (s.display !== 'on_demand') return;
    creationState.onDemandSlotState[s.containerId] = { open: false, loaded: false };
  });
}

export function onDemandSlotToggle(slot) {
  const st = creationState.onDemandSlotState[slot.containerId]
    || (creationState.onDemandSlotState[slot.containerId] = { open: false, loaded: false });
  st.open = !st.open;
  if (st.open && !st.loaded) {
    st.loaded = true;
    if (slot.onOpen) slot.onOpen();
    if (slot.graph) {
      // TICKET-0057/0058: the graph primitive is a shell-mounted island;
      // this module only signals intent, it never loads or draws.
      document.dispatchEvent(new CustomEvent('graph:slot', {
        detail: { consumer: slot.graph.consumer, containerId: slot.graph.mountId || slot.containerId, open: true },
      }));
    } else if (slot.loader) {
      slot.loader();
    }
  }
}

/** True iff `id` should be visible under the currently active tab --
 *  Creation.svelte's template calls this per container instead of this
 *  module writing style.display itself (point 3, header comment). */
export function containerVisible(id) {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (!entry) return false;
  if (entry.containers.includes(id)) return true;
  const slot = (entry.slots || []).find(s => s.containerId === id);
  if (!slot) return false;
  if (slot.display === 'on_demand') {
    return !!creationState.onDemandSlotState[id]?.open;
  }
  return true;
}

/* ── Tab-enter resets ────────────────────────────────────────────────────── */

function _entityTabEnterReset() {
  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
  document.dispatchEvent(new CustomEvent('creation:sheet-reset'));
}

function _lieuxTabEnterReset() {
  _entityTabEnterReset();
  onDemandSlotReset(CREATION_TABS.lieux);
  document.dispatchEvent(new CustomEvent('creation:batch-reset'));
}

function _npcTabEnterReset() {
  _entityTabEnterReset();
  onDemandSlotReset(CREATION_TABS.npc);
  document.dispatchEvent(new CustomEvent('creation:npcagent-reset'));
  document.dispatchEvent(new CustomEvent('creation:linkagent-reset'));
}

function _intriguesTabEnterReset() {
  creationState.selectedRecordId = null;
  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
  document.dispatchEvent(new CustomEvent('creation:sheet-reset'));
}

function _evenementsTabEnterReset() {
  creationState.selectedRecordId = null;
  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
  document.dispatchEvent(new CustomEvent('creation:sheet-reset'));
}

/* ── Generic dispatcher (TICKET-0005) ───────────────────────────────────── */

/** Dispatches every 'islands' entry the currently active tab declares, plus
 *  (for an editor-shell entity tab not yet fully islanded off its own
 *  listLoader -- Intrigues/Evenements) the legacy list fetch. Extracted so
 *  the sidebar's own "↻ Rafraîchir" button can re-run exactly this -- a
 *  shape check on the entry's own data, never a tab-id branch. */
export function creationRefreshList() {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (!entry) return;
  (entry.islands || []).forEach(isl => activateIslandFor(isl.key));
  if (entry.listLoader) entry.listLoader();
}

// Local wrapper passing the current tab key every time (mount.js's own
// activateIsland signature takes it as a second argument, exactly
// mirroring the old 'island:slot' detail).
function activateIslandFor(key) {
  if (_activateIslandImpl) _activateIslandImpl(key, creationState.activeTabKey);
}

function _creationActivateTab() {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (!entry) return;
  creationRefreshList();
  if (entry.loader) entry.loader();
  (entry.slots || []).forEach(s => { if (s.display !== 'on_demand' && s.loader) s.loader(); });
  if (entry.showPendingCreations) {
    loadPendingCreations();
  } else {
    creationState.pendingCreations = [];
  }
}

/** Generic dispatcher (TICKET-0005): every tab's visibility, reset, and load
 *  behavior comes from its CREATION_TABS entry -- no tab-id literals here. */
export function showCreationSubTab(tab) {
  const prev = creationState.activeTabKey;
  const entry = CREATION_TABS[tab];
  if (!entry) return;
  creationState.activeTabKey = tab;
  // Any tab change drops the crumb; creationOpenEntityFrom/
  // creationReturnToOrigin re-set it AFTER calling this, which is what
  // makes a manual sub-tab click clear it and a programmatic navigation
  // keep it.
  creationState.creationReturnTo = null;

  if (prev !== tab && entry.state.onTabEnter) entry.state.onTabEnter();

  if (!creationState.authorRegistry) {
    creationInit();
  } else {
    _creationActivateTab();
  }

  // TICKET-0058 (BRIEF-0058-k)'s continuous URL sync, direct now: no
  // cross-document 'route:subtab' dispatch needed once Creation and the
  // shell are the same document (replace() never pushes/dispatches
  // popstate, so this cannot re-enter applyRoute).
  replace('creation', tab);
}

/* ── Création bootstrap ─────────────────────────────────────────────────── */

export async function creationInit() {
  try {
    creationState.authorRegistry = await api('/api/entity-types');
  } catch (e) {
    console.error('creationInit:', e.message);
    return;
  }
  buildRuntimeCreationTabs(creationState.authorRegistry);
  _creationActivateTab();
}

/* ── Runtime Creation tabs -- dynamic tab factory (TICKET-0046, BRIEF-0046-d) ──
 * The single producer of runtime (custom entity-type) Creation tabs: reads
 * authorRegistry.runtime_types (world-scoped, from GET /api/entity-types) and
 * injects one entity-archetype CREATION_TABS entry per active runtime type.
 * Idempotent and world-scoped: a slug previously injected but no longer
 * live (retired type, or a world switch) is removed via the tracked
 * _runtimeCreationSlugs set -- static entries are never touched.
 * creationState.tabsVersion is bumped so Creation.svelte's tab-bar
 * `{#each}` (which cannot see into this plain mutable object on its own)
 * recomputes. */
let _runtimeCreationSlugs = new Set();

export function buildRuntimeCreationTabs(authorRegistry) {
  const liveSlugs = new Set((authorRegistry && authorRegistry.runtime_types) || []);

  for (const slug of Array.from(_runtimeCreationSlugs)) {
    if (liveSlugs.has(slug)) continue;
    delete CREATION_TABS[slug];
    _runtimeCreationSlugs.delete(slug);
  }

  for (const slug of liveSlugs) {
    const typeInfo = (authorRegistry.types && authorRegistry.types[slug]) || { label: slug };
    if (!CREATION_TABS[slug]) {
      CREATION_TABS[slug] = {
        label: typeInfo.label,
        archetype: 'entity',
        containers: ['creation-editor-area'],
        loader: null,
        state: { onTabEnter: () => _entityTabEnterReset(), onWorldSwitch: null },
        islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
        type: slug,
        createPanel: null,
        primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
        slots: [],
      };
    }
    _runtimeCreationSlugs.add(slug);
  }
  creationState.tabsVersion += 1;
}

/** Re-fetches authorRegistry then rebuilds runtime tabs -- the hook 0046-c
 *  calls after a successful type create; also run on world switch via
 *  handleWorldChanged(). */
export async function refreshCreationTabs() {
  creationState.authorRegistry = await api('/api/entity-types');
  buildRuntimeCreationTabs(creationState.authorRegistry);
}

/** BRIEF-0058-j: only pj/intrigues could still reach this -- every current
 *  entry's createPanel is null (rule 11 pairing), so this is presently
 *  unreachable, kept for a future bespoke createPanel exactly as it was in
 *  index.html (RECON-0059-a M6 chrome inventory names it; not dead code by
 *  intent, dead by current data). */
export function creationNewEntity() {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (!entry || !entry.createPanel) return;
  document.dispatchEvent(new CustomEvent('creation:sheet-legacy-active'));
  document.dispatchEvent(new CustomEvent('creation:reset-create-drafts'));
  entry.createPanel();
}

/* ── Cross-tab navigation (TICKET-0054, decision F2a) ───────────────────── */

/** Resolves the sub-tab that owns an entity. npc and pj both declare type
 *  'character'; playerCharIds is the only discriminator the registry
 *  exposes, so this pair is resolved by name here rather than by a
 *  registry lookup. Every other type resolves through the registry -- no
 *  other tab id is hardcoded. */
export function creationResolveEntityTab(entityId, entityType) {
  if (entityType === 'character') {
    return creationState.playerCharIds.has(entityId) ? 'pj' : 'npc';
  }
  const found = Object.entries(CREATION_TABS).find(
    ([, entry]) => entry.archetype === 'entity' && entry.type === entityType
  );
  return found ? found[0] : null;
}

/** Cross-tab entity navigation -- opens an entity's real, editable sheet in
 *  its own sub-tab, leaving a single-slot return crumb. Fail-closed: aborts
 *  leaving no crumb if the target tab never actually activated
 *  (showCreationSubTab can early-return into creationInit() when the
 *  registry isn't loaded yet). */
export async function creationOpenEntityFrom(entityId, entityType) {
  const tab = creationResolveEntityTab(entityId, entityType);
  if (!tab) {
    // #author-status is chrome markup (Creation.svelte's own template,
    // shared with Sheet.svelte's own status writes into the same node) --
    // a direct DOM write here matches how Sheet.svelte already uses it,
    // not a creationState field (sheetErrorMessage is Sheet.svelte's own
    // exclusively, per state.svelte.js's header comment).
    const statusEl = document.getElementById('author-status');
    if (statusEl) {
      statusEl.className = 'author-status err';
      statusEl.textContent = "Aucun onglet ne gère ce type d'entité.";
    }
    return;
  }
  const origin = creationState.selectedEntityId
    ? { tabId: creationState.activeTabKey, entityId: creationState.selectedEntityId }
    : null;
  showCreationSubTab(tab);
  if (creationState.activeTabKey !== tab) return;
  creationState.creationReturnTo = origin;
  document.dispatchEvent(new CustomEvent('creation:select-entity', { detail: { id: entityId } }));
}

/** Consumes the return crumb -- landing back on the origin tab clears the
 *  crumb via showCreationSubTab, which is correct: returning consumes it. */
export async function creationReturnToOrigin() {
  const back = creationState.creationReturnTo;
  if (!back) return;
  showCreationSubTab(back.tabId);
  if (creationState.activeTabKey !== back.tabId) return;
  document.dispatchEvent(new CustomEvent('creation:select-entity', { detail: { id: back.entityId } }));
}

/** Generic record selection (BRIEF-0021-a): the sheetRenderer-seam
 *  counterpart of sheetState.svelte.js's selectEntity for non-entity
 *  list+detail tabs whose rows already carry full data -- no per-row
 *  fetch. A registered caller either declares a bespoke sheetRenderer
 *  (none currently do) or doesn't, in which case this dispatches
 *  'creation:record-detail' for Sheet.svelte to render natively. */
export function creationSelectRecord(tabId, record) {
  const entry = CREATION_TABS[tabId];
  if (!entry) return;
  creationState.selectedRecordId = record.id;
  if (entry.sheetRenderer) {
    document.dispatchEvent(new CustomEvent('creation:sheet-legacy-active'));
    entry.sheetRenderer(record);
  } else {
    document.dispatchEvent(new CustomEvent('creation:record-detail', { detail: { record, tabId } }));
  }
  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: record.id } }));
}

/** Generic save-button dispatch: the persistent header Save button is
 *  shared by every archetype:'entity' tab; a registry entry may declare
 *  its own `saveHandler` -- every current entry falls through to the
 *  mounted entitySheet island's own save. */
export function creationSaveDispatch() {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (entry && entry.saveHandler) { entry.saveHandler(); return; }
  document.dispatchEvent(new CustomEvent('creation:sheet-save'));
}

/* ── Créations en attente (TICKET-0019, BRIEF-0019-a) ───────────────────── */

export async function loadPendingCreations() {
  const entry = CREATION_TABS[creationState.activeTabKey];
  if (!entry || !entry.type) {
    creationState.pendingCreations = [];
    return;
  }
  creationState.pendingCreationsLoading = true;
  creationState.pendingCreationsError = '';
  let items;
  try {
    items = await api('/api/creations/pending');
  } catch (e) {
    creationState.pendingCreationsLoading = false;
    creationState.pendingCreationsError = e.message;
    return;
  }
  // A germ with no valid entity_type has no home tab -- shown everywhere,
  // visible-not-realizable (RECON F6), rather than silently dropped.
  creationState.pendingCreations = items.filter(it => it.entity_type === entry.type || !it.entity_type);
  creationState.pendingCreationsLoading = false;
}

export async function generatePendingCreation(mutationId) {
  let result;
  try {
    result = await api(`/api/creations/${encodeURIComponent(mutationId)}/generate`, { method: 'POST' });
  } catch (e) {
    alert(e.message);
    return;
  }
  if (!result || result.ok === false) {
    alert((result && result.error) || 'Échec de la génération.');
    return;
  }
  document.dispatchEvent(new CustomEvent('creation:sheet-create', { detail: { type: result.entity_type, mutationId } }));
  document.dispatchEvent(new CustomEvent('creation:apply-generated-draft', {
    detail: { entityType: result.entity_type, result },
  }));
}

/* ── World-switch cascade (TICKET-0056 C3, moved here per BRIEF-0059-l) ──
 * Header.svelte's onWorldChange calls activateWorldCascade directly now
 * (TICKET-0056's own Header.svelte comment: "When Creation migrates
 * [...] the cascade moves WITH it"). handleWorldChanged is the shared tail
 * -- also called by the legacy-side world-delete reverse-bridge listener
 * (initCreationChrome below) until worldDeleteConfirm itself ports
 * (BRIEF-0059-l commit 3). */
export async function handleWorldChanged() {
  creationState.creationReturnTo = null;
  if (creationState.authorRegistry) {
    await refreshCreationTabs();
    showCreationSubTab(CREATION_TABS[creationState.activeTabKey] ? creationState.activeTabKey : 'npc');
  } else {
    await creationInit();
  }
}

export async function activateWorldCascade(worldId, refreshServerState) {
  let activated = false;
  try {
    const res = await api(`/api/worlds/${worldId}/activate`, { method: 'POST' });
    if (res.ok) {
      activated = true;
    } else {
      alert(`Échec de l'activation du monde : ${res.error}`);
    }
  } catch (err) {
    alert(`Échec de l'activation du monde : ${err.message}`);
  }
  await refreshServerState();
  if (!activated) return;
  await handleWorldChanged();
}

/* ── Chrome-level document listeners, registered once ───────────────────── */

let _chromeInitialized = false;

/** Registers every listener this module's chrome owns on the SHELL's own
 *  document -- no legacy dependency, safe to call as soon as Creation.svelte
 *  mounts (which happens at app boot, independent of the legacy iframe's
 *  own load timing). Called once from Creation.svelte's onMount. */
export function initCreationChrome() {
  if (_chromeInitialized) return;
  _chromeInitialized = true;

  // Mirrors selection changes into the active tab's own slots (e.g. npc's
  // relgraph slot invalidating the relations graph so ego mode re-centres).
  document.addEventListener('creation:selection', (ev) => {
    const entityId = ev.detail.entityId ?? null;
    if (entityId == null) return;
    const entry = CREATION_TABS[creationState.activeTabKey];
    (entry ? entry.slots || [] : []).forEach(s => { if (s.onSelect) s.onSelect(entityId); });
  });

  // Constructeur.svelte dispatches this on itself after a successful
  // runtime-type create -- same document now, no longer a cross-document
  // signal, but the event-based seam stays (Constructeur.svelte is not a
  // target file of this brief).
  document.addEventListener('creation:refresh-tabs', () => {
    refreshCreationTabs();
  });

  // NpcAgent.svelte/LinkAgent.svelte dispatch these on themselves for the
  // launcher badge dot, which lives in Creation.svelte's own chrome
  // (outside either island's own mount root).
  document.addEventListener('creation:npcagent-badge', (ev) => {
    creationState.npcAgentBadgeOpen = !!ev.detail.open;
  });
  document.addEventListener('creation:linkagent-badge', (ev) => {
    creationState.linkAgentBadgeOpen = !!ev.detail.open;
  });
}

// TICKET-0059 (BRIEF-0059-l commit 3). initWorldChangeBridge/the
// 'creation:world-changed' reverse-bridge listener are gone: they existed
// only to reach handleWorldChanged from the still-legacy worldDeleteConfirm
// (commit 1's own comment named this exact retirement condition).
// worldDeleteConfirm is Svelte now (frontend/src/creation/worldCrud.svelte.js)
// and calls handleWorldChanged directly, a plain import, no bridge needed.

export { esc };
