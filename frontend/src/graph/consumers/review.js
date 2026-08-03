/* TICKET-0057 (BRIEF-0058-j: reached by plain import, not the legacy
   bridge, now that both consumers -- Region.svelte and RoomBatch.svelte --
   are Svelte-native). The review pre-commit preview -- region generation
   and the room batch generator both feed this consumer through the same
   descriptor `graph` spec (`consumer: 'review'`). This one fetches
   nothing: the data is already in memory as the registering component's
   own draft state, reached via `reviewGraphData(key)`'s shared
   REVIEW_DESCRIPTORS singleton. Read-only by construction -- no callback
   is supplied, so the primitive renders with no drag, no connect, no edge
   deletion (nothing is committed yet, and draft nodes carry no entity ids
   to write against). */
import { reviewGraphData } from '../../creation/review/registry.js';

export default {
  dashedKinds: ['connection'],

  async load(meta) {
    return reviewGraphData(meta.key);
  },
};
