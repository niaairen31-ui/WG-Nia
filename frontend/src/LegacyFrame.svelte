<script>
  import { onMount } from 'svelte';
  import { mountLegacy } from './legacy/bridge.js';

  let frameEl;

  onMount(() => {
    mountLegacy(frameEl);
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
    height: 100vh;
    border: 0;
    display: block;
  }
</style>
