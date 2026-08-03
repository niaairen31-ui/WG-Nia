/* TICKET-0058 (BRIEF-0058-j, per RECON-SUPPLEMENT-0058's -j re-scope). The
   room batch generator's client-held draft state -- was batchAnchorId/
   batchAnchorName/batchCount/batchManifest/batchManifestAnchor/
   batchManifestNotes/batchManifestSkipped/batchDrafts/batchCoherence/
   batchAccepted/batchConfirmedEdges/batchGraphOpen/batchCommitResult
   (index.html, now deleted). A module-level store, not RoomBatch.svelte-
   local state, because the trigger ("Générer un lot ici") lives in
   EntityList.svelte -- a DIFFERENT mounted component instance than the one
   rendering #batch-panel-wrap -- exactly the reason generatePanelState/
   pendingDraftsState/subcultureDraftState are module-level too.

   Nothing here is persisted server-side; the atomic commit route
   (/api/room-batch/commit) is the only write, and it re-derives everything
   from what this store submits -- no draft id, no server-held session. */
export const roomBatchState = $state({
  open: false,
  anchorId: null,
  anchorName: null,
  count: 8,
  manifest: null,          // {rooms: [{name, one_liner, location_type, parent_room}]}
  manifestAnchor: null,    // anchor block returned by /manifest (name/location_type/description/…)
  manifestNotes: [],
  manifestSkipped: [],
  drafts: null,            // {rooms: [{local_id, name, parent_room, result:{draft, notes}}], skipped, notes}
  coherence: null,         // {edges: [{id, a_id, b_id, a_local, b_local, reason}], unresolved, notes}
  accepted: {},
  confirmedEdges: {},
  graphOpen: false,
  commitResult: null,
});

export function resetRoomBatch() {
  roomBatchState.open = false;
  roomBatchState.anchorId = null;
  roomBatchState.anchorName = null;
  roomBatchState.count = 8;
  roomBatchState.manifest = null;
  roomBatchState.manifestAnchor = null;
  roomBatchState.manifestNotes = [];
  roomBatchState.manifestSkipped = [];
  roomBatchState.drafts = null;
  roomBatchState.coherence = null;
  roomBatchState.accepted = {};
  roomBatchState.confirmedEdges = {};
  roomBatchState.graphOpen = false;
  roomBatchState.commitResult = null;
}

/** Lieux' "Générer un lot ici" (ported off renderLieuxBrowse/EntityList.svelte's
 *  own onclick) opens the panel anchored on a browsed location -- plain
 *  import now, no legacy-window call. */
export function openRoomBatch(anchorId, anchorName) {
  resetRoomBatch();
  roomBatchState.open = true;
  roomBatchState.anchorId = anchorId;
  roomBatchState.anchorName = anchorName;
}
