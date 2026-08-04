<script>
  /* TICKET-0059 (BRIEF-0059-d). Faithful port of the location discoverable-
     details sub-editor -- authorLoadDiscDetails/authorRenderDiscDetails/
     authorRenderDiscDetailRow/authorRenderDiscDetailForm/authorAddDiscDetail/
     authorDeleteDiscDetail/authorResetDiscDetail/authorEditDiscDetail/
     authorSaveDiscDetail (index.html, now deleted).

     Cluster-native display (schema v1.30, BRIEF-17, decision C1) is
     unchanged: rows sharing a signpost_group render together under a group
     header (ambient/hidden counts), ungrouped rows render individually.

     The per-row edit-mode machine becomes component state, not a DOM
     convention: legacy's authorEditDiscDetail re-fetched the full list and
     overwrote one row's innerHTML in place; here a row holds its own
     `editingId === d.id` check against a single module-scoped id plus a
     `draft` object, initialized from the already-loaded `rows` state (no
     redundant round-trip -- the data was already fresh from the last load,
     which happens after every mutation same as before). "Cancel" reverts to
     display mode without a network call, since `rows` itself was never
     mutated by the draft -- equivalent to legacy's authorLoadDiscDetails()
     reload, just without re-fetching data nothing changed.

     Status lines are per-row/per-form local state (`#disc-add-status`/
     `#disc-edit-status-{id}` in legacy), never the shared `#author-status`
     header -- this sub-editor never touched that line, so no legacyDoc/
     sheetRequest dependency is needed here, unlike Relations/Knowledge/Goals. */
  let { entityId, worldId } = $props();

  let rows = $state([]);
  let loadError = $state('');

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  async function load() {
    try {
      rows = await api(`/api/locations/${encodeURIComponent(entityId)}/discoverable-details`);
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => { load(); });

  const groups = $derived.by(() => {
    const grouped = new Map();
    const ungrouped = [];
    for (const d of rows) {
      if (d.signpost_group) {
        if (!grouped.has(d.signpost_group)) grouped.set(d.signpost_group, []);
        grouped.get(d.signpost_group).push(d);
      } else {
        ungrouped.push(d);
      }
    }
    return { grouped, ungrouped };
  });

  let editingId = $state(null);
  let draft = $state({});
  let editStatus = $state('');

  function startEdit(d) {
    editingId = d.id;
    draft = {
      subject: d.subject, content: d.content, access_level: d.access_level,
      discovery_threshold: d.discovery_threshold, signpost_group: d.signpost_group || '',
    };
    editStatus = '';
  }

  function cancelEdit() {
    editingId = null;
  }

  async function saveEdit(detailId) {
    const subject = (draft.subject || '').trim();
    const content = (draft.content || '').trim();
    if (!subject || !content) { editStatus = 'Subject and content required.'; return; }
    editStatus = '…';
    try {
      const body = {
        subject, content, access_level: draft.access_level,
        discovery_threshold: draft.discovery_threshold || 0,
      };
      const signpostRaw = (draft.signpost_group || '').trim();
      if (signpostRaw) body.signpost_group = signpostRaw;
      else body.clear_signpost_group = true;
      await api(`/api/discoverable-details/${encodeURIComponent(detailId)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      editingId = null;
      await load();
    } catch (e) {
      editStatus = e.message;
    }
  }

  async function deleteRow(detailId) {
    if (!confirm('Delete this discoverable detail?')) return;
    try {
      await api(`/api/discoverable-details/${encodeURIComponent(detailId)}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      alert(e.message);
    }
  }

  async function resetRow(detailId) {
    try {
      await api(`/api/discoverable-details/${encodeURIComponent(detailId)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ discovered: false }),
      });
      await load();
    } catch (e) {
      alert(e.message);
    }
  }

  let newSubject = $state('');
  let newContent = $state('');
  let newAccessLevel = $state('hidden');
  let newThreshold = $state(0);
  let newSignpost = $state('');
  let addStatus = $state('');

  async function addRow() {
    const subject = newSubject.trim();
    const content = newContent.trim();
    if (!subject || !content) { addStatus = 'Subject and content required.'; return; }
    addStatus = '…';
    try {
      await api(`/api/locations/${encodeURIComponent(entityId)}/discoverable-details`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: worldId, subject, content, access_level: newAccessLevel,
          discovery_threshold: newThreshold || 0, signpost_group: newSignpost.trim() || null,
        }),
      });
      newSubject = '';
      newContent = '';
      newThreshold = 0;
      newSignpost = '';
      addStatus = 'Added.';
      await load();
    } catch (e) {
      addStatus = e.message;
    }
  }
</script>

{#snippet detailRow(d)}
  <div class="row-card" id={`disc-row-${d.id}`}>
    {#if editingId === d.id}
      <div class="field-grid" style="margin-bottom:6px">
        <div class="field-row"><label>Subject</label><input type="text" bind:value={draft.subject}></div>
        <div class="field-row" style="grid-column:1/-1"><label>Content</label>
          <textarea rows="3" style="resize:vertical" bind:value={draft.content}></textarea></div>
        <div class="field-row"><label>Access level</label>
          <select bind:value={draft.access_level}>
            <option value="hidden">hidden</option>
            <option value="ambient">ambient (dormant)</option>
          </select></div>
        <div class="field-row"><label>Threshold (0–12)</label>
          <input type="number" min="0" max="12" bind:value={draft.discovery_threshold}></div>
        <div class="field-row"><label>signpost_group (optional)</label>
          <input type="text" bind:value={draft.signpost_group} placeholder="e.g. papiers_bureau"></div>
      </div>
      <div style="display:flex; gap:6px; align-items:center;">
        <button class="btn-send" style="font-size:12px" onclick={() => saveEdit(d.id)}>Save</button>
        <button class="btn-ghost" style="font-size:12px" onclick={cancelEdit}>Cancel</button>
        <span style="font-size:12px; color:var(--muted)">{editStatus}</span>
      </div>
    {:else}
      <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;">
        <span style="font-weight:600">{d.subject}</span>
        <span style="display:flex; align-items:center; gap:6px;">
          <span class="badge b-other">{d.access_level}</span>
          <span class="badge {d.discovered ? 'b-equipped' : 'b-stowed'}">{d.discovered ? 'discovered' : 'hidden'}</span>
          <span style="color:var(--muted); font-size:12px;">threshold {d.discovery_threshold}</span>
        </span>
      </div>
      <div style="color:var(--text); font-size:13px; margin:4px 0 6px; white-space:pre-wrap;">{d.content}</div>
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button class="btn-ghost" style="font-size:12px" onclick={() => startEdit(d)}>Edit</button>
        <button class="btn-end" style="font-size:12px; padding:3px 8px" onclick={() => deleteRow(d.id)}>Delete</button>
        {#if d.discovered}
          <button class="btn-ghost" style="font-size:12px" onclick={() => resetRow(d.id)}>Reset discovered</button>
        {/if}
      </div>
    {/if}
  </div>
{/snippet}

{#if loadError}
  <div class="empty">{loadError}</div>
{:else if rows.length === 0}
  <div class="empty">No discoverable details seeded yet.</div>
{:else}
  {#each [...groups.grouped] as [group, groupRows] (group)}
    {@const ambientCount = groupRows.filter((d) => d.access_level === 'ambient').length}
    {@const hiddenCount = groupRows.filter((d) => d.access_level === 'hidden').length}
    <div class="signpost-group" style="border:1px solid var(--border); border-radius:6px; margin-bottom:10px; padding:8px;">
      <div style="font-weight:700; font-size:12px; color:var(--muted); margin-bottom:6px;">
        {group} : {ambientCount} ambient panel{ambientCount === 1 ? '' : 's'} + {hiddenCount} hidden content{hiddenCount === 1 ? '' : 's'}
      </div>
      <div class="row-table">
        {#each groupRows as d (d.id)}
          {@render detailRow(d)}
        {/each}
      </div>
    </div>
  {/each}
  {#if groups.ungrouped.length}
    <div class="row-table">
      {#each groups.ungrouped as d (d.id)}
        {@render detailRow(d)}
      {/each}
    </div>
  {/if}
{/if}

<div class="field-section" style="border-top:1px solid var(--border); margin-top:8px; padding-top:8px;">
  <div class="field-grid">
    <div class="field-row"><label for="disc-f-subject">Subject *</label>
      <input type="text" id="disc-f-subject" bind:value={newSubject} placeholder="e.g. lettre_innomee"></div>
    <div class="field-row" style="grid-column:1/-1"><label for="disc-f-content">Content *</label>
      <textarea id="disc-f-content" rows="3" style="resize:vertical" bind:value={newContent} placeholder="What the player discovers…"></textarea></div>
    <div class="field-row"><label for="disc-f-access">Access level</label>
      <select id="disc-f-access" bind:value={newAccessLevel}>
        <option value="hidden">hidden</option>
        <option value="ambient">ambient (dormant)</option>
      </select></div>
    <div class="field-row"><label for="disc-f-threshold">discovery_threshold (0–12, dormant)</label>
      <input type="number" id="disc-f-threshold" bind:value={newThreshold} min="0" max="12"></div>
    <div class="field-row"><label for="disc-f-signpost">signpost_group (optional)</label>
      <input type="text" id="disc-f-signpost" bind:value={newSignpost} placeholder="e.g. papiers_bureau"></div>
  </div>
  <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
    <button class="btn-send" onclick={addRow}>+ Add detail</button>
    <span style="font-size:12px; color:var(--muted)">{addStatus}</span>
  </div>
</div>
