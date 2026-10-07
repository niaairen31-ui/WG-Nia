/* TICKET-0108 (BRIEF-0108-C). State and requests of the « Quêtes » island
   (QuestOffers.svelte): the world's offers, the editor's picker lists, and
   one draft being edited. Saving sends the whole offer (PUT replaces its
   steps and requirements, writes/quests.py::write_quest_offer). */
import { api } from './sheetRequest.svelte.js';
import { blankRequirement, requirementBody } from './questRequirements.js';

export const questOffersState = $state({
  offers: [],
  choices: null,
  loading: false,
  loadError: '',
  draft: null, // { id|null, giver_entity_id, title, summary, repeatable, status, eligibility, steps }
  saving: false,
  saveError: '',
});

export function blankStep() {
  return { objective: '', cost: 1, domain: '', requirements: [] };
}

export function newDraft() {
  questOffersState.saveError = '';
  questOffersState.draft = {
    id: null, giver_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
    eligibility: [], steps: [blankStep()],
  };
}

export function editOffer(offer) {
  questOffersState.saveError = '';
  questOffersState.draft = {
    id: offer.id, giver_entity_id: offer.giver_entity_id, title: offer.title, summary: offer.summary || '',
    repeatable: offer.repeatable, status: offer.status,
    eligibility: offer.eligibility.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
    steps: offer.steps.map((s) => ({
      objective: s.objective, cost: s.cost, domain: s.domain || '',
      requirements: s.requirements.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
    })),
  };
}

export function addRequirement(list) {
  list.push(blankRequirement());
}

export async function loadOffers(worldId) {
  if (!worldId) { questOffersState.offers = []; questOffersState.choices = null; return; }
  questOffersState.loading = true;
  questOffersState.loadError = '';
  try {
    const [offers, choices] = await Promise.all([api('/api/quest-offers'), api('/api/quest-offers/choices')]);
    questOffersState.offers = offers;
    questOffersState.choices = choices;
  } catch (e) {
    questOffersState.loadError = e.message;
  } finally {
    questOffersState.loading = false;
  }
}

function draftBody(draft) {
  return {
    giver_entity_id: draft.giver_entity_id, title: draft.title, summary: draft.summary || null,
    repeatable: draft.repeatable, status: draft.status,
    eligibility: draft.eligibility.map(requirementBody),
    steps: draft.steps.map((s) => ({
      objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
      requirements: s.requirements.map(requirementBody),
    })),
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
