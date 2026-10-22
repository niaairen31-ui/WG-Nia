<script>
  /* TICKET-0124 (BRIEF-0124-H, L1/H1). One pending germ, opened from the
     entity list's « En attente » group, alone in the right column: where it
     comes from, « Générer la fiche », and -- for a character -- « C'est
     quelqu'un qui existe ? »: the characters it could be (GET /candidates)
     or any other character of the world, each to « Rattacher » (POST
     /attach, no new entity) or to « Créer et lier » (the generated draft
     then links to that character, germLinkTarget, brief I). Its
     CREATION_ISLANDS entry declares origin 'new'. No dialog: every outcome
     shows on the status line. */
  import { creationState } from './state.svelte.js';
  import { attachGerm, generatePendingCreation, loadGermCandidates } from './tabs.js';

  const SOURCE_LABELS = { tick: 'TICK', journee: 'JOURNÉE', creation: 'BROUILLON', conversation: 'CONVERSATION' };

  let candidates = $state([]);
  let status = $state('');
  let picked = $state('');
  let loadSeq = 0;

  const germ = $derived(creationState.pendingCreations.find(g => g.mutation_id === creationState.selectedGermId));
  const others = $derived(
    creationState.entities
      .filter(e => e.type === 'character' && !creationState.playerCharIds.has(e.id))
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name)),
  );

  $effect(() => {
    const id = creationState.selectedGermId;
    const isCharacter = germ?.entity_type === 'character';
    candidates = [];
    status = '';
    picked = '';
    if (!id || !isCharacter) return;
    const seq = ++loadSeq;
    loadGermCandidates(id)
      .then((list) => { if (seq === loadSeq) candidates = list || []; })
      .catch((e) => { if (seq === loadSeq) status = `Erreur : ${e.message}`; });
  });

  async function attach(entityId) {
    if (!germ || !entityId) return;
    status = '';
    try {
      await attachGerm(germ.mutation_id, entityId);
    } catch (e) {
      status = `Erreur : ${e.message}`;
    }
  }

  function createAndLink(entityId, name) {
    if (!germ || !entityId) return;
    creationState.germLinkTarget = { entity_id: entityId, name };
    generatePendingCreation(germ.mutation_id);
  }

  function pickedName() {
    return others.find(e => e.id === picked)?.name ?? '';
  }
</script>

{#if !germ}
  <div class="empty">Aucun germe sélectionné.</div>
{:else}
  <div class="row-card">
    <div style="display:flex; justify-content:space-between; align-items:baseline; gap:8px">
      <strong>{germ.name || '(sans nom)'}</strong>
      <span class="badge b-other" style="font-size:10px">{SOURCE_LABELS[germ.source] ?? 'CONVERSATION'}</span>
    </div>
    {#if germ.concept}<div style="font-size:12px; color:var(--muted)">{germ.concept}</div>{/if}
    {#if germ.anchor_name}<div style="font-size:12px">Lieu : {germ.anchor_name}</div>{/if}
    {#if germ.source_sentence}<div style="font-size:12px">Mentionné ainsi : « {germ.source_sentence} »</div>{/if}
    {#if germ.origin_name}<div style="font-size:12px">Lié à {germ.origin_name}{germ.link_type ? ` (${germ.link_type})` : ''}</div>{/if}
    {#if !germ.entity_type}<span class="badge b-other" style="font-size:10px; border-color:var(--red); color:var(--red)">type inconnu</span>{/if}
    <div class="row-card-actions">
      {#if germ.entity_type}
        <button class="btn-send" onclick={() => generatePendingCreation(germ.mutation_id)}>Générer la fiche</button>
      {/if}
    </div>
  </div>

  {#if germ.entity_type === 'character'}
    <div class="field-section">
      <div class="field-section-title">C'est quelqu'un qui existe ?</div>
      {#if candidates.length === 0}
        <div style="font-size:12px; color:var(--muted)">Aucun personnage au même lieu ou à un lieu voisin.</div>
      {/if}
      {#each candidates as c (c.entity_id)}
        <div class="row-card">
          <div><strong>{c.name}</strong> <span style="font-size:12px; color:var(--muted)">{c.location_name ?? ''} · {c.reason}</span></div>
          <div class="row-card-actions">
            <button class="btn-send" onclick={() => attach(c.entity_id)}>Rattacher</button>
            <button class="btn-ghost" onclick={() => createAndLink(c.entity_id, c.name)}>Créer et lier</button>
          </div>
        </div>
      {/each}
      <div class="row-card">
        <select bind:value={picked}>
          <option value="">— un autre personnage —</option>
          {#each others as e (e.id)}
            <option value={e.id}>{e.name}</option>
          {/each}
        </select>
        <div class="row-card-actions">
          <button class="btn-send" disabled={!picked} onclick={() => attach(picked)}>Rattacher</button>
          <button class="btn-ghost" disabled={!picked} onclick={() => createAndLink(picked, pickedName())}>Créer et lier</button>
        </div>
      </div>
      {#if status}<div style="font-size:12px; color:var(--red)">{status}</div>{/if}
    </div>
  {/if}
{/if}
