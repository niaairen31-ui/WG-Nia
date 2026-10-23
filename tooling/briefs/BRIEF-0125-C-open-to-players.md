<!-- slug: open-to-players -->
# BRIEF 0125-C — "Création > Monde: « Ouvert aux joueurs »"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: BRIEF-0125-B (`World.open_to_players`)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/models/canon.py` -> `World.open_to_players` exists (B).
- `src/world_engine/cockpit/routes/creator.py:567-571` -> `WorldUpdateBody(name, description="", tone="", laws=[])` (R-08).
- `src/world_engine/cockpit/routes/creator.py:607-621` -> `_world_detail`
  returns `{id, name, description, tone, laws, is_active}` (R-08).
- `src/world_engine/cockpit/routes/creator.py:632-652` -> `update_world`
  sets name, description, tone, `updated_at`, laws, one commit (R-08).
- `tooling/verify/canon_write_policy.txt:143` -> `update_world` may write `world` (R-08).
- `tooling/verify/checks/world_sheet.py:65-71` -> `_expect` checks listed keys only (R-09).
- `frontend/src/creation/WorldSheet.svelte:62` -> the PUT body
  `{ name, description, tone, laws: ... }` (R-10).

Halt if any has moved.

## Facts carried

### R-08 -- world routes
Opened: `src/world_engine/cockpit/routes/creator.py:532-538` (`list_worlds`),
`:560-571` (`WorldCreateBody`, `WorldUpdateBody`), `:607-621`
(`_world_detail`), `:623-630` (`get_world`), `:632-652` (`update_world`).
`creator.py` is 963 lines.
Finding: `WorldUpdateBody(name: str, description: str = "", tone: str = "",
laws: list[str] = [])`. `_world_detail` returns `{id, name, description,
tone, laws, is_active}`, laws = `WorldLaw.text_` by `position`.
`update_world` strips name (empty -> 422 `"Le nom est requis."`), sets
description/tone (empty -> None), `updated_at`, rewrites laws through
`write_world_laws`, one commit; never touches `is_active` or
`current_phase`. `list_worlds` returns `{id, name, is_active}` per world.
`canon_write_policy.txt:143` allows `routes/creator.py::update_world` to
write `world`.
Consequence: C adds `open_to_players: Optional[bool] = None` to
`WorldUpdateBody` (None = unchanged) and the key to `_world_detail`;
`creator.py` +5 lines stays under 1000.
### R-09 -- `world_sheet.py` (a gate C must pass)
Opened: `tooling/verify/checks/world_sheet.py:1-30, 65-71, 95-165, 205-212`.
Finding: WS2/WS3 compare `get_world`/`update_world` answers through
`_expect`, which checks only the keys it lists (`got.get(key) != value`);
WG1 requires `WorldSheet.svelte` to hold `/api/worlds/`, `method: 'PUT'`,
`Ton et style`, `refreshServerState` and none of `alert(`, `confirm(`,
`prompt(`.
Consequence: a new key in `_world_detail` and a checkbox in
`WorldSheet.svelte` keep `world_sheet.py` green unchanged.
### R-10 -- the Monde page
Opened: `frontend/src/creation/WorldSheet.svelte` (121 lines).
Finding: `$state` fields `name, description, tone, laws`; `load(worldId)`
reads `GET /api/worlds/{id}`; `save()` sends `PUT` with body
`JSON.stringify({ name, description, tone, laws: ... })` (line 62); the
form has labelled fields `Nom *`, `Contexte du monde`, `Ton et style`, then
the laws list.
After a successful PUT only `laws` is reset from the answer (line 75,
`laws = [...(world.laws ?? [])]`), then `refreshServerState()`.
Consequence: C adds `openToPlayers` state, a checkbox labelled
`Ouvert aux joueurs`, and `open_to_players: openToPlayers` in the PUT body.
### R-31 -- module budgets of edited files
Opened: `wc -l` at `2e4e140`.
Finding: `routes/creator.py` 963, `models/canon.py` 961,
`models/pipeline.py` 811, `crud/entities.py` 923, `analyzer_transcript.py`
931, `lore_query.py` 244, `lore_plan.py` 130, `lore_render.py` 320,
`name_index.py` 138, `routes/lore.py` 184, `app.py` 329,
`frontend/src/lore/Lore.svelte` 237.
Consequence: every edit in this lot adds under 30 lines to any of these;
none crosses 1000. New modules start small.
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

### C-13 -- world detail and update
Produced by: C   Consumed by: E, G
`_world_detail` gains `"open_to_players": bool`. `WorldUpdateBody` gains
`open_to_players: Optional[bool] = None`; `update_world` sets the column
only when it is not None.

## Context

Nia decides which worlds a player may enter (C1). The flag lives on the
world and is edited on the « Monde » page of Création, next to the
description and the laws the player will read.

## Scope IN

1. `routes/creator.py`: `WorldUpdateBody` gains
   `open_to_players: Optional[bool] = None`. `update_world`: after the tone,
   `if body.open_to_players is not None: world.open_to_players = body.open_to_players`.
   `_world_detail` gains `"open_to_players": world.open_to_players`.
   Docstring of `update_world` gains: "TICKET-0125 (C1): the « Ouvert aux
   joueurs » flag is set only when sent; omitted, it stays."
2. `frontend/src/creation/WorldSheet.svelte`: `let openToPlayers =
   $state(false);` read in `load` from `world.open_to_players ?? false`, and
   after a successful PUT set `openToPlayers = world.open_to_players ?? false`
   right after the `laws` reset (line 75); a checkbox
   placed after the « Ton et style » field:
   ```svelte
   <label class="world-sheet-open">
     <input type="checkbox" id="world-sheet-open" bind:checked={openToPlayers}>
     Ouvert aux joueurs
   </label>
   ```
   and the PUT body becomes `{ name, description, tone, open_to_players:
   openToPlayers, laws: ... }`. No `alert(`, `confirm(`, `prompt(` (WG1).
3. `cd frontend && npm run build`; commit the built output with the source.
4. New check `tooling/verify/checks/player_worlds.py`, docstring first
   sentence "G1 check for TICKET-0125 (BRIEF-0125-C) -- a world opens to
   players from the « Monde » page and only when told.", rules (fixture R-34;
   route functions called directly with a `Session`, as `world_sheet.py`):
   - **PW1** -- `create_world` then `get_world`: `open_to_players` is
     `False`.
   - **PW2** -- `update_world` with `open_to_players=True` answers it
     `True` and the row holds it; a second `update_world` without the field
     answers `True` still; one with `False` answers `False`.
   - **PW3** -- static: `WorldSheet.svelte` holds `bind:checked={openToPlayers}`,
     `open_to_players: openToPlayers` and `Ouvert aux joueurs`.
   PASS line: `PASS: player_worlds -- a world is closed by default, opens and closes from the « Monde » page, and an omitted flag changes nothing`.

## Scope OUT

- No player route reads the flag here (E).
- `WorldCreateBody` / `create_world` unchanged: a new world starts closed.
- `list_worlds` unchanged.
- The world-create modal (`WorldCrud.svelte`) unchanged.
- Every later brief of this lot.

## Invariants to defend

- INV-08: `update_world` is the allowed `world` writer; no new write site.
- INV-49/INV-50: the « Monde » page stays the existing `worldSheet` island;
  no registry change.
- INV-55: no `$effect` writes `openToPlayers` and reads it after.

## Decision rights

STOP: an anchor has moved; `world_sheet.py` turns red.
ADAPT: the label class name collides with an existing class: rename the
class only.
REPORT-ONLY: layout remarks on the page.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `player_worlds.py` and `world_sheet.py` PASS.
- [ ] Named mutation PW2: setting the column unconditionally
      (`world.open_to_players = bool(body.open_to_players)`) makes PW2 fail
      (then revert).
- [ ] `frontend_build_fresh.py` PASS (rebuilt and committed).
- [ ] `corpus_gate.py` passes.
- [ ] Live (Nia): the checkbox shows, saves and reloads.
- [ ] `/review-step` and `/close-step`.

## Docs to update

- None beyond the docstrings: the decision is recorded by brief B's entry.
- Regenerate `FILE_MAP.md` (new check).
