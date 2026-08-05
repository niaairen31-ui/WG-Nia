/* TICKET-0059 (BRIEF-0059-i). Non-render state + API calls for the Prompts
   tab -- faithful port of the module-level `let promptsX` globals and the
   non-render prompts* functions (index.html, deleted incrementally as each
   commit ports its slice). Prompts.svelte holds rendering + the dirty-guard
   call sites; this module holds the state shape and the fetch/mutate calls
   that operate on it.

   Commit 1 ports: _promptsResetEditState (as resetEditState),
   _promptsWorldReset (as worldReset), _promptsFetchOllamaModels,
   promptsLoadList (as loadList), promptsSelectDetail (as selectDetail),
   promptsChangeModel (as changeModel), plus the extractTokens/
   highlightSegments pair backing _promptsExtractTokens/
   _promptsHighlightTokens (the latter ported as a segment list, not an
   {@html} string -- see Prompts.svelte's header).

   _promptsConfirmDiscard is a COMMIT 2 port (it guards a dirty edit, and
   edit mode doesn't exist until commit 2 adds it) -- worldReset/
   selectDetail/changeModel do NOT call a guard yet, matching the brief's
   own account of commit 2's job: retrofit the guard onto each of these
   three call sites once _promptsConfirmDiscard exists. resetEditState is
   correspondingly a no-op for now -- there is no edit/history state yet to
   clear; commit 2 and commit 3 each extend it as they add their own
   fields, the same incremental-growth shape sheetState.svelte.js followed
   across BRIEF-0059-e's three commits. */
export const promptsState = $state({
  usages: [],
  selectedId: null,
  listError: '',
  // null = unknown/unreachable; [] = reachable, empty -- a three-state,
  // not a boolean; live-refetched on every list load and detail open,
  // never cached (Scope OUT: no caching "improvement").
  ollamaModels: null,
  ollamaError: null,
  currentDetail: null,
  detailError: '',
  modelError: '',
});

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/** No-op in commit 1 -- see the module header. */
export function resetEditState() {
}

/** World-switch reset. Unlike the legacy version (which only cleared
 *  in-memory state, relying on a SEPARATE forced showCreationSubTab ->
 *  loader re-invocation to actually refetch), this island has exactly one
 *  reset+reload trigger left (Prompts.svelte's own $effect), so it must
 *  also perform the reload -- loadList() below already resets usages/
 *  selectedId/currentDetail and does the fetches; this adds the two fields
 *  loadList doesn't touch. */
export async function worldReset(onCwReload) {
  promptsState.ollamaModels = null;
  promptsState.ollamaError = null;
  resetEditState();
  await loadList(onCwReload);
}

export async function fetchOllamaModels() {
  try {
    const data = await api('/api/ollama/models');
    promptsState.ollamaModels = data.models || [];
    promptsState.ollamaError = null;
  } catch (e) {
    promptsState.ollamaModels = null;
    promptsState.ollamaError = e.message;
  }
}

/** `onCwReload`, when given, is called unconditionally before the list
 *  fetch -- reproduces promptsLoadList's unguarded `cwLoadConfig()` call,
 *  the "child loads when the parent loads" coupling (Scope IN item 2). */
export async function loadList(onCwReload) {
  promptsState.usages = [];
  promptsState.selectedId = null;
  promptsState.currentDetail = null;
  promptsState.listError = '';
  if (onCwReload) onCwReload();
  await fetchOllamaModels();
  try {
    const data = await api('/api/prompts');
    promptsState.usages = data.usages || [];
  } catch (e) {
    promptsState.listError = e.message;
  }
}

export async function selectDetail(promptId) {
  promptsState.selectedId = promptId;
  promptsState.currentDetail = null;
  promptsState.detailError = '';
  promptsState.modelError = '';
  await fetchOllamaModels();
  try {
    promptsState.currentDetail = await api(`/api/prompts/${promptId}`);
  } catch (e) {
    promptsState.detailError = e.message;
  }
}

/** PATCH model override for the currently-shown detail row, then patch the
 *  in-memory detail + list rows from the response alone (no refetch of the
 *  full detail -- C3, same as the legacy version). Throws on failure so the
 *  caller (Prompts.svelte) can revert its own bound <select> value -- the
 *  DOM revert is a rendering concern, not this module's. */
export async function changeModel(promptId, value) {
  const updated = await api(`/api/prompts/${promptId}/model`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: value === '' ? null : value }),
  });
  if (promptsState.currentDetail && promptsState.currentDetail.id === promptId) {
    promptsState.currentDetail.model = updated.model;
    promptsState.currentDetail.effective_model = updated.effective_model;
  }
  for (const u of promptsState.usages) {
    const row = (u.rows || []).find((r) => r.id === promptId);
    if (row) row.model = updated.model;
  }
}

/** {token} scan -- regex-only, no eval; used both for highlighting and for
 *  declared/actual variable drift detection (display-only). */
export function extractTokens(text) {
  const found = new Set();
  (text || '').replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (_m, name) => { found.add(name); return _m; });
  return found;
}

/** Splits text into {text, isToken} segments so the component can render
 *  <mark> around each {token} as real markup -- the Svelte-native
 *  equivalent of _promptsHighlightTokens' `<mark>` string-building, without
 *  an {@html} sink. */
export function highlightSegments(text) {
  const segments = [];
  const re = /\{[a-zA-Z_][a-zA-Z0-9_]*\}/g;
  let last = 0;
  let m;
  const s = text || '';
  while ((m = re.exec(s))) {
    if (m.index > last) segments.push({ text: s.slice(last, m.index), isToken: false });
    segments.push({ text: m[0], isToken: true });
    last = m.index + m[0].length;
  }
  if (last < s.length) segments.push({ text: s.slice(last), isToken: false });
  return segments;
}
