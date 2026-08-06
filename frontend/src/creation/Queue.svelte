<script>
  /* TICKET-0059 (BRIEF-0059-k commit 2). Faithful port of loadQueue's
     render half (index.html, now deleted) -- the healthy-empty state for
     the 'approved' filter, the generic empty state for every other
     filter, and the error branch are preserved verbatim (Item 3 of the
     brief: these are the surface's meaning, not decoration). One card per
     mutation is QueueCard.svelte's own concern.

     World reset is driven by serverState.worldId (the -d rule every
     migrated island follows); queueState.reloadToken (queue.svelte.js)
     is the second reload trigger -- bumped by QueueFilters.svelte's
     setFilter on every filter click and by the post-tick /
     post-analysis reassert, since those must reload even when the
     filter value itself doesn't change. */
  import { serverState } from '../lib/serverState.svelte.js';
  import { queueState, loadQueue } from './queue.svelte.js';
  import QueueCard from './QueueCard.svelte';

  $effect(() => {
    void serverState.worldId;
    void queueState.reloadToken;
    loadQueue();
  });
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Review Queue</h2>
    <button class="btn-icon" onclick={loadQueue} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if queueState.loading}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if queueState.loadError}
      <div class="empty" style="color:var(--red)">Error: {queueState.loadError}</div>
    {:else if queueState.mutations.length === 0}
      {#if queueState.currentFilter === 'approved'}
        <div class="empty-ok">✓ Empty — no apply errors or duplicate blocks.<br>This is the normal, healthy state.</div>
      {:else}
        <div class="empty">No "{queueState.currentFilter}" proposals.</div>
      {/if}
    {:else}
      {#each queueState.mutations as m (m.id)}
        <QueueCard mutation={m} selected={queueState.selectedIds.has(m.id)} />
      {/each}
    {/if}
  </div>
</div>
