<script>
  import Header from './Header.svelte';
  import LegacyFrame from './LegacyFrame.svelte';
  import { hideLegacyHeader, showSurface, showCreationTab, legacyDocument } from './legacy/bridge.js';
  import { serverState, refreshServerState } from './lib/serverState.svelte.js';
  import { onRoute } from './lib/router.js';
  import { initGraphMount } from './graph/mount.js';

  let currentSurface = $state('play');

  /* TICKET-0056: the URL is authoritative on ENTRY, not continuously
     synchronized. A sub-tab clicked inside the legacy frame does not
     rewrite the address bar -- doing so would require the legacy document
     to call out to the shell, i.e. an edit to index.html, which this ticket
     refuses. Continuous sync arrives with the Creation surface itself
     (TICKET-0058). */
  async function applyRoute({ surface, subTab }) {
    currentSurface = surface;
    try {
      if (surface === 'creation' && subTab) {
        await showCreationTab(subTab);
      } else {
        showSurface(surface);
      }
    } catch (err) {
      serverState.error = err.message;
    }
  }

  // TICKET-0056 (BRIEF-0056-b): on legacy load -- suppress the legacy header
  // (byte-untouched index.html, style injected via the bridge), then mirror
  // server state, then wire the shell to the router. mountLegacy itself
  // lives in LegacyFrame.svelte; this is the continuation once that
  // iframe's `load` event has fired.
  async function onLegacyReady() {
    hideLegacyHeader();
    initGraphMount(legacyDocument());
    await refreshServerState();
    onRoute(applyRoute);
  }
</script>

<div class="shell-layout">
  <Header activeSurface={currentSurface} />
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
