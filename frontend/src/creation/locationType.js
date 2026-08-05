/* TICKET-0058 (BRIEF-0058-g, family a -- the Lieux create/save flow, per
   RECON-SUPPLEMENT-0058's -g section). Faithful port of
   _authorLocationTypeOptionLabel/_authorOpenTemplateModalFor/
   _authorPromptLocationTypeClassification/_authorClassifyLocationType
   (index.html, now deleted).

   TICKET-0059 (BRIEF-0059-h commit 1, lock O1). The modal half moved out:
   this is a plain module, not a component, so it cannot own Modal.svelte's
   open/close state -- that now lives in LocationTypeModal.svelte,
   instantiated by each of the flow's trigger points. What stays here is
   pure/data only: locationTypeOptionLabel (the datalist label formatter),
   readLocationTypeName (Field.svelte's uncontrolled-input read-back --
   RoomBatch.svelte's own input is two-way bound, so it reads its value
   directly and doesn't need this), resolveClassificationDefaults (the
   catalog lookup LocationTypeModal.svelte primes its width/height inputs
   from) and classifyLocationType (the POST + catalog refresh + reverse-
   bridge dispatch, still legacyCall-free -- it never opened the modal). */
import { creationState } from './state.svelte.js';

export function locationTypeOptionLabel(row) {
  if (row.default_width == null || row.default_height == null) return row.name;
  const classLabel = row.classification === 'interior' ? 'interieur'
    : row.classification === 'exterior' ? 'exterieur' : (row.classification || '?');
  return `${row.name} (${classLabel}, ${row.default_width} x ${row.default_height} m)`;
}

export function readLocationTypeName(legacyDoc, fieldId) {
  const inputEl = legacyDoc.getElementById(fieldId);
  return (inputEl ? inputEl.value : '').trim();
}

export function resolveClassificationDefaults(typeName) {
  const folded = typeName.trim().toLowerCase();
  const catalogRow = creationState.locationTypeCatalog.find((r) => r.name.toLowerCase() === folded);
  return {
    prefWidth: catalogRow && catalogRow.default_width != null ? catalogRow.default_width : '',
    prefHeight: catalogRow && catalogRow.default_height != null ? catalogRow.default_height : '',
  };
}

export async function classifyLocationType(legacyDoc, typeName, classification, widthVal, heightVal) {
  const body = { name: typeName, classification };
  if (widthVal !== '') {
    body.default_width = parseFloat(widthVal);
    body.default_height = parseFloat(heightVal);
  }
  const postRes = await fetch('/api/location-types', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const postData = await postRes.json().catch(() => ({ detail: postRes.statusText }));
  if (!postRes.ok) throw new Error(postData.detail || JSON.stringify(postData));

  const catalog = await fetch('/api/location-types').then((r) => r.json());
  creationState.locationTypeCatalog = catalog;
  // Still-legacy readers (authorLocationTypeCatalog, batchRenderManifestTable)
  // keep their own mirror of the catalog fed by this same event
  // (index.html's 'creation:entities-loaded' listener) -- same shape
  // EntityList.svelte's own dispatch already uses.
  legacyDoc.dispatchEvent(new CustomEvent('creation:entities-loaded', {
    detail: {
      entities: creationState.entities,
      playerCharIds: Array.from(creationState.playerCharIds),
      locationTree: creationState.locationTree,
      locationTypeCatalog: catalog,
    },
  }));
}
