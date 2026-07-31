<script>
  import { serverState, refreshServerState } from './lib/serverState.svelte.js';
  import { activateWorldViaLegacy, openWorldCreate, openWorldDelete } from './legacy/bridge.js';
  import { navigate } from './lib/router.js';

  // TICKET-0056 (BRIEF-0056-c): the router is the single source of truth for
  // the active surface; App.svelte derives it from onRoute and passes it
  // down here read-only.
  let { activeSurface } = $props();

  function switchSurface(key) {
    navigate(key);
  }

  async function onWorldChange(event) {
    const id = event.target.value;
    /* TICKET-0056 (C3). The shell does NOT own the world-switch cascade. It
       delegates to the legacy activateWorld(), which is the single place that
       knows every world-scoped reset (_creationRunWorldSwitchResets), then
       re-reads the server. Duplicating the POST here would create a second
       writer for one server-side fact. When Creation migrates (TICKET-0058/59),
       the cascade moves WITH it -- it is not re-derived here in advance. */
    await activateWorldViaLegacy(id);
    await refreshServerState();
  }
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
  <button class="btn-icon" onclick={openWorldCreate} title="Créer un nouveau monde">+ Monde</button>
  <button class="btn-icon" onclick={openWorldDelete} title="Supprimer le monde sélectionné">🗑 Monde</button>
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
  .refusal-band {
    background: #4a1d1d;
    color: #ffb3b3;
    padding: 8px 20px;
    font-size: 13px;
    border-bottom: 1px solid #6a2a2a;
  }
</style>
