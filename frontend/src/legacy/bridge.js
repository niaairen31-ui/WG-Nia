/* TICKET-0056 (B1). The sole module permitted to reach into the legacy
   document. Shell and legacy are same-origin, so surface switching is a
   direct call on the legacy window -- no postMessage, one direction of
   control. legacy_mount.py confines `contentWindow` / `legacy-frame`
   tokens to this file and LegacyFrame.svelte. */
import { LEGACY_MOUNTS } from './registry.js';

let frame = null;

function legacyWindow() {
  if (!frame) {
    throw new Error('legacy/bridge: mountLegacy(frameEl) has not been called yet');
  }
  return frame.contentWindow;
}

export function mountLegacy(frameEl) {
  frame = frameEl;
  return new Promise((resolve) => {
    frame.addEventListener('load', () => resolve(), { once: true });
  });
}

function callLegacy(fnName, ...args) {
  const win = legacyWindow();
  const fn = win[fnName];
  if (typeof fn !== 'function') {
    throw new Error(`legacy/bridge: ${fnName} is not a function on the legacy window`);
  }
  return fn.apply(win, args);
}

export function showSurface(key) {
  const entry = LEGACY_MOUNTS[key];
  if (!entry) {
    throw new Error(`legacy/bridge: unknown surface key ${JSON.stringify(key)}`);
  }
  callLegacy(entry.showFn);
}

/* TICKET-0056: the legacy header is SUPPRESSED, not deleted -- index.html
   is byte-untouched by this ticket. Injecting one scoped style into the
   frame document is reversible, confined to this module, and covered by
   legacy_mount.py's confinement assertion. */
export function hideLegacyHeader() {
  const doc = legacyWindow().document;
  if (doc.getElementById('shell-injected')) return;
  const style = doc.createElement('style');
  style.id = 'shell-injected';
  style.textContent = 'header { display: none !important; }';
  doc.head.appendChild(style);
}

export function legacyDocument() {
  return legacyWindow().document;
}

/* TICKET-0058 (BRIEF-0058-f). Generic passthrough for the sheet's still-legacy
   sub-editor generators (roles/subculture/geometry/doors/relations/knowledge/
   pending-knowledge/pending-goals/pricing/membership-form/disc-detail-form/
   goal-form/generate-panel — all Scope OUT, brief -g/-h) and loaders
   (authorLoadItems/Ledger/Memberships/Goals/FactionMembersPanel/DiscDetails,
   authorMembershipFactionChanged) Sheet.svelte calls after rendering its own
   skeleton — exactly the tail authorRenderSheet used to run inline, just
   invoked from across the shell/legacy boundary instead of in the same
   function body. Every one of these stays a plain, unmigrated legacy
   function; nothing about their own behavior changes. */
export function legacyCall(fnName, ...args) {
  return callLegacy(fnName, ...args);
}
