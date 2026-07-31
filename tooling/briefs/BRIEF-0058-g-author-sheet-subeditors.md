# BRIEF — Step "entity sheet: sub-editors"

Ticket: TICKET-0058. Relies on RECON-0058-a M4, M6, M7. Requires
BRIEF-0058-f landed.

## Context

Roughly sixty of the 107 `author*` functions are sub-editors hanging off the
sheet: geometry rows and bounds, doors, faction roles and memberships,
pricing, subcultures, the ledger, items, and the pending
knowledge/notes/goals panels. Each is a small editor with its own add/remove/
save cycle, and several carry structural guarantees of their own -
`geometry_unit.py`, `placement_unit.py`, `door_coverage.py`,
`door_distinct_points.py`, `door_terminal.py`, `faction_roster_order.py`,
`role_closed_vocab.py`, `role_capacity_chokepoint.py`.

They come after the core because they mount into slots the core provides,
and because a broken sub-editor is visible and local, where a broken field
engine is invisible and global.

## Scope IN

1. **One Svelte component per sub-editor**, under `frontend/src/creation/`,
   ported faithfully. Group and land them as a small explicitly listed set
   of commits, one per coherent editor family, in this order - each testable
   alone:
   - (a) geometry + doors (`authorGeometry*`, `authorRenderDoorsEditor`,
     `authorSaveDoors`, `authorRemoveOrphanDoor`)
   - (b) faction roles + memberships + roster
     (`authorRenderRolesEditor`, `authorCreateFactionRole` ..
     `authorDeleteFactionRole`, `authorRenderMembershipForm`,
     `authorAddMembership`, `authorCloseMembership`,
     `authorLoadFactionRoster`)
   - (c) pricing + subcultures (`authorRenderPricing`, `authorSavePriceEntry`,
     `authorPriceListMutate`, `authorRenderSubcultureEditor`,
     `authorSaveSubcultureRows`)
   - (d) ledger + items (`authorLoadLedger`, `authorRenderLedger`,
     `authorAddLedgerEntry`, `authorLoadItems`, `authorRenderItems`)
   - (e) pending knowledge / notes / goals panels
     (`authorRenderPendingKnowledge`, `authorRemovePendingKnowledge`,
     `authorRenderPendingGoals`, `authorRenderGenNotes`)

2. **Preserve every structural guarantee at the seam.** Geometry and door
   editors submit through the same endpoints with the same unit conventions;
   role creation still passes through the capacity chokepoint; roster order
   is still server-decided. Where a check greps `index.html`, re-home it in
   the SAME commit as the editor it guards - never in a later cleanup.

3. **`_factionRosterRowHtml` (`index.html:8915`)** moves with (b).
   Re-home `faction_roster_panel.py` and, if it anchors on `index.html`,
   `faction_roster_order.py`.

4. **Delete each ported legacy function** in the commit that replaces it,
   and add its identifier to the island registry entry's `retiredPrefix`
   coverage so `creation_island.py` rule 7 proves it gone.

## Scope OUT

- **Any behaviour change.** Not one new validation, not one relaxed
  constraint, not one "obviously missing" confirmation dialog. Every one of
  these editors touches canon.
- **Merging two sub-editors that look similar.** They may genuinely differ;
  a convergence proposal is a finding for Nia, with evidence, not a
  mid-brief decision.
- **The generate/draft path.** Brief -h.
- **Backend changes of any kind**, including "the endpoint would be cleaner
  if". Frontend-only (cross-cutting rule 2).

## Invariants to defend

- **History is sacred** - the ledger editor appends; it must not gain a
  delete path it did not have.
- **Single canon-write authority** - every save stays on a sanctioned
  creator-CRUD route.
- **Fail-closed over advisory** - each guarded editor's check is re-homed in
  its own commit, so no guarantee lapses between commits.
- **No `<svg` under `frontend/src/` outside `graph/`** - per M6.

## Done means

- [ ] Every check named in Context exits 0 after its editor's commit, and
      each is proven to still bite on a scratch mutation.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0.
- [ ] Live (a): edit a location's geometry rows and doors; save; reload;
      confirm geometry bounds and door endpoints survive; confirm an orphan
      door can still be removed.
- [ ] Live (b): create a faction role, rename it, reorder the roster, add a
      membership, close a membership; confirm capacity refusal still fires.
- [ ] Live (c): add and delete a price entry; edit subculture rows; save.
- [ ] Live (d): append a ledger entry and confirm nothing offers to delete
      one; list items.
- [ ] Live (e): a pending knowledge row can be removed before commit; goals
      panel renders long/short goals.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief -l.
