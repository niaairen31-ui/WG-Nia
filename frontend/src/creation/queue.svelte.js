/* TICKET-0059 (BRIEF-0059-k, commits 1-3). Module-level rune store shared by
   the Review Queue's three separate mount points -- QueueFilters.svelte
   (#creation-shell-extra: filter bar + world-tick controls, commit 1),
   Queue.svelte (#creation-queue: card list + batch verdict, commit 2) and
   QueueBatchBar.svelte (#creation-shell-batch-bar, commit 3). The filter
   crosses between the first two containers, so it cannot live inside
   either component -- one authority for one fact, per this brief's own
   instruction. This module grows across all three commits, the same
   shape npcAgent.svelte.js/linkAgent.svelte.js's own headers describe.

   Faithful port of setFilter/setFilterByName/_loadMutationEntityNames/
   _mutationEntityName/_loadMutationAgendaNames/_mutationAgendaName
   (commit 1), loadQueue/approveMutation/rejectMutation (commit 2), and
   toggleSelectAll/doBatchAction (commit 3) -- all index.html, now deleted.

   Cross-surface note (found during execution, not named in RECON-0059-a
   M5 or this brief -- the second such gap after observationOpenPrompt):
   Play's analyzeConv (index.html, #btn-analyze/#btn-force, otherwise
   untouched by this ticket) called setFilterByName('proposed') then
   loadQueue() directly as legacy globals after writing new proposals.
   Both callees are gone after this brief. Per Nia's resolution: the
   await loadQueue() half is dropped outright (it repainted a hidden
   #queue-body -- a pre-warm of an island that now loads itself on mount,
   not a behaviour worth carrying forward); the setFilterByName('proposed')
   half survives, inverted -- Play now states a fact
   ('mutations:proposed', a plain CustomEvent carrying only a count)
   instead of commanding the Queue's own filter. setFilter (below) is the
   single place that decision is made; the actual addEventListener call
   lives in frontend/src/creation/mount.js's initCreationMount, the
   established legacy-document listener-registration point (mirroring
   island:slot/island:action) -- NOT here, because bridge.js's legacy
   document handle does not exist yet when this module is first evaluated
   (app boot, before the legacy iframe has loaded); calling it at this
   module's top level would throw. mount.js already receives a ready
   legacyDoc at the right time, so it owns the addEventListener call and
   this module owns what happens when the event fires.

   This is a legacy -> Svelte edge, the opposite direction from
   legacy_call.py's bridge-reach census (Svelte -> legacy through
   bridge.js/callLegacy) -- it adds no baseline record and closes none;
   the check is structurally blind to it, not silently wrong. */

export const queueState = $state({
  currentFilter: 'proposed',
  reloadToken: 0,
  mutations: [],
  loading: true,
  loadError: '',
  selectedIds: new Set(),
  batchVerdict: null, // {cls, msg} | null
});

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export function shortId(id) { return id ? id.slice(0, 8) + '…' : ''; }

/** Sets the active filter and forces a reload -- unconditionally, even
 *  when the filter value doesn't change (a repeat click, or the post-tick /
 *  post-analysis re-assert), matching the original's own
 *  setFilter/setFilterByName + loadQueue() pairing. */
export function setFilter(status) {
  queueState.currentFilter = status;
  queueState.batchVerdict = null;
  queueState.reloadToken += 1;
}

/* Lazy entity id -> name cache (BRIEF-19), used to render resource_change's
   money/knowledge legs in human-readable form. Loaded once -- never reset
   on world switch, faithfully preserved from the original (a pre-existing
   staleness gap, not this brief's to fix). */
let _mutationEntityNames = null;

export async function loadMutationEntityNames() {
  if (_mutationEntityNames) return;
  try {
    const rows = await api('/api/entities');
    _mutationEntityNames = new Map(rows.map((e) => [e.id, e.name]));
  } catch (_err) {
    _mutationEntityNames = new Map();
  }
}

export function mutationEntityName(id) {
  if (!id) return '';
  if (_mutationEntityNames && _mutationEntityNames.has(id)) return _mutationEntityNames.get(id);
  return shortId(id);
}

/* Lazy agenda id -> title cache (TICKET-0020, BRIEF-0020-c) -- mirrors
   _mutationEntityNames, for resolving agenda_delegation's agenda_id. */
let _mutationAgendaNames = null;

export async function loadMutationAgendaNames() {
  if (_mutationAgendaNames) return;
  try {
    const rows = await api('/api/agendas');
    _mutationAgendaNames = new Map(rows.map((a) => [a.id, a.title]));
  } catch (_err) {
    _mutationAgendaNames = new Map();
  }
}

export function mutationAgendaName(id) {
  if (!id) return '';
  if (_mutationAgendaNames && _mutationAgendaNames.has(id)) return _mutationAgendaNames.get(id);
  return shortId(id);
}

/* Lazy pass_play id -> day info cache (BRIEF-0075-e, D2): resolves a
   `pass_play`-sourced mutation's day number and declaration first line so
   the queue card can link back to the day it came from, mirroring
   _mutationEntityNames/_mutationAgendaNames. `/api/days` already carries
   `pass_play_id` (day.py's `_day_dict`) alongside `day_number` and
   `declared_action` -- no new endpoint needed. */
let _mutationDayInfo = null;

export async function loadMutationDayInfo() {
  if (_mutationDayInfo) return;
  try {
    const rows = await api('/api/days');
    _mutationDayInfo = new Map(
      rows.filter((d) => d.pass_play_id).map((d) => [
        d.pass_play_id,
        { dayNumber: d.day_number, firstLine: (d.declared_action || '').split('\n')[0] },
      ])
    );
  } catch (_err) {
    _mutationDayInfo = new Map();
  }
}

export function mutationDayInfo(passPlayId) {
  if (!passPlayId) return null;
  if (_mutationDayInfo && _mutationDayInfo.has(passPlayId)) return _mutationDayInfo.get(passPlayId);
  return null;
}

/* TICKET-0059 (BRIEF-0059-k commit 2). Faithful port of loadQueue's fetch
   half (index.html, now deleted) -- the render half (renderCard and its
   helpers) lives in Queue.svelte/QueueCard.svelte, reading queueState.mutations
   directly rather than being handed a rendered string. selectedIds resets
   on every load, matching the original: a fresh #queue-body innerHTML
   rewrite always discarded the previous DOM's checkboxes too. */
export async function loadQueue() {
  queueState.loading = true;
  queueState.loadError = '';
  queueState.selectedIds = new Set();
  try {
    await Promise.all([loadMutationEntityNames(), loadMutationAgendaNames(), loadMutationDayInfo()]);
    queueState.mutations = await api('/api/mutations?status=' + queueState.currentFilter);
  } catch (e) {
    queueState.loadError = e.message;
    queueState.mutations = [];
  } finally {
    queueState.loading = false;
  }
}

export function toggleSelected(id, checked) {
  const next = new Set(queueState.selectedIds);
  if (checked) next.add(id); else next.delete(id);
  queueState.selectedIds = next;
}

/** Update card visual state after an approve/reject completes -- faithful
 *  port of markCardDone's INTENT (status flips, card leaves 'proposed'),
 *  achieved by replacing the one changed row in queueState.mutations
 *  rather than querying/mutating DOM. Unchanged rows keep their object
 *  identity, so Svelte's keyed #each never remounts their QueueCard. */
function markMutationDone(id, newStatus) {
  queueState.mutations = queueState.mutations.map((m) => (m.id === id ? { ...m, status: newStatus } : m));
  if (queueState.selectedIds.has(id)) {
    const next = new Set(queueState.selectedIds);
    next.delete(id);
    queueState.selectedIds = next;
  }
}

/* Faithful port of doApprove's request half (index.html, now deleted) --
   QueueCard.svelte owns the JSON-validation pre-check, the lock/unlock
   and the result-message display (its own local state, one card's own
   concern); this function owns the request + the shared mutation-list
   update every card's result depends on. */
export async function approveMutation(id, payloadStr, creatorNotes) {
  const data = await api('/api/mutations/' + id + '/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload: payloadStr, creator_notes: creatorNotes || null }),
  });
  let cls, msg, newStatus;
  if (data.status === 'applied') {
    cls = 'ok'; msg = '✓ Applied to canon.'; newStatus = 'applied';
  } else if (data.status === 'already_applied') {
    cls = 'warn'; msg = '⚠ Already applied.'; newStatus = 'applied';
  } else {
    // 'approved' -- reviewed but not applied; error stored server-side.
    cls = 'warn';
    msg = '⚠ Saved as "approved" (not applied to canon):\n' + (data.error || '');
    newStatus = 'approved';
  }
  markMutationDone(id, newStatus);
  return { cls, msg };
}

export async function rejectMutation(id, creatorNotes) {
  await api('/api/mutations/' + id + '/reject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ creator_notes: creatorNotes || null }),
  });
  markMutationDone(id, 'rejected');
  return { cls: 'ok', msg: '✓ Rejected. World state unchanged.' };
}

/* TICKET-0059 (BRIEF-0059-k commit 3). Faithful port of toggleSelectAll's
   intent (index.html, now deleted) -- "select all" acts on the currently
   displayed proposed rows only, matching the original's own
   `.row-select` (never a reviewed row's checkbox, since those don't
   exist). QueueBatchBar.svelte derives selectableIds from
   queueState.mutations and passes it in, rather than this module deriving
   it itself -- the mutation list's shape (which rows are selectable) is
   the batch bar's own $derived read, not a second copy of that logic here. */
export function toggleSelectAll(checked, selectableIds) {
  queueState.selectedIds = checked ? new Set(selectableIds) : new Set();
}

/** Approve / reject the selected proposed mutations as one batch --
 *  faithful port of doBatchAction (index.html, now deleted). The verdict
 *  banner is shared state (queueState.batchVerdict) because it renders in
 *  Queue.svelte's #creation-queue while the buttons that trigger it live
 *  in QueueBatchBar.svelte's #creation-shell-batch-bar -- the same
 *  cross-container reasoning this module's header describes for
 *  currentFilter. */
export async function doBatchAction(action) {
  const ids = Array.from(queueState.selectedIds);
  if (!ids.length) return;

  queueState.batchVerdict = { cls: '', msg: '⟳ Processing batch…' };
  try {
    const data = await api('/api/mutations/batch-review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, mutation_ids: ids }),
    });
    const msg = (action === 'approve')
      ? `${data.applied} applied, ${data.needs_attention} needs attention, ${data.skipped} skipped`
      : `${data.rejected} rejected, ${data.skipped} skipped`;
    queueState.batchVerdict = { cls: 'ok', msg: '✓ ' + msg };
  } catch (e) {
    queueState.batchVerdict = { cls: 'err', msg: '✗ ' + e.message };
  } finally {
    // Refresh so row statuses (and the proposed list) are current.
    await loadQueue();
  }
}
