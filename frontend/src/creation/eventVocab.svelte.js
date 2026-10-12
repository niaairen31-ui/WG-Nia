/* TICKET-0114 (BRIEF-0114-B, B1, C1, D1, W1). State and requests of the
   event vocabulary in « Vocabulaire du monde »: the world's event types and
   its sortes (GET /api/event-vocabulary), with what a type may name --
   entity types, domains, scope kinds, levels. One type draft, written whole
   (POST/PUT /api/event-types); one sorte draft (POST/PUT /api/event-sortes);
   retire and restore (…/status, a type refused while a condition names it).
   A name near another's comes back `saved: false` with the near ones: the
   creator opens the existing one or creates anyway (`confirm_near`).
   `typeDraft` / `typeBody` are shared with the journal's sheet and the
   interpreter's and analyzer's proposal cards (BRIEF-0114-C/G/H). */
import { api } from './sheetRequest.svelte.js';

export const vocabState = $state({
  types: [],
  sortes: [],
  entityTypes: [],
  domains: [],
  scopeKinds: [],
  levels: [],
  loadError: '',
  typeDraft: null, // typeDraft(), plus `id` when it edits one
  sorteDraft: null, // { id, name }
  near: [],
  saving: false,
  saveError: '',
  actionError: null, // { id, message }
});

/** A type as the form edits it, from a type (or blank). */
export function typeDraft(type) {
  if (!type) {
    return { id: null, name: '', domain: 'other', counts_quantity: false, in_chronicle: true,
             participants_secret: false, roles: [{ id: null, name: '', entity_types: ['character'], accepts_sorte: false }],
             scopes: [] };
  }
  return {
    id: type.id || null, name: type.name, domain: type.domain, counts_quantity: !!type.counts_quantity,
    in_chronicle: type.in_chronicle !== false, participants_secret: !!type.participants_secret,
    roles: (type.roles || []).filter((r) => r.status !== 'retired').map((r) => ({
      id: r.id || null, name: r.name, entity_types: [...(r.entity_types || [])], accepts_sorte: !!r.accepts_sorte,
    })),
    scopes: (type.scopes || []).map((s) => ({ kind: s.kind, role: s.role || null, level: s.level })),
  };
}

/** The request body of a type draft (`EventTypeBody`). */
export function typeBody(draft, confirmNear) {
  return {
    name: draft.name, domain: draft.domain, counts_quantity: draft.counts_quantity,
    in_chronicle: draft.in_chronicle, participants_secret: draft.participants_secret,
    roles: draft.roles.map((r) => ({ id: r.id || null, name: r.name, entity_types: r.entity_types,
                                     accepts_sorte: r.accepts_sorte })),
    scopes: draft.scopes.map((s) => ({ kind: s.kind, role: ['rencontre', 'faction'].includes(s.kind) ? s.role : null,
                                       level: s.level })),
    confirm_near: !!confirmNear,
  };
}

function clearEdit() {
  vocabState.saveError = '';
  vocabState.near = [];
}

export function newTypeDraft() {
  clearEdit();
  vocabState.sorteDraft = null;
  vocabState.typeDraft = typeDraft(null);
}

export function editType(type) {
  clearEdit();
  vocabState.sorteDraft = null;
  vocabState.typeDraft = typeDraft(type);
}

export function newSorteDraft() {
  clearEdit();
  vocabState.typeDraft = null;
  vocabState.sorteDraft = { id: null, name: '' };
}

export function editSorte(sorte) {
  clearEdit();
  vocabState.typeDraft = null;
  vocabState.sorteDraft = { id: sorte.id, name: sorte.name };
}

export async function loadVocabulary(worldId) {
  if (!worldId) { vocabState.types = []; vocabState.sortes = []; return; }
  vocabState.loadError = '';
  try {
    const data = await api('/api/event-vocabulary');
    vocabState.types = data.types;
    vocabState.sortes = data.sortes;
    vocabState.entityTypes = data.entity_types;
    vocabState.domains = data.domains;
    vocabState.scopeKinds = data.scope_kinds;
    vocabState.levels = data.levels;
  } catch (e) {
    vocabState.loadError = e.message;
  }
}

async function save(path, method, body, worldId) {
  vocabState.saving = true;
  vocabState.saveError = '';
  try {
    const result = await api(path, { method, headers: { 'Content-Type': 'application/json' },
                                     body: JSON.stringify(body) });
    if (!result.saved) {
      vocabState.near = result.near;
      return;
    }
    vocabState.typeDraft = null;
    vocabState.sorteDraft = null;
    vocabState.near = [];
    await loadVocabulary(worldId);
  } catch (e) {
    vocabState.saveError = e.message;
  } finally {
    vocabState.saving = false;
  }
}

export async function saveTypeDraft(worldId, confirmNear) {
  const draft = vocabState.typeDraft;
  if (!draft) return;
  const path = draft.id ? '/api/event-types/' + encodeURIComponent(draft.id) : '/api/event-types';
  await save(path, draft.id ? 'PUT' : 'POST', typeBody(draft, confirmNear), worldId);
}

export async function saveSorteDraft(worldId, confirmNear) {
  const draft = vocabState.sorteDraft;
  if (!draft) return;
  const path = draft.id ? '/api/event-sortes/' + encodeURIComponent(draft.id) : '/api/event-sortes';
  await save(path, draft.id ? 'PUT' : 'POST', { name: draft.name, confirm_near: !!confirmNear }, worldId);
}

export async function setVocabStatus(worldId, kind, id, status) {
  vocabState.actionError = null;
  const base = kind === 'type' ? '/api/event-types/' : '/api/event-sortes/';
  try {
    await api(base + encodeURIComponent(id) + '/status', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
    });
    await loadVocabulary(worldId);
  } catch (e) {
    vocabState.actionError = { id, message: e.message };
  }
}
