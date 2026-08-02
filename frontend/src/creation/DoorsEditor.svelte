<script>
  /* TICKET-0058 (BRIEF-0058-g, family a). Faithful port of
     authorRenderDoorsEditor/authorRenderDoorsEditorFromState/
     authorSaveDoors/authorRemoveOrphanDoor (index.html, now deleted) --
     the location doors sub-editor (TICKET-0034, BRIEF-0034-a), mounted by
     Sheet.svelte into the "Portes" field-section for an existing location.

     Row set is driven by the location's connects_to neighbours (from
     detail.relations), not free text: a blank x or y on a neighbour row
     means no door toward it (the row is simply not sent) -- full-replace
     via PUT /api/entities/{id}/doors, same endpoint, same unit conventions
     (door_coverage.py/door_distinct_points.py/door_terminal.py are
     backend-only and untouched). Orphan rows (edge_live: false) render
     read-only above the neighbour rows; removing one saves immediately,
     same as the legacy editor.

     _readDoorsFromDom becomes real Svelte state (bind:value) per
     RECON-SUPPLEMENT-0058 -g item 2, rather than a DOM re-scrape at save
     time. */
  let { entityId, relations, doors, legacyDoc, onSaved } = $props();

  let neighbours = $state([]);
  let orphans = $state([]);
  let values = $state({});

  function resetFromProps(rels, doorRows) {
    neighbours = (rels || [])
      .filter((r) => r.type === 'connects_to')
      .map((r) => ({ id: r.other_entity_id, name: r.other_entity_name }));
    orphans = (doorRows || []).filter((d) => !d.edge_live);

    const doorsByTarget = {};
    (doorRows || []).forEach((d) => { doorsByTarget[d.target_location_id] = d; });
    const next = {};
    neighbours.forEach((n) => {
      const d = doorsByTarget[n.id];
      next[n.id] = { x: d ? d.x : '', y: d ? d.y : '' };
    });
    values = next;
  }

  $effect(() => { resetFromProps(relations, doors); });

  async function save() {
    const statusEl = legacyDoc.getElementById('author-status');
    const doorsPayload = [];
    neighbours.forEach((n) => {
      const v = values[n.id] || { x: '', y: '' };
      if (v.x === '' || v.y === '') return;
      doorsPayload.push({ target_location_id: n.id, x: parseFloat(v.x), y: parseFloat(v.y) });
    });
    try {
      const res = await fetch(`/api/entities/${encodeURIComponent(entityId)}/doors`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doors: doorsPayload }),
      });
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onSaved(data);
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Portes mises à jour.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }

  function removeOrphan(id) {
    orphans = orphans.filter((d) => d.id !== id);
    save();
  }
</script>

{#if orphans.length}
  {#each orphans as d (d.id)}
    <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:6px; opacity:0.75">
      <span style="flex:1">⚠ lien connects_to absent — cette porte est ignorée en jeu. Supprimez-la ou recréez le lien. ({d.target_name})</span>
      <button class="btn-icon" onclick={() => removeOrphan(d.id)} title="Supprimer">✕</button>
    </div>
  {/each}
{/if}

{#if neighbours.length === 0}
  <div class="empty">Aucun lieu adjacent — créez une relation connects_to d'abord.</div>
{:else}
  <div>
    {#each neighbours as n (n.id)}
      <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:6px">
        <span style="flex:1">{n.name}</span>
        <input type="number" step="any" bind:value={values[n.id].x} placeholder="x" style="flex:1">
        <input type="number" step="any" bind:value={values[n.id].y} placeholder="y" style="flex:1">
      </div>
    {/each}
  </div>
  <div class="row-card-actions" style="margin-top:6px; gap:8px">
    <button class="btn-send" onclick={save}>💾 Enregistrer</button>
  </div>
{/if}
