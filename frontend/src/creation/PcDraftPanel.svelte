<script>
  /* TICKET-0126 (BRIEF-0126-I, C-15, W1'). One submitted character draft,
     opened from the PJ list's « Soumis » group, alone in the right column:
     the player's story, skills, people, starting place, memberships and
     knowledge, and the verdict of its sheet. Read only -- the review is
     TICKET-0129. Its CREATION_ISLANDS entry declares origin 'new'. */
  import { creationState } from './state.svelte.js';
  import { loadPcDraft } from './pcDrafts.svelte.js';

  const KINDS = { family: 'Famille', master: 'Maître', faction: 'Faction', other: 'Autre' };
  const LEVELS = { rumor: 'Rumeur', suspicious: 'Soupçon', partial: 'Partielle', knows: 'Sait' };

  let detail = $state(null);
  let status = $state('');
  let loadSeq = 0;

  $effect(() => {
    const id = creationState.selectedPcDraftId;
    const seq = ++loadSeq;
    if (!id) return;
    detail = null;
    status = '';
    loadPcDraft(id).then(
      (body) => { if (seq === loadSeq) detail = body; },
      (err) => { if (seq === loadSeq) status = err.message; },
    );
  });

  function rankLabel(rank) {
    return rank === null || rank === undefined ? '—' : (detail.ranks[rank] ?? String(rank));
  }

  function skillName(key) {
    return detail.skill_names[key] ?? key;
  }
</script>

<div class="pc-draft-panel">
  <div class="panel-head">
    <span>Personnage soumis</span>
    <button class="btn-ghost" onclick={() => { creationState.selectedPcDraftId = null; }}>Fermer</button>
  </div>
  {#if status}
    <div class="status">{status}</div>
  {/if}
  {#if detail}
    {@const draft = detail.draft}
    <h3>{draft.name || '(sans nom)'}</h3>
    <div class="meta">
      {detail.player_name ?? '?'} · soumis le {draft.submitted_at ? new Date(draft.submitted_at).toLocaleString('fr-FR') : '?'}
    </div>

    <h4>Son histoire</h4>
    <p class="story">{draft.story}</p>

    <h4>Compétences</h4>
    {#if draft.skills.length === 0}
      <div class="muted">Les rangs de départ, inchangés.</div>
    {:else}
      <ul>
        {#each draft.skills as s (s.skill_key)}
          <li>
            <strong>{skillName(s.skill_key)}</strong> : {rankLabel(s.player_rank)}
            {#if s.designer_rank !== null && s.designer_rank !== s.player_rank}
              <span class="muted">(concepteur : {rankLabel(s.designer_rank)})</span>
            {/if}
            {#if s.justification}<div class="muted">{s.justification}</div>{/if}
          </li>
        {/each}
      </ul>
    {/if}

    <h4>Personnes</h4>
    {#if draft.sketches.length === 0}
      <div class="muted">Aucune.</div>
    {:else}
      <ul>
        {#each draft.sketches as p (p.id)}
          <li>
            <strong>{p.name}</strong> · {KINDS[p.kind] ?? p.kind}{p.kind === 'master' && p.skill_key ? ` (${skillName(p.skill_key)})` : ''}
            {#if p.role} — {p.role}{/if}
            {#if p.group_label}<span class="muted"> · {p.group_label}</span>{/if}
            {#if p.existing_entity}<span class="muted"> · personne existante : {p.existing_entity.name}</span>{/if}
            {#if p.sentence}<div class="muted">{p.sentence}</div>{/if}
          </li>
        {/each}
      </ul>
    {/if}

    <h4>Lieu de départ</h4>
    <div>{draft.start_location ? draft.start_location.name : '—'}</div>

    <h4>Appartenances</h4>
    {#if draft.memberships.length === 0}
      <div class="muted">Aucune.</div>
    {:else}
      <ul>
        {#each draft.memberships as m (m.id)}
          <li>{m.faction_name}{m.role ? ` (${m.role})` : ''}</li>
        {/each}
      </ul>
    {/if}

    <h4>Connaissances</h4>
    {#if draft.knowledge.length === 0}
      <div class="muted">Aucune.</div>
    {:else}
      <ul>
        {#each draft.knowledge as k (k.id)}
          <li><span class="muted">{LEVELS[k.level] ?? k.level} :</span> {k.content}</li>
        {/each}
      </ul>
    {/if}

    <h4>Vérification</h4>
    {#if detail.verdict.violations.length === 0}
      <div>Aucune règle enfreinte.</div>
    {:else}
      <ul class="violations">
        {#each detail.verdict.violations as v, i (i)}
          <li>{v.message}</li>
        {/each}
      </ul>
    {/if}

    <p class="muted notice">La revue de la créatrice arrive avec un prochain ticket : rien n'est encore écrit au monde.</p>
  {:else if !status}
    <div class="muted"><span class="spin">⟳</span></div>
  {/if}
</div>

<style>
  .panel-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .meta, .muted { color: var(--muted); font-size: 12px; }
  .story { white-space: pre-wrap; }
  h4 { margin: 14px 0 4px; }
  ul { padding-left: 18px; margin: 0; }
  .violations, .status { color: var(--red); }
  .notice { margin-top: 16px; font-style: italic; }
</style>
