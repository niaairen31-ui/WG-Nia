<script>
  /* TICKET-0099 (BRIEF-0099-b, C1 + D2 + H1). The Compétences list, rendered
     by EntityList.svelte in its record mode inside #author-entity-list --
     the same sidebar every entity tab uses. It never opens a fiche itself:
     every click hands a C-01 record to `onSelect`, which is EntityList's
     own onSelectRecord (creationSelectRecord, tabs.js), so the fiche opens
     through the one record path intrigues/evenements already use.

     Four sections, top to bottom:
       Brouillons       -- the assistant entry (H1), then every draft row.
       Systèmes         -- each system is a row of its own (its fiche), its
                           skills indented under it (C1).
       Sans système     -- skills with no live system, only when non-empty.
       Trous du lexique -- read-only gaps (BRIEF-0084-d); a click creates a
                           draft named after the gap and opens it.

     No scoped <style> block: every class here is already styled by
     frontend/public/creation.css / shared.css (EntityList.svelte applies
     the same ones). */
  import { creationState } from './state.svelte.js';
  import {
    competencesState, NO_SYSTEM_LABEL, ASSISTANT_RECORD_ID, groupSkillsBySystem,
    skillRecord, systemRecord, draftRecord, assistantRecord, addGapDraft,
  } from './competences.svelte.js';

  let { onSelect } = $props();

  const groups = $derived(groupSkillsBySystem(competencesState.rows, competencesState.systems));
  const systemGroups = $derived(groups.filter((g) => g.system));
  const unassigned = $derived(groups.find((g) => !g.system));

  function onKey(ev, record) {
    if (ev.key === 'Enter') onSelect(record);
  }

  function openGap(surfaceForm) {
    onSelect(addGapDraft(surfaceForm));
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  }
</script>

<div class="lieux-bucket-head">Brouillons</div>
<div class="author-list-item {creationState.selectedRecordId === ASSISTANT_RECORD_ID ? 'active' : ''}"
     role="button" tabindex="0"
     onclick={() => onSelect(assistantRecord())} onkeydown={(ev) => onKey(ev, assistantRecord())}>
  <div class="ali-name">✦ Générer avec l'assistant</div>
  <div class="ali-meta">Proposer des compétences à partir d'une intention</div>
</div>
{#each competencesState.draft as d (d.key)}
  <div class="author-list-item {creationState.selectedRecordId === `draft:${d.key}` ? 'active' : ''}"
       role="button" tabindex="0"
       onclick={() => onSelect(draftRecord(d))} onkeydown={(ev) => onKey(ev, draftRecord(d))}>
    <div class="ali-name">{d.name || '(sans nom)'}</div>
    <div class="ali-meta"><span class="badge b-other">brouillon</span> {d.base_domain || '— domaine —'}</div>
  </div>
{/each}

{#if systemGroups.length}
  <div class="lieux-bucket-head">Systèmes</div>
  {#each systemGroups as group (group.system.id)}
    <div class="author-list-item {creationState.selectedRecordId === group.system.id ? 'active' : ''}"
         role="button" tabindex="0"
         onclick={() => onSelect(systemRecord(group.system))} onkeydown={(ev) => onKey(ev, systemRecord(group.system))}>
      <div class="ali-name" style="font-weight:600">{group.system.name}</div>
      <div class="ali-meta">Système · {group.system.skill_count} compétence(s)</div>
    </div>
    {#each group.skills as row (row.id)}
      <div class="author-list-item {creationState.selectedRecordId === row.id ? 'active' : ''}"
           style="padding-left:28px" role="button" tabindex="0"
           onclick={() => onSelect(skillRecord(row))} onkeydown={(ev) => onKey(ev, skillRecord(row))}>
        <div class="ali-name">{row.name}</div>
        <div class="ali-meta">{row.base_domain}</div>
      </div>
    {/each}
  {/each}
{/if}

{#if unassigned}
  <div class="lieux-bucket-head">{NO_SYSTEM_LABEL}</div>
  {#each unassigned.skills as row (row.id)}
    <div class="author-list-item {creationState.selectedRecordId === row.id ? 'active' : ''}"
         role="button" tabindex="0"
         onclick={() => onSelect(skillRecord(row))} onkeydown={(ev) => onKey(ev, skillRecord(row))}>
      <div class="ali-name">{row.name}</div>
      <div class="ali-meta">{row.base_domain}</div>
    </div>
  {/each}
{/if}

{#if !systemGroups.length && !unassigned}
  <div class="empty">Aucune compétence propre à ce monde.</div>
{/if}

<div class="lieux-bucket-head">Trous du lexique</div>
{#if competencesState.gapsError}
  <div class="empty">{competencesState.gapsError}</div>
{:else if competencesState.gaps.length === 0}
  <div class="empty">Aucun trou détecté.</div>
{:else}
  {#each competencesState.gaps as gap (gap.surface_form)}
    <div class="author-list-item" role="button" tabindex="0"
         onclick={() => openGap(gap.surface_form)}
         onkeydown={(ev) => { if (ev.key === 'Enter') openGap(gap.surface_form); }}>
      <div class="ali-name">{gap.surface_form}</div>
      <div class="ali-meta">{gap.count} occurrence(s) · {fmtDate(gap.last_seen)}</div>
    </div>
  {/each}
{/if}
{#if competencesState.arbiterFailures.error > 0 || competencesState.arbiterFailures.empty > 0}
  <div style="padding:6px 14px; font-size:11px; color:var(--muted)">
    Échecs de l'arbitre (hors lexique) : {competencesState.arbiterFailures.error} erreur(s), {competencesState.arbiterFailures.empty} réponse(s) vide(s)
  </div>
{/if}
