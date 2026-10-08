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
   `item_held` and `vital_status` are new. `column: 'none'` is a form with
   no target (`NO_TARGET_TYPES`); `values: true` a form that compares to a
   value, its choices in `choices.form_values[form]`. */

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
  vital_status: { label: 'Est dans l’état', list: 'none', column: 'none', threshold: false, values: true },
};

// `resource`'s key is a label: one currency per world (the ledger has no
// currency column), so the editor always sends this one.
export const MONEY_KEY = 'monnaie';

export const STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure'];

export function blankRequirement() {
  return { type: 'has_met', target_entity_id: '', target_key: '', threshold: null, value: '' };
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
    default: return [];
  }
}

/** The (value, label) options of a form that compares to a value. */
export function valueOptions(form, choices) {
  return (choices?.form_values?.[form] || []).map((v) => ({ value: v.value, label: v.label }));
}

/** The request body of one requirement row: only the columns its form uses. */
export function requirementBody(req) {
  const form = REQUIREMENT_FORMS[req.type];
  return {
    type: req.type,
    target_entity_id: form.column === 'entity' ? (req.target_entity_id || null) : null,
    target_key: form.list === 'money' ? MONEY_KEY : form.column === 'key' ? (req.target_key || null) : null,
    threshold: form.threshold ? (req.threshold === '' || req.threshold === null ? null : Number(req.threshold)) : null,
    value: form.values ? (req.value || null) : null,
  };
}
