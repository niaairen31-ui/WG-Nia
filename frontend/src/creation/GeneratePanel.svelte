<script>
  /* TICKET-0058 (BRIEF-0058-h). Faithful port of authorRenderGeneratePanel/
     authorGenerateEntity (index.html, now deleted) -- the AI entity-
     authoring assistant's draft-generate panel (BRIEF-24), mounted by
     Sheet.svelte in place of the legacy {@html legacyCall(
     'authorRenderGeneratePanel')} call, for a NEW character/location/
     faction sheet only (Sheet.svelte's showGeneratePanel gate, unchanged).

     POST /api/entities/generate writes no canon (entity_author.py) -- the
     creator edits the pre-filled form freely; accepting goes through the
     EXISTING create control (Sheet.svelte's submitEntity) and the EXISTING
     knowledge/goals/roles/subculture CRUD endpoints. There is no path from
     this component to a write call: applyGeneratedDraft (generatePanel.
     svelte.js) only ever sets form-field values and draft state, never
     fetch()es a mutating endpoint. One-shot (F2 conversational refine is
     out of scope): a second "Générer" click discards the previous draft
     state and starts over, same as the legacy panel always did.

     `type` is Sheet.svelte's own resolved entity type (character/location/
     faction) -- not re-derived from the active tab here, unlike the legacy
     authorGenerateEntity which read currentCreationSubTab directly.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { generatePanelState, applyGeneratedDraft } from './generatePanel.svelte.js';

  let { legacyDoc, type } = $props();

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  async function generate() {
    const brief = generatePanelState.brief.trim();
    if (!brief) { generatePanelState.status = 'Intention requise.'; return; }

    generatePanelState.status = 'Génération…';
    let result;
    try {
      result = await api('/api/entities/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_type: type, brief }),
      });
    } catch (e) {
      generatePanelState.status = e.message;
      return;
    }

    if (!result || result.ok === false) {
      generatePanelState.status = (result && result.error) || 'Échec de la génération.';
      return; // form untouched
    }

    applyGeneratedDraft(legacyDoc, type, result);
  }
</script>

<div class="field-section" id="entity-gen-panel" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:12px;">
  <div class="field-section-title">Générer avec l'IA</div>
  <textarea rows="2" style="width:100%; resize:vertical"
    placeholder="Intention en une phrase, ex. : « Un ancien soldat devenu aubergiste, bourru, qui en sait trop sur la disparition du marchand Aldric »"
    bind:value={generatePanelState.brief}></textarea>
  <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
    <button class="btn-send" onclick={generate}>Générer</button>
    <span style="font-size:12px; color:var(--muted)">{generatePanelState.status}</span>
  </div>
  {#if generatePanelState.notes.length}
    <div class="field-section-title" style="margin-top:8px">Notes de l'assistant</div>
    <div class="row-table">
      {#each generatePanelState.notes as n}
        <div class="row-card" style="font-size:12px; color:var(--muted)">{n}</div>
      {/each}
    </div>
  {/if}
</div>
