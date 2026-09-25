# BRIEF 0094-C — "the call: prompt and choose"

Lot: LOT-0094-concordance-h2.md (authoritative on conflict)
Depends on: B (`day_choice.py` pure half)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/day_choice.py` exists with `choice_requests`,
  `render_candidates`, `category_label`, `parse_answer`, `judge_choice`,
  `record_of`, and no `chat(`.
- `src/world_engine/day_plan_select.py:33` `def _load_day_plan_select_template(`.
- `src/world_engine/ollama_client.py:39` `class OllamaError(RuntimeError):`.
- `src/world_engine/prompt_registry.py:345` `"day_plan_select": PromptSpec(`.
- `scripts/seed_pilot.py:2117` `DAY_PLAN_SELECT_USER_TEMPLATE = """\`,
  `:2126` `DAY_PROMPT_HEADS = (`, `:2217` its closing `)`.
- `tooling/verify/checks/day_prompt_delivery.py:182` `!= 9`;
  `tooling/verify/checks/prompt_registry.py:29` `WIRED_FILES = [`.
- `scripts/apply_ticket_0077_plan_select_seed.py` exists.

## Facts carried

#### R-09 — the chat call and its failures
Opened: `src/world_engine/ollama_client.py:39`, `66-70`, `88-131`;
`src/world_engine/llm_parse.py:21-22`, `44-60`;
`src/world_engine/day_plan_select.py:33-48`, `84-110`
Finding [M]: `chat(...)` raises `OllamaError(RuntimeError)` on HTTP error,
unreachable host, timeout (`OSError`) or a body error; returns the content with
the think block stripped. `extract_object` raises `LlmParseError(ValueError)`.
`day_plan_select` loads its template with a `usage == ...,
is_active == True` query preferring the world's row then the global one,
raises `LlmParseError("...: no active prompt_template for usage=...")` when
absent, reads `current_prompt`, appends `"\n/no_think"`, calls
`chat(..., model=effective_model(template, ollama_client.DEFAULT_MODEL),
host=ollama_client.OLLAMA_HOST, format="json", ...)`.
Consequence: C copies that loader and call shape. Technical failure =
`OllamaError` or `LlmParseError` from the call or `parse_answer` (Y8a). The
missing-template raise happens before the first call and is never retried.

#### R-10 — prompt plumbing gates
Opened: `src/world_engine/prompt_registry.py:55-61`, `317-351`;
`src/world_engine/prompt_coverage.py:38-50`;
`tooling/verify/checks/prompt_registry.py:29-42`, `74-79`;
`tooling/verify/checks/day_prompt_delivery.py:1-76`, `182-183`, `488`;
`scripts/seed_pilot.py:2117-2217`; `scripts/apply_ticket_0077_plan_select_seed.py`
Finding [M]:
- `DAY_CHAIN_USAGES` includes every usage whose call site matches
  `^src/world_engine/day_[a-z_]+\.py$`, minus `day_feasibility`.
- `prompt_registry` check: bijection with `usage = "..."` lines of
  `seed_pilot.py`; `WIRED_FILES` (lines 29-42) lists the modules whose `chat(`
  must use `effective_model(`.
- `day_prompt_delivery`: 16 constants, 9 heads (`EXPECTED_HEAD_IDS`, literal
  `!= 9`); R6 classifies each `day_*.py` "no active prompt_template" message
  as `Raise`/`Return`, and the `Raise` set must equal `DAY_CHAIN_USAGES`.
- `DAY_PROMPT_HEADS` closes at line 2217, last head `pt-day-plan-select`
  (2208); `DAY_PLAN_SELECT_USER_TEMPLATE` at 2117.
- The 0077 script loops `DAY_PROMPT_HEADS` through `upsert_prompt_template`
  (idempotent), embeds no text.

Consequence: C adds `"day_mention_choice"` (call site
`src/world_engine/day_choice.py:choose`), which makes it a day-chain usage
refused at declaration when missing (X4a) with no edit to `prompt_coverage`.
Counts become 18 / 10. `day_choice.py` joins `WIRED_FILES`. The apply script
copies the 0077 one.

#### R-11 — day-chain structural checks
Opened: `tooling/verify/checks/day_concordance.py:1-50`, `74`, `292-317`;
`tooling/verify/checks/day_rewrite.py:1-24`, `42-43`
Finding [M]: day_concordance R1 forbids `chat(` in `day_concordance.py`; R4
forbids `Entity(` / `Character(` / `NpcSchedule(` in extract/concordance/
plan; `EXPECTED_RUNGS` pins `MATCHING_RUNGS`. day_rewrite W2: no attribute
assignment on, and no `db.delete(` of, a `_TRACKED_MODELS = {"DayRewrite",
"DayMentionResolution"}` instance, vacuity-guarded by requiring a
construction of each; W6: `routes/day.py` calls each `extract_*` exactly
once.
Consequence: the model call lives in `day_choice.py` (R1 untouched).
`"model_choice"` is a stored rung, not a `MATCHING_RUNGS` entry
(`EXPECTED_RUNGS` untouched). A adds `"DayMentionChoice"` to
`_TRACKED_MODELS`. W6 stays true.

## Contracts

#### C-06 — `render_candidates`, `parse_answer`, `judge_choice`
Produced by: B   Consumed by: C-07
- `render_candidates(request: ChoiceRequest) -> str`: per candidate
  `f"{i}. {name}"`, then either `"   Ce que le personnage sait :"` followed by
  one `"   - {fact}"` line per fact, or
  `"   Le personnage ne sait rien de plus sur lui."`; candidates separated by
  a blank line.
- `parse_answer(raw: str) -> dict`: `llm_parse.extract_object(raw)`;
  requires `choix` an `int` (not `bool`), `extrait` a `str`, `raison` a
  `str`; otherwise `LlmParseError("day_choice: <field> missing or ill-typed")`.
  Returns `{"choix", "extrait", "raison"}`.
- `judge_choice(request, answer, declaration: str) -> ChoiceVerdict`, pure:
  `ChoiceVerdict(verdict: str, entity_id: Optional[str], excerpt:
  Optional[str], reason: Optional[str], detail: Optional[str])`.
  Rules in order:
  1. `choix == 0` → `declined`, entity None.
  2. `choix` outside `1..len(candidates)` → `rejected`, entity None,
     detail `"candidate out of range"`.
  3. `e = normalize_surface(excerpt.strip(" \t\n\"'«»“”.,;:!?…"))`; `len(e) < 3`
     → `rejected`, detail `"excerpt too short"`.
  4. `ambiguous`: `e` must be a substring of
     `normalize_surface(" ".join(chosen.facts))` and of no other candidate's
     joined facts; else `rejected`, detail `"excerpt not in the chosen
     candidate's facts"` or `"excerpt does not single out the chosen
     candidate"`.
  5. `near`: `e` must be a substring of `normalize_surface(declaration)` or
     of the chosen candidate's joined facts; else `rejected`, detail
     `"excerpt not found"`.
  6. otherwise `accepted`, entity = chosen id.
  `excerpt` and `reason` are the answer's, stripped, `None` when empty, on
  every verdict; `entity_id` is set on `accepted` and on a `rejected` whose
  number was in range.
- `record_of(request, verdict: ChoiceVerdict, attempts: int) -> dict`: the
  family shape of C-02; `chosen_entity_id` is `None` for `declined`;
  `evidence_fact_ids` flattens every candidate's `fact_ids` in display order.
  A `failed` record is `record_of(request, ChoiceVerdict("failed", None,
  None, None, <last error text>), 2)`.

#### C-07 — `choose`
Produced by: C   Consumed by: D
Signature: `def choose(result: ConcordanceResult, declaration: str, character:
Character, db: Session) -> ChoiceOutcome`;
`ChoiceOutcome(result: ConcordanceResult, records: tuple[dict, ...])`.
Behaviour: `requests = choice_requests(result, character, db)`; none →
`ChoiceOutcome(result, ())` with no template read. Else load the
`day_mention_choice` template once (missing → `LlmParseError("day_choice: no
active prompt_template for usage='day_mention_choice'")`, never retried).
Per request: up to 2 attempts of {render user message, `chat`,
`parse_answer`}; `OllamaError`/`LlmParseError` on attempt 1 → attempt 2; on
attempt 2 → verdict `failed`. Otherwise `judge_choice`. Accepted: the
mention leaves `ambiguous` (or `unmatched`) and joins `matched` as
`MatchedMention(mention, entity_id, rung="model_choice")`, appended after the
existing matched. Every request yields exactly one record (C-02 shape;
`evidence_fact_ids` = every candidate's `fact_ids`, flattened in display
order; `verdict_detail` = the judge's detail or the last technical error
text for `failed`).

## Context

B built everything except the call. This brief adds the `day_mention_choice`
prompt and `choose`: one model call per request, one retry on a technical
failure only, the judge, and the updated concordance. Nothing calls
`choose` yet (D wires it).

## Scope IN

1. In `src/world_engine/day_choice.py`:
   - imports become: `from dataclasses import dataclass, replace`;
     `from sqlmodel import Session, select`; `from . import llm_parse,
     ollama_client`; `from .day_concordance import ConcordanceResult,
     MatchedMention`; `from .models import Character, Entity,
     PromptTemplate`; add `from .prompt_registry import effective_model` and
     `from .prompt_store import current_prompt`;
   - append exactly:

```python


def _load_choice_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan_select._load_day_plan_select_template`'s precedent, verbatim."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_mention_choice",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


@dataclass(frozen=True)
class ChoiceOutcome:
    result: ConcordanceResult
    records: tuple[dict, ...]


def _ask(request: ChoiceRequest, declaration: str, template: PromptTemplate, db: Session) -> dict:
    """One attempt: render, call, parse. Raises OllamaError/LlmParseError."""
    version = current_prompt(db, template)
    user_msg = (
        version.user_template
        .replace("{declaration}", declaration)
        .replace("{surface_form}", request.mention.surface_form)
        .replace("{category}", category_label(request.mention.category))
        .replace("{candidates}", render_candidates(request))
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
        format="json",
    )
    return parse_answer(raw)


def _decide(request: ChoiceRequest, declaration: str, template: PromptTemplate, db: Session) -> dict:
    """Y5c/Y8a: one retry on a technical failure only, then `failed`."""
    error = ""
    for attempt in (1, 2):
        try:
            answer = _ask(request, declaration, template, db)
        except (ollama_client.OllamaError, llm_parse.LlmParseError) as exc:
            error = str(exc)
            continue
        return record_of(request, judge_choice(request, answer, declaration), attempt)
    return record_of(request, ChoiceVerdict("failed", None, None, None, error), 2)


def _apply(result: ConcordanceResult, request: ChoiceRequest, entity_id: str) -> ConcordanceResult:
    """An accepted choice: the mention leaves ambiguous/unmatched and joins
    matched with rung MODEL_CHOICE_RUNG (Y3b)."""
    matched = (*result.matched, MatchedMention(mention=request.mention, entity_id=entity_id, rung=MODEL_CHOICE_RUNG))
    if request.trigger == "ambiguous":
        ambiguous = tuple(am for am in result.ambiguous if am.mention is not request.mention)
        return replace(result, matched=matched, ambiguous=ambiguous)
    unmatched = tuple(um for um in result.unmatched if um.mention is not request.mention)
    return replace(result, matched=matched, unmatched=unmatched)


def choose(result: ConcordanceResult, declaration: str, character: Character, db: Session) -> ChoiceOutcome:
    """C-07: narrow, ask, judge, apply. No request → no template read and
    no call. A missing template raises before the first call and is never
    retried (X4a: the coverage guard refuses the declaration upstream)."""
    requests = choice_requests(result, character, db)
    if not requests:
        return ChoiceOutcome(result=result, records=())
    template = _load_choice_template(character.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_choice: no active prompt_template for usage='day_mention_choice'")
    records: list[dict] = []
    for request in requests:
        record = _decide(request, declaration, template, db)
        records.append(record)
        if record["verdict"] == "accepted":
            result = _apply(result, request, record["chosen_entity_id"])
    return ChoiceOutcome(result=result, records=tuple(records))
```

2. In `scripts/seed_pilot.py`, immediately before `DAY_PROMPT_HEADS = (`,
   add exactly:

```python
# ----- prompt template: mention choice (TICKET-0094, H2) ------------------
# usage = "day_mention_choice". world_id = NULL. ONE call per candidate set
# the code has already narrowed (day_choice.choice_requests): the model picks
# a number and copies an excerpt; the code judges it (day_choice.judge_choice)
# and never trusts an id from the model. The evidence is what the player
# character knows about each candidate, nothing else. Positive-form only
# (abliterated gameplay model).
DAY_MENTION_CHOICE_SYSTEM_PROMPT = """\
Tu aides un jeu de rôle à comprendre de qui ou de quoi parle le joueur. Le \
joueur a écrit une déclaration pour sa journée. Un nom qu'il emploie peut \
désigner plusieurs entités du monde : on te donne la liste numérotée des \
candidats possibles, avec, pour chacun, ce que le personnage joueur sait de \
lui.

Ton travail : choisir le candidat que le joueur désigne le plus \
probablement, en t'appuyant sur les mots de la déclaration et sur ce que le \
personnage sait des candidats.

RÈGLES :
- Choisis le numéro d'un candidat de la liste, ou 0 quand aucun ne convient \
ou quand les informations ne permettent pas de trancher.
- Recopie mot pour mot un court extrait qui justifie ton choix : un passage \
de la déclaration, ou un passage de ce que le personnage sait du candidat \
choisi. Quand plusieurs candidats portent le même nom, prends l'extrait dans \
ce que le personnage sait du candidat choisi, et choisis un passage qui le \
distingue des autres.
- Explique ton choix en une phrase.

Réponds UNIQUEMENT avec un objet JSON de la forme \
{"choix": 2, "extrait": "passage recopié", "raison": "une phrase"}, en \
français, sans préambule ni commentaire.\
"""

DAY_MENTION_CHOICE_USER_TEMPLATE = """\
Déclaration du joueur : {declaration}

Nom employé : « {surface_form} » ({category})

Candidats :
{candidates}

Quel candidat le joueur désigne-t-il ?\
"""
```

   and add as the last entry of `DAY_PROMPT_HEADS`:

```python
    dict(
        id="pt-day-mention-choice",
        name="Journée — choix d'une mention par le modèle (H2)",
        usage="day_mention_choice",
        world_id=None,
        system_prompt=DAY_MENTION_CHOICE_SYSTEM_PROMPT,
        user_template=DAY_MENTION_CHOICE_USER_TEMPLATE,
        variables=["declaration", "surface_form", "category", "candidates"],
        destination="local",
    ),
```

3. In `src/world_engine/prompt_registry.py`, after the `day_plan_select`
   entry: `"day_mention_choice": PromptSpec(surface="play",
   world_scoped=True, dry_run_capable=True,
   call_sites=("src/world_engine/day_choice.py:choose",),
   default_model=_game_model),` in the file's multi-line layout.

4. In `tooling/verify/checks/prompt_registry.py`, add
   `SRC / "day_choice.py",` to `WIRED_FILES` after `SRC / "day_extract.py",`.

5. In `tooling/verify/checks/day_prompt_delivery.py`: add
   `"DAY_MENTION_CHOICE_SYSTEM_PROMPT", "DAY_MENTION_CHOICE_USER_TEMPLATE",`
   to `DAY_CONSTANTS`; add `"pt-day-mention-choice",` to
   `EXPECTED_HEAD_IDS`; `!= 9` / `expected 9` → `!= 10` / `expected 10`;
   docstring: append `TICKET-0094/BRIEF-0094-C adds the day_mention_choice
   usage (9 -> 10 heads, 16 -> 18 constants).` to the counts paragraph, R1
   `the 16 named` → `the 18 named`, R2 `exactly 9` / `the 9` → `exactly 10` /
   `the 10`; PASS message `the 16 DAY_* constants` → `the 18 DAY_* constants`.

6. Create `scripts/apply_ticket_0094_mention_choice_seed.py` as a copy of
   `scripts/apply_ticket_0077_plan_select_seed.py` with: first docstring
   paragraph `One-shot, idempotent delivery of the TICKET-0094
   `day_mention_choice` prompt head onto the live DB (BRIEF-0094-C).`; the
   second paragraph's counts `(now ten heads)`, `the nine pre-existing heads`,
   `only the tenth (`pt-day-mention-choice`)`; the refusal message naming
   this file. No other change.

7. In `tooling/verify/checks/day_choice.py`, add cases K1-K7 (no DB, no
   Ollama): monkeypatch on the imported module `day_choice.choice_requests`,
   `day_choice._load_choice_template`, `day_choice.current_prompt` (identity
   on a stub template with `system_prompt`, `user_template =
   "{declaration}|{surface_form}|{category}|{candidates}"`, `world_id=None`),
   `day_choice.effective_model` (returns the default) and
   `ollama_client.chat` (a scripted fake recording its calls); restore all
   after each case.
   - K1: no request → `records == ()`, result unchanged, loader never called.
   - K2: a request and a `None` template → `LlmParseError` containing
     `"no active prompt_template"`, chat never called.
   - K3: ambiguous request (B's J fixture), chat raises `OllamaError` then
     returns `{"choix": 1, "extrait": "a perdu une bague", "raison": "r"}` →
     record `accepted`, `attempts == 2`; result has the mention in `matched`
     with `rung == "model_choice"` and `ambiguous == ()`.
   - K4: chat returns `"bad"` twice → record `failed`, `attempts == 2`,
     `verdict_detail` non-empty, result identical to the input.
   - K5: near request accepted on attempt 1 → the mention leaves `unmatched`,
     joins `matched`; `attempts == 1`.
   - K6: attempt 1 parses to a judge refusal (`choix: 3`) → exactly one chat
     call (no retry on refusal, Y8a); record `rejected`.
   - K7: the user message contains the declaration, the surface form,
     `personne`, the rendered candidates, and ends with `"\n/no_think"`; the
     call passes `format="json"`.

8. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## THE MODEL CHOOSES, THE CODE JUDGES (TICKET-0094) -- ONE CALL PER NARROWED SET, ONE RETRY ON FAILURE (BRIEF-0094-C, no schema change)`:
   H2 and the knowing reversal of 0075 C1 / 0081 C2, Y5c, Y8a, X3b, X4a (the
   usage is a day-chain usage, so the coverage guard refuses a declaration
   without it), the number-not-id design (the model never returns an id),
   the apply script. Regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- Calling `choose` from the route: D.
- `options=` on the chat call; a per-call timeout other than the client's.
- Any bound on the number of calls (X3b).
- Retrying a judge refusal (Y8b, rejected).
- Running the apply script on prod: Nia.

## Invariants to defend

- "Prompts live in the DB; a text change ships as an apply script": seed and
  script in the same commit.
- "All templated model calls resolve through `effective_model`": R-10's
  wired-files rule.
- Secrets: the prompt receives only `render_candidates` output (B's evidence).

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `day_prompt_delivery.py` R6 classifies `day_mention_choice` as anything
  but `Raise`;
- `day_choice.py` would exceed 1000 lines or 40 functions.

ADAPT:
- `current_prompt` lives elsewhere than `prompt_store`: import it from where
  `day_plan_select.py` does, report.

REPORT-ONLY:
- the « Prompts » dry-run for `day_mention_choice` needs sample variables.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_choice.py` → `PASS:` including K1-K7.
- [ ] `prompt_registry.py`, `day_prompt_delivery.py`, `day_concordance.py`
      (R1 untouched) → pass.
- [ ] On a test DB seeded before this brief, `WORLD_ENGINE_ENV=test python
      scripts/apply_ticket_0094_mention_choice_seed.py` prints `created
      prompt_template/pt-day-mention-choice` and nine `existing`; a second
      run prints ten `existing`.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 8).
