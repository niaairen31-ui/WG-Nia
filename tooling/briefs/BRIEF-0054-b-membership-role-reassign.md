# BRIEF — Step "Membership role reassignment + capacity chokepoint"

## Context

`faction_membership` is INSERT-only / close-only by construction (BRIEF-27):
`write_membership` can never update a `role`, so a role change is close +
reopen. That sequence exists exactly once today, on the AI path
(`cockpit/mutations.py:288-294`), and nowhere on the creator path — the cockpit
can only add and close memberships. Separately, `max_holders` is enforced only
on the AI path (`mutations.py:222-233`, via an inline counting loop that
duplicates `_active_role_counts` in `crud/factions.py:145-157`), so creator CRUD
can silently overfill a declared role. This step adds the creator-side
reassignment route (decision D2) and makes capacity fail-closed on both creator
paths through a single shared accessor (decision E1). No frontend, no schema
change.

## Scope IN

1. **`src/world_engine/writes/factions.py` — move the counting primitive in.**
   Add `active_role_counts(db: Session, faction_id: str) -> dict[str, int]`:
   casefolded role name -> count of ACTIVE memberships bearing it
   (`FactionMembership.left_at.is_(None)`). This is `_active_role_counts` from
   `cockpit/crud/factions.py:145-157` moved verbatim, renamed public (no
   leading underscore) because it now has two importers. Delete the original
   and recable its single caller `list_faction_role_rows`
   (`crud/factions.py:170-200`) to the moved function.

2. **`src/world_engine/writes/factions.py` — the capacity accessor.** Add:

   ```
   def role_capacity_state(
       db: Session, *, faction_id: str, role_name: str
   ) -> tuple[int, Optional[int], Optional[str]]:
   ```

   Returns `(active_holder_count, max_holders, canonical_name)`.
   Resolution: read the faction's `FactionRole` rows, match
   `r.name.casefold() == role_name.casefold()` in Python — never SQL
   `lower()` / `NOCASE`, ASCII-only, same rationale as
   `_resolve_role_change_role`. An undeclared role returns `(0, None, None)`.
   A declared role with `max_holders IS NULL` returns
   `(count, None, r.name)` — unlimited. Counting reuses `active_role_counts`;
   this function must contain no second counting loop.
   Export both new names through `src/world_engine/writes/__init__.py`,
   alphabetically placed alongside the existing `_validate_max_holders` export
   (`writes/__init__.py:48`).

3. **`src/world_engine/cockpit/mutations.py` — recabled, message-preserving.**
   In `_resolve_role_change_role` (`mutations.py:206-250`), replace the inline
   `holders = db.exec(...)` / `count = sum(...)` block with a call to
   `role_capacity_state`. **The reject string stays constructed in
   `mutations.py`, verbatim and unmoved:**

   > `return None, f"role_change: role {resolved_key} is full ({count}/{limit})"`

   This is not stylistic. `tooling/verify/checks/role_closed_vocab.py` is a
   plain text scan of `mutations.py` and asserts the literal `"is full ("`
   lives there; moving the message into `writes/factions.py` would fail that
   check. **This brief does NOT authorize retargeting `role_closed_vocab.py`.**
   Every other assertion that check makes (`r.name.casefold() == role_key.casefold()`,
   the `select(FactionRole)...` read, the K1 and L2 branches, the I1
   active-membership reject) must also still be satisfied after the recabling —
   if satisfying them and using the shared accessor turns out to conflict,
   STOP and report; do not amend the check.

4. **`src/world_engine/cockpit/crud/factions.py` — capacity gate on the open
   path (E1).** In `_open_membership_core` (`factions.py:299-325`), after the
   faction-type validation and BEFORE `write_membership`, when `body.role` is
   a non-blank string: call `role_capacity_state`; if `max_holders` is not
   `None` and `count >= max_holders`, raise
   `HTTPException(409, f"role {canonical_name} is full ({count}/{max_holders})")`.
   An undeclared role passes — the creator's "autre" escape hatch (BRIEF-31)
   is preserved; capacity only constrains roles the creator has declared.
   The existing `IntegrityError` -> 409 wrapper in `open_entity_membership`
   (`factions.py:328-345`) is unchanged and must still catch the partial-unique
   violations.

5. **`src/world_engine/cockpit/crud/factions.py` — the reassignment route (D2).**

   ```
   class MembershipRoleChangeBody(BaseModel):
       role: Optional[str] = None
   ```

   `_reassign_membership_role_core(membership_id: str, body: MembershipRoleChangeBody, db: DbSession) -> FactionMembership`
   — commit-free, flushing not committing, the same shape and for the same
   reason as `_open_membership_core` (BRIEF-35: the partial-unique
   `IntegrityError` surfaces deterministically at the core call site, catchable
   by this route's wrapper or a future batch caller). Behaviour, in order:

   1. Load the membership; `404` if absent.
   2. `409` if `left_at is not None` — a closed membership is history and is
      never reassigned.
   3. Normalise: `new_role = body.role.strip() or None`.
   4. **No-op guard:** if `(new_role or "").casefold() == (membership.role or "").casefold()`,
      return the membership unchanged, writing nothing. A no-op must not
      manufacture a closed row.
   5. Capacity gate (E1), identical to item 4, when `new_role` is not `None`.
   6. `write_membership(db, mode="close", membership_id=membership.id)`, then
      `write_membership(db, mode="open", world_id=..., entity_id=...,
      faction_id=..., role=new_role, cover_role=membership.cover_role,
      is_primary=membership.is_primary, is_secret=membership.is_secret)`.
      Read `cover_role` / `is_primary` / `is_secret` off the old row BEFORE
      closing it. This mirrors `mutations.py:288-294` — same order, same
      carried fields.
   7. `db.flush()`, return the new membership.

   Route `POST /memberships/{membership_id}/role`, placed immediately after
   `close_entity_membership` (`factions.py:347-355`), wrapping the core in
   `try / except IntegrityError -> db.rollback() -> HTTPException(409, ...)`
   with the same message text `open_entity_membership` already uses, then
   `db.commit()`, `db.refresh(...)`, `return _membership_dict(membership, db)`.

6. **New check `tooling/verify/checks/role_capacity_chokepoint.py`.** Anchored
   from `import_cycle.py`'s idiom: `FAILURES` list, `_report_and_exit`, `ROOT`
   via `parents[3]`. Plain text scan, no DB. Assertions:
   - `writes/factions.py` defines `def role_capacity_state(` and
     `def active_role_counts(`
   - `writes/__init__.py` exports both names
   - `cockpit/mutations.py` calls `role_capacity_state(`
   - `cockpit/crud/factions.py` calls `role_capacity_state(` at least twice
     (the open path and the reassign path)
   - `cockpit/crud/factions.py` no longer defines `_active_role_counts`
   - `cockpit/crud/factions.py` contains `mode="close"` and `mode="open"` in
     the reassign core (the close+reopen shape, not an UPDATE)
   - `cockpit/crud/factions.py` contains no `membership.role =` assignment
     anywhere (an in-place role write would silently break the append-only
     history contract)

   **Vacuous-proof guard, mandatory:** a missing target file, or zero
   assertions evaluated, is a FAILURE.

## Scope OUT

- **No frontend at all.** No button, no form, no fetch call. BRIEF-0054-c
  wires the UI to these routes.
- **The new route changes `role` and nothing else.** Not `cover_role`, not
  `is_primary`, not `is_secret`, not `faction_id`. Editing those remains
  close-then-add through the existing controls. Do not "generalise" the body.
- **No bulk / multi-member reassignment**, no reorder-and-reassign combo.
- **No change to AI-path semantics.** K1 (undeclared without `declare` whole-
  rejects) and L2 (declare-and-occupy) stay exactly as they are. The creator
  path deliberately does NOT adopt K1 — an undeclared role is legal for the
  creator and illegal for the model; that asymmetry is the decision, not an
  oversight.
- **No retarget or amendment of `role_closed_vocab.py`.** If it fails, report
  and stop.
- **No `force` / override flag on capacity.** E3 was considered and refused;
  raising `max_holders` in the roles editor is the sanctioned path.
- **No capacity enforcement on undeclared roles**, and no auto-declaration of
  an undeclared role from the creator path.
- **No schema change, no migration, no schema version bump.**
- **No touching `read_public_memberships`** (`context.py`) or any prompt path.

## Invariants to defend

- **History is sacred / append-only.** The reassignment produces one closed row
  plus one new active row. There is no `UPDATE` on `faction_membership`
  anywhere in this step — the verify check's `membership.role =` assertion is
  the tripwire.
- **Single canon-write authority (S-norme).** All writes go through
  `write_membership` and `write_faction_role`. This route is creator direct
  authority, so it does NOT pass through `proposed_mutation` — same posture as
  every other cockpit CRUD route. The AST check `single_canon_write.py` must
  stay green.
- **Fail-closed over advisory.** Capacity refuses (409); it never warns and
  never proceeds with a note.
- **Structural over disciplinary.** After this step there is exactly ONE place
  that answers "how many hold this role and what is the limit". A second
  counting loop reappearing anywhere is the regression the new check exists to
  catch.
- **R1 (80-line ceiling).** `_reassign_membership_role_core` carries seven
  numbered behaviours; keep it under 80 lines or extract the capacity gate into
  a small shared `_assert_role_capacity(db, faction_id, role)` helper used by
  both creator call sites.
- **R5 module budget.** `crud/factions.py` sits at 371 lines / 24 top-level
  defs before BRIEF-0054-a. Report post-change counts. Nowhere near 40/1000,
  but the trend is worth a line in the step report.
- **Import direction.** Both importers reach into `writes/` — a direction that
  already exists (`crud/factions.py:52`, `mutations.py:51`). Do NOT make
  `mutations.py` import from `cockpit/crud/` to share the helper; that would
  cross the AI-pipeline / creator-CRUD strata for convenience.

## Done means

- [ ] `POST /api/memberships/<id>/role` with a new declared role returns 200;
      the DB then holds exactly one closed row (`left_at` set) and one active
      row for that member+faction
- [ ] The new active row carries the OLD row's `cover_role`, `is_primary` and
      `is_secret` values unchanged
- [ ] Reassigning to the role the member already holds (any casing) returns 200
      and creates NO new row — the closed-row count is unchanged
- [ ] Reassigning a closed membership returns 409
- [ ] Reassigning to a role at `max_holders` capacity returns 409 with the
      `n/max` figures in the message
- [ ] Reassigning to an UNDECLARED role succeeds (creator escape hatch), and
      creates no `faction_role` row
- [ ] `POST /api/entities/<char>/memberships` with a full declared role returns
      409; with an unlimited or undeclared role, still 201
- [ ] The AI `role_change` effect still rejects a full role with the identical
      message text as before this step (grep the string in `mutations.py`)
- [ ] `python tooling/verify/checks/role_closed_vocab.py` exits 0, unmodified
- [ ] `python tooling/verify/checks/role_capacity_chokepoint.py` exits 0, and
      exits non-zero when the open-path capacity gate is temporarily removed
- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0
- [ ] Full `/verify` run green; `/review-step` and `/close-step` run

## Docs to update

- `world-engine-schema-changelog.md`: "Schema: none" note stated explicitly.
- `ARCHITECTURE_DECISIONS.md`: new section
  `## FACTION MEMBERSHIP — creator role reassignment + capacity chokepoint (BRIEF-0054-b, no schema change)`
  recording D2 and E1, the close+reopen shape and why it is not an UPDATE, the
  single-accessor consolidation, the deliberate creator/AI asymmetry on
  undeclared roles, and the refusal of a `force` override.
- `DECISIONS_INDEX.md`: one row for the new section.
- `CLAUDE.md`: no change.
