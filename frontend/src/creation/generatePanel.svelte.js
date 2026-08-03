/* TICKET-0058 (BRIEF-0058-h). Faithful port of authorRenderGeneratePanel/
   authorGenerateEntity/authorApplyCharacterDraft/authorApplyLocationDraft/
   authorApplyFactionDraft/authorRenderGenNotes (index.html, now deleted) --
   the AI entity-authoring assistant's draft-generate panel (BRIEF-24) and
   its per-type draft pre-fill.

   Doctrine ("Model proposes, code judges", CLAUDE.md): a draft populates
   FORM STATE ONLY -- the author-f-name/author-x-* DOM fields Field.svelte
   already owns (written here the same imperative way authorApply*Draft
   always did, via legacyDoc.getElementById) plus the already-migrated
   family-g draft stores (pendingDraftsState/subcultureDraftState/
   factionPanelState, written directly -- no reverse-bridge event needed any
   more now that the writer itself is real JS, not legacy code). Nothing
   here calls a write endpoint; the only save is Sheet.svelte's existing
   submitEntity, triggered by the creator's own click. No entity id or
   relation target is ever read off the model's response and resolved here
   -- draft.public.faction_id is written into a plain <select> the creator
   reviews and can change, never used to open a relation itself.

   generatePanelState is a shared module (not GeneratePanel.svelte-local
   state) for two reasons: Sheet.svelte's primaryAction() needs to reset it
   the same way it already resets the sibling family-g draft stores
   (resetDraftRoles/resetSubcultureDraft/resetPendingDrafts) -- a plain
   <GeneratePanel> instance does NOT remount on "+ Nouveau" when the target
   type doesn't change, so a component-local reset would go stale; and
   generatePendingCreation (index.html, still legacy -- germ realization is
   out of this brief's scope) needs to reach applyGeneratedDraft from across
   the legacy boundary via Sheet.svelte's 'creation:apply-generated-draft'
   listener, the same reverse-bridge idiom family g established for the
   functions this one replaces. Both callers end up at this one apply
   implementation per type -- never two. */
import { pendingDraftsState } from './pendingDrafts.svelte.js';
import { subcultureDraftState } from './subcultureDraft.svelte.js';
import { factionPanelState } from './factionPanel.svelte.js';

export const generatePanelState = $state({ brief: '', status: '', notes: [] });

export function resetGeneratePanel() {
  generatePanelState.brief = '';
  generatePanelState.status = '';
  generatePanelState.notes = [];
}

function setVal(legacyDoc, id, value) {
  const el = legacyDoc.getElementById(id);
  if (el) el.value = value ?? '';
}

function applyCharacterDraft(legacyDoc, result) {
  const draft = result.draft;
  setVal(legacyDoc, 'author-f-name', draft.public.name);
  setVal(legacyDoc, 'author-f-description', draft.public.description);
  setVal(legacyDoc, 'author-x-physical_tier', draft.public.physical_tier);
  setVal(legacyDoc, 'author-x-appearance', draft.public.appearance);
  setVal(legacyDoc, 'author-x-backstory', draft.public.backstory);
  setVal(legacyDoc, 'author-x-aversion', draft.public.aversion);
  setVal(legacyDoc, 'author-x-faction_id', draft.public.faction_id || '');
  setVal(legacyDoc, 'author-x-secrets', draft.secret.creator_meta != null ? JSON.stringify(draft.secret.creator_meta) : '');

  const notes = [...(result.notes || [])];
  for (const sw of (draft.secret.shared_with || [])) {
    notes.push(`Pourrait être partagé avec ${sw.with}${sw.note ? ' — ' + sw.note : ''}`);
  }

  // BRIEF-0013-b (L1): goals drafted alongside the character, POSTed via the
  // 0013-a goals endpoint right after the entity is created (Sheet.svelte's
  // submitEntity, goalsForCreate()).
  const goals = draft.public.goals;
  const shorts = (goals && Array.isArray(goals.shorts)) ? goals.shorts : [];
  pendingDraftsState.knowledge = (draft.secret.knowledge || []).map((k) => ({ ...k }));
  pendingDraftsState.goals = { long: (goals && goals.long) || '', shorts: [shorts[0] || '', shorts[1] || ''] };

  return notes;
}

/* B1: the merge of allow-listed public subculture keys + the secret
 * "hidden" key happens HERE, in code, from the two segregated draft fields
 * (draft.public.subculture / draft.secret.subculture_hidden) -- never from a
 * single field the model controls directly. magic_status is never set
 * (stays default); coordinates is never touched. sensed_links and the full
 * subculture (public + hidden) render read-only in the notes block so the
 * creator can review the hidden content before accepting. */
function applyLocationDraft(legacyDoc, result) {
  const draft = result.draft;
  setVal(legacyDoc, 'author-f-name', draft.public.name);
  setVal(legacyDoc, 'author-f-description', draft.public.description);
  setVal(legacyDoc, 'author-x-location_type', draft.public.location_type);
  setVal(legacyDoc, 'author-x-access_level', draft.public.access_level || '');

  const rows = Object.entries(draft.public.subculture || {})
    .map(([key, value]) => ({ key, value: String(value), is_hidden: false }));
  if (draft.secret.subculture_hidden) {
    rows.push({ key: 'hidden', value: draft.secret.subculture_hidden, is_hidden: true });
  }
  subcultureDraftState.rows = rows;

  const notes = [...(result.notes || [])];
  for (const link of (draft.secret.sensed_links || [])) {
    notes.push(`Lien perçu (${link.kind}) : ${link.name}${link.note ? ' — ' + link.note : ''}`);
  }
  if (draft.secret.subculture_hidden) {
    notes.push(`Subculture cachée proposée : ${draft.secret.subculture_hidden}`);
  }
  return notes;
}

/* roles flow into factionPanelState.draftRoles, POSTed to the faction_role
 * create route by Sheet.svelte's submitEntity right after the entity is
 * created -- no new write code. magic_knowledge_level, scope, and
 * parent_faction_id are never set (stay at form defaults). */
function applyFactionDraft(legacyDoc, result) {
  const draft = result.draft;
  setVal(legacyDoc, 'author-f-name', draft.public.name);
  setVal(legacyDoc, 'author-f-description', draft.public.description);
  setVal(legacyDoc, 'author-x-faction_type', draft.public.faction_type);
  setVal(legacyDoc, 'author-x-philosophy', draft.public.philosophy);
  setVal(legacyDoc, 'author-x-internal_structure', draft.public.internal_structure);
  setVal(legacyDoc, 'author-x-aversion', draft.public.aversion);
  setVal(legacyDoc, 'author-x-internal_tensions', draft.secret.internal_tensions);
  setVal(legacyDoc, 'author-x-goals', draft.secret.goals);

  factionPanelState.draftRoles = (draft.public.roles || [])
    .map((r) => ({ name: r.name || '', description: r.description || '', limit: null }));

  return [...(result.notes || [])];
}

/** One apply step per target type (BRIEF-0058-h): each function above names
 *  its exact target ids/stores instead of iterating the draft, so an
 *  unknown field in a draft is ignored, never written blind. Sets
 *  generatePanelState.status/notes as its own side effect so both callers
 *  (GeneratePanel.svelte's own "Générer" click and generatePendingCreation's
 *  reverse-bridge dispatch) render the same status/notes UI. */
export function applyGeneratedDraft(legacyDoc, entityType, result) {
  const notes = entityType === 'location' ? applyLocationDraft(legacyDoc, result)
    : entityType === 'faction' ? applyFactionDraft(legacyDoc, result)
    : applyCharacterDraft(legacyDoc, result);
  generatePanelState.status = "Brouillon généré — relisez et éditez avant d'accepter.";
  generatePanelState.notes = notes;
}
