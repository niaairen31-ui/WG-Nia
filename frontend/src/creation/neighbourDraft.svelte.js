/* TICKET-0101 (BRIEF-0101-E, K). Draft state for a NEW location's
   neighbours: the parent's geographic neighbours the creator ticked, sent
   as the create body's `link_to` (crud/zone_hooks.link_new_location links
   each with the type the server derives). Written by NeighbourPicker.svelte,
   read by Sheet.svelte's submitEntity via neighboursForCreate(), reset with
   the other create drafts. */
export const neighbourDraftState = $state({ ids: [] });

export function resetNeighbourDraft() {
  neighbourDraftState.ids = [];
}

export function toggleNeighbour(id, checked) {
  const others = neighbourDraftState.ids.filter((x) => x !== id);
  neighbourDraftState.ids = checked ? [...others, id] : others;
}

export function neighboursForCreate() {
  return [...neighbourDraftState.ids];
}

/** GET /api/locations/{id}/neighbours -- [{id, name, is_zone}], [] on any
 *  failure (the checkboxes are an offer, never a gate). */
export async function loadNeighbours(locationId) {
  if (!locationId) return [];
  try {
    const res = await fetch(`/api/locations/${encodeURIComponent(locationId)}/neighbours`);
    return res.ok ? await res.json() : [];
  } catch (_err) {
    return [];
  }
}
