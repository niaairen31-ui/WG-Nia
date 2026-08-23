/* TICKET-0059 (BRIEF-0059-d). Non-render logic for the NPC goals in-context
   editor -- state + mutation functions ported off authorLoadGoals and its
   family (index.html, now deleted). GoalsEditor.svelte owns markup only.

   goalsPanelState.goals replaces authorGoalsCache: goalPrereqRawList reads
   the current list directly from it so a single prerequisite add/remove
   never needs a round-trip first, exactly as before.

   setGoalPrerequisites/addGoal/setGoalStatus/backfillGoals share the one
   request-then-reload-then-status cycle via sheetRequest.svelte.js
   (authorGoalRequest, now deleted, was the same cycle -- it is not
   reimplemented a second time here). attachGoalLink/detachGoalLink do NOT:
   legacy alert()s on failure and never touches the status line for these
   two, a distinct shape preserved verbatim -- they call loadGoals directly,
   the same as authorAttachGoalLink/authorDetachGoalLink always did. */
import { sheetRequest, api } from './sheetRequest.svelte.js';

export const goalsPanelState = $state({
  goals: [],
  activeAgendas: [],
  loadError: '',
});

export async function loadGoals(entityId) {
  try {
    const [goals, agendas] = await Promise.all([
      api(`/api/entities/${encodeURIComponent(entityId)}/goals`),
      api('/api/agendas'),
    ]);
    goalsPanelState.goals = goals || [];
    goalsPanelState.activeAgendas = (agendas || []).filter((a) => a.status === 'active');
    goalsPanelState.loadError = '';
  } catch (e) {
    goalsPanelState.goals = [];
    goalsPanelState.activeAgendas = [];
    goalsPanelState.loadError = e.message;
  }
}

export function goalPrereqRawList(goalId) {
  const goal = goalsPanelState.goals.find((g) => g.id === goalId);
  return ((goal && goal.prerequisites) || []).map((p) => ({
    type: p.type, target_entity_id: p.target_entity_id, threshold: p.threshold,
  }));
}

export async function setGoalPrerequisites(legacyDoc, entityId, goalId, prerequisites) {
  await sheetRequest(
    legacyDoc,
    `/api/goals/${encodeURIComponent(goalId)}/prerequisites`,
    'PATCH',
    JSON.stringify({ prerequisites }),
    () => loadGoals(entityId),
  );
}

export async function addGoalPrerequisite(legacyDoc, entityId, goalId, targetId, threshold) {
  const prerequisites = goalPrereqRawList(goalId);
  prerequisites.push({ type: 'relation_gte', target_entity_id: targetId, threshold });
  await setGoalPrerequisites(legacyDoc, entityId, goalId, prerequisites);
}

export async function removeGoalPrerequisite(legacyDoc, entityId, goalId, index) {
  const prerequisites = goalPrereqRawList(goalId);
  prerequisites.splice(index, 1);
  await setGoalPrerequisites(legacyDoc, entityId, goalId, prerequisites);
}

export async function attachGoalLink(entityId, goalId, agendaId) {
  if (!agendaId) return;
  try {
    await api('/api/goal-agenda-links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_id: goalId, agenda_id: agendaId }),
    });
    await loadGoals(entityId);
  } catch (e) {
    alert(e.message);
  }
}

export async function detachGoalLink(entityId, linkId) {
  if (!confirm('Détacher ce lien ? Réversible : vous pourrez le rattacher plus tard.')) return;
  try {
    await api(`/api/goal-agenda-links/${encodeURIComponent(linkId)}/detach`, { method: 'POST' });
    await loadGoals(entityId);
  } catch (e) {
    alert(e.message);
  }
}

export async function addGoal(legacyDoc, entityId, kind, horizon, description) {
  await sheetRequest(
    legacyDoc,
    `/api/entities/${encodeURIComponent(entityId)}/goals`,
    'POST',
    JSON.stringify({ kind, horizon, description }),
    () => loadGoals(entityId),
  );
}

export async function setGoalStatus(legacyDoc, entityId, goalId, status) {
  await sheetRequest(
    legacyDoc,
    `/api/goals/${encodeURIComponent(goalId)}/status`,
    'POST',
    JSON.stringify({ status }),
    () => loadGoals(entityId),
  );
}

export async function backfillGoals(legacyDoc, entityId) {
  await sheetRequest(
    legacyDoc,
    '/api/npc-goals/backfill',
    'POST',
    JSON.stringify({ entity_id: entityId }),
    () => loadGoals(entityId),
  );
}
