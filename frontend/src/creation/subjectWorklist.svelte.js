/* TICKET-0088 (BRIEF-0088-b). State and requests for the subject worklist
   (SubjectWorklist.svelte), the first Creation island whose registry entry
   declares origin 'new'. Same split as queue.svelte.js / Queue.svelte:
   this module owns the state and every request, the component renders.

   Rows are GET /api/worlds/{world_id}/unresolved-subjects unchanged: one
   row per distinct knowledge.subject whose facts carry no fact_participant
   at all. Binding a subject is one POST /api/facts/{fact_id}/participants
   per fact, sequential, with no role (decision E1). Each POST is correct
   on its own; the first failure stops the loop; the reload that always
   follows leaves a partly bound subject listed with only its unbound
   facts, so a retry binds the remainder and never duplicates a
   participant. The route answers 500 on a duplicate (fact, entity) pair,
   which is why one bind at a time runs and every control stays disabled
   until the reload that follows it has landed.

   loadSubjects() is called from the component's $effect: before its first
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
  bindingSubject: null,
  bindErrors: {},
});

let loadedWorldId = null;
let loadSeq = 0;

export async function loadSubjects(worldId) {
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
      api(`/api/worlds/${encodeURIComponent(worldId)}/unresolved-subjects`),
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

export function suggestedEntityId(row) {
  const r = row.resolution;
  if (!r || r.verdict !== 'matched') return '';
  return subjectState.entities.some((e) => e.id === r.entity_id) ? r.entity_id : '';
}

export function selectedEntityId(row) {
  const chosen = subjectState.selections[row.subject];
  return chosen !== undefined ? chosen : suggestedEntityId(row);
}

export function selectEntity(subject, entityId) {
  subjectState.selections = { ...subjectState.selections, [subject]: entityId };
}

export async function bindSubject(row) {
  const entityId = selectedEntityId(row);
  if (!entityId || subjectState.bindingSubject !== null) return;
  const worldId = loadedWorldId;
  const subject = row.subject;
  const factIds = Array.from(row.fact_ids);
  const errors = { ...subjectState.bindErrors };
  delete errors[subject];
  subjectState.bindErrors = errors;
  subjectState.bindingSubject = subject;
  let bound = 0;
  try {
    for (const factId of factIds) {
      if (serverState.worldId !== worldId) break;
      await api(`/api/facts/${encodeURIComponent(factId)}/participants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId }),
      });
      bound += 1;
    }
  } catch (e) {
    subjectState.bindErrors = {
      ...subjectState.bindErrors,
      [subject]: `${bound}/${factIds.length} fait(s) lié(s) avant l'échec : ${e.message}`,
    };
  } finally {
    if (serverState.worldId === worldId) await loadSubjects(worldId);
    subjectState.bindingSubject = null;
  }
}
