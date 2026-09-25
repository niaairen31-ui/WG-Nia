# BRIEF 0093-B — "code repair, model repair retired"

Lot: LOT-0093-day-narration-judge.md (authoritative on conflict)
Depends on: A (the check file `day_narration_beats.py` exists)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/day_narration_guard.py:69-70` `_TOKEN_RE` and `_MARKER_RE`
  as quoted in R-02.
- `src/world_engine/day_narration_guard.py:204` `def judge_narration(`.
- `src/world_engine/day_narration.py:61` `MAX_REPAIR_ATTEMPTS = 1` and `:172`
  `def repair(`.
- `src/world_engine/cockpit/routes/day.py:43` the import line quoted in R-10,
  and `:826-832` the `repair(...)` try block.
- `src/world_engine/prompt_registry.py:331` `"day_narration_repair": PromptSpec(`.
- `scripts/seed_pilot.py:2012` `# day_narration_repair: TICKET-0079's bounded repair pass`
  and `:2224` `id="pt-day-narration-repair",`.
- `tooling/verify/checks/day_prompt_delivery.py:182` `if len(heads_node.elts) != 10:`.
- `tooling/verify/checks/day_narration.py:442`
  `"day_narration_repair": ("repair", "R20"),`.
- The enumeration (c1) of the lot header, re-run: no new consumer of `repair`,
  `day_narration_repair` or `DAY_NARRATION_REPAIR`.

## Facts carried

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

#### R-02 — `_TOKEN_RE`, `_MARKER_RE`, `_sentences`
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

#### R-03 — `_authorised_words` and the containment loop
Opened: `src/world_engine/day_narration_guard.py:192-201`, `216-233`
Finding [M]: `_authorised_words` is every whitespace-split word of every
`authorised_names` entry. A run passes if it is itself in `authorised_names`
or every one of its words is in `_authorised_words`; otherwise each of its
words NOT in `_authorised_words` is added to `unauthorised`.
Consequence: an offending word is never a word of an authorised name, so
lower-casing every occurrence of it (C-01) cannot damage an authorised name.

#### R-05 — import direction between the two narration modules
Opened: `src/world_engine/day_narration_guard.py:59-66`,
`src/world_engine/day_narration.py:39-51`
Finding [M]: the guard imports `BAND_MARKERS` from `day_narration` and
`FactSheet` from `day_resolve`; `day_narration` imports from `day_resolve`,
`llm_parse`, `ollama_client`, `models`, `prompt_registry`, `prompt_store`, and
nothing from the guard.
Consequence: C-01 lives in the guard; C-02 and C-04 live in `day_narration`.
`day_narration` must not import the guard (cycle).

#### R-06 — `day_narration.py` module constants
Opened: `src/world_engine/day_narration.py:53-69`
Finding [M]: `MAX_REWRITE_ATTEMPTS = 1` (57), `MAX_REPAIR_ATTEMPTS = 1` (61),
`BAND_MARKERS` (66-69) = `{"success": "[RÉUSSITE]", "partial": "[PARTIEL]",
"failure": "[ÉCHEC]", BLOCKED_BAND: "[BLOQUÉ]"}`.
Consequence: `MAX_REPAIR_ATTEMPTS` stays (one code repair, then the verdict is
final; check R19 keeps pinning it). `BAND_MARKERS` stays the single source of
the markers.

#### R-09 — the model repair pass
Opened: `src/world_engine/day_narration.py:27-37` (module docstring),
`172-197` (`repair`)
Finding [M]: `repair(fact_sheet, prior_prose, offending_words, db)` loads the
`day_narration_repair` template, sends the fact sheet, the words and the prose,
returns `raw.strip()`. The docstring describes it as the only recovery path.
Consequence: B deletes `repair` and rewrites the docstring paragraph.

#### R-10 — `_narrate_and_judge` (route)
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

#### R-12 — `checks/day_narration.py`
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

#### R-13 — `checks/day_prompt_delivery.py`
Opened: `tooling/verify/checks/day_prompt_delivery.py:1-50` (docstring),
`56-76` (`DAY_CONSTANTS`, `EXPECTED_HEAD_IDS`), `182-183` (literal 10),
`487-493` (PASS message)
Finding [M]: 18 constants including `DAY_NARRATION_REPAIR_SYSTEM_PROMPT` and
`DAY_NARRATION_REPAIR_USER_TEMPLATE`; 10 head ids including
`pt-day-narration-repair`; R2 compares `len(heads_node.elts) != 10`. The
docstring calls the counts "deliberately literal and deliberately brittle".
Consequence: B lowers them to 16 and 9 in every place they appear.

#### R-14 — `checks/prompt_registry.py`
Opened: `tooling/verify/checks/prompt_registry.py:1-15`, `74-79`, `115-140`
Finding [M]: rule 1 is a bijection between `PROMPT_REGISTRY` keys and every
`usage = "..."` match of `USAGE_LINE = re.compile(r'usage\s*=\s*"([a-z_]+)"')`
over the whole text of `scripts/seed_pilot.py` (comments included). Rule 2
requires every `call_sites` entry to resolve to an existing `def`.
Consequence: retiring the repair usage means removing it from the registry and
removing every `usage="day_narration_repair"` match from `seed_pilot.py` in the
same commit.

#### R-15 — `PROMPT_REGISTRY` entries
Opened: `src/world_engine/prompt_registry.py:55-61` (`PromptSpec`), `317-337`
Finding [M]: `day_narration` → `call_sites=("src/world_engine/day_narration.py:narrate",)`;
`day_narration_repair` → `call_sites=("src/world_engine/day_narration.py:repair",)`,
lines 331-337.
Consequence: B deletes lines 331-337.

#### R-16 — `scripts/seed_pilot.py` narration and repair text
Opened: `scripts/seed_pilot.py:1927-1975`, `2012-2044`, `2203-2231`
Finding [M]: comment block 1927-1940 (says the fact sheet carries "per-step
band markers"); `DAY_NARRATION_SYSTEM_PROMPT` 1941-1968 and
`DAY_NARRATION_USER_TEMPLATE` 1970-1975; repair comment 2012-2018 and the two
repair constants 2019-2044; heads `pt-day-narration` (2203-2212, variables
`["declaration", "fact_sheet"]`) and `pt-day-narration-repair` (2223-2231,
the only `usage="day_narration_repair"` line, 2226).
Consequence: B deletes 2012-2044 and the 2223-2231 head. C replaces the two
narration constants and the 1927-1940 comment. Variables are unchanged.

#### R-17 — `prompt_coverage.DAY_CHAIN_USAGES`
Opened: `src/world_engine/prompt_coverage.py:1-20`, `43-50`
Finding [M]: derived from `PROMPT_REGISTRY` (every usage whose call site is a
`src/world_engine/day_*.py` module, minus `DEGRADING_USAGES`), never a literal
list.
Consequence: once the registry entry is gone, `declare_day` no longer requires
a `day_narration_repair` template. Nothing to edit here.

#### R-18 — the prompts CRUD
Opened: `src/world_engine/cockpit/crud/prompts.py:119-145`, `148-160`
Finding [M]: the list iterates `PROMPT_REGISTRY` only; the detail route
returns 500 for a row whose usage has no registry entry.
Consequence: after B the prod head `pt-day-narration-repair` (a DB row, never
deleted — history is sacred) is no longer listed in « Prompts »; only a direct
request by its id would reach the 500. Accepted: nothing links to it.

#### R-29 — measured behaviour on prod data (diagnostic, 2026-09-25)
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

#### R-30 — enumeration: every reference to the model repair
Opened: `grep -rn "day_narration_repair\|MAX_REPAIR_ATTEMPTS\|\brepair\b"
--include=*.py src tooling scripts` and `grep -rln DAY_NARRATION_REPAIR`
Finding [M]: pasted in Gate output (c1).
Consequence: B's scope list is exactly that enumeration minus unrelated uses of
the word "repair".

## Contracts

#### C-01 — `lowercase_offending_words`
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

## Context

Measured (R-29): the model repair pass lower-cases whole proses, markers
included, and the zero-names guard then rejects them. The repair's directive
was already literal — "write these words in lower case" — so code does it
exactly (J2'a). Sentence-initial words and capitals copied from the fact
sheet are covered by the same repair (J4'a). The model repair is retired from
code, registry and seed; its DB rows stay (history is sacred).

## Scope IN

1. In `src/world_engine/day_narration_guard.py`, immediately after
   `judge_narration`, add exactly:

   ```python
   def lowercase_offending_words(prose: str, words: tuple[str, ...]) -> str:
       """The code repair (TICKET-0093, J2'a): lower-case every word token
       exactly equal to one of `words`, outside `[MARKER]` spans, and change
       nothing else. It replaces the model repair pass, which lower-cased
       whole proses. An offending word is never a word of an authorised name
       (`judge_narration` builds it from words outside `_authorised_words`),
       so no authorised name can be touched. A genuinely invented name is
       lower-cased and passes, exactly as with the model repair it
       replaces."""
       if not words:
           return prose
       targets = frozenset(words)

       def _lower_segment(segment: str) -> str:
           return _TOKEN_RE.sub(
               lambda m: m.group().lower() if m.group() in targets else m.group(), segment,
           )

       parts: list[str] = []
       last = 0
       for marker in _MARKER_RE.finditer(prose):
           parts.append(_lower_segment(prose[last:marker.start()]))
           parts.append(marker.group())
           last = marker.end()
       parts.append(_lower_segment(prose[last:]))
       return "".join(parts)
   ```

   Change the comment on `JudgeVerdict.offending_words` (lines 107-109) to:
   `# Populated only by the containment branch below -- the exact words the`
   / `# code repair (lowercase_offending_words, TICKET-0093) lower-cases.`
   / `# The route must never parse `reason` to recover this.`

2. In `src/world_engine/day_narration.py`:
   - delete the function `repair` entirely;
   - replace the module-docstring paragraph that starts `The repair pass
     (TICKET-0079, BRIEF-0079-b, `C1a`/`P1`)` and ends `never a` / `loop.`
     with exactly:

     ```
     The repair (TICKET-0093, J2'a) is code, not a model call:
     `day_narration_guard.lowercase_offending_words` lower-cases the exact
     words the judge rejected on name containment, and nothing else. The
     model repair pass it replaces (TICKET-0079) lower-cased whole proses,
     which the zero-names guard then rejected. Bounded by
     `MAX_REPAIR_ATTEMPTS`: one repair, then whatever verdict results is
     final.
     ```
   - replace the two comment lines above `MAX_REPAIR_ATTEMPTS = 1` with
     `# One code repair per resolution (TICKET-0093, J2'a) — the verdict after`
     / `# it is final, never a loop.` Keep `MAX_REPAIR_ATTEMPTS = 1`.

3. In `src/world_engine/cockpit/routes/day.py`:
   - line 43 becomes
     `from ...day_narration import detect_late_delta, narrate, rewrite as rewrite_narration`;
   - line 44 becomes
     `from ...day_narration_guard import JudgeVerdict, judge_narration, lowercase_offending_words`;
   - in `_narrate_and_judge`, replace the block
     `if not verdict.passed and verdict.offending_words:` … through the
     `verdict = judge_narration(prose, fact_sheet)` that follows the repair
     try block with exactly:

     ```python
         if not verdict.passed and verdict.offending_words:
             prose = lowercase_offending_words(prose, verdict.offending_words)
             verdict = judge_narration(prose, fact_sheet)
     ```
   - in its docstring, replace `the ONE conditional repair attempt (TICKET-0079,`
     / `BRIEF-0079-b)` with `the ONE conditional code repair (TICKET-0093,`
     / `J2'a)`.

4. In `src/world_engine/prompt_registry.py`, delete the
   `"day_narration_repair": PromptSpec(...)` entry (lines 331-337).

5. In `scripts/seed_pilot.py`, delete the `# day_narration_repair: ...`
   comment block and both `DAY_NARRATION_REPAIR_*` constants (2012-2044,
   up to and including the closing `"""` of
   `DAY_NARRATION_REPAIR_USER_TEMPLATE`), and delete the
   `dict(id="pt-day-narration-repair", ...)` entry of `DAY_PROMPT_HEADS`
   (2223-2231). After the edit, `grep -n "day_narration_repair\|DAY_NARRATION_REPAIR" scripts/seed_pilot.py`
   returns nothing (R-14: the bijection reads comments too).

6. In `tooling/verify/checks/day_prompt_delivery.py`:
   - remove `"DAY_NARRATION_REPAIR_SYSTEM_PROMPT", "DAY_NARRATION_REPAIR_USER_TEMPLATE",`
     from `DAY_CONSTANTS`;
   - remove `"pt-day-narration-repair",` from `EXPECTED_HEAD_IDS`;
   - `!= 10` and `expected 10` at 182-183 become `!= 9` and `expected 9`;
   - in the docstring, after `(9 -> 10 heads, 16 -> 18 constants) for the
     `day_narration_repair` usage.` add the sentence `TICKET-0093/BRIEF-0093-B
     retires that usage (10 -> 9 heads, 18 -> 16 constants).`; in R1 `the 18
     named` becomes `the 16 named`; in R2 `exactly 10 entries` becomes
     `exactly 9 entries` and `the 10 `id` values` becomes `the 9 `id` values`;
   - in the PASS message `the 18 DAY_* constants` becomes `the 16 DAY_* constants`.

7. In `tooling/verify/checks/day_narration.py`:
   - replace the docstring text of R19 and R20 with exactly:

     ```
     R19 (bounded code repair, TICKET-0093 J2'a): `MAX_REPAIR_ATTEMPTS` is a
     module-level constant in `day_narration.py` with the value `1`;
     `_narrate_and_judge` in `cockpit/routes/day.py` calls
     `lowercase_offending_words` exactly once, behind an `if`; and
     `day_narration.py` defines no top-level function named `repair`.
     R20 (model repair retired, TICKET-0093 J2'a): `day_narration_repair` is
     NOT a `PROMPT_REGISTRY` key.
     ```
     and change the section title `--- BRIEF-0079-b (bounded repair pass and
     failure surface) ---` to `--- BRIEF-0079-b, amended by TICKET-0093
     (bounded code repair and failure surface) ---`;
   - remove the `"day_narration_repair": ("repair", "R20"),` line from
     `_REGISTRY_WIRING_EXPECTED`; at the end of `check_registry_wiring` add:
     if `"day_narration_repair" in prompt_registry.PROMPT_REGISTRY`, fail with
     `"day_narration R20: day_narration_repair is still a PROMPT_REGISTRY key — the model repair is retired (TICKET-0093, J2'a)"`;
   - in `check_bounded_repair`: keep the `MAX_REPAIR_ATTEMPTS` part; match
     calls whose name is `lowercase_offending_words` instead of `repair` (both
     the `ast.Name` and `ast.Attribute` forms), with the same
     zero / more-than-one / no-`if` failures, messages saying "the code
     repair"; then add: if `day_narration.py`'s module body contains a
     `FunctionDef` named `repair`, fail with
     `"day_narration R19: day_narration.py still defines repair — the model repair is retired (TICKET-0093)"`;
   - in `check_registry_wiring`'s vacuity message,
     `zero day_narration/day_rewrite/day_narration_repair entries found`
     becomes `zero day_narration/day_rewrite entries found`;
   - in the PASS message, `BRIEF-0079-b's bounded repair and failure-surface gates`
     becomes `the bounded code repair, the retired model repair and the failure-surface gates`.

8. In `tooling/verify/checks/day_narration_beats.py`, add the C-01 cases, one
   per row of the lot's table (b2), called from `main()`:
   - `B1`: `lowercase_offending_words("[RÉUSSITE] Malheureusement, Mini attend la Reine. La Reine sourit.", ("Malheureusement", "Reine"))`
     == `"[RÉUSSITE] malheureusement, Mini attend la reine. La reine sourit."`;
   - `B2`: `lowercase_offending_words("[RÉUSSITE] RÉUSSITE pour Mini.", ("RÉUSSITE",))`
     == `"[RÉUSSITE] réussite pour Mini."` (marker untouched);
   - `B3`: `lowercase_offending_words("Les Reines passent.", ("Reine",))`
     == `"Les Reines passent."`;
   - `B4`: `lowercase_offending_words(p, ()) is p` for any non-empty `p`;
   - `B5` (end to end, J4'a): with A1's fact sheet, the prose of A1 fails,
     `lowercase_offending_words(prose, verdict.offending_words)` then passes
     `judge_narration`.

9. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## THE NARRATION REPAIR IS CODE (TICKET-0093) -- THE MODEL REPAIR PASS IS RETIRED (BRIEF-0093-B, no schema change)`,
   stating: the measurement (R-29), J2'a and J4'a, C-01's rule and its known
   limit (an invented name is lower-cased and passes, as before), the retired
   registry entry / seed head / constants, the DB rows left in place and the
   « Prompts » consequence (R-18), and the rejected J2'b/J2'c/J4'b with their
   reactivation conditions (TICKET-0093). Regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- The narration prompt, `_render_fact_sheet`, `narrate`, JSON output, band
  labels: brief C.
- Deleting or deactivating the `pt-day-narration-repair` DB rows, on prod or
  anywhere: never (history is sacred). No apply script in this brief.
- Ignoring sentence-initial words in the judge (J4'b, rejected).
- Any change to R5, `extract_names`, `_FUNCTION_WORD_STOPWORDS`, or the order
  of the judge's checks (J1'a).
- The rewrite pass and its prompt.
- `tooling/briefs/BRIEF-0079-b-*.md` (history).

## Invariants to defend

- "History is sacred": no DB row is edited or deleted; stored proses are not
  re-judged or rewritten.
- "The judge is Python" (check R4): `lowercase_offending_words` contains no
  `chat(`.
- Fail-closed: the code repair only acts on `offending_words`; zero-names,
  zero-steps and band-marker failures still end in 422.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- the re-run enumeration (c1) shows a consumer of `repair`,
  `day_narration_repair` or `DAY_NARRATION_REPAIR` not listed in the lot;
- removing the registry entry makes any check other than the ones this brief
  amends fail;
- `_narrate_and_judge` would exceed 80 lines, or the route module 1000.

ADAPT:
- a PASS or docstring phrase quoted above differs in wording but not in
  meaning (line-wrapping, punctuation): apply the equivalent edit, report the
  exact text found.
- `LlmParseError` becomes unused in `routes/day.py` after item 3: it is not —
  `narrate` and `rewrite_narration` still use it; if pyflakes reports it
  unused anyway, STOP.

REPORT-ONLY:
- other mentions of "repair" in unrelated docstrings (R-30 lists them).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_narration_beats.py` → `PASS:` with
      A1-A3 and B1-B5 executed.
- [ ] `python tooling/verify/checks/day_narration.py` → `PASS:`.
- [ ] `python tooling/verify/checks/day_prompt_delivery.py` → `PASS:`.
- [ ] `python tooling/verify/checks/prompt_registry.py` → exit 0.
- [ ] `grep -rn "day_narration_repair\|DAY_NARRATION_REPAIR" src scripts tooling/verify`
      returns only lines of `checks/day_narration.py` (R20 docstring and
      assertion) and the historical count sentence of
      `checks/day_prompt_delivery.py`'s docstring.
- [ ] Mutation: deleting the `lowercase_offending_words(...)` call from
      `_narrate_and_judge` makes `day_narration.py` fail on R19; restore.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry + regenerated `DECISIONS_INDEX.md`
  (Scope IN 9). No schema changelog, no CLAUDE.md (R-27).
