<!-- slug: question-to-plan-and-disambiguation -->
# BRIEF — Step "Question to plan, and the disambiguation round-trip"

> **Amended.** Corrections measured against `main`: the authoring prompt
> convention is `world_scoped=False`, not `True` (item 2); binding validation
> belongs to `/api/lore/resolve` only, since `/ask` receives no bindings
> (item 6); candidate location is reached through
> `character.current_location_id` (item 5); the selector list given to the
> model is now derived from `SELECTORS` under a check rather than retyped in
> prompt text (item 3); a non-`answered` verdict from `/resolve` is named as
> legitimate (item 6).

## Context

BRIEF-0085-b built the deterministic half: a plan goes in, rows and a verdict
come out. This step puts the model in front of it — the only place in TICKET-0085
where a model reads the creator's question — and closes the ambiguity loop the
ticket requires. Output is still structured: no prose is produced here.

## RECON required before execution

Report-only. Report and stop if a stop condition fires.

- **R-a** Confirm `lore_query.LorePlan`, `PlanMention`, `PlanCall`,
  `validate_plan` and `execute_plan` exist with the field names BRIEF-0085-b
  specified, and that `LoreResult.verdict` is the closed five-value set.
  *Stop condition:* the verdict set differs — this step's route contract is
  built on it.
- **R-b** Record how an existing authoring prompt is seeded and loaded: the
  `prompt_template` row, the `usage` string, the `_load_*_template` helper
  idiom, and the `PROMPT_REGISTRY` entry's `call_sites` format. Name one
  concrete existing example end to end. *Report;* this step copies it exactly.
- **R-c** Confirm the convention this amendment rests on: every existing
  `surface="authoring"` usage in `PROMPT_REGISTRY` carries
  `world_scoped=False`, and `cockpit/crud/prompts.py::_effective_prompt_row`
  treats `world_scoped=False` as taking the global row.
  *Stop condition:* any authoring usage carries `world_scoped=True` — the
  convention is not what item 2 asserts, and it must be re-decided, not guessed.
- **R-d** Record how `prompt_coverage` decides a usage is covered, and what
  `verify/checks/prompt_version.py` asserts about a new usage.
  *Stop condition:* a new usage requires a schema-version bump — the ticket
  declares `schema_version_touched: none`, so that must be escalated first.
- **R-e** Record every existing caller of `llm_parse.extract_object` and how it
  handles `LlmParseError`. *Report* the prevailing idiom.
- **R-f** Confirm what `verify/checks/llm_parse_chokepoint.py` greps for.
  *Report;* this step satisfies it without editing it.
- **R-g** Confirm `Character.current_location_id` is a nullable FK and record
  the exact join from it to the location's display name.
  *Stop condition:* the name does not live on the location's `entity` row —
  item 5 then names the wrong path and must be corrected before writing it.
- **R-h** Record whether any existing route returns client-held echoed state.
  *Report.* If none does, this step introduces the first and says so in the
  ARCHITECTURE_DECISIONS entry.

## Scope IN

1. **New module `src/world_engine/lore_plan.py`.** Docstring states, verbatim:

   > The model reads the question and names selectors. It never receives canon
   > rows here, never writes a query, and never chooses between two entities
   > that share a name. Its output is parsed through `llm_parse` and validated
   > against the whitelist before a single row is read; anything it names that
   > is not in `SELECTORS` is a rejected plan, not an improvised query.

2. **New prompt usage `lore_question_to_plan`**, seeded as a `prompt_template`
   row following the idiom R-b reports, registered in `PROMPT_REGISTRY` with
   `surface="authoring"`, **`world_scoped=False`**, `dry_run_capable=True`,
   `default_model=_author_model`, and `call_sites` naming the function in
   `lore_plan.py`. Resolved through `effective_model(template, default)` — no
   direct `DEFAULT_MODEL` reference.

   `world_scoped=False` is the measured authoring convention, not a preference:
   the planner prompt contains no world content, so a per-world row for it would
   be a row nobody has a reason to differentiate.

3. **Prompt content, with the selector list derived rather than retyped.**
   `lore_plan.py` holds `_SELECTOR_DESCRIPTIONS: dict[str, str]` — one line per
   selector naming its argument kinds — and the prompt builder renders the list
   from it. A G1 check (item 8, R8) asserts its key set equals `SELECTORS`, so a
   selector added in a later ticket without a description fails the check
   instead of silently becoming invisible to the planner.

   The prompt is given: the question; the rendered selector list; and the three
   mention categories, which are exactly `place`, `person`, `faction` — the
   vocabulary `_CATEGORY_ENTITY_TYPE` maps to `location`, `character`,
   `faction`. There is no fourth category.

   It is given NO canon rows, no entity names, no world description. It returns
   only JSON of the shape:

   ```
   {"mentions": [{"ref": "m1", "surface_form": "...", "category": "person"}],
    "calls": [{"selector": "entity_dossier", "args": ["m1", "$world"]}]}
   ```

   The prompt states verbatim:

   > If the question needs information no listed selector can retrieve, return
   > the selector name you would need in `"calls"` anyway. Do not substitute a
   > selector that is listed for one that is not. Do not invent entity ids. Do
   > not answer the question.

   That last instruction is what makes empty message 3 possible: a model that
   politely downgrades to a selector it *does* have would make an unanswerable
   question look answered.

4. **`draft_plan(question: str, world_id: str, db: Session) -> LorePlan`** —
   builds the prompt, calls the model through `effective_model`, parses with
   `llm_parse.extract_object`, maps the JSON into `LorePlan`. `LlmParseError`
   propagates; it is not swallowed into an empty plan. A `category` outside the
   three literals is a rejected plan, never a coerced one.

5. **New module `src/world_engine/lore_candidates.py`** — or a function in
   `lore_plan.py` if R-b's idiom makes a module of under twenty lines absurd —
   holding `describe_candidates(candidate_ids, db) -> list[dict]`, returning for
   each id: `id`, `name`, `type`, `description`, `location_name`.
   `location_name` follows the join R-g confirms, from
   `character.current_location_id` to the location's display name, and is `None`
   for any candidate that is not a character or has no current location. This is
   the enrichment RECON-0085-a's F5 found missing from `AmbiguousMention`. It
   reads `entity`, `character`, and the location's `entity` row — no
   `knowledge`, no `relation`, no `faction_membership`.

6. **New route module `src/world_engine/cockpit/routes/lore.py`**, an
   `APIRouter` included in `cockpit/app.py`:
   - `POST /api/lore/ask` — body `{question, world_id}`. Calls `draft_plan`,
     `validate_plan`, `execute_plan`. Returns
     `{verdict, rows, trace, plan, candidates}`; `plan` is the serialized
     `LorePlan`, `candidates` is populated only on verdict `ambiguous_mention`.
   - `POST /api/lore/resolve` — body `{plan, bindings, world_id}`, `bindings`
     mapping a mention `ref` to a chosen `entity_id`. It does NOT call the
     model: it deserializes the plan, applies the bindings as pre-resolved
     mentions, and calls `execute_plan`. This is the guarantee that
     disambiguation cannot shift the question.
   - **Binding validation lives on `/api/lore/resolve` only.** Each bound
     `entity_id` must be an active entity in `world_id` whose `type` matches the
     `_CATEGORY_ENTITY_TYPE` mapping of the bound mention's category, and each
     `ref` must exist in the submitted plan. A client echoing a plan back is
     untrusted input; the ids are re-checked, not trusted because the server
     produced them a moment ago. `/api/lore/ask` receives no bindings and
     performs no such validation.
   - **A non-`answered` verdict from `/resolve` is legitimate.** A question with
     one ambiguous mention and one unmatched mention returns `ambiguous_mention`
     first, by BRIEF-0085-b's precedence, then `unknown_entity` after binding.
     That is a correct second round, not an error, and nothing here may treat it
     as one.

7. **Multiple ambiguities resolve in one round.** `candidates` carries every
   ambiguous mention's set, keyed by ref, and `/api/lore/resolve` accepts all
   bindings at once. There is no one-at-a-time loop.

8. **Extend `tooling/verify/checks/lore_isolation.py`** with:
   - R4: `lore_selectors.py` and `lore_query.py` still contain no `chat(` — the
     model lives in `lore_plan.py` only.
   - R5: `lore_plan.py` contains no `select(` against `Knowledge`, `Relation`,
     `NpcGoal` or `FactionMembership` — the planner never sees canon content.
   - R6: `cockpit/routes/lore.py` contains no `chat(` and no `select(` — the
     route orchestrates and validates, matching the `routes/observation.py`
     doctrine.
   - R7: the `/api/lore/resolve` handler's AST contains no call to `draft_plan`.
   - R8: the key set of `_SELECTOR_DESCRIPTIONS` equals `SELECTORS`.
   - R9: the category literals in `lore_plan.py` equal the key set of
     `_CATEGORY_ENTITY_TYPE`.

## Scope OUT

- **No prose, no renderer, no template fallback.** BRIEF-0085-d. If you find
  yourself formatting a sentence, stop.
- **No frontend.** BRIEF-0085-e. Test with `curl` or the FastAPI docs page.
- **No server-side plan storage.** No table, no cache, no session dict. The plan
  is client-held — a dict keyed by request id "just for convenience" is exactly
  what was decided against.
- **No re-parsing on `/api/lore/resolve`.** A "the question might be better
  understood now" improvement breaks the ticket's guarantee.
- **No fourth mention category**, and no widening of `_CATEGORY_ENTITY_TYPE` —
  it is shared with the day chain, and widening it here changes what player
  declarations resolve to.
- **No third selector.**
- **No casting, no heuristic pick, no candidate ordering that implies a
  default.** Candidates are sorted by name; the creator chooses.
- **No retry loop on `LlmParseError`.** A silent retry hides a prompt problem.
- **No streaming.** `chat`, not `chat_stream`.
- **No secret filtering, no viewpoint parameter.**
- **No write path, no `ProposedMutation`.**

## Invariants to defend

- **All templated model calls resolve through `effective_model`.** Directly
  threatened: this step adds the chantier's first model call.
- **Model JSON is parsed only through `llm_parse`.** Directly threatened.
  `json.loads` on model output anywhere here fails the chokepoint check.
- **Injected context depends on the active role, never the account.** The
  planner gets no canon; R5 is the guard. The reason is not tidiness: a planner
  that sees entity names starts guessing ids.
- **Secrets are structurally excluded from every assembled context.** The
  planner prompt contains no canon at all — the strongest form of this.
  `describe_candidates` is the one place this step reads canon, and it is
  confined to name, type, description and location: nothing carrying
  `is_secret` is reachable from it.
- **Creator control is structural.** Read-only; no write appears.

## Done means

- [ ] `tooling/verify/checks/lore_isolation.py` exits 0 with R4-R9
- [ ] `tooling/verify/checks/lore_selectors.py` exits 0
- [ ] `tooling/verify/checks/llm_parse_chokepoint.py` exits 0, unedited
- [ ] `prompt_version.py` and `prompt_coverage` pass with the new usage
- [ ] `corpus_gate.py`, `import_cycle.py`, `function_length.py` exit 0
- [ ] The `PROMPT_REGISTRY` entry for `lore_question_to_plan` reads
      `world_scoped=False`
- [ ] `POST /api/lore/ask` with "Est-ce que <NPC A> connaît <NPC B> ?" returns
      `answered` with dossier rows for both and a `plan` naming two mentions
- [ ] `POST /api/lore/ask` with "Quelles sont les factions du monde ?" returns
      `answered` with zero mentions resolved
- [ ] A question needing an unbuilt selector returns `unsupported_selector`
      naming it
- [ ] A nonexistent person returns `unknown_entity` with the surface form
- [ ] A name matching two active entities returns `ambiguous_mention` with
      `candidates` carrying name, type, description and `location_name`
- [ ] A candidate with no current location returns `location_name: null` rather
      than failing
- [ ] `POST /api/lore/resolve` with that plan and a binding returns `answered`
      for the chosen entity, and the server log shows no model call
- [ ] `POST /api/lore/resolve` with a binding id from another world is rejected
- [ ] `POST /api/lore/resolve` with a binding whose entity type does not match
      the mention's category is rejected
- [ ] `/review-step` then `/close-step` run clean

## Docs to update

`tooling/standards/ARCHITECTURE_DECISIONS.md`: the client-held-plan decision with
its reason (the surface is stateless, matching the non-persisted trace), and the
no-re-parse guarantee. No schema changelog entry unless R-d finds that seeding a
prompt usage is schema-touching — in which case stop and escalate rather than
bumping the version inside this step.
