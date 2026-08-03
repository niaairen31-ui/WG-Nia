<script>
  /* TICKET-0058 (BRIEF-0058-g, family b). Faithful port of the faction
     roles editor -- two modes, exactly as the legacy pair did:

     NEW faction (authorRenderRolesEditor/_authorNewRolesEditor/
     authorAddRoleRow/authorRemoveRoleRow/authorMoveRoleRow, index.html, now
     deleted): draft rows {name, description, limit} held in
     factionPanelState.draftRoles (was the authorFactionRolesDraft global),
     read directly by Sheet.svelte's submitEntity via draftRolesForCreate()
     at creation time -- no API calls here, client-only until the entity (and
     its roles) are POSTed together. The "+ Nouveau" reset _authorNewRolesEditor
     used to do lives in Sheet.svelte's primaryAction() now (resetDraftRoles()),
     not here -- this component is reused across the isNew<->existing
     transition (the same faction sheet's #author-roles mount never tears
     down when a create succeeds), so a construction-time-only reset here
     would miss a SECOND "+ Nouveau" against an already-mounted instance.

     EXISTING faction (authorLoadFactionRoles/authorRenderExistingRolesEditor/
     authorCreateFactionRole..authorDeclareFactionRole, also deleted): each
     row commits immediately (PATCH/rename/reorder/DELETE) via RoleRow.svelte,
     no batched save -- ported verbatim including the T1 realignment
     confirm() before a rename that would reassign active holders'
     memberships (close+reopen, history-preserving, per writes/factions.py --
     this component only triggers the route, never edits membership rows
     itself). Undeclared-borne roles (a true `role` on an active membership
     matching no declared row) render as a dim hint with one-click
     "+ déclarer".

     factionPanel.svelte.js owns the API calls and the shared rolesLive/
     rolesUndeclared state FactionRoster.svelte also reads (the "roles load
     before roster" sequencing lives in that module's
     loadFactionMembersPanel, called once from Sheet.svelte's async tail --
     not duplicated here). */
  import { factionPanelState, createFactionRole, moveFactionRole, deleteFactionRole, declareFactionRole } from './factionPanel.svelte.js';
  import RoleRow from './RoleRow.svelte';

  let { isNew, factionId } = $props();

  let statusMessage = $state('');

  function addDraftRow() {
    factionPanelState.draftRoles = [...factionPanelState.draftRoles, { name: '', description: '', limit: null }];
  }

  function removeDraftRow(i) {
    factionPanelState.draftRoles = factionPanelState.draftRoles.filter((_, idx) => idx !== i);
  }

  function moveDraftRow(i, dir) {
    const j = i + dir;
    if (j < 0 || j >= factionPanelState.draftRoles.length) return;
    const rows = [...factionPanelState.draftRoles];
    [rows[i], rows[j]] = [rows[j], rows[i]];
    factionPanelState.draftRoles = rows;
  }

  let newName = $state('');
  let newDescription = $state('');
  // A number input's bind:value coerces to a number (or undefined when
  // cleared), not a string -- never compared against ''.
  let newLimit = $state(null);

  async function onCreate() {
    const name = newName.trim();
    if (!name) return;
    try {
      await createFactionRole(factionId, {
        name, description: newDescription || null,
        max_holders: newLimit ?? null,
      });
      newName = ''; newDescription = ''; newLimit = null;
      statusMessage = '';
    } catch (e) {
      statusMessage = e.message;
    }
  }

  async function onMove(i, dir) {
    try {
      await moveFactionRole(factionId, i, dir);
      statusMessage = '';
    } catch (e) {
      statusMessage = e.message;
    }
  }

  async function onDelete(roleId) {
    if (!confirm('Delete this role?')) return;
    try {
      await deleteFactionRole(factionId, roleId);
      statusMessage = '';
    } catch (e) {
      statusMessage = e.message;
    }
  }

  async function onDeclare(name) {
    try {
      await declareFactionRole(factionId, name);
      statusMessage = '';
    } catch (e) {
      statusMessage = e.message;
    }
  }
</script>

{#if isNew}
  <div id="author-roles-rows">
    {#if factionPanelState.draftRoles.length === 0}
      <div class="empty">Aucun rôle.</div>
    {:else}
      {#each factionPanelState.draftRoles as row, i}
        <div class="row-card" style="flex-direction:row; gap:8px; align-items:center;">
          <input type="number" min="1" step="1" placeholder="Limite" style="width:90px"
            bind:value={row.limit}>
          <input type="text" placeholder="Rôle" style="flex:1" bind:value={row.name}>
          <input type="text" placeholder="Description" style="flex:2" bind:value={row.description}>
          <button class="btn-icon" onclick={() => moveDraftRow(i, -1)} title="Monter" disabled={i === 0}>↑</button>
          <button class="btn-icon" onclick={() => moveDraftRow(i, 1)} title="Descendre" disabled={i === factionPanelState.draftRoles.length - 1}>↓</button>
          <button class="btn-icon" onclick={() => removeDraftRow(i)} title="Supprimer">✕</button>
        </div>
      {/each}
    {/if}
  </div>
  <div style="font-size:11px; color:var(--muted); margin:4px 0;">Limite | Rôle | Description — vide = illimité</div>
  <div class="row-card-actions" style="margin-top:6px">
    <button class="btn-send" onclick={addDraftRow}>+ Add role</button>
  </div>
{:else}
  <div id="author-roles-rows">
    {#if factionPanelState.rolesLive.length === 0}
      <div class="empty">Aucun rôle.</div>
    {:else}
      {#each factionPanelState.rolesLive as row, i (row.id)}
        <RoleRow {row} {factionId} isFirst={i === 0} isLast={i === factionPanelState.rolesLive.length - 1}
          onMoveUp={() => onMove(i, -1)} onMoveDown={() => onMove(i, 1)} onDelete={() => onDelete(row.id)}
          onStatus={(msg) => { statusMessage = msg; }} />
      {/each}
    {/if}
  </div>
  {#if factionPanelState.rolesUndeclared.length}
    <div id="author-roles-undeclared" style="margin-top:6px">
      {#each factionPanelState.rolesUndeclared as name}
        <div class="row-card" style="flex-direction:row; gap:8px; align-items:center; opacity:0.6;">
          <span style="flex:1">{name}</span>
          <span style="font-size:11px;">non déclaré</span>
          <button class="btn-send" onclick={() => onDeclare(name)}>+ déclarer</button>
        </div>
      {/each}
    </div>
  {/if}
  <div style="font-size:11px; color:var(--muted); margin:6px 0;">Limite | Rôle | Description — vide = illimité</div>
  <div class="row-card" style="flex-direction:row; gap:8px; align-items:center;">
    <input type="number" min="1" step="1" placeholder="Limite" style="width:90px" bind:value={newLimit}>
    <input type="text" placeholder="Nom" style="flex:1" bind:value={newName}>
    <input type="text" placeholder="Description" style="flex:2" bind:value={newDescription}>
    <button class="btn-send" onclick={onCreate}>+ Add role</button>
  </div>
  <span class="author-status" class:err={!!statusMessage}>{statusMessage}</span>
{/if}
