<script>
  import Header from './Header.svelte';
  import LegacyFrame from './LegacyFrame.svelte';
  import { hideLegacyHeader, showSurface, showCreationTab, legacyDocument } from './legacy/bridge.js';
  import { serverState, refreshServerState } from './lib/serverState.svelte.js';
  import { onRoute, replace } from './lib/router.js';
  import { initGraphMount } from './graph/mount.js';
  import { initCreationMount } from './creation/mount.js';

  let currentSurface = $state('play');

  /* TICKET-0058 (BRIEF-0058-k): continuous sync now holds. The legacy
     document dispatches 'route:subtab' after showCreationSubTab actually
     changes the active tab; onLegacySubtabRoute below mirrors that into
     the address bar via replace() (no pushState, no popstate) -- it never
     calls back into showCreationTab, which would re-enter the legacy
     document from a signal it just emitted itself. */
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

  // TICKET-0058 (BRIEF-0058-k): the legacy document is the sub-tab
  // authority; the shell only mirrors. One direction of control, matching
  // graph:slot/island:slot -- no function is installed on the legacy
  // window for this.
  function onLegacySubtabRoute({ detail }) {
    currentSurface = 'creation';
    replace('creation', detail.tab);
  }

  // TICKET-0056 (BRIEF-0056-b): on legacy load -- suppress the legacy header
  // (byte-untouched index.html, style injected via the bridge), then mirror
  // server state, then wire the shell to the router. mountLegacy itself
  // lives in LegacyFrame.svelte; this is the continuation once that
  // iframe's `load` event has fired.
  async function onLegacyReady() {
    hideLegacyHeader();
    initGraphMount(legacyDocument());
    initCreationMount(legacyDocument());
    legacyDocument().addEventListener('route:subtab', onLegacySubtabRoute);
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
