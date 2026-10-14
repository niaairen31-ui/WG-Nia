/* TICKET-0121 (BRIEF-0121-G, C-12, C-14). Non-render state + API calls for
   « Demandes de quête », the panel QuestRequests.svelte renders above the
   review queue: every request a day opened, moved by the server's case
   table (C-02) -- the client offers an action, the server decides.

   An existence answer `exists` / `absent` is written through the Lore
   panel: its statement pre-fills « Écrire » (`openForQuestRequest`) and
   the Lore surface opens; the commit there runs the designer again.
   `already` names the world's entity and designs at once. */
import { api } from './sheetRequest.svelte.js';
import { navigate } from '../lib/router.js';
import { queueState } from './queue.svelte.js';
import { openForQuestRequest } from '../lore/writePanel.svelte.js';

export const questRequestsState = $state({
  requests: [], loading: false, error: '', busy: {}, choices: null,
  // The existence question's inputs, by request id.
  inputs: {},
});

const post = (path, body) => api(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
});

export function requestSubject(request) {
  return request.subject || request.declaration;
}

/** The Lore statement, built the way the answer route builds it. */
export function lineFor(request, answer, text) {
  const subject = requestSubject(request);
  const said = (text || '').trim();
  return answer === 'exists' ? `${subject} : ${said}` : `${subject} n'existe pas dans ce monde. ${said}`.trim();
}

export async function loadRequests() {
  questRequestsState.loading = true;
  try {
    const requests = await api('/api/quest-requests');
    for (const r of requests) {
      questRequestsState.inputs[r.id] ||= { text: '', already: false, entityId: '' };
    }
    questRequestsState.requests = requests;
    questRequestsState.error = '';
  } catch (e) {
    questRequestsState.error = e.message;
  } finally {
    questRequestsState.loading = false;
  }
}

export async function loadChoices() {
  if (questRequestsState.choices) return;
  questRequestsState.choices = await api('/api/quest-offers/choices');
}

async function busy(id, task) {
  questRequestsState.busy[id] = true;
  questRequestsState.error = '';
  try {
    await task();
  } catch (e) {
    questRequestsState.error = e.message;
  } finally {
    delete questRequestsState.busy[id];
  }
}

export function designRequest(id) {
  return busy(id, async () => {
    await post(`/api/quest-requests/${id}/design`);
    await loadRequests();
    queueState.reloadToken += 1;
  });
}

function writeInLore(request, statement) {
  openForQuestRequest(request.id, requestSubject(request), statement);
  navigate('lore');
}

export async function answerRequest(id, answer, text, entityId) {
  let body = null;
  await busy(id, async () => {
    body = await post(`/api/quest-requests/${id}/answer`, { answer, text, entity_id: entityId || null });
  });
  if (!body) return;
  if (answer === 'already') {
    await designRequest(id);
    return;
  }
  await loadRequests();
  writeInLore(body.request, body.statement);
}

/** « Écrire dans Lore » for a request already waiting there. */
export function resumeInLore(request) {
  writeInLore(request, lineFor(request, request.existence_answer, request.creator_text));
}

export function dropRequest(id) {
  return busy(id, async () => {
    await post(`/api/quest-requests/${id}/drop`);
    await loadRequests();
  });
}

export function worldChanged() {
  questRequestsState.choices = null;
  questRequestsState.busy = {};
  questRequestsState.inputs = {};
}
