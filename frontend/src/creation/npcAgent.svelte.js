/* TICKET-0059 (BRIEF-0059-f). The NPC group agent's non-render logic --
   was the npcAgentOpenBatchId/npcAgentLocations/npcAgentSelectedRoot/
   npcAgentPreview/npcAgentGroupBrief/npcAgentLines module-level `let`s plus
   npcAgentReset/npcAgentCheckOpenBatch/npcAgentRenderLauncher/
   npcAgentSelectRoot/npcAgentPreviewRoot/npcAgentAddLine/npcAgentRemoveLine/
   npcAgentEditLine/_npcAgentLineTotal/npcAgentLaunch (index.html, deleted in
   this same commit). `_npcAgentTreeHtml` is NOT ported -- LocationTree.svelte
   (commit 1) replaces it outright. `_npcAgentLineRowHtml`/
   `_npcAgentPaintLauncher` are not ported either: Svelte's own declarative
   markup (NpcAgent.svelte) replaces the innerHTML-painting they did.

   Grown across this brief's two remaining commits rather than authored
   whole (sheetState.svelte.js's own precedent, TICKET-0059 BRIEF-0059-e):
   this commit (2) adds the launcher's state and functions only. Commit 3
   adds npcAgentState.batch/rows/loopRunning/failedRun/commitResult/
   linkHandoffMsg plus the run-loop/review functions that operate on them.

   One consequence of that split: launch() below sets npcAgentState.openBatchId
   on success but does NOT yet move the panel onto a review surface --
   npcAgentLoadBatch doesn't exist until commit 3. Between these two commits
   (both landing in this same brief execution) a freshly launched batch's
   review stays unreachable through the UI; commit 3 closes that gap by
   wiring loadBatch(batch.id) onto this same success path. Not a permanent
   half-feature -- the brief's own commit split, made explicit here so a
   future reader isn't left to infer it.

   State is module-level (not NpcAgent.svelte-local) for the same reason
   RoomBatch's roomBatchState is: TICKET-0059's BRIEF-0059-f doesn't need a
   second reader today, but keeping the shape consistent with every other
   migrated Creation panel (roomBatch.svelte.js, sheetState.svelte.js) beats
   a one-off local-state exception. */

export const npcAgentState = $state({
  loading: false,
  loadError: '',
  openBatchId: null,
  locations: [],
  selectedRoot: null,
  preview: null,
  groupBrief: '',
  lines: [],
  launchError: '',
  launchErrorReopen: false,
});

export function resetNpcAgent() {
  npcAgentState.loading = false;
  npcAgentState.loadError = '';
  npcAgentState.openBatchId = null;
  npcAgentState.locations = [];
  npcAgentState.selectedRoot = null;
  npcAgentState.preview = null;
  npcAgentState.groupBrief = '';
  npcAgentState.lines = [];
  npcAgentState.launchError = '';
  npcAgentState.launchErrorReopen = false;
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/** index.html's npcAgentCheckOpenBatch, minus the badge DOM write -- the
 *  component signals the (still-legacy) badge reactively off
 *  npcAgentState.openBatchId now (NpcAgent.svelte's own effect), instead of
 *  this function reaching into the DOM directly. */
export async function checkOpenBatch() {
  try {
    const data = await api('/api/npc-batches');
    const open = (data.batches || []).find((b) => b.status === 'open');
    npcAgentState.openBatchId = open ? open.id : null;
  } catch {
    npcAgentState.openBatchId = null;
  }
}

/** index.html's npcAgentRenderLauncher, minus the paint call -- fetches
 *  locations and resets the launcher's own draft fields. Called from
 *  NpcAgent.svelte's mount/reset effects, not from a toggle click any more
 *  (the -d rule: mounting into a display:none container is fine). */
export async function initLauncher() {
  npcAgentState.loading = true;
  npcAgentState.loadError = '';
  try {
    npcAgentState.locations = await api('/api/locations');
  } catch (e) {
    npcAgentState.loading = false;
    npcAgentState.loadError = e.message;
    return;
  }
  npcAgentState.loading = false;
  npcAgentState.selectedRoot = null;
  npcAgentState.preview = null;
  npcAgentState.groupBrief = '';
  npcAgentState.lines = [{ count: 1, description: '', faction_id: null, location_id: null }];
}

export function selectRoot(locId) {
  npcAgentState.selectedRoot = locId;
  npcAgentState.preview = null;
}

export async function previewRoot() {
  try {
    npcAgentState.preview = await api(`/api/npc-batches/preview?root_location_id=${encodeURIComponent(npcAgentState.selectedRoot)}`);
    npcAgentState.launchError = '';
  } catch (e) {
    npcAgentState.preview = null;
    npcAgentState.launchError = e.message;
  }
}

export function addLine() {
  npcAgentState.lines.push({ count: 1, description: '', faction_id: null, location_id: null });
}

export function removeLine(i) {
  npcAgentState.lines.splice(i, 1);
}

export function editLine(i, field, value) {
  npcAgentState.lines[i][field] = value;
}

/** index.html's _npcAgentLineTotal -- a pure function of the lines it's
 *  given (NpcAgent.svelte derives it off npcAgentState.lines) rather than a
 *  zero-arg global reader, so it needs no state import of its own. */
export function lineTotal(lines) {
  return lines.reduce((sum, l) => sum + (Number(l.count) || 0), 0);
}

export async function launch() {
  npcAgentState.launchError = '';
  npcAgentState.launchErrorReopen = false;
  try {
    const batch = await api('/api/npc-batches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        root_location_id: npcAgentState.selectedRoot,
        group_brief: npcAgentState.groupBrief,
        lines: npcAgentState.lines,
      }),
    });
    npcAgentState.openBatchId = batch.id;
    // Commit 3 wires npcAgentLoadBatch(batch.id)'s replacement onto this
    // same success path, moving the panel onto the review surface.
  } catch (e) {
    if (e.message && e.message.includes('already open')) {
      npcAgentState.launchError = 'Un lot est déjà ouvert.';
      npcAgentState.launchErrorReopen = true;
    } else {
      npcAgentState.launchError = e.message;
    }
  }
}

/** The launcher's half of index.html's inline reopen button
 *  (`npcAgentCheckOpenBatch().then(() => npcAgentLoadBatch(npcAgentOpenBatchId))`)
 *  -- the loadBatch half lands in commit 3, which extends this function
 *  rather than adding a second reopen path. */
export async function reopenExisting() {
  await checkOpenBatch();
}
