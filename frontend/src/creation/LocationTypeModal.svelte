<script>
  /* TICKET-0059 (BRIEF-0059-h commit 1, lock O1). Owns the interior/
     exterior classification-prompt flow's dialog state -- faithful port of
     locationType.js's former promptLocationTypeClassification (now split:
     see that file's header). locationType.js is a plain module, not a
     component, so per O1 the open/close state and the width/height inputs
     live here instead; the pure/data half (resolveClassificationDefaults'
     catalog lookup, classifyLocationType's POST + catalog refresh) stays in
     locationType.js, touching no dialog.

     Instantiated independently by each of the flow's three trigger points
     -- Field.svelte's "Gabarit..." button, RoomBatch.svelte's own Gabarit
     button, Sheet.svelte's automatic save-time classification gate -- the
     same "each component owns its own local state" idiom this tree already
     follows for e.g. its per-component api() helper, rather than a shared
     cross-component ctx plumb. Only one can ever be open at a time in
     practice (one user, one flow); a closed instance renders nothing
     (Modal.svelte's own `{#if open}`), so the duplication costs nothing at
     rest. */
  import Modal from './Modal.svelte';
  import { resolveClassificationDefaults, classifyLocationType } from './locationType.js';

  let { legacyDoc } = $props();

  let open = $state(false);
  let typeName = $state('');
  let width = $state('');
  let height = $state('');
  let status = $state('');
  let onClassifiedCb = () => {};

  export function openFor(name, onClassified) {
    const defaults = resolveClassificationDefaults(name);
    typeName = name;
    width = defaults.prefWidth;
    height = defaults.prefHeight;
    status = '';
    onClassifiedCb = onClassified;
    open = true;
  }

  function close() {
    open = false;
  }

  async function choose(classification) {
    const widthVal = String(width ?? '').trim();
    const heightVal = String(height ?? '').trim();
    if ((widthVal === '') !== (heightVal === '')) {
      status = 'Renseigne les deux dimensions, ou aucune.';
      return;
    }
    status = '…';
    try {
      await classifyLocationType(legacyDoc, typeName, classification, widthVal, heightVal);
      open = false;
      await onClassifiedCb();
    } catch (e) {
      status = e.message;
    }
  }
</script>

<Modal title="Classification du type de lieu" {open} dismissOnBackdrop={false} onClose={close}>
  {#snippet body()}
    <p>Le type « {typeName} » n'est pas encore classifié. Ce lieu est-il
    intérieur ou extérieur ? Ce choix est mémorisé pour les prochains lieux de
    ce type.</p>
    <div class="row-card-actions" style="margin-top:10px">
      <button class="btn-send" onclick={() => choose('interior')}>Interieur</button>
      <button class="btn-send" onclick={() => choose('exterior')}>Exterieur</button>
    </div>
    <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-top:10px">
      <label style="flex:1">Largeur par défaut (m)</label>
      <input type="number" step="any" bind:value={width} style="flex:1">
      <label style="flex:1">Hauteur par défaut (m)</label>
      <input type="number" step="any" bind:value={height} style="flex:1">
    </div>
    <div style="color:var(--red); margin-top:6px">{status}</div>
  {/snippet}
</Modal>
