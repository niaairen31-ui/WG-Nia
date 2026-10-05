<script>
  /* TICKET-0098 (BRIEF-0098-F). The writing panel ("Écrire") of the Lore
     shell: the creator writes lore in prose, answers at most one round of
     questions, corrects the proposal and commits it. A second bounded
     reopening of the shell's read-only lock (H1); the consultation view is
     untouched. Every entity is chosen from a list. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    writeState, ENTITY_TYPES, SCOPE_TYPES, LEVELS, reloadForWorld, askQuestions, makeDraft,
    pickExisting, refLabel, liveRefs, scopeOptions, scopeValue, pickScope, setScopeType,
    addKnower, addDefault, removeAt, blockers,
    commit, restart, loadEntries, worldEntity,
  } from './writePanel.svelte.js';

  let { visible = false } = $props();

  const ACTION_LABEL = Object.freeze({
    create: 'Fait nouveau', existing: 'Fait existant — ajouts', rewrite: 'Fait existant — réécrit',
  });
  const STATUS_LABEL = Object.freeze({
    matched: 'connue', ambiguous: 'plusieurs possibles', new: 'nouvelle',
  });

  let blocking = $derived(writeState.stage === 'draft' ? blockers() : []);

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });

  // Declared after the reset above, so a world change clears then reloads.
  $effect(() => {
    void serverState.worldId;
    if (visible) loadEntries().catch(() => {});
  });
</script>

<div class="queue-panel" id="lore-write-panel">
  <div class="panel-head">
    <h2>Lore — écrire</h2>
    {#if writeState.stage !== 'text'}
      <button disabled={writeState.busy} onclick={() => restart()}>Recommencer</button>
    {/if}
  </div>
  <div class="queue-body">
    {#if writeState.error}
      <div class="r-err">{writeState.error}</div>
    {/if}

    <textarea
      bind:value={writeState.statement}
      rows="5"
      placeholder="Ex : la reine possède le manoir et déteste qu'on lui coupe la parole."
      disabled={writeState.busy || writeState.stage !== 'text'}
    ></textarea>
    {#if writeState.stage === 'text'}
      <div>
        <button disabled={writeState.busy || !writeState.statement.trim()} onclick={() => askQuestions()}>
          {writeState.busy ? '⟳ Lecture…' : 'Proposer des faits'}
        </button>
      </div>
    {/if}

    {#if writeState.stage === 'questions'}
      <div class="write-questions">
        <strong>Quelques précisions :</strong>
        <ol>
          {#each writeState.questions as question, i (i)}<li>{question}</li>{/each}
        </ol>
        <textarea bind:value={writeState.answers} rows="3" placeholder="Tes réponses (facultatif)"
          disabled={writeState.busy}></textarea>
        <div class="row">
          <button disabled={writeState.busy} onclick={() => makeDraft()}>
            {writeState.busy ? '⟳ Rédaction…' : 'Rédiger la proposition'}
          </button>
          <button disabled={writeState.busy} onclick={() => { writeState.answers = ''; makeDraft(); }}>
            Passer
          </button>
        </div>
      </div>
    {/if}

    {#if writeState.stage === 'draft' && writeState.draft}
      {@const draft = writeState.draft}
      {#each draft.notes as note, i (i)}<div class="muted">{note}</div>{/each}

      <h3>Entités</h3>
      {#each draft.entities as entity (entity.ref)}
        <div class="card">
          <strong>« {entity.name} »</strong>
          <span class="muted">{STATUS_LABEL[entity.status] || ''}</span>
          {#if entity.decision === 'existing'}
            → {worldEntity(entity.entity_id)?.name || entity.name}
          {/if}
          <div class="row">
            <select value={entity.decision === 'existing' ? entity.entity_id : ''}
              onchange={(e) => pickExisting(entity, e.currentTarget.value)}>
              <option value="">— rattacher à une entité existante —</option>
              {#each entity.candidates || [] as c (c.entity_id)}
                <option value={c.entity_id}>{c.name} ({c.type}) — candidat</option>
              {/each}
              {#each entity.near || [] as c (c.entity_id)}
                <option value={c.entity_id}>{c.name} ({c.type}) — proche {c.score}</option>
              {/each}
              {#each writeState.entities || [] as c (c.id)}
                <option value={c.id}>{c.name} ({c.type})</option>
              {/each}
            </select>
            <label><input type="radio" checked={entity.decision === 'create'}
              onchange={() => { entity.decision = 'create'; entity.action = 'create'; entity.entity_id = undefined; }} />
              Créer</label>
            {#if entity.decision === 'create'}
              <select bind:value={entity.type}>
                <option value={null}>— type —</option>
                {#each ENTITY_TYPES as t (t.value)}<option value={t.value}>{t.label}</option>{/each}
              </select>
            {/if}
            <label><input type="radio" checked={entity.decision === 'text'}
              onchange={() => (entity.decision = 'text')} /> Garder en texte</label>
          </div>
        </div>
      {/each}

      <h3>Faits</h3>
      {#each draft.facts as fact, fi (fact.ref)}
        <div class="card">
          <div class="row"><strong>{ACTION_LABEL[fact.action]}</strong>
            <button onclick={() => removeAt(draft.facts, fi)}>Retirer</button></div>
          {#if fact.action !== 'existing'}
            <textarea bind:value={fact.content} rows="2"></textarea>
          {/if}
          {#if fact.action === 'rewrite'}
            <div class="row">
              <label><input type="radio" checked={fact.kind === 'correction'}
                onchange={() => (fact.kind = 'correction')} /> Correction</label>
              <label><input type="radio" checked={fact.kind === 'changement'}
                onchange={() => (fact.kind = 'changement')} /> Changement dans le monde</label>
            </div>
          {/if}
          {#if fact.action === 'create'}
            <select bind:value={fact.facet}>
              {#each draft.facets as f (f.name)}<option value={f.name}>{f.label}</option>{/each}
            </select>
          {/if}
          <div class="row">Concerne :
            {#each fact.participants as ref, pi (ref)}
              <span class="chip">{refLabel(ref)} <button onclick={() => removeAt(fact.participants, pi)}>×</button></span>
            {:else}<span class="muted">le monde entier</span>{/each}
          </div>
          <div>Qui le sait par défaut :</div>
          {#each fact.defaults as scope, si (si)}
            <div class="row">
              <select value={scope.scope_type} onchange={(e) => setScopeType(scope, e.currentTarget.value)}>
                {#each SCOPE_TYPES as s (s.value)}<option value={s.value}>{s.label}</option>{/each}
              </select>
              {#if scope.scope_type !== 'world'}
                <select value={scopeValue(scope)} onchange={(e) => pickScope(scope, e.currentTarget.value)}>
                  <option value="">— choisir —</option>
                  {#each scopeOptions(scope.scope_type) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
                </select>
              {/if}
              <button onclick={() => removeAt(fact.defaults, si)}>×</button>
            </div>
          {/each}
          <button onclick={() => addDefault(fact)}>+ portée</button>
          <div>Qui le sait précisément :</div>
          {#each fact.knowers as knower, ki (knower.entity_ref)}
            <div class="row">
              {refLabel(knower.entity_ref)}
              <select bind:value={knower.level}>
                {#each LEVELS as l (l)}<option value={l}>{l}</option>{/each}
              </select>
              <label><input type="checkbox" bind:checked={knower.is_secret} /> secret</label>
              <label><input type="checkbox" bind:checked={knower.is_incorrect} /> croyance fausse</label>
              <button onclick={() => removeAt(fact.knowers, ki)}>×</button>
            </div>
          {/each}
          <select value="" onchange={(e) => { addKnower(fact, e.currentTarget.value); e.currentTarget.value = ''; }}>
            <option value="">+ ajouter une personne qui le sait…</option>
            {#each (writeState.entities || []).filter((e) => e.type === 'character') as c (c.id)}
              <option value={c.id}>{c.name}</option>
            {/each}
          </select>
        </div>
      {/each}

      {#if draft.memberships.length || draft.controls.length}
        <h3>Appartenances et possessions</h3>
        {#each draft.memberships as m, mi (mi)}
          <div class="row">{refLabel(m.entity_ref)} entre dans {refLabel(m.faction_ref)}
            <button onclick={() => removeAt(draft.memberships, mi)}>×</button></div>
        {/each}
        {#each draft.controls as c, ci (ci)}
          <div class="row">{refLabel(c.owner_ref)} possède {refLabel(c.location_ref)}
            <button onclick={() => removeAt(draft.controls, ci)}>×</button></div>
        {/each}
      {/if}

      {#each blocking as b, i (i)}<div class="r-err">{b}</div>{/each}
      <div class="row">
        <button disabled={writeState.busy || blocking.length > 0} onclick={() => commit()}>
          {writeState.busy ? '⟳ Écriture…' : 'Écrire dans le monde'}
        </button>
        <button disabled={writeState.busy} onclick={() => makeDraft()}>Relancer la proposition</button>
      </div>
      <span class="muted">{liveRefs().length} entité(s) retenue(s)</span>
    {/if}

    {#if writeState.stage === 'done' && writeState.result}
      <div class="card">
        <strong>Écrit.</strong>
        {#each Object.entries(writeState.result.written) as [key, n] (key)}<div>{key} : {n}</div>{/each}
        {#each writeState.result.skipped as s, i (i)}<div class="muted">déjà présent : {s}</div>{/each}
      </div>
    {/if}

    <details class="write-history">
      <summary>Histoires écrites ({writeState.entries.length})</summary>
      {#each writeState.entries as entry (entry.id)}
        <div class="card">
          <p class="statement">{entry.statement}</p>
          {#if entry.answers}<p class="muted">Réponses : {entry.answers}</p>{/if}
          <ul>
            {#each entry.rows as row, i (i)}<li>{row.row_table} ({row.action}) — {row.label}</li>{/each}
          </ul>
        </div>
      {/each}
    </details>
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 4px 0; }
  .card { border-top: 1px solid var(--border); padding: 8px 0; display: flex; flex-direction: column; gap: 4px; }
  .chip { border: 1px solid var(--border); border-radius: 10px; padding: 0 6px; }
  .statement { white-space: pre-wrap; margin: 0; }
  h3 { margin: 12px 0 4px; font-size: 13px; }
</style>
