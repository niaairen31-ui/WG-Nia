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
    /* TICKET-0056 (BRIEF-0056-b): the header's height lives ONCE, in
       --header-height (set on the shell layout container in App.svelte) --
       this calc() reads it rather than repeating the number. */
    height: calc(100vh - var(--header-height));
    border: 0;
    display: block;
  }
</style>
