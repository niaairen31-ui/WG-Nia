/* TICKET-0109 (BRIEF-0109-D). The five currencies of a quest term as the
   offer editor shows them: a French label, the picker its target comes from
   (a key of GET /api/quest-offers/choices, or none), whether it counts an
   amount, and whether its counterparty must be a character. Mirrors
   `models.QUEST_TERM_CURRENCIES`, `writes.quest_terms.COUNTED_CURRENCIES`
   and `PERSONAL_CURRENCIES` across the network boundary -- kept equal by
   `quest_rewards.py` (RD1). */

export const TERM_DIRECTIONS = { cost: 'Coût', reward: 'Récompense' };

export const CURRENCY_FORMS = {
  money: { label: 'Monnaie', list: null, counted: true, personal: false },
  item: { label: 'Objet', list: 'items', counted: true, personal: false },
  relation: { label: 'Relation', list: null, counted: true, personal: true },
  fact: { label: 'Fait', list: 'facts', counted: false, personal: true },
  skill: { label: 'Compétence', list: 'skills', counted: false, personal: true },
};

export function blankTerm(direction) {
  return { direction, currency: 'money', counterparty_entity_id: '', item_id: '', fact_id: '',
           skill_key: '', amount: 1, level: '' };
}

/** The (value, label) options of a currency's target picker. */
export function termTargetOptions(currency, choices) {
  if (!choices) return [];
  switch (CURRENCY_FORMS[currency]?.list) {
    case 'items': return choices.items.map((i) => ({ value: i.id, label: `${i.name} (valeur ${i.value})` }));
    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
    case 'skills': return choices.skills.map((s) => ({ value: s.key, label: s.label }));
    default: return [];
  }
}

/** The request body of one term: only the columns its currency uses. */
export function termBody(term) {
  const form = CURRENCY_FORMS[term.currency];
  return {
    direction: term.direction,
    currency: term.currency,
    counterparty_entity_id: term.counterparty_entity_id || null,
    item_id: term.currency === 'item' ? (term.item_id || null) : null,
    fact_id: term.currency === 'fact' ? (term.fact_id || null) : null,
    skill_key: term.currency === 'skill' ? (term.skill_key || null) : null,
    amount: form.counted ? (term.amount === '' || term.amount === null ? null : Number(term.amount)) : null,
    level: term.currency === 'fact' && term.direction === 'reward' ? (term.level || null) : null,
  };
}
