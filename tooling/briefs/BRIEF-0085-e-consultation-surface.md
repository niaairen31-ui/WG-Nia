<!-- slug: consultation-surface -->
# BRIEF — Step "Consultation surface"

> **Amended, second revision.** Changes from the first:
> - Every row now carries a `"section"` key (BRIEF-0085-d item 2), so the trace
>   groups uniformly instead of special-casing `world_factions`.
> - Display names are sourced from the `identity` rows already in the payload,
>   because trace mention entries carry `entity_id` and no name.
> - The `page_contract.py` gate is conditional on which shell R-a selects.
> - Two RECON stop conditions that would have halted execution over something
>   the executor could simply adapt to are demoted to REPORT. Only genuine
>   blockers stop this step: an ambiguous shell choice, and a missing API field.
> - A non-`answered` verdict from `/resolve` is named as a normal outcome.

## Context

BRIEF-0085-d closed the engine side: a question in, prose plus verdict plus trace
out, degrading to a template when the model is down. This step puts it in the
cockpit so the surface is usable while running a session, and renders the two
things the API returns that prose cannot carry — the provenance trace and the
candidate chooser.

## RECON required before execution

Report-only. Report and stop only where a stop condition says so.

- **R-a** Determine which shell this surface belongs to. `page_contract.py`
  governs Création pages through the `CREATION_TABS` registry and its generic
  dispatcher; `frontend/src/observation/` is a top-level surface outside it.
  Record which of the two the lore surface must be, and what registering it
  costs in each case.
  *Stop condition:* both are defensible on the evidence — escalate to Nia rather
  than picking. A surface placed in the wrong shell is a rewrite, not a tweak,
  and this is the one judgment in this step that is not the executor's to make.
- **R-b** Confirm `/api/lore/ask` and `/api/lore/resolve` return `answer`,
  `renderer`, `verdict`, `rows`, `trace`, `plan`, `candidates`.
  *Stop condition:* `answer` or `renderer` is absent — BRIEF-0085-d item 9 is
  incomplete and the surface has nothing to display.
- **R-c** Record the store idiom in
  `frontend/src/observation/observation.svelte.js`: how state is held, how a
  fetch is issued, how an error is surfaced. *Report;* this step copies it
  rather than introducing a second pattern.
- **R-d** Record what `verify/checks/json_ui_boundary.py` asserts and what
  `verify/checks/frontend_build_fresh.py` requires at commit time — in
  particular whether a build artifact must be committed alongside source.
  *Report;* Done means adapts to the answer rather than halting on it.
- **R-e** Record how the active world id is obtained client-side on an existing
  surface. *Report.* This step adds no world selector of its own.
- **R-f** Record the exact keys each `trace` entry carries, for mention entries
  and for call entries, and whether `rows` entries all carry `"section"`.
  *Report.* If a mention entry already carries a display name, item 4's
  client-side lookup is unnecessary — drop it and render the name directly,
  noting the simplification in the close-step. That is an adaptation, not a
  blocker.

## Scope IN

1. **New surface `frontend/src/lore/`** with `Lore.svelte` and
   `lore.svelte.js`, following the structure and store idiom R-a and R-c report.
   Registered in whichever shell R-a determines, using that shell's existing
   registration mechanism — never a hand-authored branch.

2. **Question field.** A single multi-line text input and a submit control.
   Submitting posts to `/api/lore/ask` with the active world id obtained the way
   R-e reports. While in flight, the control is disabled and the previous answer
   stays visible rather than being cleared — a blank panel during a slow local
   model reads as a failure.

3. **Answer panel.** Renders `answer` as prose. Below it, a small,
   always-visible label showing which renderer produced it, with this exact
   wording:
   - `model` → « rédigé par le modèle »
   - `template` → « modèle indisponible — réponse déterministe »
   - `deterministic` → no label; the deterministic verdict messages are already
     self-explanatory and a label would clutter them.

   The `template` label is not a warning style — it states a fact. The answer is
   still correct; only its phrasing is mechanical.

4. **Trace panel, collapsed by default.** Expanding shows, from `trace`: one row
   per resolved mention (`surface_form`, verdict, rung, resolved entity) and one
   per executed call (`selector`, args, `row_count`, and a `truncated` marker
   when set). Rows are grouped by their `"section"` key, which every row carries
   — no selector is special-cased.

   **Display names are sourced client-side from the payload.** Trace mention
   entries carry `entity_id`, not a name. The surface looks the id up in the
   `identity` rows already present in `rows` and displays the name it finds
   there, falling back to the raw id when there is none — the normal case for an
   `unmatched` mention, where no entity exists to name. The surface issues no
   second request to describe what it already received.

5. **Candidate chooser.** On verdict `ambiguous_mention`, the answer panel shows
   the deterministic ambiguity prose, and below it one selectable group per
   ambiguous mention, each option showing the candidate's `name`, `type`,
   `description` and `location_name`, with the location line omitted when it is
   null rather than rendered as "null". Choosing for every ambiguous mention
   enables a confirm control that posts `plan` — echoed back unchanged as
   received — plus the bindings to `/api/lore/resolve`. Partial selection leaves
   the control disabled: the round resolves every ambiguity at once.

6. **The plan is echoed verbatim.** The surface stores the `plan` object as
   received and sends it back untouched. It does not rebuild it, reorder it,
   strip fields from it, or re-issue `/api/lore/ask` with a fuller name — any of
   which would break the ticket's guarantee that disambiguation cannot shift the
   question.

7. **A non-`answered` response from `/resolve` renders normally.** After
   binding, the result may be `unknown_entity` — a different mention in the same
   question did not resolve — or `silent_canon`. Both display like any other
   answer, through the same panel. Neither is an error state, and the surface
   must not show an error style, retry, or re-ask for either.

8. **Error surface.** A failed request or a non-2xx response shows the error the
   way R-c reports the observation surface does. `LlmParseError` from the
   planner arrives as a server error and is displayed as one, not swallowed into
   « aucun résultat » — an unparseable plan is not an empty world.

## Scope OUT

- **No question history, no saved answers, no favourites.** The trace is
  displayed and not persisted; the same holds for the exchange. Persisting
  questions is a table, which is a schema change, which is a different ticket.
- **No entity-name autocomplete in the question field.** It would leak the
  registry into the input, and it would let the creator pre-resolve names the
  resolver is supposed to resolve — hiding exactly the ambiguity and
  unknown-entity cases this ticket built.
- **No editing from the surface.** No "corriger", no "ajouter au lore", no link
  into the CRUD forms. The assertion path is a later ticket and its first
  affordance must be designed, not inherited from a read surface.
- **No world selector.** The surface uses the active world.
- **No client-side re-ranking, filtering or grouping of `rows` beyond the
  section grouping in item 4.** Reordering within a section would desynchronize
  the trace from what the renderer actually saw.
- **No streaming display.** The route is not streaming.
- **No new API route, no engine change, no change to any check file.** If the
  surface needs something the API does not return, REPORT ONLY and stop — do not
  add a field in passing.
- **No third selector, no schema change.**
- **No rephrasing of the deterministic messages client-side.** They arrive as
  prose and are displayed as prose. Reformatting them into a styled empty-state
  with its own wording re-collapses the three cases the ticket separated.
- **No retry button that re-asks automatically.**

## Invariants to defend

- **UI-visible data never lives in JSON — relational only.** The answer prose
  and the trace are transient response payload, not stored data, and nothing in
  this step may persist them anywhere.
- **The page contract** (whichever shell R-a determines): the surface is a
  registry entry rendered by the generic dispatcher, with its primary action
  declared in the registry — never a page-specific branch outside it.
- **Creator control is structural.** A read surface offering no write affordance
  is the enforcement; Scope OUT is where it is defended.
- **Injected context depends on the active role, never the account.** Not
  directly threatened, but the surface passes no identity beyond the world id.

## Done means

- [ ] `tooling/verify/checks/page_contract.py` exits 0 — required only if R-a
      places the surface inside the Création shell; if R-a places it outside,
      record that in the close-step note instead of running it as a gate
- [ ] `tooling/verify/checks/json_ui_boundary.py` exits 0
- [ ] `tooling/verify/checks/frontend_build_fresh.py` exits 0, with a build
      artifact committed if R-d reports one is required
- [ ] `tooling/verify/checks/corpus_gate.py` exits 0
- [ ] `lore_isolation.py` and `lore_selectors.py` exit 0, unedited by this step
- [ ] In a live session, asking whether one NPC knows another returns prose in
      the answer panel naming both registers
- [ ] The trace panel, expanded, lists the mentions with their rungs and the
      calls with their row counts, rows grouped by section
- [ ] A `world_factions` question shows its rows under the `factions` section
      with no special-casing in the component
- [ ] A resolved mention shows the entity's name, not its id
- [ ] An unmatched mention shows the surface form with no name and no crash
- [ ] A nonexistent name shows the verbatim `unknown_entity` message with no
      renderer label
- [ ] An ambiguous name shows the ambiguity prose plus one selectable group, and
      the confirm control stays disabled until a choice is made
- [ ] A candidate with no location renders without a location line
- [ ] Confirming returns the answer for the chosen entity, and the browser
      network log shows `/api/lore/resolve` posting the plan unchanged
- [ ] With two ambiguous mentions in one question, both groups appear and
      confirm requires both
- [ ] A `/resolve` response with verdict `unknown_entity` renders as a normal
      answer, not an error
- [ ] With Ollama stopped, an answered question shows prose with the label
      « modèle indisponible — réponse déterministe »
- [ ] `/review-step` then `/close-step` run clean

## Docs to update

`tooling/standards/ARCHITECTURE_DECISIONS.md`: record which shell the surface was
registered in and why (the R-a finding), so the next surface does not
re-litigate it. No schema changelog entry. This step closes TICKET-0085; run
`/verify` on the ticket after it.
