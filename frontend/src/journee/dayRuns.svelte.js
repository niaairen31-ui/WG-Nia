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
  // BRIEF-0128-F (C1, C′2): resolved days awaiting publication, and the
  // text the creator will publish for each (batch id -> text).
  toPublish: [],
  toPublishError: '',
  drafts: {},
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

export async function loadToPublish() {
  dayRunsState.toPublishError = '';
  try {
    const days = await api('/api/day-runs/a-publier');
    for (const d of days) {
      if (dayRunsState.drafts[d.batch_id] === undefined) dayRunsState.drafts[d.batch_id] = d.narrator_text || '';
    }
    dayRunsState.toPublish = days;
  } catch (e) {
    dayRunsState.toPublishError = e.message;
    dayRunsState.toPublish = [];
  }
}

export async function publish(batchId) {
  dayRunsState.busy = batchId;
  dayRunsState.actionError = '';
  try {
    await api('/api/day-runs/' + batchId + '/publier', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: dayRunsState.drafts[batchId] }),
    });
  } catch (e) {
    dayRunsState.actionError = e.message;
  } finally {
    dayRunsState.busy = null;
  }
  await loadToPublish();
  await loadFailures();
  await loadDays();
}

export function relaunch(batchId) {
  return act(batchId, 'relancer');
}

export function abandon(batchId) {
  return act(batchId, 'abandonner');
}
