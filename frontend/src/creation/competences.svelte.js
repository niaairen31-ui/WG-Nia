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
   commit 1) -- that state lives in Competences.svelte itself.

   TICKET-0084 (BRIEF-0084-b): `skill_system` reader. `systems` is fetched
   once alongside `rows` (world load/switch) and re-fetched after any
   write that can change a system's `skill_count` -- a system write
   itself, or a skill-definition write that attaches/detaches a system.
   Grouping the catalogue by system happens in the component
   (groupSkillsBySystem below), from these two flat lists -- never a
   nested endpoint response (json_ui_boundary).

   TICKET-0084 (BRIEF-0084-d): the read-only gaps reader. `gaps` and
   `arbiterFailures` follow the exact same shape as `systems` above --
   fetched once alongside rows/systems (world load/switch), never written
   to by this view. No re-fetch-after-write wiring: skill_resolution is
   append-only telemetry the catalogue write path never changes, so
   nothing here invalidates it (a stale gap simply stops recurring on the
   next live Play turn -- history is never rewritten). */
export const competencesState = $state({
  draft: [],   // AI-proposed rows awaiting individual accept/discard
  rows: [],    // existing world-scoped skill_definition rows
  systems: [], // existing world-scoped skill_system rows
  gaps: [],    // distinct unmatched surface forms, most frequent first
  arbiterFailures: { error: 0, empty: 0 },
  loading: true,
  loadError: '',
  systemsError: '',
  gapsError: '',
});

export const COMPETENCES_DOMAINS = ['physical', 'agility', 'perception', 'composure'];

// Exact label, both as the ungrouped catalogue's group header and as the
// skill-definition form's no-system dropdown option (BRIEF-0084-b Scope IN
// items 3-4) -- one literal, never retyped.
export const NO_SYSTEM_LABEL = 'Sans système';

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
  competencesState.draft.push({ name: '', base_domain: 'physical', system_id: null, description: '' });
}

/** Item 4 (BRIEF-0084-d): a gap click opens the same create form, name
 *  prefilled from surface_form, base_domain and system_id left unset --
 *  unlike addManualRow's 'physical' default, Nia must choose deliberately.
 *  Creates nothing; the row only lands in skill_definition on Accepter. */
export function addGapDraftRow(surfaceForm) {
  competencesState.draft.push({ name: surfaceForm, base_domain: '', system_id: null, description: '' });
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
  // The assistant proposes {name, base_domain, description} only -- it
  // knows nothing of skill_system. Default every proposed row to no
  // system, same as a manual row.
  competencesState.draft = (result.draft.skills || []).map((s) => ({ ...s, system_id: s.system_id ?? null }));
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
      system_id: row.system_id || null,
      description: row.description || '',
    }),
  });
  competencesState.draft.splice(i, 1);
  await loadList();
  await loadSystems();
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

export async function saveRow(id, name, base_domain, system_id, description) {
  await api(`/api/skill-definitions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, base_domain, system_id: system_id || null, description }),
  });
  await loadSystems();
}

/** D2-delete-cascade: dependent PC `skill` rows then the definition, in one
 *  transaction. No separate history snapshot (locked decision). */
export async function deleteDefinition(id) {
  await api(`/api/skill-definitions/${id}`, { method: 'DELETE' });
  await loadList();
  await loadSystems();
}

export async function loadSystems() {
  competencesState.systemsError = '';
  try {
    competencesState.systems = await api('/api/skill-systems');
  } catch (e) {
    competencesState.systemsError = e.message;
  }
}

/** Read-only: GET /api/skill-gaps only, never a write (BRIEF-0084-d). */
export async function loadGaps() {
  competencesState.gapsError = '';
  try {
    const data = await api('/api/skill-gaps');
    competencesState.gaps = data.gaps || [];
    competencesState.arbiterFailures = data.arbiter_failures || { error: 0, empty: 0 };
  } catch (e) {
    competencesState.gapsError = e.message;
  }
}

export async function createSystem(name, description) {
  await api('/api/skill-systems', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description || null }),
  });
  await loadSystems();
}

export async function saveSystem(id, name, description) {
  await api(`/api/skill-systems/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description || null }),
  });
  await loadSystems();
}

/** D2b-delete-refuse: the server is fail-closed while any skill_definition
 *  still carries this system_id (409) -- no optimistic removal here, the
 *  row is dropped from the list only once loadSystems() re-fetches after a
 *  confirmed success. */
export async function deleteSystem(id) {
  await api(`/api/skill-systems/${id}`, { method: 'DELETE' });
  await loadSystems();
}

/** Groups the flat skill-definition list under the flat system list,
 *  client-side (json_ui_boundary: no nested endpoint response). System
 *  groups are ordered by name and always rendered, even with zero skills
 *  (a system just created must be visible before it holds anything).
 *  Skills with no system, or whose system_id matches no live system, land
 *  in a trailing NO_SYSTEM_LABEL group -- rendered only when non-empty. */
export function groupSkillsBySystem(rows, systems) {
  const bySystem = new Map();
  for (const sys of [...systems].sort((a, b) => a.name.localeCompare(b.name))) {
    bySystem.set(sys.id, { system: sys, skills: [] });
  }
  const unassigned = [];
  for (const row of [...rows].sort((a, b) => a.name.localeCompare(b.name))) {
    const bucket = row.system_id ? bySystem.get(row.system_id) : undefined;
    if (bucket) bucket.skills.push(row);
    else unassigned.push(row);
  }
  const groups = [...bySystem.values()];
  if (unassigned.length) groups.push({ system: null, skills: unassigned });
  return groups;
}
