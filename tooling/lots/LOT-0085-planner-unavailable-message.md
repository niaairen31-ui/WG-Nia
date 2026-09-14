# LOT — TICKET-0085 "Planner-unavailable message, not a raw pre-flight error"

## Objective and cut

Closes the one open gap on TICKET-0085 before its PR (#112) can leave Draft:
`POST /api/lore/ask`, when Ollama is unreachable, currently fails a fresh
question with a raw `HTTPException(503, detail=str(exc))` built from
`OllamaError`'s English, technical message. Per Nia's decision (A2, chat
2026-09-14): fix this a minima, inside TICKET-0085, by routing the failure
through the same "always say explicitly why" doctrine the ticket's other five
empty/error cases already use — a named, French, deterministic message — and
NOT by building a model-free planner. Nia's own prior finding (confirmed live,
`tooling/questions/QUESTION-TICKET-0085.md`) already established that a fresh
`/ask` question structurally cannot be answered offline (`draft_plan` has no
non-model path) — this is not a wiring bug to fix, so this lot does not
attempt to make `/ask` answer offline. It only makes the failure explicit,
in-voice, and consistent with the rest of the ticket.

Cut: this lot does not touch `/api/lore/resolve` (already confirmed working
offline), does not touch the `LlmParseError` branch two lines below the fix
(a different failure mode), and does not touch the frontend (the existing
generic error banner already displays whatever string the backend sends).

Out-of-band reminder, not part of this lot: PR #112 is also blocked on
`ticket/0085` picking up TICKET-0086's `corpus_gate.py` fix (#111, merged
2026-09-13) via a rebase/merge from `main`. Nia has said this will be
exercised by the verify run of this lot's brief — noted here only so it is
not lost, not as a task this lot performs.

## Briefs in this lot

- **F** — `planner-unavailable-message` — replace the raw pre-flight error
  with a named deterministic message; one commit.

## Dependency graph

Single brief. No ordering to state.

## RECON

### R-01 — `ask_lore`'s current shape
Opened: `src/world_engine/cockpit/routes/lore.py:96-109`
Finding: `ask_lore` pings Ollama first (lines 98-101); on `OllamaError` it
raises `HTTPException(status_code=503, detail=str(exc))` and returns before
`_lore_plan.draft_plan` (line 104) is ever attempted. The `LlmParseError`
branch immediately below (lines 105-106) is a separate failure mode
(malformed model output, not Ollama being down) and is untouched by this lot.
Consequence: this is the sole call site that needs to change. It is a
two-token edit (the `detail=` value), not a restructure.

### R-02 — What the creator sees today
Opened: `src/world_engine/ollama_client.py:66-70,73-85` (`_connection_error`,
`ping`)
Finding: `OllamaError`'s message for an unreachable host is
`"Ollama is not reachable at {host}. Is the server running? Start it with
`ollama serve`.\n  (underlying error: {exc})"` — English, and it appends the
raw underlying exception repr.
Consequence: serviceable, but in English and with raw technical noise, unlike
every other user-facing string this ticket produces (all French, all clean).

### R-03 — The frontend needs no change to benefit
Opened: `frontend/src/lore/lore.svelte.js:22-40` (`askLore`)
Finding: any thrown error from the `/api/lore/ask` fetch is caught and stored
verbatim as `loreState.askError = e.message`, with no branching on status
code or content.
Consequence: whatever string the route's `detail` carries is exactly what
reaches the screen. Improving the backend message is sufficient on its own.

### R-04 — No visual distinction exists today, and this lot does not add one
Opened: `frontend/src/lore/Lore.svelte:87-89`
Finding: `loreState.askError` renders in a plain `<div class="r-err">`, the
same generic banner used for a 422 (malformed binding), a 502
(`LlmParseError`), or a network failure.
Consequence: named as Scope OUT below, not fixed here — see "Scope OUT".

### R-05 — Where the ticket's message doctrine lives
Opened: `src/world_engine/lore_render.py:1-233`, message constants at
lines 120-131 (`_UNKNOWN_ENTITY_WITH_NEAR`, `_UNKNOWN_ENTITY_WITHOUT_NEAR`,
`_SILENT_CANON_WITH_ENTITY`, `_SILENT_CANON_WITHOUT_ENTITY`,
`_UNSUPPORTED_SELECTOR`, `_AMBIGUOUS_MENTION_HEADER`)
Finding: these six are the ticket's established home for French,
non-technical, "explain the absence/limit explicitly" prose. `render()`
(line 213) only ever runs once a `LoreResult` exists.
Consequence: the planner-unavailable case has no `LoreResult` — it cannot be
dispatched by `_render_deterministic` or added to this six-member family. It
needs its own constant and its own call site (the route), not a seventh
member of an existing closed set.

### R-06 — The next check number
Opened: `tooling/verify/checks/lore_isolation.py:6-54` (module docstring),
`:559-617` (`check_prompt_loader_scoped_to_prompt_tables`, `main`)
Finding: R1 through R15 are all implemented, none skipped; R15
(`check_prompt_loader_scoped_to_prompt_tables`) is the highest in use.
Consequence: a new check in this file is **R16**.

### R-07 — The guard this lot's edit must not trip
Opened: `tooling/verify/checks/lore_isolation.py:264-277`
(`check_route_is_thin`, R6)
Finding: R6 fails the build if `cockpit/routes/lore.py`'s AST contains
`chat(` or `select(` anywhere.
Consequence: the fix (a keyword-argument value swap plus one import) must
not, and as drafted does not, introduce either.

### R-08 — The pre-flight-ping idiom is not the problem
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:4127-4136`
("PROMPT MODEL SELECTION — write path", BRIEF-0009-a)
Finding: a different existing route (`PATCH /api/prompts/{prompt_id}/model`)
also pings Ollama and returns a raw-message 503 on failure — but there it is
a deliberate fail-closed **write**-validation gate ("a model override is
only meaningful if the model can be checked"), not a read/render path.
Consequence: pinging before a multi-call pipeline is an established,
legitimate idiom elsewhere in this codebase (also reaffirmed by
BRIEF-0085-d's own RECON note that pre-flight `ping()` is for multi-call
pipelines, attempt-and-catch for single-call ones). Nothing about that idiom
is what this lot fixes — only the message text is. BRIEF-0009-a's path is
untouched.

### R-09 — What "done" can and cannot mean here
Opened: `tooling/tickets/TICKET-0085-lore-consultation.md:155-156`;
`tooling/questions/QUESTION-TICKET-0085.md:100-113`
Finding: the ticket's live-gate line reads "With Ollama stopped, the same
questions still answer via the template renderer." Nia's own confirmed,
live-tested finding: `/api/lore/resolve` already satisfies this fully
(no code change); a fresh `/api/lore/ask` structurally cannot, because
`draft_plan` "has no non-model path" — "the planner cannot be bypassed, not
a wiring bug."
Consequence: this brief cannot make the existing line literally true for
`/ask`. Its job is to make the ticket's acceptance criteria say the true
thing (see "Docs to update" in the brief) — a wording correction Nia is
making now by choosing this brief's shape, not a unilateral rewrite.

## Contract sheet

### C-01 — `PLANNER_UNAVAILABLE_MESSAGE`
Produced by: BRIEF-0085-f
Consumed by: none in this lot (the route uses it directly)
Signature: `PLANNER_UNAVAILABLE_MESSAGE: str`, module-level constant in
`src/world_engine/lore_render.py`, **not** added to
`_EXPECTED_DETERMINISTIC_MESSAGE_CONSTANTS` (R-05: different mechanism,
dispatched from the route, not from `_render_deterministic`).
Return shape: n/a (a string constant, not a function)
Error/empty cases: n/a
Available to a future frontend brief if Nia later wants `Lore.svelte` to
style this case differently from a genuine error (R-04) — not exercised by
this lot.

## Gate output

**(a) Unverified symbol.** Every symbol this lot names —
`ask_lore`, `ollama_client.ping`/`OllamaError`, `draft_plan`, the six
existing message constants, `check_route_is_thin`/R6,
`check_prompt_loader_scoped_to_prompt_tables`/R15, BRIEF-0009-a's ping-gate —
appears in R-01 through R-09 above, opened directly. [tick]

**(b) Unwalked rule.** No closed-set rule (selector, verdict, rung) is
introduced or modified by this lot — the fix is a single message
substitution at one call site. No case table is owed.

**(c) Unenumerated generalization.** The one universal-sounding claim this
lot relies on — "R1 through R15 are all implemented, none skipped, R15 is
the highest" — is not asserted from a class inventory; it is read directly
off `lore_isolation.py`'s `main()` (`:588-603`, the explicit call sequence)
and the docstring's own R1-R15 listing (`:6-54`), both pasted in R-06 above.

**(d) Un-rederived contract.** No family of 2+ members is introduced (see
(b)) — C-01 is a single, standalone constant, not a family member. N/A.

**(e) Unsatisfiable check.** New gate: R16 (routes/lore.py's pre-flight
`except OllamaError` handler references a named constant, not `str(exc)` or
an f-string built from the caught exception). Module that satisfies it:
`cockpit/routes/lore.py`, which needs nothing R16 forbids — the change is a
value swap on an existing keyword argument, plus one attribute import
already available (`_lore_render` is already imported in that file).

## Amendments

None yet.
