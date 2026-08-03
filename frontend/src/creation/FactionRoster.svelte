<script>
  /* TICKET-0058 (BRIEF-0058-g, family b). Faithful port of the faction
     roster panel (TICKET-0054, BRIEF-0054-c) -- authorRenderFactionRoster/
     _factionRosterRowHtml/_factionRoleOptionsHtml/authorRenderFactionMemberAddForm/
     authorFactionMemberRoleSelectChanged/authorFactionMemberAddPrefill/
     authorAddFactionMember/authorMemberRoleEditStart/Cancel/Submit
     (index.html, now deleted).

     Three-bucket grouped render (decision B1): member order INSIDE a zone
     is exactly factionPanelState.rosterRows' own order (the roster route
     owns order, decision A1) -- this component groups, it never sorts.
     Reads factionPanelState.rolesLive (loaded by RolesEditor's sibling
     fetch, sequenced via factionPanel.svelte.js's loadFactionMembersPanel)
     for the zone1 role list and the add-member/inline-edit role pickers.

     Double-click opens the member's own sheet via the still-legacy
     creationOpenEntityFrom (unchanged, reached through legacyCall since
     that's a cross-cutting Creation-list concern, not this panel's). */
  import { creationState } from './state.svelte.js';
  import { legacyCall } from '../legacy/bridge.js';
  import { factionPanelState, addFactionMember, memberRoleEditSubmit } from './factionPanel.svelte.js';

  let { factionId } = $props();

  let statusMessage = $state('');

  let newEntityId = $state('');
  let newRoleSelect = $state('');
  let newRoleOther = $state('');
  let newCoverRole = $state('');
  let newPrimary = $state(false);
  let newSecret = $state(false);

  let editRoleSelect = $state('');

  const roleOptionNames = $derived(factionPanelState.rolesLive.map((r) => r.name));
  const activeMemberIds = $derived(new Set(factionPanelState.rosterRows.map((m) => m.entity_id)));
  const candidates = $derived((creationState.entities || []).filter((e) => e.type === 'character' && !activeMemberIds.has(e.id)));

  const zone1 = $derived(factionPanelState.rolesLive.map((role) => ({
    role,
    members: factionPanelState.rosterRows.filter((m) => m.role_declared && m.role_position === role.position),
  })));

  const zone2Names = $derived((() => {
    const names = [];
    const seen = new Set();
    for (const m of factionPanelState.rosterRows) {
      const role = (m.role || '').trim();
      if (!m.role_declared && role && !seen.has(role)) { seen.add(role); names.push(role); }
    }
    return names;
  })());

  const zone3 = $derived(factionPanelState.rosterRows.filter((m) => !(m.role || '').trim()));

  function openEntity(entityId) {
    legacyCall('creationOpenEntityFrom', entityId, 'character');
  }

  function startEdit(m) {
    factionPanelState.rosterEditingId = m.id;
    editRoleSelect = m.role || '';
  }

  function cancelEdit() {
    factionPanelState.rosterEditingId = null;
  }

  async function submitEdit(membershipId) {
    try {
      await memberRoleEditSubmit(factionId, membershipId, editRoleSelect || null);
      statusMessage = '';
    } catch (e) {
      statusMessage = e.message;
    }
  }

  function prefill(roleName) {
    if (roleOptionNames.includes(roleName)) {
      newRoleSelect = roleName;
    } else {
      newRoleSelect = '__other__';
      newRoleOther = roleName;
    }
  }

  async function onAddMember() {
    if (!newEntityId) return;
    const role = newRoleSelect === '__other__' ? (newRoleOther || null) : (newRoleSelect || null);
    try {
      await addFactionMember(factionId, newEntityId, {
        role, cover_role: newCoverRole || null, is_primary: newPrimary, is_secret: newSecret,
      });
      newEntityId = ''; newRoleSelect = ''; newRoleOther = ''; newCoverRole = ''; newPrimary = false; newSecret = false;
      statusMessage = 'Saved.';
    } catch (e) {
      statusMessage = e.message;
    }
  }
</script>

{#snippet memberRow(m)}
  <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; cursor:pointer;"
       ondblclick={() => openEntity(m.entity_id)} title="Double-cliquer pour ouvrir la fiche">
    <span>{m.entity_name}{m.role ? ` — ${m.role}` : ''}{m.cover_role ? ` (façade : ${m.cover_role})` : ''}</span>
    <span style="display:flex; align-items:center; gap:8px;">
      {#if factionPanelState.rosterEditingId === m.id}
        <select onclick={(ev) => ev.stopPropagation()} bind:value={editRoleSelect}>
          <option value="">(aucun)</option>
          {#each roleOptionNames as name}<option value={name}>{name}</option>{/each}
          <option value="__other__">autre</option>
        </select>
        <button class="btn-send" style="font-size:11px; padding:2px 8px" onclick={(ev) => { ev.stopPropagation(); submitEdit(m.id); }}>Valider</button>
        <button class="btn-ghost" style="font-size:11px; padding:2px 8px" onclick={(ev) => { ev.stopPropagation(); cancelEdit(); }}>Annuler</button>
      {:else}
        {#if m.is_primary}<span class="badge b-equipped">primaire</span>{/if}
        {#if m.is_secret}<span class="badge b-rejected">secret</span>{/if}
        <button class="btn-ghost" style="font-size:11px; padding:2px 8px" onclick={(ev) => { ev.stopPropagation(); startEdit(m); }}>Changer</button>
      {/if}
    </span>
  </div>
{/snippet}

{#each zone1 as { role, members } (role.id)}
  <div class="field-section-title" style="display:flex; align-items:center; justify-content:space-between;">
    <span>{role.name} <span style="font-size:11px; color:var(--muted)">({role.active_holder_count}/{role.max_holders ?? '∞'})</span></span>
    <button class="btn-icon" onclick={() => prefill(role.name)} title="Ajouter dans ce rôle">+</button>
  </div>
  {#if members.length}
    <div class="row-table">{#each members as m (m.id)}{@render memberRow(m)}{/each}</div>
  {:else}
    <div class="empty">Aucun membre.</div>
  {/if}
{/each}

{#each zone2Names as name}
  {@const members = factionPanelState.rosterRows.filter((m) => !m.role_declared && (m.role || '').trim() === name)}
  <div class="field-section-title" style="display:flex; align-items:center; justify-content:space-between;">
    <span>{name} <span class="badge" style="font-size:10px;">non déclaré</span></span>
  </div>
  <div class="row-table">{#each members as m (m.id)}{@render memberRow(m)}{/each}</div>
{/each}

{#if zone3.length}
  <div class="field-section-title">Sans rôle</div>
  <div class="row-table">{#each zone3 as m (m.id)}{@render memberRow(m)}{/each}</div>
{/if}

<div class="row-card">
  <div class="field-grid">
    <div class="field-row"><label>Membre *</label>
      <select bind:value={newEntityId} disabled={candidates.length === 0}>
        {#if candidates.length === 0}
          <option value="">Aucun candidat</option>
        {:else}
          <option value=""></option>
          {#each candidates as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
        {/if}
      </select></div>
    <div class="field-row"><label>Role</label>
      <select bind:value={newRoleSelect}>
        <option value="">(aucun)</option>
        {#each roleOptionNames as name}<option value={name}>{name}</option>{/each}
        <option value="__other__">autre</option>
      </select></div>
    {#if newRoleSelect === '__other__'}
      <div class="field-row"><label>Role (autre)</label><input type="text" bind:value={newRoleOther}></div>
    {/if}
    <div class="field-row"><label>Cover role (façade)</label><input type="text" bind:value={newCoverRole}></div>
    <div class="field-row checkbox"><input type="checkbox" id="fmem-new-primary" bind:checked={newPrimary}><label for="fmem-new-primary">Primaire</label></div>
    <div class="field-row checkbox"><input type="checkbox" id="fmem-new-secret" bind:checked={newSecret}><label for="fmem-new-secret">Secret</label></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={onAddMember}>Ajouter le membre</button>
  </div>
</div>
<span class="author-status" class:err={!!statusMessage && statusMessage !== 'Saved.'} class:ok={statusMessage === 'Saved.'}>{statusMessage}</span>
