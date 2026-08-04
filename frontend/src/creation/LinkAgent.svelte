<script>
  /* TICKET-0059 (BRIEF-0059-g). Faithful port of the NPC link agent panel
     (index.html, BRIEF-0036-d originally) -- 27 functions across
     index.html:6726-7189, split across this brief's two commits the same
     way linkAgent.svelte.js's own header explains. This commit (1) ports
     the launcher: linkAgentReset, linkAgentCheckOpenBatch,
     linkAgentRenderLauncher, _linkAgentIsChecked, linkAgentToggleLocation,
     _linkAgentPaintLauncher, linkAgentPreviewRoster, linkAgentLaunch.
     `_linkAgentTreeHtml` is deleted, not ported -- LocationTree.svelte
     (BRIEF-0059-f commit 1) replaces it; the checkbox row below is the
     `row` snippet Amendment 1 describes, LocationTree.svelte's SECOND
     consumer and the one that actually exercises the ancestor-inheritance
     predicate npcAgent's radio row never needed.

     Mounted into #linkagent-panel on every 'npc' tab activation
     (CREATION_TABS.npc: loader: null, state.onWorldSwitch: null, the -d
     rule). The container itself stays display:none, toggled by the
     still-legacy linkAgentToggle(), until "Agent liens" is clicked --
     mounting into a display:none ancestor renders fine, nothing here reads
     layout at mount time. linkAgentToggle no longer calls
     linkAgentRenderLauncher() or linkAgentLoadBatch(): this component's own
     boot() effect (below) does the equivalent work on mount/reset instead,
     the npcAgent.svelte/NpcAgent.svelte precedent (BRIEF-0059-f commit 2)
     applied to the second agent. boot()'s open-batch branch is a
     documented no-op until commit 2 wires it to loadBatch() -- the same
     commit-to-commit gap npcAgent.svelte.js's own header records.

     World-switch reset drives off serverState.worldId (replacing the
     legacy linkAgentReset() call _creationRunWorldSwitchResets used to
     make); tab re-entry reset rides 'creation:linkagent-reset', a
     CustomEvent on legacyDoc dispatched by _npcTabEnterReset (index.html)
     in place of its old direct linkAgentReset() call -- the same idiom
     'creation:npcagent-reset' already established.

     The badge (#linkagent-badge, still legacy chrome, outside this
     component's own mount root) is told to show/hide via a component-owned
     CustomEvent on legacyDoc -- Constructeur.svelte's 'creation:refresh-tabs'
     precedent, npcAgent's own 'creation:npcagent-badge' precedent; mount.js
     explicitly stays out of per-island relays like this one (its own header
     comment).

     No scoped <style> block: renders inside the legacy iframe document,
     where Svelte's shell-injected scoped CSS never reaches; markup reuses
     the legacy document's own .linkagent-*, .empty, .spin and .btn-icon
     classes -- LocationTree.svelte's own header comment already
     documents why the .linkagent-loc-node/.linkagent-loc-children rules
     can't move into a component <style> block despite item 8's instruction
     (this brief's commit 2 message reports that finding in full; the
     .linkagent-* block stays in index.html for -l). */
  import { serverState } from '../lib/serverState.svelte.js';
  import LocationTree from './LocationTree.svelte';
  import {
    linkAgentState, resetLinkAgent, checkOpenBatch, initLauncher,
    isCheckedLocation, toggleLocation, previewRoster, launch, reopenExisting,
  } from './linkAgent.svelte.js';

  let { legacyDoc } = $props();

  /** index.html's linkAgentToggle branch ("if open batch, load it; else
   *  render the launcher"), moved to fire on mount/reset instead of on
   *  toggle-click. Commit 2 extends the truthy branch to load the review
   *  surface; until then it is a deliberate no-op (see
   *  linkAgent.svelte.js's header). */
  async function boot() {
    await checkOpenBatch();
    if (!linkAgentState.openBatchId) {
      await initLauncher();
    }
  }

  $effect(() => {
    void serverState.worldId;
    resetLinkAgent();
    boot();
  });

  legacyDoc.addEventListener('creation:linkagent-reset', () => {
    resetLinkAgent();
    boot();
  });

  $effect(() => {
    legacyDoc.dispatchEvent(new CustomEvent('creation:linkagent-badge', {
      detail: { open: !!linkAgentState.openBatchId },
    }));
  });
</script>

{#if linkAgentState.loading}
  <div class="empty"><span class="spin">⟳</span> Chargement…</div>
{:else if linkAgentState.loadError}
  <div class="empty">{linkAgentState.loadError}</div>
{:else}
  <div style="font-weight:600; margin-bottom:6px">Agent liens — sélection des lieux</div>
  <div>
    {#if linkAgentState.locations.length}
      <LocationTree locations={linkAgentState.locations}>
        {#snippet row(loc)}
          <input type="checkbox" checked={isCheckedLocation(loc.id)}
            onchange={(e) => toggleLocation(loc.id, e.currentTarget.checked)}>
        {/snippet}
      </LocationTree>
    {:else}
      <div class="empty">Aucun lieu.</div>
    {/if}
  </div>
  {#if linkAgentState.preview}
    <div style="margin-top:8px">
      {linkAgentState.preview.npcs.length} PNJ, {linkAgentState.preview.pair_count} paires, {linkAgentState.preview.pair_count} appels au modèle<br>
      <span style="color:var(--muted); font-size:11px">{linkAgentState.preview.npcs.map((n) => n.name).join(', ') || '(aucun)'}</span>
    </div>
  {/if}
  <div style="margin-top:10px; display:flex; gap:6px">
    <button class="btn-icon" onclick={previewRoster}>Prévisualiser</button>
    <button class="btn-icon" disabled={!linkAgentState.preview} onclick={launch}>Lancer</button>
  </div>
  <div style="color:var(--red); margin-top:6px">
    {linkAgentState.launchError}
    {#if linkAgentState.launchErrorReopen}
      <button class="btn-icon" onclick={reopenExisting}>Ouvrir le lot existant</button>
    {/if}
  </div>
{/if}
