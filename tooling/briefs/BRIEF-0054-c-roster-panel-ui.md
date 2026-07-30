# BRIEF — Step "Faction sheet: grouped roster panel + member authoring"

## Context

BRIEF-0054-a made `GET /entities/{id}/faction-roster` return members already
ordered in three buckets, each row carrying `role_position` and `role_declared`.
BRIEF-0054-b added `POST /memberships/{id}/role` (close+reopen) and made
`max_holders` fail-closed on both creator paths. The cockpit still renders a
flat, inert list (`authorRenderFactionRoster`, `index.html:8873-8883`). This
step gives the faction sheet its grouped roster with per-rank headers (decision
B1) and lets the creator add a member or change a member's role without leaving
the faction (decision C3). Frontend only: no route, no schema, no navigation.

The `index.html` split is Nia's next chantier and is deliberately NOT
anticipated here — this step lands in the monolith as-is (decision S1). Do not
introduce modules, bundlers, or a component framework.

## Scope IN

1. **Single ordered loader for the members panel.** Today the faction branch of
   `authorRenderSheet` (`index.html:7728-7732`) fires `authorLoadFactionRoster`
   and `authorLoadFactionRoles` independently. The grouped render needs the
   declared-role list in memory FIRST (item 3). Replace the two calls with one
   `authorLoadFactionMembersPanel(entityId)` that does
   `await authorLoadFactionRoles(entityId);` then
   `await authorLoadFactionRoster(entityId);`, in that order. Both existing
   loaders keep their current bodies and their current containers
   (`#author-roles`, `#author-faction-roster`) — this is a sequencing wrapper,
   not a merge.

2. **Section title.** The faction sheet block at `index.html:7684-7687` is
   titled `Membres (lecture seule)`. It is no longer read-only: retitle it
   `Membres`.

3. **`authorRenderFactionRoster(rows)` renders three ordered zones.** The
   member order INSIDE any zone is the order the server returned — the client
   groups, it never re-sorts. Zones:

   - **Zone 1, declared roles.** One section per entry of
     `authorFactionRolesLive` (already in memory from
     `authorLoadFactionRoles`, `index.html:8605-8616`, ordered by
     `position`), **including roles with zero members** — an empty rank still
     renders its header and its `+`, which is how the creator fills it.
     Header shows: the role `name`; an occupancy badge
     `active_holder_count / max_holders`, rendering the limit as `∞` when
     `max_holders` is null; and a `+` button calling
     `authorFactionMemberAddPrefill('<role name>')` (item 5). An empty section
     renders `<div class="empty">Aucun membre.</div>`.
     Rows are matched into a section by `role_declared === true` AND
     `role_position === <that role's position>`.
   - **Zone 2, undeclared roles.** One section per distinct `role` among rows
     where `role_declared === false` and `role` is non-empty, in the order the
     rows arrive (the server already alphabetised them). Header shows the role
     name plus a discreet `non déclaré` badge and a `Déclarer` button calling
     the EXISTING `authorDeclareFactionRole(authorEntityId, name)`
     (`index.html:8756-8767`), followed by `authorLoadFactionMembersPanel`.
     No `+` on these headers — one cannot add into a rank that does not exist.
   - **Zone 3, `Sans rôle`.** Rows whose `role` is null or blank. Header, no
     badge, no `+`.

4. **Row content is preserved verbatim from the current renderer**, plus one
   control. Keep exactly: `entity_name`, ` — role`, ` (façade : cover_role)`
   in `<em>`, the `primaire` badge (`badge b-equipped`) and the `secret` badge
   (`badge b-rejected`). Every interpolation goes through `esc()`, including
   role names read from `authorFactionRolesLive`. Add one control on the right:
   a `Changer` button calling `authorMemberRoleEditStart('<membership id>')`.

5. **Add-member form, one instance, at the foot of the roster.**
   `authorRenderFactionMemberAddForm(rows)` renders a `row-card` in the shape
   of the existing character-side form (`authorRenderMembershipForm`,
   `index.html:8769-8790`) MINUS the faction select — the faction is
   `authorEntityId`. Fields, with these ids:
   - `#fmem-new-entity`: a select over
     `authorAllEntities.filter(e => e.type === 'character')`, excluding every
     `entity_id` already present in `rows`. Player characters are NOT excluded
     (a PC may join a faction). Empty candidate set renders the select
     disabled with a single `Aucun candidat` option.
   - `#fmem-new-role-select`: options from `authorFactionRolesLive` names,
     plus an always-present `<option value="__other__">autre</option>`, plus
     an always-present `<option value="">(aucun)</option>` first. Same
     `__other__` idiom as `authorMembershipRoleSelectChanged`
     (`index.html:8822-8826`), revealing `#fmem-new-role-other-row` /
     `#fmem-new-role`.
   - `#fmem-new-cover-role` (text), `#fmem-new-primary` (checkbox),
     `#fmem-new-secret` (checkbox).
   - Button `Ajouter le membre` calling `authorAddFactionMember()`.

   `authorFactionMemberAddPrefill(roleName)` sets `#fmem-new-role-select` to
   that role (or `__other__` + the text field when the name is not among the
   options), then focuses `#fmem-new-entity`.

6. **`authorAddFactionMember()`** POSTs to
   `/api/entities/${encodeURIComponent(selectedEntityId)}/memberships` with
   body `{faction_id: authorEntityId, role, cover_role, is_primary, is_secret}`
   — the existing route (`crud/factions.py:328`) called in the reverse
   direction. `role` resolves through the same `__other__` branch
   `authorAddMembership` uses (`index.html:8828-8848`), with `''` meaning
   `null`. On success: `await authorLoadFactionMembersPanel(authorEntityId)`
   and `#author-status` set to `Saved.` with class `author-status ok`. On
   failure: `#author-status` carries `e.message` with class `author-status err`
   — the 409s from BRIEF-0054-b (role full, duplicate active membership) reach
   the creator as readable text, unmodified. Same status idiom as every
   neighbouring handler; no `alert()`, no toast.

7. **Inline role change.** `authorMemberRoleEditStart(membershipId)` swaps that
   row's right-hand side for a role select (same option set as item 5, without
   `__other__`'s text row — reuse a small shared option-builder rather than
   duplicating the markup twice) plus `Valider` / `Annuler`.
   `authorMemberRoleEditSubmit(membershipId)` POSTs to
   `/api/memberships/${encodeURIComponent(membershipId)}/role` with
   `{role}`, then reloads the panel and reports through `#author-status`
   exactly as item 6. `Annuler` re-renders the panel from the rows already in
   hand. Only one row may be in edit mode at a time; starting a second edit
   cancels the first.

8. **New check `tooling/verify/checks/faction_roster_panel.py`.** Anchored from
   `import_cycle.py`'s idiom (`FAILURES`, `_report_and_exit`, `ROOT` via
   `parents[3]`). Text scan of `src/world_engine/cockpit/index.html`, no DB.
   **Collect by function name, never by comment-anchored section slice** —
   comment-anchored slices go stale (TICKET-0043 lesson). Assertions:
   - `authorLoadFactionMembersPanel` is defined, and the faction branch of the
     sheet renderer calls it
   - `authorLoadFactionMembersPanel` awaits `authorLoadFactionRoles` BEFORE
     `authorLoadFactionRoster` (index of one substring < index of the other)
   - `authorRenderFactionRoster` references `role_declared`,
     `role_position`, and `authorFactionRolesLive`
   - `authorRenderFactionRoster` contains no `.sort(` call (the server owns
     member order — decision A1)
   - `authorAddFactionMember` posts to `/memberships` and sends `faction_id`
   - `authorMemberRoleEditSubmit` posts to a `/role` path
   - the literal `Membres (lecture seule)` no longer appears

   **Vacuous-proof guard, mandatory:** missing file, or zero assertions
   evaluated because a named function could not be located, is a FAILURE.

## Scope OUT

- **No navigation, no `ondblclick`, no cursor change on rows.** Decision F2a is
  BRIEF-0054-d and must land as a separate, independently testable commit.
- **No membership close/remove control on the faction sheet.** Closing a
  membership stays on the character sheet (`authorCloseMembership`,
  `index.html:8850-8860`). Adding it here was NOT requested; it is a separate
  decision because removing a member from the faction side reads very
  differently from leaving a faction from the character side.
- **No editing of `cover_role`, `is_primary` or `is_secret` from a roster
  row.** The reassignment route accepts `role` only (BRIEF-0054-b).
- **No role reordering, renaming, deleting, or `max_holders` editing from the
  roster.** The roles editor (`#author-roles`) owns all of that; the roster
  only reads `authorFactionRolesLive`.
- **No client-side sorting of members**, ever. Grouping only.
- **No new backend route, no change to any existing route or response shape.**
  If a needed field is missing, STOP and report — do not add it client-side.
- **No secret filtering.** The creator roster keeps showing `is_secret` rows
  with their badge (BRIEF-27 posture).
- **No auto-declaration of undeclared roles.** The `Déclarer` button is an
  explicit creator gesture; rendering a zone-2 header must never write.
- **No modularisation of `index.html`.** No new `<script src>`, no build step,
  no framework. The split is Nia's next chantier and this step must not
  pre-empt its shape.
- **No pagination or search on the roster**, whatever its size.

## Invariants to defend

- **Server owns order, client owns grouping.** The one place the client reads
  ordering is `authorFactionRolesLive`'s array order for the HEADER list —
  necessary because the server roster cannot describe a rank with zero
  members. Member order inside a zone is never recomputed. The `.sort(`
  assertion in the check is the tripwire.
- **Fail-closed over advisory.** A 409 from a full role surfaces as an error
  status and the panel does not reload as if it had worked. The client must
  never pre-filter roles by occupancy to "help" — the server refuses, the
  client reports.
- **No structure without a reader.** `role_position` / `role_declared` shipped
  in BRIEF-0054-a specifically for this render. If either ends up unused here,
  that is a finding to report, not something to leave dangling.
- **Single canon-write authority.** Every write goes through the two existing
  routes. No new fetch target appears in this step.
- **Escaping.** Role names are creator free text and now flow into headers,
  option values and prefill arguments. Every one goes through `esc()`; the
  `+` and `Déclarer` handlers must not build an unescaped inline string
  argument.

## Done means

- [ ] A faction with three declared ranks shows three headers in `position`
      order, highest first, each with its `n/∞` or `n/max` badge
- [ ] A declared rank with zero members still shows its header, its `+`, and
      `Aucun membre.`
- [ ] A member bearing a role that is not declared appears under its own
      header in zone 2 with the `non déclaré` badge; `Déclarer` creates the
      `faction_role` row and the member moves into zone 1 after reload
- [ ] A member with no role appears under `Sans rôle`, last
- [ ] Two members of the same rank appear primary-first then oldest-joined
      (server order, unchanged by the grouping)
- [ ] `+` on a rank header pre-selects that rank in the add form
- [ ] Adding a character creates the membership and the panel reloads with the
      member under the right header
- [ ] The candidate select excludes members already active in this faction, and
      includes player characters
- [ ] Adding into a rank at capacity leaves `#author-status` showing the
      server's `is full (n/max)` message, and adds nobody
- [ ] `Changer` on a row, then `Valider`, moves the member to the new header;
      the character sheet's Appartenances list shows the same new role
- [ ] `Annuler` on an in-progress role change leaves the row untouched
- [ ] `python tooling/verify/checks/faction_roster_panel.py` exits 0, and
      exits non-zero when a `.sort(` is temporarily added to
      `authorRenderFactionRoster`
- [ ] Full `/verify` run green; `/review-step` and `/close-step` run

## Docs to update

- `world-engine-schema-changelog.md`: "Schema: none".
- `ARCHITECTURE_DECISIONS.md`: append to the BRIEF-0054-a section, or open
  `## FACTION ROSTER — grouped panel + member authoring (BRIEF-0054-c, no schema change)`,
  recording B1's three zones, the "server orders / client groups" split and
  why the header list is the one client-side ordering read, C3's shared form,
  and the explicit non-inclusion of a close-membership control.
- `DECISIONS_INDEX.md`: one row if a new section is opened.
- `CLAUDE.md`: no change.
