/* TICKET-0110 (BRIEF-0110-C). State and requests of the « Dettes » island
   (Debts.svelte): every debt of the world, the pickers' lists (the quest
   editor's choices, members included), one draft written by hand, and a
   remission's note. A debt is written whole (POST /api/debts), repaid
   (POST …/repay) or forgiven (POST …/forgive) -- never edited, never
   deleted (writes/debts.py). */
import { api } from './sheetRequest.svelte.js';
import { blankDebtTerm, debtTermBody } from './debtTerms.js';

export const debtsState = $state({
  debts: [],
  choices: null,
  loading: false,
  loadError: '',
  draft: null, // { debtor_entity_id, creditor_entity_id, contact_entity_id, reason, is_secret, terms }
  saving: false,
  saveError: '',
  actionError: '', // a refused repayment or remission, by debt id: { id, message }
});

export function newDebtDraft() {
  debtsState.saveError = '';
  debtsState.draft = {
    debtor_entity_id: '', creditor_entity_id: '', contact_entity_id: '', reason: '', is_secret: false,
    terms: [blankDebtTerm()],
  };
}

export async function loadDebts(worldId) {
  if (!worldId) { debtsState.debts = []; debtsState.choices = null; return; }
  debtsState.loading = true;
  debtsState.loadError = '';
  try {
    const [debts, choices] = await Promise.all([api('/api/debts'), api('/api/quest-offers/choices')]);
    debtsState.debts = debts;
    debtsState.choices = choices;
  } catch (e) {
    debtsState.loadError = e.message;
  } finally {
    debtsState.loading = false;
  }
}

export async function saveDebtDraft(worldId) {
  const draft = debtsState.draft;
  if (!draft) return;
  debtsState.saving = true;
  debtsState.saveError = '';
  try {
    await api('/api/debts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        debtor_entity_id: draft.debtor_entity_id, creditor_entity_id: draft.creditor_entity_id,
        contact_entity_id: draft.contact_entity_id || null, reason: draft.reason || null,
        is_secret: draft.is_secret, terms: draft.terms.map(debtTermBody),
      }),
    });
    debtsState.draft = null;
    await loadDebts(worldId);
  } catch (e) {
    debtsState.saveError = e.message;
  } finally {
    debtsState.saving = false;
  }
}

async function act(worldId, id, path, body) {
  debtsState.actionError = '';
  try {
    await api('/api/debts/' + id + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
    });
    await loadDebts(worldId);
  } catch (e) {
    debtsState.actionError = { id, message: e.message };
  }
}

export function repayDebt(worldId, id) {
  return act(worldId, id, '/repay');
}

export function forgiveDebt(worldId, id, note) {
  return act(worldId, id, '/forgive', { note: note || null });
}
