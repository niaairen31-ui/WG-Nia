<!-- slug: prompt-management-tab -->
---
id: TICKET-0008
title: Prompt management tab — read-only, model column, prompt registry
type: feature
status: exec          # brief_ids reconciled from disk (Nia arbitrated: split a/b); ready for brief-exec
created: 2026-07-03
slug: prompt-management-tab
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]   # additive column on prompt_template
blast_radius: medium   # 22 chat/chat_stream call sites + cockpit tab + 2 verify checks
brief_ids: [BRIEF-0008-a, BRIEF-0008-b]   # split executed as proposed in RECON-0008
schema_version_touched: vX.YY   # Claude Code assigns (prompt_template.model)
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« On crée un autre onglet de mon outil créateur. Je veux : une page qui me
sert à gérer les prompts qui sont donnés aux AI locales. En lecture
seulement (en modification différée, mais ciblée). Je voudrais : le modèle
utilisé, et pouvoir faire une preview de prompt en fonction. Je veux le
faire pour les prompts utilisés dans l'onglet créateur et ceux utilisés
dans l'onglet play. Je veux pouvoir remonter à toutes les instances où est
généré avec le prompt. Il devrait seulement m'afficher un prompt à la fois,
celui que je veux (le reste n'a même pas besoin d'être généré sur l'app).
Propose-moi une architecture intéressante en considérant que dans le futur,
il y aura de plus en plus de prompts et qu'il s'en rajoutera. »

Deferred objective, stated at intake: eventually change the model per
prompt or per prompt category (e.g. all NPC, PC creation) — creator
authority, manual selection of any model available in the local Ollama.

## Clarifications resolved (intake)

- **A2-a2 — nullable authoritative `model` column.** `prompt_template.model
  TEXT NULL`. NULL = code decides (current behavior, bit-identical);
  non-NULL = creator override, consumed by an `effective_model(template,
  default)` resolver applied at every chat/chat_stream call site. The
  column has a real reader from day one (the resolver), not just display.
  A2-a3 (NOT NULL, column as sole authority) deferred and named.
- **A2-b — full creator model authority, no structural locks.** Any Ollama
  model selectable for any prompt, play or authoring. Consequence,
  explicitly accepted: the documented `region_manifest_topup` "hard
  requirement — never the game model" downgrades to a *default*. Must be
  re-recorded in ARCHITECTURE_DECISIONS.md when the write path ships.
- **A2-c — code registry for code facts.** `prompt_registry.py` declares,
  per usage: surface (play|authoring), static call sites (B1,
  `file:function`), `default_model`, `dry_run_capable`. DB owns text +
  model override; code owns wiring. Verify check: usage bijection
  registry↔seeded DB.
- **B1 — "instances" = static call sites** declared in the registry.
  Runtime invocation journal (B2) deferred and named.
- **C3 — hybrid preview.** Raw template (variables highlighted from the
  `variables` JSON) by default; assembled dry-run preview only for usages
  whose assembler already exists (`npc_dialogue` via
  `assemble_npc_context`, `player_narration` via `assemble_mj_context`).
  No model call ever. A new prompt costs one registry line, not a preview
  path.
- **D1 — lazy master list + one detail at a time.** List groups by usage,
  badges the *effective* row for the active world (world-specific >
  global, is_active); detail fetched on demand (`GET /api/prompts/{id}`).
- **E1 — standard shell.** New `CREATION_TABS` entry, `primaryAction:
  null` (read-only precedent: artefacts, queue); `page_contract.py`
  TAB_KEYS extended.
- **Scope** — `prompt_template` rows only. Python-built context blocks are
  visible *through* assembled previews, not as first-class objects
  (promotion deferred and named).

**Open at deposit (Nia's arbitration before brief authoring):**
- Brief split a/b as proposed in RECON (plumbing then reader), or single
  brief.
- `destination` column (zero code consumers, RECON F4): display as inert
  metadata or omit.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `effective_model(template, default)`: NULL model → returns default;
      non-NULL → returns override; all 22 chat/chat_stream call sites
      route through it (no direct `model=AUTHOR_MODEL` /
      `model=DEFAULT_MODEL` remaining at a templated call site)
      -> verify/checks/prompt_registry.py (new)
- [ ] Registry↔DB bijection: every seeded `usage` has a registry entry and
      vice versa; every registry entry declares surface, default_model,
      dry_run_capable, ≥1 call site  -> same check
- [ ] `prompts` key present in page_contract TAB_KEYS; entry satisfies the
      page contract with `primaryAction: null`
      -> verify/checks/page_contract.py (extended)
- [ ] `GET /api/prompts` and `GET /api/prompts/{id}` are read-only end to
      end: no `_apply_mutation`, no `change_history`, no canon write
      -> canon_write_policy baseline unchanged
- [ ] With `model` NULL everywhere (fresh seed), runtime model selection is
      bit-identical to pre-ticket behavior (authoring→AUTHOR_MODEL,
      play→DEFAULT_MODEL, `injected_context["model"]` path untouched)
      -> same check (static assertion on resolver defaults)

### Live  ->  human gate (Nia)
- [ ] Onglet Prompts : liste groupée par usage, badge « effectif » correct
      pour le monde actif, un seul détail rendu à la fois (lazy)
- [ ] Modèle effectif affiché conforme à la réalité : `llama3.1:8b` sur les
      usages authoring, modèle de jeu sur les usages play
- [ ] Preview brute d'un usage arbitraire : `{variables}` surlignées,
      system + user template lisibles
- [ ] Preview assemblée `npc_dialogue` sur un NPC réel avec interlocuteur
      choisi : le prompt rendu ne contient AUCUN secret
      (`knowledge.is_secret`, `character.secrets`, `internal_name`) —
      l'exclusion structurelle traverse la preview intacte
- [ ] Preview assemblée `player_narration` : contexte MJ rendu, mêmes
      exclusions
- [ ] Call sites (B1) affichés sur le détail, `file:fonction` exacts par
      sondage sur 2 usages

## Companion documents

- RECON-NNNN-ticket-0008-prompt-tab.md (delivered, commit anchor
  `4fad31d`, 2026-07-03)
