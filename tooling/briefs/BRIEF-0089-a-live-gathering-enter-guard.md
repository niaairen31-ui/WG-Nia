# BRIEF 0089-A — "The entry guard counts live gatherings"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/cockpit/routes/scene.py` -> `enter_scene` computes
  `open_g = _open_gatherings(location_id, sess.id, db)` and gates the call to
  `_enter_location(location_id, sess.id, db)` on `if not open_g:`. `open_g`
  is used nowhere else in that function.
- `src/world_engine/cockpit/routes/scene.py` -> already imports
  `_active_members`, `_open_gatherings`, `_get_or_open_session` and
  `_gathering_brief` from `..play`.
- `src/world_engine/cockpit/play.py` -> `_open_gatherings` selects `Gathering`
  on `location_id`, `session_id` and `status == 'open'` only.
- `src/world_engine/cockpit/play.py` -> `_active_members(gathering_id, db)`
  returns `list[tuple[GatheringMember, Entity]]` filtered on
  `left_at IS NULL`, `Entity.status == 'active'`,
  `Character.vital_status == 'alive'`.
- `src/world_engine/cockpit/play.py` is at 997 lines against a 1000-line cap.
- `enter_scene` is 76 physical lines against an 80-line cap.

## Facts carried

**R-03 — `enter_location` has exactly one live caller, and it is guarded.**
`enter_scene` computes `open_g = _open_gatherings(location_id, sess.id, db)`
at `:112` and calls `_enter_location` at `:139` only inside `if not open_g:`
(`:114`). `routes/mutations.py:37-38` imports `enter_location` and
`migrate_npc` and calls neither. Consequence: one open gathering at the
location, of any composition, freezes the partition for the rest of the
session.

**R-04 — `_open_gatherings` does not look at membership.** It selects
`Gathering` on `location_id`, `session_id` and `status == 'open'`. A gathering
with zero active members is returned.

**R-05 — `_active_members` is the single roster authority, with its own
filters.** It joins `GatheringMember`, `Entity` and `Character` and filters
`left_at IS NULL`, `Entity.status == 'active'`, `Character.vital_status ==
'alive'`. Its docstring designates it the single source of truth for roster
reads.

**R-15 — `play.py` cannot host a new helper.** 997 lines, 29 functions,
against the 1000/40 cap.

**R-14 — function length ceilings.** `MAX_LINES = 80`, no baseline file, cap
enforced on every function. `enter_scene` is currently 76 physical lines.

**R-27 — production state, measured.** Gathering `81d51618...` ("Reine des
ombres en solitude", location `"Chambre "`) is `open` with zero active
members; both NPCs carry `current_location_id` pointing at that location and
hold no membership row with `left_at IS NULL`.

## Contracts

**C-01 — `_live_gatherings`**
Produced by: BRIEF-0089-a   Consumed by: BRIEF-0089-a, BRIEF-0089-g
Declared in: `src/world_engine/cockpit/routes/scene.py`, module level.
Signature: `_live_gatherings(location_id: str, session_id: str, db: Session) -> list[Gathering]`
Return shape: the subset of `_open_gatherings(location_id, session_id, db)`
for which `_active_members(g.id, db)` is non-empty, in the order
`_open_gatherings` returned them.
Error and empty cases: never raises. Returns `[]` when there are no open
gatherings, and `[]` when every open gathering has zero active members. It
does not write, and it does not dissolve anything.

## Context

A creator-side location edit closes an NPC's gathering membership without
dissolving the gathering it empties. The shell stays `open`, and because the
entry guard only asks whether an open gathering exists, `enter_location` never
runs at that location again for the rest of the session -- so no NPC standing
there can ever be placed into a scene. Two NPCs are in exactly this state in
production right now. This brief is the one that makes the running session
playable again: once the guard ignores shells, `enter_location` dissolves them
itself and regenerates the partition from `current_location_id`.

## Scope IN

1. In `src/world_engine/cockpit/routes/scene.py`, add a module-level function
   `_live_gatherings` implementing `C-01` exactly. Place it after the imports
   and before `get_scene`. It must call `_open_gatherings` and
   `_active_members` -- not re-express their predicates in a new query.
2. Give it a docstring stating: the open gatherings at this location and
   session that still hold at least one active member; the empty ones are
   shells left by a membership close and must not be taken as evidence that
   the location has already been entered.
3. In `enter_scene`, replace the assignment
   `open_g = _open_gatherings(location_id, sess.id, db)` with
   `live_g = _live_gatherings(location_id, sess.id, db)` and the guard
   `if not open_g:` with `if not live_g:`. Rename no other local. Add no line
   to the function body: `enter_scene` has 4 lines of headroom and this brief
   spends none of them.
4. Update the comment on the guard so it states what the new predicate means:
   no LIVE gathering means either a genuine location transition or a location
   whose gatherings are all shells; both want a fresh partition, and
   `enter_location` dissolves whatever is still open before generating.
5. Update `enter_scene`'s docstring, which currently says the call happens
   "ONLY if no open gatherings already exist for this location+session": it
   now happens when no open gathering holds an active member.

## Scope OUT

- `_open_gatherings` itself. Six readers depend on it; filtering there was
  rejected with a named reactivation condition.
- `get_scene`, `_scene_response` and `scene_join`. An empty gathering stays
  displayable and joinable in code; this lot removes the state rather than
  hardening every reader against it. `_scene_response`'s `gatherings` key
  keeps coming from `_open_gatherings`.
- Dissolving anything here. `enter_location` already dissolves every open
  gathering at the location before regenerating; brief C handles dissolution
  at the moment of emptying.
- `close_open_memberships`, `migrate_npc`, the creator CRUD, the frontend.
- Any write against the production database. The repair is this code change
  taking effect on the next entry, nothing else.
- Every later brief in this lot: B, C, D, E, F, G.

## Invariants to defend

- **"Dissolve-before-create lives in the caller (`enter_location`), never
  inside `generate_gatherings`."** This brief must not move dissolution into
  the guard or into the core. It changes only which condition reaches
  `enter_location`.
- The idempotent-enter property behind contract B1/C1: a re-render or F5 at a
  location holding a live gathering must still be a silent no-op that returns
  the existing partition. Case row 3 of the lot's table b1 is the one that
  must not change.
- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. Regeneration dissolves before it creates, so this brief cannot
  produce a second open membership; confirm that in the live test rather than
  assuming it.

## Decision rights

STOP:
- `enter_scene` uses `open_g` anywhere other than the guard. The rename is
  then not local and the brief is incomplete.
- `_active_members` or `_open_gatherings` no longer has the signature in the
  anchors.
- The change cannot be made without adding a line to `enter_scene`.

ADAPT:
- `routes/scene.py` does not currently import `_active_members` from `..play`:
  add it to the existing `from ..play import (...)` block, alphabetically,
  and report.
- A linter requires the new function to sit elsewhere in the module: place it
  at the nearest position that satisfies the linter, and report.

REPORT-ONLY:
- Any other empty-gathering reader you notice (`scene_join`,
  `_scene_response`, `_render_gathering_status`).
- The dead `enter_location`/`migrate_npc` imports in `routes/mutations.py`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `_live_gatherings` exists in `routes/scene.py`, calls both
      `_open_gatherings` and `_active_members`, and is called by `enter_scene`.
- [ ] `grep -n "open_g" src/world_engine/cockpit/routes/scene.py` returns
      nothing.
- [ ] `enter_scene` is at most 76 physical lines
      (`python -c "import ast,pathlib; t=ast.parse(pathlib.Path('src/world_engine/cockpit/routes/scene.py').read_text()); print([(n.name,n.end_lineno-n.lineno+1) for n in ast.walk(t) if getattr(n,'name','')=='enter_scene'])"`).
- [ ] Against a scratch carrier (`WORLD_ENGINE_DATABASE_URL` pointed at a
      throwaway SQLite file, never `~/.world_engine/`): a world with one
      location, one player character there and one alive NPC there;
      `POST /api/scene/enter` yields one gathering holding the NPC; a
      `PUT /api/entities/{npc}` moving the NPC to a second location empties
      that gathering without dissolving it; a `PUT` moving it back leaves
      `current_location_id` correct; and a second `POST /api/scene/enter` now
      returns a gathering whose `members` contains the NPC, with the first
      gathering's `status` reading `dissolved`.
- [ ] Same scratch carrier, the preserved case: with two NPCs present and one
      still holding an active membership, `POST /api/scene/enter` returns the
      existing partition unchanged and creates no new `gathering` row.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/function_length.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] `/review-step` then `/close-step`.

## Docs to update

None. The behaviour change is described by the ticket's acceptance criteria;
the CLAUDE.md invariant wording and the decision-registry entry are brief G's
work, so that the registry records the whole lifecycle change once rather than
in pieces.
