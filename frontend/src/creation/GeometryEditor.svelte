<script>
  /* TICKET-0058 (BRIEF-0058-g, family a). Faithful port of
     authorRenderGeometryEditor/authorRenderGeometryEditorFromItems/
     authorGeometryDetectItem/authorAddGeometryRow/authorRemoveGeometryRow/
     authorSaveGeometry (index.html, now deleted) -- the location's spatial
     geometry sub-editor (bounds_width/bounds_height + rectangle/polygon
     obstacles), mounted by Sheet.svelte into the "Spatial geometry"
     field-section for an existing location.

     The four DOM-scraping sync helpers this family retires
     (_syncGeometryItemsFromDom/_currentGeometryBoundsFromDom) become real
     Svelte state here (RECON-SUPPLEMENT-0058 -g item 2): rows are bound
     directly via bind:value rather than re-read from the DOM at save time.
     A rect item stays individually editable (x/y/width/height); a polygon
     item stays display-only (vertex count) with a remove affordance --
     same as the legacy editor, no new authoring capability for polygons.

     PUT /api/entities/{id}/geometry is the same sanctioned endpoint
     (geometry_unit.py/placement_unit.py are backend-only and untouched).
     On success, `onSaved(detail)` hands the fresh entity detail back to
     Sheet.svelte (the same enterViewMode a 'creation:sheet-detail' dispatch
     used to trigger via _authorRefreshSheet) instead of a DOM CustomEvent
     round-trip -- parent and child are both real Svelte now, so a direct
     callback prop replaces the event. */
  let { entityId, geometry, legacyDoc, onSaved } = $props();

  let items = $state([]);
  let boundsWidth = $state('');
  let boundsHeight = $state('');

  function detectItem(vertices) {
    if (Array.isArray(vertices) && vertices.length === 4) {
      const [p0, p1, p2, p3] = vertices;
      if (p0[1] === p1[1] && p1[0] === p2[0] && p2[1] === p3[1] && p3[0] === p0[0]
          && p1[0] > p0[0] && p2[1] > p1[1]) {
        return { kind: 'rect', x: p0[0], y: p0[1], width: p1[0] - p0[0], height: p2[1] - p1[1] };
      }
    }
    return { kind: 'polygon', vertices };
  }

  function resetFromGeometry(g) {
    items = (g?.obstacles || []).map((o) => detectItem(o.vertices));
    boundsWidth = g?.bounds_width ?? '';
    boundsHeight = g?.bounds_height ?? '';
  }

  $effect(() => { resetFromGeometry(geometry); });

  function addRow() {
    items = [...items, { kind: 'rect', x: 0, y: 0, width: 0, height: 0 }];
  }

  function removeRow(i) {
    items = items.filter((_, idx) => idx !== i);
  }

  async function save() {
    const statusEl = legacyDoc.getElementById('author-status');
    const bw = boundsWidth === '' ? null : parseFloat(boundsWidth);
    const bh = boundsHeight === '' ? null : parseFloat(boundsHeight);
    const obstacles = items.map((item) =>
      item.kind === 'rect' ? { rect: [item.x, item.y, item.width, item.height] } : { vertices: item.vertices }
    );
    try {
      const res = await fetch(`/api/entities/${encodeURIComponent(entityId)}/geometry`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bounds_width: bw, bounds_height: bh, obstacles }),
      });
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onSaved(data);
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Géométrie mise à jour.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }
</script>

<div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:8px">
  <label style="flex:1">Largeur (bounds_width)</label>
  <input type="number" step="any" bind:value={boundsWidth} style="flex:1">
  <label style="flex:1">Hauteur (bounds_height)</label>
  <input type="number" step="any" bind:value={boundsHeight} style="flex:1">
</div>
<div>
  {#if items.length === 0}
    <div class="empty">Aucun obstacle.</div>
  {:else}
    {#each items as item, i}
      <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:6px">
        {#if item.kind === 'rect'}
          <input type="number" step="any" bind:value={item.x} placeholder="x" style="flex:1">
          <input type="number" step="any" bind:value={item.y} placeholder="y" style="flex:1">
          <input type="number" step="any" bind:value={item.width} placeholder="largeur" style="flex:1">
          <input type="number" step="any" bind:value={item.height} placeholder="hauteur" style="flex:1">
        {:else}
          <span style="flex:1">polygone ({item.vertices.length} sommets)</span>
        {/if}
        <button class="btn-icon" onclick={() => removeRow(i)} title="Supprimer">✕</button>
      </div>
    {/each}
  {/if}
</div>
<div class="row-card-actions" style="margin-top:6px; gap:8px">
  <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={addRow}>+ Ajouter un bloc</button>
  <button class="btn-send" onclick={save}>💾 Enregistrer</button>
</div>
