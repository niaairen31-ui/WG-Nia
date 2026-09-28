<script>
  /* TICKET-0095 (K1, BRIEF-0095-d, C-08). The model-choice review panel: each
     name the day concordance bound by a model choice (ambiguous or near) is
     shown with its day, the model's pick, the judge's verdict and the cited
     evidence, then agreed ("D'accord", appellation ticked by default: I1) or
     disagreed ("Pas d'accord", the right entity picked in a select -- never
     typed -- or "Aucune entité connue": H2). Sits beside NamesPanel.svelte in
     the "Noms à lier" tab; each write is one explicit click. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    reviewState, loadChoices, reloadForWorld, recordFor, scopeFor, targetOf,
    setRecord, setScope, setTarget, setQuery, disagreeOptions, agree, disagree, NO_ENTITY,
  } from './choiceReview.svelte.js';

  let { visible = false } = $props();

  const CATEGORY_LABEL = Object.freeze({
    place: 'lieu', person: 'personne', faction: 'faction', object: 'objet', other: 'autre',
  });
  const TRIGGER_LABEL = Object.freeze({ ambiguous: 'ambigu', near: 'nom proche' });
  const SCOPE_OPTIONS = Object.freeze([
    { value: 'rencontre', label: "Ceux qui l'ont rencontré" },
    { value: 'world', label: 'Tout le monde' },
    { value: 'none', label: 'Personne' },
  ]);

  function scopeLabel(scope) {
    if (scope.scope_type === 'world') return 'tout le monde';
    const kind = { location: 'lieu', faction: 'faction', rencontre: 'rencontre' }[scope.scope_type] || scope.scope_type;
    return `${kind} : ${scope.scope_name || '?'}`;
  }

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });

  // Declared after the reset above, so a world change clears then reloads.
  $effect(() => {
    void serverState.worldId;
    if (visible) loadChoices();
  });
</script>

<div class="queue-panel" id="lore-choice-review-panel">
  <div class="panel-head">
    <h2>Choix du modèle à revoir</h2>
    <button disabled={reviewState.loading} onclick={() => loadChoices()}>
      {reviewState.loading ? '⟳' : 'Rafraîchir'}
    </button>
  </div>
  <div class="queue-body">
    {#if reviewState.error}
      <div class="r-err">{reviewState.error}</div>
    {/if}
    {#if !reviewState.loading && reviewState.choices.length === 0}
      <p class="muted">Aucun choix à revoir.</p>
    {/if}
    {#each reviewState.choices as row (row.id)}
      <div class="choice-line">
        <div class="choice-head">
          <strong>« {row.surface_form} »</strong>
          <span class="muted">
            {CATEGORY_LABEL[row.category] || row.category} · {TRIGGER_LABEL[row.trigger] || row.trigger}
            · Jour {row.day.day_number} — {row.day.character_name}
          </span>
          {#if !row.day.planned}
            <span class="badge">sans plan</span>
          {/if}
        </div>
        <p class="excerpt">… {row.day.declaration} …</p>
        <div>
          Choix du modèle : <strong>{row.chosen.name}</strong>
          —
          {#if row.verdict === 'accepted'}
            accepté
          {:else}
            refusé par le juge{row.verdict_detail ? ` — ${row.verdict_detail}` : ''}
          {/if}
        </div>
        {#if row.excerpt}
          <div>Extrait : « {row.excerpt} »</div>
        {/if}
        {#if row.reason}
          <div>Raison : {row.reason}</div>
        {/if}
        <div>Candidats : {row.candidates.map((c) => c.name).join(', ')}</div>
        <div class="evidence">
          {#if row.excerpt_source === 'facts'}
            {#each row.evidence as item (item.fact_id)}
              <div class="evidence-item">
                <span>{item.content}</span>
                <span class="muted">({item.scopes.map(scopeLabel).join(' ; ')})</span>
              </div>
            {/each}
          {:else if row.excerpt_source === 'declaration'}
            <span class="muted">extrait tiré de la déclaration</span>
          {:else}
            <span class="muted">preuve introuvable</span>
          {/if}
        </div>

        <div class="review-block">
          <label class="record-line">
            <input
              type="checkbox"
              checked={recordFor(row, 'agree')}
              onchange={(e) => setRecord(row, 'agree', e.currentTarget.checked)}
            />
            Enregistrer « {row.surface_form} » comme appellation de {row.chosen.name}
          </label>
          <select value={scopeFor(row, 'agree')} onchange={(e) => setScope(row, 'agree', e.currentTarget.value)}>
            {#each SCOPE_OPTIONS as scope (scope.value)}
              <option value={scope.value}>{scope.label}</option>
            {/each}
          </select>
          <div class="choice-actions">
            <button disabled={reviewState.busy[row.id]} onclick={() => agree(row)}>D'accord</button>
          </div>
        </div>

        <div class="review-block">
          <input
            type="search"
            placeholder="Chercher une entité…"
            value={reviewState.query[row.id] || ''}
            oninput={(e) => setQuery(row, e.currentTarget.value)}
          />
          <select value={targetOf(row)} onchange={(e) => setTarget(row, e.currentTarget.value)}>
            <option value="">— choisir —</option>
            <option value={NO_ENTITY}>Aucune entité connue</option>
            {#each disagreeOptions(row) as option (option.id)}
              <option value={option.id}>{option.name} ({option.type})</option>
            {/each}
          </select>
          <label class="record-line">
            <input
              type="checkbox"
              checked={recordFor(row, 'disagree')}
              disabled={targetOf(row) === '' || targetOf(row) === NO_ENTITY}
              onchange={(e) => setRecord(row, 'disagree', e.currentTarget.checked)}
            />
            Enregistrer aussi comme appellation
          </label>
          <select value={scopeFor(row, 'disagree')} onchange={(e) => setScope(row, 'disagree', e.currentTarget.value)}>
            {#each SCOPE_OPTIONS as scope (scope.value)}
              <option value={scope.value}>{scope.label}</option>
            {/each}
          </select>
          <div class="choice-actions">
            <button
              disabled={reviewState.busy[row.id] || targetOf(row) === ''}
              onclick={() => disagree(row)}
            >Pas d'accord</button>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  .choice-line { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--border); padding-top: 8px; }
  .choice-head { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .badge { font-size: 11px; border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; color: var(--muted); }
  .excerpt { margin: 0; white-space: pre-wrap; }
  .evidence { display: flex; flex-direction: column; gap: 2px; }
  .evidence-item { display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
  .review-block { display: flex; flex-direction: column; gap: 6px; border: 1px solid var(--border); padding: 8px; }
  .record-line { display: flex; align-items: center; gap: 6px; }
  .choice-actions { display: flex; gap: 6px; }
</style>
