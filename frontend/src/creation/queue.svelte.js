/* TICKET-0059 (BRIEF-0059-k commit 1). Module-level rune store shared by
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
   (index.html, now deleted). loadQueue/renderCard and the batch cluster
   land here in commits 2 and 3.

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
