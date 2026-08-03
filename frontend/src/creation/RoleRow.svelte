<script>
  /* TICKET-0058 (BRIEF-0058-g, family b). One EXISTING-faction role row --
     split out of RolesEditor.svelte so each row keeps its own local edit
     buffer (description/limit) independently of the shared
     factionPanelState.rolesLive array, the same way Field.svelte gives the
     generic field engine a per-field component instead of scattering
     per-field reactive state through one big component. Committing (the
     onchange handlers) still goes straight through factionPanel.svelte.js's
     API functions -- no batching, matching authorUpdateFactionRole/
     authorRenameFactionRole's immediate-commit-per-field original. A number
     input's bind:value coerces to a number (or undefined when cleared), not
     a string -- limit is never compared against ''. */
  import { renameFactionRole, updateFactionRole } from './factionPanel.svelte.js';

  let { row, factionId, isFirst, isLast, onMoveUp, onMoveDown, onDelete, onStatus } = $props();

  let description = $state('');
  let limit = $state(null);

  $effect(() => {
    description = row.description || '';
    limit = row.max_holders ?? null;
  });

  function limitValue() {
    return limit ?? null;
  }

  async function commitUpdate() {
    try {
      await updateFactionRole(factionId, row.id, { description, max_holders: limitValue() });
      onStatus('');
    } catch (e) {
      onStatus(e.message);
    }
  }

  async function commitRename(ev) {
    const nameInputEl = ev.currentTarget;
    const newName = (nameInputEl.value || '').trim();
    if (!newName || newName === row.name) { nameInputEl.value = row.name; return; }
    const count = row.active_holder_count || 0;
    if (count > 0) {
      const ok = confirm(
        `Renommer "${row.name}" en "${newName}" ? ${count} membre(s) actif(s) tenant ce rôle seront ` +
        `réalignés (fermeture + réouverture de leur adhésion ; l'historique est conservé). Continuer ?`
      );
      if (!ok) { nameInputEl.value = row.name; return; }
    }
    try {
      await renameFactionRole(factionId, row.id, { name: newName, description, max_holders: limitValue() });
      onStatus('');
    } catch (e) {
      nameInputEl.value = row.name;
      onStatus(e.message);
    }
  }
</script>

<div class="row-card" style="flex-direction:row; gap:8px; align-items:center;">
  <input type="number" min="1" step="1" placeholder="Limite" style="width:90px" bind:value={limit} onchange={commitUpdate}>
  <input type="text" placeholder="Rôle" value={row.name} style="flex:1" onchange={commitRename}>
  <input type="text" placeholder="Description" style="flex:2" bind:value={description} onchange={commitUpdate}>
  <button class="btn-icon" onclick={onMoveUp} title="Monter" disabled={isFirst}>↑</button>
  <button class="btn-icon" onclick={onMoveDown} title="Descendre" disabled={isLast}>↓</button>
  <button class="btn-icon" onclick={onDelete} title="Supprimer">✕</button>
</div>
