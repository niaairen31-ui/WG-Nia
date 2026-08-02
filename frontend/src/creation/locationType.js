/* TICKET-0058 (BRIEF-0058-g, family a -- the Lieux create/save flow, per
   RECON-SUPPLEMENT-0058's -g section). Faithful port of
   _authorLocationTypeOptionLabel/_authorOpenTemplateModalFor/
   _authorPromptLocationTypeClassification/_authorClassifyLocationType
   (index.html, now deleted).

   locationTypeOptionLabel is pure and used directly by Field.svelte's
   location_type datalist. openTemplateModalFor/promptLocationTypeClassification/
   classifyLocationType together are the "Gabarit..." button's whole flow
   AND the save-time classification gate (Sheet.svelte's saveSheet) -- both
   need `legacyDoc` (every element they touch, including the generic modal
   genericModalOpen/Close renders into, lives in the legacy document) and
   both still reach genericModalOpen/genericModalClose via legacyCall, since
   that generic modal utility is used well beyond Creation and stays legacy.

   The room-batch generator (batchRenderManifestTable, index.html) still
   needs the option-label formatter and the template-modal trigger -- it is
   NOT migrated by this brief (brief -j). It reaches both through a tiny
   reverse-bridge CustomEvent pair Sheet.svelte listens for
   ('creation:location-type-label' / 'creation:open-location-type-modal'),
   the same idiom BRIEF-0058-f established for evenements'
   'creation:field-render'/'creation:field-read'. */
import { creationState } from './state.svelte.js';
import { legacyCall } from '../legacy/bridge.js';
import { esc } from './fields.js';

export function locationTypeOptionLabel(row) {
  if (row.default_width == null || row.default_height == null) return row.name;
  const classLabel = row.classification === 'interior' ? 'interieur'
    : row.classification === 'exterior' ? 'exterieur' : (row.classification || '?');
  return `${row.name} (${classLabel}, ${row.default_width} x ${row.default_height} m)`;
}

export function openTemplateModalFor(legacyDoc, fieldId, onClassified) {
  const inputEl = legacyDoc.getElementById(fieldId);
  const typeName = (inputEl ? inputEl.value : '').trim();
  if (!typeName) return;
  promptLocationTypeClassification(legacyDoc, typeName, onClassified);
}

export function promptLocationTypeClassification(legacyDoc, typeName, onClassified) {
  const folded = typeName.trim().toLowerCase();
  const catalogRow = creationState.locationTypeCatalog.find((r) => r.name.toLowerCase() === folded);
  const prefWidth = catalogRow && catalogRow.default_width != null ? catalogRow.default_width : '';
  const prefHeight = catalogRow && catalogRow.default_height != null ? catalogRow.default_height : '';
  legacyCall('genericModalOpen', 'Classification du type de lieu', `
    <p>Le type « ${esc(typeName)} » n'est pas encore classifié. Ce lieu est-il
    intérieur ou extérieur ? Ce choix est mémorisé pour les prochains lieux de
    ce type.</p>
    <div class="row-card-actions" style="margin-top:10px">
      <button class="btn-send" id="loctype-classify-interior">Interieur</button>
      <button class="btn-send" id="loctype-classify-exterior">Exterieur</button>
    </div>
    <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-top:10px">
      <label style="flex:1">Largeur par défaut (m)</label>
      <input type="number" step="any" id="loctype-classify-width" value="${prefWidth}" style="flex:1">
      <label style="flex:1">Hauteur par défaut (m)</label>
      <input type="number" step="any" id="loctype-classify-height" value="${prefHeight}" style="flex:1">
    </div>
    <div id="loctype-classify-status" style="color:var(--red); margin-top:6px"></div>
  `, { dismissOnBackdrop: false });
  legacyDoc.getElementById('loctype-classify-interior').onclick =
    () => classifyLocationType(legacyDoc, typeName, 'interior', onClassified);
  legacyDoc.getElementById('loctype-classify-exterior').onclick =
    () => classifyLocationType(legacyDoc, typeName, 'exterior', onClassified);
}

export async function classifyLocationType(legacyDoc, typeName, classification, onClassified) {
  const statusEl = legacyDoc.getElementById('loctype-classify-status');
  const widthVal = (legacyDoc.getElementById('loctype-classify-width').value || '').trim();
  const heightVal = (legacyDoc.getElementById('loctype-classify-height').value || '').trim();
  if ((widthVal === '') !== (heightVal === '')) {
    statusEl.textContent = 'Renseigne les deux dimensions, ou aucune.';
    return;
  }
  statusEl.textContent = '…';
  try {
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

    legacyCall('genericModalClose');
    await onClassified();
  } catch (e) {
    statusEl.textContent = e.message;
  }
}
