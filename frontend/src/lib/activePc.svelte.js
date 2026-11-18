/* TICKET-0128 (BRIEF-0128-C, A1). The active player character of the active
   world: the header's selector reads and sets it through /api/active-pc. */
import { api } from '../creation/sheetRequest.svelte.js';
import { refreshServerState } from './serverState.svelte.js';
import { handleWorldChanged } from '../creation/tabs.js';

export const activePcState = $state({ characters: [], activeId: null, chosen: false, error: '' });

function apply(body) {
  activePcState.characters = body.characters || [];
  activePcState.activeId = body.active_pc_id ?? null;
  activePcState.chosen = !!body.chosen;
  activePcState.error = '';
}

export async function loadActivePc() {
  try {
    apply(await api('/api/active-pc'));
  } catch (e) {
    activePcState.characters = [];
    activePcState.activeId = null;
    activePcState.chosen = false;
    activePcState.error = e.message;
  }
}

export async function chooseActivePc(id) {
  let result;
  try {
    result = await api('/api/active-pc', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: id || null }),
    });
  } catch (e) {
    activePcState.error = e.message;
    return;
  }
  apply(result);
  await refreshServerState();
  await handleWorldChanged();
}
