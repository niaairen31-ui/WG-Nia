<script>
  /* TICKET-0058 (BRIEF-0058-g, family d). Faithful port of the read-only
     "Items" section on a character sheet -- authorLoadItems/authorRenderItems
     (index.html, now deleted). Single write path is the entity/item flow
     elsewhere; this panel only reads GET /api/entities/{id}/items. */
  let { entityId } = $props();

  let items = $state([]);
  let loadError = $state('');

  async function load() {
    try {
      items = await fetch(`/api/entities/${encodeURIComponent(entityId)}/items`).then((r) => r.json());
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => { load(); });
</script>

{#if loadError}
  <div class="empty">{loadError}</div>
{:else if items.length === 0}
  <div class="empty">No items.</div>
{:else}
  <div class="row-table">
    {#each items as it}
      <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;">
        <span>{it.name}</span>
        <span style="display:flex; align-items:center; gap:8px;">
          <span style="color:var(--muted); font-size:12px;">{it.condition}</span>
          <span class="badge {it.equipped ? 'b-equipped' : 'b-stowed'}">{it.equipped ? 'equipped' : 'stowed'}</span>
        </span>
      </div>
    {/each}
  </div>
{/if}
