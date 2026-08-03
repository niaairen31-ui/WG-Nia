<script>
  /* TICKET-0058 (BRIEF-0058-g, family b). Faithful port of a character's
     own memberships sub-editor -- authorLoadMemberships/authorRenderMemberships/
     authorCloseMembership/authorRenderMembershipForm/authorMembershipFactionChanged/
     authorMembershipRoleSelectChanged/authorAddMembership (index.html, now
     deleted). Not named individually in the brief's family-b list (which
     names only the add-form trio), but authorRenderMemberships's own "Close"
     button called authorCloseMembership directly -- porting the mutations
     without the list they're read from would leave a legacy renderer
     wired to a deleted function, so both halves of this one sub-editor
     move together (RECON-SUPPLEMENT-0058 -g's own "preserve every seam"
     instruction, applied the same way family a's Lieux create/save flow
     was).

     Role picker (BRIEF-31, schema v1.42, decision F1): repopulates from the
     selected faction's curated `roles` (GET /api/entities/{id}/roles --
     public vocabulary, names only, stored order) plus an always-present
     "autre" option; no faction selected, or a faction with no roles,
     degrades to "autre" only (decision 3.4). */
  import { creationState } from './state.svelte.js';

  let { entityId, legacyDoc } = $props();

  let rows = $state([]);
  let loadError = $state('');
  let statusMessage = $state('');

  let selectedFactionId = $state('');
  let factionRoleNames = $state([]);
  let selectedRole = $state('');
  let otherRole = $state('');
  let coverRole = $state('');
  let isPrimary = $state(false);
  let isSecret = $state(false);

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  async function load() {
    try {
      rows = await api(`/api/entities/${encodeURIComponent(entityId)}/memberships`);
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => { load(); });

  const factionCandidates = $derived((creationState.entities || []).filter((e) => e.type === 'faction'));

  async function onFactionChange() {
    selectedRole = '';
    if (!selectedFactionId) { factionRoleNames = []; return; }
    try {
      factionRoleNames = (await api(`/api/entities/${encodeURIComponent(selectedFactionId)}/roles`)).map((r) => r.name);
    } catch (_e) {
      factionRoleNames = [];
    }
  }

  async function onAdd() {
    const statusEl = legacyDoc.getElementById('author-status');
    const role = selectedRole === '__other__' ? (otherRole || null) : (selectedRole || null);
    try {
      await api(`/api/entities/${encodeURIComponent(entityId)}/memberships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          faction_id: selectedFactionId, role, cover_role: coverRole || null,
          is_primary: isPrimary, is_secret: isSecret,
        }),
      });
      await load();
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Saved.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }

  async function onClose(id) {
    if (!confirm('Close this membership?')) return;
    const statusEl = legacyDoc.getElementById('author-status');
    try {
      await api(`/api/memberships/${encodeURIComponent(id)}/close`, { method: 'POST' });
      await load();
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Saved.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }
</script>

<div id="author-memberships">
  {#if loadError}
    <div class="empty">{loadError}</div>
  {:else if rows.length === 0}
    <div class="empty">No active memberships.</div>
  {:else}
    <div class="row-table">
      {#each rows as m (m.id)}
        <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;">
          <span>{m.faction_name}{m.role ? ` — ${m.role}` : ''}{m.cover_role ? ` (façade : ${m.cover_role})` : ''}</span>
          <span style="display:flex; align-items:center; gap:8px;">
            {#if m.is_primary}<span class="badge b-equipped">primaire</span>{/if}
            {#if m.is_secret}<span class="badge b-rejected">secret</span>{/if}
            <button class="btn-end" style="font-size:12px; padding:3px 8px" onclick={() => onClose(m.id)}>Close</button>
          </span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<div class="row-card">
  <div class="field-grid">
    <div class="field-row"><label>Faction *</label>
      <select bind:value={selectedFactionId} onchange={onFactionChange}>
        {#each factionCandidates as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
      </select></div>
    <div class="field-row"><label>Role</label>
      <select bind:value={selectedRole}>
        {#each factionRoleNames as name}<option value={name}>{name}</option>{/each}
        <option value="__other__">autre</option>
      </select></div>
    {#if selectedRole === '__other__'}
      <div class="field-row"><label>Role (autre)</label><input type="text" bind:value={otherRole}></div>
    {/if}
    <div class="field-row"><label>Cover role (façade)</label><input type="text" bind:value={coverRole}></div>
    <div class="field-row checkbox"><input type="checkbox" id="mem-new-primary" bind:checked={isPrimary}><label for="mem-new-primary">Primaire</label></div>
    <div class="field-row checkbox"><input type="checkbox" id="mem-new-secret" bind:checked={isSecret}><label for="mem-new-secret">Secret</label></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={onAdd}>Add membership</button>
  </div>
</div>
