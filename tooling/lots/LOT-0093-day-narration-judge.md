# LOT — TICKET-0093 "Day narration: a judge that can pass"

## Objective and cut

A diagnostic run on 2026-09-25 against the production DB (read-only) and a copy
of it measured the day narration chain on current `main` (204ed7c): **1 fresh
narration in 20 passes the judge**, and none of the rejections is a name the
model actually invented (R-29). The causes are in our own chain:

- the model repair pass lower-cases the whole prose, markers included, which
  the zero-names guard then rightly rejects;
- capitals the fact sheet itself carries (objectives, role hints) and
  sentence-initial words are flagged as unauthorised names;
- the model writes band markers unreliably (wrong band on the first step,
  missing accents, whole paragraphs in brackets, which `_MARKER_RE` erases).

This lot makes the chain able to pass without weakening what the judge
proves:

- **A** — NPCs chosen by the cast verdict become nameable on the fact sheet
  (J3a), and the two new checks are created.
- **B** — the repair becomes code: the offending words are lower-cased by a
  pure function, the model repair pass is retired (J2'a, J4'a).
- **C** — the model returns one text per step as JSON and the code writes the
  band markers itself (J5b). A new narration prompt version ships through an
  apply script.

The zero-names guard is kept exactly as it is (J1'a).

**Where the lot stops.** No schema change. The rewrite pass
(`day_narration.rewrite`, which cannot fire) and its prompt are untouched.
The four historical days stuck in `resolving` without a `day_rewrite` stay as
they are (Nia, 2026-09-25). H2 and K1 move to 0094 and 0095.

## Briefs in this lot

- **A** `named-refs-and-checks` — `day_resolve._named_refs` (matched + cast),
  `freeze_facts` uses it, stale docstring corrected; creates
  `checks/day_fact_sheet_refs.py` and `checks/day_narration_beats.py`.
- **B** `code-repair` — `day_narration_guard.lowercase_offending_words`, the
  route calls it in place of the model `repair`; `repair`, its registry entry,
  its seed head and constants are retired; three checks amended.
- **C** `narration-beats` — `day_narration.assemble_beats` and
  `BAND_LABELS_FR`; `narrate` asks for JSON and returns assembled prose;
  `_render_fact_sheet` no longer shows markers; new prompt text in
  `seed_pilot.py`; `scripts/apply_ticket_0093_narration_prompt.py`.

## Dependency graph

- **A first.** Not because B or C consume its code, but because every
  acceptance arrow must resolve to an existing check file once the ticket is
  in `exec` (R-25), and A creates both new checks.
- **B before C, strictly.** Both edit `day_narration.py`,
  `checks/day_narration.py` and `scripts/seed_pilot.py`; C's check cases
  extend the file B's cases live in.
- No other ordering constraint.

## RECON

Every finding below was taken on a fresh tarball of `main` in this session.
`[M]` = measured by opening the file named; `[X]` = measured by the
diagnostic Claude Code ran on prod data (R-29).

### R-01 — `judge_narration` (order of checks)
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

### R-02 — `_TOKEN_RE`, `_MARKER_RE`, `_sentences`
Opened: `src/world_engine/day_narration_guard.py:69-70`, `113-144`
Finding [M]: `_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ'-]+|[.!?]+")`;
`_MARKER_RE = re.compile(r"\[[^\[\]]*\]")` — it matches ANY bracketed span,
not only the four markers. `_sentences` substitutes every `_MARKER_RE` match
with a space before tokenizing.
Consequence: a paragraph the model wraps in brackets vanishes before name
extraction (R-29 cause 3). C removes bracket characters from model text before
assembly, so the only bracketed spans left are the code-written markers.
`lowercase_offending_words` (C-01) reuses both regexes rather than defining new
ones.

### R-03 — `_authorised_words` and the containment loop
Opened: `src/world_engine/day_narration_guard.py:192-201`, `216-233`
Finding [M]: `_authorised_words` is every whitespace-split word of every
`authorised_names` entry. A run passes if it is itself in `authorised_names`
or every one of its words is in `_authorised_words`; otherwise each of its
words NOT in `_authorised_words` is added to `unauthorised`.
Consequence: an offending word is never a word of an authorised name, so
lower-casing every occurrence of it (C-01) cannot damage an authorised name.

### R-04 — `JudgeVerdict`
Opened: `src/world_engine/day_narration_guard.py:103-110`
Finding [M]: frozen dataclass `passed: bool`, `reason: str`,
`offending_words: tuple[str, ...] = ()`.
Consequence: unchanged by the lot; the route keeps reading `offending_words`
structurally (check R21).

### R-05 — import direction between the two narration modules
Opened: `src/world_engine/day_narration_guard.py:59-66`,
`src/world_engine/day_narration.py:39-51`
Finding [M]: the guard imports `BAND_MARKERS` from `day_narration` and
`FactSheet` from `day_resolve`; `day_narration` imports from `day_resolve`,
`llm_parse`, `ollama_client`, `models`, `prompt_registry`, `prompt_store`, and
nothing from the guard.
Consequence: C-01 lives in the guard; C-02 and C-04 live in `day_narration`.
`day_narration` must not import the guard (cycle).

### R-06 — `day_narration.py` module constants
Opened: `src/world_engine/day_narration.py:53-69`
Finding [M]: `MAX_REWRITE_ATTEMPTS = 1` (57), `MAX_REPAIR_ATTEMPTS = 1` (61),
`BAND_MARKERS` (66-69) = `{"success": "[RÉUSSITE]", "partial": "[PARTIEL]",
"failure": "[ÉCHEC]", BLOCKED_BAND: "[BLOQUÉ]"}`.
Consequence: `MAX_REPAIR_ATTEMPTS` stays (one code repair, then the verdict is
final; check R19 keeps pinning it). `BAND_MARKERS` stays the single source of
the markers.

### R-07 — `_render_fact_sheet`
Opened: `src/world_engine/day_narration.py:95-114`; callers at 129, 154, 183
Finding [M]: renders `Jour N.`, `Personnage joueur : X.`, then per step
`- Étape « {objective} » — marqueur attendu {marker}{detail}.` (+ blocked
detail), then `Personnes nommables`, `Lieux nommables`, and the role-hint line.
Called by `narrate` (129), `rewrite` (154) and `repair` (183).
Consequence: C replaces the marker in the step line by a band label (C-04) and
numbers the steps; the model is never shown a marker. `rewrite` keeps calling
it (its prompt is out of scope).

### R-08 — `narrate`
Opened: `src/world_engine/day_narration.py:117-140`
Finding [M]: loads the `day_narration` template, builds `user_msg` from
`{declaration}` and `{fact_sheet}` + `"\n/no_think"`, calls
`ollama_client.chat(messages, model=effective_model(...), host=...)` with no
`format`, returns `raw.strip()`.
Consequence: C adds `format="json"` and returns `assemble_beats(raw,
fact_sheet)` (C-02, C-03). The body keeps no `select(` (check R3).

### R-09 — the model repair pass
Opened: `src/world_engine/day_narration.py:27-37` (module docstring),
`172-197` (`repair`)
Finding [M]: `repair(fact_sheet, prior_prose, offending_words, db)` loads the
`day_narration_repair` template, sends the fact sheet, the words and the prose,
returns `raw.strip()`. The docstring describes it as the only recovery path.
Consequence: B deletes `repair` and rewrites the docstring paragraph.

### R-10 — `_narrate_and_judge` (route)
Opened: `src/world_engine/cockpit/routes/day.py:40-44` (imports), `794-834`
Finding [M]: `narrate` inside `try/except LlmParseError` → `db.rollback()` +
502 (805-808); `judge_narration`; return if passed; `detect_late_delta` →
optional `rewrite_narration` + re-judge; then `if not verdict.passed and
verdict.offending_words:` → `repair(...)` inside `try/except LlmParseError` →
502 (826-831), re-judge; `return fact_sheet, prose, verdict` (834). Import line
43: `from ...day_narration import detect_late_delta, narrate, repair, rewrite
as rewrite_narration`.
Consequence: B replaces the `repair` try block by one call to C-01 under the
same `if`, and drops `repair` from the import. C changes nothing in the route:
an `assemble_beats` failure is an `LlmParseError` raised inside `narrate`, which
the existing 502 branch already covers.

### R-11 — failure surface
Opened: `src/world_engine/cockpit/routes/day.py:837-889`
Finding [M]: a failed verdict appends one `history` entry (fact sheet, prose,
verdict) and raises 422 with `reason`, `offending_words`, `prose`;
`pass_play.status` stays `resolving`.
Consequence: unchanged. The stored prose is the post-repair prose.

### R-12 — `checks/day_narration.py`
Opened: `tooling/verify/checks/day_narration.py:1-118` (docstring R1-R22),
`248-278` (R5), `439-470` (`_REGISTRY_WIRING_EXPECTED`, R9/R20),
`755-806` (`check_bounded_repair`, R19), `809-850` (R21), `853-880` (R22),
`883-915` (`main`, PASS message)
Finding [M]: R5 requires an explicit zero-names and zero-steps guard in
`judge_narration`. `_REGISTRY_WIRING_EXPECTED` maps `day_narration→narrate`,
`day_rewrite→rewrite`, `day_narration_repair→repair`. R19 requires
`MAX_REPAIR_ATTEMPTS == 1` and exactly one call named `repair` in
`_narrate_and_judge`, behind an `if`. R22 forbids five phrases in
`DAY_NARRATION_SYSTEM_PROMPT`.
Consequence: R5 unchanged (J1'a). B rewrites R19 and R20; C extends R22 and
adds R23.

### R-13 — `checks/day_prompt_delivery.py`
Opened: `tooling/verify/checks/day_prompt_delivery.py:1-50` (docstring),
`56-76` (`DAY_CONSTANTS`, `EXPECTED_HEAD_IDS`), `182-183` (literal 10),
`487-493` (PASS message)
Finding [M]: 18 constants including `DAY_NARRATION_REPAIR_SYSTEM_PROMPT` and
`DAY_NARRATION_REPAIR_USER_TEMPLATE`; 10 head ids including
`pt-day-narration-repair`; R2 compares `len(heads_node.elts) != 10`. The
docstring calls the counts "deliberately literal and deliberately brittle".
Consequence: B lowers them to 16 and 9 in every place they appear.

### R-14 — `checks/prompt_registry.py`
Opened: `tooling/verify/checks/prompt_registry.py:1-15`, `74-79`, `115-140`
Finding [M]: rule 1 is a bijection between `PROMPT_REGISTRY` keys and every
`usage = "..."` match of `USAGE_LINE = re.compile(r'usage\s*=\s*"([a-z_]+)"')`
over the whole text of `scripts/seed_pilot.py` (comments included). Rule 2
requires every `call_sites` entry to resolve to an existing `def`.
Consequence: retiring the repair usage means removing it from the registry and
removing every `usage="day_narration_repair"` match from `seed_pilot.py` in the
same commit.

### R-15 — `PROMPT_REGISTRY` entries
Opened: `src/world_engine/prompt_registry.py:55-61` (`PromptSpec`), `317-337`
Finding [M]: `day_narration` → `call_sites=("src/world_engine/day_narration.py:narrate",)`;
`day_narration_repair` → `call_sites=("src/world_engine/day_narration.py:repair",)`,
lines 331-337.
Consequence: B deletes lines 331-337.

### R-16 — `scripts/seed_pilot.py` narration and repair text
Opened: `scripts/seed_pilot.py:1927-1975`, `2012-2044`, `2203-2231`
Finding [M]: comment block 1927-1940 (says the fact sheet carries "per-step
band markers"); `DAY_NARRATION_SYSTEM_PROMPT` 1941-1968 and
`DAY_NARRATION_USER_TEMPLATE` 1970-1975; repair comment 2012-2018 and the two
repair constants 2019-2044; heads `pt-day-narration` (2203-2212, variables
`["declaration", "fact_sheet"]`) and `pt-day-narration-repair` (2223-2231,
the only `usage="day_narration_repair"` line, 2226).
Consequence: B deletes 2012-2044 and the 2223-2231 head. C replaces the two
narration constants and the 1927-1940 comment. Variables are unchanged.

### R-17 — `prompt_coverage.DAY_CHAIN_USAGES`
Opened: `src/world_engine/prompt_coverage.py:1-20`, `43-50`
Finding [M]: derived from `PROMPT_REGISTRY` (every usage whose call site is a
`src/world_engine/day_*.py` module, minus `DEGRADING_USAGES`), never a literal
list.
Consequence: once the registry entry is gone, `declare_day` no longer requires
a `day_narration_repair` template. Nothing to edit here.

### R-18 — the prompts CRUD
Opened: `src/world_engine/cockpit/crud/prompts.py:119-145`, `148-160`
Finding [M]: the list iterates `PROMPT_REGISTRY` only; the detail route
returns 500 for a row whose usage has no registry entry.
Consequence: after B the prod head `pt-day-narration-repair` (a DB row, never
deleted — history is sacred) is no longer listed in « Prompts »; only a direct
request by its id would reach the 500. Accepted: nothing links to it.

### R-19 — JSON parsing and the chat call
Opened: `src/world_engine/llm_parse.py:21-22` (`LlmParseError(ValueError)`),
`44-60` (`extract_object`); `src/world_engine/ollama_client.py:88-100`
(`chat(..., format: str | dict | None = None, options=None)`);
`src/world_engine/day_extract.py:117-127` (precedent)
Finding [M]: `extract_object` strips fences, takes the first balanced `{...}`,
raises `LlmParseError` if absent, invalid, or not an object. `day_extract`
calls `chat(..., format="json")` then `llm_parse.extract_object(raw)`.
Consequence: C-02 uses `extract_object` and raises `llm_parse.LlmParseError`;
C-03 passes `format="json"`.

### R-20 — `freeze_facts` and the stored concordance
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

### R-21 — concordance result shapes
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

### R-22 — fixture idiom for a DB-backed check
Opened: `tooling/verify/checks/identity_tokens.py:108-134`;
`src/world_engine/models/canon.py:117-127`
Finding [M]: `_fresh_engine()` points `WORLD_ENGINE_DATABASE_URL` at a temp
SQLite file, purges `world_engine*` from `sys.modules`, calls
`create_db_and_tables()`. `_world(session, label)` adds
`World(name=label, is_active=False)` and returns an `entity(kind, name)` helper
creating `Entity(world_id, type, name)`. `Entity` requires `world_id`, `type`,
`name`.
Consequence: `day_fact_sheet_refs.py` copies both helpers verbatim.

### R-23 — `checks/day_name_extraction.py`
Opened: `tooling/verify/checks/day_name_extraction.py:1-40`
Finding [M]: golden exact-set cases over `extract_names`, no DB, vacuity-
guarded, fails loudly on import error.
Consequence: unchanged; it is the gate that keeps the extractor honest while
R5 keeps the runtime zero-names guard (J1'a).

### R-24 — apply-script precedent
Opened: `scripts/apply_ticket_0078_narration_seed.py` (whole file)
Finding [M]: refuses to run unless `WORLD_ENGINE_ENV` is `prod` or `test`;
imports the constants from `seed_pilot` (embeds no text); loads head
`pt-day-narration`; exits 1 if missing; prints "unchanged" if the current
version matches; otherwise `write_prompt_version(session, template_id=...,
system_prompt=..., user_template=..., note=...)`, commits, prints
`vN -> vM`. Idempotent.
Consequence: C's script is this file with the note and names changed.

### R-25 — acceptance arrows must exist
Opened: `tooling/verify/checks/pipeline_state.py:42`, `106-114`
Finding [M]: for a ticket whose status is in `{"brief", "exec", "verify",
"live-gate", "done"}`, every Machine-checkable arrow must resolve to an
existing file under `tooling/verify/checks/`.
Consequence: A creates both new checks.

### R-26 — budgets
Opened: measured by AST on the touched modules; `tooling/verify/checks/module_budget.py:1-14`
Finding [M]: caps are 1000 lines / 40 top-level functions per `src/` module,
80 lines per function. Today: `day_narration.py` 223 lines / 6 functions;
`day_narration_guard.py` 245 / 6; `day_resolve.py` 452 / 10 (`freeze_facts`
63); `cockpit/routes/day.py` 967 / 30 (`resolve_day` 76, not touched).
Consequence: the route must not grow; B shrinks `_narrate_and_judge`.

### R-27 — CLAUDE.md
Opened: `CLAUDE.md` (grep for judge, narrat, marker, repair)
Finding [M]: no invariant names the repair pass or the markers; the file map
(441-442) says `day_narration.py # day narration + rewrite: renders the fact
sheet, never decides` and `day_narration_guard.py # T1 judge: name
containment + outcome survival, Python-only`. 35,790 characters.
Consequence: no CLAUDE.md edit; both lines stay true.

### R-28 — decision records
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:16324` (0092-e entry),
`tooling/glue/gen_decisions_index.py:1-14`
Finding [M]: headers read `## <TITLE> (TICKET-NNNN) -- <SUBTITLE> (BRIEF-NNNN-x,
no schema change)`; `DECISIONS_INDEX.md` is regenerated by
`python tooling/glue/gen_decisions_index.py`.
Consequence: one entry per brief, index regenerated in each.

### R-29 — measured behaviour on prod data (diagnostic, 2026-09-25)
Opened: Claude Code report, current judge replayed read-only on 34 stored
attempts, plus 20 fresh narrations on a DB copy with the template's model
(`richardyoung/qwen2.5-14b-instruct-abliterated`)
Finding [X]: stored: 22 zero-names, 5 band-marker, 3 unauthorised, 4 ok. In
all 22 zero-names cases the character name is present but the whole prose is
lower-cased, markers included (consistent with the repair pass; not provable
per attempt). Fresh: 1/20 pass. Rejected words: sentence-initial
(`Malheureusement`, `Heureusement`, `Arrivée`, `Ayant`, `Tenant`, `Personne`,
`Face`) and fact-sheet capitals (`Serviteurs`, `Dirigeants` from objectives,
`Reine` from a role hint). Bracketed paragraphs erased by `_MARKER_RE`. Marker
defects: first step rendered `[RÉUSSITE]` whatever its band (4/5), `[Echec]`,
`[ECHEC]`, `[Bloqué]`.
Consequence: the three briefs; the live gate measures against 1/20.

### R-30 — enumeration: every reference to the model repair
Opened: `grep -rn "day_narration_repair\|MAX_REPAIR_ATTEMPTS\|\brepair\b"
--include=*.py src tooling scripts` and `grep -rln DAY_NARRATION_REPAIR`
Finding [M]: pasted in Gate output (c1).
Consequence: B's scope list is exactly that enumeration minus unrelated uses of
the word "repair".

### R-31 — enumeration: consumers of the markers
Opened: `grep -rn "RÉUSSITE\|offending_words\|BLOQUÉ" frontend/src` and
`grep -rn "RÉUSSITE\|BAND_MARKERS" --include=*.py src | grep -v day_narration`
Finding [M]: pasted in Gate output (c2): no consumer outside the two narration
modules and their checks.
Consequence: no frontend change; `frontend_build_fresh` is untouched.

### R-32 — TICKET-0092 front matter
Opened: `tooling/tickets/TICKET-0092-names.md:1-14`; `/mnt/project/TEMPLATE.md`
(status enum)
Finding [M]: `status: live-gate` (line 5), `current_brief: E` (line 12). The
template's enum includes `done`; `current_brief` is "letter in flight, or
empty". Nia reports 0092 passed its live gate (2026-09-24).
Consequence: A sets `status: done` and empties `current_brief`. No other line
of that file changes; `pipeline_state.py` accepts `done` (R-25: its arrows all
exist already).

## Contract sheet

No family: the five contracts are independent.

### C-01 — `lowercase_offending_words`
Produced by: BRIEF-0093-B   Consumed by: BRIEF-0093-B (route), checks
Signature: `def lowercase_offending_words(prose: str, words: tuple[str, ...]) -> str`
in `src/world_engine/day_narration_guard.py`. Pure: no `db`, no `chat(`.
Return shape: `prose` with every `_TOKEN_RE` word token that is exactly equal
(case-sensitive) to a member of `words` replaced by `token.lower()`, **outside**
`_MARKER_RE` spans. Marker spans, every other character, spacing and
punctuation are byte-identical.
Error and empty cases: `words == ()` → returns `prose` unchanged. A member of
`words` occurring only inside a longer token (`Reine` in `Reines`) is not
touched. Never raises.

### C-02 — `assemble_beats`
Produced by: BRIEF-0093-C   Consumed by: `narrate` (C-03), checks
Signature: `def assemble_beats(raw: str, fact_sheet: FactSheet) -> str` in
`src/world_engine/day_narration.py`. Pure: no `db`, no `chat(`.
Return shape: checks run in this order — (1) `fact_sheet.steps` empty;
(2) `obj = llm_parse.extract_object(raw)`; (3) `beats = obj.get("etapes")` is
a list; (4) its length; (5) each beat, in order.
For each `(step, beat)` in order: `text = beat.replace("[", "").replace("]",
"").strip()`; the result is `"\n\n".join(f"{BAND_MARKERS[step.band]} {text}")`.
Error and empty cases (each raises `llm_parse.LlmParseError` with the message
given): `fact_sheet.steps` empty → `"day_narration: fact sheet has no steps"`;
`beats` not a list → `"day_narration: 'etapes' is not a list"`;
`len(beats) != len(fact_sheet.steps)` → `"day_narration: expected N texts,
got M"` (N, M filled); a beat not a `str`, or empty after bracket removal and
strip → `"day_narration: text for step K is empty or not a string"` (K
1-based). `extract_object`'s own errors propagate unchanged.

### C-03 — `narrate` (amended)
Produced by: BRIEF-0093-C   Consumed by: `cockpit/routes/day.py::_narrate_and_judge` (unchanged call)
Signature: unchanged, `def narrate(fact_sheet: FactSheet, declaration: str, db: Session) -> str`.
Return shape: `assemble_beats(raw, fact_sheet)`, where `raw` is the result of
the existing `ollama_client.chat(...)` call with `format="json"` added.
Error and empty cases: missing template → `LlmParseError` (unchanged); any
C-02 error propagates → the route's existing 502.

### C-04 — `BAND_LABELS_FR`
Produced by: BRIEF-0093-C   Consumed by: `_render_fact_sheet`, checks
Signature: module-level `BAND_LABELS_FR: dict[str, str]` in
`src/world_engine/day_narration.py`, immediately after `BAND_MARKERS`.
Return shape: exactly `{"success": "réussite", "partial": "réussite partielle",
"failure": "échec", BLOCKED_BAND: "bloquée"}` — key set equal to
`BAND_MARKERS`'.
Error and empty cases: none (a missing band is a `KeyError`, as with
`BAND_MARKERS` today).

### C-05 — `_named_refs`
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

## Gate output

### (a) Property trace

| Property asserted by the lot | Finding | Declaring file opened |
|---|---|---|
| Judge order and which failure carries `offending_words` | R-01 | `day_narration_guard.py` |
| `_MARKER_RE` matches any bracketed span | R-02 | `day_narration_guard.py` |
| An offending word is never a word of an authorised name | R-03 | `day_narration_guard.py` |
| `JudgeVerdict` fields | R-04 | `day_narration_guard.py` |
| Guard imports `day_narration`, not the reverse | R-05 | both modules |
| `MAX_REPAIR_ATTEMPTS == 1`, `BAND_MARKERS` values | R-06 | `day_narration.py` |
| `_render_fact_sheet` shows markers; three callers | R-07 | `day_narration.py` |
| `narrate` calls chat without `format` | R-08 | `day_narration.py` |
| `repair` is the model pass on `day_narration_repair` | R-09 | `day_narration.py` |
| Route: repair under `if not verdict.passed and verdict.offending_words`; `LlmParseError` in `narrate` → 502 | R-10 | `cockpit/routes/day.py` |
| Failed verdict → history entry + 422, status stays | R-11 | `cockpit/routes/day.py` |
| R5, R9, R19, R20, R21, R22 content | R-12 | `checks/day_narration.py` |
| 18 constants, 10 heads, literal 10 | R-13 | `checks/day_prompt_delivery.py` |
| Registry/seed bijection via `USAGE_LINE`; call sites must resolve | R-14 | `checks/prompt_registry.py` |
| Registry entry lines for repair | R-15 | `prompt_registry.py` |
| Seed lines for narration and repair | R-16 | `scripts/seed_pilot.py` |
| `DAY_CHAIN_USAGES` derived from registry | R-17 | `prompt_coverage.py` |
| Prompts list iterates registry; detail 500 on unregistered | R-18 | `cockpit/crud/prompts.py` |
| `extract_object` behaviour; `chat` accepts `format` | R-19 | `llm_parse.py`, `ollama_client.py` |
| `freeze_facts` loops matched only; route passes stored trace | R-20 | `day_resolve.py`, `cockpit/routes/day.py` |
| Dataclass field sets | R-21 | `day_concordance.py`, `day_extract.py`, `day_resolve.py` |
| Fixture helpers; `Entity` required fields | R-22 | `checks/identity_tokens.py`, `models/canon.py` |
| Extractor golden gate exists | R-23 | `checks/day_name_extraction.py` |
| Apply-script shape | R-24 | `scripts/apply_ticket_0078_narration_seed.py` |
| Every arrow must exist from `brief` on | R-25 | `checks/pipeline_state.py` |
| Budgets and current sizes | R-26 | `checks/module_budget.py` + AST measurement |
| No CLAUDE.md invariant on repair/markers | R-27 | `CLAUDE.md` |
| TICKET-0092 status and `current_brief` lines | R-32 | `tooling/tickets/TICKET-0092-names.md` |
| Decision header format; index generator | R-28 | `ARCHITECTURE_DECISIONS.md`, `gen_decisions_index.py` |
| Rejection causes on prod data | R-29 | diagnostic report (external measurement) |

Presuppositions: no brief says "follow the existing convention" without naming
the file; every "copy" names its source (R-22, R-24).

### (b) Case tables

**(b1) `_narrate_and_judge` after B** (late delta never fires today, R-09
docstring; its row is unchanged):

| first verdict | `offending_words` | path | final verdict |
|---|---|---|---|
| passed | — | return | passed |
| failed, zero names | `()` | no repair | failed (422) |
| failed, zero steps | `()` | no repair | failed (422) |
| failed, band markers | `()` | no repair | failed (422) — unreachable after C, markers are code-written |
| failed, unauthorised | non-empty | `lowercase_offending_words`, re-judge | passed, or failed on a later check |

After C-01 on an unauthorised failure the re-judge cannot fail on those same
words (they are now lower-case, so not extracted); it can fail on zero names
only if every extracted run was offending — then the prose names no authorised
name, and R5 rejects it, as it should.

**(b2) C-01 input classes:**

| input | output |
|---|---|
| word outside markers, exact match | lower-cased |
| same word several times | every occurrence lower-cased |
| word inside a marker span (`[RÉUSSITE]` with `RÉUSSITE` in words) | untouched |
| word as part of a longer token (`Reines`) | untouched |
| word at sentence start | lower-cased (J4'a: accepted cosmetic cost) |
| `words == ()` | prose unchanged |

**(b3) C-02 input classes:**

| input | outcome |
|---|---|
| no JSON object | `LlmParseError` (from `extract_object`) |
| object without `etapes`, or `etapes` not a list | `LlmParseError` "'etapes' is not a list" |
| list length ≠ steps | `LlmParseError` "expected N texts, got M" |
| a text not `str`, or empty after bracket removal | `LlmParseError` "text for step K ..." |
| a text containing `[`/`]` | brackets removed, text kept |
| zero steps | `LlmParseError` "fact sheet has no steps" |
| valid | one marker per step, in step order, bands from the fact sheet |

**(b4) C-04:** key set == `BAND_MARKERS` key set (four bands). Checked.

**(b5) C-05:**

| item | entity | result |
|---|---|---|
| matched | character | npcs |
| matched | location | locations |
| cast | character | npcs |
| matched or cast | faction / other type | skipped |
| matched or cast | missing row | skipped |
| same entity in matched and cast | character | once |

### (c) Enumerations

**(c1)** R-30:

```
$ grep -rn "day_narration_repair\|MAX_REPAIR_ATTEMPTS\|\brepair\b" --include=*.py src tooling scripts | grep -v "^tooling/verify/checks/day_narration.py"
src/world_engine/writes/goals_agendas.py:489,496,502,506   (word "repair" in an unrelated docstring, Z4)
src/world_engine/prompt_registry.py:331:    "day_narration_repair": PromptSpec(
src/world_engine/prompt_registry.py:335:        call_sites=("src/world_engine/day_narration.py:repair",),
src/world_engine/day_narration_guard.py:108:    # BRIEF-0079-b) -- the exact words the bounded repair pass is fed.
src/world_engine/cockpit/day_reconcile_apply.py:53,108,110  (unrelated docstring)
src/world_engine/cockpit/routes/day.py:43:from ...day_narration import detect_late_delta, narrate, repair, rewrite as rewrite_narration
src/world_engine/cockpit/routes/day.py:798:    (Scope IN items 3-4) + the ONE conditional repair attempt (TICKET-0079,
src/world_engine/cockpit/routes/day.py:828:            prose = repair(fact_sheet, prose, verdict.offending_words, db)
src/world_engine/cockpit/routes/day.py:831:            raise HTTPException(status_code=502, detail=f"day narration repair failed: {exc}") from exc
src/world_engine/gathering.py:284,293,428,451               (unrelated, "B1 repair")
src/world_engine/day_narration.py:27,34,59,61,172,173,176,178,196
tooling/verify/checks/day_plan.py:85                        (unrelated, Z4)
tooling/verify/checks/day_prompt_delivery.py:7,74
$ grep -rln "DAY_NARRATION_REPAIR" scripts src tooling
scripts/seed_pilot.py
tooling/verify/checks/day_prompt_delivery.py
tooling/briefs/BRIEF-0079-b-bounded-repair-and-failure-surface.md   (history, not edited)
```

**(c2)** R-31:

```
$ grep -rn "RÉUSSITE\|offending_words\|BLOQUÉ" frontend/src
(no output)
$ grep -rn "RÉUSSITE\|BAND_MARKERS" --include=*.py src | grep -v "day_narration"
(no output)
```

**(c3)** "No CLAUDE.md invariant on repair or markers" (R-27):

```
$ grep -n -i "judge\|narrat\|marker\|abliterat" CLAUDE.md
293, 367, 373, 384, 385, 401, 435, 441, 442 — none is an invariant on the day
narration repair or on band markers (skill lexicon, model setup, MJ narration,
file map).
```

### (d) Contracts
No family in this lot. Each contract was written before the brief that
produces it. ✔

### (e) Gates and the modules that satisfy them

| Gate | Proposed / passed | Satisfied by | What it needs that it forbids |
|---|---|---|---|
| `day_fact_sheet_refs.py` (new) | proposed, A | `day_resolve._named_refs` (A) | a DB: satisfied by the R-22 temp-SQLite fixture, no prod access |
| `day_narration_beats.py` (new) | proposed, A; cases added in B, C | A: `judge_narration` (existing); B: `lowercase_offending_words`; C: `assemble_beats`, `BAND_LABELS_FR` | no model, no DB: every function it calls is pure (C-01, C-02, C-04); imports verified without `WORLD_ENGINE_ENV` |
| `day_narration.py` R19/R20 rewritten, R22 extended, R23 new | passed | B, C | nothing |
| `day_prompt_delivery.py` counts | passed | B's seed edit | nothing |
| `prompt_registry.py` bijection and call sites | passed | B removes registry entry and seed usage together | nothing |
| `day_name_extraction.py` | passed | unchanged extractor | nothing |
| `module_budget.py`, `function_length.py` | passed | R-26 margins | nothing |
| `import_cycle.py` | passed | R-05 direction respected | nothing |
| `decisions_index.py` | passed | regenerated per brief | nothing |
| `pipeline_state.py` | passed | A creates both new checks | nothing |

## Amendments

(none)
