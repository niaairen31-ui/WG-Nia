/* TICKET-0098 (BRIEF-0098-F). Non-render state + API calls for the Lore
   shell's writing panel ("Écrire"), same shape as namesPanel.svelte.js: a
   $state object WritePanel.svelte renders, plus the functions that mutate it.

   Flow (J3): the creator's text -> at most one round of questions -> a
   draft (C-05) she corrects -> a proposal (C-02) committed in one request.
   Every entity is picked from a list, never typed from memory (K1 of 0095):
   an ambiguous or new name offers the world's entities; "garder en texte"
   drops the entity and declares the name as a mention, so the tokenizer
   records it in "Noms à lier".

   TICKET-0105 (BRIEF-0105-F, H1): a rewritten fact carries the `kind` the
   draft preselected from its facet -- a correction, or a change in the
   world -- and the creator can switch it before committing.

   TICKET-0103 (BRIEF-0103-D): `attemptId` names one use of the panel, from
   the text to its commit, for the usage journal. A fresh one comes with
   every blank state (a new text, a world change); every request of the use
   carries it.

   TICKET-0119 (BRIEF-0119-G, U1, G3): the draft's EVENTS are edited in the
   shared EventEditor, on drafts whose entity ids are the statement's refs
   (`eventEntities`: the entities kept, by ref) -- mapped back to refs in
   the proposal, made ids by the server at commit. A type the model
   proposed is created from its card first (`createProposedType`, POST
   /api/event-types), its participants then bound to its roles by name.
   « Déclarer un événement » (`declareState`) writes one event straight to
   the journal (POST /api/events), with the world's entities. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';
import { blankEventDraft, eventBodyFrom } from '../creation/eventDraft.svelte.js';
import { typeBody, typeDraft, loadVocabulary, vocabState } from '../creation/eventVocab.svelte.js';

export const ENTITY_TYPES = Object.freeze([
  { value: 'character', label: 'personnage' },
  { value: 'location', label: 'lieu' },
  { value: 'faction', label: 'faction' },
  { value: 'item', label: 'objet' },
]);
export const SCOPE_TYPES = Object.freeze([
  { value: 'world', label: 'Tout le monde' },
  { value: 'faction', label: 'Les membres de la faction' },
  { value: 'location', label: 'Ceux qui sont dans le lieu' },
  { value: 'rencontre', label: 'Ceux qui ont rencontré' },
]);
export const LEVELS = Object.freeze(['rumor', 'suspicious', 'partial', 'knows', 'fully_understands']);
const SCOPE_ENTITY_TYPE = Object.freeze({ faction: 'faction', location: 'location' });
const TYPE_CATEGORY = Object.freeze({
  location: 'place', character: 'person', faction: 'faction', item: 'object',
});

function blank() {
  return {
    stage: 'text', statement: '', answers: '', questions: [], draft: null,
    busy: false, error: '', result: null, entities: null, entries: [], pick: {},
    attemptId: crypto.randomUUID(),
  };
}

/* G3: one event declared straight to the journal, no statement. */
export const declareState = $state({ open: false, draft: null, busy: false, error: '', saved: '' });

export const writeState = $state(blank());

export function reloadForWorld() {
  Object.assign(writeState, blank());
}

const post = (path, body) => api(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
});

async function run(task) {
  writeState.busy = true;
  writeState.error = '';
  try {
    await task();
  } catch (e) {
    writeState.error = e.message;
  } finally {
    writeState.busy = false;
  }
}

export async function loadWorldEntities() {
  if (writeState.entities) return;
  const rows = await api('/api/entities');
  writeState.entities = rows.filter((e) => e.status === 'active');
}

export function askQuestions() {
  return run(async () => {
    const body = await post('/api/lore/write/questions', {
      statement: writeState.statement, attempt_id: writeState.attemptId,
    });
    writeState.questions = body.questions;
    if (body.questions.length === 0) {
      await draftNow();
    } else {
      writeState.stage = 'questions';
    }
  });
}

async function draftNow() {
  await loadWorldEntities();
  const draft = await post('/api/lore/write/draft', {
    statement: writeState.statement, answers: writeState.answers,
    attempt_id: writeState.attemptId,
  });
  for (const entity of draft.entities) {
    if (entity.status === 'matched') entity.decision = 'existing';
    else if (entity.status === 'ambiguous') entity.decision = '';
    else entity.decision = entity.type ? 'create' : '';
  }
  draft.events = (draft.events || []).map((item) => loreEventDraft(item, draft));
  if (draft.events.length) await loadVocabulary(serverState.worldId);
  writeState.draft = draft;
  writeState.result = null;
  writeState.stage = 'draft';
}

/* An event of the draft as the shared editor's draft: its entity ids are
   the statement's refs. */
function loreEventDraft(item, draft) {
  const named = (ref) => ((draft.entities || []).find((e) => e.ref === ref) || {}).name || ref;
  return {
    ...blankEventDraft(), ref: item.ref, typeId: item.type_id || '', newType: item.new_type || null,
    typeEdit: item.new_type ? typeDraft(item.new_type) : null, quantity: item.quantity ?? null,
    participants: (item.participants || []).map((p) => ({
      role_id: p.role_id, role: p.role, entity_id: p.entity_ref, sorte_id: p.sorte_id, sorte_name: null,
      name: p.entity_ref ? named(p.entity_ref) : '', secret: p.secret, saved: false,
    })),
    changes: (item.state_changes || []).map((c) => ({ entity_id: c.entity_ref, attribute: c.attribute,
                                                     mode: c.mode, value: c.value })),
    title: item.title || '', description: item.description || '', locationId: item.location_ref || null,
  };
}

/** The statement's kept entities, by ref, for the event editor. */
export function eventEntities() {
  return liveRefs().map((e) => ({ id: e.ref, name: refLabel(e.ref), type: e.type }));
}

/** A proposed type, created as the creator edited it; the event then names
 *  its roles by id. */
export function createProposedType(event) {
  return run(async () => {
    const saved = await post('/api/event-types', typeBody(event.typeEdit, true));
    await loadVocabulary(serverState.worldId);
    const type = vocabState.types.find((t) => t.id === saved.type.id);
    const byName = Object.fromEntries((type ? type.roles : []).map((r) => [r.name, r.id]));
    event.typeId = saved.type.id;
    event.newType = null;
    event.typeEdit = null;
    event.participants = event.participants.filter((p) => byName[p.role]).map((p) => ({ ...p, role_id: byName[p.role] }));
  });
}

export function openDeclare() {
  return run(async () => {
    await loadWorldEntities();
    await loadVocabulary(serverState.worldId);
    Object.assign(declareState, { open: true, draft: blankEventDraft(), error: '', saved: '' });
  });
}

export async function saveDeclared() {
  const draft = declareState.draft;
  if (!draft || !draft.typeId || !draft.title.trim()) { declareState.error = 'Un titre et un type sont requis.'; return; }
  declareState.busy = true;
  declareState.error = '';
  try {
    const body = { title: draft.title, description: draft.description || null, location_id: draft.locationId || null,
                   ...eventBodyFrom(draft, true) };
    const saved = await post('/api/events', body);
    Object.assign(declareState, { open: false, draft: null, saved: `Événement écrit : ${saved.title}` });
  } catch (e) {
    declareState.error = e.message;
  } finally {
    declareState.busy = false;
  }
}

export function makeDraft() {
  return run(draftNow);
}

export function worldEntity(id) {
  return (writeState.entities || []).find((e) => e.id === id);
}

export function pickExisting(entity, entityId) {
  const picked = worldEntity(entityId);
  if (!picked) return;
  Object.assign(entity, {
    decision: 'existing', action: 'existing', entity_id: picked.id, type: picked.type,
  });
}

export function refLabel(ref) {
  const entity = (writeState.draft?.entities || []).find((e) => e.ref === ref);
  if (!entity) return ref;
  if (entity.decision === 'existing') return worldEntity(entity.entity_id)?.name || entity.name;
  return entity.name;
}

export function liveRefs(type) {
  return (writeState.draft?.entities || []).filter((e) => e.decision
    && e.decision !== 'text' && (!type || e.type === type));
}

/* TICKET-0104 (BRIEF-0104-A, A1, A1'a). A scope picks its entity from the
   whole world, not only from the entities the text named: the entities of
   the draft first (a new one included), then every active entity of the
   world of the scope's type that the draft does not hold yet. `rencontre`
   has no entry in SCOPE_ENTITY_TYPE: any type, like the preset
   (writes/facets.py). A world entity picked here joins the draft as
   'existing', by the same path as a knower (`existingRef`). */
function existingRef(entityId) {
  const picked = worldEntity(entityId);
  if (!picked) return undefined;
  const draft = writeState.draft;
  let entity = draft.entities.find((e) => e.decision === 'existing' && e.entity_id === picked.id);
  if (!entity) {
    entity = {
      ref: `k${draft.entities.length + 1}`, name: picked.name, type: picked.type,
      status: 'matched', decision: 'existing', action: 'existing', entity_id: picked.id,
    };
    draft.entities.push(entity);
  }
  return entity.ref;
}

export function scopeOptions(scopeType) {
  const want = SCOPE_ENTITY_TYPE[scopeType];
  const inDraft = liveRefs(want);
  const held = new Set(inDraft.filter((e) => e.decision === 'existing').map((e) => e.entity_id));
  const world = (writeState.entities || [])
    .filter((e) => (!want || e.type === want) && !held.has(e.id))
    .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
  return [
    ...inDraft.map((e) => ({ value: `ref:${e.ref}`, label: refLabel(e.ref) })),
    ...world.map((e) => ({ value: `id:${e.id}`, label: e.name })),
  ];
}

export function scopeValue(scope) {
  return scope.scope_ref ? `ref:${scope.scope_ref}` : '';
}

export function pickScope(scope, value) {
  if (value.startsWith('ref:')) scope.scope_ref = value.slice(4);
  else if (value.startsWith('id:')) scope.scope_ref = existingRef(value.slice(3));
  else scope.scope_ref = undefined;
}

export function setScopeType(scope, scopeType) {
  scope.scope_type = scopeType;
  const want = SCOPE_ENTITY_TYPE[scopeType];
  const entity = (writeState.draft?.entities || []).find((e) => e.ref === scope.scope_ref);
  if (scopeType === 'world' || !entity || (want && entity.type !== want)) scope.scope_ref = undefined;
}

export function addKnower(fact, entityId) {
  const ref = existingRef(entityId);
  if (!ref) return;
  if (!fact.knowers.some((k) => k.entity_ref === ref)) {
    fact.knowers.push({ entity_ref: ref, level: 'knows', is_secret: false, is_incorrect: false });
  }
}

export function addDefault(fact) {
  fact.defaults.push({ scope_type: 'world' });
}

export function removeAt(list, index) {
  list.splice(index, 1);
}

export function blockers() {
  const draft = writeState.draft;
  if (!draft) return ['Aucune proposition.'];
  const out = [];
  for (const e of draft.entities) {
    if (!e.decision) out.push(`Choisis quoi faire de « ${e.name} ».`);
    if (e.decision === 'create' && !e.type) out.push(`Choisis le type de « ${e.name} ».`);
  }
  for (const f of draft.facts) {
    for (const d of f.defaults) {
      if (d.scope_type !== 'world' && !d.scope_ref) out.push('Une portée ne nomme pas son entité.');
    }
  }
  for (const ev of draft.events || []) {
    if (ev.newType) out.push(`Crée le type « ${ev.newType.name} » ou retire l'événement « ${ev.title} ».`);
    else if (!ev.typeId) out.push(`Choisis le type de l'événement « ${ev.title} ».`);
  }
  if (!draft.facts.length && !draft.memberships.length && !draft.controls.length && !(draft.events || []).length) {
    out.push('La proposition n’écrit rien.');
  }
  return out;
}

function eventProposal(ev, keep) {
  const out = {
    ref: ev.ref, type_id: ev.typeId, title: ev.title, description: ev.description || null,
    quantity: ev.quantity === null || ev.quantity === '' ? null : Number(ev.quantity),
    location_ref: keep(ev.locationId) ? ev.locationId : null,
    participants: ev.participants.filter((p) => !p.entity_id || keep(p.entity_id)).map((p) => ({
      role_id: p.role_id, role: p.role, entity_ref: p.entity_id || null, sorte_id: p.sorte_id || null,
      secret: p.entity_id && typeof p.secret === 'boolean' ? p.secret : null,
    })),
    state_changes: ev.changes.filter((c) => c.entity_id && c.attribute && keep(c.entity_id)).map((c) => ({
      entity_ref: c.entity_id, attribute: c.attribute, mode: c.mode || 'set', value: c.value === '' ? null : c.value,
    })),
  };
  if (ev.customScopes) {
    out.scopes = ev.scopes.filter((sc) => sc.scope_type === 'world' || keep(sc.scope_id))
      .map((sc) => ({ scope_type: sc.scope_type, scope_ref: sc.scope_type === 'world' ? null : sc.scope_id, level: sc.level }));
  }
  return out;
}

function toProposal() {
  const draft = writeState.draft;
  const dropped = new Set(draft.entities.filter((e) => e.decision === 'text').map((e) => e.ref));
  const mentions = draft.entities.filter((e) => dropped.has(e.ref))
    .map((e) => ({ name: e.name, category: TYPE_CATEGORY[e.type] || e.category || 'other' }));
  const keep = (ref) => ref && !dropped.has(ref);
  const entities = draft.entities.filter((e) => !dropped.has(e.ref)).map((e) => (
    e.decision === 'existing'
      ? { ref: e.ref, action: 'existing', entity_id: e.entity_id }
      : { ref: e.ref, action: 'create', name: e.name, type: e.type }));
  const facts = draft.facts.map((f) => {
    const out = {
      ref: f.ref, action: f.action,
      participants: f.participants.filter(keep),
      defaults: f.defaults.filter((d) => d.scope_type === 'world' || keep(d.scope_ref))
        .map((d) => (d.scope_type === 'world' ? { scope_type: 'world' } : { ...d })),
      knowers: f.knowers.filter((k) => keep(k.entity_ref)).map((k) => ({ ...k })),
    };
    if (f.action !== 'create') out.fact_id = f.fact_id;
    if (f.action !== 'existing') out.content = f.content;
    if (f.action === 'rewrite') out.kind = f.kind;
    if (f.action === 'create') Object.assign(out, { facet: f.facet, aspect: f.aspect, mentions });
    return out;
  });
  return {
    statement: draft.statement, answers: draft.answers,
    questions: writeState.questions.join('\n') || null, entities, facts,
    memberships: draft.memberships.filter((m) => keep(m.entity_ref) && keep(m.faction_ref)),
    controls: draft.controls.filter((c) => keep(c.owner_ref) && keep(c.location_ref)),
    events: (draft.events || []).map((ev) => eventProposal(ev, keep)),
  };
}

export function commit() {
  return run(async () => {
    const body = await post('/api/lore/write/commit', {
      proposal: toProposal(), attempt_id: writeState.attemptId,
    });
    writeState.result = body;
    writeState.stage = 'done';
    writeState.entities = null;
    await loadEntries();
  });
}

export function restart() {
  const entries = writeState.entries;
  Object.assign(writeState, blank(), { entries });
}

export async function loadEntries() {
  const body = await api('/api/lore/write/entries');
  writeState.entries = body.entries;
}
