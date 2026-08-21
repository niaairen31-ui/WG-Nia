/* TICKET-0056 (A2). The legacy-mount registry: an enumerated,
   MONOTONICALLY SHRINKING list of surfaces still served by the legacy
   vanilla-JS document. One entry is removed by each surface-migration
   ticket; exactly one (play) survives at TICKET-0061, until Play's own
   rewrite on its own stack. Adding an entry is a fail-closed error --
   tooling/verify/checks/legacy_mount.py compares this set against
   tooling/verify/baselines/legacy_mounts.baseline and refuses any key
   that is not already there.

   TICKET-0059 (BRIEF-0059-l commit 4): `creation` retired -- Creation is a
   shell-native Svelte component now (App.svelte drives frontend/src/
   creation/Creation.svelte directly, commit 1), never mounted inside this
   iframe. legacy_call.py rule 7's gate (a TICKET-0059 bridge-reach record
   survives only while this mount exists) was already vacuously satisfied
   before this edit -- legacy_calls.baseline held zero TICKET-0059 records
   once commit 3 landed.

   TICKET-0060 (BRIEF-0060-b commit 4): `observation` retired the same way
   -- Observation is a shell-native Svelte component now
   (frontend/src/observation/Observation.svelte, mounted directly by
   App.svelte). `play` alone remains, retiring at TICKET-0061 on its own
   stack.

   TICKET-0061 (A3). The contradiction above is settled: `play` SURVIVES
   this ticket. TICKET-0056's own decision entry said so ("survives to
   TICKET-0061 and beyond, until its own rewrite"); TICKET-0060's entry
   later said the opposite ("TICKET-0061 empties LEGACY_MOUNTS"), and this
   field carried that second reading. Resolved in favour of TICKET-0056 and
   repointed at TICKET-0069, the Play migration, deposited paused. Rule 3b
   (legacy_mount.py) now asserts that ticket exists and is not done, so
   this field can no longer be a well-formed sentence naming a finished
   ticket. */
export const LEGACY_MOUNTS = Object.freeze({
  play: Object.freeze({ showFn: 'showPlayView', retiredBy: 'TICKET-0069' }),
});

export const LEGACY_SURFACES = Object.freeze(Object.keys(LEGACY_MOUNTS));
