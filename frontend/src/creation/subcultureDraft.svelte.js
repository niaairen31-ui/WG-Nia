/* TICKET-0058 (BRIEF-0058-g, family c). Shared draft state for a NEW
   location's subculture rows -- was the authorLocationSubcultureDraft
   global (index.html, now deleted). Read directly by Sheet.svelte's
   submitEntity via subcultureDraftForCreate() at creation time, same as
   factionPanel.svelte.js's draftRoles does for a new faction's roles. */
export const subcultureDraftState = $state({ rows: [] });

export function resetSubcultureDraft() {
  subcultureDraftState.rows = [];
}

export function subcultureDraftForCreate() {
  return subcultureDraftState.rows.filter((r) => (r.key || '').trim());
}
