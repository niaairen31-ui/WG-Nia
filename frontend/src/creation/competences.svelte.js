/* TICKET-0059 (BRIEF-0059-h commit 3). Non-render state + API calls for the
   Compétences tab -- faithful port of _competencesWorldReset/
   competencesGenerateDraft/_competencesDomainOptions/competencesRenderDraft/
   competencesDiscardDraftRow/competencesAcceptDraftRow/
   competencesAddManualRow/competencesLoadList/_competencesRenderTable/
   competencesSaveRow (index.html, now deleted). AI draft proposes
   {name, base_domain, description}; the creator accepts each row
   individually (creator-CRUD POST), never a bulk silent write -- Model
   proposes, code judges.

   competencesDeleteOpen/competencesDeleteConfirm are NOT here: the delete
   confirmation is a dialog (Modal.svelte, lock O1), and a plain module
   cannot own dialog state (same rule locationType.js's own split follows,
   commit 1) -- that state lives in Competences.svelte itself. */
export const competencesState = $state({
  draft: [],   // AI-proposed rows awaiting individual accept/discard
  rows: [],    // existing world-scoped skill_definition rows
  loading: true,
  loadError: '',
});

export const COMPETENCES_DOMAINS = ['physical', 'agility', 'perception', 'composure'];

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export function resetCompetences() {
  competencesState.draft = [];
}

export function addManualRow() {
  competencesState.draft.push({ name: '', base_domain: 'physical', description: '' });
}

export function discardDraftRow(i) {
  competencesState.draft.splice(i, 1);
}

/** Returns {ok, error} | {ok:true, notes} -- the draft itself lands in
 *  competencesState.draft directly, same shape competencesRenderDraft's
 *  caller relied on. */
export async function generateDraft(brief) {
  const result = await api('/api/skill-definitions/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ brief }),
  });
  if (!result.ok) return { ok: false, error: result.error };
  competencesState.draft = result.draft.skills || [];
  return { ok: true, notes: result.notes || [] };
}

export async function acceptDraftRow(i) {
  const row = competencesState.draft[i];
  await api('/api/skill-definitions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: row.name.trim(),
      base_domain: row.base_domain,
      description: row.description || '',
    }),
  });
  competencesState.draft.splice(i, 1);
  await loadList();
}

export async function loadList() {
  competencesState.loading = true;
  competencesState.loadError = '';
  try {
    competencesState.rows = await api('/api/skill-definitions');
  } catch (e) {
    competencesState.loadError = e.message;
  } finally {
    competencesState.loading = false;
  }
}

export async function saveRow(id, name, base_domain, description) {
  await api(`/api/skill-definitions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, base_domain, description }),
  });
}

/** D2-delete-cascade: dependent PC `skill` rows then the definition, in one
 *  transaction. No separate history snapshot (locked decision). */
export async function deleteDefinition(id) {
  await api(`/api/skill-definitions/${id}`, { method: 'DELETE' });
  await loadList();
}
