<script>
  /* TICKET-0058 (BRIEF-0058-j, per RECON-SUPPLEMENT-0058's -j re-scope).
     Faithful port of batchReset/batchOpenPanel/batchClosePanel/
     batchGenerateManifest/batchManifestAddRow/RemoveRow/
     batchManifestParentOptions/batchRenderManifestTable/batchGenerateDrafts/
     batchRunCoherence/_batchNodeName/batchToggleEdgeConfirm/
     batchRenderEdgesPanel/batchOpenSheet/batchReviewDescriptor/
     batchRenderCommitResult/batchCommit/batchRenderAll (index.html, now
     deleted) -- the room batch generator, the review component's SECOND
     consumer (after Region.svelte, BRIEF-0058-i): registers through the
     exact same reviewRegister/reviewCascade singleton and renders its tree
     via <Review>, never the retired string-building render half -- nothing
     calls it once this brief lands, so BRIEF-0058-j removes it from
     review/registry.js rather than keep dead code "just in case".

     Mounted into #batch-panel-wrap on every 'lieux' tab activation (the
     -d rule: an island entry declares neither `loader` nor
     `onWorldSwitch`), same as entityList/entitySheet share that tab's
     other container -- but this island renders NOTHING (`open` stays
     false) until EntityList.svelte's "Générer un lot ici" button calls
     roomBatch.svelte.js's openRoomBatch(anchorId, anchorName), a plain
     import now instead of the legacy batchOpenPanel bridge.

     World reset is driven by serverState.worldId (the -d rule), replacing
     the legacy _lieuxWorldReset's batchReset() call.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { serverState } from '../lib/serverState.svelte.js';
  import { creationState } from './state.svelte.js';
  import { legacyCall } from '../legacy/bridge.js';
  import { locationTypeOptionLabel, openTemplateModalFor } from './locationType.js';
  import { reviewRegister } from './review/registry.js';
  import Review from './Review.svelte';
  import { roomBatchState, resetRoomBatch } from './roomBatch.svelte.js';

  let { legacyDoc } = $props();

  async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  let genStatus = $state('');
  let draftStatus = $state('');
  let coherenceStatus = $state('');
  let commitPending = $state(false);

  function isAccepted(id) {
    return roomBatchState.accepted[id] !== false;
  }

  function toggleAccept(id) {
    if (id === roomBatchState.anchorId) return; // Q1: non-toggleable
    roomBatchState.accepted[id] = !isAccepted(id);
  }

  async function generateManifest() {
    genStatus = 'Génération du manifeste… (peut prendre un moment)';
    let result;
    try {
      result = await api('/api/room-batch/manifest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anchor_id: roomBatchState.anchorId, count: roomBatchState.count }),
      });
    } catch (e) {
      genStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      genStatus = (result && result.error) || 'Échec de la génération.';
      return;
    }
    roomBatchState.manifest = result.manifest;
    roomBatchState.manifestAnchor = result.anchor;
    roomBatchState.manifestNotes = result.notes || [];
    roomBatchState.manifestSkipped = result.skipped || [];
    roomBatchState.drafts = null;
    roomBatchState.coherence = null;
    roomBatchState.accepted = {};
    roomBatchState.confirmedEdges = {};
    genStatus = '';
  }

  function manifestAddRow() {
    roomBatchState.manifest.rooms.push({ name: '', one_liner: '', location_type: '', parent_room: null });
  }

  function manifestRemoveRow(i) {
    roomBatchState.manifest.rooms.splice(i, 1);
  }

  async function generateDrafts() {
    const isNameless = (r) => !((r.name || '').trim());
    const rooms = roomBatchState.manifest.rooms.filter((r) => !isNameless(r));
    if (!rooms.length) { draftStatus = 'Au moins une pièce nommée est requise.'; return; }

    draftStatus = 'Génération des fiches… (peut prendre un moment)';
    let result;
    try {
      result = await api('/api/room-batch/draft', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: { rooms }, anchor: roomBatchState.manifestAnchor }),
      });
    } catch (e) {
      draftStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      draftStatus = (result && result.error) || 'Échec de la génération.';
      return;
    }
    roomBatchState.drafts = result;
    const accepted = {};
    for (const r of result.rooms) accepted[r.local_id] = true;
    accepted[roomBatchState.anchorId] = true;
    roomBatchState.accepted = accepted;
    roomBatchState.coherence = null;
    roomBatchState.confirmedEdges = {};
    draftStatus = '';
  }

  async function runCoherence() {
    coherenceStatus = 'Passe de cohérence…';
    let result;
    try {
      result = await api('/api/room-batch/coherence', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: roomBatchState.manifest, drafts: roomBatchState.drafts, anchor: roomBatchState.manifestAnchor }),
      });
    } catch (e) {
      coherenceStatus = e.message;
      return;
    }
    roomBatchState.coherence = result;
    roomBatchState.confirmedEdges = {};
    coherenceStatus = '';
  }

  function nodeName(id) {
    if (id === roomBatchState.anchorId) return roomBatchState.anchorName;
    const room = ((roomBatchState.drafts && roomBatchState.drafts.rooms) || []).find((r) => r.local_id === id);
    if (room) return room.name;
    const loc = (creationState.locationTree || []).find((l) => l.id === id);
    return loc ? loc.name : id;
  }

  function toggleEdgeConfirm(edgeId) {
    roomBatchState.confirmedEdges[edgeId] = !roomBatchState.confirmedEdges[edgeId];
  }

  let sheetTarget = $state(null); // { name, body } | null

  function openSheet(id) {
    if (id === roomBatchState.anchorId) {
      sheetTarget = { name: roomBatchState.anchorName, description: (roomBatchState.manifestAnchor && roomBatchState.manifestAnchor.description) || '' };
      return;
    }
    const room = ((roomBatchState.drafts && roomBatchState.drafts.rooms) || []).find((r) => r.local_id === id);
    if (!room) return;
    const pub = room.result.draft.public;
    sheetTarget = { name: room.name, locationType: pub.location_type || '', description: pub.description || '' };
  }

  function closeSheet() { sheetTarget = null; }

  /** The single site that reads roomBatchState.drafts/accepted to build a
   *  descriptor (TICKET-0041) -- named to mirror the pre-move
   *  batchReviewDescriptor() so review_component.py's single-factory rule
   *  keeps the same shape at this locus, mirroring Region.svelte's own
   *  regionReviewDescriptor. The anchor is a SYNTHETIC, always-accepted,
   *  non-toggleable root (Q1) -- toggleAccept above refuses it. */
  function batchReviewDescriptor() {
    const draftRooms = (roomBatchState.drafts && roomBatchState.drafts.rooms) || [];
    if (roomBatchState.accepted[roomBatchState.anchorId] === undefined) roomBatchState.accepted[roomBatchState.anchorId] = true;

    const nodes = [
      { id: roomBatchState.anchorId, name: roomBatchState.anchorName, subtitle: '(ancre)', parentId: null, description: '', notes: [] },
      ...draftRooms.map((r) => {
        const pub = r.result.draft.public;
        const parentRoom = r.parent_room ? draftRooms.find((o) => o.name === r.parent_room) : null;
        return {
          id: r.local_id, name: r.name, subtitle: pub.location_type || '',
          parentId: parentRoom ? parentRoom.local_id : roomBatchState.anchorId,
          description: pub.description, notes: r.result.notes || [],
        };
      }),
    ];

    return {
      key: 'batch',
      nodes,
      accepted: roomBatchState.accepted,
      fallbackParentId: roomBatchState.anchorId,
      reparentedLabel: 'rattaché à l\'ancre',
      onToggleAccept: toggleAccept,
      onOpenSheet: openSheet,
      graph: {
        consumer: 'review',
        mountId: 'batch-graph-mount',
        extraEdges: (acceptedIds) => {
          const edges = (roomBatchState.coherence && roomBatchState.coherence.edges) || [];
          return edges
            .filter((e) => roomBatchState.confirmedEdges[e.id] && acceptedIds.has(e.a_id) && acceptedIds.has(e.b_id))
            .map((e) => ({ id: e.id, entity_a_id: e.a_id, entity_b_id: e.b_id, kind: 'connection' }));
        },
      },
    };
  }

  const reviewDesc = $derived(roomBatchState.drafts ? batchReviewDescriptor() : null);

  $effect(() => {
    if (reviewDesc) reviewRegister('batch', reviewDesc);
  });

  $effect(() => {
    if (roomBatchState.drafts && roomBatchState.graphOpen) {
      legacyDoc.dispatchEvent(new CustomEvent('graph:slot', {
        detail: { consumer: 'review', containerId: 'batch-graph-mount', open: true, key: 'batch' },
      }));
    }
  });

  async function commit() {
    commitPending = true;
    const rooms = (roomBatchState.drafts.rooms || []).map((r) => ({ local_id: r.local_id, name: r.name, parent_room: r.parent_room, result: r.result }));
    const edges = (roomBatchState.coherence && roomBatchState.coherence.edges) || [];
    let result;
    try {
      result = await api('/api/room-batch/commit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          anchor_id: roomBatchState.anchorId, rooms, accepted: roomBatchState.accepted,
          edges, confirmed_edges: roomBatchState.confirmedEdges,
        }),
      });
    } catch (e) {
      result = { ok: false, error: e.message };
    }
    commitPending = false;
    roomBatchState.commitResult = result;
    if (result.ok) {
      legacyCall('creationRefreshList');
      if (creationState.activeTabKey === 'lieux') {
        legacyDoc.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'lieux' } }));
      }
    }
  }

  // The active world is server-authoritative (TICKET-0056 C3); this island
  // discards any in-progress batch on world switch rather than being told
  // to by a legacy onWorldSwitch callback (RECON-0058-a M5, the -d rule).
  $effect(() => {
    void serverState.worldId;
    resetRoomBatch();
  });

  // _lieuxTabEnterReset (index.html) fires this on every Lieux tab-enter,
  // the same 'creation:sheet-reset' idiom every other xTabEnterReset uses
  // -- any open batch panel closes on leaving/re-entering Lieux, matching
  // the legacy batchReset() call this replaces.
  legacyDoc.addEventListener('creation:batch-reset', () => { resetRoomBatch(); });
</script>

{#if roomBatchState.open}
  <div class="lieux-graph-head">
    <span>Génération de lot — {roomBatchState.anchorName}</span>
    <button class="btn-icon" onclick={resetRoomBatch}>Fermer</button>
  </div>
  <div style="padding:10px 14px; max-height:600px; overflow-y:auto">
    {#if !roomBatchState.manifest}
      <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px;">
        <div class="field-section-title">Générer le manifeste</div>
        <div class="field-row" style="max-width:160px"><label>Nombre de pièces</label>
          <input type="number" min="3" max="25" value={roomBatchState.count}
            oninput={(e) => { roomBatchState.count = Math.max(3, Math.min(25, Number(e.currentTarget.value) || 3)); }}></div>
        <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
          <button class="btn-send" onclick={generateManifest}>Générer le manifeste</button>
          <span style="font-size:12px; color:var(--muted)">{genStatus}</span>
        </div>
      </div>
    {:else if !roomBatchState.drafts}
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap">
        <button class="btn-icon" onclick={manifestAddRow}>+ Ajouter une pièce</button>
        <button class="btn-send" onclick={generateDrafts} style="margin-left:auto">Générer les fiches</button>
      </div>
      {#if [...roomBatchState.manifestNotes, ...roomBatchState.manifestSkipped.map(s => `${s.stage || ''} · ${s.name || '?'} — ${s.reason || ''}`)].length}
        <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
          <div class="field-section-title">Notes de génération du manifeste</div>
          {#each [...roomBatchState.manifestNotes, ...roomBatchState.manifestSkipped.map(s => `${s.stage || ''} · ${s.name || '?'} — ${s.reason || ''}`)] as n}
            <div style="font-size:11px; color:var(--muted)">{n}</div>
          {/each}
        </div>
      {/if}
      <div class="row-table">
        {#each roomBatchState.manifest.rooms as r, i}
          {@const typeInputId = `batch-type-${i}`}
          {@const typeDlId = `${typeInputId}-dl`}
          <div class="row-card">
            <div style="display:flex; align-items:flex-end; gap:8px; flex-wrap:wrap">
              <div class="field-row" style="flex:1; min-width:140px"><label>Nom</label>
                <input type="text" placeholder="Nom de la pièce" bind:value={r.name}></div>
              <div class="field-row" style="min-width:200px"><label>Type</label>
                <div style="display:flex; gap:6px; align-items:center">
                  <input type="text" id={typeInputId} list={typeDlId} bind:value={r.location_type} style="flex:1">
                  <button type="button" class="btn-ghost" style="font-size:12px; padding:3px 8px"
                    onclick={() => openTemplateModalFor(legacyDoc, typeInputId, () => {})}>Gabarit...</button>
                </div>
                <datalist id={typeDlId}>
                  {#each (creationState.locationTypeCatalog || []) as row (row.name)}
                    <option value={row.name}>{locationTypeOptionLabel(row)}</option>
                  {/each}
                </datalist></div>
              <div class="field-row" style="min-width:160px"><label>Parent</label>
                <select value={r.parent_room || ''} onchange={(e) => { r.parent_room = e.currentTarget.value || null; }}>
                  <option value="">{roomBatchState.anchorName} (ancre)</option>
                  {#each roomBatchState.manifest.rooms.filter((_, j) => j !== i) as other}
                    <option value={other.name}>{other.name}</option>
                  {/each}
                  {#if r.parent_room && !roomBatchState.manifest.rooms.some((o, j) => j !== i && o.name === r.parent_room)}
                    <option value={r.parent_room}>{r.parent_room}</option>
                  {/if}
                </select></div>
              <button class="btn-icon" title="Retirer" onclick={() => manifestRemoveRow(i)}>x</button>
            </div>
            <textarea rows="2" style="width:100%; resize:vertical" placeholder="Accroche en une ligne" bind:value={r.one_liner}></textarea>
          </div>
        {/each}
      </div>
      <div style="font-size:12px; color:var(--muted); margin-top:8px">{draftStatus}</div>
    {:else}
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap">
        <button class="btn-icon" onclick={runCoherence}>Passe de cohérence</button>
        <span style="font-size:12px; color:var(--muted)">{coherenceStatus}</span>
        <button class="btn-send" onclick={commit} style="margin-left:auto" disabled={commitPending}>Commiter le lot</button>
      </div>
      {#if (roomBatchState.drafts.skipped || []).length}
        <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
          <div class="field-section-title">Écartées à la génération</div>
          {#each roomBatchState.drafts.skipped as s}
            <div style="font-size:11px; color:var(--muted)">{s.name} — {s.reason || ''}</div>
          {/each}
        </div>
      {/if}
      <div style="margin-bottom:10px">
        <button class="btn-icon" onclick={() => roomBatchState.graphOpen = !roomBatchState.graphOpen}>
          {roomBatchState.graphOpen ? 'Masquer le graphe' : 'Voir le graphe'}
        </button>
        <div style="display:{roomBatchState.graphOpen ? 'block' : 'none'}; margin-top:8px;">
          <div class="lieux-graph-head"><span>Carte du lot (aperçu pré-commit)</span></div>
          <div id="batch-graph-mount"></div>
        </div>
      </div>
      <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start">
        <div style="flex:2; min-width:320px">
          <div class="field-section-title">Pièces</div>
          {#if reviewDesc}
            <Review descriptor={reviewDesc} />
          {/if}
        </div>
        <div style="flex:1; min-width:240px">
          <div class="field-section-title">Arêtes supplémentaires</div>
          {#if !roomBatchState.coherence}
            <div class="empty">Passe de cohérence non lancée.</div>
          {:else}
            {@const edges = roomBatchState.coherence.edges || []}
            {@const unresolved = roomBatchState.coherence.unresolved || []}
            {@const notes = roomBatchState.coherence.notes || []}
            {#if !edges.length}
              <div class="empty">Aucune arête supplémentaire proposée.</div>
            {:else}
              {#each edges as e (e.id)}
                {@const confirmed = !!roomBatchState.confirmedEdges[e.id]}
                <div style="display:flex; align-items:center; gap:6px; font-size:11px; {confirmed ? '' : 'color:var(--muted)'}">
                  <button class="btn-icon" onclick={() => toggleEdgeConfirm(e.id)}>{confirmed ? '✓ Confirmé' : 'Confirmer'}</button>
                  <span>{nodeName(e.a_id)} {'<->'} {nodeName(e.b_id)}{e.reason ? ' — ' + e.reason : ''}</span>
                </div>
              {/each}
            {/if}
            {#if unresolved.length}
              <div style="margin-top:8px">
                {#each unresolved as u}
                  <div style="font-size:11px; color:var(--muted)">· {u.a} {'<->'} {u.b} — {u.reason || ''}</div>
                {/each}
              </div>
            {/if}
            {#if notes.length}
              <div style="margin-top:8px">
                {#each notes as n}<div style="font-size:11px; color:var(--muted)">· {n}</div>{/each}
              </div>
            {/if}
          {/if}
        </div>
      </div>
      <div>
        {#if roomBatchState.commitResult}
          {#if !roomBatchState.commitResult.ok}
            <div class="field-section" style="border:1px solid var(--red); border-radius:6px; padding:10px; margin-top:12px;">
              <div class="field-section-title" style="color:var(--red)">Échec du commit — aucun changement n'a été appliqué</div>
              <div style="font-size:12px">{roomBatchState.commitResult.error || ''}</div>
            </div>
          {:else}
            {@const rooms = (roomBatchState.commitResult.committed && roomBatchState.commitResult.committed.rooms) || []}
            {@const unresolved = roomBatchState.commitResult.unresolved || []}
            {@const notes = roomBatchState.commitResult.notes || []}
            <div class="field-section" style="border:1px solid var(--green); border-radius:6px; padding:10px; margin-top:12px;">
              <div class="field-section-title" style="color:var(--green)">Lot commité</div>
              <div style="font-size:12px">{rooms.length} pièce(s) créée(s), {roomBatchState.commitResult.edges_written || 0} arête(s) écrite(s).</div>
              {#if unresolved.length}
                <div style="font-size:11px; color:var(--muted); margin-top:4px">
                  {#each unresolved as u}<div>· {u.reason || ''}</div>{/each}
                </div>
              {/if}
              {#if notes.length}
                <div style="font-size:11px; color:var(--yellow); margin-top:4px">
                  {#each notes as n}<div>· {n}</div>{/each}
                </div>
              {/if}
            </div>
          {/if}
        {:else if commitPending}
          <div class="empty" style="margin-top:12px"><span class="spin">⟳</span> Commit en cours…</div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

{#if sheetTarget}
  <div class="modal-backdrop" onclick={(e) => { if (e.target === e.currentTarget) closeSheet(); }}>
    <div class="modal-container">
      <div class="modal-header">
        <span class="modal-title">{sheetTarget.name}</span>
        <button class="modal-close" onclick={closeSheet}>✕</button>
      </div>
      <div class="modal-body">
        {#if sheetTarget.locationType}
          <div style="font-size:12px; color:var(--muted)">{sheetTarget.locationType}</div>
        {/if}
        <div style="margin-top:8px">{sheetTarget.description}</div>
      </div>
    </div>
  </div>
{/if}
