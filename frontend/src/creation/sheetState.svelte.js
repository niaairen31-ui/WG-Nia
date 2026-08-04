/* TICKET-0059 (BRIEF-0059-e, per SUPPLEMENT-0059-recon-amendments Amendment
   3). Sheet.svelte's own state ownership -- facts a bare legacy `let` held
   despite driving an entity sheet that is now fully Svelte: the selected
   entity + loaded detail (index.html's authorSelectEntity/_authorNotifySaved,
   now gone), the create-draft-reset trigger (_authorResetCreateDrafts), and
   the pending-creation mutation id lifecycle (_authorGetPendingCreationMutationId/
   _authorConsumePendingCreationMutationId).

   Grown across this brief's three commits rather than authored whole: each
   commit adds exactly the functions its own wiring needs, so every commit is
   independently testable (item 8). This first commit adds the create-draft
   and pending-mutation pieces only -- selectEntity/deleteEntity/
   getSelectedEntityId land in the next two commits.

   selectedEntityId/sheetDetail/sheetMode/... themselves are NOT duplicated
   here: they already live in creationState (state.svelte.js), the one
   authority EntityList.svelte and Sheet.svelte both already read. This
   module owns the FUNCTIONS that write those fields plus the two facts nothing
   else owned yet (pendingCreationMutationId, local to this file -- no other
   reader exists for it). */
import { creationState } from './state.svelte.js';

let pendingCreationMutationId = $state(null);

/** index.html's _authorResetCreateDrafts, ported: by the time this ticket
 *  reached it, TICKET-0058 had already extracted every OTHER draft reset
 *  (roles/subculture/knowledge/goals/generate-panel/event-draft) into its own
 *  Svelte reset function, called separately by Sheet.svelte's primaryAction()
 *  -- this one line is what was left. */
export function resetCreateDrafts() {
  pendingCreationMutationId = null;
}

/** index.html's _authorGetPendingCreationMutationId -- reads without
 *  clearing (BRIEF-0019-a's two-stage entity creation). */
export function getPendingCreationMutationId() {
  return pendingCreationMutationId;
}

/** index.html's _authorConsumePendingCreationMutationId's OWN half: reads
 *  and clears. Its other half (loadPendingCreations(), a still-legacy
 *  germ-realization refresh) is not ported -- Sheet.svelte calls it via
 *  legacyCall right after this, preserving the original combined order. */
export function consumePendingCreationMutationId() {
  pendingCreationMutationId = null;
}

/** index.html's generatePendingCreation (germ realization, still legacy)
 *  used to write the bare `pendingCreationMutationId` global directly before
 *  dispatching 'creation:sheet-create'; a bare `let` in a Svelte module can't
 *  be written from across the legacy boundary, so the id now rides in that
 *  same event's detail instead (Sheet.svelte's listener calls this). */
export function setPendingCreationMutationId(id) {
  pendingCreationMutationId = id;
}

/** index.html's _authorNotifySaved, ported into the save path per this
 *  brief's item 4: authorEntityType (its other half) had zero readers
 *  anywhere in the tree (confirmed by grep) and is dropped, not ported --
 *  selectedEntityId is the one fact any reader ever used. Still dispatches
 *  'creation:selection' on legacyDoc, same shape/detail authorSelectEntity
 *  itself always dispatched, since a handful of still-legacy chrome sites
 *  (creationOpenEntityFrom's return-crumb origin, an entity tab's
 *  slots.forEach notification, creationRenderReturnControl) read it to stay
 *  in sync until they migrate at -l. */
export function notifySaved(legacyDoc, id) {
  creationState.selectedEntityId = id;
  legacyDoc.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: id, recordId: null } }));
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = `${path} -> ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') msg = body.detail;
    } catch (_err) {
      // response body wasn't JSON -- keep the status-based message
    }
    throw new Error(msg);
  }
  return res.json();
}

/** index.html's authorSelectEntity, ported -- the sheet's loader. Writes
 *  creationState directly (item 2's own framing: "sets store state
 *  directly") instead of dispatching 'creation:sheet-loading'/'creation:
 *  sheet-error'/'creation:sheet-detail' for Sheet.svelte to round-trip back
 *  into itself -- those three events existed only for that round trip and
 *  had no other dispatcher, so they're retired with this function rather
 *  than kept as a dead indirection.
 *
 *  NOT ported: the old sheetRenderer branch. The only CREATION_TABS entry
 *  ever declaring one (intrigues) is reached exclusively through
 *  creationSelectRecord, never through an id-keyed entity select -- RECON-
 *  0059-a M2/M3's own caller trace confirms authorSelectEntity's three real
 *  callers (this one, creationOpenEntityFrom, creationReturnToOrigin) are
 *  never active while currentCreationSubTab === 'intrigues' (creationResolveEntityTab
 *  never resolves to a tab with no `.type`, and intrigues declares none).
 *  Porting a branch that can't fire would read the chrome CREATION_TABS
 *  global from sheet-owned code for no behavioural gain.
 *
 *  'creation:selection' still fires on legacyDoc, same shape as always: a
 *  handful of still-legacy chrome sites (creationOpenEntityFrom's
 *  return-crumb origin, an entity tab's slots.forEach notification,
 *  creationRenderReturnControl) read it to stay in sync until they migrate
 *  at -l. */
export async function selectEntity(legacyDoc, id) {
  creationState.sheetMode = 'loading';
  try {
    const detail = await api(`/api/entities/${encodeURIComponent(id)}`);
    creationState.sheetMode = 'view';
    creationState.sheetIsNew = false;
    creationState.sheetType = detail.type;
    creationState.sheetDetail = detail;
    creationState.selectedEntityId = id;
    creationState.selectedRecordId = null;
    legacyDoc.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: id, recordId: null } }));
  } catch (e) {
    creationState.sheetMode = 'error';
    creationState.sheetErrorMessage = e.message;
  }
}

/** index.html's authorGetSelectedEntityId -- the relations graph consumer's
 *  ego-mode load (graph/consumers/relations.js) reads the currently
 *  selected entity through here now, instead of the deleted
 *  authorGetSelectedEntityId/getSelectedCharacterId bridge pair. */
export function getSelectedEntityId() {
  return creationState.selectedEntityId;
}
