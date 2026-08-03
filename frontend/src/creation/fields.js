/* TICKET-0058 (BRIEF-0058-f). Read-back for the ported field engine --
   authorReadField's coercion rules, moved verbatim (per-field rendering
   itself lives in Field.svelte as real Svelte markup, used by every field
   consumer including evenements' <Field>, BRIEF-0058-j).

   Takes `doc` explicitly (never a bare `document`): every field this reads
   lives in the LEGACY document, since Field.svelte mounts there
   (TICKET-0056). */
export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
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
