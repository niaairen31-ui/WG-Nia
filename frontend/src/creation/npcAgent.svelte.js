/* TICKET-0059 (BRIEF-0059-f). The NPC group agent's non-render logic --
   was the npcAgentOpenBatchId/npcAgentLocations/npcAgentSelectedRoot/
   npcAgentPreview/npcAgentGroupBrief/npcAgentLines/npcAgentBatch/npcAgentRows/
   npcAgentLoopRunning/npcAgentFailedRun/npcAgentCommitResult/
   npcAgentLinkHandoffMsg module-level `let`s plus every npcAgent* function
   except npcAgentToggle (index.html, all deleted across this brief's
   commits 2-3). `_npcAgentTreeHtml` was never ported -- LocationTree.svelte
   (commit 1) replaces it outright. `_npcAgentLineRowHtml`/
   `_npcAgentPaintLauncher`/`_npcAgentRowHtml`/`_npcAgentGroupHtml`/
   `_npcAgentPaintReview` are not ported either: Svelte's own declarative
   markup (NpcAgent.svelte) replaces the innerHTML-painting they did.

   Grown across this brief's two remaining commits rather than authored
   whole (sheetState.svelte.js's own precedent, TICKET-0059 BRIEF-0059-e):
   commit 2 added the launcher's state and functions. This commit (3) adds
   the run-loop/review state (batch/rows/loopRunning/failedRun/
   commitResult/linkHandoffMsg) and the functions that operate on it, and
   wires launch()/reopenExisting() (both already present) onto loadBatch()
   so a freshly launched or reopened batch reaches the review surface --
   commit 2's own documented gap, closed here.

   generateLinks()'s J1 handoff is this module's one remaining reach into
   the link agent. At the time this comment was first written (BRIEF-0059-f
   commit 3), linkAgentLoadBatch was still a legacy global and a Svelte
   module cannot assign a `let` binding declared in index.html's top-level
   script -- it isn't a `window` property (frontend/src/legacy/bridge.js's
   own comment) -- so the handoff went through legacyCall('linkAgentToggle')/
   legacyCall('linkAgentLoadBatch', ...). BRIEF-0059-g commit 2 ported
   linkAgentLoadBatch to frontend/src/creation/linkAgent.svelte.js's
   loadBatch export, so the load half of the handoff is now a plain
   Svelte-to-Svelte import -- bridge.js's own selectRecord/
   getSelectedCharacterId comment already names this as the expected end
   state once both sides of a legacy bridge-reach converge. The toggle half
   stays a legacyCall: linkAgentToggle is chrome (retires at -l), so opening
   the panel still means flipping the still-legacy button's own state.
   legacyContainer reads the panel's current display style directly (a
   plain DOM read, not a bridge-reach site) so the toggle call only fires
   when the panel is actually closed -- calling linkAgentToggle
   unconditionally would CLOSE an already-open panel (it flips, it does not
   set).

   State is module-level (not NpcAgent.svelte-local) for the same reason
   RoomBatch's roomBatchState is: TICKET-0059's BRIEF-0059-f doesn't need a
   second reader today, but keeping the shape consistent with every other
   migrated Creation panel (roomBatch.svelte.js, sheetState.svelte.js) beats
   a one-off local-state exception. */
import { legacyCall, legacyContainer } from '../legacy/bridge.js';
import { loadBatch as loadLinkBatch } from './linkAgent.svelte.js';

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
  batch: null,
  rows: [],
  loopRunning: false,
  failedRun: null,
  commitResult: null,
  linkHandoffMsg: null,
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
  npcAgentState.batch = null;
  npcAgentState.rows = [];
  npcAgentState.loopRunning = false;
  npcAgentState.failedRun = null;
  npcAgentState.commitResult = null;
  npcAgentState.linkHandoffMsg = null;
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
    await loadBatch(batch.id);
  } catch (e) {
    if (e.message && e.message.includes('already open')) {
      npcAgentState.launchError = 'Un lot est déjà ouvert.';
      npcAgentState.launchErrorReopen = true;
    } else {
      npcAgentState.launchError = e.message;
    }
  }
}

/** index.html's inline reopen button
 *  (`npcAgentCheckOpenBatch().then(() => npcAgentLoadBatch(npcAgentOpenBatchId))`),
 *  now that loadBatch exists. */
export async function reopenExisting() {
  await checkOpenBatch();
  if (npcAgentState.openBatchId) await loadBatch(npcAgentState.openBatchId);
}

/* ── Run driver: "Suivant" (one unit) / "Tout générer" (loop until 409/error) ── */

/** run-next's response is just {line_index, name, npcs_done, npcs_total} --
 *  the newly staged row itself isn't in it, so every successful call
 *  re-fetches batch+rows (GET, not the heavier loadBatch which also
 *  re-fetches /preview) before the reactive repaint, or the review list
 *  would never show the row that was just generated. */
async function refreshRows() {
  const data = await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}`);
  npcAgentState.batch = data.batch;
  npcAgentState.rows = data.rows;
}

export async function runOne() {
  try {
    await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/run-next`, { method: 'POST' });
    npcAgentState.failedRun = null;
    await refreshRows();
  } catch (e) {
    if (e.message && e.message.includes('already fully generated')) {
      await loadBatch(npcAgentState.batch.id);
      return;
    }
    npcAgentState.failedRun = { message: e.message };
  }
}

export async function runLoop() {
  if (!npcAgentState.batch || npcAgentState.loopRunning) return;
  npcAgentState.loopRunning = true;
  npcAgentState.failedRun = null;
  while (npcAgentState.loopRunning) {
    try {
      await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/run-next`, { method: 'POST' });
    } catch (e) {
      npcAgentState.loopRunning = false;
      if (e.message && e.message.includes('already fully generated')) {
        await loadBatch(npcAgentState.batch.id);
      } else {
        npcAgentState.failedRun = { message: e.message };
      }
      return;
    }
    await refreshRows();
  }
}

export function pause() {
  npcAgentState.loopRunning = false;
}

export function retryRun() {
  npcAgentState.failedRun = null;
  runLoop();
}

/* ── Review surface: GET /api/npc-batches/{id}, grouped by line_index ────── */

export async function loadBatch(batchId) {
  npcAgentState.loading = true;
  npcAgentState.loadError = '';
  try {
    const data = await api(`/api/npc-batches/${encodeURIComponent(batchId)}`);
    npcAgentState.batch = data.batch;
    npcAgentState.rows = data.rows;
    npcAgentState.openBatchId = npcAgentState.batch.status === 'open' ? npcAgentState.batch.id : null;
    // Faction/location names for the review selects aren't stored on the
    // batch/rows -- re-derive via /preview over the batch's OWN
    // root_location_id, same precedent as linkAgentLoadBatch's name lookup.
    try {
      npcAgentState.preview = await api(`/api/npc-batches/preview?root_location_id=${encodeURIComponent(npcAgentState.batch.scope.root_location_id)}`);
    } catch { npcAgentState.preview = null; }
  } catch (e) {
    npcAgentState.loading = false;
    npcAgentState.loadError = e.message;
    return;
  }
  npcAgentState.loading = false;
}

/** index.html's _npcAgentGroupRows -- returns [lineIndex, rows[]] pairs in
 *  first-seen order (a Map preserves insertion order; NpcAgent.svelte
 *  iterates the array form directly). */
export function groupRows(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.line_index)) groups.set(row.line_index, []);
    groups.get(row.line_index).push(row);
  }
  return Array.from(groups.entries());
}

/** index.html's _npcAgentGroupHtml's own description lookup, split out of
 *  the (retired) paint function. */
export function groupDescription(batch, lineIndex) {
  const line = ((batch.scope && batch.scope.lines) || [])[lineIndex];
  return line ? line.description : `ligne ${lineIndex}`;
}

export async function editField(rowId, field, value) {
  try {
    const row = await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/rows/${encodeURIComponent(rowId)}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload_patch: { [field]: value } }),
    });
    const idx = npcAgentState.rows.findIndex((r) => r.id === rowId);
    if (idx !== -1) npcAgentState.rows[idx] = row;
  } catch (e) {
    alert(e.message);
  }
}

export async function toggleReject(rowId, currentlyRejected) {
  try {
    const row = await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/rows/${encodeURIComponent(rowId)}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_status: currentlyRejected ? 'proposed' : 'rejected' }),
    });
    const idx = npcAgentState.rows.findIndex((r) => r.id === rowId);
    if (idx !== -1) npcAgentState.rows[idx] = row;
  } catch (e) {
    alert(e.message);
  }
}

/* ── Commit + J1 handoff to the link agent ────────────────────────────────── */

export async function commit() {
  try {
    const result = await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/commit`, { method: 'POST' });
    npcAgentState.commitResult = `${result.committed.length} PNJ committé(s)` +
      (result.skipped.length ? `, ${result.skipped.length} ignoré(s)` : '');
    npcAgentState.linkHandoffMsg = null;
    await loadBatch(npcAgentState.batch.id);
  } catch (e) {
    npcAgentState.commitResult = e.message;
  }
}

export async function abandon() {
  if (!confirm('Abandonner ce lot de PNJ ?')) return;
  try {
    await api(`/api/npc-batches/${encodeURIComponent(npcAgentState.batch.id)}/abandon`, { method: 'POST' });
    await loadBatch(npcAgentState.batch.id);
  } catch (e) {
    alert(e.message);
  }
}

/** J1 handoff: calls the EXISTING link agent creation route with this
 *  batch's own root_location_id, then opens the link agent panel on the
 *  fresh batch (loadLinkBatch -- the roster then includes both the new
 *  NPCs and pre-existing residents of the root, F1 skips canon pairs). A
 *  409 (a link batch is already open) surfaces as a plain warning banner
 *  and is never retried automatically. See this file's header for why the
 *  panel-open half still crosses the legacy bridge (chrome, linkAgentToggle)
 *  while the load half is now a direct Svelte-to-Svelte call. */
export async function generateLinks() {
  npcAgentState.linkHandoffMsg = null;
  try {
    const batch = await api('/api/link-batches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root_location_ids: [npcAgentState.batch.scope.root_location_id] }),
    });
    npcAgentState.linkHandoffMsg = null;
    if (legacyContainer('linkagent-panel').style.display === 'none') {
      legacyCall('linkAgentToggle');
    }
    await loadLinkBatch(batch.id);
  } catch (e) {
    npcAgentState.linkHandoffMsg = e.message;
  }
}
