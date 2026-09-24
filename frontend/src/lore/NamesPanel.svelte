<script>
  /* TICKET-0091 (BRIEF-0091-K, Q17d). The name-resolution panel: names left
     plain in canon prose (`unresolved_mention`), each bound to an entity
     ("Lier") or dismissed ("Ignorer"). The one writing corner of the Lore
     shell -- the consultation pipeline stays read-only. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    namesState, loadMentions, optionsFor, setQuery, choose, bindMention, dismissMention,
    reloadForWorld,
  } from './namesPanel.svelte.js';

  let { visible = false } = $props();

  const REASON_LABEL = Object.freeze({ ambigu: 'ambigu', inconnu: 'inconnu' });
  const CATEGORY_LABEL = Object.freeze({ place: 'lieu', person: 'personne', faction: 'faction' });

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });

  // Declared after the reset above, so a world change clears then reloads.
  $effect(() => {
    void serverState.worldId;
    if (visible) loadMentions();
  });
</script>

<div class="queue-panel" id="lore-names-panel">
  <div class="panel-head">
    <h2>Noms à lier</h2>
    <button disabled={namesState.loading} onclick={() => loadMentions()}>
      {namesState.loading ? '⟳' : 'Rafraîchir'}
    </button>
  </div>
  <div class="queue-body">
    {#if namesState.error}
      <div class="r-err">{namesState.error}</div>
    {/if}
    {#if !namesState.loading && namesState.mentions.length === 0}
      <p class="muted">Aucun nom en attente.</p>
    {/if}
    {#each namesState.mentions as mention (mention.id)}
      <div class="mention-line">
        <div class="mention-head">
          <strong>« {mention.surface} »</strong>
          <span class="muted">
            {REASON_LABEL[mention.reason] || mention.reason}{mention.category ? ` · ${CATEGORY_LABEL[mention.category] || mention.category}` : ''}
          </span>
        </div>
        <p class="excerpt">… {mention.excerpt} …</p>
        <input
          type="search"
          placeholder="Chercher une entité…"
          value={namesState.queries[mention.id] || ''}
          oninput={(e) => setQuery(mention.id, e.currentTarget.value)}
        />
        <select
          value={namesState.choices[mention.id] || ''}
          onchange={(e) => choose(mention.id, e.currentTarget.value)}
        >
          <option value="">— choisir —</option>
          {#each optionsFor(mention) as option (option.id)}
            <option value={option.id}>{option.name} ({option.type})</option>
          {/each}
        </select>
        <div class="mention-actions">
          <button
            disabled={namesState.busy[mention.id] || !namesState.choices[mention.id]}
            onclick={() => bindMention(mention.id)}
          >Lier</button>
          <button disabled={namesState.busy[mention.id]} onclick={() => dismissMention(mention.id)}>Ignorer</button>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  .mention-line { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--border); padding-top: 8px; }
  .mention-head { display: flex; gap: 8px; align-items: baseline; }
  .excerpt { margin: 0; white-space: pre-wrap; }
  .mention-actions { display: flex; gap: 6px; }
</style>
