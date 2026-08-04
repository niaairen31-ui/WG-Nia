/* TICKET-0059 (BRIEF-0059-g). The NPC link agent's non-render logic --
   was the linkAgentOpen/linkAgentOpenBatchId/linkAgentLocations/
   linkAgentCheckedRoots/linkAgentPreview/linkAgentBatch/linkAgentRows/
   linkAgentNpcNames/linkAgentLoopRunning/linkAgentFailedPair/
   linkAgentCommitResult module-level `let`s plus every linkAgent* function
   except linkAgentToggle (index.html, deleted across this brief's two
   commits). `_linkAgentTreeHtml` was never ported -- LocationTree.svelte
   (BRIEF-0059-f commit 1) replaces it outright, consumed here with a
   checkbox row snippet instead of npcAgent's radio one (Amendment 1's row-
   snippet seam, proven on its second consumer).

   Grown across this brief's two commits rather than authored whole
   (npcAgent.svelte.js's own precedent, TICKET-0059 BRIEF-0059-f): commit 1
   (this state) adds the launcher's state and functions. Commit 2 adds the
   run-loop/review/coherence state and the functions that operate on it, and
   rewires launch()/reopenExisting() onto loadBatch() so a freshly launched
   or reopened batch reaches the review surface -- this commit's own
   documented gap, closed there.

   The checked-set stays a `Set`, per the brief's own item 2: a `$state`
   Set's mutations aren't guaranteed visible in Svelte 5 unless the whole
   value is reassigned. toggleLocation therefore builds a fresh Set and
   reassigns `linkAgentState.checkedRoots` rather than mutating the
   existing one in place -- the ancestor-walk predicate below reads
   `.has()` off whatever value the property currently holds, so a
   reassignment is exactly what a `$derived`/render read needs to notice.

   This module never reaches into the legacy window itself -- it is the
   RECEIVING end of npcAgent.svelte.js's J1 handoff (generateLinks() there
   imports loadBatch from here directly, commit 2), not a caller of
   legacyCall/legacyContainer. commit()'s own graph:invalidate dispatch
   (commit 2) takes `legacyDoc` as a parameter from the component instead,
   the same shape generatePanel.svelte.js's applyGeneratedDraft(legacyDoc,
   ...) already established for a `.svelte.js` module that needs the legacy
   document without owning a bridge import of its own. */

export const linkAgentState = $state({
  loading: false,
  loadError: '',
  openBatchId: null,
  locations: [],
  checkedRoots: new Set(),
  preview: null,
  launchError: '',
  launchErrorReopen: false,
  batch: null,
  rows: [],
  npcNames: {},
  loopRunning: false,
  failedPair: null,
  commitResult: null,
});

export function resetLinkAgent() {
  linkAgentState.loading = false;
  linkAgentState.loadError = '';
  linkAgentState.openBatchId = null;
  linkAgentState.locations = [];
  linkAgentState.checkedRoots = new Set();
  linkAgentState.preview = null;
  linkAgentState.launchError = '';
  linkAgentState.launchErrorReopen = false;
  linkAgentState.batch = null;
  linkAgentState.rows = [];
  linkAgentState.npcNames = {};
  linkAgentState.loopRunning = false;
  linkAgentState.failedPair = null;
  linkAgentState.commitResult = null;
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/** index.html's linkAgentCheckOpenBatch, minus the badge DOM write -- the
 *  component signals the (still-legacy) badge reactively off
 *  linkAgentState.openBatchId now (LinkAgent.svelte's own effect), instead
 *  of this function reaching into the DOM directly. */
export async function checkOpenBatch() {
  try {
    const data = await api('/api/link-batches');
    const open = (data.batches || []).find((b) => b.status === 'open');
    linkAgentState.openBatchId = open ? open.id : null;
  } catch {
    linkAgentState.openBatchId = null;
  }
}

/** index.html's linkAgentRenderLauncher, minus the paint call -- fetches
 *  locations and resets the launcher's own draft fields. Called from
 *  LinkAgent.svelte's mount/reset effects, not from a toggle click any more
 *  (the -d rule: mounting into a display:none container is fine). */
export async function initLauncher() {
  linkAgentState.loading = true;
  linkAgentState.loadError = '';
  try {
    linkAgentState.locations = await api('/api/locations');
  } catch (e) {
    linkAgentState.loading = false;
    linkAgentState.loadError = e.message;
    return;
  }
  linkAgentState.loading = false;
  linkAgentState.checkedRoots = new Set();
  linkAgentState.preview = null;
  linkAgentState.commitResult = null;
}

/** index.html's _linkAgentIsChecked -- a node is checked if the user
 *  clicked it directly, or clicked any ancestor (S1 visual mirror); only
 *  directly-clicked ids are ever sent as root_location_ids, server-side
 *  expansion stays authoritative. This is the predicate the row snippet
 *  passes as `checked` to LocationTree.svelte -- Amendment 1's whole claim
 *  that the ancestor-inheritance behaviour lives at the row, not in the
 *  traversal. */
export function isCheckedLocation(locId) {
  if (linkAgentState.checkedRoots.has(locId)) return true;
  const byId = new Map(linkAgentState.locations.map((l) => [l.id, l]));
  let current = byId.get(locId);
  while (current && current.parent_location_id) {
    if (linkAgentState.checkedRoots.has(current.parent_location_id)) return true;
    current = byId.get(current.parent_location_id);
  }
  return false;
}

export function toggleLocation(locId, checked) {
  const next = new Set(linkAgentState.checkedRoots);
  if (checked) next.add(locId);
  else next.delete(locId);
  linkAgentState.checkedRoots = next;
  linkAgentState.preview = null;
}

export async function previewRoster() {
  try {
    linkAgentState.preview = await api('/api/link-batches/preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root_location_ids: Array.from(linkAgentState.checkedRoots) }),
    });
    linkAgentState.launchError = '';
  } catch (e) {
    linkAgentState.preview = null;
    linkAgentState.launchError = e.message;
  }
}

/** "Lancer" both opens the batch AND starts the run loop in the original --
 *  commit 2 wires the run loop back on once runLoop()/loadBatch() exist
 *  here; until then this only marks the batch open (same gap
 *  npcAgent.svelte.js's launch() documented across BRIEF-0059-f's commits
 *  2-3), so the badge and reopen path are correct even though the review
 *  surface doesn't render yet. */
export async function launch() {
  linkAgentState.launchError = '';
  linkAgentState.launchErrorReopen = false;
  try {
    const batch = await api('/api/link-batches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root_location_ids: Array.from(linkAgentState.checkedRoots) }),
    });
    linkAgentState.openBatchId = batch.id;
    // Commit 2 wires loadBatch(batch.id) + runLoop() onto this same
    // success path, moving the panel onto the review surface.
  } catch (e) {
    if (e.message && e.message.includes('already open')) {
      linkAgentState.launchError = 'Un lot est déjà ouvert.';
      linkAgentState.launchErrorReopen = true;
    } else {
      linkAgentState.launchError = e.message;
    }
  }
}

/** The launcher's half of index.html's inline reopen button
 *  (`linkAgentCheckOpenBatch().then(() => linkAgentLoadBatch(linkAgentOpenBatchId))`)
 *  -- the loadBatch half lands in commit 2, which extends this function
 *  rather than adding a second reopen path (npcAgent.svelte.js's
 *  reopenExisting precedent). */
export async function reopenExisting() {
  await checkOpenBatch();
}
