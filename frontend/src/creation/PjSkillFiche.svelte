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

     skillSaveTier's route (PATCH /api/skills/{id}) is untouched by this
     port -- confirmed neither role_capacity_chokepoint.py nor
     role_closed_vocab.py greps index.html or mentions "skill", so no
     re-homing is triggered.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { creationState } from './state.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import { api } from './sheetRequest.svelte.js';

  const SKILL_DOMAIN_LABELS = {
    physical: 'Physical', agility: 'Agility',
    perception: 'Perception', composure: 'Composure',
  };
  const SKILL_TIER_LABELS = {
    '-1': '-1 · Weak', '0': '0 · Average', '1': '+1 · Trained', '2': '+2 · Exceptional',
  };

  let characters = $state([]);
  let characterId = $state(null);
  let loadError = $state('');
  let rows = $state([]);
  let rowsLoading = $state(false);
  let rowsError = $state('');
  let playerMode = $state(false);

  async function selectCharacter(id) {
    characterId = id;
    rowsLoading = true;
    rowsError = '';
    try {
      rows = await api(`/api/skills?character_id=${encodeURIComponent(id)}`);
    } catch (e) {
      rows = [];
      rowsError = e.message;
    }
    rowsLoading = false;
  }

  async function loadCharacters() {
    let fetched;
    try {
      fetched = await api('/api/skills/player-characters');
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

  async function saveTier(skillId, tier) {
    try {
      const updated = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier: Number(tier) }),
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
  <h2 style="font-size:12px">Fiche de compétences</h2>
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
  {:else if rows.length === 0}
    <div class="empty">No skill rows for this character.</div>
  {:else}
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
            <input type="text" value={SKILL_TIER_LABELS[String(s.tier)] || s.tier} disabled>
          {:else}
            <select onchange={(ev) => saveTier(s.id, ev.currentTarget.value)}>
              {#each [-1, 0, 1, 2] as t}
                <option value={t} selected={t === s.tier}>{SKILL_TIER_LABELS[String(t)]}</option>
              {/each}
            </select>
          {/if}
        </div>
      {/each}
    </div></div>
  {/if}
</div>
