/* TICKET-0075 (BRIEF-0075-a). Non-render state + API calls for the Journée
   surface -- declare-a-day plumbing only, same shape as
   observation.svelte.js: a $state object Journee.svelte renders, plus the
   functions that mutate it. No agenda data is fetched, rendered or
   referenced anywhere here (Scope OUT). */
import { api } from '../creation/sheetRequest.svelte.js';

export const journeeState = $state({
  declaration: '',
  submitting: false,
  submitError: '',
  days: [],
  daysLoading: true,
  selectedId: null,
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

export function selectDay(id) {
  journeeState.selectedId = id;
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
    journeeState.selectedId = day.id;
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
  await loadDays();
}
