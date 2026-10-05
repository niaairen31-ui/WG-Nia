# LOT — TICKET-0103 "Lore usage journal — what was proposed, refused, changed"

## Objective and cut

Every use of the Lore shell is journaled so that a later Claude Code session
can analyse the tool and improve it: for the writing panel, the statement,
the clarification questions, every draft the model proposed, the proposal
the creator committed (or the attempt she abandoned), and every refusal; for
the consultation panel, the question, the plan, the answer and the
disambiguation round. Each step keeps the model exchanges it took — prompt
version, model, rendered prompt, raw reply, error — failures included (A2,
B1, C1). Nothing is diffed at write time (D1). The journal is a global table
tagged by world (`world_ref`), never a world's table, so it outlives a
deleted test world (F2, I1). Its one reader is a JSONL export (E1).

The lot stops before the analysis itself (a Claude Code session on the
export, outside the application), before any in-app analysis screen (E2),
before journaling edits made later in the fiche to rows a Lore entry created
(H2, its own ticket), and before any retention or pruning of the journal.

## Briefs in this lot

- **A — the journal table** (schema v2.13): `lore_usage_event`,
  `writes/lore_usage.py` (C-01, C-02), `migrate_v2_13_lore_usage.py`,
  the JSON allow-list, the schema doc and changelog; `lore_usage.py` U0-U4.
- **B — capture the model exchanges** (no schema change):
  `model_exchange.py` (C-03), `prompt_load.RenderSpec` gains its prompt
  version, the four call sites append exchanges; `lore_usage.py` U5-U6.
- **C — journal the five Lore routes** (no schema change): `lore_usage.py`
  recorder (C-04), the routes (C-05); `lore_write.py` E1b wording;
  `lore_usage.py` U7-U10.
- **D — the panels carry their attempt** (no schema change):
  `writePanel.svelte.js`, `lore.svelte.js` (C-06), rebuilt `static/`;
  `lore_usage.py` U11.
- **E — the reader** (no schema change): `scripts/export_lore_usage.py`
  (C-07), the CLAUDE.md invariant; `lore_usage.py` U12.

## Dependency graph

Strictly sequential, A → B → C → D → E.

- B's U6d hands captured exchanges to A's writer.
- C wires A's writer (through the recorder) and B's capture into the routes.
- D sends the `attempt_id` field C's request bodies accept. C works without
  D (a missing id is minted per request), so D could run right after C only.
- E reads A's table and asserts what C and D filled (U12 runs after U8-U9).
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/lore_usage.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`.
- A creates `lore_usage.py` because every Machine arrow of the ticket must
  resolve from `brief` status on (`pipeline_state.py`).

## RECON

Opened on `main` at `d9c5a6a` (merge of PR #133, `ticket/0102`). Then
prototyped on a copy (branch `proto/0103`): every brief's commit ran the
full corpus green (137/137 from A on, 136/136 on `main`, with
`WORLD_ENGINE_ENV=test`), and the five diffs replayed in order on a clean
worktree of `main` reproduce the prototype tree exactly (generated files
regenerated: only the build manifest's `built_at` timestamp differs).
Findings tagged [M] were measured.

### R-01 — what the writing path keeps today [M]
Opened: `src/world_engine/models/pipeline.py:333-361` (`LoreEntry`,
`LoreEntryRow`), `src/world_engine/writes/lore_entries.py:19-47`.
Finding: only a successful commit leaves a trace: `lore_entry` (statement,
questions, answers) and one `lore_entry_row` per canon row written. Both
carry `world_id` and are deleted by the world cascade.
Consequence: the draft, abandoned attempts, refusals and model replies are
not recoverable today; the journal is a new table, not an extension of
`lore_entry` (whose rows die with their world, F2).

### R-02 — the draft is client-held, the draft routes write nothing [M]
Opened: `src/world_engine/cockpit/routes/lore_write.py:15` (« nothing is
written by a draft route, ever »), `:60-90`; `tooling/verify/checks/
lore_write.py:63` (E1b) and `:113` (`_COUNTED_TABLES`).
Finding: `/questions` and `/draft` return their result and write no row;
E1b asserts that no draft request changes the count of `_COUNTED_TABLES`
(`entity, fact, fact_participant, fact_default, knowledge, relation,
faction_membership, lore_entry, lore_entry_row`).
Consequence: journaling a draft makes these routes write; E1b stays true
(the journal is not counted) and its wording is narrowed in C; the route
docstring says « no canon row ».

### R-03 — the panel keeps refs stable [M]
Opened: `frontend/src/lore/writePanel.svelte.js:31-38` (`blank()`), `:75-88`
(`draftNow`), `:139-141` (`removeAt` splices), `:170-200` (`toProposal`:
an entity kept « en texte » is dropped and becomes a `mentions` entry),
`:210-213` (`restart`).
Finding: the server assigns `e1…`/`f1…` refs to a draft; the panel edits in
place, never renumbers, and adds `k<n>` refs for knowers it adds.
Consequence: the analysis can pair a draft and its committed proposal by
`ref` (D1); nothing needs diffing at write time.

### R-04 — the prompt version is read, then dropped [M]
Opened: `src/world_engine/prompt_load.py:35-38` (`RenderSpec`: three
strings), `:61-66`; `src/world_engine/prompt_store.py:19`
(`current_prompt` returns the `PromptVersion` row); `models/pipeline.py`
`PromptVersion` (`id`, `version_number`).
Finding: `load` has the version row in hand and returns only its text and
the model. One constructor of `RenderSpec` exists (enumeration E2).
Consequence: `RenderSpec` gains `version_id` and `version_number`, required
(B); no other constructor to adapt.

### R-05 — the Lore shell's model calls [M]
Opened: enumeration E1; `src/world_engine/lore_plan.py:79-111`,
`lore_render.py:249-284`, `lore_write_draft.py:112-122, 135-140, 238-266`.
Finding: three `chat(` sites serve four usages: `lore_question_to_plan`
(`draft_plan`), `lore_rows_to_prose` (`_call_model`, `answered` verdict
only), `lore_statement_questions` and `lore_statement_to_proposal` (one
`_call`). The raw reply goes straight to `llm_parse.extract_object`; a parse
failure loses it.
Consequence: each site records its exchange before parsing (B). Callers of
these four functions: enumeration E9 (two routes, one check).

### R-06 — the renderer is Session-free; the panel and the pipeline do not import each other [M]
Opened: `tooling/verify/checks/lore_isolation.py:44-46` (R10, implementation
`check_render_isolation` 537-566: no `Session` name, no `select(`, no
`db.add(`/`.commit(`), `:59-66` and `:91-104` (R17, `PANEL_FILES`,
`PIPELINE_FILES`, implementation 706-746).
Finding: `lore_render.py` may import plain modules; R17 forbids imports
between the panel modules and `lore_selectors, lore_query, lore_plan,
lore_render, lore_prompt`, both ways.
Consequence: the capture lives in a neutral module (`model_exchange.py`,
the `prompt_load.py` precedent), holding plain strings only; U5 forbids it
any `world_engine` import.

### R-07 — the consultation route [M]
Opened: `src/world_engine/cockpit/routes/lore.py:34-46, 76-131`;
`lore_isolation.py` R6 (`:21`, no `chat(`/`select(` call in the route),
R7 (`:24`, no `draft_plan` in resolve), R16 (`:37` and implementation
311-389: every `except` naming `OllamaError` in `ask_lore` raises
`HTTPException(detail=<named constant>)`).
Finding: `ask_lore` pings Ollama (503 + `PLANNER_UNAVAILABLE_MESSAGE` when
down), then `draft_plan` with only `LlmParseError` caught (502): an
`OllamaError` raised by the plan's own `chat` call is unhandled (500).
`resolve_lore` validates the plan and bindings (422) and never redrafts.
Neither route writes (enumeration E3).
Consequence: C catches the mid-plan `OllamaError` too, journals it as
`unavailable`, and answers the same named 503 (R16 holds by construction).

### R-08 — the writing route's commit discipline [M]
Opened: `tooling/verify/checks/lore_write.py:606-619` (E2 implementation:
the route file contains no `select(`/`chat(` substring, and its `.commit(`
calls all sit in `write_commit`, exactly one).
Finding: a second `.commit(` anywhere in the route file fails E2.
Consequence: the routes never commit a journal row themselves: the
recorder's `record` commits (C-04); `write_commit` keeps its one commit,
which also carries the `ok` journal row (`stage`).

### R-09 — `apply_proposal` annotates its input [M]
Opened: `src/world_engine/lore_write_apply.py:72-93`
(`_validate_entities`: `item["_type"] = …` at 84 and 89).
Finding: the proposal dict the route passes is mutated during validation.
Consequence: `write_commit` deep-copies the proposal before applying it and
journals the copy (found by the prototype's U8c).

### R-10 — what the world cascade calls a world's table [M]
Opened: `tooling/verify/checks/world_cascade.py:9-14` (W1) and its
implementation `_reaching_tables` 208-224.
Finding: a table is world-reaching if it has a `world_id` column or a FK to
a world-reaching table; every such table must be named by
`delete_world_cascade`.
Consequence: I1 — the journal has `world_ref` and `world_name`, no
`world_id`, no FK at all; U1 asserts it, U4 proves a row outlives its world.

### R-11 — JSON columns and `json.loads` are gated [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-102` (volet c: every
`Column(JSON` is a named allow-list entry), `tooling/verify/checks/
llm_parse_chokepoint.py:3-16` (a `json.loads` site in `src/` must be the
chokepoint or allow-listed).
Finding: both gates are fail-closed on a new site.
Consequence: A allow-lists `LoreUsageEvent.payload` and `.model_calls` with
their reason; the recorder copies payloads with
`fastapi.encoders.jsonable_encoder` (no `json.loads`; `fastapi` is already
imported outside `cockpit/`, enumeration E11).

### R-12 — schema version and migrations [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.12"`),
`world-engine-schema.md:3`, `world-engine-schema-changelog.md:16`,
`scripts/migrate_v2_12_zone_borde.py:67` (`_PREVIOUS_VERSION = "v2.11"`),
`scripts/migrate_v2_11_lore_entry.py` (the additive-table template),
`tooling/verify/checks/schema_version_agreement.py`, `schema_partition.py`.
Finding: v2.12 is current; constant, header and newest changelog entry move
together; earlier migrations converge `schema_meta` to the code constant;
no check pins `"v2.12"` (enumeration E4).
Consequence: v2.13, purely additive, refuses a database below v2.12.

### R-13 — sessions and transactions [M]
Opened: `src/world_engine/db.py:89-147` (WAL, explicit BEGIN), `:157-161`
(`get_session`); `src/world_engine/cockpit/routes/day.py:613-621` (X1b:
rollback, write the record, commit, on the refused path).
Finding: one request-scoped session; the X1b precedent journals a refusal
after a rollback, on the same session.
Consequence: `record` commits on the request session (a draft or a
consultation has nothing else staged); a refused commit rolls back first.

### R-14 — the panels' flows [M]
Opened: `frontend/src/lore/WritePanel.svelte:41` (« Recommencer » →
`restart()`), `:72-75`, `:195` (« Relancer la proposition » →
`makeDraft()`); `frontend/src/lore/lore.svelte.js:14-20, 22-40, 58-81,
83-88`; `tooling/verify/checks/lore_write.py:622-640` (F1b: the exact set
of paths `writePanel.svelte.js` calls).
Finding: a writing use runs text → questions → draft(s) → commit, restarted
by « Recommencer » or a world change; a consultation runs ask →
(resolve). Both state modules are plain `$state` objects.
Consequence: the attempt id is minted by the client per use (C-06) and sent
in the existing request bodies — no new path, F1b unchanged.

### R-15 — scripts and CLAUDE.md budgets [M]
Opened: `tooling/verify/checks/env_guard.py:7-15` (a script importing the
engine carries a fail-closed env guard before the import),
`tooling/verify/checks/claude_md_contract.py:12-14, 69-71` (38 000
characters, 100 per line, File structure ≤ 80 lines); enumeration E5.
Finding: CLAUDE.md is at 36 922 characters and its File structure section
at exactly 80 lines.
Consequence: the export carries the migration's guard; E adds one
invariant and no File structure line.

### R-16 — checks that call the Lore routes [M]
Opened: enumeration E8; `tooling/verify/checks/lore_write.py:530-603`,
`origin_guard.py`.
Finding: `lore_write.py` posts to the writing routes and `origin_guard.py`
posts through the guard; neither counts a table the journal touches.
Consequence: both stay green unchanged except for E1b's wording (C);
their journal rows land in their own temp databases.

### R-17 — the frontend build is checked fresh [M]
Opened: `tooling/verify/checks/frontend_build_fresh.py:14-17, 119-133`.
Finding: `static/.build-manifest.json` must carry the hash of the current
`frontend/` sources.
Consequence: D rebuilds and commits `static/`.

## Contract sheet

### C-01 — `writes/lore_usage.write_usage_event`
Produced by: BRIEF-0103-A   Consumed by: BRIEF-0103-C (through C-04), U3, U6d
Signature: `write_usage_event(db, *, attempt_id: str, world_ref: str,
world_name: str, kind: str, step: str, outcome: str, payload: dict,
model_calls: list[dict], lore_entry_ref: Optional[str] = None) ->
LoreUsageEvent`. Adds the row; never commits.
Table `lore_usage_event`: `id, attempt_id, world_ref, world_name, kind,
step, outcome, payload JSON, model_calls JSON, lore_entry_ref, created_at`;
no `world_id`, no FK. `LORE_USAGE_STEPS = {"write": ("questions", "draft",
"commit"), "consult": ("ask", "resolve")}`; `LORE_USAGE_OUTCOMES = ("ok",
"unavailable", "parse_error", "refused")`.
Error cases (`ValueError`): empty `attempt_id`/`world_ref`/`world_name`; a
`(kind, step)` outside `LORE_USAGE_STEPS`; an unknown outcome; a payload
not carrying exactly `PAYLOAD_KEYS[step]`; `payload["error"]` None on a
non-`ok` outcome or set on `ok`; a model call not carrying exactly
`MODEL_CALL_KEYS` or with an empty `usage`; `lore_entry_ref` set anywhere
but on `commit`/`ok`, or missing there.

### C-02 — the journal's two key families
Produced by: BRIEF-0103-A   Consumed by: B (U5), C, E
`MODEL_CALL_KEYS = {usage, prompt_version_id, prompt_version_number, model,
system_prompt, user_message, raw_output, error}`.
`PAYLOAD_KEYS` (one entry per step; written before any member, re-read
after the fifth):
- `questions`: `statement, questions, error`
- `draft`: `statement, answers, draft, error`
- `commit`: `proposal, result, error`
- `ask`: `question, response, error`
- `resolve`: `question, plan, bindings, response, error`
`error` is None on `ok` and the message the creator was shown otherwise;
the answer key (`questions`, `draft`, `result`, `response`) is None when the
step did not answer.

### C-03 — `model_exchange` and the capturing call sites
Produced by: BRIEF-0103-B   Consumed by: BRIEF-0103-C
`ModelExchange` dataclass, fields exactly `MODEL_CALL_KEYS` (U5);
`to_record() -> dict`. `begin(exchanges, usage, spec, system_prompt,
user_message) -> Optional[ModelExchange]` appends and returns a new
exchange (None when `exchanges` is None); `fail(exchanges, exc)` sets
`"<Type>: <message>"` on the last exchange without an error.
`RenderSpec(system_prompt, user_template, model, version_id: str,
version_number: int)`.
Call-site family (written before any member, re-read after the fourth):
- `lore_plan.draft_plan(question, world_id, db, exchanges=None)`, usage
  `PLAN_USAGE = "lore_question_to_plan"`
- `lore_render.render(result, question, spec, candidates, exchanges=None)`,
  usage `PROSE_USAGE = "lore_rows_to_prose"`, `answered` only; an
  `OllamaError` is recorded by `fail` before the template fallback
- `lore_write_draft.draft_questions(db, world_id, statement,
  exchanges=None)`, usage `QUESTIONS_USAGE`
- `lore_write_draft.draft_proposal(db, world_id, statement, answers="",
  exchanges=None)`, usage `PROPOSAL_USAGE`
Each assigns `raw_output` as soon as `chat` returns, before parsing.
Without a list each behaves exactly as before.

### C-04 — the recorder `lore_usage`
Produced by: BRIEF-0103-C   Consumed by: the two Lore route modules
`attempt_id(raw) -> str` (canonical UUID, or a fresh `uuid4` for None, ''
or malformed); `stage(db, *, attempt, world_id, kind, step, outcome,
payload, exchanges=None, lore_entry_ref=None)` (reads the world's name now;
`WORLD_NAME_UNKNOWN = "(monde introuvable)"` when the id matches no world;
payload and model calls copied through `jsonable_encoder`; never commits);
`record(db, **same)` = `stage` + `db.commit()`.

### C-05 — what each route journals
Produced by: BRIEF-0103-C   Consumed by: D, E, the analysis
Family (five routes; written before any member, re-read after the fifth).
Only requests that reach the model or the apply step are journaled.
- `POST /api/lore/write/questions` → `write/questions`: `ok` (questions),
  `unavailable` (503, `WRITE_UNAVAILABLE_MESSAGE`), `parse_error` (502).
  `record`.
- `POST /api/lore/write/draft` → `write/draft`: `ok` (the draft as
  returned), `unavailable`, `parse_error`. `record`.
- `POST /api/lore/write/commit` → `write/commit`: `ok` staged in the
  commit's transaction with `lore_entry_ref`; `refused` (422
  `ProposalError`, or an `HTTPException` from the entity creator) recorded
  after the rollback. The proposal as received (deep copy, R-09).
- `POST /api/lore/ask` → `consult/ask`: `unavailable` (ping down, or an
  `OllamaError` from the plan's call, 503 `PLANNER_UNAVAILABLE_MESSAGE`),
  `parse_error` (502), `ok` (the response body as returned, exchanges
  `[plan, prose?]`). `record`.
- `POST /api/lore/resolve` → `consult/resolve`: `refused` (422 malformed
  plan or binding), `ok` (response body, exchanges `[prose?]`). `record`.
Response bodies are unchanged.

### C-06 — the attempt id on the wire
Produced by: BRIEF-0103-C (server field), BRIEF-0103-D (client)
Consumed by: the journal, the export
Every request body of the five routes accepts an optional `attempt_id`.
The writing panel mints `crypto.randomUUID()` in `blank()` (each new use:
first load, « Recommencer », a world change) and sends it on questions,
draft and commit; the consultation panel mints one per `askLore()` and
reuses it in `confirmResolution()`; `reloadForWorld()` clears it.

### C-07 — the export line
Produced by: BRIEF-0103-E   Consumed by: the analysis session
One JSON line per `(attempt_id, world_ref, kind)`, in start order:
`attempt_id, kind, world_ref, world_name, started_at, ended_at, committed
(true/false for write, null for consult), lore_entry_refs, events: [step,
outcome, created_at, payload, model_calls, lore_entry_ref]`. Options
`--out` (required, refused inside the repository), `--since`,
`--world-ref`. Read-only.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| a commit leaves `lore_entry` + `lore_entry_row`, world-scoped | R-01 | `models/pipeline.py`, `writes/lore_entries.py` |
| draft routes write nothing; E1b counts `_COUNTED_TABLES` only | R-02 | `routes/lore_write.py`, `lore_write.py` check (implementation 530-603) |
| the panel never renumbers refs; « en texte » drops the entity | R-03 | `writePanel.svelte.js` |
| `load` has the version row; one `RenderSpec` constructor | R-04 | `prompt_load.py`, `prompt_store.py`, E2 |
| three `chat(` sites, four usages, parse right after `chat` | R-05 | `lore_plan.py`, `lore_render.py`, `lore_write_draft.py`, E1 |
| renderer Session-free; panel/pipeline import ban | R-06 | `lore_isolation.py` (implementations of R10, R17) |
| mid-plan `OllamaError` unhandled; R16 shape | R-07 | `routes/lore.py`, `lore_isolation.py` (R16 implementation) |
| one commit, in `write_commit` only | R-08 | `lore_write.py` check (E2 implementation) |
| `apply_proposal` mutates its input | R-09 | `lore_write_apply.py` |
| world-reaching = `world_id` or FK | R-10 | `world_cascade.py` (`_reaching_tables`) |
| JSON columns allow-listed; `json.loads` gated | R-11 | `json_ui_boundary.py`, `llm_parse_chokepoint.py` |
| schema at v2.12; no pinned literal | R-12 | `schema_version.py`, schema doc, changelog, E4 |
| WAL; request session; X1b precedent | R-13 | `db.py`, `routes/day.py` |
| panel flows; F1b path set | R-14 | `WritePanel.svelte`, `lore.svelte.js`, `lore_write.py` check (F1 implementation) |
| env guard; CLAUDE.md budgets | R-15 | `env_guard.py`, `claude_md_contract.py`, E5 |
| checks posting to Lore routes | R-16 | E8, `lore_write.py`, `origin_guard.py` |
| build freshness by source hash | R-17 | `frontend_build_fresh.py` |

Presuppositions: no brief says « follow the existing convention »; each
pattern it reuses is named with its file (the v2.11 migration, the
`lore_write.py` census, the X1b precedent, `prompt_load.py` as neutral
module).

### (b) Case tables

**Outcome by route and failure class** (C-05):

| Route | ok | Ollama down | reply unparsable | refused | not journaled |
|---|---|---|---|---|---|
| questions | `ok` 200 | `unavailable` 503 | `parse_error` 502 | — | no world (400), empty text (422), non-local origin (403) |
| draft | `ok` 200 | `unavailable` 503 | `parse_error` 502 | — | same |
| commit | `ok` 200, staged in commit | — (no model) | — | `refused` 422 (`ProposalError`, creator `HTTPException`) | no world, non-local origin |
| ask | `ok` 200 (any verdict) | `unavailable` 503 (ping or plan call) | `parse_error` 502 | — | non-local origin |
| resolve | `ok` 200 | — (render falls back, `ok`) | — | `refused` 422 | non-local origin |

Every cell is reached by the prototype's U8/U9 except: commit refused by a
creator `HTTPException` (same code path as `ProposalError`, after its own
rollback; not separately exercised) and resolve with Ollama down (render
falls back to the template, outcome `ok`, exchange carries the error — U6b
exercises the renderer half).

**Attempt boundaries** (C-06): new attempt on first load of the writing
panel, « Recommencer », world change, each new question; same attempt on
« Relancer la proposition », a commit retried after a refusal, a
disambiguation round.

### (c) Enumerations

```
--- E1 chat( in Lore modules
src/world_engine/lore_plan.py:93:    raw = chat(
src/world_engine/lore_render.py:255:    raw = chat(
src/world_engine/lore_write_draft.py:117:    raw = chat(
src/world_engine/cockpit/routes/lore.py:3:Thin orchestration only -- no `chat(`, no `select(` here, matching the
--- E2 RenderSpec( constructors in src/ tooling/verify scripts/
src/world_engine/prompt_load.py:62:    return RenderSpec(
--- E3 writes in Lore consultation route/pipeline
(end)
--- E4 v2.12 literal in checks
(end)
--- E5 File structure section lines
80
36922 CLAUDE.md
--- E7 lore_usage names in src
(end)
--- E8 checks posting to Lore routes
tooling/verify/checks/lore_isolation.py
tooling/verify/checks/lore_write.py
tooling/verify/checks/origin_guard.py
--- E9 callers of draft_plan / render / draft_questions / draft_proposal
src/world_engine/cockpit/routes/lore_write.py:64:        questions = _draft.draft_questions(db, world_id, _statement(body))
src/world_engine/cockpit/routes/lore_write.py:76:        return _draft.draft_proposal(db, world_id, _statement(body), body.answers or "")
src/world_engine/cockpit/routes/lore.py:84:    rendered = _lore_render.render(result, question, spec, candidates)
src/world_engine/cockpit/routes/lore.py:107:        plan = _lore_plan.draft_plan(body.question, body.world_id, db)
tooling/verify/checks/lore_write.py:492:            questions = lwd.draft_questions(db, world, statement)
tooling/verify/checks/lore_write.py:493:            draft = lwd.draft_proposal(db, world, statement, "Tout le monde au manoir.")
tooling/verify/checks/lore_write.py:494:            for call in (lambda: lwd.draft_questions(db, world, statement),
tooling/verify/checks/lore_write.py:495:                         lambda: lwd.draft_proposal(db, world, statement)):
--- E11 fastapi imports outside cockpit/
src/world_engine/context_window.py
src/world_engine/npc_group_author.py
src/world_engine/link_author.py
```

E3 is the commands `grep -nE "db\.add\(|\.commit\(|db\.delete\(" ` over
`routes/lore.py lore_query.py lore_plan.py lore_render.py
lore_selectors.py`; E8 matched `lore_isolation.py` on decorator strings
only (it posts nothing). E8's criterion: a check file naming a Lore route
path.

### (d) Contract families
C-02 (`PAYLOAD_KEYS`), C-03 (call sites) and C-05 (routes) were written
before their members and re-read after the last one. ✔

### (e) Gates and the modules that satisfy them

| Gate | Proposed or passed | Satisfied by | What it forbids that the module needs |
|---|---|---|---|
| `lore_usage.py` U0-U12 | proposed | A-E's files | nothing |
| `world_cascade.py` W1 | passed | `models/pipeline.py` (no `world_id`, I1) | a `world_id` column — removed by I1 |
| `json_ui_boundary.py` volet c | passed | its allow-list (two entries, A) | — |
| `llm_parse_chokepoint.py` | passed | `lore_usage.py` uses `jsonable_encoder` | a `json.loads` copy — avoided |
| `lore_isolation.py` R6, R7, R10, R16, R17 | passed | `routes/lore.py`, `lore_render.py`, `model_exchange.py` (neutral) | a Session in the renderer; a panel/pipeline import — avoided |
| `lore_write.py` E1, E2, F1 | passed (E1b reworded) | `routes/lore_write.py` (one commit), `lore_usage.record` | a second commit in the route file — moved to the recorder |
| `env_guard.py` | passed | `export_lore_usage.py` guard (b) | — |
| `claude_md_contract.py` | passed | one invariant, no tree line | a File structure line — over budget |
| `frontend_build_fresh.py` | passed | D's rebuild | — |
| `schema_version_agreement.py`, `schema_partition.py` | passed | A's constant, header, changelog | — |
| `decisions_index.py` | passed | regenerated index, each brief | — |

## Amendments

(none)
