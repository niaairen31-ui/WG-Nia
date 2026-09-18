# BRIEF — Step "germ emission hygiene"

TICKET-0081, brief c of c. Decision R2. Independent of briefs a and b; it can
land before, between, or after them.

## Context

TICKET-0019 gave `entity_creation` germs a name-collision guard in TWO places —
at emission and again at approval — plus a per-scope-call quota. The day chain
grew its own germ emitter later (`day_concordance.emit_germs`, BRIEF-0075-c) and
inherited neither. Measured consequence: two days mentioning the same missing
person stack two identical pending germs, and `_find_applied_duplicate` never
sees them because it lives inside `_apply_mutation`, which `entity_creation`
never reaches (approval short-circuits before it). The pending-creations list
fills with duplicates that Nia has to weed by hand.

This step gives the day path the guards the tick path already has. It changes no
schema and touches one function.

## Mini-RECON

All [M], same tarball, `Current schema version: v1.96`.

- `emit_germs` (`day_concordance.py:219-257`): iterates `unmatched`, skips
  non-persons, computes `name = mention.role_hint or mention.surface_form`,
  builds a `ProposedMutation(mutation_type="entity_creation",
  source_type="pass_play", pass_play_id=..., status="proposed",
  proposed_by="local_ai")` and returns the list. It performs NO collision check
  and enforces NO quota. It writes nothing — `verify/checks/day_concordance.py`
  R1 (`:147`) enforces that, and this step must not break it.
- Its only caller is `_extract_and_concord` (`routes/day.py:423-441`), which
  stages the returned germs with `db.add(germ)` for the request's single commit.
  The resolve path deliberately does NOT re-emit (`routes/day.py:691-698`).
- Approval-side guard, for alignment: `_approve_entity_creation_shortcircuit`
  (`routes/mutations.py:561-591`) case-folds `payload["name"]` against all
  ACTIVE entities of the world and routes a collision to "Needs attention".
- Realization query, for the pending-duplicate definition:
  `list_pending_creations` (`routes/creator.py:149-182`) selects
  `mutation_type == "entity_creation"` and `status == "approved"`, then skips any
  payload carrying `created_entity_id`.
- Truncate-and-log idiom to mirror: `MAX_MENTIONS_PER_PASS` at
  `day_extract.py:33`, applied at `:114-121` with an INFO log naming the count
  dropped.
- `verify/checks/day_concordance.py` R3 (`:178-205`) already asserts
  `emit_germs` constructs at least one `ProposedMutation` and checks its field
  shape; R7 (`:305-322`) already asserts `MAX_MENTIONS_PER_PASS` is declared AND
  read. Both idioms are reused below.

## Scope IN

1. **Module-level quota constant** in `day_concordance.py`, with a comment in
   the same register as `day_extract.py:31-33`:

   ```python
   # Bound on germs emitted per declaration (BRIEF-0081-c). Over the bound,
   # truncate and report the count -- never silently drop the excess without a
   # log line.
   MAX_GERMS_PER_DECLARATION = 3
   ```

2. **Collision guard at emission.** Before constructing a germ, skip the
   candidate if its computed `name`, case-folded, equals the case-folded `name`
   of any ACTIVE `Entity` in the world. Same predicate as
   `_approve_entity_creation_shortcircuit`, evaluated here as well — the two
   guards are deliberately redundant, exactly as TICKET-0019 specified for the
   tick path. Log at INFO naming the skipped surface form and the colliding
   entity name.

3. **Pending-germ dedup at emission.** Skip the candidate if a
   `ProposedMutation` already exists in the same world with
   `mutation_type == "entity_creation"`, `status IN ('proposed', 'approved')`,
   no `created_entity_id` in its payload, and a case-folded `payload["name"]`
   equal to the candidate's. World scoping goes in the query construction;
   `created_entity_id` and the name comparison are applied over the fetched rows
   because `payload` is a JSON column — that post-fetch step is acceptable ONLY
   because the world scope is already in the query. Log at INFO naming the
   existing mutation id.

4. **Quota.** After the two guards, if more than `MAX_GERMS_PER_DECLARATION`
   candidates survive, keep the first `MAX_GERMS_PER_DECLARATION` in mention
   order and log at INFO the count truncated — mirroring
   `day_extract.py:114-121` in both shape and wording.

5. **Purity preserved.** All three additions are reads. `emit_germs` still
   contains no `db.add(` and no `.commit(`. If a guard cannot be expressed as a
   read, that is a STOP.

6. **Extraction if needed.** `emit_germs` is currently ~38 lines and this step
   adds branching. If it approaches the 80-line ceiling, extract the two guards
   into `_germ_blocked(name, ctx, db) -> Optional[str]` returning a reason string
   or None, and log the reason at the call site. Do not exempt.

7. **Check additions to `tooling/verify/checks/day_concordance.py`**, reusing the
   R7 declared-and-read idiom:
   - R11: `MAX_GERMS_PER_DECLARATION` is declared at module level AND read inside
     `emit_germs`. Fail if declared but unread.
   - R12: `emit_germs`' body (or the extracted helper's) contains a `select(`
     against `Entity` and a `select(` against `ProposedMutation`. Vacuous-proof:
     fail if zero `select(` calls are found in either.
   - R1 (purity) is unchanged and must still pass.

8. **Golden cases as FAILING inputs**, exact set equality on the emitted germ
   list, in the fixture module brief a created (or a sibling if c lands first):
   - an unmatched person whose role_hint case-folds onto an existing ACTIVE
     entity name must emit ZERO germs; removing the collision guard must make
     this case fail;
   - an unmatched person matching an existing `proposed` germ's payload name
     must emit ZERO germs; removing the dedup must make this case fail;
   - five unmatched persons with distinct names must emit exactly three germs, in
     mention order; removing the quota must make this case fail;
   - an unmatched person matching a germ whose payload already carries
     `created_entity_id` MUST still emit a germ — the entity was realized and a
     second, different one may legitimately be needed. Widening the dedup to
     ignore `created_entity_id` must make this case fail.

## Scope OUT

- **R1, the source label.** `list_pending_creations` computes
  `"tick" if mut.tick_id else "conversation"` (`routes/creator.py:174`), so a
  day-sourced germ shows as "conversation". Do not fix it here, do not add a
  `tick_id`, do not widen the label expression. Named deferral.
- **R3, the forward link.** No link from a `pass_play` or an `agenda_step` to an
  entity realized days later. Do not add one.
- **D3.** Germs stay persons-only. Do not extend `emit_germs` to places or
  factions, however tempting the symmetry.
- **`_approve_entity_creation_shortcircuit`.** Not touched. Its guard stays
  exactly as TICKET-0019 left it, including the I2 parking behavior.
- **`_find_applied_duplicate`.** Not touched, not called from here, not moved
  out of `_apply_mutation`.
- **The realization chain** (`/api/creations/pending`,
  `/api/creations/{id}/generate`, `create_entity`'s linkage). Complete and out of
  scope.
- **Anything in briefs a or b.** No rung changes, no trace tables, no rewrite.

## Invariants to defend

- **R1, purity of `day_concordance.py`.** The new guards are reads only. This is
  the invariant most at risk and it already has a check.
- **World scoping at query construction.** Both new `select(` calls carry it.
  The `payload` JSON comparison is the one sanctioned post-fetch step, and only
  because the world scope precedes it in the query.
- **`emit_germs` still writes nothing.** The caller owns `db.add` and the single
  commit, so an all-or-nothing request stays all-or-nothing.
- **Function-length ceiling, 80 lines.**
- **No structure without a reader.** `MAX_GERMS_PER_DECLARATION` must be read,
  not merely declared — R11 is that guard.

## STOP conditions

- If `emit_germs` cannot stay pure (no `db.add(`, no `.commit(`) with the guards
  added.
- If `emit_germs` or its extracted helper cannot be kept under 80 lines.
- If a second germ-emitting site for `entity_creation` is found on the day path
  that this brief did not enumerate — the Mini-RECON claims `emit_germs` is the
  only one, and an incomplete enumeration invalidates the coverage claim.
- If a golden case cannot be made to FAIL against the pre-change code.
- If `MAX_GERMS_PER_DECLARATION = 3` turns out to truncate a realistic
  declaration in live testing: REPORT the count, do not raise the constant in
  this commit.

## Done means

### Machine-checkable

- [ ] `python tooling/verify/checks/day_concordance.py` exits 0 and its PASS
      line names the germ quota and the two emission guards.
- [ ] `grep -n "db.add(\|\.commit(" src/world_engine/day_concordance.py` returns
      nothing.
- [ ] Removing the collision guard makes golden case 1 exit non-zero.
- [ ] Removing the pending dedup makes golden case 2 exit non-zero.
- [ ] Removing the quota makes golden case 3 exit non-zero.
- [ ] Widening the dedup to ignore `created_entity_id` makes golden case 4 exit
      non-zero.
- [ ] Emptying the golden fixture makes it exit non-zero (vacuous guard).
- [ ] `module_budget.py` and `function_length.py` exit 0.
- [ ] `/review-step` and `/close-step` run clean.

### Live -> human gate (Nia)

- [ ] Declaring a day that mentions a missing person creates one germ; declaring
      a second day mentioning the same missing person creates none, and the
      pending-creations list still shows exactly one.
- [ ] Realizing that germ, then declaring a third day mentioning the same role,
      creates a new germ (the realized one no longer blocks).
- [ ] A declaration mentioning a person whose role_hint matches an existing NPC's
      name creates no germ.
- [ ] A declaration mentioning five missing persons creates three germs, and the
      log names the two truncated.

## Docs to update

- No schema change; no changelog entry, no version bump.
- `CLAUDE.md`: nothing expected. If the emission guards belong beside the
  TICKET-0019 approval guard in an existing pointer, add one line and respect the
  500-line / 38,000-character budget.
