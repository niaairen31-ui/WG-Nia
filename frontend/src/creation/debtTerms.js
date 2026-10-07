/* TICKET-0110 (BRIEF-0110-C). The four currencies of an owed term as the
   debt editors show them (Création › Dettes, Journée's service form): a
   French label, the picker its target comes from (a key of GET
   /api/quest-offers/choices, or none), and whether it counts an amount.
   Mirrors `models.DEBT_CURRENCIES` across the network boundary -- kept
   equal by `debts.py` (DC1). No relation: regard is not repaid (T1). A
   skill is taught, so it is a skill definition, never a base domain. */
import { STEP_DOMAINS } from './questRequirements.js';

export const DEBT_CURRENCY_FORMS = {
  money: { label: 'Monnaie', list: null, counted: true },
  item: { label: 'Objet', list: 'items', counted: true },
  fact: { label: 'Fait à transmettre', list: 'facts', counted: false },
  skill: { label: 'Compétence à enseigner', list: 'skills', counted: false },
};

export function blankDebtTerm() {
  return { currency: 'money', item_id: '', fact_id: '', skill_key: '', amount: 1 };
}

/** The (value, label) options of an owed term's target picker. */
export function debtTargetOptions(currency, choices) {
  if (!choices) return [];
  switch (DEBT_CURRENCY_FORMS[currency]?.list) {
    case 'items': return choices.items.map((i) => ({ value: i.id, label: i.name }));
    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
    case 'skills': return choices.skills.filter((s) => !STEP_DOMAINS.includes(s.key))
      .map((s) => ({ value: s.key, label: s.label }));
    default: return [];
  }
}

/** The request body of one owed term: only the columns its currency uses. */
export function debtTermBody(term) {
  const form = DEBT_CURRENCY_FORMS[term.currency];
  return {
    currency: term.currency,
    item_id: term.currency === 'item' ? (term.item_id || null) : null,
    fact_id: term.currency === 'fact' ? (term.fact_id || null) : null,
    skill_key: term.currency === 'skill' ? (term.skill_key || null) : null,
    amount: form.counted ? (term.amount === '' || term.amount === null ? null : Number(term.amount)) : null,
  };
}

/** S2: what a service gives the player now, prefilled as what he will owe
 *  -- its money and items received; Nia changes the list freely. */
export function owedFromService(terms) {
  return terms
    .filter((t) => t.direction === 'reward' && (t.currency === 'money' || t.currency === 'item'))
    .map((t) => ({ ...blankDebtTerm(), currency: t.currency, item_id: t.item_id || '', amount: t.amount ?? 1 }));
}
