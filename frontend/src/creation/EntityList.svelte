<script>
  /* TICKET-0058 (BRIEF-0058-e). The Creation entity-list sidebar -- one
     Svelte island mounted into #author-entity-list, shared by SEVEN
     CREATION_TABS entries (npc/pj/lieux/factions/objets/intrigues/
     evenements) plus every runtime type, per Nia's amendment to this
     brief: one shared mount point, one component, never three renderers
     racing for one node.

     Faithful port of creationRenderEntityList/authorRenderEntityList/
     authorLoadEntityList/renderLieuxBrowse (index.html, now deleted) plus
     the lieux hierarchy helpers, PLUS renderIntriguesListRows/
     renderEvenementsListRows -- also deleted, since #author-entity-list
     is a single Svelte-owned DOM node from this brief onward and a legacy
     innerHTML on it (RECON-0058-a M5's destruction mode) would orphan
     whichever tab's rendering got here first, regardless of which tab
     wrote it.

     The SHEET stays entirely legacy for `pj`'s create mode (#author-main,
     brief -f) -- unchanged. An ENTITY row click no longer bridges into
     legacy at all (TICKET-0059, BRIEF-0059-e): authorSelectEntity converged
     onto frontend/src/creation/sheetState.svelte.js's selectEntity, a plain
     Svelte-to-Svelte import. `evenements` converged onto real Svelte state
     (BRIEF-0058-j): its list is fetched by this component directly
     (loadEvents, mirroring loadGenericEntities -- no more 'creation:list-data'
     push from a legacy loadEventsList, which is gone), and its row click
     still reaches Sheet.svelte through creationSelectRecord (unchanged
     call), which now dispatches 'creation:record-detail' instead of calling
     a bespoke sheetRenderer. `intrigues` converged the same way (TICKET-0059,
     BRIEF-0059-j commit 1): loadAgendaRecords calls intrigues.svelte.js's
     loadAgendas (self-fetched, assigned into creationState.agendas) in
     place of the legacy listLoader + 'creation:list-data' push
     (loadAgendasList, now deleted); its row click reaches Sheet.svelte the
     identical way evenements' does. "Générer un lot ici" and "Générer les
     buts manquants" (BRIEF-0058-j) reach the room-batch island and the
     goals-backfill endpoint by plain import/fetch now too -- neither is a
     legacy function any more, so legacy/bridge.js's openBatchPanel/
     triggerNpcGoalsBackfill are gone.

     No scoped <style> block: like Graph.svelte and Constructeur.svelte,
     this renders inside the legacy iframe document, where Svelte's
     shell-injected scoped CSS never reaches. Markup reuses the legacy
     document's own classes/CSS vars.

     TICKET-0059 (BRIEF-0059-j commit 1): intrigues converged onto real
     Svelte state the same way evenements did (BRIEF-0058-j) -- its list is
     now fetched by this component directly (loadAgendaRecords, mirroring
     loadEvents), no more 'creation:list-data' push from a legacy
     loadAgendasList, which is gone. Its row click still reaches
     Sheet.svelte through creationSelectRecord, now a plain Svelte-to-Svelte
     import (BRIEF-0059-l commit 1: creationSelectRecord ported off the
     legacy window into tabs.js, alongside the rest of Creation's chrome),
     which still dispatches 'creation:record-detail' too. */
  import { creationState } from './state.svelte.js';
  import { creationSelectRecord } from './tabs.js';
  import { selectEntity } from './sheetState.svelte.js';
  import { openRoomBatch } from './roomBatch.svelte.js';
  import { loadAgendas } from './intrigues.svelte.js';

  let { legacyDoc } = $props();

  const GENERIC_TYPE_BY_TAB = { npc: 'character', pj: 'character', lieux: 'location', factions: 'faction', objets: 'item' };
  const LOCATION_TYPE_ORDER = ['city', 'district', 'building', 'room', 'natural', 'underground', 'other'];
  const LOCATION_TYPE_LABELS = {
    city: 'Villes', district: 'Quartiers', building: 'Bâtiments', room: 'Pièces',
    natural: 'Lieux naturels', underground: 'Souterrains', other: 'Autres',
  };

  let mode = $state('loading'); // 'loading' | 'flat' | 'lieux' | 'record' | 'error'
  let errorMessage = $state('');
  let recordsReady = $state(false);
  let previousTabKey = null;

  // Lieux browse view-state -- component-local (unlike entities/agendas,
  // nothing outside this island reads it once renderLieuxBrowse and its
  // helpers are gone; the room-batch "Générer un lot ici" trigger reaches
  // the room-batch island's own store directly, BRIEF-0058-j).
  let lieuxParentId = $state(null);
  let lieuxBreadcrumb = $state([]);
  let lieuxActiveOnly = $state(false);

  async function api(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return res.json();
  }

  async function loadGenericEntities() {
    mode = 'loading';
    try {
      const [entities, pcs, locations, locationTypes] = await Promise.all([
        api('/api/entities'),
        api('/api/skills/player-characters').catch(() => []),
        api('/api/locations').catch(() => []),
        api('/api/location-types').catch(() => []),
      ]);
      creationState.entities = entities;
      creationState.playerCharIds = new Set(pcs.map((p) => p.id));
      creationState.locationTree = locations;
      // BRIEF-0058-f: Sheet.svelte's location_type field needs the same
      // catalog this island already fetches -- mirrored into the shared
      // store rather than a second /api/location-types call.
      creationState.locationTypeCatalog = locationTypes;
      mode = creationState.activeTabKey === 'lieux' ? 'lieux' : 'flat';
      // Reverse bridge, extending the 'detail' payload precedent BRIEF-
      // 0058-d's Scope OUT reserved for "when they have a reader": still-
      // legacy consumers (faction roster candidates, location-type
      // classification, creationRenderReturnControl...) read
      // authorAllEntities/playerCharIds/authorLocationTree/
      // authorLocationTypeCatalog directly. authorLoadEntityList, their
      // sole populator, is deleted by this brief -- this keeps them fed.
      legacyDoc.dispatchEvent(new CustomEvent('creation:entities-loaded', {
        detail: {
          entities,
          playerCharIds: pcs.map((p) => p.id),
          locationTree: locations,
          locationTypeCatalog: locationTypes,
        },
      }));
    } catch (err) {
      errorMessage = err.message;
      mode = 'error';
    }
  }

  /** evenements' own list fetch (BRIEF-0058-j) -- mirrors loadGenericEntities'
   *  shape (self-fetched, pushed into creationState) rather than waiting on
   *  a legacy listLoader's 'creation:list-data' push; the now-deleted
   *  loadEventsList did the identical fetch, just from index.html. */
  async function loadEvents() {
    recordsReady = false;
    mode = 'record';
    try {
      creationState.events = await api('/api/events');
    } catch (err) {
      errorMessage = err.message;
      mode = 'error';
      return;
    }
    recordsReady = true;
  }

  /** intrigues' own list fetch (BRIEF-0059-j commit 1) -- same shape as
   *  loadEvents above; loadAgendas (intrigues.svelte.js) assigns straight
   *  into creationState.agendas, replacing the legacy listLoader +
   *  'creation:list-data' push (loadAgendasList, now deleted). */
  async function loadAgendaRecords() {
    recordsReady = false;
    mode = 'record';
    try {
      await loadAgendas();
    } catch (err) {
      errorMessage = err.message;
      mode = 'error';
      return;
    }
    recordsReady = true;
  }

  function activateTab(tabKey) {
    const isNewActivation = tabKey !== previousTabKey;
    previousTabKey = tabKey;
    if (tabKey === 'evenements') {
      loadEvents();
      return;
    }
    if (tabKey === 'intrigues') {
      loadAgendaRecords();
      return;
    }
    if (tabKey === 'lieux' && isNewActivation) {
      lieuxParentId = null;
      lieuxBreadcrumb = [];
    }
    loadGenericEntities();
  }

  // creation_island.py rule 8 confines 'island:slot' listening to
  // mount.js alone -- mount.js mirrors {activeTabKey, entityListActivationTick}
  // into the store on every dispatch (including a same-tab repeat), and
  // this effect reacts to that tick rather than the raw event.
  $effect(() => {
    void creationState.entityListActivationTick;
    if (creationState.activeTabKey) activateTab(creationState.activeTabKey);
  });

  legacyDoc.addEventListener('creation:selection', (ev) => {
    creationState.selectedEntityId = ev.detail.entityId ?? null;
    creationState.selectedRecordId = ev.detail.recordId ?? null;
  });

  function onSelectEntity(id) {
    selectEntity(legacyDoc, id);
  }

  function onSelectRecord(record) {
    creationSelectRecord(creationState.activeTabKey, record);
  }

  /** "Générer les buts manquants" (BRIEF-0013-b, ported off npcGoalsBackfillAll
   *  by BRIEF-0058-j) -- a plain fetch now, not a legacy-window call. If an
   *  NPC sheet is currently open, its goals list needs to refresh too; that
   *  refresh lives in GoalsEditor.svelte (BRIEF-0059-d, the one place that
   *  now owns the goals panel's load), reached the same one-bus way every
   *  other Svelte-to-Svelte signal on this document already is. */
  let npcGoalsBackfillStatus = $state('');

  async function backfillNpcGoals() {
    npcGoalsBackfillStatus = 'Génération…';
    try {
      const res = await fetch('/api/npc-goals/backfill', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      });
      const result = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
      npcGoalsBackfillStatus = `Traités : ${result.processed} · déjà complets : ${result.skipped_complete} · `
        + `écrits (long/court) : ${result.written.long}/${result.written.short}`
        + (result.failures.length ? ` · échecs : ${result.failures.length}` : '');
      legacyDoc.dispatchEvent(new CustomEvent('creation:goals-backfilled'));
    } catch (e) {
      npcGoalsBackfillStatus = e.message;
    }
  }

  function genericRows() {
    const tabKey = creationState.activeTabKey;
    const type = GENERIC_TYPE_BY_TAB[tabKey] || tabKey;
    let rows = creationState.entities.filter((e) => e.type === type);
    if (tabKey === 'npc') rows = rows.filter((e) => !creationState.playerCharIds.has(e.id));
    else if (tabKey === 'pj') rows = rows.filter((e) => creationState.playerCharIds.has(e.id));
    return rows;
  }

  function lieuxHasActiveDescendant(nodeId, visited) {
    visited = visited || new Set();
    if (visited.has(nodeId)) return false;
    visited.add(nodeId);
    const children = creationState.locationTree.filter((l) => l.parent_location_id === nodeId);
    for (const child of children) {
      if (child.status === 'active') return true;
      if (lieuxHasActiveDescendant(child.id, visited)) return true;
    }
    return false;
  }

  function lieuxChildrenOf(parentId) {
    const tree = creationState.locationTree;
    const knownIds = new Set(tree.map((l) => l.id));
    let children = parentId == null
      ? tree.filter((l) => !l.parent_location_id || !knownIds.has(l.parent_location_id))
      : tree.filter((l) => l.parent_location_id === parentId);
    if (lieuxActiveOnly) children = children.filter((l) => l.status === 'active' || lieuxHasActiveDescendant(l.id));
    return children;
  }

  function lieuxBuckets() {
    const children = lieuxChildrenOf(lieuxParentId);
    const buckets = {};
    for (const loc of children) {
      const key = LOCATION_TYPE_ORDER.includes(loc.location_type) ? loc.location_type : 'other';
      (buckets[key] = buckets[key] || []).push(loc);
    }
    return LOCATION_TYPE_ORDER
      .filter((t) => buckets[t] && buckets[t].length)
      .map((t) => ({
        type: t,
        label: LOCATION_TYPE_LABELS[t],
        rows: buckets[t].slice().sort((a, b) => a.name.localeCompare(b.name)),
      }));
  }

  function lieuxDescend(id, name) {
    lieuxBreadcrumb = [...lieuxBreadcrumb, { id, name }];
    lieuxParentId = id;
  }

  function lieuxJumpTo(index) {
    if (index < 0) {
      lieuxParentId = null;
      lieuxBreadcrumb = [];
    } else {
      lieuxBreadcrumb = lieuxBreadcrumb.slice(0, index + 1);
      lieuxParentId = lieuxBreadcrumb[lieuxBreadcrumb.length - 1].id;
    }
  }
</script>

{#if mode === 'loading'}
  <div class="empty"><span class="spin">⟳</span></div>
{:else if mode === 'error'}
  <div class="empty">{errorMessage}</div>
{:else if mode === 'flat'}
  {#if creationState.activeTabKey === 'npc'}
    <div class="row-card" style="margin-bottom:8px;">
      <button class="btn-ghost" style="font-size:12px; width:100%;" onclick={backfillNpcGoals}>Générer les buts manquants</button>
      <div style="font-size:11px; color:var(--muted); margin-top:4px;">{npcGoalsBackfillStatus}</div>
    </div>
  {/if}
  {#if genericRows().length === 0}
    <div class="empty">Aucune entité.</div>
  {:else}
    {#each genericRows() as e (e.id)}
      <div class="author-list-item {e.id === creationState.selectedEntityId ? 'active' : ''} {e.status === 'inactive' ? 'inactive' : ''}"
           onclick={() => onSelectEntity(e.id)}>
        <div class="ali-name">{e.name}</div>
        <div class="ali-meta">{e.type} · {e.status}</div>
      </div>
    {/each}
  {/if}
{:else if mode === 'lieux'}
  <div class="lieux-browse-head">
    <label class="field-row checkbox">
      <input type="checkbox" checked={lieuxActiveOnly} onchange={(ev) => { lieuxActiveOnly = ev.currentTarget.checked; }}>
      <span style="font-size:12px">Actifs seulement</span>
    </label>
    <div class="lieux-breadcrumb">
      <span class="lb-seg {lieuxParentId == null ? 'lb-current' : ''}" onclick={() => lieuxJumpTo(-1)}>Racine</span>
      {#each lieuxBreadcrumb as seg, i (seg.id)}
        <span class="lb-sep">›</span>
        <span class="lb-seg {i === lieuxBreadcrumb.length - 1 ? 'lb-current' : ''}" onclick={() => lieuxJumpTo(i)}>{seg.name}</span>
      {/each}
    </div>
    {#if lieuxParentId != null}
      <button class="btn-icon" onclick={() => openRoomBatch(lieuxParentId, lieuxBreadcrumb[lieuxBreadcrumb.length - 1]?.name || '')}>Générer un lot ici</button>
    {:else}
      <button class="btn-icon" disabled title="Descends dans un lieu pour l'utiliser comme ancre">Générer un lot ici</button>
    {/if}
  </div>
  {#if lieuxBuckets().length === 0}
    <div class="empty">Aucun lieu.</div>
  {:else}
    {#each lieuxBuckets() as bucket (bucket.type)}
      <div class="lieux-bucket-head">{bucket.label}</div>
      {#each bucket.rows as loc (loc.id)}
        {@const childCount = lieuxChildrenOf(loc.id).length}
        <div class="lieux-node-row {loc.status !== 'active' ? 'dimmed' : ''}">
          <button class="ali-name-btn" onclick={() => onSelectEntity(loc.id)}>{loc.name}</button>
          {#if loc.status !== 'active'}<span class="lieux-status-pill">{loc.status}</span>{/if}
          {#if childCount > 0}
            <button class="lieux-descend-btn" onclick={() => lieuxDescend(loc.id, loc.name)}>{childCount} enfant{childCount > 1 ? 's' : ''} ›</button>
          {/if}
        </div>
      {/each}
    {/each}
  {/if}
{:else if mode === 'record' && !recordsReady}
  <div class="empty"><span class="spin">⟳</span></div>
{:else if mode === 'record' && creationState.activeTabKey === 'intrigues'}
  {#if creationState.agendas.length === 0}
    <div class="empty">Aucune intrigue.</div>
  {:else}
    {#each creationState.agendas as a (a.id)}
      <div class="author-list-item {a.id === creationState.selectedRecordId ? 'active' : ''}" onclick={() => onSelectRecord(a)}>
        <div class="ali-name">{a.title}</div>
        <div class="ali-meta">
          <span style="color:var(--muted)">{a.owner_name}</span>
          <span class="badge b-other" title={a.owner_type === 'character' ? 'Intrigue personnelle' : 'Intrigue de faction'}>{a.owner_type === 'character' ? 'personnelle' : 'faction'}</span>
          <span class="badge b-{a.status}">{a.status}</span>
        </div>
      </div>
    {/each}
  {/if}
{:else if mode === 'record' && creationState.activeTabKey === 'evenements'}
  {#if creationState.events.length === 0}
    <div class="empty">Aucun événement.</div>
  {:else}
    {#each creationState.events as e (e.id)}
      <div class="author-list-item {e.id === creationState.selectedRecordId ? 'active' : ''}" onclick={() => onSelectRecord(e)}>
        <div class="ali-name">{e.title}</div>
        <div class="ali-meta">
          {#if e.location_name}{e.location_name}{:else}<span style="color:var(--muted)">« sans lieu »</span>{/if}
          <span class="badge b-other">{e.type_label || ''}</span>
          <span class="badge b-{e.knowledge_status}">{e.knowledge_status}</span>
        </div>
      </div>
    {/each}
  {/if}
{/if}
