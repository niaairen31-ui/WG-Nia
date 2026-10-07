/* TICKET-0108 (BRIEF-0108-C). State and requests of Journée's quest panel
   (QuestPanel.svelte) and of the day's pin (O1). GET /api/quests carries
   the offers the player may accept (I1) and his quests -- named by
   `quest_id`/`offer_id` only, never by the plan behind them (the plan stays
   invisible here, as in the rest of Journée). */
import { api } from '../creation/sheetRequest.svelte.js';

export const questState = $state({
  offers: [],
  quests: [],
  loading: false,
  loadError: '',
  busy: null, // the offer_id or quest_id being acted on
  actionError: '',
  pin: '', // O1: the quest_id the next planned day advances, '' = the day chooses
});

export function openQuests() {
  return questState.quests.filter((q) => q.open);
}

function apply(payload) {
  questState.offers = payload.offers;
  questState.quests = payload.quests;
  if (questState.pin && !openQuests().some((q) => q.quest_id === questState.pin)) questState.pin = '';
}

export async function loadQuests() {
  questState.loading = true;
  questState.loadError = '';
  try {
    apply(await api('/api/quests'));
  } catch (e) {
    questState.loadError = e.message;
    questState.offers = [];
    questState.quests = [];
  } finally {
    questState.loading = false;
  }
}

async function act(key, path, body) {
  questState.busy = key;
  questState.actionError = '';
  try {
    apply(await api(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    }));
  } catch (e) {
    questState.actionError = e.message;
  } finally {
    questState.busy = null;
  }
}

export function acceptOffer(offerId) {
  return act(offerId, '/api/quests/accept', { offer_id: offerId });
}

export function abandonQuest(questId) {
  return act(questId, '/api/quests/' + questId + '/abandon', null);
}
