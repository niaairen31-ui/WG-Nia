# BRIEF 0093-A — "named refs and the two new checks"

Lot: LOT-0093-day-narration-judge.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/day_resolve.py:367` `def freeze_facts(` — its body starts
  `npcs: list[NamedRef] = []` / `locations: list[NamedRef] = []` /
  `for mm in concordance.matched:` (382-384) and never reads
  `concordance.cast`.
- `src/world_engine/day_resolve.py:69` `from .day_concordance import ConcordanceResult`.
- `src/world_engine/day_concordance.py:104` `class CastMention:` with field
  `entity_id: str`.
- `src/world_engine/cockpit/routes/day.py:937`
  `concordance_result = _read_day_rewrite_concordance(pass_play, world_id, db)`.
- `tooling/verify/checks/identity_tokens.py:108` `def _fresh_engine():` and
  `:121` `def _world(session, label: str):`.
- `tooling/tickets/TICKET-0092-names.md:5` `status: live-gate` and `:12`
  `current_brief: E`.
- `tooling/verify/checks/day_fact_sheet_refs.py` and
  `tooling/verify/checks/day_narration_beats.py` do not exist.

## Facts carried

#### R-20 — `freeze_facts` and the stored concordance
Opened: `src/world_engine/day_resolve.py:367-431`;
`src/world_engine/cockpit/routes/day.py:777-791`, `937`
Finding [M]: `freeze_facts` builds `npcs`/`locations` by iterating
`concordance.matched` only (384-392): `db.get(Entity, mm.entity_id)`, skip if
None, `NamedRef(entity_id, name)`, `type == "character"` → npcs,
`type == "location"` → locations, no duplicates. `authorised_names` = npcs +
locations + character name (418). Its docstring (370-381) says the concordance
is "a FRESH `day_concordance.concord()` result ... re-run by the caller"; the
route actually passes `_read_day_rewrite_concordance(...)`, which reads the
stored trace through `day_rewrite.load_latest` (777-791, 937).
Consequence: A moves the loop into `_named_refs` over matched **and** cast
(C-05) and corrects the docstring. `freeze_facts` is 63 lines today; it
shrinks.

#### R-21 — concordance result shapes
Opened: `src/world_engine/day_concordance.py:96-131`;
`src/world_engine/day_extract.py:41-46`; `src/world_engine/day_resolve.py:108-153`, `185`
Finding [M]: `ConcordanceResult(matched, cast, ambiguous, unmatched,
skipped_rungs)`; `MatchedMention(mention, entity_id, rung)`;
`CastMention(mention, entity_id, rung, basis, candidate_ids)`;
`UnmatchedMention(mention, rungs_tried, candidate_location_id=None)`;
`Mention(category, surface_form, kind, role_hint=None)`;
`NamedRef(entity_id, name)`; `StepFact(objective, band, dice, modifier, total,
blocked_detail=None)`; `FactSheet(world_id, day_number, character_name, steps,
npcs, locations, role_hints, resource_deltas=(), knowledge_deltas=(),
skill_deltas=(), authorised_names=frozenset())`; `BLOCKED_BAND = "blocked"`.
`day_resolve` already imports `ConcordanceResult` (69).
Consequence: the checks build these directly, with no model and (except
C-05's case) no DB.

#### R-22 — fixture idiom for a DB-backed check
Opened: `tooling/verify/checks/identity_tokens.py:108-134`;
`src/world_engine/models/canon.py:117-127`
Finding [M]: `_fresh_engine()` points `WORLD_ENGINE_DATABASE_URL` at a temp
SQLite file, purges `world_engine*` from `sys.modules`, calls
`create_db_and_tables()`. `_world(session, label)` adds
`World(name=label, is_active=False)` and returns an `entity(kind, name)` helper
creating `Entity(world_id, type, name)`. `Entity` requires `world_id`, `type`,
`name`.
Consequence: `day_fact_sheet_refs.py` copies both helpers verbatim.

#### R-01 — `judge_narration` (order of checks)
Opened: `src/world_engine/day_narration_guard.py:204-245`
Finding [M]: four checks in this order, each returning on failure:
(1) `extract_names(prose)` empty → `passed=False`, reason
`"anti-vacuity: zero names extracted from the prose"`, no `offending_words`;
(2) any extracted run not in `authorised_names` whose words are not all in
`_authorised_words` → `passed=False`, `offending_words=tuple(sorted(...))`;
(3) `not fact_sheet.steps` → `passed=False`, no `offending_words`;
(4) `_missing_band_markers` non-empty → `passed=False`, no `offending_words`.
Otherwise `passed=True, reason="ok"`.
Consequence: only failure (2) carries words a repair can act on. The lot keeps
all four checks unchanged (J1'a).

#### R-25 — acceptance arrows must exist
Opened: `tooling/verify/checks/pipeline_state.py:42`, `106-114`
Finding [M]: for a ticket whose status is in `{"brief", "exec", "verify",
"live-gate", "done"}`, every Machine-checkable arrow must resolve to an
existing file under `tooling/verify/checks/`.
Consequence: A creates both new checks.

#### R-26 — budgets
Opened: measured by AST on the touched modules; `tooling/verify/checks/module_budget.py:1-14`
Finding [M]: caps are 1000 lines / 40 top-level functions per `src/` module,
80 lines per function. Today: `day_narration.py` 223 lines / 6 functions;
`day_narration_guard.py` 245 / 6; `day_resolve.py` 452 / 10 (`freeze_facts`
63); `cockpit/routes/day.py` 967 / 30 (`resolve_day` 76, not touched).
Consequence: the route must not grow; B shrinks `_narrate_and_judge`.

#### R-28 — decision records
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:16324` (0092-e entry),
`tooling/glue/gen_decisions_index.py:1-14`
Finding [M]: headers read `## <TITLE> (TICKET-NNNN) -- <SUBTITLE> (BRIEF-NNNN-x,
no schema change)`; `DECISIONS_INDEX.md` is regenerated by
`python tooling/glue/gen_decisions_index.py`.
Consequence: one entry per brief, index regenerated in each.

#### R-32 — TICKET-0092 front matter
Opened: `tooling/tickets/TICKET-0092-names.md:1-14`; `/mnt/project/TEMPLATE.md`
(status enum)
Finding [M]: `status: live-gate` (line 5), `current_brief: E` (line 12). The
template's enum includes `done`; `current_brief` is "letter in flight, or
empty". Nia reports 0092 passed its live gate (2026-09-24).
Consequence: A sets `status: done` and empties `current_brief`. No other line
of that file changes; `pipeline_state.py` accepts `done` (R-25: its arrows all
exist already).

## Contracts

#### C-05 — `_named_refs`
Produced by: BRIEF-0093-A   Consumed by: `freeze_facts`, checks
Signature: `def _named_refs(concordance: ConcordanceResult, db: Session) ->
tuple[tuple[NamedRef, ...], tuple[NamedRef, ...]]` in
`src/world_engine/day_resolve.py`, immediately above `freeze_facts`.
Return shape: `(npcs, locations)`. Iterates `concordance.matched` then
`concordance.cast`; for each item `entity = db.get(Entity, item.entity_id)`;
skip if `None`; `ref = NamedRef(entity_id=item.entity_id, name=entity.name)`;
`entity.type == "character"` → npcs, `entity.type == "location"` → locations,
any other type skipped; a ref already present is not added again. Order:
first occurrence.
Error and empty cases: empty concordance → `((), ())`. Never raises.

## Context

Day narrations almost never pass the judge today (1 in 20, R-29). This lot
fixes the causes in three briefs. This one fixes the smallest: an NPC the
cast verdict chose is never named on the fact sheet, so the judge rejects
his name (J3a). It also creates the two new checks now, because every
acceptance arrow must exist from `exec` on (R-25); B and C add cases to
`day_narration_beats.py`.

## Scope IN

1. In `src/world_engine/day_resolve.py`, immediately above `freeze_facts`,
   add exactly:

   ```python
   def _named_refs(
       concordance: ConcordanceResult, db: Session,
   ) -> tuple[tuple[NamedRef, ...], tuple[NamedRef, ...]]:
       """Named persons and places for the fact sheet: every `matched` AND
       every `cast` mention whose entity exists (TICKET-0093, J3a). A cast
       NPC is a real entity the concordance chose; leaving it out made the
       judge reject its name as unauthorised."""
       npcs: list[NamedRef] = []
       locations: list[NamedRef] = []
       for item in (*concordance.matched, *concordance.cast):
           entity = db.get(Entity, item.entity_id)
           if entity is None:
               continue
           ref = NamedRef(entity_id=item.entity_id, name=entity.name)
           if entity.type == "character" and ref not in npcs:
               npcs.append(ref)
           elif entity.type == "location" and ref not in locations:
               locations.append(ref)
       return tuple(npcs), tuple(locations)
   ```

2. In `freeze_facts`, replace the eleven lines from
   `npcs: list[NamedRef] = []` through the `elif entity.type == "location"
   ...: locations.append(ref)` block by the single line
   `npcs, locations = _named_refs(concordance, db)`. Leave every later line of
   the function unchanged (`tuple(npcs)` / `tuple(locations)` accept tuples).

3. Replace `freeze_facts`' docstring with exactly:

   ```
   """Build the frozen fact sheet (Scope IN item 2). `concordance` is the
   trace `/plan` stored in `day_rewrite`, read back by the caller through
   `day_rewrite.load_latest` (`_read_day_rewrite_concordance`,
   BRIEF-0081-b) — never a fresh `concord()` run. Persons and places come
   from `_named_refs`: matched and cast mentions alike (TICKET-0093, J3a)."""
   ```

4. Create `tooling/verify/checks/day_fact_sheet_refs.py`: a G1 check with a
   module docstring naming TICKET-0093 / BRIEF-0093-A and the rule "C-05:
   `_named_refs` names matched and cast entities, characters as npcs,
   locations as locations, skips other types and missing rows, never
   duplicates". Copy `_fresh_engine` and `_world` verbatim from
   `checks/identity_tokens.py:108-134` (R-22). Use the
   `FAILURES`/`fail()` idiom and a vacuity guard (zero executed cases is a
   FAILURE). Cases, one per row of the lot's table (b5):
   - world with entities: `Aldric` (`character`), `Taverne` (`location`),
     `Marin` (`character`), `Guilde` (`faction`);
   - `ConcordanceResult(matched=(Aldric, Taverne, Guilde, entity_id="nope"),
     cast=(Marin, Aldric), ambiguous=(), unmatched=(), skipped_rungs=())`,
     building `MatchedMention(mention=Mention(category="person",
     surface_form=<name>, kind="named"), entity_id=..., rung="named_exact")`
     and `CastMention(mention=Mention(category="person",
     surface_form=<text>, kind="inferred", role_hint=<text>),
     entity_id=..., rung="cast", basis="stable", candidate_ids=())`;
   - assert `npcs == (NamedRef(Aldric), NamedRef(Marin))` in that order and
     `locations == (NamedRef(Taverne),)`;
   - assert an all-empty `ConcordanceResult` gives `((), ())`.
   Print one `PASS: day_fact_sheet_refs — ...` line on success; exit 1 with
   one `FAIL:` line per failure otherwise.

5. Create `tooling/verify/checks/day_narration_beats.py`: a G1 check, no DB,
   no model, with a module docstring naming TICKET-0093 and stating that
   BRIEF-0093-A creates it with judge baseline cases, BRIEF-0093-B adds the
   code-repair cases, BRIEF-0093-C adds the beat-assembly and band-label
   cases. Bootstrap `src` on `sys.path` as `checks/day_name_extraction.py`
   does (R-23). Build `FactSheet`/`StepFact`/`NamedRef` directly (R-21).
   `FAILURES`/`fail()` idiom, one list `EXECUTED` of case names, vacuity
   guard (zero executed cases is a FAILURE), one `PASS:` line. Baseline cases
   (fact sheet: `character_name="Mini"`, one `success` step, `npcs=()`,
   `authorised_names={"Mini"}` unless stated):
   - `A1`: `judge_narration("[RÉUSSITE] Malheureusement, Mini attend la Reine.", fs)`
     → `passed is False` and `offending_words == ("Malheureusement", "Reine")`;
   - `A2`: with `npcs=(NamedRef("x", "Lorian"),)` and
     `authorised_names={"Mini", "Lorian"}`,
     `judge_narration("[RÉUSSITE] Mini attend Lorian.", fs)` → `passed is True`;
   - `A3`: `judge_narration("[réussite] mini attend.", fs)` → `passed is False`
     and `reason == "anti-vacuity: zero names extracted from the prose"`
     (J1'a: the guard stays).
   Structure the file so later briefs add cases as new functions called from
   `main()`.

6. Close TICKET-0092 (R-32), in its own commit before any other item:
   in `tooling/tickets/TICKET-0092-names.md`, `status: live-gate` becomes
   `status: done` and `current_brief: E` becomes `current_brief:`. Change
   nothing else in that file. Commit message:
   `chore(tickets): close TICKET-0092 — live gate passed (Nia, 2026-09-24)`.

7. Append to `tooling/standards/ARCHITECTURE_DECISIONS.md` an entry headed
   `## CAST NPCS ARE NAMED ON THE FACT SHEET (TICKET-0093) -- THE JUDGE STOPS REJECTING CHOSEN NPCS (BRIEF-0093-A, no schema change)`,
   stating: the measured defect (R-20), J3a, `_named_refs`' rule (C-05), the
   corrected docstring, and that both new checks are created here so every
   arrow resolves (R-25). Then run `python tooling/glue/gen_decisions_index.py`.

## Scope OUT

- Anything in `day_narration.py`, `day_narration_guard.py`,
  `cockpit/routes/day.py`, `prompt_registry.py`, `seed_pilot.py`: B and C.
- Role hints for cast mentions: unchanged (they were never in `role_hints`).
- `day_concordance.py` and the cast rule itself (`CAST_PRECEDENCE`): untouched.
- The four stuck `resolving` days: no data touched.
- Any other edit to `TICKET-0092-names.md` (its acceptance boxes, amendment log).
- H2 (0094), K1 (0095).

## Invariants to defend

- "History is sacred": no stored row is touched; the change affects only
  fact sheets built from now on.
- Secrets are structurally excluded: a cast entity is already a player-facing
  choice of the concordance (it is written to `day_mention_resolution` and
  shown in the plan); naming it adds no knowledge the player lacks. If the
  executor finds a cast path that selects an entity the character cannot
  perceive, that is a STOP.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `freeze_facts` reads `concordance.cast` somewhere already;
- a check other than the two new ones fails after the change.

ADAPT:
- `Entity` or `Session` is imported under another name in `day_resolve.py`:
  use that name, report.
- `create_db_and_tables` needs an extra environment variable in the check:
  set it in the check exactly as `checks/identity_tokens.py` does, report.

REPORT-ONLY:
- any other stale docstring noticed in `day_resolve.py`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_fact_sheet_refs.py` prints `PASS:` and exits 0.
- [ ] `python tooling/verify/checks/day_narration_beats.py` prints `PASS:`
      with cases A1, A2, A3 executed, exits 0.
- [ ] Mutation: reverting `_named_refs` to iterate `concordance.matched` only
      makes `day_fact_sheet_refs.py` fail (run it, then restore).
- [ ] `grep -n "_named_refs(concordance, db)" src/world_engine/day_resolve.py`
      returns exactly one line, inside `freeze_facts`.
- [ ] `grep -n "^status:\|^current_brief:" tooling/tickets/TICKET-0092-names.md`
      prints `status: done` and `current_brief:`, in a commit of its own.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry + regenerated `DECISIONS_INDEX.md`
  (Scope IN 7). No schema changelog, no CLAUDE.md.
