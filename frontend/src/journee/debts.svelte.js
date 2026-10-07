/* TICKET-0110 (BRIEF-0110-D). State and requests of Journée's debts:
   « Dettes » (DebtsPanel.svelte) -- what the player owes and what is owed
   to him, GET /api/journee/debts, each open one with its refusals -- and
   « Demander un service » (ServiceForm.svelte, S2), POST /api/services.
   Repaying and forgiving go through the creator's routes, the same rules
   (writes/debts.py). A debt is named by its own id, never by a plan. */
import { api } from '../creation/sheetRequest.svelte.js';
import { blankDebtTerm, debtTermBody, owedFromService } from '../creation/debtTerms.js';
import { termBody } from '../creation/questTerms.js';

export const debtState = $state({
  owes: [],
  owed: [],
  loading: false,
  loadError: '',
  busy: null, // the debt id being acted on
  actionError: '',
});

export const serviceState = $state({
  choices: null,
  draft: null, // { provider_entity_id, on_behalf_of_id, terms, owed, owedTouched, reason, is_secret }
  sending: false,
  error: '',
  done: '',
});

function applyDebts(payload) {
  debtState.owes = payload.owes;
  debtState.owed = payload.owed;
}

export async function loadJourneeDebts() {
  debtState.loading = true;
  debtState.loadError = '';
  try {
    applyDebts(await api('/api/journee/debts'));
  } catch (e) {
    debtState.loadError = e.message;
    debtState.owes = [];
    debtState.owed = [];
  } finally {
    debtState.loading = false;
  }
}

async function act(id, path, body) {
  debtState.busy = id;
  debtState.actionError = '';
  try {
    await api('/api/debts/' + id + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
    });
    await loadJourneeDebts();
  } catch (e) {
    debtState.actionError = e.message;
  } finally {
    debtState.busy = null;
  }
}

export function repay(id) {
  return act(id, '/repay');
}

export function forgive(id, note) {
  return act(id, '/forgive', { note: note || null });
}

export async function openService() {
  serviceState.error = '';
  serviceState.done = '';
  serviceState.draft = {
    provider_entity_id: '', on_behalf_of_id: '', terms: [], owed: [], owedTouched: false, reason: '',
    is_secret: false,
  };
  if (!serviceState.choices) {
    try {
      serviceState.choices = await api('/api/quest-offers/choices');
    } catch (e) {
      serviceState.error = e.message;
    }
  }
}

/** S2: until Nia edits it, what is owed follows what is received. */
export function servicePrefill() {
  const draft = serviceState.draft;
  if (draft && !draft.owedTouched) draft.owed = owedFromService(draft.terms);
}

export function addOwed() {
  serviceState.draft.owedTouched = true;
  serviceState.draft.owed.push(blankDebtTerm());
}

export async function askService() {
  const draft = serviceState.draft;
  if (!draft) return;
  serviceState.sending = true;
  serviceState.error = '';
  try {
    applyDebts(await api('/api/services', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_entity_id: draft.provider_entity_id, on_behalf_of_id: draft.on_behalf_of_id || null,
        terms: draft.terms.map(termBody), owed: draft.owed.map(debtTermBody),
        reason: draft.reason || null, is_secret: draft.is_secret,
      }),
    }));
    serviceState.draft = null;
    serviceState.done = 'Service rendu : la dette est inscrite dans « Dettes ».';
  } catch (e) {
    serviceState.error = e.message;
  } finally {
    serviceState.sending = false;
  }
}
