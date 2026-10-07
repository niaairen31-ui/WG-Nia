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
  // TICKET-0109 (D1, G1): the recap shown before « déclarer accomplie ».
  settling: null, // quest_id whose recap is open
  settlement: null, // GET /api/quests/{id}/settlement
  settlementError: '',
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

/** G1: open (or close) the measured recap of one quest. */
export async function openSettlement(questId) {
  if (questState.settling === questId) { questState.settling = null; return; }
  questState.settling = questId;
  questState.settlement = null;
  questState.settlementError = '';
  try {
    questState.settlement = await api('/api/quests/' + questId + '/settlement');
  } catch (e) {
    questState.settlementError = e.message;
  }
}

/** D1: apply the quest's terms at once; the server refuses an unpayable cost. */
export async function settleQuest(questId) {
  await act(questId, '/api/quests/' + questId + '/settle', null);
  if (!questState.actionError) questState.settling = null;
}

/** A2 (TICKET-0110): what the player lacks of coins or items becomes a
 *  debt per creditor; `contacts` names a faction creditor's member. */
export async function settleOnCredit(questId, contacts, isSecret) {
  await act(questId, '/api/quests/' + questId + '/settle-on-credit', { contacts, is_secret: isSecret });
  if (!questState.actionError) questState.settling = null;
}
