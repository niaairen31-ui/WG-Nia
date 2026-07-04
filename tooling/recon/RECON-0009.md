# RECON-0009 — Per-template local model selection, live Ollama model list

Status: report-only. No action taken. All citations are `file:line` against
`niaairen31-ui/WG-Nia@main`, read via the unauthenticated raw channel
(TICKET-0006 asymmetric read path).

---

## 1. Already in place — shipped by BRIEF-0008-a/-b (schema v1.67)

The intake for TICKET-0009 assumed a green field. It is not. Roughly half of
the locked design already exists:

- **`prompt_template.model` column exists** — nullable TEXT, NULL = "code
  decides", non-NULL = creator override.
  `src/world_engine/models.py:794-796`.
- **The single resolution accessor exists and is the one the intake
  demanded** — `effective_model(template, default)` in
  `src/world_engine/prompt_registry.py:40-42`. Pure function, no DB access,
  no cockpit import. The structural invariant "resolution lives in exactly
  ONE accessor; call sites never re-implement the fallback" is already
  satisfied.
- **Every templated call site already routes through it**:
  - `src/world_engine/analyzer.py:474, 753`
  - `src/world_engine/entity_author.py:412, 537, 626, 714`
  - `src/world_engine/region_author.py:338, 414`
  - `src/world_engine/cockpit/app.py:1836, 2556, 4005, 4041` (and the
    downstream `model=model` propagation through `_stream`, e.g.
    `app.py:2814, 3133, 3458, 3646`)
- **Per-usage defaults are code facts in `PROMPT_REGISTRY`** —
  `default_model` is a zero-argument callable resolved at read time:
  `_game_model → ollama_client.DEFAULT_MODEL`,
  `_author_model → entity_author.AUTHOR_MODEL`.
  `src/world_engine/prompt_registry.py:45-51, 54-63`.
- **`DEFAULT_MODEL` is env-overridable** via `WORLD_ENGINE_OLLAMA_MODEL`
  (`src/world_engine/ollama_client.py:22-24`); `AUTHOR_MODEL` is the
  hardcoded `"llama3.1:8b"` (`src/world_engine/entity_author.py:38`).
  `OLLAMA_HOST` is likewise already an env default
  (`src/world_engine/ollama_client.py:21`) — intake question 2 (remote
  Ollama someday) is answered by construction: any list endpoint built on
  the existing client inherits it.
- **The live model list already has a function** —
  `ollama_client.ping(host, timeout) -> list[str]` reads
  `GET {host}/api/tags` and returns installed model names, raising
  `OllamaError` with a human-readable message when unreachable.
  `src/world_engine/ollama_client.py:73-85`. It is currently used only as a
  pre-analysis health check (`src/world_engine/cockpit/app.py:4502`); no
  route exposes the name list to the UI.
- **`chat()` / `chat_stream()` already accept `model`** —
  `src/world_engine/ollama_client.py:88-95, 211-217`.
- **Read-only prompt routes exist** — `GET /api/prompts` (master list,
  lazy, no bodies) and `GET /api/prompts/{id}` (detail), both exposing
  `model`, `default_model`, `effective_model`, effective-row resolution and
  shadowing. `src/world_engine/cockpit/crud.py:1596-1710`.
- **Cockpit Prompts sub-tab exists, read-only** —
  `src/world_engine/cockpit/index.html:1165` (tab button), `:1351`
  (panel, commented "read-only, one detail at a time"), detail renders
  `modèle effectif : <b>X</b> (override : Y)` (`index.html:~3655`).

## 2. The actual gap — what TICKET-0009 must build

`prompt_registry.py:9-11` states it plainly: `model` is NULL on every row
"until a write path ships". The gap is exactly:

1. **No write path for `model`.** The full route inventory of
   `cockpit/crud.py` (lines 496-1625) contains no PUT/PATCH/POST touching
   `prompt_template`. Nothing anywhere writes the column.
2. **No endpoint exposing the live model list** — `ping()` exists but is
   unexposed to the UI.
3. **No selector UI** — the detail panel displays the override but offers
   no control to set it.
4. **No save-time validation (C1)** — nothing checks a proposed `model`
   against the live tag list.
5. **No "model absent" badge (C3)** — the UI has no signal when a stored
   override no longer exists in Ollama.

## 3. Refuted intake assumptions — flagged, not silently adjusted

**R1 — no migration, no schema bump.** The intake ticket carried
`danger_class: [db_write, migration]` and `schema_version_touched: vX.YY`.
The column shipped in v1.67 (BRIEF-0008-a). TICKET-0009 touches no schema.
Ticket header must drop `migration` and set `schema_version_touched: none`.

**R2 — the Q1-seed decision is refuted by BRIEF-0008-a's documented
design.** Intake locked "seed explicit": `seed_pilot.py` writes the current
defaults into the seeded templates' `model` field. BRIEF-0008-a made the
opposite choice deliberately (`prompt_registry.py:9-12, 20-26`):

- `default_model` is a **callable resolved at read time** precisely so that
  an env override of `WORLD_ENGINE_OLLAMA_MODEL` "shows through". Writing
  explicit names into rows severs that channel: overridden templates would
  silently stop following the env var.
- NULL-on-every-row is the documented condition for "runtime behavior is
  bit-identical to before this module existed" — a stated invariant of the
  shipped brief.
- The visibility motivation for seeding explicit values is already met
  another way: the cockpit displays `default_model` and `effective_model`
  per usage today (`crud.py:1608-1614`, `index.html:~3655`).

**Recommendation: revert to seed-NULL.** The dropdown's NULL option renders
as `Défaut (⟨resolved name⟩)` so exhaustive visibility is preserved without
materializing anything. Requires Nia's re-confirmation (this reverses an
intake lock).

## 4. Design points to lock before brief (small)

- **W — write route shape.**
  - **W1 (recommended)** — `PATCH /api/prompts/{prompt_id}/model`,
    body `{"model": string | null}`. Model-only. Full prompt-text editing
    (system_prompt/user_template) is a separate chantier; bundling it here
    would violate one-chantier-per-brief.
  - W2 — general `PUT /api/prompts/{id}` editing the whole row. Rejected
    unless Nia wants to open template editing now.
- **V — C1 validation when Ollama is down at save time.**
  - **V1 (recommended)** — fail-closed: the PATCH returns 503 with the
    `OllamaError` message; the save is refused. Consistent with the
    no-silent-fallback posture; a model override is only meaningful with
    Ollama running.
  - V2 — fail-open (accept unvalidated). Rejected: silent divergence.
- **L — list endpoint shape.** `GET /api/ollama/models`, thin wrapper over
  `ollama_client.ping()`: 200 `{"models": [...]}` or 503 with the explicit
  error message — never an empty-list masquerade. Lives beside the other
  cockpit routes; inherits `OLLAMA_HOST` by construction.

## 5. Observations (report-only, no action)

- `_effective_prompt_row` documents an accepted latent nondeterminism for
  non-world-scoped usages with 2+ active rows (`crud.py:1566-1583`).
  Unaffected by this ticket; noted because the badge (C3) renders per row,
  not per usage, so no interaction.
- `prompt_template` is creator-CRUD territory (state-setting path): no
  `change_history` row exists for template edits today, and the PATCH
  should follow the same posture — `updated_at` bump only, consistent with
  the two-sanctioned-write-paths doctrine.
- Preview routes (`app.py:123, 167`) and the dry-run surface read
  `effective_model` already; a saved override will show through them with
  zero additional wiring.
