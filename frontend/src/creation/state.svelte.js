/* TICKET-0058 (BRIEF-0058-e). The Creation store -- a MIRROR of what the
   legacy document already decides about the active tab and selection,
   never a second authority. Legacy pushes updates via CustomEvents
   ('creation:selection' and 'creation:list-data', listened for directly by
   EntityList.svelte); nothing in this store is written from a Svelte
   effect guessing at legacy state.

   activeTabKey/entityListActivationTick are set by mount.js's 'island:slot'
   listener, not by EntityList.svelte itself: creation_island.py rule 8
   confines that event's listener to mount.js alone, so the component
   reacts to these two fields instead of the raw event. tick increments on
   EVERY 'entityList' activation (mount.js's own mount is a no-op on a
   repeat dispatch into the same live node, but the component still needs
   to refetch each time, matching authorLoadEntityList's old per-activation
   cadence) -- activeTabKey alone wouldn't change on e.g. npc -> pj -> npc.

   Every field here has a named reader in this ticket's commits (E2):
   activeTabKey/entityListActivationTick/selectedEntityId/selectedRecordId/
   entities/playerCharIds/locationTree/agendas/events are all read by
   EntityList.svelte (BRIEF-0058-e); Sheet.svelte (BRIEF-0058-f) reads the
   same store rather than inventing a second one -- entities/playerCharIds/
   locationTypeCatalog feed entity_ref/location_type field candidates,
   activeTabKey resolves the create-mode type.

   BRIEF-0058-f additions: locationTypeCatalog (EntityList's own
   /api/location-types fetch, mirrored here the same way entities/
   locationTree already are, so Field.svelte doesn't need a second fetch)
   and the sheetMode/sheetDetail/sheetIsNew/sheetType/sheetErrorMessage
   quintet, which Sheet.svelte owns exclusively (set by its own
   'creation:sheet-*' listeners and its exported primaryAction/saveSheet,
   never written from outside that component).

   TICKET-0059 (BRIEF-0059-l commit 1) additions, now that Creation.svelte
   drives the chrome directly instead of index.html: tabsVersion (bumped by
   tabs.js's refreshCreationTabs/_buildRuntimeCreationTabs so the tab bar's
   {#each} — reading CREATION_TABS, a plain mutable object this store
   cannot see into on its own — recomputes on a runtime type's arrival or
   departure) and onDemandSlotState (BRIEF-0023-a's per on_demand-slot
   open/loaded map, moved off the legacy `let onDemandSlotState = {}`
   module global so Creation.svelte's shell-band toggles react to it). Both
   read AND written from tabs.js as well as Creation.svelte -- mutating a
   nested property of this $state root still notifies regardless of which
   module performs the write, the same guarantee factionPanelState and
   subcultureDraftState already rely on.

   Also added: authorRegistry (the legacy `let authorRegistry` module
   global, now the one copy -- GET /api/entity-types response, read by
   tabs.js's whole chrome cluster and by the legacy-side world-delete
   reverse-bridge listener), creationReturnTo (the legacy `let
   creationReturnTo` module global -- the single-slot return-crumb {tabId,
   entityId} | null), and npcAgentBadgeOpen/linkAgentBadgeOpen (mirrors of
   the 'creation:npcagent-badge'/'creation:linkagent-badge' events
   NpcAgent.svelte/LinkAgent.svelte dispatch on themselves -- Creation.svelte's
   template binds the two launcher badges to these instead of an imperative
   getElementById toggle, now that the badge markup is its own).

   npcAgentOpen/linkAgentOpen (BRIEF-0059-l amendment, the legacyContainer
   exposure): the two NPC-panel launcher toggle booleans, ported into
   Creation.svelte's chrome (npcAgentToggle/linkAgentToggle) alongside the
   #npcagent-panel/#linkagent-panel markup they show/hide -- moved onto
   this shared store rather than kept Creation.svelte-local specifically so
   npcAgent.svelte.js's generateLinks() can request the link agent panel
   open (`if (!creationState.linkAgentOpen) creationState.linkAgentOpen =
   true;`) as ordinary parent-owned state, never reaching into a sibling
   component's internals or reintroducing an event bus.

   pendingCreations/pendingCreationsLoading/pendingCreationsError: the
   Créations en attente strip's data (loadPendingCreations, tabs.js),
   rendered by Creation.svelte's own {#each} instead of the legacy
   renderPendingCreationCard HTML-string generator. */
export const creationState = $state({
  activeTabKey: null,
  entityListActivationTick: 0,
  entities: [],
  playerCharIds: new Set(),
  locationTree: [],
  locationTypeCatalog: [],
  agendas: [],
  events: [],
  selectedEntityId: null,
  selectedRecordId: null,
  pendingCreations: [],
  pendingCreationsLoading: false,
  pendingCreationsError: '',
  // 'empty' | 'loading' | 'view' | 'error' | 'legacy' -- 'create' is a
  // sub-case of 'view' carrying sheetIsNew: true (same skeleton, blank data).
  sheetMode: 'empty',
  sheetDetail: null,
  sheetIsNew: false,
  sheetType: null,
  sheetErrorMessage: '',
  npcAgentOpen: false,
  linkAgentOpen: false,
  tabsVersion: 0,
  onDemandSlotState: {},
  authorRegistry: null,
  creationReturnTo: null,
  npcAgentBadgeOpen: false,
  linkAgentBadgeOpen: false,
});
