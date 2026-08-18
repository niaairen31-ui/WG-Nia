<script>
  /* TICKET-0058 (BRIEF-0058-i, per RECON-SUPPLEMENT-0058's re-scope: this
     brief re-scoped from "Review Queue" -- which never used the governed
     review component (RECON) -- to "review component + Region", its first
     consumer). Faithful port of regionGenerate/regionRenderBriefForm/
     regionRenderManifest/regionBuild/regionRestart/regionReviewDescriptor/
     regionRenderFactionsPanel/regionRenderCommitResult/regionRenderAll/
     regionCommit/regionRenderSheet and their helpers (index.html, now
     deleted).

     The tree view routes through Review.svelte (the review component's
     Svelte-native half) via reviewRegister so the pre-commit graph preview
     (frontend/src/graph/consumers/review.js -> legacy/bridge.js's
     reviewGraphData -> review/registry.js, injected onto the legacy window
     for the room batch generator's continued use, BRIEF-0058-j) keeps
     resolving 'region' the same way it always has -- one REVIEW_DESCRIPTORS
     singleton, read from either realm.

     The sheet's own FIELD editor (the _sheetField family, _regionSheetNode,
     the _regionSheetRoles family, regionRenderSheet) is reimplemented
     natively here rather than converging onto Sheet.svelte/Field.svelte's
     field engine. RECON-SUPPLEMENT-0058 flags this as "distinct from
     authorRenderField... a genuine several-things-doing-the-same-thing
     candidate" and says REPORT ONLY -- do not converge it in this brief.
     Reported here, not resolved: region's sheet fields (plain text/
     textarea/select, no FieldSpec/ext_columns) duplicate Sheet.svelte's
     generic field renderer in shape. Nia decides whether that overlap
     earns its own convergence step. Unaffected by, and distinct from, the
     modal-SHELL convergence below.

     TICKET-0059 (BRIEF-0059-l commit 3, amendment). The sheet's outer
     modal SHELL (backdrop/container/header/close button) converged onto
     Modal.svelte -- it was reimplemented here (not reused) because the
     shared legacy generic modal's only other callers (world create/
     delete, skill delete) stayed legacy, and reaching across the realm
     boundary for every keystroke would have needed a window-injection
     trick not worth it for one consumer. Both reasons are gone: this
     brief deletes the legacy modal (commit 3) and the realm boundary
     itself (commit 4, Creation no longer lives in an iframe). The close
     glyph changes from this file's own ✕ to Modal.svelte's &times; --
     the primitive wins, a one-character visual change. closeSheet's own
     semantics are unchanged (still the onClose handler, called on both
     the close button and a backdrop click, dismissOnBackdrop defaulting
     to true exactly as this file's own onclick guard always did).

     World reset is driven by serverState.worldId (the -d rule), replacing
     _regionWorldReset. No scoped <style> block: like every other Creation
     island, this renders inside the legacy iframe document. */
  import { tick } from 'svelte';
  import { serverState } from '../lib/serverState.svelte.js';
  import { creationRefreshList } from './tabs.js';
  import { reviewRegister } from './review/registry.js';
  import Review from './Review.svelte';
  import Modal from './Modal.svelte';

  let { legacyDoc } = $props();

  let regionDraft = $state(null);
  let regionManifest = $state(null);
  let regionManifestNotes = $state([]);
  let regionManifestSkipped = $state([]);
  let regionAccepted = $state({});
  let regionConfirmedLinks = $state({});
  let regionCommitResult = $state(null);
  let regionLocGraphOpen = $state(false);

  let briefText = $state('');
  let genStatus = $state('');
  let buildStatus = $state('');
  let commitPending = $state(false);

  let sheetNode = $state(null); // { type: 'location'|'faction', localId } | null

  let briefInputEl = $state(null);

  const REGION_FACTION_COLORS = ['#e0703c', '#3c91e0', '#5cc06a', '#c95cc0', '#d4b23c', '#6a7bd1', '#c0505c', '#3cc0a8'];

  async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  function isAccepted(id) {
    return regionAccepted[id] !== false;
  }

  function toggleAccept(id) {
    regionAccepted[id] = !isAccepted(id);
  }

  function regionFactionColor(localId) {
    if (!regionDraft) return '#888';
    const i = regionDraft.factions.findIndex(f => f.local_id === localId);
    return REGION_FACTION_COLORS[i >= 0 ? i % REGION_FACTION_COLORS.length : 0];
  }

  function regionLinkKey(locLocalId, idx) {
    return `${locLocalId}#${idx}`;
  }

  function regionIsLinkConfirmed(key) {
    return !!regionConfirmedLinks[key];
  }

  function regionToggleLink(key) {
    regionConfirmedLinks[key] = !regionIsLinkConfirmed(key);
  }

  function regionEntityNotes(entry, kind) {
    const draft = entry.result.draft;
    const notes = [...(entry.result.notes || [])];
    if (kind === 'location') {
      for (const link of (draft.secret.sensed_links || [])) {
        if (link.kind === 'connection' || link.kind === 'faction') continue; // wirable — rendered as a toggle, not a note
        notes.push(`Lien perçu (${link.kind}) : ${link.name}${link.note ? ' — ' + link.note : ''}`);
      }
      if (draft.secret.subculture_hidden) notes.push(`Subculture cachée proposée : ${draft.secret.subculture_hidden}`);
    }
    return notes;
  }

  function openSheet(type, localId) {
    sheetNode = { type, localId };
  }

  function closeSheet() {
    sheetNode = null;
  }

  const sheetTarget = $derived.by(() => {
    if (!sheetNode || !regionDraft) return null;
    const collection = sheetNode.type === 'location' ? regionDraft.locations : regionDraft.factions;
    return (collection || []).find(e => e.local_id === sheetNode.localId) || null;
  });

  /** The single site that reads regionDraft/regionAccepted to build a
   *  descriptor (TICKET-0041) -- named to mirror the pre-move
   *  regionReviewDescriptor() so review_component.py's single-factory rule
   *  keeps the same shape at the new locus. Registered into review/
   *  registry.js's shared REVIEW_DESCRIPTORS so the pre-commit graph
   *  preview (consumer: 'review') resolves it the same way it resolves
   *  'batch'. */
  function regionReviewDescriptor() {
    if (!regionDraft) return null;
    return {
      key: 'region',
      nodes: regionDraft.locations.map(l => ({
        id: l.local_id,
        name: l.result.draft.public.name,
        subtitle: l.result.draft.public.location_type || '',
        parentId: l.parent_local_id,
        description: l.result.draft.public.description,
        notes: regionEntityNotes(l, 'location'),
        raw: l,
      })),
      accepted: regionAccepted,
      fallbackParentId: (regionDraft.locations.find(l => l.parent_local_id == null) || {}).local_id || null,
      reparentedLabel: 'rattaché à la racine',
      onToggleAccept: toggleAccept,
      onOpenSheet: id => openSheet('location', id),
      graph: {
        consumer: 'review',
        mountId: 'region-graph-mount',
        /** Pre-commit location graph adapter (C1, BRIEF-0033-d) — draft-fed,
         *  no IDs, read-only. Mirrors the intra-region half of
         *  _region_resolve_link_target (regions.py) for confirmed
         *  connection links: trim+lowercase name match, no DB fallback. */
        extraEdges: (acceptedIds, nodeById) => {
          const accepted = regionDraft.locations.filter(l => acceptedIds.has(l.local_id));
          const byName = new Map(accepted.map(l => [(l.result.draft.public.name || '').trim().toLowerCase(), l.local_id]));
          const edges = [];
          for (const l of accepted) {
            const links = l.result.draft.secret.sensed_links || [];
            links.forEach((link, idx) => {
              if (link.kind !== 'connection') return;
              if (!regionIsLinkConfirmed(regionLinkKey(l.local_id, idx))) return;
              const targetName = (link.name || '').trim().toLowerCase();
              if (!targetName) return;
              const targetId = byName.get(targetName);
              if (!targetId || targetId === l.local_id) return;
              edges.push({ id: `c-${l.local_id}-${idx}`, entity_a_id: l.local_id, entity_b_id: targetId, kind: 'connection' });
            });
          }
          return edges;
        },
      },
    };
  }

  const reviewDesc = $derived(regionReviewDescriptor());

  $effect(() => {
    if (reviewDesc) reviewRegister('region', reviewDesc);
  });

  $effect(() => {
    if (regionDraft && regionLocGraphOpen) {
      legacyDoc.dispatchEvent(new CustomEvent('graph:slot', {
        detail: { consumer: 'review', containerId: 'region-graph-mount', open: true, key: 'region' },
      }));
    }
  });

  async function regionGenerate() {
    const brief = briefText.trim();
    if (!brief) { genStatus = 'Intention requise.'; return; }
    genStatus = 'Génération du manifeste… (peut prendre un moment)';
    let result;
    try {
      result = await api('/api/regions/manifest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief }),
      });
    } catch (e) {
      genStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      genStatus = (result && result.error) || 'Échec de la génération.';
      return;
    }
    regionManifest = result.manifest;
    regionManifestNotes = result.notes || [];
    regionManifestSkipped = result.skipped || [];
    genStatus = '';
  }

  function manifestRemoveRow(kind, i) {
    regionManifest[kind].splice(i, 1);
  }

  function manifestAddFaction() {
    (regionManifest.factions = regionManifest.factions || []).push({ name: '', one_liner: '' });
  }

  function manifestAddLocation() {
    (regionManifest.locations = regionManifest.locations || []).push(
      { name: '', one_liner: '', is_root: false, parent_name: null });
  }

  function manifestSetRoot(i, checked) {
    const l = regionManifest.locations[i];
    l.is_root = checked;
    if (checked) l.parent_name = null;
  }

  async function regionBuild() {
    const isNameless = (item) => !((item.name || '').trim());
    const hasContent = (item) => !!((item.one_liner || '').trim());
    const blocked = ['factions', 'locations'].some(kind =>
      (regionManifest[kind] || []).some(item => isNameless(item) && hasContent(item)));
    if (blocked) {
      buildStatus = 'Chaque entrée doit avoir un nom.';
      return;
    }

    const manifestToSend = {
      ...regionManifest,
      factions: (regionManifest.factions || []).filter(f => !isNameless(f)),
      locations: (regionManifest.locations || []).filter(l => !isNameless(l)),
    };

    buildStatus = 'Génération des fiches… (peut prendre un moment)';
    let result;
    try {
      result = await api('/api/regions/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: manifestToSend }),
      });
    } catch (e) {
      buildStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      buildStatus = (result && result.error) || 'Échec de la génération.';
      return;
    }

    closeSheet();
    regionDraft = result.region;
    regionAccepted = {};
    regionConfirmedLinks = {};
    regionCommitResult = null;
  }

  function regionRestart() {
    closeSheet();
    regionDraft = null;
    regionManifest = null;
    regionManifestNotes = [];
    regionManifestSkipped = [];
    regionAccepted = {};
    regionConfirmedLinks = {};
    regionCommitResult = null;
    regionLocGraphOpen = false;
    briefText = '';
    genStatus = '';
    buildStatus = '';
  }

  async function regionCommit() {
    commitPending = true;
    let result;
    try {
      result = await api('/api/regions/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: regionDraft, accepted: regionAccepted, confirmed_links: regionConfirmedLinks }),
      });
    } catch (e) {
      result = { ok: false, error: e.message };
    }
    commitPending = false;
    regionCommitResult = result;
    if (result.ok) {
      // TICKET-0058: authorLoadEntityList is gone; the entity list now
      // lives in the entityList island, refreshed the same way its own
      // "↻" button does. Fire-and-forget.
      creationRefreshList();
    }
  }

  function addRole(node) {
    const pub = node.result.draft.public;
    if (!pub.roles) pub.roles = [];
    pub.roles.push({ name: '', description: '' });
  }

  function removeRole(node, i) {
    node.result.draft.public.roles.splice(i, 1);
  }

  function moveRole(node, i, dir) {
    const roles = node.result.draft.public.roles;
    const j = i + dir;
    if (j < 0 || j >= roles.length) return;
    [roles[i], roles[j]] = [roles[j], roles[i]];
  }

  // The active world is server-authoritative (TICKET-0056 C3); this island
  // discards any in-progress region on world switch rather than being told
  // to by a legacy onWorldSwitch callback (RECON-0058-a M5).
  $effect(() => {
    void serverState.worldId;
    regionRestart();
  });

  /** Region's primaryAction handler — discards any in-progress manifest/
   *  draft via regionRestart(), then focuses the fresh brief input. */
  export async function primaryAction() {
    regionRestart();
    await tick();
    briefInputEl?.focus();
  }
</script>

{#snippet locationExtra(n)}
  {@const wirable = ((n.raw.result.draft.secret.sensed_links) || [])
    .map((link, idx) => ({ link, idx }))
    .filter(({ link }) => link.kind === 'connection' || link.kind === 'faction')}
  {#if wirable.length}
    <div style="margin-top:4px">
      {#each wirable as { link, idx } (idx)}
        {@const key = regionLinkKey(n.raw.local_id, idx)}
        {@const confirmed = regionIsLinkConfirmed(key)}
        <div style="display:flex; align-items:center; gap:6px; font-size:11px; {confirmed ? '' : 'color:var(--muted)'}">
          <button class="btn-icon" onclick={() => regionToggleLink(key)}>{confirmed ? '✓ Confirmé' : 'Confirmer'}</button>
          <span>{link.kind === 'connection' ? 'Connexion' : 'Faction contrôlante'} : {link.name}{link.note ? ' — ' + link.note : ''}</span>
        </div>
      {/each}
    </div>
  {/if}
{/snippet}

{#if !regionDraft}
  {#if regionManifest}
    <!-- ── Manifest checkpoint (full editing) ── -->
    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:10px;">
      <div class="field-section-title">Concept</div>
      <textarea rows="3" style="width:100%; resize:vertical" bind:value={regionManifest.concept}></textarea>
    </div>
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap">
      <button class="btn-send" style="margin-left:auto" onclick={regionBuild}>Générer les fiches</button>
      <button class="btn-end" onclick={regionRestart}>Recommencer</button>
    </div>
    {#if [...regionManifestNotes, ...regionManifestSkipped.map(s => `${s.stage || ''} · ${s.name || '?'} — ${s.reason || ''}`)].length}
      <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
        <div class="field-section-title">Notes de génération du manifeste</div>
        {#each [...regionManifestNotes, ...regionManifestSkipped.map(s => `${s.stage || ''} · ${s.name || '?'} — ${s.reason || ''}`)] as n}
          <div style="font-size:11px; color:var(--muted)">{n}</div>
        {/each}
      </div>
    {/if}

    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:10px;">
      <div class="field-section-title" style="display:flex; align-items:center; gap:8px;">
        <span>Factions</span>
        <button class="btn-icon" style="margin-left:auto" onclick={manifestAddFaction}>+ Ajouter une faction</button>
      </div>
      {#if !(regionManifest.factions || []).length}
        <div class="empty">Aucun.</div>
      {:else}
        <div class="row-table">
          {#each regionManifest.factions as f, i}
            <div class="row-card">
              <div style="display:flex; align-items:flex-end; gap:8px; flex-wrap:wrap">
                <div class="field-row" style="flex:1; min-width:140px"><label>Nom</label>
                  <input type="text" placeholder="Nom de la faction" bind:value={f.name}></div>
                <button class="btn-icon" title="Retirer" onclick={() => manifestRemoveRow('factions', i)}>x</button>
              </div>
              <textarea rows="2" style="width:100%; resize:vertical" bind:value={f.one_liner}></textarea>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:10px;">
      <div class="field-section-title" style="display:flex; align-items:center; gap:8px;">
        <span>Lieux</span>
        <button class="btn-icon" style="margin-left:auto" onclick={manifestAddLocation}>+ Ajouter un emplacement</button>
      </div>
      {#if !(regionManifest.locations || []).length}
        <div class="empty">Aucun.</div>
      {:else}
        <div class="row-table">
          {#each regionManifest.locations as l, i}
            <div class="row-card">
              <div style="display:flex; align-items:flex-end; gap:8px; flex-wrap:wrap">
                <div class="field-row" style="flex:1; min-width:140px"><label>Nom</label>
                  <input type="text" placeholder="Nom du lieu" bind:value={l.name}></div>
                <div class="field-row checkbox" style="margin:0 0 5px 0">
                  <input type="checkbox" id={`region-loc-root-${i}`} checked={l.is_root}
                    onchange={(e) => manifestSetRoot(i, e.currentTarget.checked)}>
                  <label for={`region-loc-root-${i}`}>racine</label></div>
                <div class="field-row" style="min-width:140px"><label>Parent</label>
                  <select disabled={l.is_root} value={l.parent_name || ''}
                    onchange={(e) => l.parent_name = e.currentTarget.value || null}>
                    <option value="">--</option>
                    {#each regionManifest.locations.filter((_, j) => j !== i) as other}
                      <option value={other.name}>{other.name}</option>
                    {/each}
                    {#if l.parent_name && !regionManifest.locations.some((o, j) => j !== i && o.name === l.parent_name)}
                      <option value={l.parent_name}>{l.parent_name}</option>
                    {/if}
                  </select></div>
                <button class="btn-icon" title="Retirer" onclick={() => manifestRemoveRow('locations', i)}>x</button>
              </div>
              <textarea rows="2" style="width:100%; resize:vertical" bind:value={l.one_liner}></textarea>
            </div>
          {/each}
        </div>
      {/if}
    </div>
    <div style="font-size:12px; color:var(--muted)">{buildStatus}</div>
  {:else}
    <!-- ── Brief form ── -->
    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px;">
      <div class="field-section-title">Générer une région</div>
      <textarea rows="3" style="width:100%; resize:vertical" bind:this={briefInputEl} bind:value={briefText}
        placeholder="Intention en une phrase, ex. : « Un avant-poste minier en déclin, sous la coupe d'une guilde marchande corrompue »"></textarea>
      <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
        <button class="btn-send" onclick={regionGenerate}>Générer la région</button>
        <span style="font-size:12px; color:var(--muted)">{genStatus}</span>
      </div>
    </div>
  {/if}
{:else}
  <!-- ── Draft review + commit ── -->
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap">
    <h2 style="margin:0; font-size:15px">{regionDraft.concept || 'Région'}</h2>
    <button class="btn-send" style="margin-left:auto" onclick={regionCommit} disabled={commitPending}>Commit la région</button>
    <button class="btn-end" onclick={regionRestart}>Recommencer</button>
  </div>
  {#if (regionDraft.skipped || []).length}
    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
      <div class="field-section-title">Écartés à la génération</div>
      {#each regionDraft.skipped as s}
        <div style="font-size:11px; color:var(--muted)">{s.stage} · {s.name || '?'} — {s.reason || ''}</div>
      {/each}
    </div>
  {/if}
  <div style="margin-bottom:10px">
    <button class="btn-icon" onclick={() => regionLocGraphOpen = !regionLocGraphOpen}>
      {regionLocGraphOpen ? 'Masquer le graphe des lieux' : 'Voir le graphe des lieux'}
    </button>
    <div style="display:{regionLocGraphOpen ? 'block' : 'none'}; margin-top:8px;">
      <div class="lieux-graph-head"><span>Carte des lieux (aperçu pré-commit)</span></div>
      <div id="region-graph-mount"></div>
    </div>
  </div>
  <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start">
    <div style="flex:2; min-width:320px">
      <div class="field-section-title">Lieux</div>
      {#if reviewDesc}
        <Review descriptor={reviewDesc} extra={locationExtra} />
      {/if}
    </div>
    <div style="flex:1; min-width:240px">
      <div class="field-section-title">Factions</div>
      {#if !regionDraft.factions.length}
        <div class="empty">Aucune faction proposée.</div>
      {:else}
        <div class="row-table">
          {#each regionDraft.factions as f (f.local_id)}
            {@const accepted = isAccepted(f.local_id)}
            {@const color = regionFactionColor(f.local_id)}
            {@const notes = regionEntityNotes(f, 'faction')}
            <div class="row-card" class:review-rejected={!accepted}>
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap">
                <span class="region-fac-badge review-name-link" style="border-color:{color}; color:{color}"
                  onclick={() => openSheet('faction', f.local_id)}>{f.result.draft.public.name}</span>
                <button class="btn-icon" style="margin-left:auto" onclick={() => toggleAccept(f.local_id)}>
                  {accepted ? 'Rejeter' : 'Accepter'}</button>
              </div>
              {#if f.result.draft.public.description}
                <div style="font-size:12px; color:var(--muted)">{f.result.draft.public.description}</div>
              {/if}
              {#if notes.length}
                <div style="margin-top:4px">
                  {#each notes as n}
                    <div style="font-size:11px; color:var(--muted)">· {n}</div>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  <div>
    {#if regionCommitResult}
      {#if !regionCommitResult.ok}
        <div class="field-section" style="border:1px solid var(--red); border-radius:6px; padding:10px; margin-top:12px;">
          <div class="field-section-title" style="color:var(--red)">Échec du commit — aucun changement n'a été appliqué</div>
          <div style="font-size:12px">{regionCommitResult.error || ''}</div>
        </div>
      {:else}
        {@const c = regionCommitResult.committed}
        {@const links = regionCommitResult.links || { written: [], unresolved: [] }}
        {@const notes = regionCommitResult.notes || []}
        <div class="field-section" style="border:1px solid var(--green); border-radius:6px; padding:10px; margin-top:12px;">
          <div class="field-section-title" style="color:var(--green)">Région commitée</div>
          <div style="font-size:12px">{c.factions.length} faction(s), {c.locations.length} lieu(x) — entités créées dans le canon.</div>
          {#if links.written.length}
            <div style="font-size:12px; margin-top:4px">{links.written.length} lien(s) confirmé(s) câblé(s).</div>
          {/if}
          {#if links.unresolved.length}
            <div style="font-size:11px; color:var(--muted); margin-top:4px">
              {#each links.unresolved as u}
                <div>· {u.kind} « {u.name || ''} » non câblé — {u.reason || ''}</div>
              {/each}
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

{#if sheetTarget}
  {@const type = sheetNode.type}
  {@const pub = sheetTarget.result.draft.public}
  {@const sec = sheetTarget.result.draft.secret}
  {@const notes = sheetTarget.result.notes || []}
  <Modal title={pub.name || ''} open={true} onClose={closeSheet}>
    {#snippet body()}
        <div class="sheet-section-title">Public</div>
        {#if type === 'location'}
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Nom</div>
            <input type="text" style="width:100%" bind:value={pub.name}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Description</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={pub.description}></textarea></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Type</div>
            <input type="text" style="width:100%" bind:value={pub.location_type}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Niveau d'accès</div>
            <input type="text" style="width:100%" bind:value={pub.access_level}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Subculture</div>
            <input type="text" style="width:100%" bind:value={pub.subculture}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Contenu dans</div>
            <select value={sheetTarget.parent_local_id || ''}
              onchange={(e) => sheetTarget.parent_local_id = e.currentTarget.value || null}>
              <option value="">--</option>
              {#each regionDraft.locations.filter(e => e.local_id !== sheetNode.localId) as e (e.local_id)}
                <option value={e.local_id}>{e.result.draft.public.name || '(sans nom)'}{isAccepted(e.local_id) ? '' : ' (rejeté)'}</option>
              {/each}
            </select></div>

          <div class="sheet-section-title sheet-secret-title">Secret — caché en jeu</div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Subculture cachée</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={sec.subculture_hidden}></textarea></div>
          {#if (sec.sensed_links || []).length}
            <div class="sheet-field-label" style="font-size:11px; margin-top:6px">Liens perçus</div>
            {#each sec.sensed_links as l}
              <div class="sheet-list-item">{l.kind || ''} · {l.name || ''}{l.note ? ' — ' + l.note : ''}</div>
            {/each}
          {/if}
        {:else}
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Nom</div>
            <input type="text" style="width:100%" bind:value={pub.name}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Description</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={pub.description}></textarea></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Type</div>
            <input type="text" style="width:100%" bind:value={pub.faction_type}></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Philosophie</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={pub.philosophy}></textarea></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Structure interne</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={pub.internal_structure}></textarea></div>
          <div class="sheet-field-label" style="font-size:11px; margin-top:6px">Rôles</div>
          {@const roles = pub.roles || []}
          <div>
            {#if roles.length === 0}
              <div class="empty">Aucun rôle.</div>
            {/if}
            {#each roles as role, i}
              <div class="row-card" style="flex-direction:row; gap:8px; align-items:center;">
                <input type="text" placeholder="Rôle" style="flex:1" bind:value={role.name}>
                <input type="text" placeholder="Description" style="flex:2" bind:value={role.description}>
                <button class="btn-icon" title="Monter" disabled={i === 0} onclick={() => moveRole(sheetTarget, i, -1)}>↑</button>
                <button class="btn-icon" title="Descendre" disabled={i === roles.length - 1} onclick={() => moveRole(sheetTarget, i, 1)}>↓</button>
                <button class="btn-icon" title="Supprimer" onclick={() => removeRole(sheetTarget, i)}>✕</button>
              </div>
            {/each}
          </div>
          <div class="row-card-actions" style="margin-top:6px">
            <button class="btn-send" onclick={() => addRole(sheetTarget)}>+ Ajouter un rôle</button>
          </div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Aversion</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={pub.aversion}></textarea></div>

          <div class="sheet-section-title sheet-secret-title">Secret — caché en jeu</div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Tensions internes</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={sec.internal_tensions}></textarea></div>
          <div class="sheet-field"><div class="sheet-field-label" style="font-size:11px">Objectifs</div>
            <textarea rows="3" style="width:100%; resize:vertical" bind:value={sec.goals}></textarea></div>
        {/if}

        {#if notes.length}
          <div class="sheet-section-title">Notes</div>
          {#each notes as n}<div class="sheet-field">{n}</div>{/each}
        {/if}
    {/snippet}
  </Modal>
{/if}
