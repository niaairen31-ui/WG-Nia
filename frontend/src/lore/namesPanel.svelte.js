/* TICKET-0091 (BRIEF-0091-K, Q17d). Non-render state + API calls for the
   name-resolution panel ("Noms à lier"), same shape as lore.svelte.js: a
   $state object NamesPanel.svelte renders, plus the functions that mutate it.

   `mentions` holds GET /api/lore/mentions's rows unchanged. `choices` is the
   creator's in-progress entity choice per mention id; `entities` caches the
   active world's entities per type for the search over the category. */
import { api } from '../creation/sheetRequest.svelte.js';

// Mirror of lore_resolve._CATEGORY_ENTITY_TYPE; a NULL category searches all three.
const CATEGORY_TYPE = Object.freeze({ place: 'location', person: 'character', faction: 'faction' });

export const namesState = $state({
  loading: false,
  error: '',
  mentions: [],
  choices: {},
  queries: {},
  entities: {},
  busy: {},
});

export function typesOf(mention) {
  return mention.category && CATEGORY_TYPE[mention.category]
    ? [CATEGORY_TYPE[mention.category]]
    : Object.values(CATEGORY_TYPE);
}

async function loadEntities(types) {
  for (const type of types) {
    if (namesState.entities[type]) continue;
    const rows = await api(`/api/entities?type=${encodeURIComponent(type)}`);
    namesState.entities = { ...namesState.entities, [type]: rows.filter((e) => e.status === 'active') };
  }
}

export async function loadMentions() {
  namesState.loading = true;
  namesState.error = '';
  try {
    const body = await api('/api/lore/mentions');
    namesState.mentions = body.mentions;
    await loadEntities([...new Set(body.mentions.flatMap(typesOf))]);
  } catch (e) {
    namesState.error = e.message;
  } finally {
    namesState.loading = false;
  }
}

// Candidates first, then the category's entities matching the search text.
export function optionsFor(mention) {
  const query = (namesState.queries[mention.id] || '').trim().toLowerCase();
  const candidateIds = new Set(mention.candidates.map((c) => c.id));
  const searched = query
    ? typesOf(mention)
        .flatMap((type) => namesState.entities[type] || [])
        .filter((e) => !candidateIds.has(e.id) && e.name.toLowerCase().includes(query))
    : [];
  return [...mention.candidates, ...searched.map((e) => ({ id: e.id, name: e.name, type: e.type }))];
}

export function setQuery(mentionId, text) {
  namesState.queries = { ...namesState.queries, [mentionId]: text };
}

export function choose(mentionId, entityId) {
  namesState.choices = { ...namesState.choices, [mentionId]: entityId };
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
  return close(mentionId, `/api/lore/mentions/${encodeURIComponent(mentionId)}/resolve`, { entity_id: entityId });
}

export function dismissMention(mentionId) {
  return close(mentionId, `/api/lore/mentions/${encodeURIComponent(mentionId)}/dismiss`, {});
}

export function reloadForWorld() {
  namesState.mentions = [];
  namesState.choices = {};
  namesState.queries = {};
  namesState.entities = {};
  namesState.error = '';
}
