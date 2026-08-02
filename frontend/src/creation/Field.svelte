<script>
  /* TICKET-0058 (BRIEF-0058-f). One field-spec rendered as a labeled form
     control -- faithful port of authorRenderField (index.html, now
     deleted), kept as real Svelte markup (not an {@html} string) so the
     generic kinds need no cross-realm bridge at all. Read-back stays
     imperative (fields.js's readFieldValue, called from Sheet.svelte at
     save time via legacyDoc.getElementById) rather than two-way bound --
     this is a port, not a redesign of the field engine's state model.

     The two kinds that reach legacy code (location_type's catalog options
     and its "Gabarit..." button) call the SAME still-legacy functions the
     original inline handlers called (_authorLocationTypeOptionLabel,
     _authorOpenTemplateModalFor) via the generic legacyCall bridge --
     those functions stay legacy (brief -g's Lieux create/save flow
     family), unchanged.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { legacyCall } from '../legacy/bridge.js';

  let { field, value, idPrefix, ctx } = $props();

  const id = $derived(`${idPrefix}-${field.name}`);
  const dlid = $derived(`${id}-dl`);
  const label = $derived(`${field.label}${field.required ? ' *' : ''}`);
  const resolvedValue = $derived(value === undefined && field.default !== undefined ? field.default : value);
</script>

{#if field.kind === 'textarea'}
  <div class="field-row"><label for={id}>{label}</label>
    <textarea {id} data-field={field.name} data-kind="textarea" value={resolvedValue ?? ''}></textarea></div>
{:else if field.kind === 'json'}
  <div class="field-row"><label for={id}>{label}</label>
    <textarea {id} data-field={field.name} data-kind="json" placeholder="null"
      >{resolvedValue != null ? JSON.stringify(resolvedValue, null, 2) : ''}</textarea></div>
{:else if field.kind === 'bool'}
  <div class="field-row checkbox">
    <input type="checkbox" {id} data-field={field.name} data-kind="bool" checked={!!resolvedValue}>
    <label for={id}>{label}</label>
  </div>
{:else if field.kind === 'number'}
  <div class="field-row"><label for={id}>{label}</label>
    <input type="number" {id} data-field={field.name} data-kind="number"
      min={field.min ?? undefined} max={field.max ?? undefined}
      value={resolvedValue != null ? resolvedValue : ''}></div>
{:else if field.kind === 'select'}
  <div class="field-row"><label for={id}>{label}</label>
    <select {id} data-field={field.name} data-kind="select">
      {#each (field.options || []) as o (o)}
        <option value={o} selected={o === resolvedValue}>{o === '' ? '—' : o}</option>
      {/each}
    </select>
  </div>
{:else if field.kind === 'datalist'}
  <div class="field-row"><label for={id}>{label}</label>
    <div style="display:flex; gap:6px; align-items:center">
      <input type="text" {id} data-field={field.name} data-kind="text" list={dlid} value={resolvedValue ?? ''} style="flex:1">
      {#if field.name === 'location_type'}
        <button type="button" class="btn-ghost" style="font-size:12px; padding:3px 8px"
          onclick={() => legacyCall('_authorOpenTemplateModalFor', id)}>Gabarit...</button>
      {/if}
    </div>
    <datalist id={dlid}>
      {#if field.name === 'location_type'}
        {#each (ctx.locationTypeCatalog || []) as r (r.name)}
          <option value={r.name}>{legacyCall('_authorLocationTypeOptionLabel', r)}</option>
        {/each}
      {:else}
        {#each (field.options || []) as o (o)}
          <option value={o}></option>
        {/each}
      {/if}
    </datalist>
  </div>
{:else if field.kind === 'entity_ref'}
  {@const candidates = (ctx.entities || []).filter((e) => e.type === field.ref_type && !(field.exclude_self && ctx.entityId && e.id === ctx.entityId))}
  <div class="field-row"><label for={id}>{label}</label>
    <select {id} data-field={field.name} data-kind="entity_ref" disabled={!!field.readonly}>
      <option value="">—</option>
      {#each candidates as e (e.id)}
        <option value={e.id} selected={e.id === resolvedValue}>{e.name}</option>
      {/each}
    </select>
  </div>
{:else}
  <div class="field-row"><label for={id}>{label}</label>
    <input type="text" {id} data-field={field.name} data-kind="text" value={resolvedValue ?? ''}></div>
{/if}
