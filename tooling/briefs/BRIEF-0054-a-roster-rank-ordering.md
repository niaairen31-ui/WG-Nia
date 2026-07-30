# BRIEF — Step "Faction roster: server-side rank ordering"

## Context

`GET /entities/{entity_id}/faction-roster` (`cockpit/crud/factions.py:358-371`)
returns active memberships with no `order_by` at all, and `_membership_dict`
(`factions.py:109-124`) carries no rank information. The rank already exists
relationally: `faction_role.position` is the ordered vocabulary, read by
`list_faction_role_rows` (`factions.py:170-200`). This step makes the roster
route the single source of roster ordering (decision A1) and pins the
three-bucket order (decision B1). Read-only step: no write path, no schema
change, no frontend.

## Scope IN

1. **`src/world_engine/cockpit/crud/factions.py` — new module-level helper
   `_roster_rank_index`.** Signature:
   `_roster_rank_index(db: DbSession, faction_id: str) -> dict[str, int]`.
   One query: `select(FactionRole).where(FactionRole.faction_id == faction_id)`
   ordered by `FactionRole.position`. Returns `{role.name.casefold(): role.position}`.
   Matching is done in Python via `.casefold()`, never SQL `lower()` /
   `NOCASE` — same rationale as `_resolve_role_change_role`
   (`cockpit/mutations.py:206-215`): SQLite's `lower()` is ASCII-only and
   would mishandle accented French role names. Copy that rationale into the
   docstring in these words:

   > Matched in Python (`.casefold()`), not SQL `lower()` — SQLite's
   > NOCASE/lower() is ASCII-only and would mishandle accented French role
   > names.

2. **New module-level helper `_roster_sort_key`.** Signature:
   `_roster_sort_key(m: FactionMembership, rank_index: dict[str, int]) -> tuple`.
   Returns a five-element tuple, all elements type-stable across buckets so no
   comparison ever mixes `int` and `str`:

   | element | declared role | undeclared role | no role |
   |---|---|---|---|
   | `bucket` (int) | `0` | `1` | `2` |
   | `position` (int) | `rank_index[role.casefold()]` | `0` | `0` |
   | `role_key` (str) | `""` | `role.casefold()` | `""` |
   | `primary_key` (int) | `0 if m.is_primary else 1` | idem | idem |
   | `joined_key` (str) | `_iso(m.joined_at) or ""` | idem | idem |

   A membership whose `role` is `None` or whitespace-only is bucket `2`.
   The `primary_key` / `joined_key` tiebreak is the same static ordering
   `read_public_memberships` already applies (BRIEF-29): primary first, then
   oldest-joined.

3. **New module-level helper `_roster_dict`.** Signature:
   `_roster_dict(m: FactionMembership, db: DbSession, rank_index: dict[str, int]) -> dict`.
   Returns `_membership_dict(m, db)` extended with exactly two keys:
   - `role_position`: the `int` position when the role is declared, else `None`
   - `role_declared`: `True` when the role is declared, else `False`
     (a `None`/blank role is `False`)

   This enrichment lives ONLY on the roster path. `_membership_dict` itself is
   NOT modified — `list_entity_memberships` (`factions.py:288-296`, the
   character sheet's "Appartenances" list) must keep its current shape and must
   not acquire a per-row `faction_role` lookup.

4. **`get_faction_roster` recabled.** Body becomes: resolve the entity, load
   the active rows as today, build `rank_index = _roster_rank_index(db, entity_id)`
   once, then
   `return [_roster_dict(m, db, rank_index) for m in sorted(rows, key=lambda m: _roster_sort_key(m, rank_index))]`.
   The existing `_get_entity(db, entity_id)` call, the `left_at.is_(None)`
   predicate, and the inclusion of secret members are all unchanged.

5. **`get_faction_roster` docstring gains the ordering contract, verbatim:**

   > Ordering (TICKET-0054, decision B1) is a property of this route, not of
   > its callers: declared roles by `faction_role.position` ascending, then
   > roles borne by active members but never declared (alphabetical, casefold),
   > then members with no role — and within any one role, `is_primary` first
   > then oldest `joined_at`. Any future roster reader inherits this order by
   > calling this route; none re-sorts client-side.

   The existing paragraph about secret members being included for the creator
   is preserved verbatim.

6. **New check `tooling/verify/checks/faction_roster_order.py`.** Anchored from
   `tooling/verify/checks/import_cycle.py`'s idiom: `FAILURES` list,
   `_report_and_exit`, `ROOT` via `parents[3]`. Plain text scan of
   `src/world_engine/cockpit/crud/factions.py`, no DB. Assertions:
   - `_roster_rank_index` and `_roster_sort_key` are both defined
   - `get_faction_roster` calls `_roster_sort_key` (the route sorts; a
     roster returned unsorted is the exact regression this check exists for)
   - `FactionRole.position` is read inside `_roster_rank_index`
   - `role_position` and `role_declared` appear in `_roster_dict`
   - `_membership_dict` does NOT contain `role_position` (the enrichment did
     not leak onto the character-sheet path)
   - `.casefold()` appears in `_roster_rank_index` (no ASCII-only SQL matching)

   **Vacuous-proof guard, mandatory:** if the target file is missing, or if
   zero assertions were evaluated because `get_faction_roster` could not be
   located in the source text, that is a FAILURE, not a pass.

## Scope OUT

Name the temptations explicitly. None of the following belongs to this step:

- **No change to `_membership_dict`** and no change to `list_entity_memberships`.
  Adding `role_position` there would put an N+1 `faction_role` lookup on the
  character sheet for no reader.
- **No frontend.** `authorRenderFactionRoster` (`index.html:8873-8883`) stays a
  flat list this step. Grouped headers are BRIEF-0054-c.
- **No capacity enforcement.** `max_holders` (decision E1) is BRIEF-0054-b.
- **No role change route, no add-member route.** BRIEF-0054-b / -c.
- **No navigation work.** Decision F2a is BRIEF-0054-d.
- **No secret filtering.** The creator roster keeps showing `is_secret` rows
  with their badge — BRIEF-27's posture, unchanged. Do not add an
  `include_secret` parameter "while we're here".
- **No schema change, no migration, no schema version bump.** State this
  explicitly in the changelog note.
- **No role hierarchy / tree.** `faction_role` stays flat-ordered; a `parent`
  key remains the deliberate non-feature of BRIEF-31.
- **No promotion of undeclared roles.** Rendering an undeclared role in its
  own bucket must not write a `faction_role` row. The "autre" escape hatch
  stays one-shot (BRIEF-31).

## Invariants to defend

- **No structure without a reader (E2).** `role_position` and `role_declared`
  ship in this step only because BRIEF-0054-c's grouped render consumes them,
  and because the route's own ordering consumes `position`. Nothing else is
  added to the payload.
- **Single canon-write authority.** This step writes nothing. If the executor
  finds itself importing `write_membership` or `write_faction_role` here, the
  step has gone out of scope.
- **Exclusion is structural, never instructional.** Untouched: this route is a
  creator surface and is not a prompt path. The prompt-facing accessor remains
  `read_public_memberships` (`context.py`), which this step does not modify.
- **R1 (80-line ceiling).** `get_faction_roster` must stay well under it; the
  three helpers exist partly for that reason.
- **R5 module budget.** `crud/factions.py` is at 371 lines / 24 top-level
  defs before this step. Three added helpers put it near 28 defs — still far
  from 40/1000. Report the post-change counts; do not pre-emptively split.

## Done means

- [ ] `curl /api/entities/<faction>/faction-roster` on a faction with at least
      one declared role, one member bearing an undeclared role, and one member
      with no role returns the three buckets in order, declared first
- [ ] Two members holding the same declared role come back primary-first, then
      oldest `joined_at` first
- [ ] Every row carries `role_position` (int or null) and `role_declared`
      (bool); a declared-role row's `role_position` equals that role's
      `faction_role.position`
- [ ] A role declared as `Capitaine` and borne as `capitaine` on a membership
      resolves as DECLARED (casefold match), not as bucket 1
- [ ] `curl /api/entities/<character>/memberships` returns exactly the same
      JSON keys as before this step (no `role_position`)
- [ ] `python tooling/verify/checks/faction_roster_order.py` exits 0
- [ ] The same check exits non-zero when `_roster_sort_key` is temporarily
      removed from `get_faction_roster` (prove it is not vacuous)
- [ ] Full `/verify` run green; `/review-step` and `/close-step` run

## Docs to update

- `world-engine-schema-changelog.md`: a "Schema: none" note for this step,
  stated explicitly (read-only step, `faction_membership` and `faction_role`
  unchanged since v1.39 / TICKET-0024).
- `ARCHITECTURE_DECISIONS.md`: new section
  `## FACTION ROSTER — server-side rank ordering (BRIEF-0054-a, no schema change)`
  recording A1 and B1, the three-bucket order verbatim, the casefold rationale,
  and the explicit note that `_membership_dict` was deliberately left alone.
- `DECISIONS_INDEX.md`: one row for the new section.
- `CLAUDE.md`: no change.
