<script>
  /* TICKET-0059 (BRIEF-0059-c). Faithful port of the knowledge in-context
     editor -- authorRenderKnowledge/authorRenderKnowledgeForm/
     authorAddKnowledge/authorUpdateKnowledge/authorDeleteKnowledge
     (index.html, now deleted). Same request/refresh/status cycle as
     RelationsEditor, via the shared sheetRequest.svelte.js this brief also
     introduces. */
  import { sheetRequest, api } from './sheetRequest.svelte.js';

  let { knowledge, entityId, levelOptions, legacyDoc, onSaved } = $props();

  let rows = $state([]);
  $effect(() => {
    rows = (knowledge || []).map((k) => ({
      id: k.id,
      subject: k.subject,
      level: k.level,
      source: k.source ?? '',
      share_threshold: k.share_threshold,
      is_incorrect: k.is_incorrect,
      is_secret: k.is_secret,
      content: k.content ?? '',
    }));
  });

  let newSubject = $state('');
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
      subject: row.subject,
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
      subject: newSubject,
      level: newLevel,
      source: newSource || null,
      share_threshold: Number(newShareThreshold),
      is_incorrect: newIncorrect,
      is_secret: newSecret,
      content: newContent || null,
    });
    const ok = await sheetRequest(legacyDoc, `/api/entities/${encodeURIComponent(entityId)}/knowledge`, 'POST', body, reloadEntity);
    if (ok) {
      newSubject = '';
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
          <div class="field-row"><label>Subject</label><input type="text" bind:value={row.subject}></div>
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
    <div class="field-row"><label>Subject *</label><input type="text" bind:value={newSubject}></div>
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
    <div class="field-row span-2"><label>Content</label><textarea bind:value={newContent}></textarea></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={addRow}>Add knowledge</button>
  </div>
</div>
