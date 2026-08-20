<script>
  import { onMount } from 'svelte';
  import { mountLegacy } from './legacy/bridge.js';

  let { onReady } = $props();
  let frameEl;

  onMount(async () => {
    await mountLegacy(frameEl);
    if (onReady) await onReady();
  });
</script>

<!-- TICKET-0056 (B1): ONE iframe, ONE src, assigned once and never
     reassigned. An iframe navigation pushes an entry onto the PARENT
     history stack -- reassigning src to switch surfaces would make the
     browser Back button replay legacy boots instead of shell routes.
     Surface switching goes through legacy/bridge.js by direct
     same-origin call. legacy_mount.py enforces the single-assignment
     rule. -->
<iframe id="legacy-frame" title="Cockpit (legacy)" src="/legacy" bind:this={frameEl}></iframe>

<style>
  iframe {
    width: 100%;
    /* TICKET-0065 (BRIEF-0065-a): the iframe fills the slot the shell gives
       it instead of computing its own viewport height. --header-height is
       still read by Header.svelte's own `height` rule; this was its only
       other consumer, and it was the shell's second, independent height
       authority. shell_height_chain.py forbids that viewport-unit literal
       from returning. */
    flex: 1;
    min-height: 0;
    border: 0;
    display: block;
  }
</style>
