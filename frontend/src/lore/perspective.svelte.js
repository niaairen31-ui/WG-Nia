/* TICKET-0125 (BRIEF-0125-F). Non-render state + API calls for Lore >
   Perspective: the same question asked "as the public", through the
   creator perspective routes (/api/lore/perspective/ask|resolve).

   `result` holds the response body unchanged (verdict, answer, renderer,
   candidates, plan, rows, withheld); `selections` is the creator's choice
   per ambiguous mention ref until confirmPerspective() sends it back with
   the plan as received. `attemptId` names one question for the usage
   journal: askPerspective() opens a fresh one, confirmPerspective()
   reuses it. Writes nothing but the journal row the route writes. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

export const perspectiveState = $state({
  perspective: 'public',
  question: '',
  asking: false,
  error: '',
  result: null,
  selections: {},
  attemptId: '',
});

// The world the state was last reset for -- a plain variable, never
// reactive, so a remount of the panel keeps its result.
let stateWorldId = null;

export async function askPerspective() {
  const question = perspectiveState.question.trim();
  if (!question || perspectiveState.asking) return;
  perspectiveState.asking = true;
  perspectiveState.error = '';
  perspectiveState.attemptId = crypto.randomUUID();
  try {
    const result = await api('/api/lore/perspective/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        world_id: serverState.worldId,
        perspective: perspectiveState.perspective,
        attempt_id: perspectiveState.attemptId,
      }),
    });
    perspectiveState.result = result;
    perspectiveState.selections = {};
  } catch (e) {
    perspectiveState.error = e.message;
  } finally {
    perspectiveState.asking = false;
  }
}

export function selectPerspectiveCandidate(ref, entityId) {
  perspectiveState.selections = { ...perspectiveState.selections, [ref]: entityId };
}

export function allPerspectiveChoicesMade() {
  const result = perspectiveState.result;
  if (!result || result.verdict !== 'ambiguous_mention') return false;
  const refs = Object.keys(result.candidates || {});
  return refs.length > 0 && refs.every((ref) => perspectiveState.selections[ref]);
}

export async function confirmPerspective() {
  const result = perspectiveState.result;
  if (!result || perspectiveState.asking) return;
  perspectiveState.asking = true;
  perspectiveState.error = '';
  try {
    const resolved = await api('/api/lore/perspective/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan: result.plan,
        bindings: { ...perspectiveState.selections },
        world_id: serverState.worldId,
        question: perspectiveState.question,
        perspective: perspectiveState.perspective,
        attempt_id: perspectiveState.attemptId,
      }),
    });
    perspectiveState.result = resolved;
    perspectiveState.selections = {};
  } catch (e) {
    perspectiveState.error = e.message;
  } finally {
    perspectiveState.asking = false;
  }
}

export function resetPerspectiveForWorld() {
  const worldId = serverState.worldId;
  if (worldId === stateWorldId) return;
  stateWorldId = worldId;
  perspectiveState.question = '';
  perspectiveState.error = '';
  perspectiveState.result = null;
  perspectiveState.selections = {};
  perspectiveState.attemptId = '';
}
