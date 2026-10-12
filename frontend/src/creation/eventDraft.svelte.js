/* TICKET-0058 (BRIEF-0058-j); rewritten by TICKET-0114 (BRIEF-0114-C). The
   journal sheet's draft beyond its plain fields: the event's type, its
   quantity, its participants by role -- an entity or a sorte, each entity
   keeping it secret or not (X1) -- and who learns it besides them (its
   scopes: the type's when `customScopes` is off, W1). A module-level store,
   not Evenements.svelte-local state, because Sheet.svelte's save reads it
   too and a plain <Evenements> instance does not remount on every
   selection change. A participant already written (`saved`) stays: an
   event's participants are never taken away.

   TICKET-0119 (BRIEF-0119-D, H1, Y2, M-c): one draft SHAPE for every event
   editor -- the journal's sheet (this store), the review card of a
   proposed event, Lore's events -- rendered by EventEditor.svelte. Beyond
   the above it carries `changes` (what the event changes in the world,
   pre-filled from its type's effects through POST /api/events/changes) and,
   for a card, `newType` (a type proposed with the event: its participants
   name its roles by `role`, no id yet) and its own `title`, `description`,
   `locationId`. `draftFromPayload` / `payloadFromDraft` read a typed
   `event_creation` payload into a draft and back, so the card approves
   what the creator edited. */
import { api } from './sheetRequest.svelte.js';

export function blankEventDraft() {
  return {
    typeId: '', newType: null, quantity: null, participants: [], customScopes: false, scopes: [], changes: [],
    title: '', description: '', locationId: null,
  };
}

export const eventDraftState = $state(blankEventDraft());

export function resetEventDraft() {
  Object.assign(eventDraftState, blankEventDraft());
}

export function setEventDraftFromEvent(event) {
  eventDraftState.typeId = event.type_id || '';
  eventDraftState.quantity = event.quantity ?? null;
  eventDraftState.participants = (event.participants || []).map((p) => ({
    role_id: p.role_id, role: p.role_name || '', entity_id: p.entity_id, sorte_id: p.sorte_id, sorte_name: null,
    name: p.name, secret: !!p.secret, saved: true,
  }));
  eventDraftState.customScopes = true;
  eventDraftState.scopes = (event.scopes || []).map((s) => ({ scope_type: s.scope_type, scope_id: s.scope_id, level: s.level }));
  eventDraftState.changes = [];
}

/** Prefill from the AI draft (POST /api/events/generate): its former
 *  category picks the world's type of that domain, its entities fill the
 *  type's first role when the role accepts them. */
export function setEventDraftFromGenerated(result, types, entities) {
  const type = types.find((t) => t.status === 'active' && t.domain === result.type);
  eventDraftState.typeId = type ? type.id : eventDraftState.typeId;
  const role = type ? type.roles.find((r) => r.status === 'active') : null;
  eventDraftState.participants = [];
  if (!role) return;
  for (const id of result.involved_entities || []) {
    const entity = entities.find((e) => e.id === id);
    if (entity && role.entity_types.includes(entity.type)) {
      eventDraftState.participants.push({ role_id: role.id, role: role.name, entity_id: id, sorte_id: null,
                                         sorte_name: null, name: entity.name,
                                         secret: !!type.participants_secret, saved: false });
    }
  }
}

/** A participant fills `role` (a type's role, or a proposed type's, whose
 *  `id` is null): an entity or a sorte (`kind`), once per role. */
export function addParticipantTo(draft, role, kind, id, name, defaultSecret) {
  const inRole = (p) => (role.id ? p.role_id === role.id : !p.role_id && p.role === role.name);
  const same = (p) => inRole(p) && (kind === 'entity' ? p.entity_id === id
    : (id ? p.sorte_id === id : p.sorte_name === name));
  if (draft.participants.some(same)) return;
  draft.participants.push({ role_id: role.id || null, role: role.name, entity_id: kind === 'entity' ? id : null,
                            sorte_id: kind === 'sorte' ? id : null, sorte_name: kind === 'sorte' && !id ? name : null,
                            name, secret: !!defaultSecret, saved: false });
}

export function removeParticipantFrom(draft, i) {
  if (draft.participants[i] && !draft.participants[i].saved) {
    draft.participants.splice(i, 1);
  }
}

export function addParticipant(role, kind, id, name, defaultSecret) {
  addParticipantTo(eventDraftState, role, kind, id, name, defaultSecret);
}

export function removeParticipant(i) {
  removeParticipantFrom(eventDraftState, i);
}

/** The changes the type's effects pre-fill on the draft's participants
 *  (POST /api/events/changes), each with its French `line`. */
export async function prefilledChanges(draft) {
  if (!draft.typeId) return [];
  const data = await api('/api/events/changes', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      type_id: draft.typeId,
      participants: draft.participants.filter((p) => p.role_id && p.entity_id)
        .map((p) => ({ role_id: p.role_id, entity_id: p.entity_id })),
    }),
  });
  return data.prefilled.map((c) => ({ entity_id: c.entity_id, attribute: c.attribute, mode: c.mode, value: c.value }));
}

function changesBody(draft) {
  return (draft.changes || []).filter((c) => c.entity_id && c.attribute)
    .map((c) => ({ entity_id: c.entity_id, attribute: c.attribute, mode: c.mode || 'set',
                   value: c.value === '' ? null : c.value }));
}

/** A draft's body for POST /api/events (`EventBody`, beside the plain
 *  fields). A correction carries no change: the event already made them. */
export function eventBodyFrom(draft, isNew = true) {
  return {
    type_id: draft.typeId,
    quantity: draft.quantity === null || draft.quantity === '' ? null : Number(draft.quantity),
    participants: draft.participants.map((p) => ({
      role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, secret: p.entity_id ? !!p.secret : null,
    })),
    scopes: draft.customScopes ? draft.scopes.map((s) => ({ ...s })) : null,
    state_changes: isNew ? changesBody(draft) : [],
  };
}

/** The journal sheet's draft part, from its store. */
export function eventDraftBody(isNew = true) {
  return eventBodyFrom(eventDraftState, isNew);
}

/** A typed `event_creation` payload as a draft the review card edits. */
export function draftFromPayload(payload, nameOf) {
  const p = payload || {};
  return {
    ...blankEventDraft(),
    typeId: p.type_id || '',
    newType: p.new_type && typeof p.new_type === 'object' ? p.new_type : null,
    quantity: p.quantity ?? null,
    participants: (p.participants || []).map((x) => ({
      role_id: x.role_id || null, role: x.role || '', entity_id: x.entity_id || null, sorte_id: x.sorte_id || null,
      sorte_name: x.sorte_name || null, name: x.entity_id ? nameOf(x.entity_id) : (x.sorte_name || ''),
      secret: typeof x.secret === 'boolean' ? x.secret : null, saved: false,
    })),
    customScopes: Array.isArray(p.scopes),
    scopes: Array.isArray(p.scopes) ? p.scopes.map((s) => ({ ...s })) : [],
    changes: (p.state_changes || []).map((c) => ({ ...c })),
    title: p.title || '', description: p.description || '', locationId: p.location_id || null,
  };
}

/** The payload the card approves: the proposal's own keys, the draft's edits
 *  over them (`type_name` follows the type picked). */
export function payloadFromDraft(draft, payload, types) {
  const type = (types || []).find((t) => t.id === draft.typeId);
  const out = {
    ...(payload || {}),
    title: draft.title, description: draft.description || null, location_id: draft.locationId || null,
    type_id: draft.newType ? null : draft.typeId,
    type_name: draft.newType ? draft.newType.name : (type ? type.name : (payload || {}).type_name),
    quantity: draft.quantity === null || draft.quantity === '' ? null : Number(draft.quantity),
    participants: draft.participants.map((p) => ({
      role_id: p.role_id, role: p.role, entity_id: p.entity_id, sorte_id: p.sorte_id, sorte_name: p.sorte_name,
      secret: p.entity_id && typeof p.secret === 'boolean' ? p.secret : null,
    })),
    state_changes: changesBody(draft),
  };
  if (draft.customScopes) out.scopes = draft.scopes.map((s) => ({ ...s }));
  else delete out.scopes;
  if (!draft.newType) delete out.new_type;
  return out;
}
