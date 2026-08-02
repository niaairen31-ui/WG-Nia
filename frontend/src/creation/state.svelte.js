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
   EntityList.svelte (BRIEF-0058-e); a future brief mounting a second
   island onto this container (the sheet, brief -f) reads the same store
   rather than inventing one. */
export const creationState = $state({
  activeTabKey: null,
  entityListActivationTick: 0,
  entities: [],
  playerCharIds: new Set(),
  locationTree: [],
  agendas: [],
  events: [],
  selectedEntityId: null,
  selectedRecordId: null,
});
