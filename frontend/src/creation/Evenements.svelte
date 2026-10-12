<script>
  /* TICKET-0058 (BRIEF-0058-j); rewritten by TICKET-0114 (BRIEF-0114-C) as
     the event journal's sheet. Its plain fields (title, description, place)
     come from `registry.event_fields` through <Field>; the rest is its own:
     the event's type (one of the world's, fixed once written), its quantity
     when the type counts, its participants role by role -- an entity of a
     type the role accepts or a sorte, each entity keeping the event secret
     or not (X1, never a player character), a participant once written
     staying -- and who learns it besides them: the type's scopes by
     default, or the creator's own (W1). The types and sortes come from the
     shared vocabulary store (eventVocab.svelte.js).

     TICKET-0119 (BRIEF-0119-D, H1): everything past the plain fields is the
     shared EventEditor.svelte, the same the review card and Lore render; a
     new event also says what it changes in the world (M-c), a correction
     does not.

     Rendered by Sheet.svelte in 'view' mode on the « Événements » tab;
     saved through its saveEventSheet (POST /api/events, PUT
     /api/events/{id}). No delete anywhere (C3 -- an event is history; a
     retraction empties its scopes). No scoped <style> block. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromGenerated,
  } from './eventDraft.svelte.js';
  import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
  import Field from './Field.svelte';
  import EventEditor from './EventEditor.svelte';

  let { legacyDoc, isNew, event, entities, playerCharIds, eventFields, onSave } = $props();

  let genStatus = $state('');
  let genNotes = $state([]);
  let genBrief = $state('');

  $effect(() => {
    loadVocabulary(serverState.worldId);
  });

  $effect(() => {
    void isNew;
    void (event && event.id);
    resetEventDraft();
    if (!isNew && event) setEventDraftFromEvent(event);
    genStatus = '';
    genNotes = [];
    genBrief = '';
  });

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
    if (result.location_id) setVal('event-f-location_id', result.location_id);
    setEventDraftFromGenerated(result, vocabState.types, entities || []);
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

<EventEditor draft={eventDraftState} {entities} {playerCharIds} typeFixed={!isNew} withChanges={isNew} />

{#if !isNew}
  <div class="field-section"><span style="color:var(--muted); font-size:12px;">Enregistré : {event.recorded_at || ''}</span></div>
{/if}

{#if isNew}
  <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
    <button class="btn-send" onclick={onSave}>+ Créer l'événement</button>
  </div>
{/if}
