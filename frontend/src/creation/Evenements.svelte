<script>
  /* TICKET-0058 (BRIEF-0058-j, per RECON-SUPPLEMENT-0058's -j re-scope).
     Faithful port of renderEventSheet/evenementsRenderCreatePanel/
     evenementsSave/evenementsSubmitCreate/evenementsGenerateDraft/
     _evenementsRenderChips/evenementsAddChip/evenementsRemoveChip
     (index.html, now deleted) -- evenements' bespoke, non-entity sheet
     (`event` is not an ENTITY_TYPE_REGISTRY row, so it never used
     authorRenderSheet's registry.types[type] shape; `authorRegistry.
     event_fields` -- now Sheet.svelte's own `registry.event_fields`, the
     SAME GET /api/entity-types response -- feeds the shared field engine
     directly through <Field>, not through the now-deleted
     'creation:field-render'/'creation:field-read' reverse-bridge brief -f
     stood up for this exact gap.

     Rendered by Sheet.svelte inside its own 'view' mode when
     creationState.activeTabKey === 'evenements', with the SAME isNew/event
     shape every other entity type's fields already use -- this component
     only differs in field source (registry.event_fields, not
     registry.types[type].fields) and save target (/api/events, not
     /api/entities). The header Save button (view mode) and this
     component's own inline "+ Créer l'événement" button (create mode) both
     call the SAME onSave prop -- Sheet.svelte's saveEventSheet, exactly
     mirroring how the generic entity sheet's header Save button and
     Constructeur-style creates share one submit path.

     Two writes only, no delete anywhere (C3 -- event is history, retraction
     is knowledge_status='secret'): POST /api/events (create) and
     PUT /api/events/{id} (save), both inside onSave.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromIds, addEventChip, removeEventChip } from './eventDraft.svelte.js';
  import Field from './Field.svelte';

  let { legacyDoc, isNew, event, entities, eventFields, onSave } = $props();

  let genStatus = $state('');
  let genNotes = $state([]);
  let genBrief = $state('');

  $effect(() => {
    void isNew;
    void (event && event.id);
    resetEventDraft();
    if (!isNew && event) setEventDraftFromEvent(event);
    genStatus = '';
    genNotes = [];
    genBrief = '';
  });

  const candidates = $derived((entities || []).filter((e) => !eventDraftState.involved.some((c) => c.id === e.id)));

  function onChipAdd(ev) {
    const id = ev.currentTarget.value;
    if (!id) return;
    const entity = (entities || []).find((e) => e.id === id);
    if (entity) addEventChip(entity);
    ev.currentTarget.value = '';
  }

  /** evenements' AI assistant (BRIEF-0022-b) -- pre-fills the create shell
   *  from a one-shot POST /api/events/generate; a second click overwrites,
   *  same F2 precedent as the entity GeneratePanel. The currently chosen
   *  location_id (if any) is sent as an authoritative pre-selection. */
  async function generate() {
    const brief = genBrief.trim();
    if (!brief) { genStatus = 'Intention requise.'; return; }
    const locationId = legacyDoc.getElementById('event-f-location_id')?.value || null;

    genStatus = 'Génération…';
    let result;
    try {
      const res = await fetch('/api/events/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief, location_id: locationId }),
      });
      result = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
    } catch (e) {
      genStatus = e.message;
      return;
    }
    if (!result || result.ok === false) {
      genStatus = (result && result.error) || 'Échec de la génération.';
      return;
    }

    const setVal = (id, v) => { const el = legacyDoc.getElementById(id); if (el) el.value = v ?? ''; };
    setVal('event-f-title', result.title);
    setVal('event-f-description', result.description);
    setVal('event-f-type', result.type);
    if (result.location_id) setVal('event-f-location_id', result.location_id);

    setEventDraftFromIds(result.involved_entities, entities || []);

    genNotes = result.notes || [];
    genStatus = "Brouillon généré — relisez et éditez avant d'accepter.";
  }
</script>

{#if isNew}
  <div class="field-section" id="event-gen-panel" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:12px;">
    <div class="field-section-title">Générer avec l'IA</div>
    <textarea rows="2" style="width:100%; resize:vertical" bind:value={genBrief}
      placeholder="Une phrase, ex. : « Une crue emporte le pont du quartier bas pendant la nuit »"></textarea>
    <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
      <button class="btn-send" onclick={generate}>Générer</button>
      <span style="font-size:12px; color:var(--muted)">{genStatus}</span>
    </div>
    {#if genNotes.length}
      <div class="field-section-title" style="margin-top:8px">Notes de l'assistant</div>
      <div class="row-table">
        {#each genNotes as n}
          <div class="row-card" style="font-size:12px; color:var(--muted)">{n}</div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<div class="field-section"><div class="field-section-title">{isNew ? 'Nouvel événement' : 'Événement'}</div><div class="field-grid">
  {#each (eventFields || []) as f (f.name)}
    <Field field={f} value={isNew ? undefined : event[f.name]} idPrefix="event-f" ctx={{ entities }} />
  {/each}
</div></div>

<div class="field-section"><div class="field-section-title">Entités impliquées</div>
  <div id="evenements-chips">
    {#if eventDraftState.involved.length === 0}
      <div class="empty">Aucune entité impliquée.</div>
    {:else}
      {#each eventDraftState.involved as c, i}
        <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
          {c.name ? c.name : `« entité inconnue » (${(c.id || '').slice(0, 8)})`}
          <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeEventChip(i)}>✕</button>
        </span>
      {/each}
    {/if}
  </div>
  <select onchange={onChipAdd}>
    <option value="">— ajouter une entité —</option>
    {#each candidates as e (e.id)}
      <option value={e.id}>{e.name}</option>
    {/each}
  </select>
</div>

{#if !isNew}
  <div class="field-section"><span style="color:var(--muted); font-size:12px;">Enregistré : {event.recorded_at || ''}</span></div>
{/if}

{#if isNew}
  <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
    <button class="btn-send" onclick={onSave}>+ Créer l'événement</button>
  </div>
{/if}
