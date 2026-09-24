/* TICKET-0091 (BRIEF-0091-F). Shared draft state for a NEW entity's
   descriptive facts -- the `facets` payload of the create body (C-05's
   write_entity_facets shape): a bloc facet is a string, an affirmation facet
   a list of strings, `coutume` a list of {aspect, content, hidden}, and
   `creator_meta` (generator-only) a string. Written by FactsEditor.svelte in
   create mode and by generatePanel.svelte.js's draft apply; read by
   Sheet.svelte's submitEntity via factsDraftForCreate() -- the server writes
   the facts in the entity's own create transaction. */
export const factsDraftState = $state({ facets: {} });

export function resetFactsDraft() {
  factsDraftState.facets = {};
}

/** The create body's `facets`: empty strings, blank lines and blank coutume
 *  entries dropped, so the server receives only what the creator wrote. */
export function factsDraftForCreate() {
  const out = {};
  for (const [name, value] of Object.entries(factsDraftState.facets)) {
    if (typeof value === 'string') {
      if (value.trim()) out[name] = value;
    } else if (name === 'coutume') {
      const rows = (value || [])
        .filter((r) => (r.content || '').trim())
        .map((r) => ({ aspect: (r.aspect || '').trim() || null, content: r.content, hidden: !!r.hidden }));
      if (rows.length) out[name] = rows;
    } else {
      const lines = (value || []).filter((l) => typeof l === 'string' && l.trim());
      if (lines.length) out[name] = lines;
    }
  }
  return out;
}
