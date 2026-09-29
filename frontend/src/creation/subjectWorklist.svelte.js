/* TICKET-0088 (BRIEF-0088-b), re-aimed by TICKET-0097 (BRIEF-0097-f, I1/J1).
   State and requests for the « Sujets » worklist (SubjectWorklist.svelte).
   Same split as queue.svelte.js / Queue.svelte: this module owns the state
   and every request, the component renders.

   Rows are GET /api/worlds/{world_id}/unbound-facts unchanged: one row per
   free fact someone knows and no fact_participant binds, with its text, the
   first knower's version, the knower count, and the Lore resolver's
   candidates and near names. Binding is ONE POST
   /api/facts/{fact_id}/participants with no role (decision E1 of 0088). The
   reload that always follows drops the bound fact from the list. Only one
   bind runs at a time, and every control stays disabled until its reload
   has landed (the route answers 500 on a duplicate (fact, entity) pair).

   loadFacts() is called from the component's $effect: before its first
   await it only WRITES subjectState, and the world it compares against is
   a plain module variable, so the effect depends on serverState.worldId
   alone. */
import { api } from './sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

export const subjectState = $state({
  loading: false,
  loadError: '',
  rows: [],
  entities: [],
  selections: {},
  bindingFact: null,
  bindErrors: {},
});

let loadedWorldId = null;
let loadSeq = 0;

export async function loadFacts(worldId) {
  const seq = ++loadSeq;
  if (worldId !== loadedWorldId) {
    loadedWorldId = worldId;
    subjectState.rows = [];
    subjectState.entities = [];
    subjectState.selections = {};
    subjectState.bindErrors = {};
  }
  subjectState.loadError = '';
  if (!worldId) {
    subjectState.loading = false;
    return;
  }
  subjectState.loading = true;
  try {
    const [rows, entities] = await Promise.all([
      api(`/api/worlds/${encodeURIComponent(worldId)}/unbound-facts`),
      api('/api/entities'),
    ]);
    if (seq !== loadSeq) return;
    subjectState.rows = rows;
    subjectState.entities = entities.filter((e) => e.status === 'active' && e.world_id === worldId);
  } catch (e) {
    if (seq !== loadSeq) return;
    subjectState.rows = [];
    subjectState.entities = [];
    subjectState.loadError = e.message;
  } finally {
    if (seq === loadSeq) subjectState.loading = false;
  }
}

/* A suggestion exists only when the resolver found exactly one candidate:
   the resolver never picks between two. */
export function suggestedEntityId(row) {
  if (row.candidates.length !== 1) return '';
  const id = row.candidates[0].id;
  return subjectState.entities.some((e) => e.id === id) ? id : '';
}

export function selectedEntityId(row) {
  const chosen = subjectState.selections[row.fact_id];
  return chosen !== undefined ? chosen : suggestedEntityId(row);
}

export function selectEntity(factId, entityId) {
  subjectState.selections = { ...subjectState.selections, [factId]: entityId };
}

export async function bindFact(row) {
  const entityId = selectedEntityId(row);
  if (!entityId || subjectState.bindingFact !== null) return;
  const worldId = loadedWorldId;
  const factId = row.fact_id;
  const errors = { ...subjectState.bindErrors };
  delete errors[factId];
  subjectState.bindErrors = errors;
  subjectState.bindingFact = factId;
  try {
    await api(`/api/facts/${encodeURIComponent(factId)}/participants`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_id: entityId }),
    });
  } catch (e) {
    subjectState.bindErrors = { ...subjectState.bindErrors, [factId]: `Échec de la liaison : ${e.message}` };
  } finally {
    if (serverState.worldId === worldId) await loadFacts(worldId);
    subjectState.bindingFact = null;
  }
}
