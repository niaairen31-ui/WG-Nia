/* TICKET-0056 (A2). The legacy-mount registry: an enumerated,
   MONOTONICALLY SHRINKING list of surfaces still served by the legacy
   vanilla-JS document. One entry is removed by each surface-migration
   ticket; exactly one (play) survives at TICKET-0061, until Play's own
   rewrite on its own stack. Adding an entry is a fail-closed error --
   tooling/verify/checks/legacy_mount.py compares this set against
   tooling/verify/baselines/legacy_mounts.baseline and refuses any key
   that is not already there. */
export const LEGACY_MOUNTS = Object.freeze({
  play:        Object.freeze({ showFn: 'showPlayView',        retiredBy: 'TICKET-0061' }),
  creation:    Object.freeze({ showFn: 'showCreationView',    retiredBy: 'TICKET-0059' }),
  observation: Object.freeze({ showFn: 'showObservationView', retiredBy: 'TICKET-0060' }),
});

export const LEGACY_SURFACES = Object.freeze(Object.keys(LEGACY_MOUNTS));
