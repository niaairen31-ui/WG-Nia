/* TICKET-0112 (BRIEF-0112-E, IB1, IC1, IG1). The interpreter of one
   condition of the offer editor: the creator writes it in French, reads the
   proposal back (its French lines, the notes, the errors), picks a name
   when one is ambiguous, then inserts it into her draft or discards it.
   Nothing reaches the offer before her « Enregistrer »: an inserted
   proposal replaces the condition draft (`conditionDraft`) and leaves its
   id on it (`cond.draftId`), which the save sends back (IH1). One attempt
   id per editor, kept across reformulations.
   TICKET-0113 (BRIEF-0113-E, WK2, WN2): a proposal may carry the
   attributes it proposes. Each is a card: when its name is near another
   attribute's, the creator uses that one or creates this one; the one she
   creates she may retouch (AttributeDefinitionForm) before « Insérer »,
   which confirms the definitions with the condition and adds them to the
   offer draft's `unsaved` list -- the offer's save writes them. Every
   request carries that list. */
import { api } from './sheetRequest.svelte.js';
import { conditionBody, conditionDraft } from './questRequirements.js';
import { definitionBody, specDraft } from './attributes.svelte.js';

export function interpreterState() {
  return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
           proposal: null, picks: {}, cards: [] };
}

async function post(path, body) {
  return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

function unsavedBody(unsaved) {
  return (unsaved || []).map((u) => ({ ref: u.ref, definition: u.definition }));
}

/** One card per proposed attribute: its near attributes, the creator's pick
    (`new` when nothing is near), its definition as a form draft. */
function cardsOf(proposal) {
  return (proposal?.definitions || []).filter((d) => !d.adopted).map((d) => ({
    ref: d.ref, near: d.near || [], pick: (d.near || []).length ? '' : 'new', draft: specDraft(d.definition),
  }));
}

async function run(state, request) {
  state.busy = true;
  state.error = '';
  try {
    state.proposal = await request();
    state.picks = {};
    state.cards = cardsOf(state.proposal);
  } catch (e) {
    state.error = e.message;
  } finally {
    state.busy = false;
  }
}

/** A proposal for `cond` from the sentence; the current condition goes along (IC1). */
export function askInterpreter(state, cond, role, unsaved) {
  return run(state, () => post('/api/conditions/interpret', {
    instruction: state.instruction, role, current: conditionBody(cond), attempt_id: state.attemptId,
    unsaved_attributes: unsavedBody(unsaved),
  }));
}

/** The names the creator picked, one per waiting mention, and her pick for
    each proposed attribute near another (WK2). */
export function pickNames(state, unsaved) {
  const bindings = { ...state.picks };
  for (const card of state.cards) if (card.near.length) bindings[card.ref] = card.pick;
  return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
                               { bindings, unsaved_attributes: unsavedBody(unsaved) }));
}

async function decide(state, decision, body) {
  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision, ...(body || {}) });
}

/** Insert the proposal into the condition draft (a flat one as rows, a
    nested one locked), with the attributes it proposes as confirmed. */
export async function insertProposal(state, cond, unsaved) {
  const proposal = state.proposal;
  const definitions = state.cards.map((c) => ({ ref: c.ref, definition: definitionBody(c.draft, false) }));
  try {
    await decide(state, 'inserted', { definitions, unsaved_attributes: unsavedBody(unsaved) });
  } catch (e) {
    state.error = e.message;
    return;
  }
  for (const d of definitions) unsaved.push(d);
  Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id });
  state.proposal = null;
  state.cards = [];
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
  state.cards = [];
}
