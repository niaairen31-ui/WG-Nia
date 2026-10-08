/* TICKET-0108 (BRIEF-0108-C). State and requests of the « Quêtes » island
   (QuestOffers.svelte): the world's offers, the editor's picker lists, and
   one draft being edited. Saving sends the whole offer (PUT replaces its
   steps and requirements, writes/quests.py::write_quest_offer). Since
   TICKET-0109 (BRIEF-0109-D): its costs and rewards, their live indicative
   value (POST /api/quest-offers/value), and the world's rates. Since
   TICKET-0111 (BRIEF-0111-D): every condition -- the eligibility, each
   step's prerequisite and completion -- is a condition draft, sent as a
   tree (conditionBody). */
import { api } from './sheetRequest.svelte.js';
import { blankCondition, conditionBody, conditionDraft } from './questRequirements.js';
import { blankTerm, termBody } from './questTerms.js';

export const questOffersState = $state({
  offers: [],
  choices: null,
  loading: false,
  loadError: '',
  draft: null, // { id|null, giver_entity_id, contact_entity_id, title, summary, repeatable, status, eligibility, steps, terms }
  saving: false,
  saveError: '',
  value: null, // the draft's indicative value (cost, reward, ratio_pct, verdict_label)
  economy: null, // { stored, effective, defaults }
  economyError: '',
});

export function blankStep() {
  return { objective: '', cost: 1, domain: '', prerequisite: blankCondition(), completion: blankCondition() };
}

export function newDraft() {
  questOffersState.saveError = '';
  questOffersState.draft = {
    id: null, giver_entity_id: '', contact_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
    eligibility: blankCondition(), steps: [blankStep()], terms: [],
  };
  refreshValue();
}

export function editOffer(offer) {
  questOffersState.saveError = '';
  questOffersState.draft = {
    id: offer.id, giver_entity_id: offer.giver_entity_id, contact_entity_id: offer.contact_entity_id || '',
    title: offer.title, summary: offer.summary || '',
    repeatable: offer.repeatable, status: offer.status,
    eligibility: conditionDraft(offer.eligibility),
    steps: offer.steps.map((s) => ({
      objective: s.objective, cost: s.cost, domain: s.domain || '',
      prerequisite: conditionDraft(s.prerequisite), completion: conditionDraft(s.completion),
    })),
    terms: (offer.terms || []).map((t) => ({
      direction: t.direction, currency: t.currency, counterparty_entity_id: t.counterparty_entity_id || '',
      item_id: t.item_id || '', fact_id: t.fact_id || '', skill_key: t.skill_key || '', amount: t.amount,
      level: t.level || '',
    })),
  };
  questOffersState.value = offer.value || null;
}

export function addTerm(direction) {
  questOffersState.draft.terms.push(blankTerm(direction));
  refreshValue();
}

/** The draft's indicative value, recomputed by the server (C1). */
export async function refreshValue() {
  const draft = questOffersState.draft;
  if (!draft) return;
  try {
    questOffersState.value = await api('/api/quest-offers/value', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ terms: draft.terms.map(termBody) }),
    });
  } catch (_e) {
    questOffersState.value = null;
  }
}

export async function loadEconomy() {
  try {
    questOffersState.economy = await api('/api/quest-economy');
    questOffersState.economyError = '';
  } catch (e) {
    questOffersState.economyError = e.message;
  }
}

/** E1: `stored` values, '' = the code's default. */
export async function saveEconomy(stored) {
  const body = Object.fromEntries(Object.entries(stored).map(([k, v]) => [k, v === '' || v === null ? null : Number(v)]));
  try {
    questOffersState.economy = await api('/api/quest-economy', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    questOffersState.economyError = '';
    await refreshValue();
  } catch (e) {
    questOffersState.economyError = e.message;
  }
}

export async function loadOffers(worldId) {
  if (!worldId) { questOffersState.offers = []; questOffersState.choices = null; return; }
  questOffersState.loading = true;
  questOffersState.loadError = '';
  try {
    const [offers, choices] = await Promise.all([api('/api/quest-offers'), api('/api/quest-offers/choices')]);
    questOffersState.offers = offers;
    questOffersState.choices = choices;
    await loadEconomy();
  } catch (e) {
    questOffersState.loadError = e.message;
  } finally {
    questOffersState.loading = false;
  }
}

function draftBody(draft) {
  return {
    giver_entity_id: draft.giver_entity_id, contact_entity_id: draft.contact_entity_id || null,
    title: draft.title, summary: draft.summary || null,
    repeatable: draft.repeatable, status: draft.status,
    eligibility: conditionBody(draft.eligibility),
    steps: draft.steps.map((s) => ({
      objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
      prerequisite: conditionBody(s.prerequisite), completion: conditionBody(s.completion),
    })),
    terms: draft.terms.map(termBody),
  };
}

export async function saveDraft(worldId) {
  const draft = questOffersState.draft;
  if (!draft) return;
  questOffersState.saving = true;
  questOffersState.saveError = '';
  try {
    const saved = await api(draft.id ? '/api/quest-offers/' + draft.id : '/api/quest-offers', {
      method: draft.id ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draftBody(draft)),
    });
    await loadOffers(worldId);
    editOffer(saved);
  } catch (e) {
    questOffersState.saveError = e.message;
  } finally {
    questOffersState.saving = false;
  }
}
