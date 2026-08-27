# BRIEF — Step "intent and arbitration engine"

## Context

TICKET-0051 decisions C3, D1+D2+D3, O1. This is the heart of the ticket: the
mechanism by which every present NPC gets an opportunity to act each beat, and
the code — not a prompt — decides who speaks.

Today one MJ call picks a single NPC, and the prompt itself pushes the choice
toward relation extremes. `scripts/seed_pilot.py:1426+` says, verbatim:

```
- Un PNJ à relation basse (intensité < 40) est plus susceptible d'intervenir
par hostilité ou méfiance.
- Un PNJ à relation haute (intensité > 70) peut réagir par implication
affective ou intérêt.
```

That is the U-curve: an NPC at 20 or at 85 always outranks an NPC at 50. The
arbitration is invisible, unlogged, and unadjustable.

This brief ships the engine as PURE FUNCTIONS plus one model call per NPC. It
does NOT ship the loop that drives them (BRIEF-0051-e).

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate.

1. **Prompt template registration** — how `pt-npc-initiative-act` and
   `pt-mj-initiative` are seeded (`scripts/seed_pilot.py:1684`, `:1831`) and
   fetched (`play_initiative.py:369`, `:386`). Report the exact template
   `id` convention, and whether `PromptTemplate` carries a `version` column
   and how it increments — BRIEF-0051-a's `observation_run_template` pins it.
2. **Model call idiom** — `ollama_client.chat` (`ollama_client.py:88`,
   params `messages, model, host, timeout, format, options`). Report whether
   `format="json"` is used anywhere today and with what result.
3. **JSON extraction** — `llm_parse.extract_object` (`llm_parse.py:44`) vs
   `extract_object_or_none` (`:63`). Report which one distinguishes a parse
   failure from a valid negative answer; the engine needs that distinction to
   set `call_status` correctly.
4. **Model selection** — `prompt_registry.effective_model`
   (`prompt_registry.py:40`) and `_game_model` (`:45`).
5. **NPC->NPC relations** — the `Relation` query shape needed for a set of
   NPCs among themselves. `_initiative_candidate_data`
   (`play_initiative.py:415-421`) is the player-keyed version and is NOT
   reusable; report what an NPC-to-NPC variant costs.
6. **Goals** — how an NPC's active goals are read (needed for the intent
   prompt, and by BRIEF-0051-e's readiness gate).
7. **Socle columns** — confirm `observation_intent` from BRIEF-0051-a carries
   `propensity`, `cooldown_active`, `debt_score`, `final_score`, `selected`,
   `call_status`, `latency_ms`, `raw_response`, and NO `not_selected_reason`.

## Scope IN

### 1. New module `src/world_engine/observation_engine.py`

R7 domain-prefixed. Two responsibilities, kept separate.

**a. The intent call — one per present NPC, per beat.**

```python
def request_intent(
    npc_id: str,
    audience_ids: list[str],
    transcript: str,
    location_id: str,
    template: PromptTemplate,
    db: Session,
    model: str,
    host: str,
) -> IntentResult
```

`IntentResult` is a dataclass: `act: bool`, `urgency: int | None`,
`target_id: str | None`, `why: str | None`, `call_status: str`,
`latency_ms: int`, `raw_response: str`.

- Context is assembled with `assemble_npc_context(..., audience_ids=...)` from
  BRIEF-0051-b, so the intent prompt sees a correctly floored disclosure set.
- `call_status` is one of `ok` / `parse_error` / `timeout` / `error`, and is
  the ONLY thing distinguishing a declined intent from a failed call. A
  `parse_error` yields `act=False` AND `call_status='parse_error'` — never a
  silent `False`. This is the defect the ticket exists to fix
  (`play_initiative.py:508-510` currently collapses all three).
- **Name resolution stays in code.** The model returns a target NAME from the
  supplied list; `request_intent` resolves it to an id and returns `None` if
  it does not resolve exactly. The model never emits an entity id.
- `latency_ms` is measured around the call.

**b. Arbitration — pure, no I/O, no model.**

```python
def arbitrate(
    intents: list[IntentResult],
    npc_ids: list[str],
    last_actor_id: str | None,
    acted_counts: dict[str, int],
    beats_elapsed: int,
    cooldown_beats: int,
    debt_weight: float,
    propensity_mode: str,
) -> ArbitrationResult
```

Returns, per candidate: `propensity`, `cooldown_active`, `debt_score`,
`final_score`, `selected` — the exact component set BRIEF-0051-a stores, so
the decision is reconstructible rather than merely reported.

Rules:

- **D1 / O1 — propensity.** `propensity_mode='flat'` (the DEFAULT) sets
  `propensity = 1.0` for every candidate: relation intensity plays NO part.
  `propensity_mode='relation_weighted'` is implemented as the second mode:
  `1.0 + k * (abs(intensity_toward_last_actor - 50) / 50)` with `k` capped so
  the multiplier never exceeds 1.5. Both modes are code-side; NEITHER is a
  prompt instruction.
- **D2 — cooldown.** `cooldown_active = (npc_id == last_actor_id and
  beats_since_last_act < cooldown_beats)`. A cooling candidate is excluded
  from selection UNLESS every other candidate declined, in which case it may
  be selected and `cooldown_active` still records True. The exclusion is
  soft-floor, never a hard drop that would produce a false `silence`.
- **D3 — speaking debt.** `debt_score = debt_weight * (expected_share -
  actual_share)` where `expected_share = beats_elapsed / len(npc_ids)` and
  `actual_share = acted_counts[npc_id]`. Positive means under-served.
- **Final.** `final_score = urgency * propensity + debt_score`, with
  `cooldown_active` candidates ranked last. Highest wins. Ties break on lowest
  `acted_counts`, then on stable `npc_ids` order. **No RNG anywhere** (D4 not
  taken).
- Candidates with `act=False` are never selected and get `final_score = 0.0`.
- If no candidate has `act=True`, `selected` is None for all — the caller
  (BRIEF-0051-e) turns that into `outcome='silence'` or `'degraded'` based on
  `call_status`.

### 2. New prompt template `pt-observation-intent`

Seeded like the existing pair. Its job is NARROW: given who you are, where you
are, and what has just been said, do you have something to say right now and
how much does it press.

**Hard constraints on the prompt body:**

- **No intensity thresholds.** No "< 40", no "> 70", no relation-magnitude
  guidance of any kind. That reasoning is now code (D1). Reproducing it here
  would double-count the bias the ticket is removing.
- **No selection language.** The model answers only for ITSELF. It is never
  asked to choose among NPCs, never shown the other NPCs' intents, and never
  told one NPC acts per beat.
- Returns strictly:
  `{"act": false}` or
  `{"act": true, "urgency": <0-100>, "target": "<exact name or empty>", "why": "<one short sentence>"}`
- Carries the existing "invent nothing" discipline, matching
  `NPC_DIALOGUE_SYSTEM_PROMPT` (`seed_pilot.py:1517+`).

Prompt body in French, matching the other game-facing templates. Creator-owned
and editable in the Prompts tab like every other.

### 3. Reuse for the act itself

When a candidate is selected, the spoken line is produced with the EXISTING
`pt-npc-initiative-act` template (`seed_pilot.py:1517`), not a new one. Report
in the step result whether its `[MODE INITIATIVE]` framing reads correctly with
no player present; if it does not, escalate rather than editing it here.

## Scope OUT

- **The loop.** No beat sequencing, no stop condition, no run lifecycle, no
  writes to any `observation_*` table. `arbitrate` is pure; `request_intent`
  returns a value. BRIEF-0051-e persists them.
- **`play_initiative.py`.** Not refactored, not generalized, not shared. The
  played-turn initiative vote keeps working exactly as today. If a shared
  abstraction looks attractive, REPORT it; do not build it.
- **`pt-mj-initiative`.** Untouched, including its intensity lines — it still
  governs played turns. Removing D1's bias from the PLAYED path is a separate
  future ticket, and conflating the two would change the live game inside an
  observation ticket.
- **MJ narration.** The `mj_narration` toggle is the runner's concern.
- **The readiness gate.** BRIEF-0051-e.
- **Proposal production.** BRIEF-0051-e, via the BRIEF-0051-c seam.
- **Any cockpit surface.** BRIEF-0051-f.
- **Metrics.** BRIEF-0051-g.
- **D4** stochastic weighting. Not taken; no RNG.

## Invariants to defend

- **Model proposes, code judges.** The model reports its OWN intent; it never
  ranks, never selects, never sees a rival's intent. Every selection input is
  a number computed in Python.
- **Exclusion is structural, never instructional.** Disclosure floor comes from
  BRIEF-0051-b's `audience_ids`, not from prompt wording.
- **Model never resolves ids.** Names in, ids resolved in code, unresolved ->
  `None`.
- **Fail-closed over advisory.** A parse failure is a recorded `parse_error`,
  never an implicit decline.
- **Silence is a logged outcome.** `arbitrate` returning no selection is a
  first-class result carrying every component score, not an empty return.
- **Reconstructible judgment.** Components stored, reason derived. If a
  `not_selected_reason` string appears anywhere in this module, the brief has
  been misread.

## Done means

- [ ] `arbitrate` is importable and callable with NO database and NO model —
      demonstrate in the step result with a hand-built `intents` list.
- [ ] With `propensity_mode='flat'`, two candidates of equal urgency and equal
      `acted_counts` but intensities 15 and 85 produce IDENTICAL
      `final_score`. This is the ticket's core claim; show the numbers.
- [ ] A candidate that acted on the previous beat has `cooldown_active=True`
      and is not selected when any other candidate has `act=True`.
- [ ] With all candidates `act=False`, `arbitrate` returns no selection AND a
      full component row per candidate.
- [ ] A forced JSON parse failure yields `act=False` with
      `call_status='parse_error'`, distinguishable from a genuine decline.
- [ ] `grep -n "40\|70\|intensit" <pt-observation-intent body>` shows no
      threshold guidance.
- [ ] `grep -rn "not_selected_reason" src/` returns nothing.
- [ ] `grep -rn "random\|shuffle\|choice" src/world_engine/observation_engine.py`
      returns nothing.
- [ ] `observation_engine.py` within 40 functions / 1000 lines; full-tree
      verify passes.

## Docs to update

`world-engine-schema.md`: the new `pt-observation-intent` row in the prompt
template inventory. `ARCHITECTURE_DECISIONS.md`: subsection recording C3
(per-NPC intent, code-side selection), D1/O1 (the U-curve moved out of the
prompt, `flat` as default and WHY — measuring the bias before damping it),
D2, D3, the explicit rejection of D4, and the parse-error/decline distinction
with its `play_initiative.py:508-510` origin. `DECISIONS_INDEX.md` entry.
