/* TICKET-0091 (BRIEF-0091-K, Q17d). Non-render state + API calls for the
   name-resolution panel ("Noms à lier"), same shape as lore.svelte.js: a
   $state object NamesPanel.svelte renders, plus the functions that mutate it.

   `mentions` holds GET /api/lore/mentions's rows unchanged. `choices` is the
   creator's in-progress entity choice per mention id; `entities` caches the
   active world's active entities, every type, for the search.

   TICKET-0092 (BRIEF-0092-e). `record`/`recordScope` carry the per-mention
   "also record as appellation" choice sent with "Lier". `lookup` is the
   card opened from a Lore miss (Lore.svelte): a name the resolver did not
   find, recorded as an appellation of the entity the creator picks. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

// Mirror of lore_resolve.category_of_type: a type no category claims is 'other'.
const TYPE_CATEGORY = Object.freeze({
  location: 'place', character: 'person', faction: 'faction', item: 'object',
});

export const DEFAULT_SCOPE = 'rencontre';

export const namesState = $state({
  loading: false,
  error: '',
  mentions: [],
  choices: {},
  queries: {},
  record: {},
  recordScope: {},
  entities: null,
  busy: {},
  lookup: null,
});

export function categoryOf(type) {
  return TYPE_CATEGORY[type] || 'other';
}

async function loadEntities() {
  if (namesState.entities) return;
  const rows = await api('/api/entities');
  namesState.entities = rows.filter((e) => e.status === 'active');
}

export async function loadMentions() {
  namesState.loading = true;
  namesState.error = '';
  try {
    const body = await api('/api/lore/mentions');
    namesState.mentions = body.mentions;
    await loadEntities();
  } catch (e) {
    namesState.error = e.message;
  } finally {
    namesState.loading = false;
  }
}

function nearLabel(near) {
  return `${near.name} — ressemblance ${near.score} %`;
}

// Candidates, then near names, then the search results; no id twice.
function mergeOptions(groups) {
  const seen = new Set();
  const options = [];
  for (const group of groups) {
    for (const option of group) {
      if (seen.has(option.id)) continue;
      seen.add(option.id);
      options.push(option);
    }
  }
  return options;
}

export function optionsFor(mention) {
  const query = (namesState.queries[mention.id] || '').trim().toLowerCase();
  const searched = query
    ? (namesState.entities || [])
        .filter((e) => !mention.category || categoryOf(e.type) === mention.category)
        .filter((e) => e.name.toLowerCase().includes(query))
    : [];
  return mergeOptions([
    mention.candidates.map((c) => ({ id: c.id, name: c.name, type: c.type })),
    (mention.near || []).map((n) => ({ id: n.id, name: nearLabel(n), type: n.type })),
    searched.map((e) => ({ id: e.id, name: e.name, type: e.type })),
  ]);
}

// The lookup card's options: candidates, near names, then every active entity.
export function lookupOptions() {
  const lookup = namesState.lookup;
  if (!lookup) return [];
  return mergeOptions([
    lookup.candidates.map((c) => ({ id: c.id, name: c.name, type: c.type })),
    lookup.near.map((n) => ({ id: n.id, name: nearLabel(n), type: n.type })),
    (namesState.entities || []).map((e) => ({ id: e.id, name: e.name, type: e.type })),
  ]);
}

export function setQuery(mentionId, text) {
  namesState.queries = { ...namesState.queries, [mentionId]: text };
}

export function choose(mentionId, entityId) {
  namesState.choices = { ...namesState.choices, [mentionId]: entityId };
}

export function setRecord(mentionId, checked) {
  namesState.record = { ...namesState.record, [mentionId]: checked };
}

export function setRecordScope(mentionId, scope) {
  namesState.recordScope = { ...namesState.recordScope, [mentionId]: scope };
}

async function close(mentionId, path, body) {
  namesState.busy = { ...namesState.busy, [mentionId]: true };
  namesState.error = '';
  try {
    await api(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    namesState.mentions = namesState.mentions.filter((m) => m.id !== mentionId);
  } catch (e) {
    namesState.error = e.message;
  } finally {
    namesState.busy = { ...namesState.busy, [mentionId]: false };
  }
}

export function bindMention(mentionId) {
  const entityId = namesState.choices[mentionId];
  if (!entityId) return;
  return close(mentionId, `/api/lore/mentions/${encodeURIComponent(mentionId)}/resolve`, {
    entity_id: entityId,
    record_appellation: !!namesState.record[mentionId],
    scope_type: namesState.recordScope[mentionId] || DEFAULT_SCOPE,
  });
}

export function dismissMention(mentionId) {
  return close(mentionId, `/api/lore/mentions/${encodeURIComponent(mentionId)}/dismiss`, {});
}

function patchLookup(fields) {
  if (namesState.lookup) namesState.lookup = { ...namesState.lookup, ...fields };
}

export async function openLookup(surface) {
  namesState.lookup = {
    worldId: serverState.worldId, surface, candidates: [], near: [],
    choice: '', scope: DEFAULT_SCOPE, busy: true, message: '',
  };
  try {
    const body = await api(`/api/lore/names/lookup?surface=${encodeURIComponent(surface)}`);
    await loadEntities();
    patchLookup({ candidates: body.candidates, near: body.near, busy: false });
  } catch (e) {
    patchLookup({ busy: false, message: e.message });
  }
}

export function setLookupChoice(entityId) {
  patchLookup({ choice: entityId, message: '' });
}

export function setLookupScope(scope) {
  patchLookup({ scope });
}

export async function saveAppellation() {
  const lookup = namesState.lookup;
  if (!lookup || !lookup.choice || lookup.busy) return;
  patchLookup({ busy: true, message: '' });
  try {
    const body = await api('/api/lore/appellations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_id: lookup.choice, surface: lookup.surface, scope_type: lookup.scope }),
    });
    patchLookup({ busy: false, message: body.written ? 'Appellation enregistrée.' : 'Déjà connue sous ce nom.' });
  } catch (e) {
    patchLookup({ busy: false, message: e.message });
  }
}

export function closeLookup() {
  namesState.lookup = null;
}

// A lookup opened from the question tab survives the panel's mount-time
// call; only a world change clears it.
export function reloadForWorld() {
  namesState.mentions = [];
  namesState.choices = {};
  namesState.queries = {};
  namesState.record = {};
  namesState.recordScope = {};
  namesState.entities = null;
  namesState.error = '';
  if (namesState.lookup && namesState.lookup.worldId !== serverState.worldId) namesState.lookup = null;
}
