<script>
  /* TICKET-0059 (BRIEF-0059-f). Faithful port of the NPC group agent panel
     (index.html, BRIEF-0037-c originally) -- 29 functions across
     index.html:6688-7164, split across this brief's commits 2-3 the same
     way npcAgent.svelte.js's own header explains. This commit (2) ports
     the launcher: npcAgentReset, npcAgentCheckOpenBatch,
     npcAgentRenderLauncher, npcAgentSelectRoot, npcAgentPreviewRoot,
     npcAgentAddLine, npcAgentRemoveLine, npcAgentEditLine,
     _npcAgentLineTotal, _npcAgentLineRowHtml, _npcAgentPaintLauncher,
     npcAgentLaunch. `_npcAgentTreeHtml` is deleted, not ported --
     LocationTree.svelte (commit 1) replaces it; the radio row below is the
     `row` snippet Amendment 1/this brief's narrowing describes.

     Mounted into #npcagent-panel on every 'npc' tab activation
     (CREATION_TABS.npc: loader: null, state.onWorldSwitch: null, the -d
     rule). The container itself stays display:none, toggled by the
     still-legacy npcAgentToggle(), until "Agent PNJ" is clicked --
     mounting into a display:none ancestor renders fine, nothing here reads
     layout at mount time. npcAgentToggle no longer calls
     npcAgentRenderLauncher(): this component's own boot() effect (below)
     does the equivalent work unconditionally on mount, so the panel is
     ready the instant it's shown rather than only after the first toggle.

     World-switch reset drives off serverState.worldId (replacing the
     legacy npcAgentReset() call the deleted _npcWorldReset/
     _creationRunWorldSwitchResets pairing used to make); tab re-entry reset
     rides 'creation:npcagent-reset', a CustomEvent on legacyDoc dispatched
     by _npcTabEnterReset (index.html) in place of its old direct
     npcAgentReset() call -- the same idiom RoomBatch.svelte's
     'creation:batch-reset' already established for an identical situation.

     The badge (#npcagent-badge, still legacy chrome, outside this
     component's own mount root) is told to show/hide via a component-owned
     CustomEvent on legacyDoc -- Constructeur.svelte's 'creation:refresh-tabs'
     precedent; mount.js explicitly stays out of per-island relays like this
     one (its own header comment).

     No scoped <style> block: renders inside the legacy iframe document,
     where Svelte's shell-injected scoped CSS never reaches; markup reuses
     the legacy document's own .linkagent-*, .empty, .spin and .btn-icon
     classes (the .linkagent-* block is shared with linkAgent, still legacy
     -- that CSS moves at -g or -l, per this brief's Scope OUT). */
  import { serverState } from '../lib/serverState.svelte.js';
  import LocationTree from './LocationTree.svelte';
  import {
    npcAgentState, resetNpcAgent, checkOpenBatch, initLauncher,
    selectRoot, previewRoot, addLine, removeLine, editLine, lineTotal,
    launch, reopenExisting,
  } from './npcAgent.svelte.js';

  let { legacyDoc } = $props();

  /** index.html's npcAgentToggle branch ("if open batch, load it; else
   *  render the launcher"), moved to fire on mount/reset instead of on
   *  toggle-click (item 5's rule). Commit 3 extends the truthy branch to
   *  load the review surface; until then it is a deliberate no-op (see
   *  npcAgent.svelte.js's header). */
  async function boot() {
    await checkOpenBatch();
    if (!npcAgentState.openBatchId) {
      await initLauncher();
    }
  }

  $effect(() => {
    void serverState.worldId;
    resetNpcAgent();
    boot();
  });

  legacyDoc.addEventListener('creation:npcagent-reset', () => {
    resetNpcAgent();
    boot();
  });

  $effect(() => {
    legacyDoc.dispatchEvent(new CustomEvent('creation:npcagent-badge', {
      detail: { open: !!npcAgentState.openBatchId },
    }));
  });

  const total = $derived(lineTotal(npcAgentState.lines));
</script>

{#if npcAgentState.loading}
  <div class="empty"><span class="spin">⟳</span> Chargement des lieux…</div>
{:else if npcAgentState.loadError}
  <div class="empty">{npcAgentState.loadError}</div>
{:else}
  <div style="font-weight:600; margin-bottom:6px">Agent PNJ — sélection de la racine</div>
  <div>
    {#if npcAgentState.locations.length}
      <LocationTree locations={npcAgentState.locations}>
        {#snippet row(loc)}
          <input type="radio" name="npcagent-root" checked={npcAgentState.selectedRoot === loc.id}
            onchange={() => selectRoot(loc.id)}>
        {/snippet}
      </LocationTree>
    {:else}
      <div class="empty">Aucun lieu.</div>
    {/if}
  </div>
  {#if npcAgentState.preview}
    <div style="margin-top:8px; font-size:11px; color:var(--muted)">
      {npcAgentState.preview.locations.length} lieu(x), {npcAgentState.preview.factions.length} faction(s) dans la zone
    </div>
  {/if}
  <div style="margin-top:10px">
    <button class="btn-icon" disabled={!npcAgentState.selectedRoot} onclick={previewRoot}>Prévisualiser</button>
  </div>
  <div style="margin-top:10px; font-weight:600">Brief du groupe</div>
  <textarea rows="2" style="width:100%; resize:vertical" value={npcAgentState.groupBrief}
    oninput={(e) => { npcAgentState.groupBrief = e.currentTarget.value; }}></textarea>
  <div style="margin-top:8px">
    {#if npcAgentState.preview}
      {#each npcAgentState.lines as line, i}
        <div class="linkagent-row">
          <input type="number" min="1" style="width:52px" value={line.count}
            onchange={(e) => editLine(i, 'count', Number(e.currentTarget.value))}>
          <input type="text" placeholder="description" style="flex:1; min-width:140px" value={line.description || ''}
            onchange={(e) => editLine(i, 'description', e.currentTarget.value)}>
          <select onchange={(e) => editLine(i, 'faction_id', e.currentTarget.value || null)}>
            <option value="">(aucune)</option>
            {#each npcAgentState.preview.factions as f (f.id)}
              <option value={f.id} selected={line.faction_id === f.id}>{f.name}</option>
            {/each}
          </select>
          <select onchange={(e) => editLine(i, 'location_id', e.currentTarget.value || null)}>
            <option value="">(modèle)</option>
            {#each npcAgentState.preview.locations as l (l.id)}
              <option value={l.id} selected={line.location_id === l.id}>{l.name}</option>
            {/each}
          </select>
          <button class="btn-icon" onclick={() => removeLine(i)}>Retirer</button>
        </div>
      {/each}
    {:else}
      <div class="empty">Sélectionnez une racine puis prévisualisez pour éditer les lignes.</div>
    {/if}
  </div>
  {#if npcAgentState.preview}
    <button class="btn-icon" onclick={addLine}>+ Ligne</button>
  {/if}
  <div style="margin-top:8px">Total : {total} PNJ</div>
  <div style="margin-top:10px">
    <button class="btn-icon" disabled={!npcAgentState.preview} onclick={launch}>Lancer</button>
  </div>
  <div style="color:var(--red); margin-top:6px">
    {npcAgentState.launchError}
    {#if npcAgentState.launchErrorReopen}
      <button class="btn-icon" onclick={reopenExisting}>Ouvrir le lot existant</button>
    {/if}
  </div>
{/if}
