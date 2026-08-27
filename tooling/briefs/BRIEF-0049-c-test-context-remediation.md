# BRIEF-0049-c — Step "test_context.py -> test DB (G1 + H1)"

## Context
`scripts/test_context.py` is the current prod polluter: it imports
`world_engine.db.engine` directly (RECON anchor test_context.py:33) and hard-codes
prod IDs `npc-maelis` / `char-player` / `loc-dernier-verre` (test_context.py:38-40),
so it reads (and its setup path can touch) the prod DB. This step converts it to
run against the seeded test DB and to reference the deterministic fixture IDs
from `seed_test.py` (G1 + H1). After this brief, no test script reaches prod.

## Mini-RECON (execute first, REPORT ONLY, no edits)
1. `sed -n '30,45p' scripts/test_context.py` — re-confirm the import at line ~33
   and the three hard-coded ID constants at ~38-40. If line numbers moved,
   re-anchor and REPORT.
2. `grep -n "def main\|SEED\|ID =\|contract" scripts/seed_test.py` — read the
   deterministic-ID docstring block landed in BRIEF-0049-b and copy the EXACT
   fixture IDs (`world-test`, `loc-test-tavern`, `npc-test-keeper`,
   `char-test-player`) and the knowledge-row subjects. The constants in this
   brief must match that block verbatim. If they differ, the seed is the source
   of truth — REPORT the mismatch, do not guess.
3. Read the assertion body of `test_context.py` (the `results` list construction
   after line ~62) and confirm which subjects/thresholds it asserts on. The
   seeded rows from -b must satisfy every assertion. REPORT the mapping
   (assertion -> seeded row) so the live gate is traceable.

## Scope IN
1. **Add a fail-closed env guard** at the very top of `test_context.py`, BEFORE
   the `from world_engine.db import engine` import: if
   `os.environ.get("WORLD_ENGINE_ENV") != "test"` => print (verbatim)
   `test_context.py refuses to run unless WORLD_ENGINE_ENV=test (got: <value>).`
   and `sys.exit(1)`. This is the structural guarantee that this harness can
   never read prod again, independent of the resolver.
2. **Replace the three hard-coded ID constants** (test_context.py:38-40) with the
   fixture IDs from `seed_test.py`:
   - `NPC_ID = "npc-test-keeper"`
   - `PLAYER_ID = "char-test-player"`
   - `LOCATION_ID = "loc-test-tavern"`
3. **Update the module docstring** to describe the test-world scenario (keeper ->
   test player at the test tavern) instead of the Maelis/Joran prod scenario,
   and to state the `WORLD_ENGINE_ENV=test` requirement and the seed dependency.
4. **Adjust the assertion subjects/thresholds** only as needed so they name the
   subjects actually seeded in -b (e.g. the `share_threshold=50` row subject, the
   `65` row subject, the `personal_magic_incident` player secret). Keep the
   assertion *logic* (>= threshold visible, < threshold absent, is_secret absent)
   identical — only the referenced subject strings change to match the fixture.
5. **Leave the disclosure-policy semantics unchanged.** This is a rename/retarget
   of the fixture, not a rewrite of what the test proves.

## Scope OUT
- Do NOT convert this into a pytest test or add a pytest dependency. It stays a
  standalone operator script (consistent with the other two scratch scripts).
- Do NOT modify `seed_test.py` or `db.py`.
- Do NOT touch `test_ddl_atomicity.py` / `test_rollback_quarantine.py`.
- Do NOT add new assertions or broaden coverage — retarget only.
- Do NOT introduce ID auto-discovery (that was option H2, explicitly not chosen;
  H1 = reference the documented fixture IDs).

## Invariants to defend
- **Exclusion is structural**: the `is_secret` / `share_threshold` assertions
  must still prove that secrets and above-threshold rows are filtered at query
  construction, not by instruction. Do not weaken these assertions.
- **Fail-closed**: the env guard must exit non-zero when not `test`; it must not
  warn-and-continue.

## Done means
- [ ] `WORLD_ENGINE_ENV=test python scripts/seed_test.py` then
      `WORLD_ENGINE_ENV=test python scripts/test_context.py` => assertion report
      prints and ALL assertions pass against the seeded test world.
- [ ] `WORLD_ENGINE_ENV=prod python scripts/test_context.py` (or unset) => exits
      non-zero with the verbatim refusal message, reads nothing from prod.
- [ ] `grep -c "npc-maelis\|char-player\|loc-dernier-verre" scripts/test_context.py`
      => `0` (no prod IDs remain).
- [ ] `/review-step` and `/close-step` if `src/` touched (expected none — script
      only).

## Docs to update
- `test_context.py` docstring (Scope IN item 3). No schema/ARCHITECTURE change.
