# BRIEF — Step "Region commit writes faction roles" (BRIEF-0033-a, corrective)

## Context

The region draft's faction sheets display `public.roles` (produced and
normalized by `entity_author.py` — `_normalize_roles` at :297, attached at
:464) but `_commit_region_factions` in `cockpit/routes/regions.py:135-165`
never writes them: `ext_data` copies faction_type / philosophy /
internal_structure / aversion / internal_tensions / goals and silently drops
`roles`. The unitary faction creator DOES commit roles (frontend POSTs each
row to `POST /api/factions/{id}/roles` after creation, `index.html:8039-8048`,
which goes through `write_faction_role`). Region-committed factions therefore
lose their role vocabulary — the bug Nia observed. Fix first, independent of
the rest of TICKET-0033.

## Scope IN

1. In `cockpit/routes/regions.py`, function `_commit_region_factions`:
   after `fac_entity = _crud._create_entity_core(fac_body, db)`, iterate
   the draft's roles: `for r in (pub.get("roles") or []):` and call
   `write_faction_role(db, mode="create", ...)` for each, mirroring EXACTLY
   the argument set used by the existing `POST /factions/{faction_id}/roles`
   route in `cockpit/crud/factions.py:203` (same `changed_by` value, same
   defaults), with: `world_id` = the region commit's world id,
   `faction_id=fac_entity.id`, `name=r["name"]`,
   `description=r.get("description")`, `max_holders=None` (the draft does
   not carry it — consistent with the unitary creator's `limit: null`),
   `position=None` -> the helper auto-assigns next position, preserving
   draft order because rows are written in draft order.
2. Import `write_faction_role` in `routes/regions.py` from `...writes`
   (same import site as the existing `write_relation` import at :26).
3. Dedupe before writing: fold role names casefold within one faction's
   list, first occurrence wins (the `idx_faction_role_name` unique index on
   `(faction_id, name COLLATE NOCASE)` would otherwise abort the whole
   atomic commit on a model-produced duplicate). Skip rows whose `name` is
   not a non-empty string after `.strip()` (defense in depth —
   `_normalize_roles` already drops nameless rows upstream).
4. NO extra `db.commit()`: `write_faction_role` is commit-free
   (`writes/factions.py:36` — it owns `db.add`, never commit); the writes
   join the single end-of-commit transaction, exactly like the stage-4
   `write_relation` calls. Any exception still rolls back the whole region.

## Scope OUT

- No change to `entity_author.py` or `_normalize_roles`.
- No `max_holders` in the draft or the prompt — stays null at region commit.
- No response-shape change for `/api/regions/commit` (no new fields).
- No editing of roles in the review sheet — that is BRIEF-0033-c (F1).
- No touch to the unitary faction creator path (already correct).
- No schema change.

## Invariants to defend

- Single canon-write paths: `write_faction_role` is the sole chokepoint for
  `faction_role` writes (`writes/factions.py:22`) — the fix goes through
  it, never raw `FactionRole(...)` construction in the route.
- All-or-nothing region commit: no intermediate commit; a role-write
  failure aborts the entire region (existing rollback path).

## Done means

- [ ] Live: generate a region whose manifest yields at least one faction
      with roles visible in the review sheet; commit; `GET
      /api/factions/{committed_id}/roles` returns those roles in draft
      order; the faction's roles editor in the Factions tab shows them.
- [ ] Live: a draft faction with a casefold-duplicate role name commits
      successfully (one row for the duplicate pair, first occurrence).
- [ ] `/review-step` and `/close-step` run (engine code touched).
- [ ] All verify checks pass.

## Docs to update

- ARCHITECTURE_DECISIONS.md: append under a "TICKET-0033" section — region
  commit writes faction roles through `write_faction_role`, max_holders
  null at region commit, casefold-dedupe-first-wins. No schema changelog
  entry (no schema change).
