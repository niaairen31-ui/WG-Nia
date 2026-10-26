/* TICKET-0129 (BRIEF-0129-F, C-15). The creator's review of a submitted
   character draft: her choices, the batches per group, the return and the
   approval. Every write goes through `api` (sheetRequest.svelte.js). */

import { creationState } from './state.svelte.js';
import { loadSubmittedDrafts } from './pcDrafts.svelte.js';
import { api } from './sheetRequest.svelte.js';

function review(id) {
  return `/api/pc-reviews/${encodeURIComponent(id)}`;
}

function batch(batchId) {
  return `/api/npc-batches/${encodeURIComponent(batchId)}`;
}

function send(method, body) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  };
}

export function loadReview(id) {
  return api(review(id));
}

export function saveReview(id, body) {
  return api(review(id), send('PUT', body));
}

export function returnDraft(id, note) {
  return api(`${review(id)}/renvoyer`, send('POST', { note }));
}

export function prepareLot(id, label) {
  return api(`${review(id)}/lots`, send('POST', { group_label: label }));
}

export function loadLot(batchId) {
  return api(batch(batchId));
}

export async function runLot(batchId, onStep) {
  let step = await api(`${batch(batchId)}/run-next`, send('POST'));
  if (onStep) onStep(step);
  while (step.npcs_done < step.npcs_total) {
    step = await api(`${batch(batchId)}/run-next`, send('POST'));
    if (onStep) onStep(step);
  }
  return step;
}

export function setLotRow(batchId, rowId, patch) {
  return api(`${batch(batchId)}/rows/${encodeURIComponent(rowId)}`, send('PATCH', patch));
}

export function abandonLot(batchId) {
  return api(`${batch(batchId)}/abandon`, send('POST'));
}

export function approveDraft(id) {
  return api(`${review(id)}/approuver`, send('POST'));
}

export function afterApproval() {
  creationState.selectedPcDraftId = null;
  loadSubmittedDrafts();
  creationState.entityListActivationTick += 1;
}

export function afterReturn() {
  creationState.selectedPcDraftId = null;
  loadSubmittedDrafts();
}
