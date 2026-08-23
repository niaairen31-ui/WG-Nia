/* TICKET-0074 (BRIEF-0074-b). Non-render logic for ScheduleEditor.svelte --
   "la journée de X", the T-C1 authoring island -- on the GoalsEditor /
   goalsPanel.svelte.js split (component owns markup, this module owns
   state and requests). One request-then-reload-then-status cycle via
   sheetRequest.svelte.js, the same shape addGoal/setGoalStatus already
   use.

   scheduleState.rows always holds SCHEDULE_PHASES.length entries, one per
   phase, in order -- GET /api/entities/{id}/schedule guarantees this shape
   server-side (an absent phase is a null-valued row, never an omitted
   one), so the component never has to reconstruct a missing phase itself.

   standingGoals is this NPC's own kind='standing' goals (a GoalsEditor add
   is how those come to exist) -- fed to the standing-goal picker; a
   schedule row's standing_goal_id must already belong to this NPC
   (write_npc_schedule enforces it server-side too). */
import { sheetRequest, api } from './sheetRequest.svelte.js';

export const scheduleState = $state({
  rows: [],
  standingGoals: [],
  loadError: '',
});

export async function loadSchedule(entityId) {
  try {
    const [rows, goals] = await Promise.all([
      api(`/api/entities/${encodeURIComponent(entityId)}/schedule`),
      api(`/api/entities/${encodeURIComponent(entityId)}/goals`),
    ]);
    scheduleState.rows = rows || [];
    scheduleState.standingGoals = (goals || []).filter((g) => g.kind === 'standing');
    scheduleState.loadError = '';
  } catch (e) {
    scheduleState.rows = [];
    scheduleState.standingGoals = [];
    scheduleState.loadError = e.message;
  }
}

export async function saveSchedule(legacyDoc, entityId, rows) {
  // Clearing a row's location and saving removes that phase (E1 full
  // replace) -- rows with no location_id are dropped from the payload
  // rather than sent empty, so write_npc_schedule's delete-then-insert
  // simply never re-inserts them.
  const payload = rows
    .filter((r) => r.location_id)
    .map((r) => ({ phase: r.phase, location_id: r.location_id, standing_goal_id: r.standing_goal_id || null }));
  await sheetRequest(
    legacyDoc,
    `/api/entities/${encodeURIComponent(entityId)}/schedule`,
    'PUT',
    JSON.stringify({ rows: payload }),
    () => loadSchedule(entityId),
  );
}
