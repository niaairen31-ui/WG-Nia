<!-- slug: renderer-and-deterministic-fallback -->
# BRIEF — Step "Prose renderer and deterministic fallback"

> **Amended, second revision.** Three corrections, all from findings that fired
> against the first revision:
> - **The section contract.** `world_factions` rows carry no `"section"` key,
>   so grouping by section was undefined for the very question this brief
>   tests. Item 2 now establishes the contract and item 3 authorizes the narrow
>   amendment that makes it true, in its own commit.
> - **`silent_canon` has two forms.** The original wording assumed a resolved
>   mention; a plan with no mentions has no name to put in it.
> - **`world_scoped=False` for the right reason.** "Authoring implies False" is
>   false — `npc_link_coherence` is authoring and `True`. The criterion is
>   whether a creator would want the template to differ between worlds.
>
> RECON findings already measured and confirmed, folded in rather than re-asked:
> the codebase's idiom for a function making one `chat()` call is
> attempt-and-catch with no pre-flight `ping()` (pre-flight exists only at route
> level for multi-call pipelines); `json_ui_boundary.py` gates DB-column JSON
> storage only and does not touch a response field.

## Context

BRIEF-0085-b and -c produce rows, a verdict and a trace. This step turns them
into the prose answer the ticket exists for. The model appears here in a third
role — not proposing, not judging, rendering — and sees only the rows the
selectors returned. Every non-`answered` verdict is rendered by code, never by
the model, so an empty retrieval can never be filled in.

## RECON required before execution

Report-only. Report and stop if a stop condition fires.

- **R-a** Record, for each entry in `SELECTORS`, the exact key set of the row
  dicts it returns, and whether every row carries `"section"`.
  *Expected at the time of writing:* `entity_dossier` rows carry `section`
  (`identity`, `relations`, `knowledge`, `memberships`, `goals`);
  `world_factions` rows carry none. Item 3 fixes exactly that gap.
  *Stop condition:* a selector emits rows with a `section` value not in the
  union item 2 lists — the formatter map would silently drop them, and the
  section vocabulary must be settled before writing the renderer.
- **R-b** Record the exact section names `entity_dossier` actually emits in the
  shipped code, rather than the ones BRIEF-0085-b specified.
  *Report.* Item 2's vocabulary is built from the shipped set, not the planned
  set — `traits` was struck during execution and `memberships` carries an open
  question of its own, so the two may differ.
- **R-c** Confirm `LoreResult` carries `verdict`, `rows` and `trace`, and that
  the verdict set is the closed five from BRIEF-0085-b.
  *Stop condition:* the verdict set differs.
- **R-d** Record the `prompt_template` seeding and `PROMPT_REGISTRY` idiom as
  applied by BRIEF-0085-c for `lore_question_to_plan`, so the second usage is
  registered identically. *Report.*
- **R-e** Record whether `execute_plan` currently validates the shape of rows
  returned by a selector at all. *Report.* Item 3 adds the guard if none exists.

## Scope IN

1. **New module `src/world_engine/lore_render.py`.** Docstring states, verbatim:

   > The renderer neither proposes nor judges — it renders. It receives the rows
   > the selectors returned and nothing else: no `Session`, no `select(`, no
   > entity id it can look up. Only the `answered` verdict reaches the model;
   > every empty verdict is rendered by code, because a model asked to explain
   > an absence will fill it.

2. **The section contract, stated once and enforced.** Every row returned by
   every selector carries a `"section"` key. Section is not a dossier-local
   idea: it is the grouping key the renderer and the trace both need, so a
   selector returning one uniform kind of row declares one section rather than
   none.

   The vocabulary is the union of what the shipped selectors emit — at the time
   of writing, `identity`, `relations`, `knowledge`, `memberships`, `goals`
   from `entity_dossier`, and `factions` from `world_factions`, subject to what
   R-b reports. `_SECTION_FORMATTERS: dict[str, Callable[[dict], str]]` in
   `lore_render.py` has exactly these keys. An unknown section **raises** in
   `render_template`; it is never skipped, and rows are never dropped to keep a
   render from failing.

3. **Authorized narrow amendment, in its own commit, before the renderer
   commit.**
   *Trigger:* R-a reports that `world_factions` rows carry no `"section"` key.
   *Fix, exactly and only this:*
   - `lore_selectors.world_factions` adds `"section": "factions"` to each row it
     returns. No other field changes, no other selector is touched.
   - `lore_query.execute_plan` raises on any row returned by a selector that
     lacks a `"section"` key, naming the selector. If R-e reports such a guard
     already exists, skip this half.
   *Everything else found in `lore_selectors.py` or `lore_query.py`: REPORT
   ONLY.* This amendment is not a licence to revisit BRIEF-0085-b's selector
   output; it establishes the one contract this step cannot be written without.

4. **`render(result: LoreResult, question: str) -> RenderedAnswer`** where
   `RenderedAnswer` is a frozen dataclass `(prose: str, renderer: str, trace:
   list[dict])` and `renderer` is one of `"model"`, `"template"`,
   `"deterministic"`. The function takes NO `Session` parameter. That is the
   structural guarantee, not a convention.

5. **Deterministic verdict messages.** Every verdict other than `answered` is
   rendered by code with `renderer="deterministic"`, from module-level string
   constants, using this exact wording:

   - `unknown_entity`, with near candidates:
     > Aucune entité nommée « {surface_form} » dans ce monde. Noms proches :
     > {noms}.
   - `unknown_entity`, without near candidates:
     > Aucune entité nommée « {surface_form} » dans ce monde, et aucun nom
     > proche.
   - `silent_canon`, **when the plan resolved at least one mention**:
     > {nom} existe. Le canon ne détient rien sur ce point.
   - `silent_canon`, **when the plan resolved no mention at all** — the
     `world_factions` case, where there is no entity to name:
     > Le canon ne détient rien sur ce point.
   - `unsupported_selector`:
     > Je ne sais pas encore interroger : {selector}. C'est une limite de
     > l'outil, pas du monde.
   - `ambiguous_mention`:
     > Deux entités portent le nom « {surface_form} ». Laquelle ?

     followed by one line per candidate: name, type, description, and location
     when present. When the count exceeds two, the first clause reads
     « {n} entités portent le nom ». When several mentions are ambiguous, each
     gets its own block, in the order the mentions appear in the plan.

   When several mentions are unmatched, `unknown_entity` produces one block per
   unmatched surface form, in plan order.

   These strings are copied verbatim. They are the distinction the ticket is
   built on — an executor paraphrasing them into one generic "aucun résultat"
   collapses three different facts about the world into one.

6. **New prompt usage `lore_rows_to_prose`**, registered in `PROMPT_REGISTRY`
   with `surface="authoring"`, **`world_scoped=False`**, `dry_run_capable=True`,
   `default_model=_author_model`, `call_sites` naming the function in
   `lore_render.py`, resolved through `effective_model`.

   `world_scoped` controls whether a per-world override row is consulted, not
   whether a usage is authoring — `npc_link_coherence` is authoring and `True`
   because tone and social convention are world properties. Here the renderer's
   job is fidelity to the rows, not register, and no per-world override has a
   reader yet. `False`. Flipping it later is one line in the registry, with no
   migration and no data rework, so nothing is foreclosed.

7. **Renderer prompt content.** The model receives the question and the rows,
   serialized by section in the order of item 2's vocabulary. It receives no
   world description, no entity the rows do not mention, and no DB access. The
   prompt states verbatim:

   > N'ajoute aucun fait absent des lignes fournies. Si les lignes ne répondent
   > pas à la question, dis-le au lieu de combler.
   >
   > Un lien social (lignes de section « relations ») et une information détenue
   > (lignes de section « knowledge ») sont deux choses distinctes. Nomme-les
   > séparément. Ne déduis jamais l'une de l'autre : deux personnes liées ne
   > savent pas forcément quelque chose l'une sur l'autre, et détenir une
   > information sur quelqu'un n'est pas le connaître.
   >
   > Une ligne marquée `is_incorrect` est une croyance de l'entité, pas un fait
   > du monde. Rends-la comme une croyance et signale explicitement qu'elle est
   > fausse. Ne la remplace jamais par ce qui est vrai.
   >
   > Réponds en français, en prose continue. Pas de listes à puces, pas de
   > titres.

8. **Deterministic fallback.** `ollama_client.chat` raising `OllamaError` is
   caught in `render` and falls through to `render_template(result)`, which
   produces prose from the same rows with `renderer="template"`: one short
   paragraph per section present in the result, each row rendered by its
   `_SECTION_FORMATTERS` entry, sections in the item 2 order, and
   `is_incorrect` rows carrying the literal suffix « (croyance fausse) ». One
   `chat` attempt wrapped in try/except, no pre-flight `ping()` — that is the
   measured idiom for a single-call function, and a ping would double the
   latency of every question while still racing. `LlmParseError` is not caught
   here: the renderer returns prose, not JSON.

9. **Route change.** `/api/lore/ask` and `/api/lore/resolve` now return `answer`
   and `renderer` alongside `verdict`, `rows`, `trace`, `plan`, `candidates`.
   The routes call `lore_render.render`; they contain no formatting themselves.

10. **Extend `tooling/verify/checks/lore_isolation.py`** with:
    - R10: `lore_render.py` contains no `select(`, no `db.add(`, no `.commit(`,
      and no `Session` identifier.
    - R11: in `render`'s AST, no call to `chat(` appears on a path reachable
      when `verdict != "answered"` — the empty branches return first.
    - R12: `lore_render.py` contains a `try` whose handler names `OllamaError`
      and whose body reaches `render_template`.
    - R13: the six deterministic message templates exist as module-level string
      constants, not inline literals, so a paraphrase is visible in a diff.
    - R14: `render_template`'s AST contains a raise on the unknown-section path
      — rows are never silently dropped.

## Scope OUT

- **No frontend.** BRIEF-0085-e. Test with `curl`.
- **No change to any selector's output beyond item 3's exact amendment.** Not a
  renamed field, not a reordered key, not a "while I'm here" addition.
- **No new selector, no schema change, no `knowledge.subject` FK.**
- **No resolution of the `memberships` question.** Whether the creator's dossier
  should see secret memberships and true roles is an open decision on its own
  ticket. This step renders whatever sections the shipped selectors emit, and
  the formatter map follows R-b. If `memberships` is later removed, nothing here
  breaks.
- **No streaming of the answer.** `chat`, not `chat_stream`. Streaming would
  change the route contract; it is its own step.
- **No model call on any empty verdict** — including "just to phrase the absence
  more naturally". That is exactly the failure the three distinct messages exist
  to prevent.
- **No retry on `OllamaError`.** One attempt, then template.
- **No pre-flight `ping()` in `render`.**
- **No second model pass** to check or improve the first answer.
- **No citation markers, footnotes, or row ids inside the prose.** Provenance
  lives in the trace panel, which BRIEF-0085-e renders.
- **No caching of answers.**
- **No secret filtering, no viewpoint parameter.**
- **No persistence of the question, the answer, or the trace.**
- **No write path.**

## Invariants to defend

- **Secrets are structurally excluded from every assembled context — never
  instructionally.** This step is the one most likely to damage it: it builds a
  prompt containing canon rows. The exclusion here is structural in a different
  way — the creator is the reader, so rows are not filtered, and the guard is
  that `lore_render.py` can never be reused for an NPC prompt because it takes
  no `Session` and its usage is registered `surface="authoring"`. A future
  NPC-facing prose path builds its own.
- **All templated model calls resolve through `effective_model`.** Directly
  threatened; second usage added here.
- **`discoverable_detail` is structurally excluded from every assembler.**
  Already guarded in `lore_selectors.py`; the renderer cannot reintroduce it,
  since it renders only what it is given.
- **UI-visible data never lives in JSON; relational only.** The `answer` string
  is generated prose, not stored data. Nothing here may write it anywhere.
- **Creator control is structural.** Read-only; R10 is the guard.

## Done means

- [ ] Two commits: the item 3 amendment, then the renderer
- [ ] `tooling/verify/checks/lore_isolation.py` exits 0 with R10-R14
- [ ] `lore_selectors.py`, `llm_parse_chokepoint.py`, `prompt_version.py`,
      `corpus_gate.py`, `import_cycle.py`, `function_length.py`,
      `no_print_in_src.py` exit 0
- [ ] The `PROMPT_REGISTRY` entry for `lore_rows_to_prose` reads
      `world_scoped=False`
- [ ] Every row returned by every selector carries a `"section"` key, verified
      by a script that calls each selector once against a live DB
- [ ] A selector stubbed to return a row without `"section"` makes
      `execute_plan` raise, naming that selector
- [ ] "Est-ce que <NPC A> connaît <NPC B> ?" returns French prose naming the
      social link and the held information separately, `renderer: "model"`
- [ ] An NPC with a `knowledge` row flagged `is_incorrect` is described as
      believing it, with the falsity stated, and the true version not
      substituted
- [ ] "Quelles sont les factions du monde ?" returns prose listing them,
      `renderer: "model"`
- [ ] A nonexistent name returns the verbatim `unknown_entity` message with
      `renderer: "deterministic"`
- [ ] Two nonexistent names in one question return one block each, in plan order
- [ ] An entity with nothing on the point returns the verbatim mention-form
      `silent_canon` message
- [ ] A `world_factions` question against a world with no faction returns the
      verbatim no-mention form of `silent_canon`, with no stray name or empty
      brackets
- [ ] A question needing an unbuilt selector returns the verbatim
      `unsupported_selector` message naming it
- [ ] An ambiguous name returns the verbatim ambiguity message with one line per
      candidate; a third same-named entity renders the « {n} entités » form
- [ ] With Ollama stopped, the same `answered` question returns prose with
      `renderer: "template"`, containing the same facts, with one paragraph per
      section present
- [ ] With Ollama stopped, a `world_factions` question renders its `factions`
      section paragraph
- [ ] With Ollama stopped, an empty verdict returns `renderer: "deterministic"`
      — unchanged from the Ollama-running case
- [ ] `/review-step` then `/close-step` run clean on both commits

## Docs to update

`tooling/standards/ARCHITECTURE_DECISIONS.md`: record the renderer as a third
model role alongside proposing and judging; record that only the `answered`
verdict reaches a model; record the section contract — every selector row
carries a section, enforced in `execute_plan`, so a later selector cannot repeat
the `world_factions` gap. Add one CLAUDE.md invariant, now that the path is live:

> **The lore renderer receives rows, never a `Session`,** and only the
> `answered` verdict reaches a model — every empty verdict is rendered by code,
> so an absence is never explained by a model.

No schema changelog entry.
