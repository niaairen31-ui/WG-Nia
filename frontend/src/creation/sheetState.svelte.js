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
