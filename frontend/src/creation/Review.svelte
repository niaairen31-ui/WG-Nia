<script>
  /* TICKET-0058 (BRIEF-0058-i). Svelte-native presentational half of the
     generic review-tree component (TICKET-0041) -- the reactive counterpart
     to review/registry.js's string-building reviewNode/reviewTree, which
     stays in place for the room batch generator (still legacy until
     BRIEF-0058-j). Both share the exact same reviewCascade -- one pure
     function, two render strategies, never two cascade implementations.

     Knows nothing about the world model: a consumer (Region.svelte) builds
     a descriptor and hands it here. `extra` is an optional per-node snippet
     replacing the old string-based `node.extras` field -- a real Svelte
     snippet can carry its own event handlers (region's sensed-link confirm
     toggles), which a pre-rendered HTML string never could once this
     renders inside the shell's own reactivity instead of a legacy
     innerHTML write.

     No scoped <style> block: this mounts inside the legacy iframe document
     (via Region.svelte's own mount target), where Svelte's shell-injected
     scoped CSS never reaches -- markup reuses the legacy document's own
     .review-node/.review-children/.review-rejected classes and CSS vars,
     same posture as Constructeur.svelte and the graph primitive. */
  import { reviewCascade } from './review/registry.js';

  let { descriptor, extra } = $props();

  const cascade = $derived(reviewCascade(descriptor));
  const childrenByParent = $derived.by(() => {
    const map = {};
    for (const n of descriptor.nodes) {
      const p = cascade.effectiveParent[n.id];
      if (p == null) continue;
      (map[p] = map[p] || []).push(n);
    }
    return map;
  });
  // BRIEF-0033-c: render every top-level node, not just the first found, so
  // a reparented-to-root node stays visible (same fix reviewTree carries).
  const roots = $derived(descriptor.nodes.filter(n => cascade.effectiveParent[n.id] == null));

  function isAccepted(id) {
    return descriptor.accepted[id] !== false;
  }
</script>

{#snippet node(n)}
  {@const accepted = isAccepted(n.id)}
  {@const reparented = n.parentId != null && cascade.effectiveParent[n.id] !== n.parentId}
  {@const children = childrenByParent[n.id] || []}
  <div class="review-node" class:review-rejected={!accepted}>
    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap">
      <span style="font-weight:600" class="review-name-link" onclick={() => descriptor.onOpenSheet(n.id)}>{n.name}</span>
      <span style="font-size:11px; color:var(--muted)">{n.subtitle || ''}</span>
      {#if reparented}
        <span class="badge b-other" style="font-size:10px">{descriptor.reparentedLabel}</span>
      {/if}
      <button class="btn-icon" style="margin-left:auto" onclick={() => descriptor.onToggleAccept(n.id)}>
        {accepted ? 'Rejeter' : 'Accepter'}
      </button>
    </div>
    {#if n.description}
      <div style="font-size:12px; color:var(--muted)">{n.description}</div>
    {/if}
    {#if n.notes && n.notes.length}
      <div style="margin-top:4px">
        {#each n.notes as note}
          <div style="font-size:11px; color:var(--muted)">· {note}</div>
        {/each}
      </div>
    {/if}
    {#if extra}{@render extra(n)}{/if}
    {#if children.length}
      <div class="review-children">
        {#each children as child (child.id)}
          {@render node(child)}
        {/each}
      </div>
    {/if}
  </div>
{/snippet}

{#if !descriptor.nodes.length}
  <div class="empty">Aucun element propose.</div>
{:else if !roots.length}
  <div class="empty">Aucun element racine dans le brouillon.</div>
{:else}
  {#each roots as root (root.id)}
    {@render node(root)}
  {/each}
{/if}
