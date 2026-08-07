<script>
  /* TICKET-0059 (BRIEF-0059-j). Faithful port of renderAgendaSheet/
     _intriguesRenderStep/_intriguesRenderLinkedGoal (commit 1) plus
     intriguesRenderCreatePanel/intriguesGenerateDraft/intriguesSubmitCreate
     (commit 2) -- all now deleted from index.html. `agenda` carries no
     ENTITY_TYPE_REGISTRY row, so this never used Sheet.svelte's own
     registry.types[type] shape. Mutation/fetch logic lives in
     intrigues.svelte.js; this component owns markup only, mirroring
     Evenements.svelte's own split off eventDraft.svelte.js.

     Rendered by Sheet.svelte inside its own 'view' mode when
     creationState.activeTabKey === 'intrigues', gated on tabKey exactly
     like evenements -- not a registry.types[type] lookup, and the SAME
     isNew/agenda shape evenements' own isNew/event split already uses.

     View mode: no save/delete, the API surface is frozen to status
     transitions and link detach, unchanged from the legacy renderer's own
     doc comment. detachLink shares its endpoint with the entity sheet's
     own goals editor (GoalsEditor.svelte's detachGoalLink) -- both
     surfaces legitimately act on the same
     /api/goal-agenda-links/{id}/detach route; see this brief's own note
     for why they stay unmerged.

     Create mode: intriguesGenerateDraft fills the form, never writes;
     intriguesSubmitCreate (submitAgenda here) is the one write, POST
     /api/agendas, invoked by this component's own inline
     "+ Créer l'intrigue" button (the same posture Evenements' create mode
     takes with its own inline submit, not the shared header Save button --
     intrigues never shows that button, view or create).

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { setAgendaStatus, detachLink, setStepStatus, populateOwnerOptions, generateAgendaDraft, submitAgenda } from './intrigues.svelte.js';

  let { isNew, agenda } = $props();

  let ownerOptions = $state({ factions: [], characters: [] });
  let ownerId = $state('');
  let title = $state('');
  let steps = $state(['', '', '', '', '']);
  let genBrief = $state('');
  let genStatus = $state('');
  let genNotes = $state([]);
  let addStatus = $state('');

  $effect(() => {
    if (!isNew) return;
    ownerId = '';
    title = '';
    steps = ['', '', '', '', ''];
    genBrief = '';
    genStatus = '';
    genNotes = [];
    addStatus = '';
    populateOwnerOptions().then((opts) => { ownerOptions = opts; }).catch(() => { /* left with just the placeholder option */ });
  });

  async function generate() {
    if (!ownerId) { genStatus = 'Propriétaire requis.'; return; }
    const brief = genBrief.trim();
    if (!brief) { genStatus = 'Intention requise.'; return; }
    genStatus = 'Génération…';
    let result;
    try {
      result = await generateAgendaDraft(ownerId, brief);
    } catch (e) {
      genStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      genStatus = (result && result.error) || 'Échec de la génération.';
      return; // form untouched
    }
    title = result.title || '';
    const resultSteps = result.steps || [];
    steps = [0, 1, 2, 3, 4].map((i) => resultSteps[i] || '');
    genNotes = result.notes || [];
    genStatus = "Brouillon généré — relisez et éditez avant d'accepter.";
  }

  async function submit() {
    const trimmedTitle = title.trim();
    const stepRows = steps.map((s) => s.trim()).filter((v) => v).map((objective) => ({ objective }));
    if (!ownerId) { addStatus = 'Propriétaire requis.'; return; }
    if (!trimmedTitle) { addStatus = 'Titre requis.'; return; }
    if (stepRows.length < 2 || stepRows.length > 5) { addStatus = 'Entre 2 et 5 étapes requises.'; return; }
    addStatus = '…';
    try {
      await submitAgenda(ownerId, trimmedTitle, stepRows);
    } catch (e) {
      addStatus = e.message;
    }
  }
</script>

{#if isNew}
  <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:12px;">
    <div class="field-section-title">Générer avec l'IA</div>
    <textarea rows="2" style="width:100%; resize:vertical" bind:value={genBrief}
      placeholder="Intention en une phrase, ex. : « La Guilde du Sel veut prendre le contrôle du port sans que le Magistrat ne s'en aperçoive »"></textarea>
    <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
      <button class="btn-send" onclick={generate}>Générer</button>
      <span style="font-size:12px; color:var(--muted)">{genStatus}</span>
    </div>
    {#if genNotes.length}
      <div class="field-section-title" style="margin-top:8px">Notes de l'assistant</div>
      <div class="row-table">
        {#each genNotes as n}
          <div class="row-card" style="font-size:12px; color:var(--muted)">{n}</div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="field-section">
    <div class="field-section-title">Nouvelle intrigue</div>
    <div class="field-grid">
      <div class="field-row">
        <label for="intrigues-f-owner">Propriétaire (faction ou personnage) *</label>
        <select id="intrigues-f-owner" bind:value={ownerId}>
          <option value="">—</option>
          {#if ownerOptions.factions.length}
            <optgroup label="Factions">
              {#each ownerOptions.factions as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
            </optgroup>
          {/if}
          {#if ownerOptions.characters.length}
            <optgroup label="Personnages (intrigue personnelle)">
              {#each ownerOptions.characters as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
            </optgroup>
          {/if}
        </select>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="intrigues-f-title">Titre *</label>
        <input type="text" id="intrigues-f-title" placeholder="ex : Le complot du sel" bind:value={title}>
      </div>
    </div>
    <div class="field-section-title" style="margin-top:8px">Étapes (2 à 5, dans l'ordre)</div>
    <div class="field-grid">
      <div class="field-row" style="grid-column:1/-1"><label>Étape 1 * (objectif)</label><input type="text" bind:value={steps[0]}></div>
      <div class="field-row" style="grid-column:1/-1"><label>Étape 2 * (objectif)</label><input type="text" bind:value={steps[1]}></div>
      <div class="field-row" style="grid-column:1/-1"><label>Étape 3 (optionnel)</label><input type="text" bind:value={steps[2]}></div>
      <div class="field-row" style="grid-column:1/-1"><label>Étape 4 (optionnel)</label><input type="text" bind:value={steps[3]}></div>
      <div class="field-row" style="grid-column:1/-1"><label>Étape 5 (optionnel)</label><input type="text" bind:value={steps[4]}></div>
    </div>
    <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
      <button class="btn-send" onclick={submit}>+ Créer l'intrigue</button>
      <span style="font-size:12px; color:var(--muted)">{addStatus}</span>
    </div>
  </div>
{:else}
  <div class="field-section">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
      <div><strong>{agenda.title}</strong>
        <span class="badge b-other" title={agenda.owner_type === 'character' ? 'Intrigue personnelle' : 'Intrigue de faction'}>
          {agenda.owner_type === 'character' ? 'personnelle' : 'faction'}
        </span>
        <span style="color:var(--muted); font-size:12px;">({agenda.owner_name})</span>
      </div>
      <div style="display:flex; gap:6px; align-items:center;">
        <span class="badge b-{agenda.status}">{agenda.status}</span>
        {#if agenda.status === 'active'}
          <button class="btn-icon" title="Abandonner l'intrigue"
            onclick={() => setAgendaStatus(agenda.id, 'abandoned', (agenda.linked_goals || []).length)}>⏸</button>
        {/if}
        {#if agenda.status === 'abandoned' || agenda.status === 'failed'}
          <button class="btn-icon" title="Réactiver l'intrigue" onclick={() => setAgendaStatus(agenda.id, 'active', 0)}>▶</button>
        {/if}
      </div>
    </div>
  </div>

  <div class="field-section">
    <div class="field-section-title">Étapes</div>
    {#each agenda.steps as s (s.id)}
      <div class="row-card" style="flex-direction:row; align-items:flex-start; justify-content:space-between; gap:6px; margin:4px 0;">
        <div style="flex:1; min-width:160px;">
          <span style="font-size:12px; color:var(--muted);">#{s.step_order}</span>
          <span>{s.objective}</span>
          {#if s.visibility_trace}<div style="font-size:11px; color:var(--muted);">trace : {s.visibility_trace}</div>{/if}
          {#if s.outcome}<div style="font-size:11px; color:var(--muted);">résultat : {s.outcome}</div>{/if}
        </div>
        <span class="badge b-{s.status}">{s.status}</span>
        <div>
          {#if s.status === 'active'}
            <button class="btn-icon" title="Terminer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'completed')}>✓</button>
            <button class="btn-icon" title="Échouer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'failed')}>✗</button>
          {:else if s.status === 'pending'}
            <button class="btn-icon" title="Activer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'active')}>▶</button>
          {/if}
        </div>
      </div>
    {/each}
  </div>

  {#if (agenda.linked_goals || []).length > 0}
    <div class="field-section">
      <div class="field-section-title">Objectifs liés ({agenda.linked_goals.length})</div>
      {#each agenda.linked_goals as l (l.link_id)}
        <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; gap:6px; margin:4px 0;">
          <span style="flex:1; min-width:160px;">
            {l.goal_description}
            <span style="font-size:11px; color:var(--muted);"> — {l.npc_name}</span>
            <span class="badge {l.goal_status !== 'active' ? 'b-rejected' : 'b-equipped'}">{l.goal_status}</span>
          </span>
          <button class="btn-icon" title="Détacher (réversible — le lien peut être rattaché plus tard)"
            onclick={() => detachLink(agenda.id, l.link_id)}>✕</button>
        </div>
      {/each}
    </div>
  {/if}
{/if}
