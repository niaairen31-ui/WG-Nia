/* TICKET-0126 (BRIEF-0126-I, C-15, W1'). The creator's read of submitted
   character drafts: the PJ list's « Soumis » group and the one draft open
   in the right column (PcDraftPanel.svelte). Read only -- the review is
   TICKET-0129. Its own fetch helper, the shape of tabs.js' `api`, so this
   module imports nothing from tabs.js. */

import { creationState } from './state.svelte.js';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) {
    let msg = `${path} -> ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') msg = body.detail;
    } catch (_err) {
      // response body wasn't JSON -- keep the status-based message
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function loadSubmittedDrafts() {
  try {
    creationState.submittedDrafts = await api('/api/pc-drafts');
  } catch (_err) {
    creationState.submittedDrafts = [];
  }
}

export function selectPcDraft(id) {
  creationState.selectedGermId = null;
  creationState.selectedPcDraftId = id;
}

export function loadPcDraft(id) {
  return api(`/api/pc-drafts/${encodeURIComponent(id)}`);
}
