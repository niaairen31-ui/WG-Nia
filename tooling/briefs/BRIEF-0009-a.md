<!-- slug: model-selection-write-path -->
# BRIEF-0009-a — Per-template local model selection: write path, live list, cockpit selector

Ticket: TICKET-0009 · Recon: RECON-0009 · Schema: **none** (no migration, no
version bump — the column shipped in v1.67, BRIEF-0008-a)

---

## Context

TICKET-0009 asks for per-template selection of the local Ollama model in the
prompt management tool, with the selectable list being exactly the models
installed in Ollama on Nia's machine (live: `ollama pull`/`rm` reflected
without restart).

RECON-0009 established that BRIEF-0008-a/-b already shipped half the design:

- `prompt_template.model` exists, nullable TEXT (`src/world_engine/models.py:794-796`).
- `prompt_registry.effective_model(template, default)` is the single
  resolution accessor (`src/world_engine/prompt_registry.py:40-42`), consumed
  at every templated call site (`analyzer.py:474,753`;
  `entity_author.py:412,537,626,714`; `region_author.py:338,414`;
  `cockpit/app.py:1836,2556,4005,4041`).
- `ollama_client.ping()` already returns the installed model names from
  `GET {OLLAMA_HOST}/api/tags`, raising `OllamaError` with a human-readable
  message when unreachable (`src/world_engine/ollama_client.py:73-85`).
- Read-only routes `GET /api/prompts` and `GET /api/prompts/{id}` expose
  `model`, `default_model`, `effective_model`, effective-row resolution and
  shadowing (`src/world_engine/cockpit/crud.py:1596-1710`).
- The cockpit Prompts sub-tab is read-only
  (`src/world_engine/cockpit/index.html:1165, 1351`, detail rendering
  `modèle effectif : <b>X</b> (override : Y)` near `:3655`).

What does not exist — and is exactly this brief — is the write path:
`prompt_registry.py:9-11` says `model` stays NULL on every row "until a
write path ships".

Locked decisions: **A1** (nullable column — already shipped), **B1** (live
list, zero persistence), **C1+C3** (save-time validation + visible badge,
never silent fallback), **D** (no Claude category; `model` is generic, its
only reader is the local path), **S-null** (seed stays NULL; the
`WORLD_ENGINE_OLLAMA_MODEL` env channel of 0008-a stays intact), **W1**
(model-only PATCH), **V1** (fail-closed validation).

## Scope IN

### 1. `GET /api/ollama/models` — live model list

- Thin wrapper over `ollama_client.ping()`. No cache, no table, no sync.
- Success: `200 {"models": ["name", ...]}` — the list exactly as `ping()`
  returns it (order preserved; no filtering, no sorting mandate).
- `OllamaError` → `503` with the error's own message as `detail`. Never a
  `200` with an empty list when Ollama is unreachable (no empty-list
  masquerade).
- Placement: beside the existing prompts read routes in
  `src/world_engine/cockpit/crud.py` (adjacent to `GET /api/prompts`,
  `crud.py:1596`), keeping the prompt-tool surface in one place. The route
  reads no DB and writes nothing.
- Inherits `OLLAMA_HOST` by construction (it is `ping()`'s default,
  `ollama_client.py:21,73`). No new configuration of any kind.

### 2. `PATCH /api/prompts/{prompt_id}/model` — the write path (W1)

- Body: `{"model": string | null}`. This route writes `model` and
  `updated_at` and NOTHING else — full template editing is Scope OUT.
- `prompt_id` unknown → `404` (same message style as
  `get_prompt_detail`, `crud.py:1630-1631`).
- `model` is a non-empty string → **C1 validation, fail-closed (V1)**:
  - Call `ollama_client.ping()`. `OllamaError` → `503` with the message,
    row untouched. Setting an override requires Ollama running; this is
    deliberate, not incidental.
  - Value not in the returned list → `422` with an explicit message naming
    the value and stating it is not installed in Ollama. Row untouched.
  - Value in the list → write it, bump `updated_at`, commit.
- `model` is `null` (or empty string, normalized to NULL) → always
  accepted, **no `ping()` call** — clearing an override must work with
  Ollama down.
- Response: the same summary shape as `_prompt_row_summary`
  (`crud.py:1585-1594`) plus `effective_model` recomputed via
  `prompt_registry.effective_model` and the usage's
  `PROMPT_REGISTRY` `default_model()` — so the UI can re-render from the
  response alone.
- **No `change_history` row.** `prompt_template` is creator-CRUD
  state-setting territory (same posture as every other creator CRUD write);
  `updated_at` is the only trace. This is the existing doctrine, restated —
  not a new exception.

### 3. Cockpit — selector, default rendering, badge (C3)

In the Prompts sub-tab (`index.html`, panel at `:1351`, detail renderer
near `:3626-3660`):

- **On entering the detail view** (and on re-entering the sub-tab), fetch
  `GET /api/ollama/models` once and hold the list in client view-state
  (same no-persistence posture as `lieuxBrowse*` view-state — reset on
  fresh tab entry, never stored server-side).
- **Selector**: replace the static override display with a `<select>`:
  - First option: `Défaut (⟨default_model⟩)` where `⟨default_model⟩` is the
    detail payload's `default_model` field — this option maps to
    `{"model": null}`.
  - One option per name returned by the live endpoint.
  - Current state preselected: NULL → the default option; an override →
    its name.
  - On change: `PATCH` immediately; on success re-render the
    `modèle effectif` line from the response; on error (`422`/`503`)
    display the server's `detail` message visibly next to the selector and
    revert the selection to the stored value. No optimistic UI.
- **Stored override absent from the live list** (the model was removed
  from Ollama after being saved):
  - Detail view: render a visible `⚠ modèle absent` badge next to the
    selector; the stored value appears as a marked, non-selectable entry
    (visible truth, not a save candidate — re-saving it is refused
    server-side by C1 anyway).
  - Master list (`_promptsRenderUsageCard` rows): the same badge on any
    row whose `model` is non-NULL and not in the live list. Comparison is
    client-side against the one fetched list.
- **Ollama unreachable when the tab loads** (`503` from the list
  endpoint): the selector area shows the error message and falls back to
  the current read-only display. No empty dropdown, no silent degradation.
  Badges are simply not computed (no list to compare against) — absence of
  signal, never a wrong signal.

### 4. Verify check

`verify/checks/NNNN.py` (deterministic, no Ollama dependency for the parts
that don't need it; where the check exercises C1 it may stub/monkeypatch
`ping`):

- `PATCH /api/prompts/{id}/model` exists; `{"model": null}` accepted and
  clears the override with `updated_at` bumped; unknown id → 404.
- With `ping` stubbed to `["m1", "m2"]`: `{"model": "m1"}` → 200 and
  persisted; `{"model": "zz"}` → 422, row unchanged.
- With `ping` stubbed to raise `OllamaError`: non-null save → 503, row
  unchanged; null save → still 200.
- `GET /api/ollama/models`: stub list → 200 with exactly that list; stub
  raise → 503, and the body is not an empty list.
- Grep-level guard: no new `\.model` dispatch read outside
  `prompt_registry.effective_model` (the two GET routes' display reads in
  `crud.py` are the sanctioned exceptions, they already exist).
- `scripts/seed_pilot.py` sets no `model=` on any `prompt_template` row
  (S-null intact).

## Scope OUT (named deferrals)

- Full template text editing (`system_prompt`, `user_template`, `notes`,
  `is_active`, `version`) — separate chantier; this PATCH writes `model`
  only.
- Per-template inference parameters (temperature, `num_ctx`,
  `repeat_penalty`…) — `NPC_DIALOGUE_OPTIONS` / `MJ_NARRATION_OPTIONS`
  stay code constants (`ollama_client.py:30,33`).
- Model management from the cockpit — the cockpit lists, it never `pull`s
  or `rm`s.
- Any `claude_api`-side reader of `model` (decision D: no Claude category;
  a future Claude-side reader is its own chantier with its own reader).
- Remote-Ollama configuration UI — `OLLAMA_HOST` env already covers it.
- `change_history` on prompt template edits — existing creator-CRUD
  posture, unchanged.
- The latent nondeterminism of `_effective_prompt_row` for
  non-world-scoped usages with 2+ active rows (`crud.py:1566-1583`) —
  accepted observation from 0008, untouched here.

## Invariants to defend

- **Single resolver.** All model dispatch routes through
  `prompt_registry.effective_model`; this brief adds no second resolver and
  no direct `template.model` dispatch read outside it.
- **S-null / env channel.** Seeded rows keep `model = NULL`;
  `WORLD_ENGINE_OLLAMA_MODEL` continues to show through for NULL-model
  templates (0008-a's documented read-time-callable design,
  `prompt_registry.py:20-26`).
- **Never silent fallback.** A stored-but-removed model produces a visible
  badge and, at call time, the natural `OllamaError` ("pull it first",
  `ollama_client.py:118-122`) — never a quiet substitution of the default.
- **No schema change.** No version bump, no migration, no new column, no
  new table. `danger_class: [db_write]` only.
- **Two sanctioned canon-write paths unaffected.** This PATCH is creator
  CRUD state-setting on a non-canon table; `_apply_mutation` and the
  narrative pipeline are untouched.
- **History is sacred where it applies** — and explicitly does not apply
  here (no `change_history` for creator CRUD; restated, not weakened).

## Done-means checklist

### Machine-checkable → G1 deterministic gate (`verify/checks/NNNN.py`)
- [ ] PATCH route: null-accept, valid-accept, invalid-422, unknown-404,
      `updated_at` bump, model-only write
- [ ] V1 fail-closed: ping-raise → 503 on non-null, 200 on null, row
      unchanged on every failure path
- [ ] List route: 200 exact list / 503 with message, never empty-list
      masquerade
- [ ] No second resolver (grep guard)
- [ ] `seed_pilot.py` model-free (S-null)

### Live → human gate (Nia)
- [ ] Le dropdown liste exactement la sortie d'`ollama list` ; après
      `ollama pull`/`ollama rm`, rouvrir l'onglet reflète le changement
      sans redémarrage
- [ ] Changer le modèle d'un template change le modèle réellement invoqué
      à l'appel suivant (visible dans les logs Ollama / console serveur)
- [ ] Un template dont le modèle stocké a été retiré affiche le badge
      `⚠ modèle absent` ; re-sauvegarder cette valeur est refusé avec un
      message clair
- [ ] Un template NULL affiche `Défaut (⟨nom résolu⟩)` et se comporte à
      l'identique d'avant le changement
- [ ] `WORLD_ENGINE_OLLAMA_MODEL` transparaît toujours pour les templates
      NULL (canal 0008-a intact)
- [ ] Ollama éteint : l'onglet Prompts affiche l'erreur explicite dans la
      zone du sélecteur, retombe en lecture seule, aucun dropdown vide

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — append entry "PROMPT MODEL SELECTION —
  write path (BRIEF-0009-a, no schema change)": decisions S-null/W1/V1,
  the fail-closed rationale, the badge semantics, and the explicit
  "Schema: none" callout.
- `world-engine-schema.md` — no change (column already documented at
  v1.67). Changelog file: one line noting BRIEF-0009-a shipped with no
  schema change (the established convention for schema-free steps).
- `CLAUDE.md` — only if it currently states that `prompt_template.model`
  has no write path; if so, update that sentence. Otherwise untouched.
