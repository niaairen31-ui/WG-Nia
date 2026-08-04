<script>
  /* TICKET-0059 (BRIEF-0059-f). Faithful port of the NPC group agent panel
     (index.html, BRIEF-0037-c originally) -- 29 functions across
     index.html:6688-7164, split across this brief's commits 2-3 the same
     way npcAgent.svelte.js's own header explains. Commit 2 ported the
     launcher (npcAgentReset through npcAgentLaunch). This commit (3) ports
     the run loop and review surface: npcAgentRunOne, npcAgentRunLoop,
     npcAgentPause, npcAgentRetryRun, npcAgentLoadBatch, npcAgentEditField,
     npcAgentToggleReject, npcAgentCommit, npcAgentAbandon,
     npcAgentGenerateLinks, plus the underscore-prefixed painters/helpers
     (_npcAgentRefreshRows, _npcAgentGroupRows, _npcAgentRowHtml,
     _npcAgentGroupHtml, _npcAgentPaintReview) -- the four HTML-building ones
     among them are not ported as functions at all; the markup below
     replaces what they used to paint. npcAgentToggle is the one function in
     the original range that stays legacy (chrome).

     Mounted into #npcagent-panel on every 'npc' tab activation
     (CREATION_TABS.npc: loader: null, state.onWorldSwitch: null, the -d
     rule). The container itself stays display:none, toggled by the
     still-legacy npcAgentToggle(), until "Agent PNJ" is clicked --
     mounting into a display:none ancestor renders fine, nothing here reads
     layout at mount time. boot() below now reproduces the original
     npcAgentToggle's "if open batch, load it; else render the launcher"
     branch in full, firing on mount/reset instead of on toggle-click
     (item 5's rule) -- commit 2 left the truthy branch as a documented
     no-op; this commit wires it to loadBatch.

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
    launch, reopenExisting, loadBatch, runOne, runLoop, pause, retryRun,
    groupRows, groupDescription, editField, toggleReject, commit, abandon,
    generateLinks,
  } from './npcAgent.svelte.js';

  let { legacyDoc } = $props();

  async function boot() {
    await checkOpenBatch();
    if (npcAgentState.openBatchId) {
      await loadBatch(npcAgentState.openBatchId);
    } else {
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
  const groups = $derived(groupRows(npcAgentState.rows));
</script>

{#if npcAgentState.loading}
  <div class="empty"><span class="spin">⟳</span> Chargement…</div>
{:else if npcAgentState.loadError}
  <div class="empty">{npcAgentState.loadError}</div>
{:else if npcAgentState.batch}
  {@const b = npcAgentState.batch}
  {@const isOpen = b.status === 'open'}
  {@const canCommit = isOpen && b.npcs_done === b.npcs_total}
  <div style="font-weight:600; margin-bottom:6px">Agent PNJ — lot {b.id.slice(0, 8)}</div>
  {#if isOpen}
    <div>PNJ {b.npcs_done}/{b.npcs_total}
      <button class="btn-icon" disabled={b.npcs_done >= b.npcs_total} onclick={runOne}>Suivant</button>
      {#if npcAgentState.loopRunning}
        <button class="btn-icon" onclick={pause}>Pause</button>
      {:else if b.npcs_done < b.npcs_total}
        <button class="btn-icon" onclick={runLoop}>Tout générer</button>
      {/if}
    </div>
    {#if npcAgentState.failedRun}
      <div style="color:var(--red)">Échec : {npcAgentState.failedRun.message}
        <button class="btn-icon" onclick={retryRun}>Réessayer</button></div>
    {/if}
  {:else}
    <div style="color:var(--muted)">Lot {b.status}.</div>
  {/if}
  <div style="margin-top:10px">
    {#if groups.length}
      {#each groups as [lineIndex, rows] (lineIndex)}
        <div class="linkagent-pair-group">
          <div style="font-weight:600; font-size:12px">{groupDescription(b, lineIndex)}</div>
          {#each rows as row (row.id)}
            {@const pub = (row.payload.draft && row.payload.draft.public) || {}}
            {@const goals = row.payload.goals || {}}
            {@const notes = row.payload.notes || []}
            {@const rejected = row.row_status === 'rejected'}
            <div class="linkagent-row {rejected ? 'rejected' : ''}" style="flex-direction:column; align-items:stretch">
              <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center">
                <input type="text" style="width:140px" value={pub.name || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'name', e.currentTarget.value)}>
                <input type="text" placeholder="description" style="flex:1; min-width:140px" value={pub.description || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'description', e.currentTarget.value)}>
                <input type="number" min="-1" max="2" title="physical_tier" style="width:52px" value={pub.physical_tier ?? ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'physical_tier', Number(e.currentTarget.value))}>
                <select disabled={rejected} onchange={(e) => editField(row.id, 'faction_id', e.currentTarget.value || null)}>
                  <option value="">(aucune)</option>
                  {#each (npcAgentState.preview ? npcAgentState.preview.factions : []) as f (f.id)}
                    <option value={f.id} selected={pub.faction_id === f.id}>{f.name}</option>
                  {/each}
                </select>
                <select disabled={rejected} onchange={(e) => editField(row.id, 'location_id', e.currentTarget.value || null)}>
                  {#each (npcAgentState.preview ? npcAgentState.preview.locations : []) as l (l.id)}
                    <option value={l.id} selected={row.payload.location_id === l.id}>{l.name}</option>
                  {/each}
                </select>
                <button class="btn-icon" onclick={() => toggleReject(row.id, rejected)}>{rejected ? 'Rétablir' : 'Rejeter'}</button>
              </div>
              <div style="display:flex; gap:6px; margin-top:4px">
                <input type="text" placeholder="objectif long" style="flex:1" value={goals.long || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'goals.long', e.currentTarget.value)}>
                <input type="text" placeholder="objectifs courts (séparés par ;)" style="flex:1" value={(goals.shorts || []).join('; ')} disabled={rejected}
                  onchange={(e) => editField(row.id, 'goals.shorts', e.currentTarget.value.split(';').map((s) => s.trim()).filter(Boolean))}>
              </div>
              {#if notes.length}
                <div style="color:var(--muted); font-size:11px; margin-top:2px">{notes.join(' · ')}</div>
              {/if}
            </div>
          {/each}
        </div>
      {/each}
    {:else}
      <div class="empty">Aucun PNJ généré pour l'instant.</div>
    {/if}
  </div>
  <div style="margin-top:14px; display:flex; gap:6px; align-items:center">
    <button class="btn-icon" disabled={!canCommit} onclick={commit}>Committer le lot</button>
    {#if isOpen}
      <button class="btn-icon" onclick={abandon}>Abandonner</button>
    {/if}
  </div>
  <div style="margin-top:8px">{npcAgentState.commitResult || ''}</div>
  {#if b.status === 'committed'}
    <div style="margin-top:8px">
      <button class="btn-icon" onclick={generateLinks}>Générer les liens pour ce groupe</button>
    </div>
    {#if npcAgentState.linkHandoffMsg}
      <div class="linkagent-warn-banner">{npcAgentState.linkHandoffMsg}</div>
    {/if}
  {/if}
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
