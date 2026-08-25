/* TICKET-0075 (BRIEF-0075-a; plan/resolve/account wiring BRIEF-0075-e).
   Non-render state + API calls for the Journée surface, same shape as
   observation.svelte.js: a $state object Journee.svelte renders, plus the
   functions that mutate it. No agenda data is fetched, rendered or
   referenced anywhere here (Scope OUT) -- `plan`/`resolve` responses never
   carry an agenda_id/step_id (backend Scope OUT, re-asserted at this
   surface), and the account block (BRIEF-0075-e item 4) is read-only: no
   approve/reject control lives here, that is the review queue's job. */
import { api } from '../creation/sheetRequest.svelte.js';

export const journeeState = $state({
  declaration: '',
  submitting: false,
  submitError: '',
  days: [],
  daysLoading: true,
  selectedId: null,
  detail: null,
  detailLoading: false,
  detailError: '',
  planning: false,
  planError: '',
  resolving: false,
  resolveError: '',
});

export function selectedDay() {
  return journeeState.days.find((d) => d.id === journeeState.selectedId) || null;
}

export async function loadDays() {
  journeeState.daysLoading = true;
  try {
    journeeState.days = await api('/api/days');
  } catch (_e) {
    journeeState.days = [];
  } finally {
    journeeState.daysLoading = false;
  }
}

/** Full day detail (account included once resolved) -- a separate fetch
 *  from `journeeState.days` (the list view), matching GET /api/day/{id}'s
 *  own shape rather than duplicating it into the list payload. */
export async function loadDayDetail(id) {
  if (!id) { journeeState.detail = null; return; }
  journeeState.detailLoading = true;
  journeeState.detailError = '';
  try {
    journeeState.detail = await api('/api/day/' + id);
  } catch (e) {
    journeeState.detailError = e.message;
    journeeState.detail = null;
  } finally {
    journeeState.detailLoading = false;
  }
}

export function selectDay(id) {
  journeeState.selectedId = id;
  journeeState.planError = '';
  journeeState.resolveError = '';
  loadDayDetail(id);
}

export async function planDay(id) {
  journeeState.planning = true;
  journeeState.planError = '';
  try {
    await api('/api/day/' + id + '/plan', { method: 'POST' });
    await loadDays();
    await loadDayDetail(id);
  } catch (e) {
    journeeState.planError = e.message;
  } finally {
    journeeState.planning = false;
  }
}

export async function resolveDay(id) {
  journeeState.resolving = true;
  journeeState.resolveError = '';
  try {
    await api('/api/day/' + id + '/resolve', { method: 'POST' });
    await loadDays();
    await loadDayDetail(id);
  } catch (e) {
    journeeState.resolveError = e.message;
  } finally {
    journeeState.resolving = false;
  }
}

export async function submitDeclaration() {
  const text = journeeState.declaration.trim();
  if (!text) return;
  journeeState.submitting = true;
  journeeState.submitError = '';
  try {
    const day = await api('/api/day/declare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ declared_action: text }),
    });
    journeeState.declaration = '';
    await loadDays();
    selectDay(day.id);
  } catch (e) {
    journeeState.submitError = e.message;
  } finally {
    journeeState.submitting = false;
  }
}

export async function reloadForWorld() {
  journeeState.declaration = '';
  journeeState.submitError = '';
  journeeState.selectedId = null;
  journeeState.detail = null;
  journeeState.detailError = '';
  await loadDays();
}
