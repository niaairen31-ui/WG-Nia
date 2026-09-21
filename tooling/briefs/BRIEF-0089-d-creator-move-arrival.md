# BRIEF 0089-D — "A creator move attaches the NPC at its destination"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: BRIEF-0089-b (line budget in `crud/entities.py`),
BRIEF-0089-c (consumes `C-02`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/cockpit/crud/entities.py` -> `update_entity` captures
  `prior_location_id = ext.current_location_id` inside
  `if entity.type == "character":`, then runs, verbatim:
  ```
      if entity.type == "character" and ext is not None and ext.current_location_id != prior_location_id:
          close_open_memberships(entity_id, db)
      if prior_status == "active" and entity.status != "active":
          close_open_memberships(entity_id, db)

      db.commit()
  ```
- `update_entity` is at most 71 physical lines against an 80-line cap.
- `crud/entities.py` is at most 890 lines after BRIEF-0089-b.
- `delete_entity` calls `close_open_memberships(entity_id, db)` then
  `db.commit()`.
- `src/world_engine/gathering.py` declares `dissolve_emptied` with the `C-02`
  signature (BRIEF-0089-c landed).
- `src/world_engine/gathering.py:175-180` -> `_solo_partition` builds
  `{"label": f"{entity.name}, seul·e", "members": [entity.id]}`.
- `src/world_engine/gathering.py:236-243` -> `generate_gatherings` builds
  `Gathering(world_id=location.world_id, session_id=..., location_id=...,
  label=group["label"], status="open", created_at=now)`.
- `src/world_engine/cockpit/play.py` -> `_get_or_open_session(world_id, db)`
  returns the world's open session **or creates and commits one**.
- `src/world_engine/models` -> `Session` (the play session) carries
  `world_id`, `number`, `status`, and `Gathering` carries `world_id`,
  `session_id`, `location_id`, `label`, `status`, `created_at`,
  `dissolved_at`.

## Facts carried

**R-09 — the creator CRUD closes memberships at three sites.** Verbatim at
`:787-794`:
```
    # BRIEF-53 A1: a character's location change, or any transition to a
    # non-active entity.status, closes its open gathering_member rows
    # (gatherings are not canon -- no proposed_mutation, no change_history).
    # Re-saving with the same current_location_id must not close anything.
    if entity.type == "character" and ext is not None and ext.current_location_id != prior_location_id:
        close_open_memberships(entity_id, db)
    if prior_status == "active" and entity.status != "active":
        close_open_memberships(entity_id, db)
```
plus `delete_entity`. `prior_location_id` is captured at `:771`. `db.commit()`
follows at `:796`. Consequence: the equality guard at `:791` is what keeps a
re-save from closing anything, and it stays.

**R-03 — `enter_location` has exactly one live caller, and it is guarded.**
Even after BRIEF-0089-a, a location holding a live gathering legitimately
blocks regeneration -- which is the whole point of the guard. An NPC moved
into the room the player is standing in therefore never gets a membership
from the entry path.

**R-30 — `_get_or_open_session` creates a session when none is open.**
Consequence: this brief must not call it. A creator-side sheet save may not
open a play session.

**R-14 — function length ceilings.** `MAX_LINES = 80`, no baseline. Briefs D
and E share the 9 free lines inside `update_entity`; this brief takes at most
4 of them.

**R-20 — gathering rows are outside the canon-write policy.** No
`[ALLOWED_SITES]` entry is needed for the insert this brief adds.

## Contracts

**C-02 — `dissolve_emptied`** (consumed)
`dissolve_emptied(gathering_ids: Iterable[str], db: Session, model: str = ollama_client.DEFAULT_MODEL, host: str = ollama_client.OLLAMA_HOST) -> list[str]`
For each distinct id, if the gathering exists, is `open`, and has no
`GatheringMember` row with `left_at IS NULL`: analyse its open conversations,
then set `status='dissolved'` and `dissolved_at=now`. Commits once at the end.
Returns the ids dissolved. Never raises; unknown ids and non-empty gatherings
are skipped.

**C-03 — `attach_on_arrival`** (produced)
Produced by: BRIEF-0089-d   Consumed by: BRIEF-0089-d, BRIEF-0089-g
Declared in: `src/world_engine/gathering.py`.
Signature: `attach_on_arrival(entity_id: str, location_id: Optional[str], db: Session) -> Optional[str]`
Behaviour, in order, returning `None` at the first miss:
1. `location_id` is not `None`.
2. `db.get(Entity, entity_id)` exists and has `status == 'active'`.
3. `db.get(Character, entity_id)` exists, `character_type == 'npc'`,
   `vital_status == 'alive'`.
4. `db.get(Entity, location_id)` exists and is a `location`.
5. A play-session row (`models.Session`, imported into `gathering.py` as
   `Session as PlaySession` because `sqlmodel.Session` already owns the bare
   name there) for that location's `world_id` with `status == 'open'` exists
   -- found by a read-only `select`, never by `_get_or_open_session`.
6. At least one `Gathering` with that `session_id`, that `location_id` and
   `status == 'open'` exists.
Then: insert one `Gathering` with `world_id` taken from the LOCATION entity
(matching `generate_gatherings`, which reads `location.world_id`),
`session_id`, `location_id`, `label = f"{entity.name}, seul·e"` (the exact
shape of `_solo_partition`), `status='open'`, `created_at=now`; and one
`GatheringMember` (`gathering_id`, `entity_id`, `joined_at=now`,
`left_at=None`); then return the new gathering id.
Return shape: the new gathering id, or `None`.
Error and empty cases: does NOT commit -- the caller owns the transaction,
same convention as `close_open_memberships`. Never raises. Never opens a
session. Never joins an existing gathering.

## Context

Briefs A and C make a departure clean: the shell is gone and the entry guard
ignores any that survive. The arrival is still missing. When Nia moves an NPC
into the room her player is standing in, that room legitimately holds a live
gathering, so the entry guard does not regenerate -- correctly, since
regenerating would reshuffle the scene she is in. The NPC therefore stays
invisible until she leaves and returns. This brief gives the write that owns
the departure the matching responsibility for the arrival.

## Scope IN

1. In `src/world_engine/gathering.py`, add `attach_on_arrival` implementing
   `C-03`. Place it immediately after `dissolve_emptied`. Add
   `Session as PlaySession` to the `from .models import (...)` line, and
   `Optional` to the `typing` import.
2. Its docstring states: the creator-side counterpart of
   `close_open_memberships` -- a manually relocated NPC arrives into a
   location the player has already entered this session, where the entry guard
   will not regenerate because a live gathering is legitimately there. The
   arrival is always solo: code never asserts that an arriving NPC joined an
   existing group; the MJ partition at entry is the only authority for that.
   It states the two negatives explicitly: it never opens a session, and it
   does not commit.
3. In `crud/entities.py`, rewrite the block at `:787-796` to collect the
   closed rows, attach at the destination before the commit, and dissolve
   whatever was emptied after it:
   ```
       closed: list = []
       if entity.type == "character" and ext is not None and ext.current_location_id != prior_location_id:
           closed += close_open_memberships(entity_id, db)
           attach_on_arrival(entity_id, ext.current_location_id, db)
       if prior_status == "active" and entity.status != "active":
           closed += close_open_memberships(entity_id, db)

       db.commit()
       dissolve_emptied({row.gathering_id for row in closed}, db)
   ```
   Keep the existing four-line comment above it and extend it by one sentence
   naming the two new verbs and why the dissolve runs after the commit.
   Net growth of `update_entity`: 4 lines.
4. Import `attach_on_arrival` and `dissolve_emptied` from `...gathering`
   alongside the existing `close_open_memberships` import.
5. In `delete_entity`, apply the same post-commit dissolve:
   ```
       closed = close_open_memberships(entity_id, db)
       db.commit()
       dissolve_emptied({row.gathering_id for row in closed}, db)
   ```
   No arrival there -- a soft-deleted entity arrives nowhere.

## Scope OUT

- The status-transition branch gains no `attach_on_arrival`. An entity
  becoming inactive arrives nowhere, and one becoming active again is not a
  move: it will be placed by the next entry.
- `mutations.py`'s `_mutation_apply_npc_move` (the tick path). It closes
  memberships too, and is the second place that could leave a shell, but the
  tick is followed by its own scene flow and this lot does not touch it.
  REPORT-ONLY.
- Joining an existing gathering at the destination. Named and rejected: the
  arrival is always solo.
- Opening a play session from the creator surface, in any form.
- Any change to how the label is rendered, to `_gathering_brief`, or to the
  scene response shape.
- Regenerating the whole partition on arrival. That is `enter_location`'s job
  and would reshuffle the scene the player is standing in.
- Every other brief in this lot: A, B, C, E, F, G.

## Invariants to defend

- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. `attach_on_arrival` runs only after `close_open_memberships` has
  closed every open row for that entity, in the same transaction, so the
  inserted row is the only open one. This is the invariant most at risk in
  this brief -- verify it in the live test, on an NPC that was in a gathering
  before the move.
- **Creator-CRUD edits that change a character's `current_location_id`, or set
  an entity's `status` to a non-active value, MUST close that entity's open
  `gathering_member` rows via `close_open_memberships`.** The equality guard
  stays; a re-save with an unchanged location must still close nothing,
  attach nothing and dissolve nothing.
- **Single canon-write paths.** Nothing here writes canon: `gathering` and
  `gathering_member` are not canon tables, and `current_location_id` itself is
  still written by the existing `setattr` loop, untouched by this brief.
- **History is sacred.** The arrival inserts; it updates no existing row.

## Decision rights

STOP:
- `crud/entities.py` is over 886 lines before your edit -- BRIEF-0089-b has
  not landed and the budget is not there.
- `dissolve_emptied` is absent from `gathering.py` -- BRIEF-0089-c has not
  landed.
- `update_entity` would exceed 80 lines after the edit.
- The `:791` equality guard is not in the anchor's shape.

ADAPT:
- `close_open_memberships` returns something other than a list of rows
  carrying `gathering_id`: build the id set from whatever it returns, and
  report.
- A formatter splits the comprehension in the `dissolve_emptied` call across
  lines and pushes `update_entity` over 80: extract the whole block into a
  module-level `_close_and_relocate(entity, ext, prior_location_id, prior_status, db)`
  helper in the same file, called once from `update_entity`, and report.

REPORT-ONLY:
- `_mutation_apply_npc_move`'s close site and whether it now leaves shells.
- Any other writer of `current_location_id` you find.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `attach_on_arrival` exists in `gathering.py` with the `C-03` signature
      and returns `None` at each of the six guard misses.
- [ ] `grep -n "_get_or_open_session" src/world_engine/gathering.py` returns
      nothing.
- [ ] Against a scratch carrier (`WORLD_ENGINE_DATABASE_URL` pointed at a
      throwaway SQLite file, never `~/.world_engine/`), all five rows of the
      lot's case table b2 observed through `PUT /api/entities/{id}`:
      destination NULL -> no gathering created; a player character moved ->
      none; no open session -> none; open session but destination has no open
      gathering -> none; open session and destination has an open gathering ->
      exactly one new open gathering labelled `"<name>, seul·e"` holding
      exactly that NPC.
- [ ] Same carrier, the round trip: player at X with NPC B present; move NPC A
      from Y into X; `GET /api/scene` now lists a second group holding A,
      without any call to `/api/scene/enter`; and A has exactly one
      `gathering_member` row with `left_at IS NULL`.
- [ ] Same carrier, the departure: moving the last NPC out of a gathering
      leaves that gathering `dissolved` with a non-null `dissolved_at`, and
      `POST /api/scene/enter` at that location regenerates.
- [ ] Same carrier, the no-op: re-saving a sheet without changing the location
      creates no gathering, closes no membership and dissolves nothing.
- [ ] `update_entity` is at most 76 physical lines.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/function_length.py` passes.
- [ ] `python tooling/verify/checks/single_canon_write.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] `/review-step` then `/close-step`.

## Docs to update

None here. Brief G records the lifecycle in `ARCHITECTURE_DECISIONS.md` and
extends the CLAUDE.md invariant, once briefs C and D have both landed.
