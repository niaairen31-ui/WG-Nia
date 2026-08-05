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

   Commit 2 ports: _promptsConfirmDiscard (as confirmDiscard),
   promptsEnterEditMode (as enterEditMode), promptsCancelEdit (as
   cancelEdit), promptsEditInput (as editInput), promptsSaveEdit (as
   saveEdit), _promptsRefreshDetail (as refreshDetail), plus
   undeclaredTokens backing _promptsUpdateEditHint (a pure computation
   here, not a DOM-mutating function -- Prompts.svelte reads it directly
   in the template instead of an imperative hint-element update).
   resetEditState now actually resets something.

   _promptsConfirmDiscard's real call sites, verified against this tree's
   pre-port index.html (NOT the brief's prose, which named three more that
   the actual code never had): _promptsWorldReset, promptsSelectDetail,
   promptsCancelEdit -- three, not six. promptsChangeModel,
   promptsToggleHistory, promptsSelectHistoryVersion and
   promptsRestoreVersion never called the guard in this codebase; this
   port does not add it to them -- a faithful port reproduces what the
   code does, not what a brief's summary implied it does. */
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
  // Edit mode (BRIEF-0011-b) -- client-side draft state only; nothing
  // survives a reload or a prompt/world switch (no-draft-persistence
  // doctrine).
  editMode: false,
  editDirty: false,
  editDraftSystem: '',
  editDraftUser: '',
  editDraftNote: '',
  saveError: null,
});

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/** Shared X1 dirty guard -- true if it's safe to discard the current edit. */
export function confirmDiscard() {
  return !promptsState.editDirty || confirm('Unsaved prompt edit will be lost — continue?');
}

/** Resets edit client state (BRIEF-0011-b) -- called on every prompt
 *  selection and on world-switch reset, after the X1 dirty guard. Commit 3
 *  extends this further with history-state fields once they exist. */
export function resetEditState() {
  promptsState.editMode = false;
  promptsState.editDirty = false;
  promptsState.editDraftSystem = '';
  promptsState.editDraftUser = '';
  promptsState.editDraftNote = '';
  promptsState.saveError = null;
}

/** World-switch reset. Unlike the legacy version (which only cleared
 *  in-memory state, relying on a SEPARATE forced showCreationSubTab ->
 *  loader re-invocation to actually refetch), this island has exactly one
 *  reset+reload trigger left (Prompts.svelte's own $effect), so it must
 *  also perform the reload -- loadList() below already resets usages/
 *  selectedId/currentDetail and does the fetches; this adds the two fields
 *  loadList doesn't touch. */
export async function worldReset(onCwReload) {
  if (!confirmDiscard()) return;
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
  if (!confirmDiscard()) return;
  resetEditState();
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

export function enterEditMode() {
  if (!promptsState.currentDetail) return;
  promptsState.editMode = true;
  promptsState.editDirty = false;
  promptsState.editDraftSystem = promptsState.currentDetail.system_prompt;
  promptsState.editDraftUser = promptsState.currentDetail.user_template;
  promptsState.editDraftNote = '';
  promptsState.saveError = null;
}

export function cancelEdit() {
  if (!confirmDiscard()) return;
  promptsState.editMode = false;
  promptsState.editDirty = false;
  promptsState.saveError = null;
}

/** Draft input handler -- updates client state (never left to the DOM
 *  alone, so drafts survive an incidental full-pane re-render). The
 *  advisory undeclared-token hint (Scope IN 2 -- never blocks Save) is
 *  computed by undeclaredTokens() below, read directly by the template
 *  instead of imperatively pushed into a hint element. */
export function editInput(field, value) {
  if (field === 'system') promptsState.editDraftSystem = value;
  else if (field === 'user') promptsState.editDraftUser = value;
  else if (field === 'note') promptsState.editDraftNote = value;
  promptsState.editDirty = true;
}

export function undeclaredTokens(detail, draftSystem, draftUser) {
  if (!detail) return [];
  const declared = new Set(Array.isArray(detail.variables) ? detail.variables : []);
  const tokens = new Set([...extractTokens(draftSystem), ...extractTokens(draftUser)]);
  return [...tokens].filter((t) => !declared.has(t));
}

/** Save (C1 is the sole authoritative gate; this call may 422). On success,
 *  never patch `currentDetail` locally -- refetch through the server
 *  (fidelity doctrine, same as the model PATCH handler), which also picks
 *  up the new version number for free. On failure, stay in edit mode with
 *  drafts intact and the server's message set in promptsState.saveError
 *  for the caller to render inline. */
export async function saveEdit(promptId) {
  try {
    await api(`/api/prompts/${promptId}/text`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_prompt: promptsState.editDraftSystem,
        user_template: promptsState.editDraftUser,
        note: promptsState.editDraftNote.trim() || undefined,
      }),
    });
    promptsState.editMode = false;
    promptsState.editDirty = false;
    promptsState.saveError = null;
    await refreshDetail(promptId);
  } catch (e) {
    promptsState.saveError = e.message;
  }
}

/** Post-write refresh (save or restore) -- refetches the head and
 *  re-syncs the list row's version, then re-renders once. Never a
 *  locally-patched draft standing in for the server's canonical read.
 *  Commit 3 extends this to also refresh an open history list. */
export async function refreshDetail(promptId) {
  try {
    promptsState.currentDetail = await api(`/api/prompts/${promptId}`);
  } catch (e) {
    promptsState.detailError = e.message;
    return;
  }
  for (const u of promptsState.usages) {
    const row = (u.rows || []).find((r) => r.id === promptId);
    if (row) row.version = promptsState.currentDetail.version;
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
