<script>
  /* TICKET-0059 (BRIEF-0059-h commit 1, lock O1). Governed dialog primitive
     -- a faithful port of the legacy generic modal (index.html's
     genericModalOpen/genericModalClose, BRIEF-41): same backdrop-click
     condition (closes only when dismissOnBackdrop is true AND the click
     target is the backdrop itself, index.html:7326's inline handler), same
     .modal-backdrop/.modal-container/.modal-header/.modal-title/.modal-close/
     .modal-body classes (index.html:1024-1044, still legacy CSS -- this
     renders inside the legacy iframe document like every other Creation
     island, so no scoped <style> block here).

     The body is a snippet, not an HTML string: the legacy modal took
     bodyHtml because inline onclick="..." handlers were its only option. A
     Svelte primitive keeps its consumers' interactive logic in real
     component code instead of carrying that coupling forward.

     Open/close state is owned by the consumer, not this component: `open`
     is a plain prop and `onClose` is the single path both the close button
     and an eligible backdrop click route through -- the consumer decides
     what "closed" means for its own flow (Competences.svelte's delete
     modal, LocationTypeModal.svelte's classification prompt). */
  let { title, open, dismissOnBackdrop = true, onClose, body } = $props();

  function backdropClick(e) {
    if (dismissOnBackdrop && e.target === e.currentTarget) onClose();
  }
</script>

{#if open}
  <div class="modal-backdrop" onclick={backdropClick}>
    <div class="modal-container">
      <div class="modal-header">
        <span class="modal-title">{title}</span>
        <button class="modal-close" onclick={onClose}>&times;</button>
      </div>
      <div class="modal-body">
        {@render body()}
      </div>
    </div>
  </div>
{/if}
