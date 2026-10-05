---
id: TICKET-0103
title: Keep a usage journal of the Lore shell — proposed, refused, changed — for an offline analysis
type: feature
status: live-gate
created: 2026-10-02
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0103-lore-usage-journal.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched: v2.13
retry_count: 0
slug: lore-usage-journal
---

## Request (verbatim, as Nia stated it)

> Je veux que les données de mon utilisation de l'outil lore soit concerver.
> Ce qui m'a été proposé, ce que j'ai refusé, ce que j'ai changer. Le But est
> de lancer un analyse des données dans claude code plus tard pour faire un
> analyse de l'outil et l'améliorer.

Planning answers, in order:

> A2, B1, C1, D1, E1, F2, H1

> I1

## Clarifications resolved (intake)

- **Today only a successful commit leaves a trace** (`lore_entry`,
  `lore_entry_row`, LOT R-01): the drafts the model proposed, abandoned
  attempts, refused commits, the questions asked of the consultation panel
  and every raw model reply are lost, and the prompt version that produced a
  draft is not known (LOT R-02, R-04, R-05).
- **What she removed, changed or added is computable from two snapshots**:
  the panel never renumbers a draft's refs (LOT R-03), so the analysis pairs
  the last draft of an attempt with its committed proposal by `ref`.
- **« Changed » means corrections made in the panel before committing**
  (H1). Later edits in the fiche to rows a Lore entry created are not in this
  ticket.
- **The world cascade's check defines a world's table by its `world_id`
  column** (LOT R-10): a journal that must outlive its world carries
  `world_ref` instead (I1).

## Decisions locked (do not re-litigate without Nia)

- **A2** — journal both panels: writing (questions, draft, commit) and
  consultation (ask, resolve). Partly reverses TICKET-0085's « trace not
  persisted »: the consultation's response is now kept in the journal (never
  read back by the application). Rejected: A1, writing only (reactivates if
  the consultation journal is found unused by two analyses).
- **B1** — each model call keeps its prompt version id and number, model,
  rendered system prompt and user message, and raw reply. Rejected: B2, raw
  reply and version without the rendered input (the context served changes
  over time and cannot be rebuilt; reactivates if the journal's size becomes
  a measured problem).
- **C1** — failures are journaled (Ollama down, unparsable reply, refused
  commit), each step in its own transaction. Rejected: C2, successes only.
- **D1** — store the draft and the committed proposal as they were; the
  diff is computed by the analysis. Rejected: D2, a per-element verdict
  table written at commit (reactivates when a reader inside the application
  needs per-element verdicts).
- **E1** — one reader: `scripts/export_lore_usage.py`, JSONL, run before a
  Claude Code analysis. Rejected: E2, an analysis panel in the cockpit
  (reactivates once an analysis has shown which measures deserve a screen;
  its first UI consumer relationalizes the JSON columns).
- **F2** — the journal outlives a deleted world. Rejected: F1, the journal
  in the world cascade (test worlds are deleted, and their journal is the
  analysis material).
- **H1** — « what I changed » is the panel's corrections before commit.
  Rejected for this ticket: H2, later edits of rows born from a Lore entry
  (own ticket, see below).
- **I1** — no `world_id` column: `world_ref` + `world_name`, no FK; a global
  journal tagged by world, out of the cascade by construction, W1 unexempted.
  Rejected: I2, a `world_id` exempted by name in `world_cascade.py` W1
  (reactivates when a second table must outlive its world AND be read by the
  application itself).

## Carried forward / open

- **H2 — later edits in the fiche to rows a Lore entry created.** Not
  journaled. Deserves its own ticket if the analysis shows it matters;
  `change_history` already holds part of it for facts, relations and
  knowledge.
- **Retention.** The journal grows without bound (B1 keeps the rendered
  prompt of every call, up to 200 coded facts each). No pruning in this
  ticket; reopen when the database size is measured to matter.
- **Entries committed before this ticket** (`lore_entry` rows) are not
  exported: they have no draft to compare with.
- **The analysis itself** runs in a Claude Code session on an export, outside
  the application and outside this ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The journal: schema, migration, writer, capture, routes, panels, export -> verify/checks/lore_usage.py
- [ ] The writing path still writes canon only on commit, thin and guarded -> verify/checks/lore_write.py
- [ ] The consultation pipeline stays pure; the renderer stays Session-free -> verify/checks/lore_isolation.py
- [ ] Every world-scoped table is still cascaded; the journal is not one -> verify/checks/world_cascade.py
- [ ] The journal's JSON columns are named, justified exceptions -> verify/checks/json_ui_boundary.py
- [ ] No new `json.loads` site -> verify/checks/llm_parse_chokepoint.py
- [ ] The export script guards its environment -> verify/checks/env_guard.py
- [ ] CLAUDE.md budgets and pointers hold -> verify/checks/claude_md_contract.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_13_lore_usage.py` on prod reports `Migration v2.13 applied.`; the cockpit boots.
- [ ] Écrire: one text taken to a commit, after correcting the draft (remove a fact, change a facet, add a knower); one text abandoned after its draft; one draft asked with Ollama stopped.
- [ ] Consulter: one answered question, one ambiguous question resolved by a pick.
- [ ] `python scripts/export_lore_usage.py --out <a path outside the repo>` lists those attempts: the committed one `committed: true` with its draft and its proposal, the abandoned one `committed: false`, the Ollama-down step `unavailable`.
- [ ] A test world with journaled attempts is deleted; a new export still lists its attempts with the world's name.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
