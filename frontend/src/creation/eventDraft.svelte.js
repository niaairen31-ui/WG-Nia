/* TICKET-0058 (BRIEF-0058-j); rewritten by TICKET-0114 (BRIEF-0114-C). The
   journal sheet's draft beyond its plain fields: the event's type, its
   quantity, its participants by role -- an entity or a sorte, each entity
   keeping it secret or not (X1) -- and who learns it besides them (its
   scopes: the type's when `customScopes` is off, W1). A module-level store,
   not Evenements.svelte-local state, because Sheet.svelte's save reads it
   too and a plain <Evenements> instance does not remount on every
   selection change. A participant already written (`saved`) stays: an
   event's participants are never taken away. */
export const eventDraftState = $state({
  typeId: '',
  quantity: null,
  participants: [], // {role_id, entity_id, sorte_id, name, secret, saved}
  customScopes: false,
  scopes: [], // {scope_type, scope_id, level}
});

export function resetEventDraft() {
  eventDraftState.typeId = '';
  eventDraftState.quantity = null;
  eventDraftState.participants = [];
  eventDraftState.customScopes = false;
  eventDraftState.scopes = [];
}

export function setEventDraftFromEvent(event) {
  eventDraftState.typeId = event.type_id || '';
  eventDraftState.quantity = event.quantity ?? null;
  eventDraftState.participants = (event.participants || []).map((p) => ({
    role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, name: p.name, secret: !!p.secret, saved: true,
  }));
  eventDraftState.customScopes = true;
  eventDraftState.scopes = (event.scopes || []).map((s) => ({ scope_type: s.scope_type, scope_id: s.scope_id, level: s.level }));
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
      eventDraftState.participants.push({ role_id: role.id, entity_id: id, sorte_id: null, name: entity.name,
                                         secret: !!type.participants_secret, saved: false });
    }
  }
}

export function addParticipant(role, kind, id, name, defaultSecret) {
  const same = (p) => p.role_id === role.id && (kind === 'entity' ? p.entity_id === id : p.sorte_id === id);
  if (eventDraftState.participants.some(same)) return;
  eventDraftState.participants.push({ role_id: role.id, entity_id: kind === 'entity' ? id : null,
                                      sorte_id: kind === 'sorte' ? id : null, name, secret: !!defaultSecret,
                                      saved: false });
}

export function removeParticipant(i) {
  if (eventDraftState.participants[i] && !eventDraftState.participants[i].saved) {
    eventDraftState.participants.splice(i, 1);
  }
}

/** The request body's draft part (`EventBody`, beside the plain fields). */
export function eventDraftBody() {
  return {
    type_id: eventDraftState.typeId,
    quantity: eventDraftState.quantity === null || eventDraftState.quantity === '' ? null
      : Number(eventDraftState.quantity),
    participants: eventDraftState.participants.map((p) => ({
      role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, secret: p.entity_id ? !!p.secret : null,
    })),
    scopes: eventDraftState.customScopes ? eventDraftState.scopes.map((s) => ({ ...s })) : null,
  };
}
