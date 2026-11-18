/* TICKET-0075 (BRIEF-0075-a; plan/resolve/account wiring BRIEF-0075-e).
   Non-render state + API calls for the Journée surface, same shape as
   observation.svelte.js: a $state object Journee.svelte renders, plus the
   functions that mutate it. No agenda data is fetched, rendered or
   referenced anywhere here (Scope OUT) -- the day worker plans and
   resolves (TICKET-0128, K1), and the account block (BRIEF-0075-e item 4) is read-only: no
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
});

// TICKET-0128 (K1): the worker plans and resolves a declared day in the
// background; while one is under way the list re-reads itself.
export const DAY_POLL_MS = 5000;
let pollTimer = null;

function schedulePoll() {
  if (pollTimer !== null) clearTimeout(pollTimer);
  pollTimer = null;
  if (!journeeState.days.some((d) => d.status === 'submitted' || d.status === 'resolving')) return;
  pollTimer = setTimeout(async () => {
    pollTimer = null;
    await loadDays();
    if (journeeState.selectedId) await loadDayDetail(journeeState.selectedId);
  }, DAY_POLL_MS);
}

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
  schedulePoll();
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
  loadDayDetail(id);
}

/** Q1 (TICKET-0128): `questId` pins the declared day to one open quest;
 *  '' or null lets the day choose. */
export async function submitDeclaration(questId) {
  const text = journeeState.declaration.trim();
  if (!text) return;
  journeeState.submitting = true;
  journeeState.submitError = '';
  try {
    const day = await api('/api/day/declare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ declared_action: text, quest_id: questId || null }),
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
