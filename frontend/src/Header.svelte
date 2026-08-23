<script>
  import { onMount } from 'svelte';
  import { serverState, refreshServerState } from './lib/serverState.svelte.js';
  import { activateWorldCascade } from './creation/tabs.js';
  import { openWorldCreateModal, openWorldDeleteModal } from './creation/worldCrud.svelte.js';
  import { navigate } from './lib/router.js';
  import { SCHEDULE_PHASES, PHASE_LABELS } from './creation/schedule.js';

  // TICKET-0056 (BRIEF-0056-c): the router is the single source of truth for
  // the active surface; App.svelte derives it from onRoute and passes it
  // down here read-only.
  let { activeSurface } = $props();

  function switchSurface(key) {
    navigate(key);
  }

  async function onWorldChange(event) {
    const id = event.target.value;
    /* TICKET-0056 (C3) planned this move explicitly: "When Creation
       migrates (TICKET-0058/59), the cascade moves WITH it -- it is not
       re-derived here in advance." TICKET-0059 (BRIEF-0059-l commit 1) is
       that migration -- activateWorldCascade (frontend/src/creation/tabs.js)
       is the single writer (POST /api/worlds/{id}/activate) plus the
       world-scoped resets, replacing the legacy activateWorld() this used
       to delegate to via the bridge. */
    await activateWorldCascade(id, refreshServerState);
    await loadWorldPhase();
  }

  // TICKET-0074 (BRIEF-0074-b), T-A1 condition 1: the current phase, shown
  // here as persistent text -- never behind a click, never a tooltip -- so
  // a forgotten phase is VISIBLE rather than mute. Header.svelte is always
  // mounted, outside every surface's own gated container (App.svelte), so
  // this is the ONE place a control reaches every surface at once.
  let worldPhase = $state({ current_phase: '', phases: [] });

  async function loadWorldPhase() {
    try {
      const res = await fetch('/api/world/phase');
      if (!res.ok) return;
      worldPhase = await res.json();
    } catch (_err) {
      // best-effort chrome display -- a failed fetch just leaves the
      // control blank rather than raising a shell-wide error banner.
    }
  }

  async function onPhaseChange(event) {
    const next = event.target.value;
    try {
      const res = await fetch('/api/world/phase', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_phase: next }),
      });
      if (res.ok) worldPhase = await res.json();
    } catch (_err) {
      // leave the previously displayed phase on failure
    }
  }

  onMount(() => { loadWorldPhase(); });
</script>

{#if serverState.error}
  <div class="refusal-band">Erreur de chargement de l'état serveur : {serverState.error}</div>
{/if}
<header>
  <h1>🌍 World Engine</h1>
  <span class="divider">│</span>
  <span class="brand">Cockpit</span>
  <span class="sub">creator review dashboard</span>
  <span class="spacer"></span>
  <div class="mode-tabs">
    <button class="mode-tab" class:active={activeSurface === 'play'} onclick={() => switchSurface('play')}>Play</button>
    <button class="mode-tab" class:active={activeSurface === 'creation'} onclick={() => switchSurface('creation')}>Création</button>
    <button class="mode-tab" class:active={activeSurface === 'observation'} onclick={() => switchSurface('observation')}>Observation</button>
  </div>
  {#if !serverState.error}
    <select id="world-selector" onchange={onWorldChange} title="Monde actif">
      {#each serverState.worlds as w (w.id)}
        <option value={w.id} selected={w.id === serverState.worldId}>{w.is_active ? `${w.name} (actif)` : w.name}</option>
      {/each}
    </select>
  {/if}
  <button class="btn-icon" onclick={openWorldCreateModal} title="Créer un nouveau monde">+ Monde</button>
  <button class="btn-icon" onclick={openWorldDeleteModal} title="Supprimer le monde sélectionné">🗑 Monde</button>
  <span class="phase-indicator">Phase : <strong>{PHASE_LABELS[worldPhase.current_phase] || '—'}</strong></span>
  <select id="world-phase-selector" onchange={onPhaseChange} title="Avancer la phase du monde actif" disabled={!worldPhase.phases?.length}>
    {#each SCHEDULE_PHASES as phase (phase)}
      <option value={phase} selected={phase === worldPhase.current_phase}>{PHASE_LABELS[phase]}</option>
    {/each}
  </select>
  <span class="local-badge">127.0.0.1 · local only</span>
</header>

<style>
  header {
    height: var(--header-height);
    box-sizing: border-box;
    background: #1a1d24;
    color: #e6e6e6;
    border-bottom: 1px solid #333;
    padding: 0 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  h1 { font-size: 15px; font-weight: 600; margin: 0; }
  .divider { color: #444; }
  .brand { font-weight: 600; color: #6ab0ff; }
  .sub { color: #888; font-size: 12px; }
  .spacer { flex: 1; }
  .mode-tabs { display: flex; gap: 4px; }
  .mode-tab {
    background: transparent;
    border: 1px solid #333;
    color: #ccc;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
  }
  .mode-tab.active { background: #2a3a52; border-color: #6ab0ff; color: #fff; }
  select, .btn-icon {
    background: #22262e;
    color: #e6e6e6;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px 8px;
    cursor: pointer;
  }
  .local-badge { font-size: 11px; color: #888; border: 1px solid #333; border-radius: 4px; padding: 2px 6px; }
  .phase-indicator { font-size: 12px; color: #ccc; }
  .phase-indicator strong { color: #6ab0ff; }
  .refusal-band {
    background: #4a1d1d;
    color: #ffb3b3;
    padding: 8px 20px;
    font-size: 13px;
    border-bottom: 1px solid #6a2a2a;
  }
</style>
