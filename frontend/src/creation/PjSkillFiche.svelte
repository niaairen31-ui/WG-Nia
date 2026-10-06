<script>
  /* TICKET-0059 (BRIEF-0059-j commit 4, final). Faithful port of skillInit/
     skillLoadCharacters/skillSelectCharacter/skillRender/skillSaveTier/
     pjFicheOnSelect (index.html, now deleted) -- the Fiche (player skill
     sheet, BRIEF-10) slot on the pj tab.

     Registered as an island on #creation-pj-skill (registry.js), mounted
     alongside entityList/entitySheet whenever the pj tab activates. The
     pj entry's 'fiche' slot descriptor survives with loader/onSelect both
     null (creation_island.py's shape for a converged slot) -- this
     component fetches its own character list on mount/world-switch
     (mirroring NpcAgent.svelte's own serverState.worldId-driven reset,
     replacing the legacy per-activation loader) and reacts to the
     selected character itself: creationState.selectedEntityId is already
     the Svelte-side equivalent of the legacy onSelect signal
     (sheetState.svelte.js's selectEntity writes it), the same
     already-established channel a cross-component "onSelect" needs.

     skillSaveTier's route (PATCH /api/skills/{id}, body {rank} since
     TICKET-0106) was untouched by this port -- confirmed neither role_capacity_chokepoint.py nor
     role_closed_vocab.py greps index.html or mentions "skill", so no
     re-homing is triggered.

     TICKET-0107 (BRIEF-0107-C): the same fiche serves the npc tab (an
     island of both entries; its character list follows activeTabKey). A
     player's master skills he was never taught are listed under « À
     apprendre » with their masters; « Apprendre » grants the row at
     Inexpérimenté (rank 0), from a master or without one (the creator's
     bypass). An NPC lists every skill it lacks under « Ajouter », at the
     rank the creator picks.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { creationState } from './state.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import { api } from './sheetRequest.svelte.js';

  const SKILL_DOMAIN_LABELS = {
    physical: 'Physical', agility: 'Agility',
    perception: 'Perception', composure: 'Composure',
  };
  // TICKET-0106 (BRIEF-0106-A): a skill row carries a rank (0-5); its
  // name is the world's (GET /api/skill-ranks), never a literal here.

  let ranks = $state([]);
  let characters = $state([]);
  let characterId = $state(null);
  let loadError = $state('');
  let rows = $state([]);
  let rowsLoading = $state(false);
  let rowsError = $state('');
  let playerMode = $state(false);
  let learnable = $state([]);
  let teacherFor = $state({}); // learnable key -> chosen master id ('' = without a master)
  let rankFor = $state({}); // learnable key -> rank for an NPC grant
  let grantError = $state('');

  const characterType = $derived(creationState.activeTabKey === 'npc' ? 'npc' : 'player');

  function learnKey(entry) {
    return entry.skill_definition_id || `domain:${entry.domain}`;
  }

  async function selectCharacter(id) {
    characterId = id;
    rowsLoading = true;
    rowsError = '';
    grantError = '';
    try {
      rows = await api(`/api/skills?character_id=${encodeURIComponent(id)}`);
      learnable = await api(`/api/skills/learnable?character_id=${encodeURIComponent(id)}`);
    } catch (e) {
      rows = [];
      learnable = [];
      rowsError = e.message;
    }
    rowsLoading = false;
  }

  async function loadCharacters() {
    let fetched;
    try {
      ranks = await api('/api/skill-ranks');
      fetched = await api(`/api/skills/player-characters?character_type=${characterType}`);
      loadError = '';
    } catch (e) {
      characters = [];
      loadError = e.message;
      return;
    }
    characters = fetched;
    if (fetched.length === 0) return;
    if (!characterId || !fetched.some((c) => c.id === characterId)) {
      characterId = fetched[0].id;
    }
    await selectCharacter(characterId);
  }

  // World switch (TICKET-0056 C3, mirrors NpcAgent.svelte/LinkAgent.svelte):
  // the active world is server-authoritative, so this island refetches its
  // own character list reactively rather than being told to by a legacy
  // per-activation loader.
  $effect(() => {
    void serverState.worldId;
    void characterType;
    characterId = null;
    rows = [];
    loadCharacters();
  });

  // pjFicheOnSelect's replacement: a clicked entity-list row writes
  // creationState.selectedEntityId (sheetState.svelte.js's selectEntity);
  // this reacts to that the same way EntityList.svelte's own row highlight
  // does, syncing the dropdown to whichever player character was clicked --
  // but only once the character list itself has loaded, matching the
  // legacy pjFicheOnSelect's own precondition (it set the dropdown's
  // .value directly, a no-op if the option didn't exist yet).
  $effect(() => {
    const id = creationState.selectedEntityId;
    if (id && characters.some((c) => c.id === id) && id !== characterId) {
      selectCharacter(id);
    }
  });

  function onCharacterChange(ev) {
    selectCharacter(ev.currentTarget.value);
  }

  // TICKET-0106 (BRIEF-0106-D): the points earned within the rank, out of
  // the points needed to leave it (null at the top rank).
  function pointsLine(s) {
    return s.points_to_next == null ? `${s.xp} pt · rang maximal` : `${s.xp} / ${s.points_to_next} pts`;
  }

  async function grant(entry) {
    grantError = '';
    const key = learnKey(entry);
    const body = {
      character_id: characterId,
      skill_definition_id: entry.skill_definition_id,
      domain: entry.skill_definition_id ? null : entry.domain,
      rank: characterType === 'player' ? 0 : Number(rankFor[key] ?? 1),
      taught_by_id: teacherFor[key] || null,
    };
    try {
      await api('/api/skills', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      await selectCharacter(characterId);
    } catch (e) {
      grantError = e.message;
    }
  }

  async function saveRank(skillId, rank) {
    try {
      const updated = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rank: Number(rank) }),
      });
      const idx = rows.findIndex((s) => s.id === skillId);
      if (idx !== -1) rows[idx] = updated;
    } catch (e) {
      alert(e.message);
      await selectCharacter(characterId); // reload to discard the failed edit
    }
  }
</script>

<div class="panel-head" style="flex-shrink:0; border-top:2px solid var(--border)">
  <h2 style="font-size:12px">Fiche de compétences{characterType === 'npc' ? ' (PNJ)' : ''}</h2>
  <select value={characterId ?? ''} onchange={onCharacterChange}>
    {#each characters as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
  </select>
  <label class="field-row checkbox" style="margin:0">
    <input type="checkbox" bind:checked={playerMode}>
    <span style="font-size:12px">Mode joueur</span>
  </label>
  <button class="btn-icon" onclick={loadCharacters} title="Rafraîchir">↻</button>
</div>
<div class="author-main" style="overflow-y:auto">
  {#if loadError}
    <div class="empty">{loadError}</div>
  {:else if characters.length === 0}
    <div class="empty">No player characters yet.</div>
  {:else if rowsLoading}
    <div class="empty"><span class="spin">⟳</span></div>
  {:else if rowsError}
    <div class="empty">{rowsError}</div>
  {:else}
    {#if rows.length === 0}
      <div class="empty">{characterType === 'npc' ? 'Aucune compétence : Initié dans chaque domaine de base.' : 'Aucune compétence.'}</div>
    {/if}
    <div class="field-section"><div class="field-grid">
      {#each rows as s (s.id)}
        <div class="field-row">
          <label>
            {#if s.definition_name}
              {s.definition_name}<br><small style="font-weight:normal;color:var(--muted)">{SKILL_DOMAIN_LABELS[s.domain] || s.domain}</small>
            {:else}
              {SKILL_DOMAIN_LABELS[s.domain] || s.domain}
            {/if}
          </label>
          {#if playerMode}
            <input type="text" value={s.rank_label} disabled>
          {:else}
            <select onchange={(ev) => saveRank(s.id, ev.currentTarget.value)}>
              {#each ranks as r (r.rank)}
                <option value={r.rank} selected={r.rank === s.rank}>{r.label}</option>
              {/each}
            </select>
          {/if}
          <small style="color:var(--muted)">{pointsLine(s)}{s.taught_by_name ? ` · enseignée par ${s.taught_by_name}` : (s.requires_master ? ' · accordée sans maître' : '')}</small>
        </div>
      {/each}
    </div></div>
    {#if learnable.length && !playerMode}
      <div class="field-section">
        <div style="font-size:12px; font-weight:600; margin-bottom:4px">
          {characterType === 'player' ? 'À apprendre (exige un maître)' : 'Compétences à donner'}
        </div>
        {#each learnable as entry (learnKey(entry))}
          <div class="field-row" style="display:flex; gap:6px; align-items:center; flex-wrap:wrap">
            <span style="min-width:120px">{SKILL_DOMAIN_LABELS[entry.name] || entry.name}</span>
            <select title="Maître" onchange={(ev) => { teacherFor[learnKey(entry)] = ev.currentTarget.value; }}>
              <option value="">Sans maître (créatrice)</option>
              {#each entry.masters.filter((m) => m.id !== characterId) as m (m.id)}
                <option value={m.id}>{m.name}</option>
              {/each}
            </select>
            {#if characterType === 'npc'}
              <select title="Rang" onchange={(ev) => { rankFor[learnKey(entry)] = ev.currentTarget.value; }}>
                {#each ranks as r (r.rank)}
                  <option value={r.rank} selected={r.rank === 1}>{r.label}</option>
                {/each}
              </select>
            {/if}
            <button class="btn-ghost" onclick={() => grant(entry)}>{characterType === 'player' ? 'Apprendre' : 'Ajouter'}</button>
          </div>
        {/each}
        {#if grantError}<div style="color:var(--red); font-size:12px">{grantError}</div>{/if}
      </div>
    {/if}
  {/if}
</div>
