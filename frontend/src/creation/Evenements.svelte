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

     Rendered by Sheet.svelte in 'view' mode on the « Événements » tab;
     saved through its saveEventSheet (POST /api/events, PUT
     /api/events/{id}). No delete anywhere (C3 -- an event is history; a
     retraction empties its scopes). No scoped <style> block. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromGenerated, addParticipant,
    removeParticipant,
  } from './eventDraft.svelte.js';
  import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
  import Field from './Field.svelte';

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

  const SCOPE_TYPES = [
    { value: 'world', label: 'tout le monde' }, { value: 'location', label: 'ceux qui passent au lieu' },
    { value: 'rencontre', label: 'ceux qui ont rencontré' }, { value: 'faction', label: 'les membres de la faction' },
  ];

  let type = $derived(vocabState.types.find((t) => t.id === eventDraftState.typeId) || null);
  let roles = $derived(type ? type.roles.filter((r) => r.status === 'active') : []);
  let activeSortes = $derived(vocabState.sortes.filter((s) => s.status === 'active'));
  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));

  function candidates(role) {
    return (entities || []).filter((e) => role.entity_types.includes(e.type));
  }

  function onAdd(role, ev) {
    const value = ev.currentTarget.value;
    ev.currentTarget.value = '';
    if (!value) return;
    const [kind, id] = value.split(':');
    const name = kind === 'sorte' ? (activeSortes.find((s) => s.id === id) || {}).name
      : ((entities || []).find((e) => e.id === id) || {}).name;
    addParticipant(role, kind, id, name, type && type.participants_secret);
  }

  function scopeTargets(scopeType) {
    if (scopeType === 'location') return (entities || []).filter((e) => e.type === 'location');
    if (scopeType === 'faction') return (entities || []).filter((e) => e.type === 'faction');
    return entities || [];
  }

  function typeScopeLine(t) {
    if (!t || !t.scopes.length) return 'les participants seulement';
    return t.scopes.map((s) => `${s.kind}${s.role ? ' ' + s.role : ''} (${levelLabels[s.level] || s.level})`).join(' · ');
  }

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

<div class="field-section"><div class="field-section-title">Type</div>
  <select id="event-f-type_id" bind:value={eventDraftState.typeId} disabled={!isNew}>
    <option value="">— choisir un type —</option>
    {#each vocabState.types.filter((t) => t.status === 'active' || t.id === eventDraftState.typeId) as t (t.id)}
      <option value={t.id}>{t.name} ({t.domain_label})</option>
    {/each}
  </select>
  {#if !isNew}<span style="color:var(--muted); font-size:12px;"> Le type d'un événement ne change pas.</span>{/if}
  {#if type && type.counts_quantity}
    <label style="display:block; margin-top:6px">Quantité
      <input id="event-f-quantity" type="number" min="1" style="width:90px" bind:value={eventDraftState.quantity}>
    </label>
  {/if}
</div>

{#if type}
  <div class="field-section"><div class="field-section-title">Participants</div>
    {#each roles as role (role.id)}
      <div style="margin:4px 0">
        <strong>{role.name}</strong>
        {#each eventDraftState.participants as p, i (i)}
          {#if p.role_id === role.id}
            <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
              {p.sorte_id ? 'sorte : ' : ''}{p.name || '« inconnu »'}
              {#if p.entity_id && !(playerCharIds && playerCharIds.has(p.entity_id))}
                <label title="Il garde le secret"><input type="checkbox" bind:checked={p.secret}> secret</label>
              {/if}
              {#if !p.saved}
                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeParticipant(i)}>✕</button>
              {/if}
            </span>
          {/if}
        {/each}
        <select onchange={(ev) => onAdd(role, ev)}>
          <option value="">— ajouter —</option>
          {#each candidates(role) as e (e.id)}<option value={'entity:' + e.id}>{e.name}</option>{/each}
          {#if role.accepts_sorte}
            {#each activeSortes as s (s.id)}<option value={'sorte:' + s.id}>sorte : {s.name}</option>{/each}
          {/if}
        </select>
      </div>
    {/each}
  </div>

  <div class="field-section"><div class="field-section-title">Qui l'apprend, en plus des participants</div>
    <label><input type="checkbox" bind:checked={eventDraftState.customScopes}> Choisir pour cet événement</label>
    {#if !eventDraftState.customScopes}
      <div style="color:var(--muted); font-size:12px;">Celle du type : {typeScopeLine(type)}</div>
    {:else}
      {#each eventDraftState.scopes as scope, k (k)}
        <div style="display:flex; gap:6px; align-items:center; margin:2px 0">
          <select bind:value={scope.scope_type} onchange={() => (scope.scope_id = null)}>
            {#each SCOPE_TYPES as st (st.value)}<option value={st.value}>{st.label}</option>{/each}
          </select>
          {#if scope.scope_type !== 'world'}
            <select bind:value={scope.scope_id}>
              <option value={null}>— choisir —</option>
              {#each scopeTargets(scope.scope_type) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
            </select>
          {/if}
          <select bind:value={scope.level}>
            {#each vocabState.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
          </select>
          <button class="btn-icon" title="Retirer" onclick={() => eventDraftState.scopes.splice(k, 1)}>✕</button>
        </div>
      {/each}
      {#if !eventDraftState.scopes.length}<div style="color:var(--muted); font-size:12px;">Personne d'autre.</div>{/if}
      <button onclick={() => eventDraftState.scopes.push({ scope_type: 'world', scope_id: null, level: 'knows' })}>+ portée</button>
    {/if}
  </div>
{/if}

{#if !isNew}
  <div class="field-section"><span style="color:var(--muted); font-size:12px;">Enregistré : {event.recorded_at || ''}</span></div>
{/if}

{#if isNew}
  <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
    <button class="btn-send" onclick={onSave}>+ Créer l'événement</button>
  </div>
{/if}
