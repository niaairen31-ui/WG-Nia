<script>
  /* TICKET-0101 (BRIEF-0101-C, S1). The promotion dialog: a location about
     to receive its first active child becomes a zone, and what can only sit
     in a visitable place moves to that child. Fed by the read-only
     GET /api/locations/{id}/promotion-preview (writes/zone_promotion.py's
     promotion_preview); the write that follows carries confirm_promotion
     only after the creator confirms here. Same instance shape as
     LocationTypeModal.svelte: Sheet.svelte owns one, opened from its save
     path; open/close state lives here, the Modal primitive renders it. */
  import Modal from './Modal.svelte';

  let open = $state(false);
  let preview = $state(null);
  let childName = $state('');
  let onConfirmCb = () => {};

  const SECTIONS = [
    { key: 'links', title: 'Liens, qui deviennent « borde » (non traversables)', label: (r) => r.other_name },
    { key: 'beings', title: 'Personnages présents, déplacés', label: (r) => r.name },
    { key: 'schedules', title: 'Horaires, reciblés', label: (r) => `${r.npc_name} (${r.phase})` },
    { key: 'items', title: 'Objets posés, déplacés', label: (r) => r.name },
    { key: 'details', title: 'Détails découvrables, déplacés', label: (r) => r.subject },
    { key: 'gatherings', title: 'Rassemblements ouverts, fermés', label: (r) => r.label || 'sans nom' },
  ];

  /** Resolves the save: `proceed(false)` at once when the write promotes
   *  nothing that moves, else after the dialog, `proceed(true)` on confirm
   *  (cancel calls nothing). A failed preview read lets the save go through
   *  unconfirmed -- the server still refuses it (409) if it had to ask.
   *  AMENDMENT-0101-01: a child that is itself a zone cannot receive the
   *  contents; no dialog, the save goes through and the server's 409
   *  message lands in the fiche's status line. */
  export async function gate(parentId, childId, name, proceed) {
    if (!parentId) return proceed(false);
    const query = childId ? `?child_id=${encodeURIComponent(childId)}` : '';
    let data;
    try {
      const res = await fetch(`/api/locations/${encodeURIComponent(parentId)}/promotion-preview${query}`);
      data = res.ok ? await res.json() : null;
    } catch (_err) {
      data = null;
    }
    if (!data || !data.needs_confirmation || data.target_is_zone) return proceed(false);
    preview = data;
    childName = name || 'le nouveau lieu';
    onConfirmCb = () => proceed(true);
    open = true;
  }

  function close() {
    open = false;
  }

  async function confirmPromotion() {
    open = false;
    await onConfirmCb();
  }
</script>

<Modal title="Ce lieu devient une zone" {open} dismissOnBackdrop={false} onClose={close}>
  {#snippet body()}
    {#if preview}
      <p>« {preview.location_name} » reçoit son premier lieu enfant : il devient une zone, qu'on
      ne visite plus directement. Ce qui suit va dans « {childName} ».</p>
      {#each SECTIONS as section (section.key)}
        {#if preview[section.key].length}
          <div class="field-section-title" style="margin-top:8px">{section.title}</div>
          {#each preview[section.key] as row (row.id || `${row.npc_id}-${row.phase}`)}
            <div style="font-size:12px">· {section.label(row)}</div>
          {/each}
        {/if}
      {/each}
      <p style="font-size:11px; color:var(--muted); margin-top:8px">Plan intérieur, événements,
      faits, connaissances et contrôle de faction restent sur la zone.</p>
      <div class="row-card-actions" style="margin-top:10px">
        <button class="btn-send" onclick={confirmPromotion}>Confirmer</button>
        <button class="btn-icon" onclick={close}>Annuler</button>
      </div>
    {/if}
  {/snippet}
</Modal>
