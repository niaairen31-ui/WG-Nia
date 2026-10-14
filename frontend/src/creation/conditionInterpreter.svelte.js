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
   request carries that list.
   TICKET-0114 (BRIEF-0114-G, R1): a proposal may also carry the event
   types and sortes it proposes (`vocabulary`). Each is a card: the creator
   uses a near one, or creates this one -- retouched in EventTypeForm --
   through the vocabulary's own routes; « Appliquer les choix » then binds
   each ref to the id she chose. Created at once: the vocabulary belongs to
   the world, not to the offer.
   TICKET-0121 (BRIEF-0121-F, C-14): a condition the quest designer left
   waiting for the creator opens seeded (`seededState`) on the designer's
   answer, as after « Proposer »; « Insérer » and « Écarter » then call
   `onsettle`, so the review card stops counting it as pending. */
import { api } from './sheetRequest.svelte.js';
import { conditionBody, conditionDraft } from './questRequirements.js';
import { definitionBody, specDraft } from './attributes.svelte.js';
import { typeBody, typeDraft } from './eventVocab.svelte.js';
import { reloadChoices } from './questOffers.svelte.js';

export function interpreterState() {
  return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
           proposal: null, picks: {}, cards: [], vocab: [] };
}

/** An interpreter opened on an answer it did not ask for -- one of the
    designer's `pending_drafts` (TICKET-0121, C-10): the same shape `run`
    leaves after a request. */
export function seededState(answer) {
  return { ...interpreterState(), open: true, instruction: answer.instruction || '', proposal: answer,
           cards: cardsOf(answer), vocab: vocabCardsOf(answer) };
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

/** One card per proposed event type or sorte (TICKET-0114): its near
    names, the creator's choice (`new` or a near id), its draft, and once
    chosen or created the id it binds to (`pick`). */
function vocabCardsOf(proposal) {
  return (proposal?.vocabulary || []).map((v) => ({
    ref: v.ref, kind: v.kind, near: v.near || [], choice: (v.near || []).length ? '' : 'new', pick: '',
    draft: v.kind === 'type' ? typeDraft(v.definition) : { name: v.definition.name }, error: '', busy: false,
  }));
}

/** Create the card's type or sorte now (`confirm_near`: she saw the near ones). */
export async function createVocab(card) {
  card.busy = true;
  card.error = '';
  try {
    const result = card.kind === 'type'
      ? await post('/api/event-types', typeBody(card.draft, true))
      : await post('/api/event-sortes', { name: card.draft.name, confirm_near: true });
    card.pick = card.kind === 'type' ? result.type.id : result.sorte.id;
    await reloadChoices(); // the editor's lists now hold it
  } catch (e) {
    card.error = e.message;
  } finally {
    card.busy = false;
  }
}

async function run(state, request) {
  state.busy = true;
  state.error = '';
  try {
    state.proposal = await request();
    state.picks = {};
    state.cards = cardsOf(state.proposal);
    state.vocab = vocabCardsOf(state.proposal);
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
  for (const card of state.vocab) bindings[card.ref] = card.pick;
  return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
                               { bindings, unsaved_attributes: unsavedBody(unsaved) }));
}

async function decide(state, decision, body) {
  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision, ...(body || {}) });
}

/** Insert the proposal into the condition draft (a flat one as rows, a
    nested one locked), with the attributes it proposes as confirmed. */
export async function insertProposal(state, cond, unsaved, onsettle) {
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
  state.vocab = [];
  state.instruction = '';
  state.open = false;
  if (onsettle) onsettle();
}

/** Discard the proposal; the sentence stays, to reformulate. */
export async function discardProposal(state, onsettle) {
  let settled = true;
  try {
    if (state.proposal.outcome !== 'refused') await decide(state, 'discarded');
  } catch (e) {
    state.error = e.message;
    settled = false;
  }
  state.proposal = null;
  state.cards = [];
  state.vocab = [];
  if (settled && onsettle) onsettle();
}
