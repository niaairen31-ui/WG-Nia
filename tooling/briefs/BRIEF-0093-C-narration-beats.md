# BRIEF 0093-C — "one text per step, markers written by code"

Lot: LOT-0093-day-narration-judge.md (authoritative on conflict)
Depends on: B (shared files: `day_narration.py`, `checks/day_narration.py`,
`checks/day_narration_beats.py`, `scripts/seed_pilot.py`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/day_narration.py`: `BAND_MARKERS` as quoted in R-06;
  `def _render_fact_sheet(` whose step line contains `marqueur attendu`;
  `def narrate(` whose `ollama_client.chat(` call has no `format=` and which
  returns `raw.strip()`; no function named `repair` (B removed it).
- `src/world_engine/llm_parse.py:44` `def extract_object(raw: str) -> dict:`.
- `src/world_engine/ollama_client.py:88-95` `chat(...)` accepts
  `format: str | dict | None = None`.
- `src/world_engine/cockpit/routes/day.py`: in `_narrate_and_judge`,
  `narrate(...)` sits inside `try:` / `except LlmParseError as exc:` → 502.
- `scripts/seed_pilot.py`: `DAY_NARRATION_SYSTEM_PROMPT = """\` and
  `DAY_NARRATION_USER_TEMPLATE = """\`; head `pt-day-narration` with
  `variables=["declaration", "fact_sheet"]`.
- `scripts/apply_ticket_0078_narration_seed.py` exists, 72 lines.
- `tooling/verify/checks/day_narration_beats.py` runs A1-A3 and B1-B5.

## Facts carried

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

#### R-07 — `_render_fact_sheet`
Opened: `src/world_engine/day_narration.py:95-114`; callers at 129, 154, 183
Finding [M]: renders `Jour N.`, `Personnage joueur : X.`, then per step
`- Étape « {objective} » — marqueur attendu {marker}{detail}.` (+ blocked
detail), then `Personnes nommables`, `Lieux nommables`, and the role-hint line.
Called by `narrate` (129), `rewrite` (154) and `repair` (183).
Consequence: C replaces the marker in the step line by a band label (C-04) and
numbers the steps; the model is never shown a marker. `rewrite` keeps calling
it (its prompt is out of scope).

#### R-08 — `narrate`
Opened: `src/world_engine/day_narration.py:117-140`
Finding [M]: loads the `day_narration` template, builds `user_msg` from
`{declaration}` and `{fact_sheet}` + `"\n/no_think"`, calls
`ollama_client.chat(messages, model=effective_model(...), host=...)` with no
`format`, returns `raw.strip()`.
Consequence: C adds `format="json"` and returns `assemble_beats(raw,
fact_sheet)` (C-02, C-03). The body keeps no `select(` (check R3).

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

#### R-19 — JSON parsing and the chat call
Opened: `src/world_engine/llm_parse.py:21-22` (`LlmParseError(ValueError)`),
`44-60` (`extract_object`); `src/world_engine/ollama_client.py:88-100`
(`chat(..., format: str | dict | None = None, options=None)`);
`src/world_engine/day_extract.py:117-127` (precedent)
Finding [M]: `extract_object` strips fences, takes the first balanced `{...}`,
raises `LlmParseError` if absent, invalid, or not an object. `day_extract`
calls `chat(..., format="json")` then `llm_parse.extract_object(raw)`.
Consequence: C-02 uses `extract_object` and raises `llm_parse.LlmParseError`;
C-03 passes `format="json"`.

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

#### R-24 — apply-script precedent
Opened: `scripts/apply_ticket_0078_narration_seed.py` (whole file)
Finding [M]: refuses to run unless `WORLD_ENGINE_ENV` is `prod` or `test`;
imports the constants from `seed_pilot` (embeds no text); loads head
`pt-day-narration`; exits 1 if missing; prints "unchanged" if the current
version matches; otherwise `write_prompt_version(session, template_id=...,
system_prompt=..., user_template=..., note=...)`, commits, prints
`vN -> vM`. Idempotent.
Consequence: C's script is this file with the note and names changed.

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

#### R-31 — enumeration: consumers of the markers
Opened: `grep -rn "RÉUSSITE\|offending_words\|BLOQUÉ" frontend/src` and
`grep -rn "RÉUSSITE\|BAND_MARKERS" --include=*.py src | grep -v day_narration`
Finding [M]: pasted in Gate output (c2): no consumer outside the two narration
modules and their checks.
Consequence: no frontend change; `frontend_build_fresh` is untouched.

## Contracts

#### C-02 — `assemble_beats`
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

#### C-03 — `narrate` (amended)
Produced by: BRIEF-0093-C   Consumed by: `cockpit/routes/day.py::_narrate_and_judge` (unchanged call)
Signature: unchanged, `def narrate(fact_sheet: FactSheet, declaration: str, db: Session) -> str`.
Return shape: `assemble_beats(raw, fact_sheet)`, where `raw` is the result of
the existing `ollama_client.chat(...)` call with `format="json"` added.
Error and empty cases: missing template → `LlmParseError` (unchanged); any
C-02 error propagates → the route's existing 502.

#### C-04 — `BAND_LABELS_FR`
Produced by: BRIEF-0093-C   Consumed by: `_render_fact_sheet`, checks
Signature: module-level `BAND_LABELS_FR: dict[str, str]` in
`src/world_engine/day_narration.py`, immediately after `BAND_MARKERS`.
Return shape: exactly `{"success": "réussite", "partial": "réussite partielle",
"failure": "échec", BLOCKED_BAND: "bloquée"}` — key set equal to
`BAND_MARKERS`'.
Error and empty cases: none (a missing band is a `KeyError`, as with
`BAND_MARKERS` today).

## Context

Measured (R-29): the model writes band markers unreliably — the first step is
rendered `[RÉUSSITE]` whatever its outcome, accents are dropped, and whole
paragraphs come back in brackets, which `_MARKER_RE` erases before name
extraction. J5b makes markers correct by construction: the model returns one
text per step as JSON and never sees a marker; the code writes each marker
from the fact sheet. After B, this is the last cause the lot addresses.

## Scope IN

1. In `src/world_engine/day_narration.py`, immediately after `BAND_MARKERS`,
   add exactly:

   ```python
   # French outcome labels the model reads instead of markers (TICKET-0093,
   # J5b): the model never sees or writes a marker; `assemble_beats` writes
   # them. Key set equal to BAND_MARKERS'.
   BAND_LABELS_FR: dict[str, str] = {
       "success": "réussite", "partial": "réussite partielle", "failure": "échec", BLOCKED_BAND: "bloquée",
   }
   ```

2. Replace `_render_fact_sheet`'s step loop (the four lines from
   `for step in fact_sheet.steps:` through `lines.append(line)`, keeping the
   `blocked_detail` sentence) with exactly:

   ```python
       for index, step in enumerate(fact_sheet.steps, start=1):
           detail = f" (jet total {step.total})" if step.total is not None else " (aucun jet)"
           line = f"- Étape {index} « {step.objective} » — issue : {BAND_LABELS_FR[step.band]}{detail}."
           if step.blocked_detail:
               line += f" Le personnage n'a pas pu l'entreprendre : {step.blocked_detail}."
           lines.append(line)
   ```
   Every other line of `_render_fact_sheet` is unchanged.

3. Immediately after `_render_fact_sheet`, add exactly:

   ```python
   def assemble_beats(raw: str, fact_sheet: FactSheet) -> str:
       """C-02 (TICKET-0093, J5b): the model's JSON — one text per step, in
       step order — becomes the prose, each text prefixed by the step's
       marker from BAND_MARKERS. Brackets in the model's text are removed so
       the code-written markers are the only bracketed spans the judge sees.
       Pure: no db, no chat(. Every defect raises LlmParseError, which the
       route already turns into a 502."""
       if not fact_sheet.steps:
           raise llm_parse.LlmParseError("day_narration: fact sheet has no steps")
       obj = llm_parse.extract_object(raw)
       beats = obj.get("etapes")
       if not isinstance(beats, list):
           raise llm_parse.LlmParseError("day_narration: 'etapes' is not a list")
       if len(beats) != len(fact_sheet.steps):
           raise llm_parse.LlmParseError(
               f"day_narration: expected {len(fact_sheet.steps)} texts, got {len(beats)}"
           )
       parts: list[str] = []
       for number, (step, beat) in enumerate(zip(fact_sheet.steps, beats), start=1):
           text = beat.replace("[", "").replace("]", "").strip() if isinstance(beat, str) else ""
           if not text:
               raise llm_parse.LlmParseError(f"day_narration: text for step {number} is empty or not a string")
           parts.append(f"{BAND_MARKERS[step.band]} {text}")
       return "\n\n".join(parts)
   ```

4. In `narrate`: add `format="json",` as a keyword argument of the
   `ollama_client.chat(` call (after `host=...`), and replace
   `return raw.strip()` with `return assemble_beats(raw, fact_sheet)`.
   Replace its docstring with exactly:
   `"""ONE model call (Scope IN item 3). Takes the fact sheet and the`
   / `declaration and nothing else derived from the DB (R3): `db` is used`
   / `only to load and read the prompt template. Returns the prose assembled`
   / `by assemble_beats (TICKET-0093, J5b)."""`

5. In the module docstring, replace the item beginning
   `  2. Prefix each step's beat with the EXACT band marker` (four lines,
   ending `outcome-survival check key off.`) with exactly:

   ```
     2. Return one text per step as JSON (`{"etapes": [...]}`); the code
        writes each step's band marker itself (`assemble_beats`,
        TICKET-0093 J5b), so the model never sees or writes a marker.
        `BAND_MARKERS` below stays the single source both the assembly and
        the judge's outcome-survival check key off.
   ```

6. In `scripts/seed_pilot.py`, replace the comment block that starts
   `# ----- prompt templates: day narration and rewrite (TICKET-0075, -------`
   and ends just above `DAY_NARRATION_SYSTEM_PROMPT = """\` with exactly:

   ```
   # ----- prompt templates: day narration and rewrite (TICKET-0075, -------
   # BRIEF-0075-d; narration reshaped by TICKET-0093, J5b). The narration is
   # a RENDERING of an already-decided outcome (dice are Python,
   # resolution.py); this prompt never asks the model to decide anything.
   # Since TICKET-0093 the model returns one text per step as JSON and the
   # code writes each step's band marker (day_narration.assemble_beats), so
   # the prompt never mentions a marker. Positive-form only: the gameplay
   # model is abliterated and does not reliably follow negative constraints;
   # enforcement is the T1 judge (day_narration_guard.py), never the prompt
   # text. `{fact_sheet}` is a code-rendered block
   # (day_narration._render_fact_sheet) — its authorised names must match
   # EXACTLY what the judge checks against.
   ```

7. Replace `DAY_NARRATION_SYSTEM_PROMPT` and `DAY_NARRATION_USER_TEMPLATE`
   with exactly (the backslash line continuations are part of the text):

   ```python
   DAY_NARRATION_SYSTEM_PROMPT = """\
   Tu es le conteur d'un jeu de rôle. Le joueur a passé une journée entière \
   hors scène ; le déroulé mécanique de sa journée (jets de dés, issues) est \
   déjà DÉCIDÉ et te sera donné, étape par étape. Ton travail : raconter \
   chaque étape en prose, en RENDANT ce qui s'est déjà passé, jamais en \
   décidant quoi que ce soit toi-même.

   RÈGLES :
   - Écris un texte par étape, dans l'ordre donné : exactement autant de \
   textes qu'il y a d'étapes.
   - Chaque texte raconte son étape dans l'esprit de son issue. Pour une étape \
   dont l'issue est « bloquée », raconte que le personnage s'y est heurté et ce \
   qu'il en a entrevu, en te servant de la raison donnée sans la recopier.
   - Nomme le personnage joueur par son nom (donné sous « Personnage joueur ») \
   au moins une fois dans l'ensemble du récit.
   - Nomme les personnes et les lieux listés sous « Personnes nommables » et \
   « Lieux nommables », plus le personnage joueur lui-même. La majuscule \
   initiale est réservée à ces noms et au premier mot de chaque phrase ; tout \
   autre mot s'écrit en minuscules, y compris les groupes, les métiers, les \
   titres et les fonctions.
   - Pour toute personne ou tout lieu listé sous « Personnes et lieux sans nom \
   résolu », désigne-le uniquement par sa fonction donnée, en minuscules.
   - Écris chaque texte en prose simple, sans crochets, sans titre et sans \
   numéro d'étape.

   Réponds UNIQUEMENT avec un objet JSON de la forme \
   {"etapes": ["texte de l'étape 1", "texte de l'étape 2"]}, en français, sans \
   préambule ni commentaire.\
   """

   DAY_NARRATION_USER_TEMPLATE = """\
   Déclaration du joueur : {declaration}

   {fact_sheet}

   Raconte cette journée, un texte par étape.\
   """
   ```
   The `pt-day-narration` head (variables `["declaration", "fact_sheet"]`)
   is unchanged.

8. Create `scripts/apply_ticket_0093_narration_prompt.py` as a copy of
   `scripts/apply_ticket_0078_narration_seed.py` (R-24) with exactly these
   changes:
   - the first docstring paragraph becomes
     `"""One-shot, idempotent delivery of the TICKET-0093 `day_narration``
     / `prompt update onto the live DB (BRIEF-0093-C, Scope IN item 8): one`
     / `text per step as JSON, markers written by code (J5b).`;
     every other docstring paragraph is kept;
   - the refusal message names `apply_ticket_0093_narration_prompt.py`;
   - `note="TICKET-0093 BRIEF-0093-C -- one text per step as JSON (J5b)"`.
   It embeds no prompt text (it imports the constants from `seed_pilot`).

9. In `tooling/verify/checks/day_narration.py`:
   - R22: add to `forbidden` the strings `"[RÉUSSITE]"`, `"[PARTIEL]"`,
     `"[ÉCHEC]"`, `"[BLOQUÉ]"` and `"marqueur"`; extend R22's docstring with
     `TICKET-0093 (J5b): it also names no band marker and no "marqueur" — the
     code writes markers.`;
   - add R23 (docstring, function `check_narration_beats_wiring`, called from
     `main()`, mentioned in the PASS message as `the code-written markers
     (R23)`): `narrate`'s body contains a call named `assemble_beats` and an
     `ollama_client.chat(` call with keyword `format` equal to the constant
     `"json"`; `_render_fact_sheet`'s body contains no `Name` `BAND_MARKERS`.
     Vacuity: either function not found is a FAILURE.

10. In `tooling/verify/checks/day_narration_beats.py`, add, called from
    `main()` (fact sheet: `character_name="Eiraan"`,
    `authorised_names={"Eiraan"}`, steps `partial` then `blocked`):
    - `C1`: `assemble_beats('{"etapes": ["[Eiraan se rend au manoir.]", "Elle s\'y heurte."]}', fs)`
      == `"[PARTIEL] Eiraan se rend au manoir.\n\n[BLOQUÉ] Elle s'y heurte."`,
      and `judge_narration` on it passes;
    - `C2`: `"pas de json"` → `LlmParseError`;
    - `C3`: `'{"x": 1}'` → `LlmParseError` whose message contains
      `"'etapes' is not a list"`;
    - `C4`: `'{"etapes": ["a"]}'` → message contains `"expected 2 texts, got 1"`;
    - `C5`: `'{"etapes": ["a", "[]"]}'` and `'{"etapes": ["a", 3]}'` → message
      contains `"text for step 2"`;
    - `C6`: a fact sheet with `steps=()` → message contains `"has no steps"`;
    - `C7`: `set(BAND_LABELS_FR) == set(BAND_MARKERS)`;
    - `C8`: `_render_fact_sheet(fs)` contains none of `BAND_MARKERS.values()`,
      and contains `"- Étape 1 « "` and `"issue : réussite partielle"`.

11. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
    `## ONE TEXT PER STEP (TICKET-0093) -- THE CODE WRITES THE BAND MARKERS (BRIEF-0093-C, no schema change)`,
    stating: the measured marker defects (R-29), J5b, C-02's rules and error
    cases, that `_render_fact_sheet` shows labels not markers (so the rewrite
    pass also receives labels), the apply script Nia runs on prod, and the
    rejected J5a with its reactivation condition. Regenerate
    `DECISIONS_INDEX.md`.

## Scope OUT

- The rewrite prompt (`DAY_REWRITE_*`) and `rewrite()`: untouched, although
  its prompt still mentions markers (it cannot fire today, R-09's docstring).
- Tolerant marker counting in the judge (J5a, rejected) and any change to
  `judge_narration`, `_MARKER_RE`, `extract_names` (J1'a).
- Retry on a JSON 502 inside the route: none; Nia clicks « Résoudre » again,
  as today.
- `options=` on the chat call (temperature etc.): not in this lot.
- Running the apply script on prod: Nia does it (live gate).
- Frontend: no change (R-31).

## Invariants to defend

- "Prompts live in the DB; a text change ships as an apply script": the seed
  constants change AND the script ships in the same commit.
- "History is sacred": the script appends a `prompt_version`, never edits one.
- "The prose is a rendering" (R3): `narrate` keeps no `select(`;
  `assemble_beats` has no `db`.
- The gameplay model is abliterated: the prompt stays positive-form (R22).

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- a caller of `_render_fact_sheet` or `narrate` exists beyond R-07/R-10's;
- `format="json"` is rejected by `ollama_client.chat` at runtime in the test
  environment;
- `day_narration.py` would exceed 1000 lines or 40 functions.

ADAPT:
- the four-line step loop in `_render_fact_sheet` differs only by
  whitespace: replace it anyway, report.
- `BLOCKED_BAND` is not imported in `day_narration.py`: it is (line 48); if
  the import moved, use it from `day_resolve`, report.

REPORT-ONLY:
- the « Prompts » dry-run for `day_narration` now shows raw JSON.
- the rewrite prompt's marker wording.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_narration_beats.py` → `PASS:` with
      A1-A3, B1-B5, C1-C8 executed.
- [ ] `python tooling/verify/checks/day_narration.py` → `PASS:` (R22, R23 included).
- [ ] `python tooling/verify/checks/day_prompt_delivery.py` and
      `python tooling/verify/checks/prompt_registry.py` → pass.
- [ ] On a test DB seeded before this brief, `WORLD_ENGINE_ENV=test python
      scripts/apply_ticket_0093_narration_prompt.py` prints
      `pt-day-narration: vN -> vN+1`; a second run prints `unchanged`.
- [ ] Mutation: `return raw.strip()` restored in `narrate` makes R23 fail;
      restore.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry + regenerated `DECISIONS_INDEX.md`
  (Scope IN 11). No schema changelog, no CLAUDE.md (R-27).
