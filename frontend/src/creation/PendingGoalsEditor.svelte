<script>
  /* TICKET-0058 (BRIEF-0058-g, family e). Faithful port of the
     "créés à l'acceptation" pending-goals panel on a NEW npc sheet --
     authorRenderPendingGoals (index.html, now deleted). Same
     in-creation-form idiom as PendingKnowledgeEditor: 1 long + 2 short
     textareas, each clearable (an empty textarea is simply not sent) --
     read once, at accept time, via pendingDrafts.svelte.js's
     goalsForCreate(). No per-row remove control: the slots are fixed
     (M2 cardinality), not a dynamic list, same as the legacy panel. */
  import { pendingDraftsState } from './pendingDrafts.svelte.js';
</script>

<div class="row-card">
  <div class="field-grid">
    <div class="field-row span-2"><label>Long terme</label><textarea bind:value={pendingDraftsState.goals.long}></textarea></div>
    <div class="field-row span-2"><label>Court terme 1</label><textarea bind:value={pendingDraftsState.goals.shorts[0]}></textarea></div>
    <div class="field-row span-2"><label>Court terme 2</label><textarea bind:value={pendingDraftsState.goals.shorts[1]}></textarea></div>
  </div>
</div>
