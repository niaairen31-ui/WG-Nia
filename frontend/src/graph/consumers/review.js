/* TICKET-0057. The review pre-commit preview -- region generation and the
   room batch generator both feed this consumer through the same
   descriptor `graph` spec (`consumer: 'review'`). Unlike the Lieux
   consumer, this one fetches nothing: the data is already in memory as
   the legacy document's draft state, reached via `reviewGraphData(key)`
   through the bridge. Read-only by construction -- no callback is
   supplied, so the primitive renders with no drag, no connect, no edge
   deletion (nothing is committed yet, and draft nodes carry no entity
   ids to write against). */
import { reviewGraphData } from '../../legacy/bridge.js';

export default {
  dashedKinds: ['connection'],

  async load(meta) {
    return reviewGraphData(meta.key);
  },
};
