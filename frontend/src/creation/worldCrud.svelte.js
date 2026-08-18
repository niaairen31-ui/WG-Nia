/* TICKET-0059 (BRIEF-0059-l commit 3, Amendment 3). World create/delete --
   ported off index.html's worldCreateOpen/worldCreateSubmit/
   worldGenerateDraft/worldApplyDraft/worldDeleteOpen/worldDeleteConfirm
   (BRIEF-44/47/54), now Modal.svelte's third and fourth consumers
   (competences' delete confirm and LocationTypeModal are the first two).

   State lives here, not in WorldCrud.svelte, matching every other
   Creation controller module (tabs.js, sheetState.svelte.js): Header.svelte
   triggers openWorldCreateModal/openWorldDeleteModal directly, a plain
   Svelte-to-Svelte import, replacing bridge.js's openWorldCreate/
   openWorldDelete (both deleted -- their only job was a legacyCall
   passthrough to the functions this file now owns outright).

   loadWorldSelector does not port: Header.svelte already renders its own
   <select> reactively off serverState.worlds (TICKET-0056) -- the legacy
   #world-selector this function used to populate had no other reader (the
   -l amendment already deleted the dead element in commit 1). Every path
   that used to call loadWorldSelector calls refreshServerState() instead.

   Play's post-delete refresh (was loadBootstrap()/loadScene()/
   loadPlayerName(), all still-legacy) is approximated the same way
   PjCreatePanel.svelte already established for this exact class of problem
   (its own header comment, BRIEF-0059-j commit 3): refreshServerState()
   covers the WORLD_ID/PLAYER_ID mirror; Play's own scene view is NOT
   re-rendered here (no new legacy_calls.baseline entry -- Scope OUT is
   explicit that the baseline may only shrink). A narrow, documented gap:
   Play's scene panel shows stale content until the player next navigates
   there, same as PjCreatePanel's own skill-fiche dropdown gap. */
import { serverState, refreshServerState } from '../lib/serverState.svelte.js';
import { handleWorldChanged } from './tabs.js';

export const worldCrudState = $state({
  createOpen: false,
  createName: '',
  createDescription: '',
  createLaws: '',
  createStatus: '',
  genBrief: '',
  genStatus: '',
  genNotes: [],
  deleteOpen: false,
  deleteWorldId: null,
  deleteWorldName: '',
  deleteConfirmText: '',
  deleteStatus: '',
});

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = `${path} -> ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') msg = body.detail;
    } catch (_err) {
      // response body wasn't JSON -- keep the status-based message
    }
    throw new Error(msg);
  }
  return res.json();
}

/** BRIEF-44 (B2): minimal create-world form -- name + description +
 *  fundamental_laws, both optional. On success the new world is already
 *  active server-side; just refresh the shell's own mirror. */
export function openWorldCreateModal() {
  worldCrudState.createOpen = true;
  worldCrudState.createName = '';
  worldCrudState.createDescription = '';
  worldCrudState.createLaws = '';
  worldCrudState.createStatus = '';
  worldCrudState.genBrief = '';
  worldCrudState.genStatus = '';
  worldCrudState.genNotes = [];
}

export function closeWorldCreateModal() {
  worldCrudState.createOpen = false;
}

/** BRIEF-47: world-bible generator. Seed phrase -> AI draft -> pre-fills
 *  the SAME create-world fields above; accept is still worldCreateSubmit()
 *  unchanged. Generating again simply re-runs this and overwrites the
 *  fields/notes -- no separate discard step needed. */
export async function worldGenerateDraft() {
  const brief = worldCrudState.genBrief.trim();
  if (!brief) { worldCrudState.genStatus = 'Intention requise.'; return; }
  worldCrudState.genStatus = 'Génération…';
  try {
    const result = await api('/api/worlds/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief }),
    });
    if (!result.ok) { worldCrudState.genStatus = result.error; return; }
    const draft = result.draft;
    worldCrudState.createName = draft.public.name ?? '';
    worldCrudState.createDescription = draft.public.description ?? '';
    worldCrudState.createLaws = draft.public.fundamental_laws ?? '';
    worldCrudState.genNotes = result.notes || [];
    worldCrudState.genStatus = 'Brouillon généré — relisez et éditez avant de créer.';
  } catch (err) {
    worldCrudState.genStatus = err.message;
  }
}

export async function worldCreateSubmit() {
  const name = worldCrudState.createName.trim();
  if (!name) { worldCrudState.createStatus = 'Le nom est requis.'; return; }
  worldCrudState.createStatus = '…';
  try {
    const res = await api('/api/worlds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        description: worldCrudState.createDescription.trim(),
        fundamental_laws: worldCrudState.createLaws.trim(),
      }),
    });
    if (!res.ok) { worldCrudState.createStatus = res.error; return; }
    closeWorldCreateModal();
    await refreshServerState();
  } catch (err) {
    worldCrudState.createStatus = err.message;
  }
}

/** BRIEF-54 (B2'): delete-world confirm modal. Click-away protected; reads
 *  the active world straight off serverState instead of the DOM. */
export function openWorldDeleteModal() {
  const world = serverState.worlds.find((w) => w.id === serverState.worldId);
  if (!world) return;
  worldCrudState.deleteOpen = true;
  worldCrudState.deleteWorldId = world.id;
  worldCrudState.deleteWorldName = world.name;
  worldCrudState.deleteConfirmText = '';
  worldCrudState.deleteStatus = '';
}

export function closeWorldDeleteModal() {
  worldCrudState.deleteOpen = false;
}

export async function worldDeleteConfirm() {
  const worldId = worldCrudState.deleteWorldId;
  worldCrudState.deleteStatus = '…';
  try {
    const res = await api(`/api/worlds/${worldId}`, { method: 'DELETE' });
    if (!res.ok) { worldCrudState.deleteStatus = res.error || 'Échec de la suppression.'; return; }
    closeWorldDeleteModal();
    if (res.remaining === 0) {
      openWorldCreateModal();
      return;
    }
    await refreshServerState();
    await handleWorldChanged();
  } catch (err) {
    worldCrudState.deleteStatus = err.message;
  }
}
