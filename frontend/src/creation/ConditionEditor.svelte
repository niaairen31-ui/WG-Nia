<script>
  /* TICKET-0111 (BRIEF-0111-D, T1). One condition of a quest offer: a flat
     condition is edited as a list of requirement rows (`all` of them); a
     nested one is shown by its French lines, read-only, and saved back
     unchanged. `cond` is a draft object owned by questOffersState
     (conditionDraft in questRequirements.js). TICKET-0112 (BRIEF-0112-E,
     IB1, T1): both are also written and edited in French, through the
     interpreter under the condition; `role` is the condition's.
     TICKET-0113 (BRIEF-0113-E, WN2): `unsaved`, the offer draft's proposed
     attributes, is listed with the rows' attributes and goes to the
     interpreter, which adds the ones the creator confirms.
     TICKET-0121 (BRIEF-0121-F): `seed` and `onsettle` go to the
     interpreter -- a quest designer's condition still waiting. */
  import QuestRequirementRow from './QuestRequirementRow.svelte';
  import ConditionInterpreter from './ConditionInterpreter.svelte';
  import { blankRequirement, withUnsaved } from './questRequirements.js';

  let { cond, choices, role, emptyLabel, addLabel, unsaved = [], seed = null, onsettle = null } = $props();

  let rowChoices = $derived(withUnsaved(choices, unsaved));

  function clearLocked() {
    cond.locked = null;
    cond.lines = [];
  }
</script>

{#if cond.locked}
  <div class="cond-locked">
    {#each cond.lines as line, i (i)}
      <div style={'padding-left:' + line.depth * 14 + 'px'}>{line.text}</div>
    {/each}
    <p class="muted">Condition imbriquée : elle se modifie en langage naturel.</p>
    <button onclick={() => clearLocked()}>Effacer cette condition</button>
  </div>
{:else}
  {#if cond.list.length === 0 && emptyLabel}<p class="muted">{emptyLabel}</p>{/if}
  {#each cond.list as req, i (i)}
    <QuestRequirementRow {req} choices={rowChoices} onremove={() => cond.list.splice(i, 1)} />
  {/each}
  <button onclick={() => cond.list.push(blankRequirement())}>{addLabel}</button>
{/if}
<ConditionInterpreter {cond} {role} {unsaved} {seed} {onsettle} types={choices?.entity_types || []} />

<style>
  .cond-locked { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
  .muted { color: var(--muted); font-size: 12px; }
</style>
