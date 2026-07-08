# RECON-0015 — npc-movement (interval-scaled off-screen movement in the world tick)

Date: 2026-07-08
Branch inspected: `main` (post TICKET-0014 merge; schema head v1.70; live-gate 0014 validated by Nia)
Mode: report-only. No actions taken.

Locked decisions in force: E3 (interval-scaled radius, structural), co-located
NPCs NOT excluded (an approved move pulls the NPC out of its open gathering,
player present or not), G2/I2/A1/B2/H1 locked for LATER tickets (not this one).

---

## F1 — CORRECTION to TICKET-0015: interval labels are verbatim French strings

`cockpit/app.py:4752` — `_VALID_TICK_INTERVALS = frozenset({"quelques heures",
"quelques jours", "quelques semaines"})`, enforced at the endpoint
(`app.py:4774-4775`, 422 on anything else). The ticket's radius map was drafted
as `heures | jours | semaines`; the real keys MUST be the three verbatim
labels. The label reaches the runner untouched (`app.py:4841` ->
`run_world_tick(db, npc_ids, body.interval)`), so the radius map lives in
`tick.py` keyed on the same three strings — no endpoint change needed.

## F2 — `assemble_tick_context` is interval-agnostic; the destination section
## needs a new input, and the candidate set must be computed ONCE per NPC

`tick.py:109` — `assemble_tick_context(npc_id: str, session: Session)`. The
briefing has no interval input, but `OÙ TU PEUX ALLER` depends on the radius.
Meanwhile the normalizer must resolve the proposed destination against the
SAME candidate set the model was shown. Consequence: the reachable set must be
computed once per NPC in `run_world_tick` (which already loads `npc_char` and
`current_location_id` at `tick.py:507-510` for `_build_roster`) and passed
BOTH into the briefing (new parameter) and into `_normalize_tick_item` (new
kwarg). Computing it twice (once per consumer) would open a drift window
between what the model saw and what resolution accepts.

Signature ripple: `scripts/preview_tick_context.py` (`--npc`, argparse at
line 28-29) is an allowlisted `assemble_tick_context` caller
(`tooling/verify/checks/world_tick.py:45-49`) and must gain `--interval`
(choices = the three verbatim labels) to render the new section. The T1
contract ("every section header appears in every briefing", BRIEF-0014-a)
applies: an NPC with no location or no reachable neighbour renders the header
with a French placeholder, never omits it.

## F3 — No BFS exists anywhere; the only `connects_to` traversal is
## direct-neighbours, cockpit-side, and tick.py must not import it

`cockpit/app.py:1713-1740` — `_location_neighbours(location_id, db)` returns
direct ACTIVE neighbours only (1 hop), and its docstring records decision D1:
`connects_to` readers are deliberately NOT refactored to share code.
`tick.py`'s module comment (tick.py:268-270) states it never imports
`cockpit/app.py`. Consequence: the radius traversal is a NEW tick-local
helper (BFS over `Relation.type == "connects_to"` among ACTIVE locations,
origin excluded), third `connects_to` reader, same D1 posture. Note the
semantic this forces (flagged to Nia in the brief): "quelques semaines" =
unbounded BFS = the origin's CONNECTED COMPONENT, not all locations — an
unmapped island stays unreachable at any interval, the map is the world's
traversability truth.

## F4 — Type acceptance path: shared alias map + local frozenset;
## the analyzer map must not gain `npc_move`

`tick.py:29-34` imports `_MUTATION_TYPE_MAP` from `analyzer.py`;
`tick.py:274` — `_TICK_MUTATION_TYPES = frozenset({"goal_change",
"relation_change", "new_knowledge"})`; acceptance at `tick.py:350-353` is
`_MUTATION_TYPE_MAP.get(raw_mt)` then membership in `_TICK_MUTATION_TYPES`.
`analyzer.py:94-95` maps event aliases; nothing maps `npc_move`. Consequence:
a tick-LOCAL alias dict (`{**_MUTATION_TYPE_MAP, "npc_move": "npc_move",
"move": "npc_move", "movement": "npc_move"}`) replaces the direct `.get` in
`_normalize_tick_item`, and `_TICK_MUTATION_TYPES` gains `"npc_move"`.
`analyzer._MUTATION_TYPE_MAP` stays byte-identical — conversation analysis
and overhearing can never propose movement (machine-checkable: the map
literal in analyzer.py contains no `npc_move` key).

## F5 — Rule-3 forced-attribution mechanics extend cleanly

`tooling/verify/checks/world_tick.py:56` — `_FORCED_FIELDS = ("npc_id",
"entity_a_id")`; `check_forced_attribution` (lines 118-147) fails on ANY
`.get("<field>")` call in tick.py and on any dict literal where a forced key's
value is not a bare `ast.Name`. Adding `"from_location_id"` to
`_FORCED_FIELDS` gives the origin stamp the same structural guarantee as
`npc_id` for free, provided the emit code writes
`{"npc_id": npc_id, "from_location_id": from_location_id, ...}` with bare
Names. `to_location_id` must NOT join `_FORCED_FIELDS`: it is legitimately
DERIVED from the model's `destination` name via the candidate set (the
resolved id is still a bare Name at the dict site, so rule 3 tolerates it
either way — but semantically it is resolved, not forced).

## F6 — Duplicate guard: the 0014 tick doctrine is canon-existence checks,
## and for movement the stale-from check subsumes the duplicate check

`cockpit/app.py:753-782` — the tick branch of `_find_applied_duplicate`
deliberately ignores `tick_id` equality and asks the CANON (re-run-proof,
revival-safe). For `npc_move` the canon question is "is the NPC still at
`from_location_id`?": a second approval of the same move finds
`current_location_id == to_location_id != from_location_id` and fails the
stale-from test; a cross-run duplicate from a re-run tick fails it
identically; a legitimate later move A->B->A passes it correctly. One check
covers duplicate, cross-run duplicate, AND world-moved-since-proposal.
Consequence (drafting decision, flagged): the stale-from gate lives in the
APPLY BRANCH (which must load the `Character` row anyway) and
`_find_applied_duplicate` gains a mirror `npc_move` clause returning the
same verdict for pre-write blocking symmetry with the other tick types —
both compare `Character.current_location_id` to `payload["from_location_id"]`.

## F7 — Apply side: no location write helper exists; the CRUD seam is the model

`src/world_engine/writes.py:172-200` (`write_relation`) is the helper shape
precedent (keyword-only, `mutation_id` audit param, caller owns the
transaction). No helper writes `Character.current_location_id`. The
creator-CRUD seam (`cockpit/crud.py:711-724`, BRIEF-53 A1) shows the full
apply recipe: detect actual change, set the column, call
`close_open_memberships(entity_id, db)` (`gathering.py:261-283` — closes
`left_at IS NULL` rows, never deletes, does not commit, caller owns the
transaction). Note: `character` has no `change_history` column and the CRUD
location edit snapshots nothing — the `proposed_mutation` row itself
(payload from->to, `applied_at`, `tick_id`) is the durable audit trail; the
apply branch follows the same convention rather than inventing a history
mechanism this step.

## F8 — Prompt: the system prompt's closed contract must be re-versioned,
## and the head already exists (append-version branch only)

`scripts/seed_pilot.py:844-905` — `WORLD_TICK_SYSTEM_PROMPT` locks "EXACT 5
keys", enumerates the three types twice (key list + payload shapes), and the
SCALE section already scales ambition to «{interval_label}». A new version
must: add `npc_move` to the type enumeration, add the payload shape
(`npc_move -> {"destination":"<name from OÙ TU PEUX ALLER>"}`,
`target_table: "character"`), and add a MOVE RULES block (at most one move
per interval; destination ONLY from the section; staying put is legitimate
and is expressed by emitting no npc_move). Delivery via
`scripts/apply_ticket_0015_prompt_updates.py` on the 0013/0014 script
pattern — the `pt-world-tick` head exists since 0014, so ONLY the
append-a-version branch is needed (unlike 0014's head-absent branch).

## F9 — Queue rendering: payload is surfaced raw; names must ride in the payload

`cockpit/app.py:681-699` (`_mutation_dict`) returns the payload verbatim to
the queue UI; there is no per-type rendering layer to extend server-side.
Origin/destination legibility ("Reike : Le Dernier Verre -> Marché bas")
therefore rides IN the payload as display fields (`from_name`, `to_name`)
stamped at emit alongside the canonical ids — precedent: `resource_change`
payloads already carry prose display fields (`reason`).

## F10 — Scope resolution is upstream and untouched

`cockpit/app.py:4780-4835` — location- and faction-scoped invocations already
resolve to per-NPC id lists before `run_world_tick`; movement lands per
ticked NPC with zero endpoint change. An NPC with `current_location_id`
NULL simply gets an empty candidate set (F2 placeholder) and cannot move —
correct by construction.

---

## Summary of corrections to TICKET-0015 (intake -> post-recon)

1. Radius map keys are `"quelques heures" | "quelques jours" |
   "quelques semaines"` (F1), values 1 / 3 / unbounded hops.
2. "Unbounded" means the origin's connected component, not all locations (F3).
3. The `tick_id`-keyed guard promised at intake is replaced by the
   canon-existence stale-from check, per the 0014 guard doctrine (F6).
4. `from_location_id` joins `_FORCED_FIELDS`; `to_location_id` does not (F5).
5. Payload carries `from_name`/`to_name` display fields (F9).
