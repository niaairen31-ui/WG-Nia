<!-- slug: planner-unavailable-message -->
# BRIEF 0085-F — "Planner-unavailable message, not a raw pre-flight error"

Lot: LOT-0085-planner-unavailable-message.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `ask_lore` (`src/world_engine/cockpit/routes/lore.py:96-109`) -> still pings
  `ollama_client.ping()` first, still raises
  `HTTPException(status_code=503, detail=str(exc))` on `OllamaError`, still
  calls `_lore_plan.draft_plan` only after the ping succeeds. Halt if this
  shape moved.
- `src/world_engine/lore_render.py` -> still defines exactly six `_`-prefixed
  message constants (lines 120-131) and nothing else already named
  `PLANNER_UNAVAILABLE_MESSAGE`. Halt if a seventh already exists under a
  different name, or if the six have been restructured.
- `tooling/verify/checks/lore_isolation.py` -> still stops at R15
  (`check_prompt_loader_scoped_to_prompt_tables`). Halt if R16 already exists
  (someone else landed a check with that number first) — do not silently
  renumber to R17; report and stop.
- `frontend/src/lore/lore.svelte.js` / `Lore.svelte` -> `askError` handling
  is still the plain catch-and-store-`e.message` / generic `.r-err` div
  (R-03/R-04). Halt if this has already grown status-code branching — the
  "no frontend change" scope call below assumes it has not.

## Facts carried

- **R-01.** `ask_lore` pings Ollama first (lines 98-101); on `OllamaError` it
  raises `HTTPException(status_code=503, detail=str(exc))` and returns
  before `_lore_plan.draft_plan` (line 104) is attempted. The `LlmParseError`
  branch two lines below is a separate failure mode, untouched here.
- **R-02.** `OllamaError`'s unreachable-host message is English and appends
  the raw underlying exception repr.
- **R-05.** The ticket's six deterministic message constants live in
  `lore_render.py` and are dispatched by `_render_deterministic`, which
  requires a `LoreResult` that does not exist yet at ping time. The new
  constant is a standalone, seventh string — not a member of that dispatch
  table.
- **R-06.** `lore_isolation.py`'s highest existing check is R15. This brief's
  new check is R16.
- **R-07.** R6 (`check_route_is_thin`) fails the build on any `chat(` or
  `select(` anywhere in `cockpit/routes/lore.py`'s AST.
- **R-08.** `PATCH /api/prompts/{prompt_id}/model` (BRIEF-0009-a,
  `ARCHITECTURE_DECISIONS.md:4127-4136`) also pings-then-503s, deliberately,
  for a write-validation reason unrelated to this brief. Not touched.
- **R-09.** The ticket's "With Ollama stopped..." live-gate line is
  literally true for `/api/lore/resolve` only. A fresh `/api/lore/ask`
  cannot be made to satisfy it without a model — confirmed by Nia, live,
  as "not a wiring bug."

## Contracts

- **C-01.** `PLANNER_UNAVAILABLE_MESSAGE: str` — new module-level constant in
  `src/world_engine/lore_render.py`, produced by this brief, consumed by
  `cockpit/routes/lore.py`'s `ask_lore`. Not added to
  `_EXPECTED_DETERMINISTIC_MESSAGE_CONSTANTS`.

## Context

TICKET-0085's PR (#112) is marked Draft/blocked specifically on this gap:
a fresh `/api/lore/ask` question, asked while Ollama is down, currently
fails with a raw English exception string instead of the explicit,
French, "here is why there's no answer" prose every other empty/error path
in this ticket already gives. Nia has decided (A2) to close this a minima:
change the message, not the capability. `/api/lore/resolve` already
degrades correctly and is not touched.

## Scope IN

1. **New constant in `src/world_engine/lore_render.py`**, placed alongside
   the existing six message constants (after line 131), named and worded
   exactly:

   ```python
   # Route-level: no LoreResult exists yet at ping time, so this is not
   # dispatched by _render_deterministic and is not one of the six above —
   # it is the planner's own precondition failing, not an empty retrieval.
   PLANNER_UNAVAILABLE_MESSAGE = (
       "Je ne peux pas répondre à une nouvelle question : le modèle local "
       "n'est pas disponible pour en tirer un plan. Démarre Ollama, puis "
       "repose la question."
   )
   ```

   This wording is Claude's drafting proposal (flagged, per convention, as
   drafting decision **D1** below) — copy it verbatim unless Nia edits it
   when reviewing this brief; do not paraphrase once approved.

2. **One-line change in `src/world_engine/cockpit/routes/lore.py`**, in
   `ask_lore`'s pre-flight `except` block only:

   ```python
   except ollama_client.OllamaError as exc:
       raise HTTPException(
           status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE
       ) from exc
   ```

   replacing the current `detail=str(exc)`. No other line in `ask_lore` or
   `resolve_lore` changes. `_lore_render` is already imported in this file
   (line 24) — no new import needed.

3. **New check in `tooling/verify/checks/lore_isolation.py`: R16.** Add a
   `check_ask_ollama_error_uses_named_message()` function, called from
   `main()` after `check_route_is_thin` (i.e., right after R6, keeping
   related route checks adjacent), asserting: in `ask_lore`'s AST, the
   `except` handler naming `OllamaError` raises `HTTPException` whose
   `detail` keyword argument is an `ast.Attribute`/`ast.Name` reference
   (i.e., a named constant), never an `ast.Call` to `str(...)` and never an
   `ast.JoinedStr` (f-string) built from the handler's bound exception name.
   Follow the file's existing idiom exactly: reuse `_local_functions`,
   locate `ask_lore` the same way `check_resolve_never_redrafts` (R7)
   locates its target handler (by `@router.post("/api/lore/ask")`), walk its
   `ast.Try` nodes, and call `fail(...)` with the `lore_isolation R16:` prefix
   used by every other rule in this file. Add the docstring block for R16 to
   the module docstring (lines 6-54) in the same style as R1-R15, and add
   `check_ask_ollama_error_uses_named_message()` to the `main()` call
   sequence and to the `PASS:` summary string (currently ending
   `"...(R10-R14) are all intact"` — extend it to name R16 too, per the
   file's own convention of listing every rule number in that final message).

## Scope OUT

- **No change to `/api/lore/resolve`.** Already confirmed working offline
  (R-09); nothing here may touch `resolve_lore` or `lore_resolve.py`.
- **No change to the `LlmParseError` branch** two lines below the fix in
  `ask_lore` (lines 105-106). Different failure mode, different message,
  not this brief.
- **No offline/model-free planner.** Explicitly rejected by Nia's decision:
  "the planner cannot be bypassed, not a wiring bug." If you find yourself
  writing a heuristic plan-builder, stop.
- **No frontend change.** `loreState.askError` / `.r-err` (R-03/R-04)
  already surfaces whatever string `detail` carries; it will now show
  `PLANNER_UNAVAILABLE_MESSAGE` instead of the raw English one, unchanged
  mechanism. A visual distinction between this "expected, explained" case
  and a genuine error is a future frontend brief, not this one.
- **No new member of `_EXPECTED_DETERMINISTIC_MESSAGE_CONSTANTS` / no new
  `LoreResult` verdict.** R-05: this case has no `LoreResult` yet. Do not
  route it through `_render_deterministic` or the verdict system.
- **No change to `ollama_client.py`.** The pre-flight `ping()` idiom itself
  is correct for this multi-call pipeline (R-08) and is not what this brief
  fixes — only the message the route builds from its failure.
- **No renumbering of R1-R15**, and no reuse of R16 if it turns out to
  already exist (see Mini-RECON halt condition) — escalate instead.
- **No touching `main`, no rebase of `ticket/0085`.** The corpus_gate/
  TICKET-0086 item is a separate, already-understood step Nia is handling
  around this brief, not part of it (see the LOT's "Objective and cut").

## Invariants to defend

- **R6 (route stays thin — no `chat(`, no `select(` in `cockpit/routes/
  lore.py`).** Directly adjacent: this brief edits that exact file. The
  change is a keyword-argument value and one attribute reference; neither
  introduces a forbidden call.
- **"Say explicitly why there is no answer, never a silence."** This is the
  invariant this brief extends into a case it did not yet cover (planner
  precondition failure), not a new one.
- **Message constants, not inline literals (R13's pattern).** The new
  constant follows the same shape — named, module-level, quoted verbatim —
  even though it is deliberately kept out of R13's own closed set (R-05).
- **Pre-flight `ping()` for multi-call pipelines only (BRIEF-0085-d's
  measured idiom, reaffirmed by R-08).** This brief does not add, remove, or
  relocate a `ping()` call — it only changes what the existing one says on
  failure.

## Decision rights

STOP:
- The Mini-RECON anchors above have moved (any of the four).
- R16 already exists under a different implementation than described here.
- Fixing R16's check cleanly requires touching a file outside
  `cockpit/routes/lore.py` / `lore_render.py` / `lore_isolation.py`.

ADAPT:
- The exact AST-matching approach inside the new check function, as long as
  it enforces the rule stated in Scope IN item 3 and follows the file's
  existing helper idiom (`_local_functions`, `fail()`, the `lore_isolation
  R16:` message prefix). Report the approach taken.
- Where exactly in `main()`'s call sequence R16 is invoked, if "right after
  R6" turns out to be awkward given the function's current layout — keep it
  adjacent to another route-level check and report where.

REPORT-ONLY:
- Anything noticed in `ollama_client.py`, the `LlmParseError` branch, or the
  frontend error styling that looks improvable. Out of scope; note it,
  change nothing.

Any finding not listed above that touches neither a CLAUDE.md invariant nor
a `danger_class` of this ticket: resolve it by the most conservative option
available, proceed, and report it. Any finding that touches an invariant or
a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `tooling/verify/checks/lore_isolation.py` exits 0, with R16 in the
      `main()` sequence and named in the PASS summary string
- [ ] `corpus_gate.py` exits 0 — requires `ticket/0085` rebased onto `main`
      (carries TICKET-0086's fix, #111, merged 2026-09-13); not this brief's
      change, but part of this ticket's overall verify per Nia
- [ ] `import_cycle.py` and `function_length.py` exit 0
- [ ] Live, Ollama stopped: a fresh `POST /api/lore/ask` (a question never
      sent to `/ask` before) returns HTTP 503 with `detail` equal, verbatim,
      to `PLANNER_UNAVAILABLE_MESSAGE`
- [ ] Live, Ollama stopped: `POST /api/lore/resolve` with a previously
      obtained plan still returns HTTP 200 with `renderer: "template"` —
      regression check, must remain exactly as before this brief
- [ ] Live, Ollama running: `POST /api/lore/ask` behaves exactly as before
      this brief (unaffected path) for at least one previously-verified
      question (e.g. "Est-ce que Mara connaît Corvin ?")
- [ ] `/review-step` and `/close-step` run clean

## Docs to update

- **`tooling/tickets/TICKET-0085-lore-consultation.md`:**
  - Append `BRIEF-0085-f` to `brief_ids` in the frontmatter.
  - Add `lot_id: LOT-0085-planner-unavailable-message.md` (this ticket
    predates the lot protocol and has no prior `lot_id` — first one).
  - Reword the acceptance-criterion line "With Ollama stopped, the same
    questions still answer via the template renderer" to state the real
    split: `/api/lore/resolve` (with a previously-obtained plan) still
    answers via the template renderer; a fresh `/api/lore/ask` question
    instead returns the explicit `PLANNER_UNAVAILABLE_MESSAGE` rather than
    a raw error, since drafting a new plan has no non-model path. This is a
    correction to the ticket's own gate, made because Nia is choosing this
    brief's shape now — flag the exact new line wording back to her before
    or when closing this brief, don't silently finalize it.
  - Leave `retry_count` untouched — tooling-managed, not this brief's call.
- **`tooling/standards/ARCHITECTURE_DECISIONS.md`:** add an entry (e.g.
  "LORE CONSULTATION — PLANNER UNAVAILABLE IS AN EXPLICIT MESSAGE, NOT A RAW
  ERROR (BRIEF-0085-f, no schema change)") recording: the pre-flight-ping
  idiom is kept and is correct for this multi-call pipeline (citing
  BRIEF-0009-a as existing precedent for the idiom itself); only the
  message changed; a model-free planner was considered and rejected as
  disproportionate for a single-operator local tool, reactivation condition
  named explicitly — e.g. "reactivate if `/ask` must ever run where the
  operator does not control whether Ollama is running (remote or
  multi-user access)."
  **Do not hand-edit `DECISIONS_INDEX.md`** — it is generated
  (`tooling/glue/gen_decisions_index.py`); regenerate it after the
  `ARCHITECTURE_DECISIONS.md` entry is added.
- No schema changelog entry (`schema_version_touched: none`, unchanged).

---

**Drafting decisions flagged for Nia's review (numbered per convention):**

**D1.** The exact French wording of `PLANNER_UNAVAILABLE_MESSAGE` (Scope IN
item 1) is Claude's proposal, not dictated. Override it here if you want
different phrasing before this brief runs — the executor copies verbatim.

**D2.** The new constant's home is `lore_render.py` (co-located with the
other six, imported by the route) rather than `cockpit/routes/lore.py`
itself, and it is deliberately named without a leading underscore (unlike
the other six, which are file-private) to signal it is meant to be imported
cross-module. If you'd rather keep it private and have the route reference
`_lore_render._PLANNER_UNAVAILABLE` (or place it directly in the route
file instead), say so before this runs.

**D3.** `lot_id`'s value and the convention for where `LOT-*.md` files live
in the repo (`tooling/lots/`, proposed by analogy with `tooling/briefs/` and
`tooling/tickets/`) are both new as of today's protocol rewrite — there is
no prior example to measure against. Confirm or correct the directory
before depositing `LOT-0085-planner-unavailable-message.md`.
