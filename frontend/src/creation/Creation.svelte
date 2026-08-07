<script>
  /* TICKET-0059 (BRIEF-0059-l, D1). Creation's own shell -- the chrome
     inversion. App.svelte drives this component directly now (item 2);
     Creation no longer lives inside the legacy iframe, so this is a
     REAL scoped Svelte component: real event bindings, real reactive
     `style:display`, not the innerHTML/onclick-attribute string-building
     the legacy chrome needed to reach across a document boundary.

     All of the LOGIC lives in tabs.js (registry, tab-switch dispatcher,
     on-demand slots, navigation, pending creations, the world-switch
     cascade) -- this file is template plus the two trivial NPC-panel
     toggles it owns directly (npcAgentToggle/linkAgentToggle, moved here
     in Commit 1 rather than the brief's originally-scheduled Commit 4:
     see tooling/standards/ARCHITECTURE_DECISIONS.md, "the legacyContainer
     exposure" -- their #npcagent-panel/#linkagent-panel markup is forced
     to move the moment this component's containers do, and
     npcAgent.svelte.js's generateLinks() already reached into
     #linkagent-panel through the legacy bridge, which breaks the instant
     that markup leaves the legacy document).

     Every container div below keeps its original id -- mount.js resolves
     islands via document.getElementById against THIS document now,
     shared.css/creation.css (TICKET-0063) style them exactly as they were
     styled inside the legacy iframe, and creation_island.py's rule 4
     confirms every declared containerId still resolves. */
  import { onMount } from 'svelte';
  import { creationState } from './state.svelte.js';
  import {
    CREATION_TABS, creationInit, showCreationSubTab, creationRefreshList,
    containerVisible, onDemandSlotToggle, creationReturnToOrigin,
    creationSaveDispatch, loadPendingCreations, generatePendingCreation,
    initCreationChrome, setMountActions,
  } from './tabs.js';
  import { triggerPrimaryAction, activateIsland } from './mount.js';

  // Wires tabs.js's two mount.js dependencies once, at module-instance
  // init (this component is instantiated exactly once, always-mounted) --
  // see tabs.js's own header comment for why this is a setter instead of a
  // static top-level import (it would cycle back through every island
  // component that imports navigation functions from tabs.js).
  setMountActions({ triggerPrimaryAction, activateIsland });

  /* Always mounted (never destroyed -- islands would lose their state on
     every surface switch otherwise); `active` only toggles this root's own
     visibility. App.svelte hides LegacyFrame's iframe the same way for the
     surfaces this component now owns. */
  let { active = false } = $props();

  let tabEntries = $derived.by(() => {
    creationState.tabsVersion; // dependency touch: CREATION_TABS is a
    // plain mutable object this $derived cannot see into on its own.
    return Object.entries(CREATION_TABS);
  });
  let activeEntry = $derived(CREATION_TABS[creationState.activeTabKey] ?? null);
  let onDemandSlots = $derived((activeEntry?.slots ?? []).filter(s => s.display === 'on_demand'));

  let returnLabel = $derived.by(() => {
    const back = creationState.creationReturnTo;
    if (!back) return null;
    const origin = creationState.entities.find(e => e.id === back.entityId);
    return origin ? origin.name : (CREATION_TABS[back.tabId]?.label || '');
  });

  // TICKET-0059 (BRIEF-0059-l): always mounted from app boot, not lazily on
  // first visit. initCreationChrome has no legacy dependency, safe here;
  // the one listener that DOES need the legacy document
  // ('creation:world-changed') is wired separately from App.svelte's
  // onLegacyReady, the hook that actually waits for the iframe's own
  // `load` event -- this component mounts as soon as App.svelte renders,
  // independent of that timing.
  onMount(() => {
    initCreationChrome();
    creationInit();
  });
</script>

<div class="app-view" id="creation-view" style:display={active ? '' : 'none'}>

  <!-- ── Sub-tab bar ── -->
  <div class="creation-sub-tab-bar">
    {#each tabEntries as [key, entry] (key)}
      <button
        class="creation-sub-tab"
        class:active={key === creationState.activeTabKey}
        id={'ctab-' + key}
        onclick={() => showCreationSubTab(key)}
      >{entry.label}</button>
    {/each}
  </div>

  <!-- ── Standard shell band (BRIEF-0005-c) -- one header band above every
       Création page: the entry's label (title) plus, iff it declares a
       primaryAction, exactly one button in this same fixed position on
       every tab. #creation-shell-extra/#creation-shell-batch-bar are
       Review Queue's mount points (a one-off relocation, not a generic
       shell concept); both are declared slots on CREATION_TABS.queue so
       containerVisible covers them the same way as any other slot. -->
  <div class="panel-head" id="creation-shell-band">
    <h2 id="creation-shell-title">{activeEntry?.label ?? ''}</h2>
    <div id="creation-shell-extra" style:display={containerVisible('creation-shell-extra') ? '' : 'none'}></div>
    <div id="creation-shell-batch-bar" style:display={containerVisible('creation-shell-batch-bar') ? '' : 'none'}></div>
    <!-- On-demand slot toggles (BRIEF-0023-a, F1) -- one button per slot
         the active entry declares display:'on_demand'; same fixed shell
         position on every tab, mirroring primaryAction. -->
    <div id="creation-shell-toggles" style="display:flex; gap:8px;">
      {#each onDemandSlots as slot (slot.containerId)}
        <button class="btn-icon" onclick={() => onDemandSlotToggle(slot)}>
          {creationState.onDemandSlotState[slot.containerId]?.open ? 'Masquer le graphe' : (slot.toggleLabel || 'Voir le graphe')}
        </button>
      {/each}
    </div>
    {#if activeEntry?.primaryAction}
      <button class="btn-send" id="creation-shell-action" onclick={activeEntry.primaryAction.handler}>{activeEntry.primaryAction.label}</button>
    {/if}
  </div>

  <!-- TICKET-0057: mount point for the graph primitive (island rendered by
       the shell). Empty by construction -- chrome, canvas and help text
       all belong to Graph.svelte and its Lieux consumer. -->
  <div id="creation-lieux-graph" style:display={containerVisible('creation-lieux-graph') ? '' : 'none'}></div>

  <!-- ── Lieux -- Room batch generator panel (TICKET-0042). Empty by
       construction -- the whole panel belongs to
       frontend/src/creation/RoomBatch.svelte, mounted here as the `batch`
       island; this wrapper only participates in containerVisible's
       show/hide so it disappears when leaving the Lieux tab. ── -->
  <div id="batch-panel-wrap" style:display={containerVisible('batch-panel-wrap') ? '' : 'none'}></div>

  <!-- ── NPC -- Relation ego/global graph panel (BRIEF-0023-b, BRIEF-0033-e).
       The graph's own chrome (mode/Lier/buckets/canvas/info-card) is
       entirely shell-rendered into #relgraph-mount by the relations
       consumer; this outer container keeps only what survives the graph's
       mount/remount cycle byte-untouched: the Agent PNJ/liens launchers
       and their panels. ── -->
  <div id="creation-npc-relgraph" style:display={containerVisible('creation-npc-relgraph') ? '' : 'none'}>
    <div class="lieux-graph-head">
      <span>Panneaux NPC</span>
      <button class="btn-icon" id="npcagent-launcher-btn" onclick={() => creationState.npcAgentOpen = !creationState.npcAgentOpen}>
        Agent PNJ<span id="npcagent-badge" style:display={creationState.npcAgentBadgeOpen ? '' : 'none'}>●</span>
      </button>
      <button class="btn-icon" id="linkagent-launcher-btn" onclick={() => creationState.linkAgentOpen = !creationState.linkAgentOpen}>
        Agent liens<span id="linkagent-badge" style:display={creationState.linkAgentBadgeOpen ? '' : 'none'}>●</span>
      </button>
    </div>
    <!-- ── NPC group agent panel (BRIEF-0037-c) -- content rendered by the
         frontend/src/creation/NpcAgent.svelte island; empty/hidden until
         "Agent PNJ" is clicked ── -->
    <div id="npcagent-panel" style:display={creationState.npcAgentOpen ? '' : 'none'} style="border-bottom:1px solid var(--border); padding:10px 14px; max-height:460px; overflow-y:auto"></div>
    <!-- ── NPC link agent panel (BRIEF-0036-d) -- content rendered by the
         frontend/src/creation/LinkAgent.svelte island; empty/hidden until
         "Agent liens" is clicked ── -->
    <div id="linkagent-panel" style:display={creationState.linkAgentOpen ? '' : 'none'} style="border-bottom:1px solid var(--border); padding:10px 14px; max-height:460px; overflow-y:auto"></div>
    <!-- ── The graph island's own mount point (TICKET-0057) -- empty by
         construction; chrome, canvas, info-card and edge panel all belong
         to Graph.svelte and its relations consumer. ── -->
    <div id="relgraph-mount"></div>
  </div>

  <!-- ── Entity editor (NPC / PJ / Lieux / Factions / Objets) ── -->
  <div class="layout" id="creation-editor-area" style:display={containerVisible('creation-editor-area') ? '' : 'none'}>
    <aside class="sidebar">
      <div class="sidebar-head">
        <span id="creation-list-label">{activeEntry?.containers?.includes('creation-editor-area') ? (activeEntry.label ?? '') : ''}</span>
        <button class="btn-icon" onclick={() => creationRefreshList()} title="Rafraîchir">↻</button>
      </div>
      <!-- The entityList island's mount point. Empty by construction --
           Svelte mount() appends, it never clears a target's pre-existing
           children, so a static placeholder here would sit beside the
           island's own DOM forever. The island renders its own loading
           state. -->
      <div class="conv-list" id="author-entity-list"></div>
    </aside>

    <div class="right-col">
      <!-- Créations en attente (BRIEF-0019-a) -- approved entity_creation
           germs awaiting on-demand sheet generation; shown only for entity
           tabs whose registry entry sets showPendingCreations. -->
      <div id="creation-pending-strip" style:display={activeEntry?.showPendingCreations ? '' : 'none'} style="border-bottom:2px solid var(--border)">
        <div class="panel-head" style="flex-shrink:0">
          <h2 style="font-size:12px">Créations en attente</h2>
          <button class="btn-icon" onclick={() => loadPendingCreations()} title="Rafraîchir">↻</button>
        </div>
        <div id="creation-pending-list" class="conv-list" style="max-height:180px; overflow-y:auto">
          {#if creationState.pendingCreationsLoading}
            <div class="empty"><span class="spin">⟳</span></div>
          {:else if creationState.pendingCreationsError}
            <div class="empty" style="color:var(--red)">Erreur : {creationState.pendingCreationsError}</div>
          {:else if creationState.pendingCreations.length === 0}
            <div class="empty">Aucune création en attente.</div>
          {:else}
            {#each creationState.pendingCreations as item (item.mutation_id)}
              <div class="row-card">
                <div style="display:flex; justify-content:space-between; align-items:baseline; gap:8px">
                  <strong>{item.name || '(sans nom)'}</strong>
                  <span class="badge b-other" style="font-size:10px">{item.source === 'tick' ? 'TICK' : 'CONVERSATION'}</span>
                </div>
                {#if item.concept}<div style="font-size:12px; color:var(--muted)">{item.concept}</div>{/if}
                {#if !item.entity_type}<span class="badge b-other" style="font-size:10px; border-color:var(--red); color:var(--red)">type inconnu</span>{/if}
                <div class="row-card-actions">
                  {#if item.entity_type}
                    <button class="btn-send" onclick={() => generatePendingCreation(item.mutation_id)}>Générer la fiche</button>
                  {/if}
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </div>

      <div class="transcript-panel" style="border-bottom:none">
        <div class="panel-head">
          <h2 id="author-sheet-title">Sélectionner une entité</h2>
          <button class="btn-ghost" id="author-return-btn" onclick={() => creationReturnToOrigin()}
                  style:display={returnLabel ? '' : 'none'} title="Retour à l'entité d'origine">{returnLabel ? '← ' + returnLabel : ''}</button>
          <span class="author-status" id="author-status"></span>
          <button class="btn-send" id="author-save-btn" onclick={() => creationSaveDispatch()} style="display:none">Save</button>
        </div>
        <!-- The entitySheet island's mount point. Empty by construction --
             Sheet.svelte renders its own empty/loading/view state. -->
        <div class="author-main" id="author-main"></div>
      </div>

      <!-- PJ Fiche -- a declared slot on the pj registry entry
           (BRIEF-0005-b), rendered by default on tab activation, outside
           the create gate. Empty by construction, same as every other
           island's container. -->
      <div id="creation-pj-skill" style:display={containerVisible('creation-pj-skill') ? '' : 'none'}></div>
    </div><!-- .right-col -->
  </div><!-- #creation-editor-area -->

  <!-- ── Artefacts sub-tab -- Svelte island: read-only list, empty by
       construction ── -->
  <div id="creation-artefacts" style:display={containerVisible('creation-artefacts') ? '' : 'none'}></div>

  <!-- ── Compétences sub-tab -- Svelte island: empty by construction ── -->
  <div id="creation-competences" style:display={containerVisible('creation-competences') ? '' : 'none'}></div>

  <!-- ── Région sub-tab -- Svelte island: generation + review + atomic
       commit ── -->
  <div id="creation-region" style:display={containerVisible('creation-region') ? '' : 'none'}></div>

  <!-- ── Constructeur sub-tab -- runtime entity-type creation: name/slug +
       checkable-trait palette, server-sourced ── -->
  <div id="creation-constructeur" style:display={containerVisible('creation-constructeur') ? '' : 'none'}></div>

  <!-- ── Registre sub-tab -- Svelte island: empty by construction ── -->
  <div id="creation-registre" style:display={containerVisible('creation-registre') ? '' : 'none'}></div>

  <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
  <div id="creation-queue" style:display={containerVisible('creation-queue') ? '' : 'none'}></div>

  <!-- ── Prompts sub-tab -- Svelte island: prompt management + the parked
       D-0050 conversation-window config panel ── -->
  <div id="creation-prompts" style:display={containerVisible('creation-prompts') ? '' : 'none'}></div>

</div><!-- #creation-view -->
