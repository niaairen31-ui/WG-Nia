<script>
  /* TICKET-0058 (BRIEF-0058-g, family c). Faithful port of the NPC Tarifs
     editor (BRIEF-20, relationalized TICKET-0025/BRIEF-0025-a) --
     authorRenderPricing/authorSavePriceEntry/authorDeletePriceEntry/
     authorAddPriceEntry/authorPriceListMutate (index.html, now deleted).
     `npc_price` rows, full-replace via PUT /api/entities/{id}/prices -- no
     proposed_mutation, no change_history (curated config).

     authorPriceListMutate always re-GETs the entity fresh before mutating
     the {tag: amount} dict and PUTting the whole thing back -- kept
     verbatim here (mutateFn below) rather than trusting the `detail` prop,
     since another path could have changed prices between renders. */
  let { entityId, prices, legacyDoc, onSaved } = $props();

  let rows = $state([]);

  $effect(() => {
    rows = Object.entries(prices || {}).map(([tag, amount]) => ({ tag, amount }));
  });

  let newTag = $state('');
  let newAmount = $state(null);

  async function mutateFn(fn) {
    const statusEl = legacyDoc.getElementById('author-status');
    try {
      const fresh = await fetch(`/api/entities/${encodeURIComponent(entityId)}`).then((r) => r.json());
      const priceList = { ...(fresh.prices || {}) };
      fn(priceList);
      const res = await fetch(`/api/entities/${encodeURIComponent(entityId)}/prices`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prices: priceList }),
      });
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onSaved(data);
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Tarifs mis à jour.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }

  function saveEntry(row) {
    if (!Number.isFinite(row.amount)) { alert('Montant invalide'); return; }
    mutateFn((pl) => { pl[row.tag] = row.amount; });
  }

  function deleteEntry(tag) {
    mutateFn((pl) => { delete pl[tag]; });
  }

  function addEntry() {
    const tag = newTag.trim();
    const amount = newAmount;
    if (!tag) { alert('Tag requis'); return; }
    if (!Number.isFinite(amount)) { alert('Montant invalide'); return; }
    mutateFn((pl) => { pl[tag] = amount; });
    newTag = '';
    newAmount = null;
  }
</script>

<div id="author-pricing-rows">
  {#if rows.length === 0}
    <div class="empty">Aucun tarif.</div>
  {:else}
    {#each rows as row (row.tag)}
      <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:6px">
        <span style="flex:1">{row.tag}</span>
        <input type="number" bind:value={row.amount} style="width:90px">
        <button class="btn-icon" onclick={() => saveEntry(row)} title="Enregistrer">💾</button>
        <button class="btn-icon" onclick={() => deleteEntry(row.tag)} title="Supprimer">✕</button>
      </div>
    {/each}
  {/if}
</div>
<div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-top:8px">
  <input type="text" bind:value={newTag} placeholder="tag (ex : biere)" style="flex:1">
  <input type="number" bind:value={newAmount} placeholder="montant" style="width:90px">
  <button class="btn-send" onclick={addEntry}>+ Ajouter</button>
</div>
