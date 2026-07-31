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

export function showSurface(key) {
  const entry = LEGACY_MOUNTS[key];
  if (!entry) {
    throw new Error(`legacy/bridge: unknown surface key ${JSON.stringify(key)}`);
  }
  const win = legacyWindow();
  const fn = win[entry.showFn];
  if (typeof fn !== 'function') {
    throw new Error(`legacy/bridge: ${entry.showFn} is not a function on the legacy window`);
  }
  fn.call(win);
}

export function whenLegacyReady(predicate, { timeoutMs = 5000 } = {}) {
  const win = legacyWindow();
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function poll() {
      let ok;
      try {
        ok = predicate(win);
      } catch (err) {
        reject(err);
        return;
      }
      if (ok) {
        resolve();
        return;
      }
      if (Date.now() - start >= timeoutMs) {
        reject(new Error('legacy/bridge: whenLegacyReady timed out'));
        return;
      }
      setTimeout(poll, 50);
    }
    poll();
  });
}
