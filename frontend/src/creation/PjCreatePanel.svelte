<script>
  /* TICKET-0059 (BRIEF-0059-j commit 3). Faithful port of pjRenderCreatePanel/
     pcCreateLoadLocations/pcCreateSubmit/pcRenderDraftKnowledge/
     pcGenerateDraft/pcApplyDraft (index.html, now deleted) -- pj's bespoke
     create flow, deliberately NOT the generic field engine: pcCreateSubmit
     posts to /api/characters/player, not /api/entities (the reason this
     panel stays bespoke, per this brief's own note) -- that distinction
     survives the port unchanged.

     Rendered by Sheet.svelte inside its own 'view' mode when
     tabKey === 'pj' && isNew, ahead of the generic entity-create branch
     every other entity-archetype tab (including pj's own VIEW mode -- pj
     has no bespoke sheetRenderer, only this bespoke createPanel) still
     uses.

     Two Play-view side effects the legacy version's post-create tail
     performed (loadBootstrap/loadPlayerName -- refreshing WORLD_ID/
     PLAYER_ID and the Play header's #play-pc-name) are approximated
     without a new legacy_calls.baseline entry (Scope IN item 8: this brief
     adds nothing to it): refreshServerState() (serverState.svelte.js,
     TICKET-0056) is the Svelte shell's own already-established bootstrap
     mirror, reached by a plain Svelte-to-Svelte import; the Play header
     text is a direct legacyDoc DOM write (the same primitive every
     sub-editor already uses via its own legacyDoc prop), not a legacyCall.
     The skill-fiche dropdown refresh (skillLoadCharacters) is deferred to
     this brief's next commit, once it is itself Svelte -- until then the
     newly-created character simply isn't in that still-legacy dropdown
     until the pj tab is re-entered, a narrow one-commit gap.

     The sidebar entity list refresh (creationRefreshList, legacy chrome)
     is replaced by incrementing creationState.entityListActivationTick
     directly -- the exact signal mount.js's own 'island:slot' handler
     already writes on every activation, which EntityList.svelte's $effect
     already reacts to by refetching. Again no new bridge call needed.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { creationState } from './state.svelte.js';
  import { serverState, refreshServerState } from '../lib/serverState.svelte.js';
  import { api } from './sheetRequest.svelte.js';

  let { legacyDoc } = $props();

  let genBrief = $state('');
  let genStatus = $state('');

  let name = $state('');
  let locationId = $state('');
  let description = $state('');
  let appearance = $state('');
  let backstory = $state('');
  let draftKnowledge = $state([]);

  let locations = $state([]);
  let locationsError = $state(false);
  let createStatus = $state('');
  let createStatusIsErr = $state(false);

  async function loadLocations() {
    try {
      const entities = await api('/api/entities?type=location');
      locations = entities.filter((e) => e.world_id === serverState.worldId && e.status !== 'inactive');
      locationsError = false;
    } catch (_e) {
      locations = [];
      locationsError = true;
    }
  }

  // serverState.worldId is already kept current by the shell on every
  // world switch (Header.svelte's activateWorld -> refreshServerState) --
  // unlike the legacy pcCreateLoadLocations, no re-fetch-then-read is
  // needed before filtering, just a reactive read.
  $effect(() => {
    void serverState.worldId;
    loadLocations();
  });

  /** pj's AI creation assistant (BRIEF-52), ported -- pre-fills the SAME
   *  fields below; accept is still submit() unchanged. knowledge[] is
   *  read-only in the draft (I1), rendered read-only further down;
   *  regenerating simply overwrites the fields/knowledge in place, no
   *  separate discard step. */
  async function generate() {
    const brief = genBrief.trim();
    if (!brief) { genStatus = 'Concept requis.'; return; }
    genStatus = 'Génération…';
    try {
      const result = await api('/api/characters/player/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ brief }),
      });
      if (!result.ok) { genStatus = result.error; return; }
      const draft = result.draft;
      name = draft.name ?? '';
      description = draft.description ?? '';
      appearance = draft.appearance ?? '';
      backstory = draft.backstory ?? '';
      draftKnowledge = draft.knowledge || [];
      genStatus = 'Brouillon généré — relisez et éditez avant de créer.';
    } catch (err) {
      genStatus = err.message;
    }
  }

  async function submit() {
    const trimmedName = name.trim();
    createStatusIsErr = false;
    if (!trimmedName) { createStatusIsErr = true; createStatus = 'Le nom est requis.'; return; }
    if (!locationId) { createStatusIsErr = true; createStatus = 'Choisissez un lieu de départ.'; return; }

    createStatus = 'Création…';
    try {
      const result = await api('/api/characters/player', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: trimmedName,
          current_location_id: locationId,
          description: description.trim() || null,
          appearance: appearance.trim() || null,
          backstory: backstory.trim() || null,
          knowledge: draftKnowledge,
        }),
      });
      if (!result.ok) { createStatusIsErr = true; createStatus = result.error || 'Échec de la création.'; return; }

      createStatusIsErr = false;
      createStatus = 'Personnage créé.';
      name = ''; locationId = ''; description = ''; appearance = ''; backstory = '';
      genBrief = ''; genStatus = ''; draftKnowledge = [];

      await refreshServerState();
      if (serverState.playerId) {
        try {
          const entity = await api(`/api/entities/${encodeURIComponent(serverState.playerId)}`);
          const nameEl = legacyDoc.getElementById('play-pc-name');
          if (nameEl) nameEl.textContent = entity.name || serverState.playerId;
        } catch (_e) { /* matches loadPlayerName's own silent catch */ }
      }
      creationState.entityListActivationTick += 1;
    } catch (e) {
      createStatusIsErr = true;
      createStatus = e.message;
    }
  }
</script>

<div class="field-section" style="margin:0; padding:10px 14px">
  <div class="field-row" style="margin:0">
    <label>Concept (pour l'assistant)</label>
    <textarea rows="2" placeholder="Ex. une ancienne contrebandière qui a tout quitté pour..." bind:value={genBrief}></textarea>
  </div>
  <div style="display:flex; gap:10px; align-items:center; margin-top:6px">
    <button class="btn-send" onclick={generate}>Générer le brouillon</button>
    <span class="author-status">{genStatus}</span>
  </div>
</div>
<div class="field-section" style="margin:0; padding:10px 14px; display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap">
  <div class="field-row" style="margin:0; min-width:180px">
    <label>Nom</label>
    <input type="text" placeholder="Nom du personnage" bind:value={name}>
  </div>
  <div class="field-row" style="margin:0; min-width:200px">
    <label>Lieu de départ</label>
    <select bind:value={locationId}>
      <option value="">{locationsError ? '(erreur de chargement)' : '— choisir —'}</option>
      {#each locations as l (l.id)}<option value={l.id}>{l.name}</option>{/each}
    </select>
  </div>
  <button class="btn-send" onclick={submit}>Créer</button>
  <span class="author-status {createStatusIsErr ? 'err' : ''}">{createStatus}</span>
</div>
<div class="field-section" style="margin:0; padding:0 14px 10px">
  <div class="field-row" style="margin:0 0 6px 0">
    <label>Description (publique)</label>
    <textarea rows="2" placeholder="Ce qu'autrui perçoit au premier regard" bind:value={description}></textarea>
  </div>
  <div class="field-row" style="margin:0 0 6px 0">
    <label>Apparence</label>
    <textarea rows="2" placeholder="Référence du joueur" bind:value={appearance}></textarea>
  </div>
  <div class="field-row" style="margin:0 0 6px 0">
    <label>Histoire personnelle</label>
    <textarea rows="3" placeholder="Référence du joueur" bind:value={backstory}></textarea>
  </div>
  <div class="field-row" style="margin:0">
    <label>Savoirs proposés (lecture seule — éditables après création via la Fiche)</label>
    <div style="font-size:12px; color:var(--muted)">
      {#if draftKnowledge.length === 0}
        (aucun)
      {:else}
        {#each draftKnowledge as k}
          <div>{k.subject} ({k.level}) : {k.content}</div>
        {/each}
      {/if}
    </div>
  </div>
</div>
