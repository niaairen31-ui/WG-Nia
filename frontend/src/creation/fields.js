/* TICKET-0058 (BRIEF-0058-f). Read-back for the ported field engine --
   authorReadField's coercion rules, moved verbatim (per-field rendering
   itself lives in Field.svelte as real Svelte markup for the core entity
   types; renderFieldHtml below is a SEPARATE, string-returning sibling used
   ONLY by Sheet.svelte's 'creation:field-render' listener, which answers
   evenements' still-legacy renderEventSheet/evenementsRenderCreatePanel --
   evenements stays bridged until brief -j, per RECON-SUPPLEMENT-0058's -f
   section, and its rendering builds a raw HTML string the same way
   authorRenderField always did, so the bridge needs a string producer, not
   a component. The two are intentionally kept side by side in this one
   small file rather than scattered, to keep them from drifting apart.

   Both take `doc` explicitly (never a bare `document`): every field this
   reads/renders lives in the LEGACY document, whether the element was
   created by Field.svelte (mounted there, TICKET-0056) or by evenements'
   own innerHTML write. */
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export function renderFieldHtml(field, value, idPrefix, ctx) {
  ctx = ctx || {};
  if (value === undefined && field.default !== undefined) value = field.default;
  const id = `${idPrefix}-${field.name}`;
  const label = `${esc(field.label)}${field.required ? ' *' : ''}`;
  switch (field.kind) {
    case 'textarea':
      return `<div class="field-row"><label for="${id}">${label}</label>
        <textarea id="${id}" data-field="${esc(field.name)}" data-kind="textarea">${esc(value ?? '')}</textarea></div>`;
    case 'json':
      return `<div class="field-row"><label for="${id}">${label}</label>
        <textarea id="${id}" data-field="${esc(field.name)}" data-kind="json" placeholder="null"
          >${value != null ? esc(JSON.stringify(value, null, 2)) : ''}</textarea></div>`;
    case 'bool':
      return `<div class="field-row checkbox">
        <input type="checkbox" id="${id}" data-field="${esc(field.name)}" data-kind="bool" ${value ? 'checked' : ''}>
        <label for="${id}">${label}</label></div>`;
    case 'number':
      return `<div class="field-row"><label for="${id}">${label}</label>
        <input type="number" id="${id}" data-field="${esc(field.name)}" data-kind="number"
          ${field.min != null ? `min="${field.min}"` : ''} ${field.max != null ? `max="${field.max}"` : ''}
          value="${value != null ? esc(value) : ''}"></div>`;
    case 'select': {
      const opts = (field.options || []).map((o) =>
        `<option value="${esc(o)}" ${o === value ? 'selected' : ''}>${esc(o === '' ? '—' : o)}</option>`
      ).join('');
      return `<div class="field-row"><label for="${id}">${label}</label>
        <select id="${id}" data-field="${esc(field.name)}" data-kind="select">${opts}</select></div>`;
    }
    case 'datalist': {
      // event_fields' only datalist field is 'type' (plain options, no
      // location_type catalog/gabarit special-case -- that path is
      // core-sheet-only, ported into Field.svelte instead).
      const dlid = `${id}-dl`;
      const opts = (field.options || []).map((o) => `<option value="${esc(o)}">`).join('');
      return `<div class="field-row"><label for="${id}">${label}</label>
        <input type="text" id="${id}" data-field="${esc(field.name)}" data-kind="text" list="${dlid}" value="${esc(value ?? '')}">
        <datalist id="${dlid}">${opts}</datalist></div>`;
    }
    case 'entity_ref': {
      const candidates = (ctx.entities || []).filter((e) => e.type === field.ref_type);
      const opts = ['<option value="">—</option>'].concat(
        candidates.map((e) => `<option value="${esc(e.id)}" ${e.id === value ? 'selected' : ''}>${esc(e.name)}</option>`)
      ).join('');
      return `<div class="field-row"><label for="${id}">${label}</label>
        <select id="${id}" data-field="${esc(field.name)}" data-kind="entity_ref">${opts}</select></div>`;
    }
    default:
      return `<div class="field-row"><label for="${id}">${label}</label>
        <input type="text" id="${id}" data-field="${esc(field.name)}" data-kind="text" value="${esc(value ?? '')}"></div>`;
  }
}

export function readFieldValue(doc, field, idPrefix) {
  const el = doc.getElementById(`${idPrefix}-${field.name}`);
  switch (field.kind) {
    case 'bool':
      return el.checked;
    case 'number':
      return el.value === '' ? null : Number(el.value);
    case 'json': {
      const raw = el.value.trim();
      return raw ? JSON.parse(raw) : null;
    }
    default:
      return el.value;
  }
}
