# BRIEF 0094-B — "requests and judge, no model call"

Lot: LOT-0094-concordance-h2.md (authoritative on conflict)
Depends on: A (`near_in_surfaces`, `checks/day_choice.py`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/lore_resolve.py`: `def near_in_surfaces(` (A),
  `def rung_named_partial(`, `def normalize_surface(`, `def category_of_type(`.
- `src/world_engine/day_concordance.py:344` `def _classify(` and the
  perceiver `NameScope` construction inside `concord` quoted in R-01.
- `src/world_engine/facet_reads.py:64` `def facts_of(` (keyword-only
  `entity_id`, `facets`).
- `src/world_engine/knowledge_resolve.py:220` `def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:`.
- `src/world_engine/facets.py:78` `FACETS: dict[str, FacetSpec]`.
- `src/world_engine/day_choice.py` does not exist.

## Facts carried

#### R-01 — `concord` and the named rungs
Opened: `src/world_engine/day_concordance.py:134-167`, `344-422`
Finding [M]: `concord` builds the perceiver surfaces once
(`name_surfaces(db, world_id, NameScope("perceiver", known_fact_ids=
frozenset(resolve_levels_for_entity(db, character.id))))`), walks
`MATCHING_RUNGS` per mention, and `_classify` returns `MatchedMention` for one
candidate, `AmbiguousMention(candidate_ids=tuple(sorted(...)))` for 2+ on a
named mention, `CastMention` for 2+ on an inferred one. A mention with no hit
is `UnmatchedMention(rungs_tried, candidate_location_id)`. No partial rung, no
near names. The module docstring (lines 34-39) states the C2-partition
"never resolved by picking".
Consequence: `concord` is not modified. H2 runs on its result (`choose`,
C-07). D corrects the docstring to say the pick now happens after `concord`,
in `day_choice.py`.

#### R-02 — `ConcordanceResult` shapes
Opened: `src/world_engine/day_concordance.py:96-131`; `src/world_engine/day_extract.py:41-46`
Finding [M]: `MatchedMention(mention, entity_id, rung)`,
`AmbiguousMention(mention, candidate_ids)`, `UnmatchedMention(mention,
rungs_tried, candidate_location_id=None)`, `ConcordanceResult(matched, cast,
ambiguous, unmatched, skipped_rungs)`, all frozen;
`Mention(category, surface_form, kind, role_hint=None)`.
Consequence: `choose` returns a new `ConcordanceResult` via
`dataclasses.replace`, never mutates one.

#### R-06 — rungs, near names and the normalizer
Opened: `src/world_engine/lore_resolve.py:1-56`, `70-86`, `90-122`, `183-214`
Finding [M]: `rung_named_partial(surface_form, category, name_surfaces)` is
pure (surface tokens all ≥3 chars and a subset of the name's tokens).
`near_candidates(surface_form, world_id, db, *, scope, exclude_ids)` raises
`ValueError` unless `scope.regime == "creator"`, reads
`surfaces(db, world_id, scope)`, keeps per entity the best surface with
`difflib` ratio ≥ `NEAR_RATIO` (0.8) or a shared 3+ token, scores
half-up to 0-100, sorts `(-score, name.casefold(), entity_id)`, returns at
most `NEAR_LIMIT` (5) `NearCandidate(entity_id, name, entity_type, surface,
score)`, every category. `normalize_surface` casefolds, strips accents, drops
up to three leading article tokens, splits on whitespace and apostrophes,
joins with single spaces; punctuation stays attached to tokens.
Consequence: A extracts the loop into pure `near_in_surfaces` (C-03);
`near_candidates` keeps its guard and output exactly. B calls
`rung_named_partial` and `near_in_surfaces` on the perceiver surfaces and
filters by category itself. The judge reuses `normalize_surface`, after
stripping edge punctuation from the excerpt.

#### R-07 — checks pinning the resolver
Opened: `tooling/verify/checks/name_resolution.py:1-45`;
`tooling/verify/checks/name_index.py:17-30`; `tooling/verify/checks/lore_resolve.py:1-20`
Finding [M]: G2 checks `near_candidates` scores (Maelys→83, reine→63/59),
`exclude_ids`, and that `scope=PROSE` raises. G5 checks a generator mention
"Varn" stays unresolved outside `creator` (tokenizer). name_index R5 confines
`CREATOR`; R6 requires a `scope=` keyword on every `resolve_named` /
`near_candidates` call. lore_resolve R1 forbids `db.add(`, `.commit(`,
`chat(` in `lore_resolve.py`.
Consequence: `near_in_surfaces` takes surfaces, not a scope; R6 does not
apply to it. `day_choice.py` never names `CREATOR` and never calls
`resolve_named` or `near_candidates`. G2 and G5 must stay green unchanged.

#### R-08 — the evidence reader
Opened: `src/world_engine/facet_reads.py:1-124`; `src/world_engine/facets.py:78`;
`src/world_engine/knowledge_resolve.py:220-231`
Finding [M]: `facts_of(db, *, entity_id, facets, ...)` returns `FactRow(fact_id,
facet, aspect, content, created_at)`, content rendered through
`prose_render.fact_texts`, creator-only facts excluded in the query, ordered by
`facets` order then `created_at`. `known_facts_of` calls
`resolve_levels_for_entity(db, perceiver_id)` on every call.
`resolve_levels_for_entity(db, entity_id) -> dict[fact_id, level]` for facts
above `unaware`. `FACETS: dict[str, FacetSpec]` is the registry.
Consequence: B reads each candidate's facts with
`facts_of(db, entity_id=cid, facets=tuple(FACETS))` and filters them with ONE
`resolve_levels_for_entity(db, character.id)` call per `choice_requests` —
the same filter `known_facts_of` applies, without one level resolution per
candidate. Nothing outside the character's known set is ever assembled
(abliterated model: structural exclusion, never an instruction).

#### R-14 — the render chokepoint
Opened: `src/world_engine/facet_reads.py:95-104`
Finding [M]: `facts_of` renders `content` through `fact_texts` (one entity
query).
Consequence: fact text reaches the prompt only through `facts_of`; no raw
`Fact.text` read in `day_choice.py`.

## Contracts

#### C-04 — `Candidate` and `ChoiceRequest`
Produced by: B   Consumed by: C-05, C-06, C-07
```python
@dataclass(frozen=True)
class Candidate:
    entity_id: str
    name: str                 # entity.name
    facts: tuple[str, ...]    # rendered contents, known to the character
    fact_ids: tuple[str, ...] # same order as facts

@dataclass(frozen=True)
class ChoiceRequest:
    mention: Mention
    trigger: str              # "ambiguous" | "near"
    candidates: tuple[Candidate, ...]  # display order, numbered from 1
```

#### C-05 — `choice_requests`
Produced by: B   Consumed by: C-07
Signature: `def choice_requests(result: ConcordanceResult, character:
Character, db: Session) -> tuple[ChoiceRequest, ...]`.
Behaviour:
1. `ambiguous`: one request per `AmbiguousMention`, candidates in
   `candidate_ids` order.
2. `near`: for each `UnmatchedMention` with `mention.kind == "named"`: ids
   from `rung_named_partial(surface, category, surfaces)` (sorted), then
   ids from `near_in_surfaces(surface, surfaces)` whose
   `category_of_type(entity_type) == category` in their order, duplicates
   dropped, first `MAX_CANDIDATES` (8) kept; a request only if non-empty.
   `surfaces` is built once, with the exact `NameScope("perceiver", ...)` of
   R-01.
3. Evidence: `known = resolve_levels_for_entity(db, character.id)` once; per
   candidate `facts_of(db, entity_id=cid, facets=tuple(FACETS))` filtered to
   `fact_id in known`, first `MAX_FACTS_PER_CANDIDATE` (12) kept; `name` from
   `db.get(Entity, cid).name` (a missing entity is dropped).
Order: all `ambiguous` requests, then all `near`, each in result order.
Empty result → `()`.

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

## Context

H2's code half: narrow the candidates, gather what the character knows about
each, render them, parse and judge an answer. No model is called in this
brief; C adds the call. Everything here is testable without Ollama.

## Scope IN

1. Create `src/world_engine/day_choice.py` with exactly this content:

```python
"""Model choice among narrowed candidates (TICKET-0094, H2).

The code narrows the candidates (`choice_requests`), the model chooses one
and cites an excerpt (`choose`, BRIEF-0094-C), the code judges the choice
(`judge_choice`). This reopens 0075 C1 / 0081 C2 knowingly: a pick now
happens, but only here, only among entities the concordance or the
character's own name surfaces produced, and only when the judge accepts it.
Every call is recorded (`writes.write_day_mention_choices`).

Evidence is what the character knows about each candidate, read through
`facet_reads.facts_of` (creator-only facts excluded by construction) and
filtered by one `resolve_levels_for_entity` call. The gameplay model is
abliterated: nothing the character does not know is ever assembled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from . import llm_parse
from .day_concordance import ConcordanceResult
from .day_extract import Mention
from .facet_reads import facts_of
from .facets import FACETS
from .knowledge_resolve import resolve_levels_for_entity
from .lore_resolve import category_of_type, near_in_surfaces, normalize_surface, rung_named_partial
from .models import Character, Entity
from .name_index import NameScope, surfaces as name_surfaces

MAX_CANDIDATES = 8
MAX_FACTS_PER_CANDIDATE = 12
MODEL_CHOICE_RUNG = "model_choice"

_EXCERPT_EDGE = " \t\n\"'«»“”.,;:!?…"
_CATEGORY_LABEL_FR = {"person": "personne", "place": "lieu", "faction": "faction"}


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    name: str
    facts: tuple[str, ...]
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class ChoiceRequest:
    mention: Mention
    trigger: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class ChoiceVerdict:
    verdict: str
    entity_id: Optional[str]
    excerpt: Optional[str]
    reason: Optional[str]
    detail: Optional[str]


def _near_ids(mention: Mention, surfaces: tuple) -> list[str]:
    """C-05 step 2: partial ids (sorted), then near ids in the mention's
    category, duplicates dropped, first MAX_CANDIDATES kept."""
    ids: list[str] = list(rung_named_partial(mention.surface_form, mention.category, surfaces) or [])
    for near in near_in_surfaces(mention.surface_form, surfaces):
        if category_of_type(near.entity_type) == mention.category and near.entity_id not in ids:
            ids.append(near.entity_id)
    return ids[:MAX_CANDIDATES]


def _candidates(ids: list[str], known: dict[str, str], db: Session) -> tuple[Candidate, ...]:
    """C-05 step 3: evidence per candidate, known facts only."""
    out: list[Candidate] = []
    for entity_id in ids:
        entity = db.get(Entity, entity_id)
        if entity is None:
            continue
        rows = [r for r in facts_of(db, entity_id=entity_id, facets=tuple(FACETS)) if r.fact_id in known]
        rows = rows[:MAX_FACTS_PER_CANDIDATE]
        out.append(Candidate(
            entity_id=entity_id, name=entity.name,
            facts=tuple(r.content for r in rows), fact_ids=tuple(r.fact_id for r in rows),
        ))
    return tuple(out)


def choice_requests(result: ConcordanceResult, character: Character, db: Session) -> tuple[ChoiceRequest, ...]:
    """C-05: one request per named ambiguity, then one per named unmatched
    mention with partial or near candidates among the character's own name
    surfaces (Y2b). Cast and inferred mentions never produce a request."""
    near_mentions = [um.mention for um in result.unmatched if um.mention.kind == "named"]
    if not result.ambiguous and not near_mentions:
        return ()
    known = resolve_levels_for_entity(db, character.id)
    requests: list[ChoiceRequest] = []
    for am in result.ambiguous:
        candidates = _candidates(list(am.candidate_ids), known, db)
        if candidates:
            requests.append(ChoiceRequest(mention=am.mention, trigger="ambiguous", candidates=candidates))
    if near_mentions:
        surfaces = name_surfaces(db, character.world_id, NameScope(
            "perceiver", known_fact_ids=frozenset(known),
        ))
        for mention in near_mentions:
            candidates = _candidates(_near_ids(mention, surfaces), known, db)
            if candidates:
                requests.append(ChoiceRequest(mention=mention, trigger="near", candidates=candidates))
    return tuple(requests)


def render_candidates(request: ChoiceRequest) -> str:
    """C-06: the numbered list the model reads."""
    blocks: list[str] = []
    for number, candidate in enumerate(request.candidates, start=1):
        lines = [f"{number}. {candidate.name}"]
        if candidate.facts:
            lines.append("   Ce que le personnage sait :")
            lines.extend(f"   - {fact}" for fact in candidate.facts)
        else:
            lines.append("   Le personnage ne sait rien de plus sur lui.")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def category_label(category: str) -> str:
    return _CATEGORY_LABEL_FR[category]


def parse_answer(raw: str) -> dict:
    """C-06: a technical failure (Y8a) raises LlmParseError."""
    obj = llm_parse.extract_object(raw)
    choix = obj.get("choix")
    if not isinstance(choix, int) or isinstance(choix, bool):
        raise llm_parse.LlmParseError("day_choice: choix missing or ill-typed")
    for key in ("extrait", "raison"):
        if not isinstance(obj.get(key), str):
            raise llm_parse.LlmParseError(f"day_choice: {key} missing or ill-typed")
    return {"choix": choix, "extrait": obj["extrait"], "raison": obj["raison"]}


def _joined(facts: tuple[str, ...]) -> str:
    return normalize_surface(" ".join(facts))


def judge_choice(request: ChoiceRequest, answer: dict, declaration: str) -> ChoiceVerdict:
    """C-06: pure. The model's number must be on the list; its excerpt must
    be found verbatim after normalization — for an ambiguity, in the chosen
    candidate's facts and in no other candidate's; for a near name, in the
    declaration or the chosen candidate's facts (X2b)."""
    excerpt = answer["extrait"].strip() or None
    reason = answer["raison"].strip() or None
    choix = answer["choix"]
    if choix == 0:
        return ChoiceVerdict("declined", None, excerpt, reason, None)
    if not 1 <= choix <= len(request.candidates):
        return ChoiceVerdict("rejected", None, excerpt, reason, "candidate out of range")
    chosen = request.candidates[choix - 1]
    normalized = normalize_surface(answer["extrait"].strip(_EXCERPT_EDGE))
    if len(normalized) < 3:
        return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason, "excerpt too short")
    in_chosen = normalized in _joined(chosen.facts)
    if request.trigger == "ambiguous":
        if not in_chosen:
            return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason,
                                 "excerpt not in the chosen candidate's facts")
        others = [c for c in request.candidates if c.entity_id != chosen.entity_id]
        if any(normalized in _joined(c.facts) for c in others):
            return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason,
                                 "excerpt does not single out the chosen candidate")
    elif not (in_chosen or normalized in normalize_surface(declaration)):
        return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason, "excerpt not found")
    return ChoiceVerdict("accepted", chosen.entity_id, excerpt, reason, None)


def record_of(request: ChoiceRequest, verdict: ChoiceVerdict, attempts: int) -> dict:
    """The choice-record family shape (C-02)."""
    return {
        "category": request.mention.category, "surface_form": request.mention.surface_form,
        "trigger": request.trigger,
        "candidate_ids": [c.entity_id for c in request.candidates],
        "evidence_fact_ids": [fid for c in request.candidates for fid in c.fact_ids],
        "verdict": verdict.verdict, "chosen_entity_id": verdict.entity_id if verdict.verdict != "declined" else None,
        "excerpt": verdict.excerpt, "reason": verdict.reason, "verdict_detail": verdict.detail,
        "attempts": attempts,
    }
```

2. In `tooling/verify/checks/day_choice.py`, add (called from `main()`):
   - **J (judge, pure)** — one case per row of the lot's table (b2), on the
     two requests below, declaration `"Je vais voir la Comtesse pour lui
     rendre sa bague. Et Maelys."`:
     `ambiguous`: candidates `a` "Maelis" facts `("Elle a perdu une bague au
     marché de Vesk.",)` ids `("f1",)`, `b` "Ilune" facts `("Elle règne sur
     le val d'Orre.",)` ids `("f2",)`; `near`: candidate `a` "Maelis", no
     facts.
     - J1 `{"choix": 0, ...}` → `declined`, entity None (both triggers);
     - J2 `choix: 3` → `rejected`, `"candidate out of range"`;
     - J3 `extrait: "Va"` → `rejected`, `"excerpt too short"`;
     - J4 ambiguous `choix: 1, extrait: "Maelys"` → `rejected`, `"excerpt not
       in the chosen candidate's facts"`; near `choix: 1, extrait: "Maelys"`
       → `accepted`, entity `a`;
     - J5 ambiguous `choix: 1, extrait: "Elle"` → `rejected`, `"excerpt does
       not single out the chosen candidate"`;
     - J6 ambiguous `choix: 1, extrait: "« a perdu une bague. »"` →
       `accepted` (edge punctuation stripped), entity `a`;
     - J7 ambiguous `choix: 2, extrait: "a perdu une bague"` → `rejected`,
       not in chosen facts;
     - J8 near `choix: 1, extrait: "Varek"` → `rejected`, `"excerpt not
       found"`.
   - **P (parse)** — `'{"choix": 1, "extrait": "a", "raison": "b"}'` returns
     the three keys; `choix: true`, a missing `extrait`, and `"nope"` each
     raise `LlmParseError`.
   - **Rd (render)** — the near request renders exactly
     `"1. Maelis\n   Le personnage ne sait rien de plus sur lui."`; the
     ambiguous one contains `"   Ce que le personnage sait :"` and
     `"   - Elle a perdu une bague au marché de Vesk."`.
   - **Rc (record)** — `record_of` on a declined verdict has
     `chosen_entity_id is None`; on J6's verdict with `attempts=1` it has the
     eleven C-02 keys and `evidence_fact_ids == ["f1", "f2"]`.
   - **Q (requests, fixture)** — temp SQLite; `_fresh_engine` and `_world`
     copied from `checks/identity_tokens.py:108-134`. A world with a PC
     `Mini` and NPCs `Maelis`, `Ilune` (entities from `_world`'s helper;
     `resolve_levels_for_entity` needs no `Character` row for this). Three
     `histoire` facts on Maelis through
     `writes.facets.add_entity_fact(session, entity_id=..., facet="histoire",
     content=..., created_by="check", scope=ScopeChoice(...))`:
     « Elle a perdu une bague. » (`ScopeChoice("world")`, known),
     « Elle cache un poignard. » (`ScopeChoice("none")`, unknown), and
     « Secret de créatrice. » (`ScopeChoice("world")`) made creator-only with
     `writes.knowledge.write_knowledge(session, entity_id=maelis.id,
     fact_id=..., subject="creator_meta", level="unaware", is_secret=True,
     changed_by="check")` as `checks/name_index.py::_make_creator_only`
     does. (Measured on a prototype: only the first reaches the PC.) The
     `character` argument is any object with `.id` and `.world_id` of the PC.
     - Q1: an `AmbiguousMention(candidate_ids=(maelis, ilune))` yields one
       `ambiguous` request whose Maelis candidate carries exactly the known
       fact (not the unknown, not the creator-only one).
     - Q2: an unmatched named person "Maelys" yields one `near` request with
       candidate Maelis; an unmatched named place "Maelys" yields none
       (category filter).
     - Q3: an unmatched INFERRED person yields no request; a `cast` yields
       none.
     - Q4: an empty `ConcordanceResult` yields `()`.

3. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## H2 NARROWS AND JUDGES IN CODE (TICKET-0094) -- THE MODEL WILL ONLY CHOOSE AMONG WHAT THE CHARACTER CAN NAME (BRIEF-0094-B, no schema change)`:
   Y2b, Y4b, X2b, the two constants and their reason (quality first, X3b,
   while keeping prompts readable), the judge table, the structural secrecy
   argument (R-08). Regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- Any `ollama_client` import or `chat(` in `day_choice.py`: C.
- The prompt, the registry entry, the seed: C.
- The route: D.
- Showing the matched appellation next to a candidate's name (drafting
  judgment; K1).
- Changing `near_candidates`, `resolve_named`, `concord`.

## Invariants to defend

- Secrets structurally excluded: evidence only through `facts_of` (no
  `include_creator_only`) filtered by the PC's resolved levels; the
  perceiver `NameScope` is built exactly as `concord` builds it; never
  `CREATOR` (name_index R5).
- "The resolver never authors" (C1 as it stands): nothing here writes; no
  `db.add(`, no `.commit(`.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `import_cycle.py` reports a cycle through `day_choice`;
- a Q case shows an unknown or creator-only fact in a candidate's evidence.

ADAPT:
- the knowledge-row builder used by `checks/name_index.py` has another name
  or signature: use what that check uses, report.
- `Character` construction needs a field `day_concordance_golden.py` sets:
  set it the same way, report.

REPORT-ONLY:
- `resolve_levels_for_entity` cost on a large world (it scans every fact of
  the world once per plan with requests).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_choice.py` → `PASS:` with N1-N3,
      J1-J8, P, Rd, Rc, Q1-Q4 executed.
- [ ] `python -c "import sys; sys.path.insert(0,'src'); import world_engine.day_choice"`
      succeeds with `WORLD_ENGINE_ENV=test`; `import_cycle.py` passes.
- [ ] `grep -n "chat(\|db.add(\|\.commit(\|CREATOR" src/world_engine/day_choice.py` returns nothing.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 3).
