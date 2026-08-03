<script>
  /* TICKET-0058 (BRIEF-0058-g, family e). Faithful port of the
     "créé à l'acceptation" pending-knowledge panel on a NEW npc sheet --
     authorRenderPendingKnowledge/authorRemovePendingKnowledge (index.html,
     now deleted). No per-row save button -- rows are read once, at accept
     time, via pendingDrafts.svelte.js's knowledgeForCreate(), same as the
     legacy _syncPendingKnowledgeFromDom this replaces. Secret is always
     forced true (disabled checkbox, matching the original -- an AI-drafted
     NPC secret is never anything else). */
  import { pendingDraftsState } from './pendingDrafts.svelte.js';

  let { levelOptions } = $props();

  function removeRow(i) {
    pendingDraftsState.knowledge = pendingDraftsState.knowledge.filter((_, idx) => idx !== i);
  }
</script>

{#if pendingDraftsState.knowledge.length === 0}
  <div class="empty">Aucun savoir secret proposé.</div>
{:else}
  <div class="row-table">
    {#each pendingDraftsState.knowledge as k, i}
      <div class="row-card">
        <div class="field-grid">
          <div class="field-row"><label>Subject</label><input type="text" bind:value={k.subject}></div>
          <div class="field-row"><label>Level</label>
            <select bind:value={k.level}>
              {#each levelOptions as l}<option value={l}>{l}</option>{/each}
            </select></div>
          <div class="field-row checkbox">
            <input type="checkbox" checked disabled>
            <label>Secret (forcé)</label></div>
          <div class="field-row span-2"><label>Content</label><textarea bind:value={k.content}></textarea></div>
        </div>
        <div class="row-card-actions">
          <button class="btn-end" onclick={() => removeRow(i)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}
