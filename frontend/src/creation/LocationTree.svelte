<script>
  /* TICKET-0059 (BRIEF-0059-f, per SUPPLEMENT-0059-recon-amendments
     Amendment 1). The location-tree primitive: a faithful port of the
     traversal shared by `_npcAgentTreeHtml` (index.html:7463-7475) and
     `_linkAgentTreeHtml` (index.html:7959-7971) -- RECON-0059-a M4 found the
     two are NOT a copy-paste modulo renames (single-select radio vs
     multi-select checkbox with ancestor inheritance), but the traversal
     itself -- root detection, alphabetical sort, recursion, and the two CSS
     classes below -- IS identical, confirmed already served by one shared
     stylesheet rule set.

     Props: `locations` (the flat array) and a `row` snippet rendering ONE
     node's control. Everything else -- the `known` id set, the orphan-root
     rule, the sort, the recursion, the `linkagent-loc-node`/
     `linkagent-loc-children` wrapper divs, the `<label>` and the name text
     -- belongs to this component; a consumer expresses none of it.

     Narrowing from Amendment 1: the amendment specified a separate
     `isChecked(node)` predicate prop alongside the row snippet. This brief
     drops it -- once the snippet renders the `<input>` itself, the input
     owns its own `checked` attribute (npcAgent: `checked={selectedRoot ===
     loc.id}`; linkAgent, at `-g`: its own ancestor-aware predicate), and a
     separate predicate prop would just be a second expression of the same
     fact. No `mode` prop either (rejected by Amendment 1 itself, as the
     leaky union type TICKET-0057's D-C question taught this project to
     refuse).

     Empty case: the legacy renderers returned '' from `_*TreeHtml(null)`
     and each caller substituted its own empty message. This component keeps
     that shape -- it renders nothing when there are no roots; the empty
     message is the consumer's to word (the two agents phrase it
     differently), never this component's.

     `esc()` is gone: Svelte escapes text interpolation by construction.

     Recursion is a local snippet calling itself (Svelte 5), not
     `<svelte:self>` -- tooling/verify/checks/location_tree.py's
     self-recursion detector recognizes both forms, but a snippet keeps the
     `known`/`childrenOf` closures in one script block instead of forcing
     them onto props for a second component instance.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document, where Svelte's shell-injected
     scoped CSS never reaches -- the `.linkagent-loc-node`/
     `.linkagent-loc-children` rules stay in index.html's own stylesheet
     (BRIEF-0059-g/-l retire that block once both agents have migrated). */
  let { locations, row } = $props();

  const known = $derived(new Set(locations.map((l) => l.id)));

  function childrenOf(parentId) {
    return locations
      .filter((l) => (parentId == null
        ? (!l.parent_location_id || !known.has(l.parent_location_id))
        : l.parent_location_id === parentId))
      .sort((a, b) => a.name.localeCompare(b.name));
  }
</script>

{#snippet tree(parentId)}
  {#each childrenOf(parentId) as loc (loc.id)}
    <div class="linkagent-loc-node">
      <label>{@render row(loc)} {loc.name}</label>
      <div class="linkagent-loc-children">{@render tree(loc.id)}</div>
    </div>
  {/each}
{/snippet}

{@render tree(null)}
