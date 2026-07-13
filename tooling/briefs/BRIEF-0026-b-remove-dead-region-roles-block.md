# BRIEF — Step "Remove dead role-list block in commit_region Stage 1"

TICKET-0026 · variant E1 (dead-code removal, behavior-preserving). Cites
RECON-0026. CONTINGENT on Nia confirming E1; if she picks E2 (persist drafted
roles in both commit paths), this brief is rewritten.

## Context

`commit_region` Stage 1 still assembles a `roles` list from `pub.get("roles")`
and sets `entity_data["metadata"] = {"roles": roles}` (`app.py:720-727`). Since
BRIEF-0025-a dropped `entity.metadata`, `metadata` is no longer in
`ENTITY_BASE_FIELDS`, so `_apply_base_fields` never reads the key
(RECON-0026 §2b): the commit succeeds and the roles are silently discarded — no
crash, no persistence. RECON-0026 §2d established that NO accept/create path
writes `faction_role`: the single-entity faction accept path ALSO discards
drafted roles, so the two commit paths are already symmetric. Removing this
block writes no behavior change; it only stops the code from constructing a
value that reaches nothing.

## Scope IN

1. **`src/world_engine/cockpit/app.py`, `commit_region`, Stage 1 factions
   (`app.py:720-727`).** Delete the dead block in full — the `roles = [ ... ]`
   comprehension AND the `if roles: entity_data["metadata"] = {"roles": roles}`
   that follows it. After deletion, `entity_data` for a faction is exactly:
   ```
   entity_data: dict[str, Any] = {
       "type": "faction",
       "name": pub.get("name"),
       "description": pub.get("description"),
   }
   ```
   directly followed by the existing `ext_data = { ... }` construction. `pub`
   and `sec` remain in use by `ext_data`; only the `roles` local and the
   `metadata` assignment go. Do not touch Stage 2 / Stage 3 / Stage 4.

2. **Dead import cleanup.** Remove the unused `write_location_subculture` import
   at `app.py:124` (RECON-0026 §1e — imported, never called in `app.py`). ONLY
   if a project-standard lint/import check would otherwise flag it or if it is
   trivially confirmable as unused by grep; if there is any doubt it is
   referenced, leave it and REPORT instead.

## Scope OUT

- **Do NOT persist drafted roles to `faction_role`** (that is decision E2, a
  feature, explicitly not chosen for E1). No `write_faction_role` call is added
  to `commit_region` or to `_create_entity_core`.
- **Do NOT touch the single-entity faction accept path** (`create_entity` /
  `_create_entity_core`). It already discards drafted roles; keeping it that way
  is what preserves symmetry.
- **Do NOT touch the faction-role CRUD editor** (`crud.py:1842+`) or the
  `role_change` mutation consequence (`app.py:1456`) — those are the sanctioned
  `faction_role` writers and are correct.
- No schema change, no migration, no new route, no template change.

## Invariants to defend

- "No structure without a reader" — this removal ENFORCES it: the block built a
  structure (a `metadata.roles` payload) with no reader. Nothing in the removal
  threatens an invariant.
- Atomicity of `commit_region`'s single-transaction / single-`db.commit()`
  contract is untouched (the removed lines contained no DB call).
- If E2 is ever taken later, "AI never authors canon directly" must be revisited
  (drafted roles pass through no granular review) — noted, not acted on here.

## Done means

- [ ] `grep -n 'metadata' src/world_engine/cockpit/app.py` returns no
      `entity_data["metadata"]` assignment inside `commit_region`.
- [ ] `grep -n 'pub.get("roles")' src/world_engine/cockpit/app.py` returns
      nothing (the block was the only reference).
- [ ] The faction `entity_data` in Stage 1 matches the three-key form in
      Scope IN item 1.
- [ ] **Live parity check:** generate a region whose draft includes a faction
      with declared roles; commit it; the commit returns `{"ok": true}` and the
      committed faction exists with NO `faction_role` rows — identical to
      pre-change behavior and identical to a single-entity faction accept.
- [ ] If Scope IN item 2 was applied: `python -c "import
      world_engine.cockpit.app"` (with `PYTHONPATH=src`) imports clean.
- [ ] `/review-step` and `/close-step` run (engine code in a canon-write path
      is touched — commit before touching, per CLAUDE.md).

## Docs to update

None. This is behavior-preserving dead-code removal; no schema changelog,
no ARCHITECTURE_DECISIONS entry, no CLAUDE.md change. (If E2 were chosen, a
decision record WOULD be required — another reason E1 stays a clean correction.)
