/* TICKET-0085 (BRIEF-0085-e). Non-render state + API calls for the Lore
   consultation surface, same shape as observation.svelte.js/journee.svelte.js:
   a $state object Lore.svelte renders, plus the functions that mutate it.

   `result` holds the full response body from either /api/lore/ask or
   /api/lore/resolve unchanged (verdict, rows, trace, plan, candidates,
   answer, renderer) -- the component renders directly off it rather than
   this module reshaping it. `selections` is the only local addition: the
   creator's in-progress candidate choice per ambiguous mention ref, kept
   here (not in `result`) until confirmResolution() sends it back. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

export const loreState = $state({
  question: '',
  asking: false,
  askError: '',
  result: null,
  selections: {},
});

export async function askLore() {
  const question = loreState.question.trim();
  if (!question || loreState.asking) return;
  loreState.asking = true;
  loreState.askError = '';
  try {
    const result = await api('/api/lore/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, world_id: serverState.worldId }),
    });
    loreState.result = result;
    loreState.selections = {};
  } catch (e) {
    loreState.askError = e.message;
  } finally {
    loreState.asking = false;
  }
}

export function selectCandidate(ref, entityId) {
  loreState.selections = { ...loreState.selections, [ref]: entityId };
}

// Every ambiguous mention must have a choice before the confirm control
// enables (BRIEF-0085-e item 5: "partial selection leaves the control
// disabled -- the round resolves every ambiguity at once").
export function allAmbiguitiesResolved() {
  const result = loreState.result;
  if (!result || result.verdict !== 'ambiguous_mention') return false;
  const refs = Object.keys(result.candidates || {});
  return refs.length > 0 && refs.every((ref) => loreState.selections[ref]);
}

// The plan travels back exactly as received -- no rebuild, no re-issue of
// /ask (item 6): `result.plan` is passed through untouched.
export async function confirmResolution() {
  const result = loreState.result;
  if (!result || loreState.asking) return;
  loreState.asking = true;
  loreState.askError = '';
  try {
    const resolved = await api('/api/lore/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan: result.plan,
        bindings: { ...loreState.selections },
        world_id: serverState.worldId,
        question: loreState.question,
      }),
    });
    loreState.result = resolved;
    loreState.selections = {};
  } catch (e) {
    loreState.askError = e.message;
  } finally {
    loreState.asking = false;
  }
}

export function reloadForWorld() {
  loreState.question = '';
  loreState.askError = '';
  loreState.result = null;
  loreState.selections = {};
}
