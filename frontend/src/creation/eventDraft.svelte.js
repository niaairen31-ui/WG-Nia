/* TICKET-0058 (BRIEF-0058-j). Shared involved_entities chip-editor draft
   for the Événements sheet -- was the evenementsInvolvedDraft global
   (index.html, now deleted). A module-level store, not Evenements.svelte-
   local state, for the same reason generatePanelState is module-level
   (generatePanel.svelte.js): Sheet.svelte's header/save code needs to read
   and reset it too, and a plain <Evenements> instance does not remount on
   every selection change (it renders the same component, new props). */
export const eventDraftState = $state({ involved: [] }); // [{id, name}]

export function resetEventDraft() {
  eventDraftState.involved = [];
}

export function setEventDraftFromEvent(event) {
  eventDraftState.involved = (event.involved_entities || []).map((c) => ({ id: c.id, name: c.name }));
}

/** Prefill from the AI draft-generate response, which carries a flat id
 *  list (not {id, name} pairs) -- resolved against the already-loaded
 *  entity list, same as the legacy evenementsGenerateDraft did. */
export function setEventDraftFromIds(ids, entities) {
  eventDraftState.involved = (ids || []).map((id) => {
    const entity = entities.find((e) => e.id === id);
    return { id, name: entity ? entity.name : null };
  });
}

export function addEventChip(entity) {
  if (eventDraftState.involved.some((c) => c.id === entity.id)) return;
  eventDraftState.involved.push({ id: entity.id, name: entity.name });
}

export function removeEventChip(i) {
  eventDraftState.involved.splice(i, 1);
}
