<!-- slug: pc-resolution -->
# BRIEF 0125-A — "Land 0124's artifacts; refuse to pick one PC among several"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `ls tooling/tickets tooling/lots tooling/briefs | grep 0124` on the branch
  base -> nothing tracked (R-01). Then `git status --porcelain tooling/`
  tells whether the files are present untracked (that is the trigger of
  Scope IN 1, not an anchor).
- `src/world_engine/cockpit/crud/entities.py:209-220` -> `_player_character_id`
  selects `Character` joined to `Entity`, `.first()`, 400
  `"No player character in the active world."` when none (R-04).
- `src/world_engine/analyzer_transcript.py:248-255` -> `_resolve_player_id`,
  same query, `.first()`, returns `char.id if char else None` (R-04).
- `src/world_engine/cockpit/routes/day.py:124-137` ->
  `_resolve_player_character` raises 400 when `len(rows) != 1` (R-04).
- `src/world_engine/cockpit/routes/creator.py:767-771` -> the bootstrap
  catches `HTTPException` around `_player_character_id` (R-05).
- `tooling/verify/checks/world_sheet.py:47-62` -> `_fresh_engine` as R-34.

Halt if any has moved.

## Facts carried

### R-01 -- TICKET-0124 artifacts on `main`
Opened: `ls tooling/tickets | grep 0124`, `ls tooling/lots | grep 0124`,
`ls tooling/briefs | grep 0124` at `2e4e140`.
Finding: all three print nothing. `tooling/tickets` ends at
`TICKET-0123-lore-usage-since.md` among numbered tickets. 0124's code is on
`main` (`scripts/migrate_v2_30_world_tone.py`, `world_premise.py`).
Consequence: brief A commits them, as a separate commit, only if they are
present untracked in the working tree; otherwise it reports and goes on.
Nia says Claude Code did not commit them.
### R-04 -- PC lookups that choose "the" PC
Opened: `src/world_engine/cockpit/crud/entities.py:209-220`,
`src/world_engine/analyzer_transcript.py:248-255`,
`src/world_engine/cockpit/routes/day.py:124-137`.
Finding: `_player_character_id(db, world_id)` selects `Character` joined to
`Entity` where `Entity.world_id == world_id` and `character_type ==
"player"`, `.first()`; none -> `HTTPException(400, "No player character in
the active world.")`. `_resolve_player_id(db, world_id)` is the same query,
`.first()`, returns `char.id if char else None`.
`_resolve_player_character(world_id, db)` selects `.all()` and raises 400
`"expected exactly one player character for this world, found {n}"` when
`len(rows) != 1`.
Consequence: M2 touches the first two only; Journée already refuses.
### R-05 -- every lookup by `character_type == "player"` in `src/`
Opened: `grep -rln '\.first()' src/world_engine | xargs grep -ln
'character_type == "player"'` and `grep -rn '_player_character_id(' src`.
Finding (pasted):
```
src/world_engine/writes/events.py
src/world_engine/cockpit/crud/entities.py
src/world_engine/cockpit/crud/skills.py
src/world_engine/cockpit/routes/day.py
src/world_engine/analyzer_transcript.py
---
cockpit/routes/creator.py:769   player_id = _crud._player_character_id(db, world_id)
cockpit/routes/scene.py:82,110,183,391   player_id = <given> or _crud._player_character_id(...)
cockpit/routes/play.py:97,381,436        player_id = <given> or _crud._player_character_id(...)
cockpit/routes/spatial.py:69,117         player_id = <given> or _crud._player_character_id(...)
```
`writes/events.py:179` and `crud/skills.py:204` are predicates on one
character (`character.character_type == "player"`), not lookups;
`crud/skills.py:526` loops over every PC of a world (`_backfill_open_skill`),
correctly. `routes/day.py` refuses (R-04). The bootstrap
(`routes/creator.py:767-771`) catches `HTTPException` and returns
`player_id: None`.
Consequence: the M2 sites are exactly `_player_character_id` and
`_resolve_player_id`. The 10 callers need no edit: a refusal raised inside
`_player_character_id` reaches them as an `HTTPException`, and the bootstrap
already turns one into `player_id: None`.
### R-06 -- one PC per user and world
Opened: `src/world_engine/models/canon.py:154-158`.
Finding: `Index("idx_character_one_pc_per_user_world", "world_id",
"user_id", unique=True, sqlite_where=text("character_type = 'player'"))`.
`create_player_character` binds every PC to the lone `role == "creator"`
user (`routes/creator.py:821`).
Consequence: today a world holds at most one PC; a second one can only
appear once TICKET-0126 binds PCs to player profiles. M2 is preventive and
proven by a fixture (brief A), not live.
### R-34 -- DB fixture pattern for a check
Opened: `tooling/verify/checks/world_sheet.py:47-62` (`_fresh_engine`),
`:213-240` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` makes a temp dir, sets
`WORLD_ENGINE_DATABASE_URL=sqlite:///<tmp>/check.db` and
`WORLD_ENGINE_ENV=test` (setdefault), puts `src` on `sys.path`, drops every
cached `world_engine` module, imports `world_engine.models`, then
`SQLModel.metadata.create_all(engine)` with `world_engine.db.engine`. Route
functions are then called directly with a `Session`. `main()` runs each rule
in `try/except Exception`, turning a crash into a failure, and prints
`FAIL:` lines / one `PASS:` line.
Consequence: every new DB-backed check of this lot builds its database with
this `_fresh_engine` body (copied: each check is standalone) and never
touches Nia's database.

## Contracts

This brief produces no contract of the contract sheet. It implements the M2
case table of the lot (Gate output, (b)), copied here verbatim:

| PCs in `w` | `_player_character_id` | `_resolve_player_id` |
|---|---|---|
| 0 | 400 `"No player character in the active world."` (unchanged) | None |
| 1 | that PC's id | that PC's id |
| 2+ | 409 `"Plusieurs personnages joueurs dans ce monde : précisez lequel."` | None |

## Context

TICKET-0125 opens the player's side. From TICKET-0126 on, several player
profiles may each hold a PC in the same world (R-06). Two creator lookups
pick the first PC they meet; they must refuse instead (M2). The "active PC"
selector is TICKET-0128. TICKET-0124's ticket, lot and briefs were never
committed (R-01); this brief lands them first.

## Scope IN

1. **Commit 1 (conditional) -- "Land TICKET-0124 artifacts".** Trigger: one
   or more untracked files matching `tooling/tickets/TICKET-0124-*.md`,
   `tooling/lots/LOT-0124-*.md`, `tooling/briefs/BRIEF-0124-*.md` or
   `tooling/briefs/AMENDMENT-0124-*.md` / `tooling/tickets/AMENDMENT-0124-*.md`
   exist in the working tree. Action: `git add` exactly those files,
   unchanged (no edit, no front-matter change), and commit them alone. No
   trigger: no commit; report it. This commit precedes every other one.
2. **Commit 2 -- M2.** In `crud/entities.py::_player_character_id`, replace
   `.first()` by `.all()`; zero rows -> the existing 400 unchanged; more
   than one -> `HTTPException(status_code=409, detail="Plusieurs personnages
   joueurs dans ce monde : précisez lequel.")`; one -> its id. Add one
   docstring sentence: "TICKET-0125 (M2): more than one PC in the world is a
   refusal, never a choice."
3. In the same commit, `analyzer_transcript.py::_resolve_player_id`:
   `.all()`; return the id when exactly one row, else `None`. Docstring
   sentence: "TICKET-0125 (M2): None unless the world has exactly one PC."
4. In the same commit, a new check `tooling/verify/checks/pc_resolution.py`,
   docstring first sentence "G1 check for TICKET-0125 -- a world with several
   player characters is refused, never resolved to one of them.", rules:
   - **PR1** -- fixture (R-34 `_fresh_engine`): one world, two `user` rows
     (`role="creator"` and `role="player"`, written with `db.add`, `user` is
     not canon), the M2 table walked row by row: 0 PCs, then one PC
     (`Entity` + `Character(character_type="player", user_id=<creator>)`),
     then a second PC bound to the player user. Each row asserts both
     functions exactly as the table says (status code AND detail for the
     refusals). A row not reached is a failure.
   - **PR2** -- static: the bodies of `_player_character_id` and
     `_resolve_player_id` (AST, found by name) contain no `.first()` call;
     either function not found is a failure.
   PASS line: `PASS: pc_resolution -- 0, 1 and 2 PCs in one world: refused, resolved, refused`.
5. Link `verify/checks/pc_resolution.py` in TICKET-0125's Machine-checkable
   section is already present; do not edit the ticket.

## Scope OUT

- No caller of `_player_character_id` is edited (R-05: the refusal reaches
  them as an `HTTPException`).
- `routes/day.py::_resolve_player_character` is not touched (it already
  refuses).
- No "active PC" selector, no change to the bootstrap (TICKET-0128).
- No edit to any 0124 artifact's content, and no status change on
  TICKET-0124.
- Every later brief of this lot.

## Invariants to defend

- INV-08 / INV-11: this brief writes no canon path; the check writes canon
  rows only in its own temp database.
- The verify-check rules (`.claude/rules/verify-checks.md`): fail-closed,
  a named mutation per rule, never Nia's database.
No CLAUDE.md invariant is otherwise at stake.

## Decision rights

STOP:
- an anchor above has moved;
- a tracked 0124 artifact exists and differs from the untracked one of the
  same name (two versions of one artifact).
ADAPT:
- the 0124 files carry another naming than listed (e.g. a slug variant):
  commit every untracked file whose name contains `0124` under
  `tooling/tickets|lots|briefs`, unchanged, and list them in the report;
- `_resolve_player_id` gained another caller since the RECON: keep the
  change, list the caller in the report.
REPORT-ONLY:
- any other "first PC" lookup found in `src/` (the lot enumerated them in
  R-05).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit 1 exists iff the trigger held; it contains only 0124 files.
- [ ] `python tooling/verify/checks/pc_resolution.py` prints its PASS line.
- [ ] Named mutation PR1: restoring `.first()` with no count test in
      `_player_character_id` makes PR1 fail on the 2-PC row (then revert).
- [ ] Named mutation PR2: the same edit makes PR2 fail (then revert).
- [ ] `python tooling/verify/checks/corpus_gate.py` passes (with
      `WORLD_ENGINE_ENV=test`).
- [ ] `/review-step` and `/close-step` on commit 2.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: one entry, inserted above
  the footer (`---` / `*Co-built…*`), header
  `## A world with several PCs refuses instead of choosing (BRIEF-0125-A, no schema change)`,
  body: M2, the two functions, the 409 message, why Journée was already
  safe (R-04), that the selector is TICKET-0128.
- Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
