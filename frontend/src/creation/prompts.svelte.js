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
   code does, not what a brief's summary implied it does.

   Commit 3 ports: _promptsRenderHistorySection (folded into
   Prompts.svelte's template -- no separate render function; see
   toggleHistory below), promptsToggleHistory (as toggleHistory),
   _promptsLoadHistory (as loadHistory), promptsSelectHistoryVersion (as
   selectHistoryVersion), promptsRestoreVersion (as restoreVersion),
   _promptsPopulateEntitySelectors (as fetchPreviewEntities, returning
   data instead of mutating <select> DOM directly), and
   promptsRunAssembledPreview (as runAssembledPreview). Laziness preserved
   exactly: historyVersions stays null (not fetched) until first
   expansion; toggleHistory only calls loadHistory when historyVersions is
   still null, never on every expand. saveEdit/refreshDetail are extended
   here to invalidate/reload an open history list, matching the legacy
   promptsSaveEdit/_promptsRefreshDetail's full behaviour now that history
   state exists. */
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
  // History section (V1) -- collapsed + unfetched by default; lazy on
  // first expansion, cached until a save/restore invalidates it.
  historyExpanded: false,
  historyVersions: null, // null = not fetched yet
  historyError: null,
  historySelectedVersion: null,
  historyVersionDetail: null,
  restoreError: null,
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

/** Resets edit + history client state (BRIEF-0011-b/V1) -- called on
 *  every prompt selection and on world-switch reset, after the X1 dirty
 *  guard. */
export function resetEditState() {
  promptsState.editMode = false;
  promptsState.editDirty = false;
  promptsState.editDraftSystem = '';
  promptsState.editDraftUser = '';
  promptsState.editDraftNote = '';
  promptsState.saveError = null;
  promptsState.historyExpanded = false;
  promptsState.historyVersions = null;
  promptsState.historyError = null;
  promptsState.historySelectedVersion = null;
  promptsState.historyVersionDetail = null;
  promptsState.restoreError = null;
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
    promptsState.historySelectedVersion = null;
    promptsState.historyVersionDetail = null;
    promptsState.historyVersions = null;
    await refreshDetail(promptId);
  } catch (e) {
    promptsState.saveError = e.message;
  }
}

/** Post-write refresh (save or restore) -- refetches the head, and the
 *  version list too if History is open, then re-syncs the list row's
 *  version. Never a locally-patched draft standing in for the server's
 *  canonical read. */
export async function refreshDetail(promptId) {
  try {
    promptsState.currentDetail = await api(`/api/prompts/${promptId}`);
  } catch (e) {
    promptsState.detailError = e.message;
    return;
  }
  if (promptsState.historyExpanded) {
    await loadHistory(promptId);
  }
  for (const u of promptsState.usages) {
    const row = (u.rows || []).find((r) => r.id === promptId);
    if (row) row.version = promptsState.currentDetail.version;
  }
}

/* ── History section (V1) ────────────────────────────────────────────────
 * Lazy: GET .../versions fires only on first expansion, never for a prompt
 * whose history stays collapsed. Cached until a save/restore invalidates
 * it (both null out historyVersions before refreshing). */

export async function toggleHistory(promptId) {
  promptsState.historyExpanded = !promptsState.historyExpanded;
  if (!promptsState.historyExpanded) {
    promptsState.historySelectedVersion = null;
    promptsState.historyVersionDetail = null;
    return;
  }
  if (!promptsState.historyVersions) {
    await loadHistory(promptId);
  }
}

export async function loadHistory(promptId) {
  promptsState.historyError = null;
  try {
    const data = await api(`/api/prompts/${promptId}/versions`);
    promptsState.historyVersions = data.versions || [];
  } catch (e) {
    promptsState.historyVersions = null;
    promptsState.historyError = e.message;
  }
}

export async function selectHistoryVersion(promptId, versionNumber) {
  promptsState.historySelectedVersion = versionNumber;
  promptsState.historyVersionDetail = null;
  promptsState.restoreError = null;
  try {
    promptsState.historyVersionDetail = await api(`/api/prompts/${promptId}/versions/${versionNumber}`);
  } catch (e) {
    promptsState.historyVersionDetail = null;
    promptsState.restoreError = e.message;
  }
}

/** Restores by writing a NEW version (append-only), never rewriting
 *  history -- see the POST endpoint this calls. */
export async function restoreVersion(promptId, versionNumber) {
  promptsState.restoreError = null;
  try {
    await api(`/api/prompts/${promptId}/versions/${versionNumber}/restore`, { method: 'POST' });
    promptsState.historySelectedVersion = null;
    promptsState.historyVersionDetail = null;
    promptsState.historyVersions = null;
    await refreshDetail(promptId);
  } catch (e) {
    promptsState.restoreError = e.message;
  }
}

/* ── Assembled preview (dry_run_capable usages only) ────────────────────── */

/** Fetches character entities and splits them into npc/pc buckets by
 *  playerCharIds -- returns data instead of mutating <select> DOM
 *  directly (Prompts.svelte renders the options). Failure swallowed
 *  silently, same as the legacy version: selectors stay empty, the
 *  preview button will just 400. */
export async function fetchPreviewEntities(playerCharIds) {
  try {
    const entities = await api('/api/entities?type=character');
    return {
      npcs: entities.filter((e) => !playerCharIds.has(e.id)),
      pcs: entities.filter((e) => playerCharIds.has(e.id)),
    };
  } catch (_e) {
    return { npcs: [], pcs: [] };
  }
}

export async function runAssembledPreview(usage, pcId, npcId) {
  if (!pcId) return { error: 'Choisissez un personnage joueur.' };
  if (usage === 'npc_dialogue' && !npcId) return { error: 'Choisissez un NPC.' };
  const params = new URLSearchParams({ pc_id: pcId });
  if (usage === 'npc_dialogue') params.set('npc_id', npcId);
  try {
    const data = await api(`/api/prompts/preview/${usage}?${params.toString()}`);
    const body = usage === 'npc_dialogue'
      ? data.system_prompt
      : `${data.system_prompt}\n\n=== CONTEXTE MJ ASSEMBLÉ ===\n${data.mj_context_rendered}`;
    return { body };
  } catch (e) {
    return { error: e.message };
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
