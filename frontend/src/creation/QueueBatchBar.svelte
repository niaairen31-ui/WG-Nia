<script>
  /* TICKET-0059 (BRIEF-0059-k commit 3). Faithful port of renderBatchBar +
     toggleSelectAll's DOM half + updateBatchBar (index.html, now deleted)
     -- mounts into #creation-shell-batch-bar, the third container
     (BRIEF-0005-c), distinct from both the filters slot and the queue
     body. Shown only on the 'proposed' filter WITH at least one row,
     matching the original's own showBatchBar gate exactly -- loadQueue's
     zero-mutations early return cleared the batch slot outright,
     regardless of filter.

     selectableIds/selectedCount/allSelected/indeterminate are all
     $derived from queueState (queue.svelte.js) -- never assigned inside
     an effect (effect_self_write.py's invariant: card list, selected-ids
     set and batch counts stay derived, not manually kept in sync). The
     master checkbox's `indeterminate` DOM property has no HTML attribute
     equivalent, so it is the one thing an effect sets directly on the
     element ref -- reading a $derived value, never a local $state
     assigned earlier in the same effect. */
  import { queueState, toggleSelectAll, doBatchAction } from './queue.svelte.js';

  let selectableIds = $derived(queueState.mutations.filter((m) => m.status === 'proposed').map((m) => m.id));
  let selectedCount = $derived(queueState.selectedIds.size);
  let allSelected = $derived(selectableIds.length > 0 && selectedCount === selectableIds.length);
  let indeterminate = $derived(selectedCount > 0 && selectedCount < selectableIds.length);

  let masterCbEl;

  // `indeterminate` must be read UNCONDITIONALLY, not behind the
  // `masterCbEl` guard: at the very first run masterCbEl is still
  // undefined (the checkbox doesn't exist until #if flips true, which
  // itself waits on the async loadQueue), so a short-circuited read never
  // registers `indeterminate` as a tracked dependency -- the effect would
  // then never re-run again once masterCbEl does appear.
  $effect(() => {
    const val = indeterminate;
    if (masterCbEl) masterCbEl.indeterminate = val;
  });

  function onToggleAll(ev) {
    toggleSelectAll(ev.currentTarget.checked, selectableIds);
  }
</script>

{#if queueState.currentFilter === 'proposed' && queueState.mutations.length > 0}
  <div class="batch-bar" id="batch-bar">
    <label>
      <input type="checkbox" bind:this={masterCbEl} checked={allSelected} onchange={onToggleAll}>
      Select all / none
    </label>
    <span class="batch-count">{selectedCount} selected</span>
    <div class="batch-actions">
      <button class="btn-approve" disabled={selectedCount === 0} onclick={() => doBatchAction('approve')}>✓ Approve selected</button>
      <button class="btn-reject" disabled={selectedCount === 0} onclick={() => doBatchAction('reject')}>✗ Reject selected</button>
    </div>
  </div>
{/if}
