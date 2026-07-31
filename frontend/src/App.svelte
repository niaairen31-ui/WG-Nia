<script>
  import Header from './Header.svelte';
  import LegacyFrame from './LegacyFrame.svelte';
  import { hideLegacyHeader } from './legacy/bridge.js';
  import { refreshServerState } from './lib/serverState.svelte.js';

  let activeSurface = $state('play');

  // TICKET-0056 (BRIEF-0056-b): on legacy load -- suppress the legacy header
  // (byte-untouched index.html, style injected via the bridge), then mirror
  // server state. mountLegacy itself lives in LegacyFrame.svelte; this is the
  // continuation once that iframe's `load` event has fired.
  async function onLegacyReady() {
    hideLegacyHeader();
    await refreshServerState();
  }
</script>

<div class="shell-layout">
  <Header bind:activeSurface />
  <LegacyFrame onReady={onLegacyReady} />
</div>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
  }
  .shell-layout {
    --header-height: 56px;
  }
</style>
