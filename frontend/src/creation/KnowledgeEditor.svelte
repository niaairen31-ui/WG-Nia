<script>
  /* TICKET-0059 (BRIEF-0059-c). Faithful port of the knowledge in-context
     editor -- authorRenderKnowledge/authorRenderKnowledgeForm/
     authorAddKnowledge/authorUpdateKnowledge/authorDeleteKnowledge
     (index.html, now deleted). Same request/refresh/status cycle as
     RelationsEditor, via the shared sheetRequest.svelte.js this brief also
     introduces. */
  import { sheetRequest, api } from './sheetRequest.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';

  let { knowledge, entityId, levelOptions, legacyDoc, onSaved } = $props();

  let rows = $state([]);
  $effect(() => {
    rows = (knowledge || []).map((k) => ({
      id: k.id,
      fact: k.fact_content ?? '',
      level: k.level,
      source: k.source ?? '',
      share_threshold: k.share_threshold,
      is_incorrect: k.is_incorrect,
      is_secret: k.is_secret,
      content: k.content ?? '',
      fact_id: k.fact_id,
      subject_participants: k.subject_participants || [],
    }));
    loadSubjectEntities();
    loadSubjectSuggestions();
  });

  /* TICKET-0087 (BRIEF-0087-d): subject entity binding -- a fact
     participant (`fact_participant`, no role) attached to the knowledge
     row's own fact, through the routes BRIEF-0082-b already exposes
     (POST/DELETE /api/facts/{fact_id}/participants[/{entity_id}]).
     Two lazily-loaded, world-scoped lists shared by every row: the picker's
     candidate entities, and the resolver's suggestion per unbound fact
     (TICKET-0097: GET /api/worlds/{world_id}/unbound-facts, C-08 -- the
     same read the « Sujets » worklist shows; a suggestion exists when the
     resolver found exactly one candidate). Loaded once per world, reset
     when serverState.worldId changes (Registre.svelte's own convention).
     A row shows its fact's text read-only (K1): the fact is what is known,
     the row's content is this entity's version of it. */
  let subjectEntities = $state([]);
  let subjectEntitiesLoaded = false;
  let subjectSuggestions = $state({}); // fact_id -> suggested entity_id
  let subjectSuggestionsLoaded = false;
  let pickerSelections = $state({}); // knowledge row id -> chosen entity_id

  $effect(() => {
    void serverState.worldId;
    subjectEntities = [];
    subjectEntitiesLoaded = false;
    subjectSuggestions = {};
    subjectSuggestionsLoaded = false;
    pickerSelections = {};
  });

  async function loadSubjectEntities() {
    if (subjectEntitiesLoaded) return;
    subjectEntitiesLoaded = true;
    try {
      subjectEntities = (await api('/api/entities')).filter((e) => e.status === 'active');
    } catch (_err) { /* picker still usable, just empty until a retry */ }
  }

  async function loadSubjectSuggestions() {
    if (subjectSuggestionsLoaded || !serverState.worldId) return;
    subjectSuggestionsLoaded = true;
    try {
      const residue = await api(`/api/worlds/${encodeURIComponent(serverState.worldId)}/unbound-facts`);
      const map = {};
      for (const r of residue) {
        if (r.candidates.length === 1) map[r.fact_id] = r.candidates[0].id;
      }
      subjectSuggestions = map;
    } catch (_err) { /* suggestion is advisory only */ }
  }

  function pickerValue(row) {
    if (row.id in pickerSelections) return pickerSelections[row.id];
    return subjectSuggestions[row.fact_id] || '';
  }

  async function bindSubject(row) {
    const entityIdToBind = pickerValue(row);
    if (!entityIdToBind) return;
    await sheetRequest(
      legacyDoc,
      `/api/facts/${encodeURIComponent(row.fact_id)}/participants`,
      'POST',
      JSON.stringify({ entity_id: entityIdToBind }),
      reloadEntity,
    );
  }

  async function unbindSubject(row, participantEntityId) {
    await sheetRequest(
      legacyDoc,
      `/api/facts/${encodeURIComponent(row.fact_id)}/participants/${encodeURIComponent(participantEntityId)}`,
      'DELETE',
      null,
      reloadEntity,
    );
  }

  let newLevel = $state('rumor');
  let newSource = $state('');
  let newShareThreshold = $state(50);
  let newIncorrect = $state(false);
  let newSecret = $state(false);
  let newContent = $state('');

  async function reloadEntity() {
    onSaved(await api(`/api/entities/${encodeURIComponent(entityId)}`));
  }

  async function saveRow(row) {
    const body = JSON.stringify({
      level: row.level,
      source: row.source || null,
      share_threshold: Number(row.share_threshold),
      is_incorrect: row.is_incorrect,
      is_secret: row.is_secret,
      content: row.content || null,
    });
    await sheetRequest(legacyDoc, `/api/knowledge/${encodeURIComponent(row.id)}`, 'PUT', body, reloadEntity);
  }

  async function deleteRow(id) {
    if (!confirm('Permanently delete this knowledge entry?')) return;
    await sheetRequest(legacyDoc, `/api/knowledge/${encodeURIComponent(id)}`, 'DELETE', null, reloadEntity);
  }

  async function addRow() {
    const body = JSON.stringify({
      level: newLevel,
      source: newSource || null,
      share_threshold: Number(newShareThreshold),
      is_incorrect: newIncorrect,
      is_secret: newSecret,
      content: newContent || null,
    });
    const ok = await sheetRequest(legacyDoc, `/api/entities/${encodeURIComponent(entityId)}/knowledge`, 'POST', body, reloadEntity);
    if (ok) {
      newLevel = 'rumor';
      newSource = '';
      newShareThreshold = 50;
      newIncorrect = false;
      newSecret = false;
      newContent = '';
    }
  }
</script>

{#if !knowledge || knowledge.length === 0}
  <div class="empty">No knowledge entries.</div>
{:else}
  <div class="row-table">
    {#each rows as row (row.id)}
      <div class="row-card">
        <div class="field-grid">
          <div class="field-row span-2"><label>Fact</label><div>{row.fact}</div></div>
          <div class="field-row"><label>Level</label>
            <select bind:value={row.level}>
              {#each levelOptions as l}
                <option value={l}>{l}</option>
              {/each}
            </select></div>
          <div class="field-row"><label>Source</label><input type="text" bind:value={row.source}></div>
          <div class="field-row"><label>Share threshold (1-100)</label>
            <input type="number" min="1" max="100" bind:value={row.share_threshold}></div>
          <div class="field-row checkbox">
            <input type="checkbox" id={`kn-incorrect-${row.id}`} bind:checked={row.is_incorrect}>
            <label for={`kn-incorrect-${row.id}`}>Incorrect</label></div>
          <div class="field-row checkbox">
            <input type="checkbox" id={`kn-secret-${row.id}`} bind:checked={row.is_secret}>
            <label for={`kn-secret-${row.id}`}>Secret</label></div>
          <div class="field-row span-2"><label>Content</label><textarea bind:value={row.content}></textarea></div>
          <div class="field-row span-2">
            <label>Subject entity</label>
            {#if row.subject_participants.length > 0}
              <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                {#each row.subject_participants as p (p.entity_id)}
                  <span class="badge b-other">{p.name}{p.role ? ` (${p.role})` : ''}</span>
                  <button class="btn-ghost" onclick={() => unbindSubject(row, p.entity_id)}>Unbind</button>
                {/each}
              </div>
            {:else}
              <div style="display:flex; gap:6px; align-items:center;">
                <select value={pickerValue(row)} onchange={(e) => pickerSelections[row.id] = e.target.value}>
                  <option value="">—</option>
                  {#each subjectEntities as e (e.id)}
                    <option value={e.id}>{e.name} ({e.type})</option>
                  {/each}
                </select>
                <button class="btn-ghost" disabled={!pickerValue(row)} onclick={() => bindSubject(row)}>Bind</button>
              </div>
            {/if}
          </div>
        </div>
        <div class="row-card-actions">
          <button class="btn-ghost" onclick={() => saveRow(row)}>Save</button>
          <button class="btn-end" onclick={() => deleteRow(row.id)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<div class="row-card">
  <div class="field-grid">
    <div class="field-row"><label>Level *</label>
      <select bind:value={newLevel}>
        {#each levelOptions as l}
          <option value={l}>{l}</option>
        {/each}
      </select></div>
    <div class="field-row"><label>Source</label><input type="text" bind:value={newSource}></div>
    <div class="field-row"><label>Share threshold (1-100)</label>
      <input type="number" min="1" max="100" bind:value={newShareThreshold}></div>
    <div class="field-row checkbox"><input type="checkbox" id="kn-new-incorrect" bind:checked={newIncorrect}><label for="kn-new-incorrect">Incorrect</label></div>
    <div class="field-row checkbox"><input type="checkbox" id="kn-new-secret" bind:checked={newSecret}><label for="kn-new-secret">Secret</label></div>
    <div class="field-row span-2"><label>Content *</label><textarea bind:value={newContent}></textarea></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" disabled={!newContent.trim()} onclick={addRow}>Add knowledge</button>
  </div>
</div>
