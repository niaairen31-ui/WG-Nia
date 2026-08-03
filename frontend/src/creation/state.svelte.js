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
   never written from outside that component). */
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
  // 'empty' | 'loading' | 'view' | 'error' | 'legacy' -- 'create' is a
  // sub-case of 'view' carrying sheetIsNew: true (same skeleton, blank data).
  sheetMode: 'empty',
  sheetDetail: null,
  sheetIsNew: false,
  sheetType: null,
  sheetErrorMessage: '',
});
