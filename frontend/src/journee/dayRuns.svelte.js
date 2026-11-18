/* TICKET-0128 (BRIEF-0128-E, M1, Z1): the day worker's failed days, as
   Journée shows them -- relaunch or abandon. Every request goes through
   `api` (INV-69). */
import { api } from '../creation/sheetRequest.svelte.js';
import { loadDays } from './journee.svelte.js';

export const dayRunsState = $state({
  failures: [],
  failuresError: '',
  busy: null, // the batch_id being acted on
  actionError: '',
});

export async function loadFailures() {
  dayRunsState.failuresError = '';
  try {
    dayRunsState.failures = await api('/api/day-runs/echecs');
  } catch (e) {
    dayRunsState.failuresError = e.message;
    dayRunsState.failures = [];
  }
}

async function act(batchId, verb) {
  dayRunsState.busy = batchId;
  dayRunsState.actionError = '';
  try {
    await api('/api/day-runs/' + batchId + '/' + verb, { method: 'POST' });
  } catch (e) {
    dayRunsState.actionError = e.message;
  } finally {
    dayRunsState.busy = null;
  }
  await loadFailures();
  await loadDays();
}

export function relaunch(batchId) {
  return act(batchId, 'relancer');
}

export function abandon(batchId) {
  return act(batchId, 'abandonner');
}
