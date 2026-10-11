/* TICKET-0113 (BRIEF-0113-C, WI1). State and requests of the « États »
   island (States.svelte): every attribute of the world -- the system ones
   first, read-only -- and the types a definition may name; one definition
   draft, written whole (POST/PUT /api/attributes); retire and restore (POST
   …/status, refused while a condition names it, WJ2). A name near another
   attribute's comes back `saved: false` with the near ones: the creator
   opens the existing one or creates anyway (`confirm_near`, WK2).
   `definitionDraft` / `definitionBody` are shared with the interpreter's
   proposal card (BRIEF-0113-E). */
import { api } from './sheetRequest.svelte.js';

export const statesState = $state({
  attributes: [],
  entityTypes: [],
  loadError: '',
  draft: null, // definitionDraft(), plus `key` when it edits one
  near: [], // the attributes near the draft's name, after a refused save
  saving: false,
  saveError: '',
  actionError: '', // a refused retire, by key: { key, message }
});

/** A definition as the form edits it, from an attribute (or blank). */
export function definitionDraft(attr) {
  if (!attr) {
    return { key: null, name: '', kind: 'choice', holder_types: [], value_types: [],
             choices: [{ id: null, label: 'non' }, { id: null, label: 'oui' }], defaultLabel: 'non',
             defaultInteger: 0, is_hidden: false };
  }
  const def = (attr.choices || []).find((c) => c.value === attr.default);
  return {
    key: attr.key, name: attr.name, kind: attr.kind, holder_types: [...(attr.holder_types || [])],
    value_types: [...(attr.value_types || [])],
    choices: (attr.choices || []).map((c) => ({ id: c.value, label: c.label })),
    defaultLabel: def ? def.label : '', defaultInteger: attr.kind === 'integer' ? attr.default : 0,
    is_hidden: !!attr.hidden,
  };
}

/** The request body of a definition draft (`DefinitionBody`). */
export function definitionBody(draft, confirmNear) {
  return {
    name: draft.name, kind: draft.kind, holder_types: draft.holder_types,
    value_types: draft.kind === 'entity' ? draft.value_types : [],
    choices: draft.kind === 'choice' ? draft.choices.map((c) => ({ id: c.id || null, label: c.label })) : [],
    default: draft.kind === 'choice' ? draft.defaultLabel
      : draft.kind === 'integer' ? Number(draft.defaultInteger) : null,
    is_hidden: draft.is_hidden, confirm_near: !!confirmNear,
  };
}

export function newAttributeDraft() {
  statesState.saveError = '';
  statesState.near = [];
  statesState.draft = definitionDraft(null);
}

export function editAttribute(attr) {
  statesState.saveError = '';
  statesState.near = [];
  statesState.draft = definitionDraft(attr);
}

export async function loadAttributes(worldId) {
  if (!worldId) { statesState.attributes = []; statesState.entityTypes = []; return; }
  statesState.loadError = '';
  try {
    const data = await api('/api/attributes');
    statesState.attributes = data.attributes;
    statesState.entityTypes = data.entity_types;
  } catch (e) {
    statesState.loadError = e.message;
  }
}

export async function saveAttributeDraft(worldId, confirmNear) {
  const draft = statesState.draft;
  if (!draft) return;
  statesState.saving = true;
  statesState.saveError = '';
  try {
    const path = draft.key ? '/api/attributes/' + encodeURIComponent(draft.key) : '/api/attributes';
    const result = await api(path, {
      method: draft.key ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(definitionBody(draft, confirmNear)),
    });
    if (!result.saved) {
      statesState.near = result.near;
      return;
    }
    statesState.draft = null;
    statesState.near = [];
    await loadAttributes(worldId);
  } catch (e) {
    statesState.saveError = e.message;
  } finally {
    statesState.saving = false;
  }
}

export async function setAttributeStatus(worldId, key, status) {
  statesState.actionError = '';
  try {
    await api('/api/attributes/' + encodeURIComponent(key) + '/status', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
    });
    await loadAttributes(worldId);
  } catch (e) {
    statesState.actionError = { key, message: e.message };
  }
}
