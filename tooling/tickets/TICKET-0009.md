---
id: TICKET-0009
title: Per-template local model selection, live Ollama model list
type: feature
status: recon
created: 2026-07-03
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: small
brief_ids: []
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Ajouter la modification du modèle d'IA local utilisé à mon outil de gestion
des prompts. Je veux que la liste des modèles disponibles soit celle des
modèles que je peux runner avec Ollama, disponibles sur mon ordinateur.
Donc si j'en ajoute ou que j'en enlève, ils s'ajoutent automatiquement aux
modèles que je peux sélectionner.

## Clarifications resolved (intake + RECON)

- **A1 — already satisfied by BRIEF-0008-a (schema v1.67).** Nullable
  `model` column on `prompt_template` exists (`models.py:794-796`); the
  single resolution accessor `prompt_registry.effective_model` exists and
  is consumed at every templated call site. NO schema change in this
  ticket; NO migration; `danger_class` reduced to `[db_write]`.
- **B1 — live list, reusing `ollama_client.ping()`.** New cockpit endpoint
  `GET /api/ollama/models`, thin wrapper over `ping()`
  (`ollama_client.py:73-85`): 200 `{"models": [...]}` or 503 carrying the
  explicit `OllamaError` message — never an empty-list masquerade. No
  cache, no table, no sync. Inherits `OLLAMA_HOST` env by construction.
- **C1+C3 — save-time validation + visible badge, never silent fallback.**
  The write route rejects a non-NULL `model` absent from the live tag list
  (4xx, explicit message); NULL always accepted. If a stored model is later
  removed from Ollama, the chat call fails with the natural Ollama error
  (`ollama_client.py:118-122` already produces the human-readable "pull it
  first" message). Cockpit shows a "modèle absent" badge on any row whose
  stored `model` is not in the live list.
- **D (no Claude category)** — `model` is a generic field, always present.
  No destination-conditional UI, no claude_api branch anywhere. Its only
  reader is the local Ollama call path via `effective_model`; a future
  Claude-side reader is a separate chantier.
- **W1 — write route is model-only.** `PATCH
  /api/prompts/{prompt_id}/model`, body `{"model": string | null}`.
  Full prompt-text editing (system_prompt / user_template) is explicitly
  NOT this chantier.
- **V1 — fail-closed validation.** Ollama unreachable at save time → PATCH
  returns 503 with the `OllamaError` message; the save is refused.
- **Seed — REVISED AT RECON (pending Nia confirmation, reverses the
  intake Q1-seed lock).** Seeded templates keep `model = NULL`.
  BRIEF-0008-a deliberately made `default_model` a read-time callable so
  the `WORLD_ENGINE_OLLAMA_MODEL` env override shows through and a fresh
  seed is behavior-identical (`prompt_registry.py:9-12, 20-26`);
  materializing explicit names would sever that channel and contradict a
  documented invariant. Visibility is preserved in the UI: the dropdown's
  NULL option renders as `Défaut (⟨resolved name⟩)`.
- **Structural invariant (already in force, defended not built)** —
  resolution stays in exactly ONE accessor
  (`prompt_registry.effective_model`); this ticket adds no second resolver
  and no direct `template.model` dispatch read outside it.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `PATCH /api/prompts/{prompt_id}/model` exists; accepts
      `{"model": string | null}`; rejects a non-NULL value absent from
      live tags (4xx, explicit message); NULL always accepted; bumps
      `updated_at`; 404 on unknown id  -> verify/checks/prompt_model_write.py
- [ ] `GET /api/ollama/models` returns the name list from Ollama
      `/api/tags` via `ollama_client.ping()`; Ollama down → 503 with the
      explicit error message, never an empty list
- [ ] Ollama unreachable at save time → PATCH returns 503, row unchanged
      (fail-closed, V1)
- [ ] No second resolver: all model dispatch still routes through
      `prompt_registry.effective_model`; no new direct `template.model`
      read for dispatch outside it
- [ ] `seed_pilot.py` unchanged with respect to `model` (all seeded rows
      NULL); no schema version bump anywhere

### Live  ->  human gate (Nia)
- [ ] Prompt editor dropdown lists exactly the output of `ollama list`;
      after `ollama pull` / `ollama rm`, reopening the form reflects it
      without restart
- [ ] Changing a template's model changes the model actually invoked on
      the next call (observable in Ollama logs / server console)
- [ ] A template whose stored model was removed shows the "modèle absent"
      badge; attempting to re-save that value is refused with a clear
      error
- [ ] A NULL-model template shows `Défaut (⟨nom résolu⟩)` and behaves
      byte-identically to before the change
- [ ] `WORLD_ENGINE_OLLAMA_MODEL` env override still shows through for
      NULL-model templates (0008-a channel intact)

## Scope OUT (named deferrals)

- Full template text editing (`system_prompt`, `user_template`, `notes`,
  `is_active`) — separate chantier
- Per-template inference parameters (temperature, num_ctx, repeat_penalty…)
- Model management from the cockpit — the cockpit lists, it never
  `pull`s/`rm`s
- Any `claude_api`-side reader of `model`
- Remote-Ollama configuration UI (`OLLAMA_HOST` env already covers it)
- `change_history` on prompt template edits — `prompt_template` is
  creator-CRUD state-setting territory, consistent with existing posture
