---
id: TICKET-0054
title: Faction roster - rank ordering, membership authoring, cross-tab navigation
type: feature
status: exec
created: 2026-07-30
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0054-a, BRIEF-0054-b, BRIEF-0054-c, BRIEF-0054-d]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je veux ameliorer l'onglet creation/Faction :
> Dans la section membre (lecture seule), je veux que les membres soit organise
> par role. Du role le plus haut, au role le plus bas. Je veux pouvoir associe
> des NPC a cette faction a partir de la ou changer leur role. Pour associe un
> nouveau NPC a la faction. Je veux aussi que si je double clic sur le membre,
> je puisse me rendre sur sa fiche, idealement je pourrait retourner sur la
> factions en fermant l'onglet du NPC.

## Clarifications resolved (intake)

Locked as `A1, B1, C3, D2, E1, F2a`:

- **A1 - the server orders the roster.** `GET /entities/{id}/faction-roster`
  (`crud/factions.py:358`) joins `faction_role` and returns rows already
  sorted, carrying `role_position`. Ordering is a single structural fact, not
  a JS convention; any future roster reader inherits it.
- **B1 - three ordered buckets with visible headers.** Declared roles by
  `faction_role.position` ascending, then roles borne by active members but
  not declared (alphabetical), then members with no role. Within one role:
  `is_primary` first, then `joined_at` ascending - the same static ordering
  `read_public_memberships` already uses (BRIEF-29). The undeclared bucket
  doubles as the adoption surface already fed by
  `list_faction_role_rows.undeclared_active_roles` (`crud/factions.py:170`).
- **C3 - authoring from the faction sheet reuses the existing route.** One
  add-member form at the foot of the roster, plus a `+` on each role header
  that pre-selects that role. Backend is `POST /entities/{entity_id}/memberships`
  (`crud/factions.py:328`) called in the reverse direction - no new create
  route. Player characters remain eligible members.
- **D2 - role change is a dedicated close+reopen route.** `faction_membership`
  is INSERT-only / close-only by construction (BRIEF-27), so a role change is
  never an UPDATE. A new `POST /memberships/{id}/role` performs close then
  reopen inside one transaction, preserving `cover_role` / `is_primary` /
  `is_secret` - mirroring the AI path's existing shape (`mutations.py:288-294`)
  verbatim. The client never issues the two writes itself.
- **E1 - `max_holders` becomes fail-closed on the creator paths too.** Today
  capacity is enforced only on the AI `role_change` effect
  (`mutations.py:222-233`); the creator CRUD ignores it. Both creator paths
  (open a membership, change a role) now reject a full role with HTTP 409.
  The escape hatch is already canon and already creator-owned: raise
  `max_holders` in the roles editor. No `force` override flag - that would be
  a second truth about what a declared capacity means.
- **F2a - cross-tab navigation with a single-slot return.** Double-click on a
  roster row opens the member's real, editable sheet in its own creation
  sub-tab (`npc` or `pj`, resolved against `playerCharIds`); a contextual
  `<- Faction : X` control returns to the faction sheet - the same house
  idiom as `<- Lieu` (`index.html:1087`). State is one slot, not a stack:
  nothing reads a depth greater than one today. A real multi-entity tab bar
  (F3) is refused for now and is coupled to the pending `index.html` split
  decision.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The roster route orders by `faction_role.position` and exposes
      `role_position`; the three-bucket order is asserted, not implied
      -> verify/checks/faction_roster_order.py
- [ ] Role capacity is read through one shared accessor called by BOTH the AI
      path and the two creator paths; no inline holder-counting loop remains
      in either -> verify/checks/role_capacity_chokepoint.py
- [ ] The faction sheet's roster panel groups members into the three ordered
      zones, loads roles before the roster, and the read-only title is gone
      -> verify/checks/faction_roster_panel.py
- [ ] `role_closed_vocab.py` still passes unchanged (the AI path keeps its
      reject-message literals in `mutations.py`)
- [ ] `single_canon_write.py`, `module_budget.py`, `function_length.py`,
      `import_cycle.py`, `undefined_names.py` all pass
- [ ] Full `/verify` run green

### Live  ->  human gate (Nia)

- [ ] A faction with declared roles shows its members grouped under role
      headers, highest rank first; an undeclared role and a role-less member
      each land in their own bucket, last
- [ ] Adding an NPC from the faction sheet creates the membership; adding one
      already active in that faction is refused (409), not silently duplicated
- [ ] Changing a member's role leaves exactly one active row and one closed
      row for that member+faction, with `cover_role` / `is_primary` /
      `is_secret` carried over untouched
- [ ] Assigning a role whose `max_holders` is already met is refused with a
      readable message on both creator paths
- [ ] Double-click on a member opens their editable sheet in the right
      sub-tab (NPC vs Personnages joueurs); the return control lands back on
      the same faction with its roster loaded
- [ ] Switching worlds, or clicking any sub-tab manually, clears the pending
      return - no stale breadcrumb survives
