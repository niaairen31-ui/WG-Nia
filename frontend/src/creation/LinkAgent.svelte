<script>
  /* TICKET-0059 (BRIEF-0059-g). Faithful port of the NPC link agent panel
     (index.html, BRIEF-0036-d originally) -- 27 functions across
     index.html:6726-7189, split across this brief's two commits the same
     way linkAgent.svelte.js's own header explains. This commit (2) ports
     the remainder: linkAgentRunLoop, linkAgentPause, linkAgentRetry,
     linkAgentLoadBatch, _linkAgentNpcName, _linkAgentGroupRows,
     _linkAgentRelationRowHtml/_linkAgentKnowledgeRowHtml/
     _linkAgentNoLinksRowHtml/_linkAgentPairGroupHtml (folded into
     declarative markup below, not ported as functions), linkAgentEditField,
     linkAgentToggleReject, _linkAgentFindingHtml (folded into markup too),
     linkAgentRunCoherence, linkAgentApplyFinding, linkAgentCommit, and
     _linkAgentPaintReview. `_linkAgentTreeHtml` was deleted outright in
     commit 1 -- LocationTree.svelte replaces it; the checkbox row below is
     the `row` snippet Amendment 1 describes, LocationTree.svelte's SECOND
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
     the npcAgent.svelte/NpcAgent.svelte precedent (BRIEF-0059-f) applied to
     the second agent.

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
     comment). The same shape covers graph:invalidate on commit() -- see
     linkAgent.svelte.js's own header for why that dispatch takes legacyDoc
     as a parameter instead of the module importing a bridge accessor.

     No scoped <style> block: renders inside the legacy iframe document,
     where Svelte's shell-injected scoped CSS never reaches; markup reuses
     the legacy document's own .linkagent-*, .empty, .spin and .btn-icon
     classes. Item 8 (move the .linkagent-* block into the Svelte
     components now that both consumers are Svelte) is NOT done by this
     commit -- LocationTree.svelte's own header comment already establishes
     why a Svelte <style> block silently does nothing inside these
     iframe-mounted islands (Graph.svelte's identical constraint, enforced
     by graph_primitive.py rule 8): a `<style>` block placed in
     LocationTree.svelte or here would stop applying the moment index.html's
     copy is deleted, which is exactly the "duplication is the only option"
     escape hatch item 8 names -- except the failure mode here isn't a
     second copy of a shared rule, it's an INERT copy. REPORTING and
     stopping at step 8: the .linkagent-* block (index.html:999-1012) stays
     in index.html, untouched, for -l (when Creation stops living in a
     legacy iframe and a real scoped <style> becomes possible). */
  import { serverState } from '../lib/serverState.svelte.js';
  import LocationTree from './LocationTree.svelte';
  import {
    linkAgentState, resetLinkAgent, checkOpenBatch, initLauncher,
    isCheckedLocation, toggleLocation, previewRoster, launch, reopenExisting,
    loadBatch, runLoop, pause, retry, groupRows, npcName, editField,
    toggleReject, runCoherence, applyFinding, commit,
  } from './linkAgent.svelte.js';

  let { legacyDoc } = $props();

  /** index.html's linkAgentToggle branch ("if open batch, load it; else
   *  render the launcher"), moved to fire on mount/reset instead of on
   *  toggle-click. */
  async function boot() {
    await checkOpenBatch();
    if (linkAgentState.openBatchId) {
      await loadBatch(linkAgentState.openBatchId);
    } else {
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
{:else if linkAgentState.batch}
  {@const b = linkAgentState.batch}
  {@const isOpen = b.status === 'open'}
  {@const groups = groupRows(linkAgentState.rows)}
  {@const findings = b.coherence_findings || []}
  {@const canCommit = isOpen && (b.coherence_status === 'ran' || b.coherence_status === 'partial')}
  <div style="font-weight:600; margin-bottom:6px">Agent liens — lot {b.id.slice(0, 8)}</div>
  {#if isOpen}
    <div>paire {b.pairs_done}/{b.pairs_total}
      {#if linkAgentState.loopRunning}
        <button class="btn-icon" onclick={pause}>Pause</button>
      {:else if b.pairs_done < b.pairs_total}
        <button class="btn-icon" onclick={runLoop}>Reprendre</button>
      {/if}
    </div>
    {#if linkAgentState.failedPair}
      <div style="color:var(--red)">Échec : {linkAgentState.failedPair.message}
        <button class="btn-icon" onclick={retry}>Réessayer</button></div>
    {/if}
  {:else}
    <div style="color:var(--muted)">Lot {b.status}.</div>
  {/if}
  <div style="margin-top:10px">
    {#if groups.length}
      {#each groups as [key, rows] (key)}
        {@const [aId, bId] = key.split('::')}
        <div class="linkagent-pair-group">
          <div style="font-weight:600; font-size:12px">{npcName(aId)} — {npcName(bId)}</div>
          {#each rows as row (row.id)}
            {@const rejected = row.row_status === 'rejected'}
            {#if row.kind === 'relation'}
              {@const p = row.payload}
              <div class="linkagent-row {rejected ? 'rejected' : ''}">
                <span class="badge b-other">relation</span>
                <input type="text" placeholder="type" style="width:110px" value={p.type || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'type', e.currentTarget.value)}>
                <select disabled={rejected} onchange={(e) => editField(row.id, 'direction', e.currentTarget.value)}>
                  <option value="mutual" selected={p.direction === 'mutual'}>mutual</option>
                  <option value="a_to_b" selected={p.direction === 'a_to_b'}>a_to_b</option>
                  <option value="b_to_a" selected={p.direction === 'b_to_a'}>b_to_a</option>
                </select>
                <input type="number" min="1" max="100" style="width:52px" value={p.value} disabled={rejected}
                  onchange={(e) => editField(row.id, 'value', Number(e.currentTarget.value))}>
                <label style="font-size:11px"><input type="checkbox" checked={p.visible_to_b} disabled={rejected}
                  onchange={(e) => editField(row.id, 'visible_to_b', e.currentTarget.checked)}> visible à B</label>
                <input type="text" placeholder="notes" style="flex:1; min-width:100px" value={p.notes || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'notes', e.currentTarget.value)}>
                <button class="btn-icon" onclick={() => toggleReject(row.id, rejected)}>{rejected ? 'Rétablir' : 'Rejeter'}</button>
              </div>
            {:else if row.kind === 'knowledge'}
              {@const p = row.payload}
              {@const aboutId = (p.subject || '').replace(/^npc:/, '')}
              <div class="linkagent-row {rejected ? 'rejected' : ''}">
                <span class="badge b-other">knowledge</span>
                <span style="font-size:11px; color:var(--muted)">{npcName(p.entity_id)} à propos de {npcName(aboutId)}</span>
                <input type="text" placeholder="niveau" style="width:110px" value={p.level || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'level', e.currentTarget.value)}>
                <input type="text" placeholder="contenu" style="flex:1; min-width:120px" value={p.content || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'content', e.currentTarget.value)}>
                <input type="text" placeholder="source" style="width:100px" value={p.source || ''} disabled={rejected}
                  onchange={(e) => editField(row.id, 'source', e.currentTarget.value)}>
                <input type="number" min="1" max="100" style="width:52px" title="share_threshold" value={p.share_threshold} disabled={rejected}
                  onchange={(e) => editField(row.id, 'share_threshold', Number(e.currentTarget.value))}>
                <label style="font-size:11px"><input type="checkbox" checked={p.is_incorrect} disabled={rejected}
                  onchange={(e) => editField(row.id, 'is_incorrect', e.currentTarget.checked)}> incorrect</label>
                <label style="font-size:11px"><input type="checkbox" checked={p.is_secret} disabled={rejected}
                  onchange={(e) => editField(row.id, 'is_secret', e.currentTarget.checked)}> secret</label>
                <button class="btn-icon" onclick={() => toggleReject(row.id, rejected)}>{rejected ? 'Rétablir' : 'Rejeter'}</button>
              </div>
            {:else}
              <div class="linkagent-row {rejected ? 'rejected' : ''}" style="color:var(--muted); font-style:italic">
                Aucun lien proposé
                <button class="btn-icon" onclick={() => toggleReject(row.id, rejected)}>{rejected ? 'Rétablir' : 'Rejeter'}</button>
              </div>
            {/if}
          {/each}
        </div>
      {/each}
    {:else}
      <div class="empty">Aucune paire traitée pour l'instant.</div>
    {/if}
  </div>
  <div style="margin-top:14px; font-weight:600">Passe de cohérence
    {#if isOpen}<button class="btn-icon" onclick={runCoherence}>Lancer</button>{/if}
  </div>
  {#if b.coherence_status === 'partial'}
    <div class="linkagent-warn-banner">Graphe canon tronqué — passe partielle</div>
  {/if}
  <div>
    {#if findings.length}
      {#each findings as finding, i}
        {@const rejected = finding.validation === 'rejected'}
        {@const applied = !!finding.applied_at}
        {@const targetTxt = finding.target ? `${finding.target.scope}:${(finding.target.id || '').slice(0, 8)}` : ''}
        {@const canonBadge = finding.target && finding.target.scope === 'canon' && applied}
        <div class="linkagent-finding {rejected ? 'finding-rejected' : ''}">
          <div><span class="badge b-other">{finding.source}</span> <span style="font-size:11px; color:var(--muted)">{targetTxt}</span>
            {#if applied}<span class="badge b-applied">appliqué</span>{/if}
            {#if canonBadge}<span class="badge b-approved">canon modifié</span>{/if}</div>
          <div style="margin-top:4px">{finding.problem || ''}</div>
          {#if finding.rationale}<div style="color:var(--muted); font-size:11px; margin-top:2px">{finding.rationale}</div>{/if}
          {#if rejected}<div style="color:var(--red); font-size:11px; margin-top:4px">rejeté : {finding.validation_reason || ''}</div>{/if}
          {#if finding.validation === 'valid' && finding.patch != null && !applied}
            <button class="btn-icon" style="margin-top:6px" onclick={() => applyFinding(i)}>Appliquer</button>
          {/if}
        </div>
      {/each}
    {:else}
      <div class="empty">Aucun résultat de cohérence pour l'instant.</div>
    {/if}
  </div>
  <div style="margin-top:14px">
    <button class="btn-icon" disabled={!canCommit} onclick={() => commit(legacyDoc)}>Committer le lot</button>
  </div>
  <div style="margin-top:8px">{linkAgentState.commitResult || ''}</div>
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
