---
id: TICKET-0027
title: Code standards v1 seeding — enforcement checks and legacy remediation
type: feature
status: brief
created: 2026-07-13
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # no schema change; no migration; no destructive data op
blast_radius: large       # touches say (live play path) and _apply_mutation (canon-write path)
brief_ids: [BRIEF-0027-a, BRIEF-0027-b, BRIEF-0027-c, BRIEF-0027-d, BRIEF-0027-e, BRIEF-0027-f, BRIEF-0027-g]
schema_version_touched:   # none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

26 tickets sont complete. Je veux mon analyse de processus et de mon code
pour voir si cela vaut la peine d'avoir ma premiere version de ce document
[tooling/standards/code_standards.md]. [Follow-up:] on cap la quantite de
lignes d'une fonction, mais je pense qu'il faudrait aussi limiter le nombre
de fonctions dans un fichier (103 fonctions pour un seul fichier c'est fou).

## Clarifications resolved (intake)

The one-time SEEDING review defined in `code_standards.md` was executed
against `main` at schema v1.79 (RECON-0027). Decisions locked with Nia:

- **A2** — document scope: ratify emergent norms + corrective rules
  targeting the four observed risk zones (monolith concentration, duplicated
  LLM-output parsing, inconsistent logging, ungoverned frontend).
- **B2** — two-tier enforcement: every rule tagged `enforced` (dedicated
  fail-closed verify check) or `advisory`; advisory rules violated twice
  across distinct tickets become promotion candidates.
- **C2** — legacy violations are remediated by immediate refactoring (this
  ticket), not permanently grandfathered. Transition baselines exist only so
  checks ship before the refactor lands; they may only shrink and are
  deleted at stage g.
- **D2** — frontend covered by a light advisory section only; `page_contract`
  remains the sole frontend check.
- **E3** — module budget enforced on both dimensions in one check:
  <= 40 functions AND <= 1000 lines per `src/` module. No permanent
  exemptions; a doctrinal registry module (`writes.py`) outgrowing the cap
  is the intended tripwire forcing a package split at that moment.
- Function ceiling: 80 lines (AST span, decorators excluded).
- LLM-parse chokepoint: new module `src/world_engine/llm_parse.py`
  (`ollama_client` stays transport-only; `analyzer` is not a neutral host).
- Single ticket, staged briefs a -> g, checks-first: the R1/R5 baselines are
  born in stage a and die in stage g, making their lifecycle atomic and
  verifiable at ticket close.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `function_length.py` exists, fail-closed: any function created or
      modified beyond 80 lines fails unless present in
      `baselines/function_length.json` at a length it has not exceeded;
      baseline entries may only shrink or disappear
      -> verify/checks/function_length.py
- [ ] `module_budget.py` exists, fail-closed: any `src/` module over 40
      top-level functions/methods OR over 1000 lines fails unless baselined
      at values it has not exceeded on either dimension
      -> verify/checks/module_budget.py
- [ ] `llm_parse_chokepoint.py` exists, fail-closed: `json.loads` appears
      only in `src/world_engine/llm_parse.py` and named allow-list entries;
      an empty parsed allow-list is a failure, not a vacuous pass
      -> verify/checks/llm_parse_chokepoint.py
- [ ] `no_print_in_src.py` exists, fail-closed: zero `print(` call sites
      under `src/world_engine/` (AST call check, not grep)
      -> verify/checks/no_print_in_src.py
- [ ] After stage g: both transition baseline files are absent from
      `tooling/verify/baselines/` and all four checks pass with no
      exemptions -> verify/checks/function_length.py, module_budget.py
- [ ] `say` route handler and every function extracted from it are each
      <= 80 lines -> verify/checks/function_length.py
- [ ] `_apply_mutation` is decomposed into per-mutation-type appliers, each
      <= 80 lines, all canon writes still routed through `writes.py`
      helpers -> verify/checks/single_canon_write.py (must stay green)
- [ ] `cockpit/app.py` and `cockpit/crud.py` each <= 40 functions and
      <= 1000 lines after stage d -> verify/checks/module_budget.py
- [ ] `page_contract.py`, `single_canon_write.py`, `json_ui_boundary.py`,
      and the full existing check suite remain green after every stage
      -> tooling/verify/run.py

### Live  ->  human gate (Nia)

- [ ] After stage b and after stage d: a live `/say` round-trip in an
      existing conversation streams narration and persists the line
      identically to pre-refactor behavior
- [ ] After stage c: one AI-proposed mutation of each refactored type is
      approved in the cockpit and applies correctly (SAVEPOINT atomicity
      observed on a deliberately failing sibling)
- [ ] After stage f: `scripts/analyze_conversation.py` run shows English
      log output through the logging module, no raw prints from `src/`
- [ ] `code_standards.md` v1 is deposited in `tooling/standards/` and its
      section 4 matches what actually shipped
