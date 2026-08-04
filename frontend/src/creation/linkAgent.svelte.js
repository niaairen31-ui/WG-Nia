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
   added the launcher's state and functions. This commit (2) adds the
   run-loop/review/coherence state and the functions that operate on it, and
   rewires launch()/reopenExisting() onto loadBatch() so a freshly launched
   or reopened batch reaches the review surface -- commit 1's own documented
   gap, closed here.

   The run loop's termination protocol is preserved exactly as the legacy
   linkAgentRunLoop wrote it: it reads `result.done` and updates
   `linkAgentState.batch.pairs_done` per iteration, never the error-string
   protocol npcAgent's own run driver uses. BRIEF-0059-f named that
   divergence a backend-contract difference and a deliberate deferral; this
   commit does not touch npcAgent's loop, and this loop is not touched to
   match it.

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

/** "Lancer" both opens the batch AND starts the run loop (brief item 1+2
 *  are one click) -- the loop runs unawaited so progress paints live,
 *  exactly as the legacy linkAgentLaunch did. */
export async function launch() {
  linkAgentState.launchError = '';
  linkAgentState.launchErrorReopen = false;
  try {
    const batch = await api('/api/link-batches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root_location_ids: Array.from(linkAgentState.checkedRoots) }),
    });
    linkAgentState.openBatchId = batch.id;
    await loadBatch(batch.id);
    runLoop();
  } catch (e) {
    if (e.message && e.message.includes('already open')) {
      linkAgentState.launchError = 'Un lot est déjà ouvert.';
      linkAgentState.launchErrorReopen = true;
    } else {
      linkAgentState.launchError = e.message;
    }
  }
}

/** index.html's inline reopen button
 *  (`linkAgentCheckOpenBatch().then(() => linkAgentLoadBatch(linkAgentOpenBatchId))`),
 *  now that loadBatch exists (commit 1's own documented gap). */
export async function reopenExisting() {
  await checkOpenBatch();
  if (linkAgentState.openBatchId) await loadBatch(linkAgentState.openBatchId);
}

/* ── Run loop: sequential fetch of run-next until {done:true} ─────────────── */

export async function runLoop() {
  if (!linkAgentState.batch || linkAgentState.loopRunning) return;
  linkAgentState.loopRunning = true;
  linkAgentState.failedPair = null;
  while (linkAgentState.loopRunning) {
    let result;
    try {
      result = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/run-next`, { method: 'POST' });
    } catch (e) {
      linkAgentState.loopRunning = false;
      linkAgentState.failedPair = { message: e.message };
      return;
    }
    if (result.done) {
      linkAgentState.loopRunning = false;
      await loadBatch(linkAgentState.batch.id);
      return;
    }
    linkAgentState.batch.pairs_done = result.pairs_done;
  }
}

export function pause() {
  linkAgentState.loopRunning = false;
}

export function retry() {
  linkAgentState.failedPair = null;
  runLoop();
}

/* ── Review surface: GET /api/link-batches/{id}, grouped by pair ─────────── */

export async function loadBatch(batchId) {
  linkAgentState.loading = true;
  linkAgentState.loadError = '';
  try {
    const data = await api(`/api/link-batches/${encodeURIComponent(batchId)}`);
    linkAgentState.batch = data.batch;
    linkAgentState.rows = data.rows;
    linkAgentState.openBatchId = linkAgentState.batch.status === 'open' ? linkAgentState.batch.id : null;
    // Names aren't stored on the batch/rows -- re-derive via /preview over
    // the batch's OWN root_location_ids rather than adding a new endpoint.
    const rootIds = (linkAgentState.batch.scope && linkAgentState.batch.scope.root_location_ids) || [];
    try {
      const preview = await api('/api/link-batches/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root_location_ids: rootIds }),
      });
      const names = {};
      preview.npcs.forEach((n) => { names[n.id] = n.name; });
      linkAgentState.npcNames = names;
    } catch { linkAgentState.npcNames = {}; }
  } catch (e) {
    linkAgentState.loading = false;
    linkAgentState.loadError = e.message;
    return;
  }
  linkAgentState.loading = false;
}

export function npcName(id) {
  return linkAgentState.npcNames[id] || id;
}

/** index.html's _linkAgentGroupRows -- returns [key, rows[]] pairs in
 *  first-seen order (a Map preserves insertion order; LinkAgent.svelte
 *  iterates the array form directly, npcAgent.svelte.js's groupRows
 *  precedent). `key` is `pair_a_id::pair_b_id`, unpacked by the consumer. */
export function groupRows(rows) {
  const groups = new Map();
  for (const row of rows) {
    const key = `${row.pair_a_id}::${row.pair_b_id}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return Array.from(groups.entries());
}

export async function editField(rowId, field, value) {
  try {
    const row = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/rows/${encodeURIComponent(rowId)}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload: { [field]: value } }),
    });
    const idx = linkAgentState.rows.findIndex((r) => r.id === rowId);
    if (idx !== -1) linkAgentState.rows[idx] = row;
  } catch (e) {
    alert(e.message);
  }
}

export async function toggleReject(rowId, currentlyRejected) {
  try {
    const row = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/rows/${encodeURIComponent(rowId)}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_status: currentlyRejected ? 'proposed' : 'rejected' }),
    });
    const idx = linkAgentState.rows.findIndex((r) => r.id === rowId);
    if (idx !== -1) linkAgentState.rows[idx] = row;
  } catch (e) {
    alert(e.message);
  }
}

/* ── Coherence block + commit ──────────────────────────────────────────── */

export async function runCoherence() {
  try {
    const result = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/coherence`, { method: 'POST' });
    linkAgentState.batch.coherence_status = result.coherence_status;
    linkAgentState.batch.coherence_findings = result.findings;
  } catch (e) {
    alert(e.message);
  }
}

/** A finding whose patch targets a STAGED row mutates that row's payload --
 *  reload the batch so the pair group shows the patched value; a CANON
 *  patch only flips this finding's own applied_at/badge, no row refresh. */
export async function applyFinding(index) {
  try {
    const finding = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/findings/${index}/apply`, { method: 'POST' });
    if (finding.target && finding.target.scope === 'staged') {
      await loadBatch(linkAgentState.batch.id);
      return;
    }
    const findings = linkAgentState.batch.coherence_findings.slice();
    findings[index] = finding;
    linkAgentState.batch.coherence_findings = findings;
  } catch (e) {
    alert(e.message);
  }
}

/** `legacyDoc` is a parameter, not an import -- see this file's header. */
export async function commit(legacyDoc) {
  try {
    const result = await api(`/api/link-batches/${encodeURIComponent(linkAgentState.batch.id)}/commit`, { method: 'POST' });
    linkAgentState.commitResult = `${result.committed.length} lien(s) committé(s)` +
      (result.skipped.length ? `, ${result.skipped.length} ignoré(s) (conflit)` : '');
    await loadBatch(linkAgentState.batch.id);
    // TICKET-0058 (BRIEF-0058-c, M8): the graph's own reload entry point is
    // the relations consumer's graph:invalidate seam -- dispatched on
    // legacyDoc since graph/mount.js's listener lives inside the legacy
    // iframe document (RoomBatch.svelte/Sheet.svelte's own precedent for a
    // Creation island triggering this seam).
    legacyDoc.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'relations' } }));
  } catch (e) {
    linkAgentState.commitResult = e.message;
  }
}
