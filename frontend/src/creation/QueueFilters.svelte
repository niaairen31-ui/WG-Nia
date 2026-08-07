<script>
  /* TICKET-0059 (BRIEF-0059-k commit 1). Faithful port of the Review
     Queue's filter bar (setFilter/setFilterByName) and the world-tick
     controls (loadTickControls/tickScopeTypeChanged/runWorldTick,
     index.html, now deleted) -- both rendered into the same
     #creation-shell-extra slot in the legacy markup (BRIEF-0005-c), so
     both port together as one island. currentFilter lives in
     queue.svelte.js (queueState), not here -- Queue.svelte reads the same
     store from its own, separate mount point (#creation-queue).

     World reset is driven by serverState.worldId (the -d rule every
     migrated island follows) -- since the slot's own loader is null now,
     this effect does the initial load too, replacing the legacy
     loader/onWorldSwitch pair. The three scope selects
     (npcs/location/faction) stay always-rendered and CSS-hidden rather
     than conditionally destroyed, preserving the original's own
     behaviour of keeping each select's selection alive across a scope-type
     switch.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document; markup reuses index.html's
     own .f-btn/.tick-controls classes verbatim. */
  import { serverState } from '../lib/serverState.svelte.js';
  import { queueState, setFilter } from './queue.svelte.js';

  const FILTERS = [
    { status: 'proposed', label: 'Proposed' },
    { status: 'approved', label: '⚠ Needs attention', title: 'Proposals that were approved but could not be applied to canon (apply error, unhandled type, or duplicate block). Needs creator attention.' },
    { status: 'applied', label: 'Applied' },
    { status: 'rejected', label: 'Rejected' },
  ];

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  let npcs = $state([]);
  let locations = $state([]);
  let factions = $state([]);

  let scopeType = $state('npcs');
  let scopeNpcIds = $state([]);
  let scopeLocationId = $state('');
  let scopeFactionId = $state('');
  let interval = $state('quelques heures');

  let tickRunning = $state(false);
  let tickStatus = $state('');
  let tickStatusColor = $state('var(--muted)');

  async function loadTickTargets() {
    try {
      const [entities, pcs, locs, facs] = await Promise.all([
        api('/api/entities?type=character'),
        api('/api/skills/player-characters').catch(() => []),
        api('/api/locations').catch(() => []),
        api('/api/entities?type=faction').catch(() => []),
      ]);
      const pcIds = new Set(pcs.map((p) => p.id));
      npcs = entities.filter((e) => e.type === 'character' && !pcIds.has(e.id));
      locations = locs;
      factions = facs;
    } catch (e) {
      tickStatusColor = 'var(--red)';
      tickStatus = 'Erreur de chargement des cibles : ' + e.message;
    }
  }

  async function runWorldTick() {
    const body = { scope_type: scopeType, interval };
    if (scopeType === 'npcs') {
      if (!scopeNpcIds.length) {
        tickStatusColor = 'var(--red)';
        tickStatus = 'Sélectionnez au moins un PNJ.';
        return;
      }
      body.npc_ids = scopeNpcIds;
    } else {
      const id = scopeType === 'location' ? scopeLocationId : scopeFactionId;
      if (!id) {
        tickStatusColor = 'var(--red)';
        tickStatus = 'Sélectionnez une cible.';
        return;
      }
      body.scope_id = id;
    }

    tickRunning = true;
    tickStatusColor = 'var(--muted)';
    tickStatus = '⟳ Le monde avance…';
    try {
      const data = await api('/api/world-tick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const npcNotes = (data.npcs || [])
        .filter((n) => (n.notes && n.notes.length) || n.dropped)
        .map((n) => `${n.name}: ${n.proposed} proposé(s), ${n.dropped} écarté(s)` +
          (n.notes && n.notes.length ? ' — ' + n.notes.join('; ') : ''));
      tickStatusColor = 'var(--text)';
      tickStatus = `✓ ${data.total_proposed} propositions (tick ${String(data.tick_id).slice(0, 4)})` +
        (npcNotes.length ? ' — ' + npcNotes.join(' | ') : '');
      setFilter('proposed');
    } catch (e) {
      tickStatusColor = 'var(--red)';
      tickStatus = '✗ ' + e.message;
    } finally {
      tickRunning = false;
    }
  }

  $effect(() => {
    void serverState.worldId;
    scopeType = 'npcs';
    scopeNpcIds = [];
    scopeLocationId = '';
    scopeFactionId = '';
    tickStatus = '';
    loadTickTargets();
  });
</script>

<div class="filter-bar" id="filter-bar">
  {#each FILTERS as f (f.status)}
    <button class="f-btn" class:active={queueState.currentFilter === f.status}
            title={f.title || ''} onclick={() => setFilter(f.status)}>{f.label}</button>
  {/each}
</div>
<!-- ── World tick controls (TICKET-0014/BRIEF-0014-b, I1/J1/M3) ──
     Manual, scoped off-screen NPC advancement. Lands in this same slot as
     the filter bar -- a second row via flex-basis:100%, not a new
     registry entry (this tab's rows are still append-only via
     /api/world-tick -> proposed_mutation, never created directly here). -->
<div class="tick-controls" id="tick-controls"
     style="flex-basis:100%; display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:8px; padding-top:8px; border-top:1px solid var(--border);">
  <button class="btn-send" id="btn-world-tick" onclick={runWorldTick} disabled={tickRunning}>Faire avancer le monde</button>
  <select id="tick-scope-type" bind:value={scopeType} title="Portée du tick">
    <option value="npcs">PNJ(s)</option>
    <option value="location">Lieu</option>
    <option value="faction">Faction</option>
  </select>
  <select id="tick-scope-npcs" multiple size="4" style="min-width:180px; display:{scopeType === 'npcs' ? '' : 'none'}"
          bind:value={scopeNpcIds} title="Ctrl/Cmd+clic pour sélectionner plusieurs PNJ">
    {#each npcs as n (n.id)}<option value={n.id}>{n.name}</option>{/each}
  </select>
  <select id="tick-scope-location" style="display:{scopeType === 'location' ? '' : 'none'}; min-width:180px;" bind:value={scopeLocationId}>
    {#each locations as l (l.id)}<option value={l.id}>{l.name}</option>{/each}
  </select>
  <select id="tick-scope-faction" style="display:{scopeType === 'faction' ? '' : 'none'}; min-width:180px;" bind:value={scopeFactionId}>
    {#each factions as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
  </select>
  <select id="tick-interval" bind:value={interval} title="Intervalle écoulé">
    <option value="quelques heures">quelques heures</option>
    <option value="quelques jours">quelques jours</option>
    <option value="quelques semaines">quelques semaines</option>
  </select>
  <span class="analyze-status" id="tick-status" style="color:{tickStatusColor}">{tickStatus}</span>
</div>
