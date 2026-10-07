<script>
  /* TICKET-0058 (BRIEF-0058-g, family d) read-only port; editable since
     TICKET-0109 (BRIEF-0109-A, A1). An item is a kind held in quantity:
     on a character, faction or location sheet this panel lists what that
     entity holds; on an item's sheet, who holds it. Every change is one
     PUT /api/item-holdings (absolute quantity; 0 removes it from the list).
     The server refuses a zone as a place that receives. */
  import { api } from './sheetRequest.svelte.js';

  let { entityId, entityType } = $props();

  let rows = $state([]);
  let choices = $state([]);
  let loadError = $state('');
  let saveError = $state('');
  let busy = $state(false);
  let adding = $state({ id: '', quantity: 1 });

  let ofItem = $derived(entityType === 'item');

  async function load() {
    try {
      rows = await api(ofItem
        ? `/api/items/${encodeURIComponent(entityId)}/holders`
        : `/api/entities/${encodeURIComponent(entityId)}/items`);
      const all = ofItem
        ? (await Promise.all(['character', 'faction', 'location'].map((t) => api('/api/entities?type=' + t)))).flat()
        : await api('/api/entities?type=item');
      choices = all.filter((e) => e.id !== entityId);
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => { void entityId; load(); });

  async function setQuantity(otherId, quantity) {
    busy = true;
    saveError = '';
    const body = ofItem
      ? { item_id: entityId, holder_entity_id: otherId, quantity: Number(quantity) }
      : { item_id: otherId, holder_entity_id: entityId, quantity: Number(quantity) };
    try {
      await api('/api/item-holdings', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      adding = { id: '', quantity: 1 };
      await load();
    } catch (e) {
      saveError = e.message;
    } finally {
      busy = false;
    }
  }
</script>

{#if loadError}
  <div class="empty">{loadError}</div>
{:else}
  {#if rows.length === 0}
    <div class="empty">{ofItem ? 'Personne ne le détient.' : 'Aucun objet.'}</div>
  {:else}
    <div class="row-table">
      {#each rows as r (r.id)}
        <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;">
          <span>{r.name}{#if !ofItem && r.condition && r.condition !== 'intact'} <span style="color:var(--muted); font-size:12px;">({r.condition})</span>{/if}</span>
          <span style="display:flex; align-items:center; gap:6px;">
            <input type="number" min="0" style="width:64px" value={r.quantity} disabled={busy}
                   onchange={(e) => setQuantity(r.id, e.currentTarget.value)}>
            <button class="btn-icon" title="Retirer" disabled={busy} onclick={() => setQuantity(r.id, 0)}>✕</button>
          </span>
        </div>
      {/each}
    </div>
  {/if}
  <div style="display:flex; gap:6px; align-items:center; margin-top:6px;">
    <select bind:value={adding.id} disabled={busy}>
      <option value="">{ofItem ? '— donner à —' : '— ajouter un objet —'}</option>
      {#each choices as c (c.id)}<option value={c.id}>{c.name}{ofItem ? ` (${c.type})` : ''}</option>{/each}
    </select>
    <input type="number" min="1" style="width:64px" bind:value={adding.quantity} disabled={busy}>
    <button disabled={busy || !adding.id} onclick={() => setQuantity(adding.id, adding.quantity)}>Ajouter</button>
  </div>
  {#if saveError}<div style="color:var(--red); font-size:12px;">{saveError}</div>{/if}
{/if}
