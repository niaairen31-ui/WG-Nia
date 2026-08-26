/* TICKET-0059 (BRIEF-0059-j). Faithful port of intrigues' own non-render
   logic -- loadAgendasList/_intriguesPopulateOwnerSelect/
   _intriguesRefreshSelection/intriguesSetAgendaStatus/intriguesDetachLink/
   intriguesStepStatus/intriguesGenerateDraft/intriguesSubmitCreate
   (index.html, now deleted). Intrigues.svelte owns markup only, the same
   split GoalsEditor.svelte/goalsPanel.svelte.js already established.

   loadAgendas mirrors EntityList.svelte's own loadEvents (BRIEF-0058-j): a
   self-fetch assigned straight into creationState.agendas, replacing the
   legacy listLoader + 'creation:list-data' push this tab used to need.

   setAgendaStatus/detachLink/setStepStatus share one shape, unchanged from
   the legacy _intriguesRefreshSelection: none of the three mutation
   endpoints (PATCH /api/agendas/{id}, PATCH /api/agenda-steps/{id}, POST
   /api/goal-agenda-links/{id}/detach) returns the full nested agenda
   (steps + linked_goals), so every one re-fetches the whole list and
   re-selects by id, writing creationState.sheetDetail directly -- the same
   external-write precedent sheetState.svelte.js's selectEntity already
   established for entities. No success status line and alert() on
   failure, verbatim: unlike the entity sheet's own submitEntity/
   sheetRequest cycle, these three never touched #author-status. */
import { creationState } from './state.svelte.js';
import { api } from './sheetRequest.svelte.js';

export async function loadAgendas() {
  creationState.agendas = await api('/api/agendas');
}

export async function populateOwnerOptions() {
  const [factions, characters] = await Promise.all([
    api('/api/entities?type=faction'),
    api('/api/entities?type=character'),
  ]);
  return {
    factions: factions.filter((e) => e.status === 'active'),
    characters: characters.filter((e) => e.status === 'active'),
  };
}

async function refreshAgendaSelection(agendaId) {
  await loadAgendas();
  const agenda = creationState.agendas.find((a) => a.id === agendaId);
  if (agenda) {
    creationState.sheetDetail = agenda;
    creationState.selectedRecordId = agenda.id;
  }
}

export async function setAgendaStatus(agendaId, status, linkedGoalCount) {
  if (status !== 'active' && status !== 'paused' && linkedGoalCount > 0) {
    const ok = confirm(
      `Cette intrigue a ${linkedGoalCount} objectif(s) lié(s). La fermer transitionnera ` +
      `(complété/abandonné) chaque objectif dont c'est le DERNIER lien actif — un objectif ` +
      `qui sert aussi une autre intrigue encore active survit. Continuer ?`
    );
    if (!ok) return;
  }
  try {
    await api(`/api/agendas/${agendaId}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
    });
    await refreshAgendaSelection(agendaId);
  } catch (e) {
    alert(e.message);
  }
}

export async function detachLink(agendaId, linkId) {
  if (!confirm('Détacher ce lien ? Réversible : vous pourrez le rattacher plus tard.')) return;
  try {
    await api(`/api/goal-agenda-links/${encodeURIComponent(linkId)}/detach`, { method: 'POST' });
    await refreshAgendaSelection(agendaId);
  } catch (e) {
    alert(e.message);
  }
}

export async function setStepStatus(agendaId, stepId, status) {
  try {
    await api(`/api/agenda-steps/${stepId}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
    });
    await refreshAgendaSelection(agendaId);
  } catch (e) {
    alert(e.message);
  }
}

/** intrigues' AI assistant (BRIEF-0021-b item 5), ported (BRIEF-0059-j
 *  commit 2) -- pre-fills the create form (title + up to 5 steps) via
 *  POST /api/agendas/generate; writes no canon, one-shot (F2 precedent): a
 *  second call overwrites the draft. Returns the raw result, soft
 *  `{ok: false, error}` failure included, for Intrigues.svelte to inspect
 *  and assign into its own form fields -- generation fills the form,
 *  submitAgenda posts it. An HTTP-level failure throws (caller's job to
 *  catch), unchanged from the legacy try/catch shape. */
export async function generateAgendaDraft(ownerId, brief) {
  return api('/api/agendas/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner_entity_id: ownerId, brief }),
  });
}

/** intrigues' create submit (BRIEF-0021-a item 8), ported (BRIEF-0059-j
 *  commit 2). POST /api/agendas returns the full nested agenda already
 *  (unlike the status/step/detach trio above), but the sidebar list still
 *  needs its own refetch -- loadAgendas mirrors the legacy
 *  loadAgendasList()-then-creationSelectRecord() sequence, all in Svelte
 *  now: no legacyCall bridge needed (Scope IN item 8: this brief adds no
 *  new bridge-reach site). */
export async function submitAgenda(ownerId, title, steps) {
  const agenda = await api('/api/agendas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner_entity_id: ownerId, title, steps }),
  });
  await loadAgendas();
  creationState.sheetIsNew = false;
  creationState.sheetDetail = agenda;
  creationState.selectedRecordId = agenda.id;
  return agenda;
}
