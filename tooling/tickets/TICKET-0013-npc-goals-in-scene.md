---
id: TICKET-0013
title: NPC goals — in-scene volition (structured goals, injection, initiative signal, goal_change)
type: feature
status: escalated
created: 2026-07-06
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0013-a, BRIEF-0013-b, BRIEF-0013-c]
schema_version_touched: v1.69
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je veux avoir des discussions qui me semblent réalistes avec les NPC, je veux
> qu'ils agissent et se comportent comme s'ils avaient un objectif et une
> volonté, pas qu'ils attendent mes ordres. […] la frustration vient surtout
> de en scène, mais j'aimerais pouvoir laisser le monde avancer après sa
> génération. […] je ne peux pas gérer les buts de chaque NPC individuellement.

Scope split (K1): this ticket covers the **in-scene** half only. The
"world advances off-screen" half (agenda tick, scoped approval batches) is
**TICKET-0014 (`world-tick`)**, to be designed after this ticket has been
observed live.

## Clarifications resolved (intake)

All decisions locked across four arbitration rounds:

| Code | Decision |
|------|----------|
| **F1** | Flat structured table `npc_goal` — no hierarchy. `horizon ∈ {short, long}`, `status ∈ {active, completed, abandoned}`. |
| **B3** | Goals reach the model through BOTH the NPC context assembler and the initiative-vote signal list. |
| **G1+G2+L1** | Goals are model-authored at three gates sharing ONE generator: region generation, existing-world backfill, single-NPC creation pre-fill. |
| **H1** | New mutation type `goal_change` proposed by `analyze_window`, applied through `_apply_mutation` under creator approval. No other emitter this ticket. |
| **M2** | Generated cardinality: exactly 1 long-term + 2 short-term goals per NPC. |
| **N1** | Goals are NPC interiority. Read ONLY by `assemble_npc_context` and the initiative vote. `assemble_mj_context` NEVER reads `npc_goal` — structural exclusion (no query), never instructional. |
| **O1** | The model may propose `completed`/`abandoned` on any goal, and CREATION of **short-term goals only**. Long-term goals are born and die under authoring/creator authority exclusively — enforced in the apply branch, not by prompt. |
| **P2** | Backfill completes missing goals PER HORIZON (an NPC with a long but no shorts receives shorts only), idempotent. |
| **Q1** | Injection shows ALL active goals: the long + the 2 most recent active shorts, one line each, horizon-tagged. No selection logic. |
| **R1** | Vote signal carries the single most recent active SHORT-term goal per candidate, as a compact fragment. Long-term goals never enter the vote. |
| **S1** | No write-side cap on active shorts. The read side is the bound: injection reads the 2 most recent active shorts; older un-closed shorts go silent. Append-only-friendly; nothing rejected, nothing deleted. |
| **T1** | One generator function + one dedicated prompt template (`pt-npc-goals`, authoring model), called by all three gates. The region MANIFEST contract is NOT touched. |
| **D1** | One behavioural directive line added to the NPC dialogue template ("you pursue your goals; you may ask, refuse, bargain, end the exchange") — via a new appended `prompt_version`, post-0012 lean style: one line, not a paragraph. |
| **E1→E2** | Creator CRUD is the baseline authority (E1); `goal_change` (H1) is the E2 evolution shipped in this same ticket because Nia cannot hand-manage per-NPC goals. |

### Deferred decisions (named, with reactivation triggers)

- **F2 — goal hierarchy (`parent_goal_id`)**: deferred until a reader exploits
  parentage (e.g. "short goal completed → model proposes the next step of the
  parent long goal"). Nia is explicitly interested; record in
  ARCHITECTURE_DECISIONS "Deferred decisions" with this trigger.
- **J2/pre-authorization — batch or auto-approval of goal proposals**: Nia
  anticipates needing pre-authorized categories "si le jeu devient gros".
  Opening this is a conscious doctrinal exception to *model proposes, code
  judges* and must be a deliberate future decision, never a drift. Record as
  deferred.
- **N3 — per-goal `is_secret` flag**: superfluous while no player-facing
  consumer reads the table; every goal is secret by construction under N1.
- **H2 — `goal_change` emitted by the off-screen tick**: belongs to
  TICKET-0014.
- **I1 (manual tick button), J1 (scoped tick)**: locked in principle, scoped
  to TICKET-0014.

## RECON findings (post-0011/0012 code, main @ 2026-07-06)

TICKET-0011 (v1.68 `prompt_version`) and TICKET-0012 (prompt lean rewrite,
`scripts/apply_ticket_0012_prompt_rewrite.py`) are both landed — anchors below
are against the restructured code.

**Schema / models** — current schema version **v1.68**
(`world-engine-schema-changelog.md:11`); this ticket is **v1.69**.
`models.py` extension-table idiom: `Knowledge` (`models.py:292`) is the shape
reference for `npc_goal` (`change_history` JSON column pattern at
`models.py:322-325`); `Character` at `models.py:110`; `ProposedMutation` at
`models.py:522`.

**NPC context assembler** — `assemble_npc_context` at
`src/world_engine/context.py:168`. Section-header constants block at
`context.py:48-56` (`H_IDENTITY` … `H_MJ_CUSTOM_SKILLS`) — new `H_GOALS`
joins it. Identity section built at `context.py:209-219`; final section
concatenation at `context.py:391-404` (identity → setting → speak →
perception → company → affiliations → pricing → boundaries). The affiliations
section (`context.py:349-360`, `read_public_memberships`) is the pattern for
an optional block. **N1 boundary**: `assemble_mj_context` at
`context.py:419` — must gain no `npc_goal` query.

**Initiative vote** — `_npc_initiative_vote` at
`src/world_engine/cockpit/app.py:1868`. `_signal_line` at
`app.py:1914-1917` builds one line per candidate
(`- {name} : relation=…, statut=…`) — R1's anchor. Two-section list
(in-group / other-group) at `app.py:1920-1934`. Template text fetched via
`current_prompt` at `app.py:1936` (0011 accessor in live use).

**Analyzer (H1 emit side)** — `_CANONICAL_TYPES` at
`src/world_engine/analyzer.py:50-59` (currently `relation_change`,
`new_knowledge`, `knowledge_change`, `status_change`, …, `resource_change`);
alias map `_TYPE_ALIASES` at `analyzer.py:80-104`; `_TARGET_TABLES` at
`analyzer.py:108+`; `_normalize_to_schema` is the per-item validation gate.

**Apply side (H1)** — `_apply_mutation` at `app.py:775`; per-type branches
begin `app.py:821`; docstring enumerates implemented types and the
"better un-applied than wrongly applied" posture for unknowns. The
`knowledge_change` branch (find row by `entity_id + subject`, monotone,
history-append) is the matching pattern `goal_change` follows — goals match by
`npc_id + normalized description` since **the model never receives structural
IDs** (standing doctrine).

**Write chokepoints** — `writes.py`: `write_knowledge` at `writes.py:282` and
`write_membership` at `writes.py:450` are the helper patterns; a new
`write_npc_goal` (insert) + status-transition helper (history-append) join
them. Both sanctioned canon paths (creator CRUD, `_apply_mutation`) must go
through these helpers; the `single_canon_write.py` AST scan allowlist
(`tooling/verify/checks/`) gains the new helper.

**Generator gates**
- *Entity author (L1)* — `generate_entity_draft` at
  `src/world_engine/entity_author.py:380`; character draft shape at
  `entity_author.py:484-500` (`public` gains a `goals` block). Template-loader
  idiom at `entity_author.py:96-131`; `AUTHOR_MODEL = "llama3.1:8b"` at
  `entity_author.py:39`; drafts are pure generate-and-return, zero canon
  writes — L1 pre-fill fits natively.
- *Region (G1)* — region draft phase: `/api/regions/generate` at
  `app.py:289`; canon commit: `commit_region` at `app.py:368`, NPC Stage 3 at
  `app.py:490-536` (`_create_entity_core` then per-NPC knowledge rows —
  `npc_goal` rows join this same transaction). The manifest
  (`region_author.py:368`, top-up `:302`) is untouched, per T1.
- *Templates* — `seed_pilot.py` upsert idiom from `~:1154` onward; S2
  discipline (seed writes v1 only on virgin heads) applies to the new
  `pt-npc-goals` head. Text edits to `pt-npc-dialogue` (D1) go through
  `writes.write_prompt_version` (`writes.py:522`) as an appended version —
  never a seed rewrite, never a raw UPDATE.
- *Creation endpoint* — `POST /api/entities` at `cockpit/crud.py:627`
  (`_create_entity_core` shared with region commit).

## Design (locked, for brief drafting)

### Table `npc_goal` (schema v1.69, F1)

`id`, `world_id` (FK world), `npc_id` (FK entity), `description` (prose,
NOT NULL), `horizon` TEXT CHECK IN ('short','long'), `status` TEXT CHECK IN
('active','completed','abandoned') DEFAULT 'active', `created_at`,
`updated_at`, `change_history` JSON DEFAULT '[]' (knowledge idiom: every
status transition appends the previous state; description is immutable after
insert — a "changed" goal is a closed goal plus a new one). Index on
`(npc_id, status)`. No `parent_goal_id` (F2 deferred). Migration script
`migrate_v1_69_npc_goal.py`, pure additive.

### Injection (Q1, S1, N1)

New `H_GOALS = "TES OBJECTIFS"` section in `assemble_npc_context`, placed
immediately after `H_IDENTITY`. Content: the active long goal (`[LONG TERME]
…`) + the 2 most recent active shorts (`[COURT TERME] …`), ordered long
first. Query bound at construction: `status='active'`, horizon filter,
`ORDER BY created_at DESC LIMIT 2` for shorts. Section omitted entirely when
the NPC has no active goals. No goal IDs in the prompt, ever.

### Vote signal (R1)

`_signal_line` gains `, objectif=« {short} »` — the single most recent active
short-term goal, truncated (~80 chars) — omitted when none. One batched query
for all candidates (same round-trip discipline as the existing relation
batch at `app.py:1898-1904`).

### Generator (T1, M2)

`generate_npc_goals(name, description, backstory, faction_goals, db) →
{"ok": bool, "long": str, "shorts": [str, str], "notes"/"error"}` in
`entity_author.py`, template `pt-npc-goals` (usage `npc_goal_generation`,
`world_id=NULL`, authoring model, `format="json"`). Exactly 1 long + 2
shorts requested and validated; short/missing output degrades gracefully
(notes, partial accept), never raises into callers. Three callers:

1. **G1** — region generate phase calls it per NPC after the NPC's entity
   draft; result attached to the draft (`public.goals`) so the creator sees
   goals in the region review UI; `commit_region` Stage 3 writes the
   `npc_goal` rows (via `write_npc_goal`) in the same transaction as the NPC.
2. **L1** — the cockpit NPC-creation "generate" flow merges goals into the
   editable pre-fill; the create POST writes them through creator CRUD.
3. **G2/P2** — `POST /api/npc-goals/backfill` (creator-direct): for every
   NPC of the active world, compute per-horizon deficit (needs 1 active long?
   needs up to 2 active shorts?), generate only the missing horizon(s),
   write via `write_npc_goal`. Idempotent by construction; re-run = no-op on
   complete NPCs. A per-NPC "Générer les buts" button on the character sheet
   reuses the same endpoint scoped to one id.

### `goal_change` (H1, O1, S1)

- **Emit**: `goal_change` added to `_CANONICAL_TYPES`, aliases
  (`goal`, `goal_update`, `objective_change`…), `_TARGET_TABLES` →
  `npc_goal`. `pt-conversation-analysis` gains the type with an
  anti-inflation rubric entry (a goal changes only on clear narrative
  evidence). Payload: `{npc_id, action: "complete"|"abandon"|"create_short",
  goal_description, new_description?}`.
- **Apply** (`_apply_mutation` branch): `complete`/`abandon` match the target
  by `npc_id` + normalized (case/whitespace) description among that NPC's
  ACTIVE goals — no match → error string → Needs attention (knowledge_change
  posture). `create_short` inserts an active short via `write_npc_goal`.
  **O1 is structural here**: any `action` attempting to create or touch a
  long-term goal's horizon is rejected in the branch — not by prompt.
  **S1**: no active-count check on insert.

### Directive (D1)

One line appended to the `pt-npc-dialogue` system prompt via
`write_prompt_version` (new version, note referencing this ticket):
« Tu poursuis tes objectifs : tu peux solliciter, refuser, marchander ou
mettre fin à l'échange si cela les sert. » Exact wording final in
BRIEF-0013-c; one sentence, 0012 lean discipline.

### Structural guard (N1)

New verify check `tooling/verify/checks/npc_goal_read.py`: static scan that
`NpcGoal` is imported/queried only in the allowlisted modules
(`context.py` [npc assembler only — scan asserts no reference inside
`assemble_mj_context`'s span], `cockpit/app.py` vote + apply, `writes.py`,
`cockpit/crud.py` goal endpoints, `entity_author.py`). Same mechanical
philosophy as `single_canon_write.py`.

## Brief plan (K1 — three testable steps)

- **BRIEF-0013-a-goal-table-and-injection** — schema v1.69 + migration +
  `write_npc_goal`/transition helper + creator CRUD (list/create/edit-status
  on the character sheet) + Q1 injection + N1 verify check. Reader ships with
  the structure. Testable: hand-create goals on one NPC, see them in the
  assembled-context preview, absent from MJ preview.
- **BRIEF-0013-b-goal-generator-three-gates** — `pt-npc-goals` seed +
  `generate_npc_goals` + G1 region wiring + L1 pre-fill + G2/P2 backfill
  endpoint + sheet button. Testable: backfill a live world, inspect goals.
- **BRIEF-0013-c-goal-behavior-loop** — R1 vote signal + H1 emit/apply +
  D1 directive version. Testable: play a scene where an NPC's short goal is
  relevant; observe initiative + a `goal_change` proposal at scene boundary.

Each brief carries its own Scope OUT (notably: no TICKET-0014 tick machinery,
no F2 hierarchy, no auto-approval, no MJ-side goal read, no manifest change).

## Acceptance criteria

### Machine-checkable → G1 deterministic gate
- [ ] `npc_goal` table exists post-migration with both CHECK constraints and `(npc_id, status)` index → schema check
- [ ] `NpcGoal` referenced only in allowlisted modules; zero references inside `assemble_mj_context` → verify/checks/npc_goal_read.py
- [ ] All `npc_goal` inserts/updates flow through `writes.py` helpers → verify/checks/single_canon_write.py (allowlist extended)
- [ ] `goal_change` apply branch rejects long-horizon creation (unit-level assertion) → verify
- [ ] Backfill run twice on the same world writes zero rows the second time → verify or scripted check

### Live → human gate (Nia)
- [ ] An NPC with an injected short-term goal visibly steers a conversation toward it
- [ ] The initiative vote picks a goal-relevant NPC in a scene where its short goal applies
- [ ] A scene boundary produces a plausible `goal_change` proposal; approving it updates the goal on the sheet
- [ ] MJ narration never leaks a goal the player hasn't discovered in fiction
