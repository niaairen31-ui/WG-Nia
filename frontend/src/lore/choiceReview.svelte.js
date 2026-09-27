/* TICKET-0095 (K1, BRIEF-0095-d, C-08). Non-render state + API calls for the
   model-choice review panel (ChoiceReviewPanel.svelte), same shape as
   namesPanel.svelte.js: a $state object the panel renders, plus the
   functions that mutate it.

   `choices` holds GET /api/lore/choices's pending rows (C-06) unchanged.
   `record`/`scope` carry the creator's per-row appellation choice, keyed
   `<row id>:agree` or `<row id>:disagree` (the two blocks are independent);
   `target` is the disagree select's value per row ("" = nothing picked,
   "none" = no known entity, else an entity id); `query` filters that select.
   Nothing posts except agree()/disagree() -- one explicit click each. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';
import { categoryOf } from './namesPanel.svelte.js';

export const DISAGREE_SCOPE = 'rencontre';
export const NO_ENTITY = 'none';

export const reviewState = $state({
  loading: false,
  error: '',
  choices: [],
  entities: null,
  record: {},
  scope: {},
  target: {},
  query: {},
  busy: {},
});

async function loadEntities() {
  if (reviewState.entities) return;
  const rows = await api('/api/entities');
  reviewState.entities = rows.filter((e) => e.status === 'active');
}

export async function loadChoices() {
  reviewState.loading = true;
  reviewState.error = '';
  try {
    const body = await api('/api/lore/choices');
    reviewState.choices = body.choices;
    await loadEntities();
  } catch (e) {
    reviewState.error = e.message;
  } finally {
    reviewState.loading = false;
  }
}

export function reloadForWorld() {
  reviewState.choices = [];
  reviewState.entities = null;
  reviewState.record = {};
  reviewState.scope = {};
  reviewState.target = {};
  reviewState.query = {};
  reviewState.busy = {};
  reviewState.error = '';
}

function key(row, side) {
  return `${row.id}:${side}`;
}

// I1: the agree block records the appellation unless the creator unticks it;
// the disagree block records nothing unless ticked, and never without an entity.
export function recordFor(row, side) {
  const value = reviewState.record[key(row, side)];
  if (side === 'agree') return value === undefined ? true : value;
  return !!value && targetOf(row) !== '' && targetOf(row) !== NO_ENTITY;
}

export function scopeFor(row, side) {
  return reviewState.scope[key(row, side)] || (side === 'agree' ? row.preselected_scope : DISAGREE_SCOPE);
}

export function targetOf(row) {
  return reviewState.target[row.id] || '';
}

export function setRecord(row, side, checked) {
  reviewState.record = { ...reviewState.record, [key(row, side)]: checked };
}

export function setScope(row, side, scope) {
  reviewState.scope = { ...reviewState.scope, [key(row, side)]: scope };
}

export function setTarget(row, value) {
  reviewState.target = { ...reviewState.target, [row.id]: value };
}

export function setQuery(row, text) {
  reviewState.query = { ...reviewState.query, [row.id]: text };
}

// Active entities of the row's category, the model's choice excluded, filtered
// by the search text. The search only filters: no free text is ever posted.
export function disagreeOptions(row) {
  const query = (reviewState.query[row.id] || '').trim().toLowerCase();
  return (reviewState.entities || [])
    .filter((e) => categoryOf(e.type) === row.category)
    .filter((e) => e.id !== row.chosen.id)
    .filter((e) => !query || e.name.toLowerCase().includes(query));
}

async function review(row, body) {
  reviewState.busy = { ...reviewState.busy, [row.id]: true };
  reviewState.error = '';
  try {
    await api(`/api/lore/choices/${encodeURIComponent(row.id)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    reviewState.choices = reviewState.choices.filter((c) => c.id !== row.id);
  } catch (e) {
    reviewState.error = e.message;
  } finally {
    reviewState.busy = { ...reviewState.busy, [row.id]: false };
  }
}

export function agree(row) {
  return review(row, {
    verdict: 'agreed',
    record_appellation: recordFor(row, 'agree'),
    scope_type: scopeFor(row, 'agree'),
  });
}

export function disagree(row) {
  const target = targetOf(row);
  if (target === '') return;
  const entityId = target === NO_ENTITY ? null : target;
  return review(row, {
    verdict: 'disagreed',
    entity_id: entityId,
    record_appellation: entityId === null ? false : recordFor(row, 'disagree'),
    scope_type: scopeFor(row, 'disagree'),
  });
}
