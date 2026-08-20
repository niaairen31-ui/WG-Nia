<script>
  import Header from './Header.svelte';
  import LegacyFrame from './LegacyFrame.svelte';
  import Creation from './creation/Creation.svelte';
  import WorldCrud from './creation/WorldCrud.svelte';
  import { hideLegacyHeader, showSurface, legacyDocument } from './legacy/bridge.js';
  import { showCreationSubTab } from './creation/tabs.js';
  import { serverState, refreshServerState } from './lib/serverState.svelte.js';
  import { onRoute, navigate } from './lib/router.js';
  import { initGraphMount } from './graph/mount.js';
  import { initCreationMount } from './creation/mount.js';

  let currentSurface = $state('play');

  /* TICKET-0059 (BRIEF-0059-l item 2): Creation no longer routes through
     the legacy bridge -- showCreationSubTab (frontend/src/creation/tabs.js)
     is called directly, same document, no cross-document 'route:subtab'
     dispatch/mirror dance (it calls replace() itself now). play/observation
     are the only two surfaces still legacy-mounted, so they're the only
     ones still reached through showSurface(). */
  function applyRoute({ surface, subTab }) {
    currentSurface = surface;
    try {
      if (surface === 'creation') {
        showCreationSubTab(subTab || 'npc');
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
  // TICKET-0059 (BRIEF-0059-l commit 1). Observation's own
  // observationOpenPrompt (index.html, TICKET-0060 territory, untouched
  // otherwise) reaches Creation's now-shell-side Prompts tab through this
  // reverse-bridge event -- navigate() drives the surface/sub-tab switch
  // through the same router path any other navigation takes, then the
  // 'creation:open-prompt' re-dispatch (on THIS document, not the legacy
  // one) reaches Prompts.svelte's own listener, whose legacyDoc prop now
  // resolves to this document too (mount.js targets it directly).
  function onObservationOpenPrompt({ detail }) {
    navigate('creation', 'prompts');
    document.dispatchEvent(new CustomEvent('creation:open-prompt', { detail }));
  }

  async function onLegacyReady() {
    hideLegacyHeader();
    initGraphMount(legacyDocument());
    initCreationMount(legacyDocument());
    legacyDocument().addEventListener('observation:open-prompt', onObservationOpenPrompt);
    await refreshServerState();
    onRoute(applyRoute);
  }
</script>

<div class="shell-layout">
  <Header activeSurface={currentSurface} />
  <div class="legacy-slot" style:display={currentSurface === 'creation' ? 'none' : 'flex'}>
    <LegacyFrame onReady={onLegacyReady} />
  </div>
  <Creation active={currentSurface === 'creation'} />
  <WorldCrud />
</div>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
  }
  /* TICKET-0065 (BRIEF-0065-a). The shell owns ONE height authority.
     shared.css:11 makes html/body full-height; these two rules carry that
     height down to the surfaces, so `.app-view`'s own `flex:1; min-height:0`
     (shared.css:41) resolves against a definite-height flex parent exactly
     as it did when it was a direct child of the legacy document's body.
     Before this, #app had no rule at all and .shell-layout set only a
     custom property, so every Creation flex ladder below resolved against
     an auto-height ancestor and .conv-list never became scrollable. */
  :global(#app) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .shell-layout {
    --header-height: 56px;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .legacy-slot {
    flex: 1;
    min-height: 0;
    flex-direction: column;
  }
</style>
