/* TICKET-0108 (BRIEF-0108-C). The requirement forms as the offer
   editor shows them: a French label, the picker list its target comes
   from (a key of GET /api/quest-offers/choices, or 'money'), whether that
   target is an entity (`target_entity_id`) or a key (`target_key`), and
   whether it takes a threshold. Mirrors `day_plan.REQUIREMENT_TYPES`,
   `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `THRESHOLD_TYPES` across
   the network boundary -- kept equal by `quests.py` (QC1), never by hand
   alone. TICKET-0110 (BRIEF-0110-A): the two debt forms, whose target is
   a creditor -- a character or a faction (the `givers` list).
   TICKET-0111 (BRIEF-0111-C): `quest_state` replaces `quest_completed`;
   `item_held` is new; `values: true` a form that compares to a value, its
   choices in `choices.form_values[form]`. TICKET-0113 (BRIEF-0113-B):
   `attribute` replaces `vital_status` -- its key is an attribute of
   `choices.attributes`, and what it compares to depends on that
   attribute's kind (`attributeOf`): a label, a threshold, or an entity.
   TICKET-0114 (BRIEF-0114-E, G1): `event` counts the events of one type
   its subject took part in -- its key an event type of
   `choices.event_types`, its value the subject's role (empty: any), its
   entity the place, plus a window (`since`) and filters on other roles. */

export const REQUIREMENT_FORMS = {
  knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
  relation_gte: { label: 'Est apprécié de (≥)', list: 'characters', column: 'entity', threshold: true },
  resource: { label: 'Possède au moins (monnaie)', list: 'money', column: 'key', threshold: true },
  location_reachable: { label: 'Peut atteindre le lieu', list: 'locations', column: 'entity', threshold: false },
  has_met: { label: 'A rencontré', list: 'characters', column: 'entity', threshold: false },
  faction_member: { label: 'Est membre de', list: 'factions', column: 'entity', threshold: false },
  skill_rank_gte: { label: 'Compétence au rang (≥)', list: 'skills', column: 'key', threshold: true },
  quest_state: { label: 'Quête dans l’état', list: 'offers', column: 'key', threshold: false, values: true },
  has_debt_to: { label: 'A une dette envers', list: 'givers', column: 'entity', threshold: false },
  no_debt_to: { label: 'N’a aucune dette envers', list: 'givers', column: 'entity', threshold: false },
  item_held: { label: 'Possède au moins (objet)', list: 'items', column: 'entity', threshold: true },
  attribute: { label: 'Est dans l’état', list: 'attributes', column: 'key', threshold: false },
  event: { label: 'A vécu l’événement', list: 'eventTypes', column: 'key', threshold: true },
};

// TICKET-0114 (F1): an `event` leaf's window. Mirrors
// `models.CONDITION_WINDOWS` (kept equal by `event_conditions.py`).
export const EVENT_WINDOWS = {
  always: 'depuis toujours',
  quest: 'depuis l’acceptation de la quête',
  step: 'depuis le début de l’étape',
};

// `resource`'s key is a label: one currency per world (the ledger has no
// currency column), so the editor always sends this one.
export const MONEY_KEY = 'monnaie';

export const STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure'];

// TICKET-0111 (BRIEF-0111-D, P1): who a requirement judges -- a role bound
// when it is judged, or one character (`entity:<id>`). Mirrors
// `conditions.SUBJECT_ROLES` (kept equal by `conditions.py` CD1).
export const SUBJECT_ROLES = {
  doer: 'Le personnage',
  giver: 'Le donneur',
  contact: 'Le contact',
};

export function blankRequirement() {
  return { type: 'has_met', subject: 'role:doer', target_entity_id: '', target_key: '', threshold: null, value: '',
           since: 'always', filters: [] };
}

/** TICKET-0114: the event type a row names, from `choices.event_types`. */
export function eventTypeOf(key, choices) {
  return (choices?.event_types || []).find((t) => t.id === key) || null;
}

/** TICKET-0114: what may fill a filter on `role` -- the entities of a type
    it accepts, then the sortes when it takes one (`sorte:<id>`). */
export function fillerOptions(role, choices) {
  if (!role) return [];
  const people = (choices?.entities || []).filter((e) => role.entity_types.includes(e.type))
    .map((e) => ({ value: 'entity:' + e.id, label: e.name }));
  const sortes = role.accepts_sorte
    ? (choices?.sortes || []).map((s) => ({ value: 'sorte:' + s.id, label: s.name + ' (sorte)' })) : [];
  return people.concat(sortes);
}

/** The subject options: the three roles, then every character -- or, for
    an `attribute` (TICKET-0113), every entity of a type it applies to. */
export function subjectOptions(choices, req) {
  const roles = Object.entries(SUBJECT_ROLES).map(([role, label]) => ({ value: 'role:' + role, label }));
  const attr = req?.type === 'attribute' ? attributeOf(req.target_key, choices) : null;
  const people = attr
    ? (choices?.entities || []).filter((e) => !attr.holder_types || attr.holder_types.includes(e.type))
    : choices?.characters || [];
  return roles.concat(people.map((c) => ({ value: 'entity:' + c.id, label: c.name })));
}

/** TICKET-0113: the attribute a row names, from `choices.attributes`. */
export function attributeOf(key, choices) {
  return (choices?.attributes || []).find((a) => a.key === key) || null;
}

/** TICKET-0113 (BRIEF-0113-E, WN2): the editor's choices with the draft's
    unsaved attributes -- those the interpreter proposed and the creator
    confirmed -- listed as `new:<ref>`, their labels as their own keys,
    until the offer's save writes them. */
export function withUnsaved(choices, unsaved) {
  if (!choices || !unsaved?.length) return choices;
  const extra = unsaved.map((u) => ({
    key: 'new:' + u.ref, name: u.definition.name + ' (à créer)', kind: u.definition.kind, system: false,
    hidden: !!u.definition.is_hidden, holder_types: u.definition.holder_types,
    value_types: u.definition.value_types || [],
    choices: (u.definition.choices || []).map((c) => ({ value: c.label, label: c.label })),
  }));
  return { ...choices, attributes: [...(choices.attributes || []), ...extra] };
}

/** TICKET-0113: what an `entity` attribute's value may name. */
export function attributeTargets(attr, choices) {
  return (choices?.entities || []).filter((e) => attr.value_types.includes(e.type))
    .map((e) => ({ value: e.id, label: e.name }));
}

/** The (value, label) options of a form's picker, from the editor's choices. */
export function targetOptions(form, choices) {
  if (!choices) return [];
  switch (REQUIREMENT_FORMS[form]?.list) {
    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
    case 'skills': return choices.skills.map((s) => ({ value: s.key, label: s.label }));
    case 'offers': return choices.offers.map((o) => ({ value: o.id, label: o.title }));
    case 'characters': return choices.characters.map((c) => ({ value: c.id, label: c.name }));
    case 'locations': return choices.locations.map((c) => ({ value: c.id, label: c.name }));
    case 'factions': return choices.factions.map((c) => ({ value: c.id, label: c.name }));
    case 'givers': return choices.givers.map((c) => ({ value: c.id, label: c.name }));
    case 'items': return choices.items.map((c) => ({ value: c.id, label: c.name }));
    case 'attributes': return (choices.attributes || []).map((a) => ({ value: a.key, label: a.name }));
    case 'eventTypes': return (choices.event_types || []).map((t) => ({ value: t.id, label: t.name }));
    default: return [];
  }
}

/** The (value, label) options of a form that compares to a value. */
export function valueOptions(form, choices) {
  return (choices?.form_values?.[form] || []).map((v) => ({ value: v.value, label: v.label }));
}

/** The request body of one requirement row: only the columns its form uses.
    An `attribute` row sends its label, threshold or entity as set: the row
    clears the two its attribute's kind does not use (TICKET-0113). */
export function requirementBody(req) {
  const form = REQUIREMENT_FORMS[req.type];
  const [kind, id] = (req.subject || 'role:doer').split(':');
  if (req.type === 'attribute') {
    return {
      op: 'leaf', type: req.type,
      subject_role: kind === 'role' ? id : null, subject_entity_id: kind === 'entity' ? id : null,
      target_entity_id: req.target_entity_id || null, target_key: req.target_key || null,
      threshold: req.threshold === '' || req.threshold === null || req.threshold === undefined
        ? null : Number(req.threshold),
      value: req.value || null,
    };
  }
  if (req.type === 'event') {
    return {
      op: 'leaf', type: req.type,
      subject_role: kind === 'role' ? id : null, subject_entity_id: kind === 'entity' ? id : null,
      target_entity_id: req.target_entity_id || null, target_key: req.target_key || null,
      threshold: req.threshold === '' || req.threshold === null || req.threshold === undefined
        ? null : Number(req.threshold),
      value: req.value || null, since: req.since || 'always',
      filters: (req.filters || []).filter((f) => f.role_id && f.filler).map((f) => {
        const [fk, fid] = f.filler.split(':');
        return { role_id: f.role_id, entity_id: fk === 'entity' ? fid : null, sorte_id: fk === 'sorte' ? fid : null };
      }),
    };
  }
  return {
    op: 'leaf',
    type: req.type,
    subject_role: kind === 'role' ? id : null,
    subject_entity_id: kind === 'entity' ? id : null,
    target_entity_id: form.column === 'entity' ? (req.target_entity_id || null) : null,
    target_key: form.list === 'money' ? MONEY_KEY : form.column === 'key' ? (req.target_key || null) : null,
    threshold: form.threshold ? (req.threshold === '' || req.threshold === null ? null : Number(req.threshold)) : null,
    value: form.values ? (req.value || null) : null,
  };
}

/* TICKET-0111 (BRIEF-0111-D, T1). A condition in the editor: `list`, the
   rows of a flat condition (`all` of its leaves), or `locked`, a nested
   tree shown read-only by its French `lines` and sent back unchanged --
   only the interpreter will edit those. */

/** The editor's draft of one condition, from the server's view (`quest_reads.condition_view`).
    TICKET-0112 (IH1): `draftId`, the interpreter's proposal inserted here, if any. */
export function conditionDraft(view) {
  if (view && !view.flat) return { list: [], locked: view.tree, lines: view.lines || [], draftId: null };
  return {
    list: (view?.flat || []).map((r) => ({
      ...r,
      subject: r.subject_entity_id ? 'entity:' + r.subject_entity_id : 'role:' + (r.subject_role || 'doer'),
      target_entity_id: r.target_entity_id || '', target_key: r.target_key || '', value: r.value || '',
      since: r.since || 'always',
      filters: (r.filters || []).map((f) => ({
        role_id: f.role_id, filler: f.entity_id ? 'entity:' + f.entity_id : f.sorte_id ? 'sorte:' + f.sorte_id : '',
      })),
    })),
    locked: null,
    lines: [],
    draftId: null,
  };
}

export function blankCondition() {
  return { list: [], locked: null, lines: [], draftId: null };
}

/** The tree a condition draft sends: the locked tree, `all` of the rows, or null. */
export function conditionBody(cond) {
  if (cond.locked) return cond.locked;
  if (!cond.list.length) return null;
  return { op: 'all', children: cond.list.map(requirementBody) };
}
