/* TICKET-0112 (BRIEF-0112-E, IB1, IC1, IG1). The interpreter of one
   condition of the offer editor: the creator writes it in French, reads the
   proposal back (its French lines, the notes, the errors), picks a name
   when one is ambiguous, then inserts it into her draft or discards it.
   Nothing reaches the offer before her « Enregistrer »: an inserted
   proposal replaces the condition draft (`conditionDraft`) and leaves its
   id on it (`cond.draftId`), which the save sends back (IH1). One attempt
   id per editor, kept across reformulations. */
import { api } from './sheetRequest.svelte.js';
import { conditionBody, conditionDraft } from './questRequirements.js';

export function interpreterState() {
  return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
           proposal: null, picks: {} };
}

async function post(path, body) {
  return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

async function run(state, request) {
  state.busy = true;
  state.error = '';
  try {
    state.proposal = await request();
    state.picks = {};
  } catch (e) {
    state.error = e.message;
  } finally {
    state.busy = false;
  }
}

/** A proposal for `cond` from the sentence; the current condition goes along (IC1). */
export function askInterpreter(state, cond, role) {
  return run(state, () => post('/api/conditions/interpret', {
    instruction: state.instruction, role, current: conditionBody(cond), attempt_id: state.attemptId,
  }));
}

/** The names the creator picked, one per waiting mention. */
export function pickNames(state) {
  return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
                               { bindings: state.picks }));
}

async function decide(state, decision) {
  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision });
}

/** Insert the proposal into the condition draft (a flat one as rows, a nested one locked). */
export async function insertProposal(state, cond) {
  const proposal = state.proposal;
  try {
    await decide(state, 'inserted');
  } catch (e) {
    state.error = e.message;
    return;
  }
  Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id });
  state.proposal = null;
  state.instruction = '';
  state.open = false;
}

/** Discard the proposal; the sentence stays, to reformulate. */
export async function discardProposal(state) {
  try {
    if (state.proposal.outcome !== 'refused') await decide(state, 'discarded');
  } catch (e) {
    state.error = e.message;
  }
  state.proposal = null;
}
