<!-- slug: law-split-by-scope -->
# BRIEF 0117-E — "The law split by where it holds -- transversal invariants in CLAUDE.md, local ones in path-scoped rules, every one with a permanent id and its check or `[no check]`"

Lot: LOT-0117-claude-md-restructure.md (authoritative on conflict)
Depends on: BRIEF-0117-D

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `ticket/0117` after BRIEF-0117-D).

- `git apply --check` of the embedded diff succeeds.
- `CLAUDE.md:383` -> `## Local model notes`; `CLAUDE.md:425` -> `### File structure`; the file is 36 693 characters.
- The Invariants section of CLAUDE.md holds 60 `- ` bullets, in the order the decision entry of this brief numbers I01 to I60 (first: `- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open`; last: ``- **The Lore usage journal (`lore_usage_event`) is written only through `lore_usage` and read only``).
- `tooling/verify/checks/claude_md_contract.py:69` -> `TOTAL_CHAR_BUDGET = 38_000`
- `tooling/verify/checks/npc_skills.py:529` -> `def check_b4() -> None:`
- `tooling/verify/checks/session_config.py:145` -> `def main() -> int:`
- `tooling/standards/FILE_MAP.md` exists and `file_map.py` passes.
- No `.claude/rules/` directory, no `tooling/verify/baselines/invariant_ids.retired`.
- Each check that an invariant below cites with `-- enforced by` exists under `tooling/verify/checks/` (R-16).

## Facts carried

### R-01 — CLAUDE.md size [M]
Opened: `CLAUDE.md` (read whole); `python -c "len(open('CLAUDE.md',encoding='utf-8').read())"`.
Finding: 37 202 characters, 572 lines. By section: Invariants 18 324
(261 lines), File structure 5 886 (80 lines), Ticket pipeline 3 071, How to
run 2 373, Local model notes 2 230, the rest 5 318.
Consequence: the budget breaks on the next ticket that adds a module or a
lesson; moving the Invariants and the tree is where the room is.

### R-02 — what the CLAUDE.md contract enforces [M]
Opened: `tooling/verify/checks/claude_md_contract.py` (implementation, 249 lines).
Finding: exact ordered H2 list (`EXPECTED_H2`, eight entries including
`Local model notes`) and H3 list under Conventions; `TOTAL_CHAR_BUDGET =
38_000` on `len(text)`; `MAX_LINE_LENGTH = 100` on every line;
`FILE_STRUCTURE_LINE_BUDGET = 80`; File structure bans `BRIEF-`, `schema v`,
`v\d+\.\d+`; Invariants bans `TICKET-\d`, `BRIEF-\d` and fails on zero `- `
bullets; every `tooling/...` token exists; every `[a-z0-9_]+\.py` token
names a file somewhere in the repo, zero tokens is a FAILURE. It reads
`CLAUDE.md` only.
Consequence: E rewrites it to cover the rule files; A to D keep its current
rules green on every intermediate CLAUDE.md.

### R-03 — two checks read CLAUDE.md's text [M]
Opened: `tooling/verify/checks/npc_skills.py:529-532`;
`tooling/verify/checks/skill_progression.py:611-622`; enumeration
`grep -ln "CLAUDE.md" tooling/verify/checks/*.py` (13 files: these two,
the contract itself, and ten that only name it in docstrings, comments or
messages).
Finding: `npc_skills.check_b4` fails unless CLAUDE.md contains
`requires_master` and `skill_access`; `skill_progression.check_b4` fails
unless it contains `skill_progress`.
Consequence: `skill_progress` stays in the root (INV-15). The skills
invariants move to `skills.md`, so E retargets `npc_skills` B4 there.

### R-15 — how Claude Code loads instructions [external, M]
Opened: https://code.claude.com/docs/en/memory (2026-10-10).
Finding: CLAUDE.md files above the working directory load at launch; a
`CLAUDE.md` in a subdirectory loads when a file there is read or edited.
`.claude/rules/*.md` files with a `paths:` front-matter list load when the
Read, Write or Edit tool (or a `cat`-style read) touches a matching file;
without `paths:` they load at launch. `@path` imports load at launch. Block
HTML comments are stripped from context. The docs recommend under 200 lines
per file. Observed in the prototype session itself: writing
`tooling/verify/checks/claude_md_contract.py` loaded
`.claude/rules/verify-checks.md`.
Consequence: G1, and the rejection of D3.

### R-16 — enforcement links, read in the checks' implementations [M]
Opened: each check's `fail(` call sites and the code around them.
Finding: carried from CLAUDE.md and confirmed: `single_canon_write.py`
(writes outside `canon_write_policy.txt`, hard deletes in its policy),
`runtime_ddl_guard.py`, `skill_progression.py`, `zone_placement.py` (15
placement outcomes, zones refused), `npc_skills.py`, `prompt_registry.py`,
`prompt_model_write.py` (PATCH outcomes), `prompt_version.py` (no
UPDATE/DELETE), `json_ui_boundary.py`, `page_contract.py`,
`creation_island.py`, `review_component.py`, `graph_primitive.py`,
`creation_tab_switch.py`, `creation_container_sizing.py`,
`effect_self_write.py`, `fact_learning.py` (`B1: Passage( constructed in
{rel}`), `lore_usage.py`. New: `knowledge_identity.py` K1 (`idx_knowledge_entity_fact`
UNIQUE on exactly `(entity_id, fact_id)`), `gathering_lifecycle.py` rules
1-6 (entry guard through `_live_gatherings`, `dissolve_emptied`,
`attach_on_arrival`, `update_entity` calling `close_open_memberships`),
`zone_map_links.py` (a/b/c: `connects_to` to a zone refused, link type
derived, no retype across the pair), `lore_write.py` C1a-C1e (rows recorded
in `lore_entry_row`, a refused write leaves no row).
Every other invariant is `[no check]`: no link was established, which is
not a claim that no check exists.
Consequence: the markers of E (39 `[no check]`, 22 linked).

### R-17 — decision entries [M]
Opened: `tooling/verify/checks/decisions_index.py` (`STRICT_HEADER`);
the registry's last 30 lines.
Finding: a new header must match `## … (BRIEF-NNNN[-x][, …], schema vX.YY |
no schema change)` with a lowercase brief letter; entries sit above the
`---` / `*Co-built with Claude, June 2026.*` footer; the index is
regenerated by `python tooling/glue/gen_decisions_index.py`.
Consequence: each brief appends one entry above the footer and regenerates.

### R-18 — the rule globs [M]
Opened: `pathlib.Path(".").glob(...)` for every planned glob.
Finding (match counts): `analyzer*.py` 2, `tick*.py` 3, `observation_*.py`
5, `day_mutations.py` 1, `cockpit/mutations.py` 1, `cockpit/routes/mutations.py`
1, `writes/knowledge.py` 1, `gathering.py` 1, `encounters.py` 1,
`passages.py` 1, `cockpit/routes/scene.py` 1, `cockpit/crud/entities.py` 1,
`context*.py` 3, `cockpit/play*.py` 5, `scene_format.py` 1, `skill*.py` 3,
`cockpit/crud/skills.py` 1, `prompt_*.py` 5, `cockpit/crud/prompts.py` 1,
`scripts/seed_pilot.py` 1, `frontend/src/**/*.svelte` 71,
`frontend/src/**/*.js` 51, `frontend/public/*.css` 2, `ollama_client.py` 1,
`scripts/talk.py` 1, `tooling/verify/checks/*.py` 146, `scripts/migrate_*.py`
70, `writes/schema.py` 1, `schema_*.py` 2, `scripts/rollback_quarantine.py`
1, `region_author.py` 1, `cockpit/routes/regions.py` 1, `lore_*.py` 13,
`scripts/export_lore_usage.py` 1. `src/world_engine/world_tick.py` matches
nothing (it is a check name) and is not used.
Consequence: every glob of C-05 matches at least one file.

## Contracts

### C-03 — `tooling/verify/checks/session_config.py`
Produced by: BRIEF-0117-B (SC1-SC5), BRIEF-0117-E (SC6)   Consumed by: the ticket's Machine section
Signature: rules SC1-SC6 as in its docstring; prose is matched with its
whitespace collapsed (`flat`).
Return shape: exit 0 with one `PASS: session_config -- …` line, else
`FAIL: SCn: …` lines and exit 1.
Error and empty cases: every file it reads missing is a FAILURE; no
`PreToolUse` Bash hook collected is a FAILURE.

### C-04 — `tooling/glue/gen_file_map.py` and `FILE_MAP.md`
Produced by: BRIEF-0117-D   Consumed by: `file_map.py` (D), CLAUDE.md (D, E), `/close-step` (D)
Signature: `SCOPES = ("src/world_engine", "scripts", "tooling/glue",
"tooling/verify")`; `collect() -> (groups, missing)`; `render(groups) -> str`;
`role(path) -> str | None`.
Return shape: `HEADER`, then per directory (sorted, repo-relative POSIX)
`## <dir>/` and one `- \`<name>\` — <first sentence>` line per module; the
first sentence is the docstring's first paragraph, whitespace collapsed,
cut after the first `.`, `!` or `?` followed by whitespace.
Error and empty cases: an empty file is skipped; a non-empty module without
a docstring is in `missing`, and the CLI exits 1 without writing.

### C-05 — the rule files and the invariant bullets
Produced by: BRIEF-0117-E   Consumed by: `claude_md_contract.py`, `/review-step`, `/close-step`
Signature: `.claude/rules/<topic>.md` opens with
```
---
paths:
  - "<glob>"
---
```
(one or more glob lines, no `{` or `[`), then an H1, optional notes, and an
optional `## Invariants`. An invariant bullet is `- **INV-NN** <law>`,
continuation lines indented two spaces, ending with `-- enforced by
\`<check>.py\`` (comma-separated for several) or `[no check]`.
`tooling/verify/baselines/invariant_ids.retired` holds comment lines and
`INV-NN|<ticket>|<reason>` lines.
Return shape: ids unique over the root and every rule file; live plus
retired = INV-01..max.
Error and empty cases: see `claude_md_contract.py` rules 6 and 7.

### C-06 — budgets
Produced by: BRIEF-0117-E   Consumed by: every later ticket
Root CLAUDE.md <= 22 000 characters (19 767 after E); each rule file <= 4 000
(largest 2 524); 100 characters per line everywhere; File structure <= 30
lines (26 after E).

## Context

D1, G1, H1, C1, F1, E1. CLAUDE.md loads whole into every session; after
this brief it holds only what must hold wherever new code lands (INV-01 to
INV-22), and ten `.claude/rules/*.md` files carry the rest, loaded when a
session touches a matching file and read in full by `/review-step` and
`/close-step`. Only rationale leaves the active text; the previous
Invariants section is archived verbatim in this brief's decision entry.
Last of five sequential briefs.

## Scope IN

1. Apply the embedded diff (`git apply`). It rewrites `CLAUDE.md` whole;
   creates the ten files of `.claude/rules/` (`authoring-lore.md`,
   `context-assembly.md`, `frontend.md`, `gatherings.md`, `local-models.md`,
   `mutation-pipeline.md`, `prompts.md`, `schema-migrations.md`,
   `skills.md`, `verify-checks.md`) and
   `tooling/verify/baselines/invariant_ids.retired`; rewrites
   `tooling/verify/checks/claude_md_contract.py` whole; retargets
   `npc_skills.py`'s B4 at `.claude/rules/skills.md`; adds SC6 to
   `session_config.py`; appends one decision entry above the footer.
2. `python tooling/glue/gen_file_map.py` (the contract's docstring changed:
   its first sentence is a map line).
3. `python tooling/glue/gen_decisions_index.py`
4. One commit: `feat(docs): the law split by where it holds -- INV ids, path-scoped rules, contract over the whole corpus (TICKET-0117, BRIEF-0117-e)`.

The texts of CLAUDE.md and of the rule files are law: copy them from the
diff, never retype or rephrase them.

### Embedded diff

Applies on `ticket/0117` after BRIEF-0117-D. Excludes the two generated
files (steps 2 and 3).

````diff
diff --git a/.claude/rules/authoring-lore.md b/.claude/rules/authoring-lore.md
new file mode 100644
index 0000000..593ba12
--- /dev/null
+++ b/.claude/rules/authoring-lore.md
@@ -0,0 +1,37 @@
+---
+paths:
+  - "src/world_engine/region_author.py"
+  - "src/world_engine/cockpit/routes/regions.py"
+  - "src/world_engine/lore_*.py"
+  - "src/world_engine/writes/lore_entries.py"
+  - "src/world_engine/writes/lore_usage.py"
+  - "src/world_engine/cockpit/routes/lore*.py"
+  - "scripts/export_lore_usage.py"
+---
+
+# Region generation and the Lore surface
+
+## Invariants
+
+- **INV-56** Region generation writes no canon; its commit is atomic; its
+  resolution is server-authoritative. `generate_region_draft` proposes
+  factions and locations only. `POST /api/regions/commit` is the single
+  write point: entities, skeleton (`parent_location_id`, faction roles via
+  `write_faction_role`) and creator-confirmed links commit in one
+  transaction, all-or-nothing, via the commit-free cores and
+  `write_relation`. No model-emitted id reaches a canon row; the
+  accept/reject cascade and link targets are re-derived server-side from raw
+  client state; rejected, uncommitted, unresolved or self-referential
+  targets write nothing. [no check]
+- **INV-57** A lore statement commits whole or not at all, through
+  `lore_write_apply.apply_proposal`. No model-emitted id reaches a canon
+  row: facts by code, entities by name, both resolved in code and confirmed
+  by the creator; every row written is recorded in `lore_entry_row`.
+  -- enforced by `lore_write.py`
+- **INV-58** The lore renderer receives rows, never a `Session`, and only
+  the `answered` verdict reaches a model — every empty verdict is rendered
+  by code, so an absence is never explained by a model. [no check]
+- **INV-59** The Lore usage journal (`lore_usage_event`) is written only
+  through `lore_usage` and read only by `scripts/export_lore_usage.py`; no
+  prompt, play or creator path reads it back, and it has no `world_id`, so
+  it outlives its world. -- enforced by `lore_usage.py`
diff --git a/.claude/rules/context-assembly.md b/.claude/rules/context-assembly.md
new file mode 100644
index 0000000..0b21465
--- /dev/null
+++ b/.claude/rules/context-assembly.md
@@ -0,0 +1,31 @@
+---
+paths:
+  - "src/world_engine/context*.py"
+  - "src/world_engine/cockpit/play*.py"
+  - "src/world_engine/scene_format.py"
+---
+
+# Context assembly and play
+
+## Invariants
+
+- **INV-35** Constraint gating is structural: gagged/restrained/blindfolded
+  effects are enforced in Python before any model call (`_stream` in
+  `app.py`). Blindfolded exclusion is a data exclusion in
+  `assemble_mj_context`, never a "don't describe" prompt. [no check]
+- **INV-36** The condition ladder is monotone for engine writes:
+  `unharmed -> bruised -> injured -> neutralized` — forward only by
+  violent-verdict code; backward only by creator CRUD. [no check]
+- **INV-37** A frozen scene yields no model calls: `scene_state.frozen =
+  True` -> `/say` short-circuits with a fixed MJ message. Only the creator
+  panel unfreezes. [no check]
+- **INV-38** A PC is excluded from NPC co-presence by construction: the
+  `H_COMPANY` query in `assemble_npc_context` carries
+  `Character.character_type != "player"`. Do not widen this filter, and do
+  not repoint it at NPC-to-NPC observation without a decision. [no check]
+- **INV-39** `_npc_dialogue_system_prompt(system_prompt, context)` in
+  `cockpit/play.py` is the single npc_dialogue system-prompt construction:
+  every live call site and the Prompts tab's preview call it — never an
+  inline concatenation. [no check]
+- **INV-40** Affinity tiers are resolved in code (`context.py`'s
+  `_affinity_tier`); prompt templates never carry the tier table. [no check]
diff --git a/.claude/rules/frontend.md b/.claude/rules/frontend.md
new file mode 100644
index 0000000..d4848e7
--- /dev/null
+++ b/.claude/rules/frontend.md
@@ -0,0 +1,42 @@
+---
+paths:
+  - "frontend/src/**/*.svelte"
+  - "frontend/src/**/*.js"
+  - "frontend/public/*.css"
+---
+
+# Frontend (Svelte shell)
+
+Any `frontend/` edit is rebuilt (`npm run build` in `frontend/`) and the
+built output under `src/world_engine/cockpit/static/` is committed with it.
+Creation's Compétences tab reads `skill_system`: a list grouped by system
+beside one fiche; `Sans système` is a rendered group, never a stored row.
+
+## Invariants
+
+- **INV-49** Every Création page is a `CREATION_TABS` registry entry rendered
+  by the generic dispatcher; no page/tab-specific branch exists outside it.
+  -- enforced by `page_contract.py`
+- **INV-50** Every Création surface mounts as a `CREATION_ISLANDS` entry
+  declaring its origin (`migration` or `new`) through `mount.js` alone;
+  `Creation.svelte` imports and renders no component. -- enforced by
+  `creation_island.py`
+- **INV-51** The review tree (`review*`,
+  `frontend/src/creation/review/registry.js`) is a generic accept/reject
+  component, never driven by consumer globals. -- enforced by
+  `review_component.py`
+- **INV-52** The graph primitive (`frontend/src/graph/Graph.svelte`) is the
+  ONE graph component; a second engine is constructible only by defeating
+  the check's fail-closed lock. -- enforced by `graph_primitive.py`
+- **INV-53** A Creation sub-tab change clears the entity sheet from the
+  single dispatcher (`showCreationSubTab`), BEFORE `activeTabKey` moves and
+  on every change, never per registry entry; `Sheet.svelte` selects its
+  render branch from `sheetType`, the same fact that feeds it, never from
+  `activeTabKey`. -- enforced by `creation_tab_switch.py`
+- **INV-54** A Création tab that owns a single container sizes it in
+  `frontend/public/creation.css` (`flex: 1; min-height: 0`), so its content
+  scrolls instead of being clipped. -- enforced by
+  `creation_container_sizing.py`
+- **INV-55** Inside a `$effect` body, a `$state` binding assigned there is
+  never read afterwards in the same body. -- enforced by
+  `effect_self_write.py`
diff --git a/.claude/rules/gatherings.md b/.claude/rules/gatherings.md
new file mode 100644
index 0000000..821cbef
--- /dev/null
+++ b/.claude/rules/gatherings.md
@@ -0,0 +1,36 @@
+---
+paths:
+  - "src/world_engine/gathering.py"
+  - "src/world_engine/encounters.py"
+  - "src/world_engine/passages.py"
+  - "src/world_engine/cockpit/routes/scene.py"
+  - "src/world_engine/cockpit/crud/entities.py"
+---
+
+# Gatherings, encounters and passages
+
+## Invariants
+
+- **INV-23** Per-NPC uniqueness: each present NPC belongs to exactly ONE open
+  gathering. Per-NPC, NOT per-location (several open gatherings in one
+  location are legal). Defended on every join/migrate path. [no check]
+- **INV-24** Dissolve-before-create lives in the caller (`enter_location`),
+  never inside `generate_gatherings`. [no check]
+- **INV-25** Creator-CRUD edits that change a character's
+  `current_location_id`, or set an entity's `status` to a non-active value,
+  close that entity's open `gathering_member` rows via
+  `close_open_memberships` (gatherings are not canon — no `_apply_mutation`,
+  no `change_history`). A location change also attaches the entity to the
+  destination's live open gathering when the open session holds one there,
+  and, after the commit, dissolves any gathering the move left with no
+  active member. Roster and co-present reads gate on `entity.status='active'
+  AND vital_status='alive'` in addition to `gathering_member.left_at IS
+  NULL`. -- enforced by `gathering_lifecycle.py`
+- **INV-26** An open gathering with no active member is a defect state:
+  dissolved the moment it is emptied, and ignored by the entry guard where
+  it survives — a location counts as entered only while one of its open
+  gatherings still holds an active member. -- enforced by
+  `gathering_lifecycle.py`
+- **INV-27** `passage` is written only by `passages.py`, whose `before_flush`
+  listener records every placement write; `rencontre.last_at` moves forward
+  only, in `encounters.py`. -- enforced by `fact_learning.py`
diff --git a/.claude/rules/local-models.md b/.claude/rules/local-models.md
new file mode 100644
index 0000000..eae3d44
--- /dev/null
+++ b/.claude/rules/local-models.md
@@ -0,0 +1,47 @@
+---
+paths:
+  - "src/world_engine/ollama_client.py"
+  - "src/world_engine/cockpit/play*.py"
+  - "src/world_engine/analyzer*.py"
+  - "scripts/talk.py"
+---
+
+# Local model notes
+
+Default game model for NPC dialogue and analysis:
+**`huihui_ai/qwen3-abliterated:8b-v2`** via Ollama; authoring model:
+`llama3.1:8b`. Per-template overrides exist (`prompt_template.model`,
+cockpit Prompts tab, live dropdown from `GET /api/ollama/models`); NULL
+resolves to the registry's `default_model` at read time, so env overrides
+show through. `prompt_registry.effective_model` is the sole resolver.
+
+- **Abliterated** = refusal mechanisms removed; maximally compliant,
+  including to a player pushing for reveals. This makes it the strictest
+  test of concealed knowledge: if secrets hold here, they hold anywhere.
+  The creator checkpoint remains the real safety net.
+- **Thinking mode:** Qwen3 emits `<think>...</think>` before answering;
+  `ollama_client.strip_think()` handles all malformed variants. Policies by
+  call site:
+  - **NPC dialogue** (`talk.py`): `/no_think` in the user message.
+  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` +
+    `_StreamThinkFilter`; thinking on, filtered before any token is
+    yielded; reply buffered, never raw to the player.
+  - **MJ narration** (`/say`, MJ phase): `chat_stream` + `/no_think` +
+    filter as backstop; narration prose only streams to the player.
+  - **MJ interpretation** (`/say`, phase 0): `chat()` + `/no_think` +
+    `format="json"`; fallback to `dialogue` on any error — a
+    misclassification must never break a turn.
+  - **MJ arbitration** (`/say`, physical turns): `chat()` +
+    `format="json"` + `/no_think`; falls back to
+    `("physical", None, None, False)` on any failure.
+  - **NPC initiative vote:** `chat()` + `format="json"` + `/no_think`;
+    failure is silent.
+  - **NPC initiative act:** `chat()` + `format="json"`, **no** `/no_think`
+    (thinking helps the two-field contract `act_text`/`move`); falls back
+    to `_NPC_INITIATIVE_ACT_FALLBACK` if the template isn't seeded; any
+    error -> silent skip.
+  - **Conversation analysis** (`analyzer.py`): thinking enabled;
+    `strip_think` before JSON parsing.
+- **French quality:** multilingual but not idiomatic-Mistral-grade;
+  acceptable for validating logic. If narrative quality disappoints, that's
+  a model-selection signal, not a code defect.
diff --git a/.claude/rules/mutation-pipeline.md b/.claude/rules/mutation-pipeline.md
new file mode 100644
index 0000000..0c32ddb
--- /dev/null
+++ b/.claude/rules/mutation-pipeline.md
@@ -0,0 +1,47 @@
+---
+paths:
+  - "src/world_engine/analyzer*.py"
+  - "src/world_engine/tick*.py"
+  - "src/world_engine/observation_*.py"
+  - "src/world_engine/day_mutations.py"
+  - "src/world_engine/cockpit/mutations.py"
+  - "src/world_engine/cockpit/routes/mutations.py"
+  - "src/world_engine/writes/knowledge.py"
+---
+
+# The mutation pipeline: proposers and appliers
+
+## Invariants
+
+- **INV-28** `relation_change` is owned by window analysis (`analyze_window`,
+  `proposed_by='local_ai_window'`): at most one `relation_change` per NPC
+  pair per window, proportionate to that window. Never deduplicated against
+  prior windows (not covered by `_mutation_match_key`). [no check]
+- **INV-29** `new_knowledge` / `status_change` are idempotent facts:
+  identity-based dedup (`entity_id` + `fact_refs.knowledge_key`; `entity_id`)
+  via `_mutation_match_key`, same conversation required. [no check]
+- **INV-30** `relation_change`'s `entity_a_id`/`entity_b_id` come from the
+  model's payload. Missing -> skip and log (`_normalize_to_schema` returns
+  `None`); never attributed via a conversation-level default. [no check]
+- **INV-31** Knowledge levels never decrease through the mutation pipeline:
+  `unaware < rumor < suspicious < partial < knows < fully_understands` is
+  monotone for every `knowledge_change` apply (`_apply_mutation`'s "level
+  already >= proposed" guard). `analyze_overhearing` also caps acquired or
+  upgraded levels at `knows` in code; `analyze_window` has no structural
+  cap. Downgrades, forgetting and `is_incorrect` correction are creator CRUD
+  only. [no check]
+- **INV-32** `new_knowledge`'s `subject_entity_id` is untrusted payload
+  input, re-validated against an active entity of the mutation's own world
+  at apply, and never part of a dedup key. [no check]
+- **INV-33** `resource_change` writes two canon tables (`ledger` + optional
+  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single sanctioned
+  exception to one-branch-one-table. Its money leg accumulates (never
+  deduped) and targets the player only; its knowledge leg is idempotent,
+  guarded at apply time. [no check]
+- **INV-34** Tick-sourced `proposed_mutation` rows have
+  `source_type='world_tick'`, `proposed_by='local_ai_tick'`, NULL
+  `pass_play_id`/`conversation_id`, and a mandatory `tick_id` (one UUID per
+  `run_world_tick`). `_find_applied_duplicate`'s tick branch
+  (`cockpit/routes/mutations.py`) is canon-existence-based, never a
+  `tick_id`-scoped history comparison, and is never extended to
+  `relation_change`. [no check]
diff --git a/.claude/rules/prompts.md b/.claude/rules/prompts.md
new file mode 100644
index 0000000..7647b2c
--- /dev/null
+++ b/.claude/rules/prompts.md
@@ -0,0 +1,18 @@
+---
+paths:
+  - "src/world_engine/prompt_*.py"
+  - "src/world_engine/writes/prompts.py"
+  - "src/world_engine/cockpit/crud/prompts.py"
+  - "src/world_engine/cockpit/routes/prompts.py"
+  - "scripts/seed_pilot.py"
+---
+
+# Prompts
+
+## Invariants
+
+- **INV-47** `prompt_template.model` is written ONLY via `PATCH
+  /api/prompts/{id}/model`, validated fail-closed against live Ollama.
+  -- enforced by `prompt_model_write.py`
+- **INV-48** Prompt text lives ONLY in the append-only `prompt_version`
+  table, never UPDATE/DELETE. -- enforced by `prompt_version.py`
diff --git a/.claude/rules/schema-migrations.md b/.claude/rules/schema-migrations.md
new file mode 100644
index 0000000..459d8f3
--- /dev/null
+++ b/.claude/rules/schema-migrations.md
@@ -0,0 +1,27 @@
+---
+paths:
+  - "scripts/migrate_*.py"
+  - "scripts/rollback_quarantine.py"
+  - "src/world_engine/schema_*.py"
+  - "src/world_engine/writes/schema.py"
+  - "src/world_engine/cockpit/app.py"
+---
+
+# Schema, migrations and the boot guard
+
+## Invariants
+
+- **INV-60** The app refuses to boot when `schema_meta.static_version` !=
+  `EXPECTED_STATIC_SCHEMA_VERSION`, OR when a physical table is neither a
+  static model table nor a registered `entity_type.physical_table`
+  (`schema_reconcile.unaccounted_tables`, in the same `cockpit/app.py`
+  startup hook; `_orphan_ext_*` quarantine tables are pattern-accounted).
+  `schema_meta` is migration-only infra, never canon, never written outside
+  a migration script. [no check]
+- **INV-61** Rollback contract: once a runtime type exists, rolling code back
+  past the constructor version requires running
+  `scripts/rollback_quarantine.py` first, after a backup. `--restore` is
+  potentially lossy, bounded to rows whose `entity` row was deleted during
+  the rollback window; every lost row is kept in `_orphan_lost_*` and
+  reported, never silently dropped. The contract is SQLite-scoped.
+  [no check]
diff --git a/.claude/rules/skills.md b/.claude/rules/skills.md
new file mode 100644
index 0000000..d8367a4
--- /dev/null
+++ b/.claude/rules/skills.md
@@ -0,0 +1,41 @@
+---
+paths:
+  - "src/world_engine/skill*.py"
+  - "src/world_engine/cockpit/crud/skills.py"
+---
+
+# Skills and skill definitions
+
+## Invariants
+
+- **INV-41** Custom skill lookups filter `skill_definition_id`, by
+  construction: a base-domain `skill` lookup includes `AND
+  skill_definition_id IS NULL`. A custom skill resolves via its
+  `skill_definition.base_domain` — never its own `domain` column — and that
+  resolved `base_domain` is what every base-domain-keyed downstream branch
+  keys off. An NPC holds only the rows it was given; Play's roll reads both
+  sides through `skill_access` (NPC: skill, else base domain, else Initié).
+  -- enforced by `npc_skills.py`
+- **INV-42** A `skill_definition` delete always succeeds (no `ON DELETE
+  RESTRICT`, no `change_history` snapshot): dependent PC `skill` rows, then
+  the definition, in one transaction. The type-"Oui" modal is the sole
+  safeguard — a named exception to "history is sacred", scoped to one row.
+  [no check]
+- **INV-43** A new open `skill_definition` backfills a default-rank `skill`
+  row onto every existing PC of its world, in the create's own transaction.
+  A `requires_master` skill is held only once taught (`POST /api/skills`),
+  and `skill_access` locks it in Play until then. Renaming touches no `skill`
+  row (FK-by-id); re-basing (`base_domain` change) updates `domain` on every
+  dependent `skill` row in the same write. [no check]
+- **INV-44** A `skill_definition.name` never equals a base-domain literal
+  (`physical`/`agility`/`perception`/`composure`, case-insensitive): both
+  write paths (creator CRUD and `_normalize_skill_catalogue`) reject or drop
+  it. [no check]
+- **INV-45** A `skill_definition` may carry a `system_id`, the body of rules
+  it belongs to; NULL = unaffiliated. `DELETE /api/skill-systems` refuses
+  while any skill is attached, unlike `DELETE /api/skill-definitions`, which
+  deletes its dependents. [no check]
+- **INV-46** `GET /api/skill-gaps` is read-only. It surfaces distinct
+  `unmatched` `skill_resolution.surface_form` rows for the active world; the
+  two arbiter-failure sentinels (`__arbiter_error__`, `__arbiter_empty__`)
+  are excluded from `gaps` and reported in `arbiter_failures`. [no check]
diff --git a/.claude/rules/verify-checks.md b/.claude/rules/verify-checks.md
new file mode 100644
index 0000000..fad78eb
--- /dev/null
+++ b/.claude/rules/verify-checks.md
@@ -0,0 +1,30 @@
+---
+paths:
+  - "tooling/verify/checks/*.py"
+---
+
+# Writing a verify check
+
+- One rule per observable, named in the module docstring (`R1`, `A2`, ...).
+  The docstring is the law the check enforces: when an invariant ends with
+  `-- enforced by <check>.py`, a reviewer reads that docstring for the full
+  rule. Its first sentence is the check's line in `FILE_MAP.md`.
+- Fail-closed: a missing file, a parse error, or a rule that collected zero
+  items is a FAILURE, never a pass. Collect every failure in a `FAILURES`
+  list through `fail()`, print each as `FAIL: ...`, exit 1; print one
+  `PASS: <name> -- ...` line and exit 0 otherwise (`file_map.py`,
+  `session_config.py`).
+- Never touch Nia's database. A DB-backed check builds a fresh temp-file
+  SQLite fixture and sets `WORLD_ENGINE_DATABASE_URL` before any
+  `world_engine` import (`fact_spine.py`), and builds its rows through the
+  real sanctioned writers.
+- Never a second copy of a parser or renderer: import it
+  (`pipeline_state.py` imports `run.py` and `escalation.py`; `file_map.py`
+  imports `gen_file_map.py`).
+- Every rule is proven by a named mutation in the brief's Done means: a
+  one-line change that turns that rule red, then reverted.
+- `corpus_gate.py` runs every check here as a subprocess with a 15-second
+  timeout; an import error, a crash or a timeout is a failure.
+- A check is retired by deleting it and recording `<file>|<ticket>` in
+  `tooling/verify/baselines/checks.retired` in the same commit; older
+  tickets keep their arrows to it.
diff --git a/CLAUDE.md b/CLAUDE.md
index 839a0da..804db36 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -6,21 +6,21 @@ A locally-hosted AI-powered tabletop RPG world engine (Verkhaal is the pilot
 world). A creator cockpit (world-building + play surface) drives local models
 through structured prompts; every AI-proposed change to world canon passes a
 creator checkpoint before it is applied. This file is the standing contract
-for Claude Code sessions: conventions, invariants, and how to run things.
-History and rationale live in `tooling/standards/ARCHITECTURE_DECISIONS.md`
-and `world-engine-schema-changelog.md` — never here.
+for Claude Code sessions: conventions, the invariants that hold everywhere,
+and how to run things. Invariants that hold for one part of the code live in
+`.claude/rules/` (see Path-scoped rules). History and rationale live in
+`tooling/standards/ARCHITECTURE_DECISIONS.md` and
+`world-engine-schema-changelog.md` — never here.
 
 ## Stack
 
 - Python, FastAPI, SQLModel, SQLite (Supabase/PostgreSQL migration path
   preserved via the env-var DB URL).
-- Frontend: a built Svelte shell (`frontend/`) serves the cockpit at `/`. Creation, Observation,
-  Journée and Lore are shell-native Svelte components, mounted directly by `App.svelte`; Play
-  alone stays legacy (`/legacy`, one governed iframe, `cockpit/legacy.html`), sealed rather than
-  migrated by TICKET-0061, until its own ticket (TICKET-0069). No new dependency without a
-  decision.
-  Creation's Compétences tab reads `skill_system`: a list grouped by system beside one fiche;
-  `Sans système` is a rendered group, never a stored row (TICKET-0084).
+- Frontend: a built Svelte shell (`frontend/`) serves the cockpit at `/`.
+  Creation, Observation, Journée and Lore are shell-native Svelte
+  components, mounted directly by `App.svelte`; Play alone stays legacy
+  (`/legacy`, one governed iframe, `cockpit/legacy.html`) until its own
+  ticket. No new dependency without a decision.
 - Local models via Ollama; Claude API reserved for heavy lore-coherence work.
 - Runtime: Windows / PowerShell — `.venv\Scripts\Activate.ps1`,
   `$env:PYTHONPATH = "src"`.
@@ -50,12 +50,12 @@ and `world-engine-schema-changelog.md` — never here.
 - **Language convention:** design conversation happens in French; all code,
   schema, comments, commit messages, and documentation are in English.
 - **Step closure:** every closed step updates the schema changelog (if
-  schema-touching) and keeps `tooling/standards/ARCHITECTURE_DECISIONS.md`
-  and this file consistent with the code. Use the `/close-step` command.
-  This file is contract-checked: `tooling/verify/checks/claude_md_contract.py`
-  enforces its section whitelist, a 38 000-character file budget, a
-  100-character per-line ceiling, and archaeology bans in File structure
-  and Invariants.
+  schema-touching) and keeps `tooling/standards/ARCHITECTURE_DECISIONS.md`,
+  this file and `.claude/rules/` consistent with the code. Use `/close-step`.
+  This file and every rule file are contract-checked by
+  `tooling/verify/checks/claude_md_contract.py`: section whitelist,
+  character budgets, 100-character lines, archaeology bans, invariant ids
+  and markers, and every rule's `paths:` still matching a file.
 
 ## Ticket pipeline (governance)
 
@@ -94,10 +94,10 @@ and `world-engine-schema-changelog.md` — never here.
   An amendment is never named `TICKET-*`, which `pipeline_state.py` globs.
 - **Where things live:** `tooling/tickets`, `tooling/lots`, `tooling/briefs`;
   `tooling/recon` (archived RECONs of earlier tickets, none written now);
-  `tooling/glue` (`gen_decisions_index.py`, `escalation.py`);
-  `tooling/verify` (`run.py`, `checks/`, `baselines/`, `results/`);
-  `tooling/standards` (`ARCHITECTURE_DECISIONS.md`, generated
-  `DECISIONS_INDEX.md`, `code_standards.md`).
+  `tooling/glue` (`gen_decisions_index.py`, `gen_file_map.py`,
+  `escalation.py`); `tooling/verify` (`run.py`, `checks/`, `baselines/`,
+  `results/`); `tooling/standards` (`ARCHITECTURE_DECISIONS.md`, generated
+  `DECISIONS_INDEX.md` and `FILE_MAP.md`, `code_standards.md`).
 - This section governs the ticket pipeline itself (process, gating,
   escalation). It does not replace or relax any invariant below — those
   still apply to every change regardless of how it was ticketed.
@@ -114,386 +114,160 @@ and `world-engine-schema-changelog.md` — never here.
   the header form
   `## TITLE (BRIEF-NNNN[-x][, ...], schema vX.YY | no schema change)` —
   enforced by `tooling/verify/checks/decisions_index.py` against baseline.
-- `tooling/standards/DECISIONS_INDEX.md` is generated; never edit by hand.
-  Generated files are never hand-resolved in a merge conflict: regenerate
-  (`python tooling/glue/gen_decisions_index.py`) and stage the result. A
-  conflict outside a branch's diagnosed set is an escalation, not an improvisation.
+- `tooling/standards/DECISIONS_INDEX.md` and `FILE_MAP.md` are generated;
+  never edit them by hand. A generated file is never hand-resolved in a
+  merge conflict: regenerate it (`gen_decisions_index.py`,
+  `gen_file_map.py`) and stage the result. A conflict outside a branch's
+  diagnosed set is an escalation, not an improvisation.
 
 ## Invariants (verified at every review)
 
-Law only. Rationale, chantier history, and deferred alternatives live in
-`tooling/standards/ARCHITECTURE_DECISIONS.md`.
+Law only; rationale lives in `tooling/standards/ARCHITECTURE_DECISIONS.md`.
+Each invariant has a permanent id `INV-NN`, never reused; a retired id is
+listed in `tooling/verify/baselines/invariant_ids.retired`. Each ends with
+`-- enforced by <check>.py`, whose docstring holds the full law, or with
+`[no check]`: no enforcing check has been established for it yet.
 
-- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
-  gathering. Per-NPC, NOT per-location (multiple open gatherings in one
-  location are legal). Defended on every join/migrate path.
-- **Dissolve-before-create lives in the caller** (`enter_location`), never
-  inside `generate_gatherings`.
-- **`relation_change` is owned by window analysis** (`analyze_window`,
-  `proposed_by='local_ai_window'`): at most one `relation_change` per NPC
-  pair per window, proportionate to that window. Never deduplicated against
-  prior windows (not covered by `_mutation_match_key`).
-- **`new_knowledge` / `status_change` are idempotent facts:** identity-based
-  dedup (`entity_id` + `fact_refs.knowledge_key`; `entity_id`) via
-  `_mutation_match_key`, same conversation required.
-- **A `knowledge` row is identified by its fact:** `(entity_id, fact_id)` is unique. A model
-  names a fact only by a code from a `fact_refs.code_facts` list; code resolves it.
-- **Secrets are structurally excluded** from every assembled context — never
-  "guarded by instruction". The creator's note on an entity (a `histoire`
-  fact whose entity holds an `unaware` `is_secret` row on it) is excluded from
-  `facet_reads` by query construction; only the Lore dossier opts in, plus the
-  `creator` regime of `name_index` for name resolution (Lore question, names
-  panel, writing panel, condition interpreter).
-  Token posing never indexes a creator-only or unscoped appellation.
-  What an NPC knows-but-conceals lives in `knowledge` rows with
-  `is_secret = TRUE`,
-  excluded by query construction at every assembler AND every propagation
-  path (`analyze_overhearing` never sources a proposal from an `is_secret`
-  row).
-- **`relation_change`'s `entity_a_id`/`entity_b_id` come from the model's
-  payload.** Missing -> skip and log (`_normalize_to_schema` returns
-  `None`); never attributed via a conversation-level default. Per-item
-  roster resolution is a named deferral.
-- Two canon-write paths for rows: `_apply_mutation`, creator CRUD. A third covers canon STRUCTURE
-  -- closed by `single_canon_write.py` + `runtime_ddl_guard.py`.
-- **History is sacred on BOTH write paths:** any edit to `relation` or `knowledge` appends the
-  previous state to `change_history`; states are preserved, never silently overwritten.
-  `entity_type_history` extends this to the schema grain: append-only by construction, no
-  `change_history` column — the rows ARE the history.
-- **Commit before touching any canon-writing path** (`_apply_mutation`, the creator CRUD, the
-  analyzers, and everything they call) — hard. Recommended: also commit before touching the `/say`
-  flow or the interpretation phase (playability-critical). On SQLite, DDL participates in the
-  surrounding transaction — a structural guarantee of the shared engine (`db.py`), never a per-
-  site precaution.
-- **The MJ context assembler is scoped to the player's perception
-  boundary:** only what the player may perceive or already knows. Never
+- **INV-01** Secrets are structurally excluded from every assembled context,
+  by query construction, never by instruction. What an NPC knows but conceals
+  is a `knowledge` row with `is_secret = TRUE`, excluded at every assembler
+  AND every propagation path (`analyze_overhearing` never sources a proposal
+  from one). The creator's note on an entity (a `histoire` fact whose entity
+  holds an `unaware` `is_secret` row on it) is excluded from `facet_reads`;
+  only the Lore dossier opts in, plus the `creator` regime of `name_index`
+  (Lore question, names panel, writing panel, condition interpreter). Token
+  posing never indexes a creator-only or unscoped appellation. [no check]
+- **INV-02** The MJ context assembler is scoped to the player's perception
+  boundary: only what the player may perceive or already knows. Never
   NPC-private knowledge, secrets, internal names, non-public entities, or
-  invisible relations. Enforced by query construction, never by instruction.
-- **Knowledge levels never decrease through the mutation pipeline:**
-  `unaware < rumor < suspicious < partial < knows < fully_understands` is
-  monotone for every `knowledge_change` apply (`_apply_mutation`'s
-  "level already >= proposed" guard). `analyze_overhearing` additionally
-  caps acquired/upgraded levels at `knows` in code; `analyze_window` has no
-  structural cap (named deferral). Downgrades, forgetting, and
-  `is_incorrect` correction are creator CRUD only.
-- **A `fact_participant` row is the aboutness claim for every `knowledge`
-  row on that fact.** `role` is descriptive only, never a filter or a
-  discriminator; `(fact_id, entity_id)` is unique, so every writer reads
-  before it writes.
-- **`new_knowledge`'s `subject_entity_id` is untrusted payload input,**
-  re-validated against an active entity of the mutation's own world at
-  apply, and it is never part of a dedup key.
-- **`scene_state` is a third, explicitly ephemeral write path.**
+  invisible relations. [no check]
+- **INV-03** Membership reaches a model prompt only via
+  `read_public_memberships`; `is_secret` rows never enter any prompt,
+  including the holder's own, with no override parameter. The true `role`
+  behind a `cover_role` never enters a prompt: the accessor resolves
+  `cover_role ?? role`. Espionage rides on `goals` prose, never a confessable
+  affiliation label. Declared faction roles live in `faction_role`
+  (relational, never JSON). [no check]
+- **INV-04** `npc_price` rows are seller configuration, injected ONLY into
+  that seller's own dialogue context — never into `assemble_mj_context` or
+  any other entity's context. A quoted price writes no canon; money moves via
+  `resource_change` through the checkpoint. [no check]
+- **INV-05** `discoverable_detail` is read by no assembler or prompt-building
+  path. `hidden` content reaches a model ONLY via the post-selection
+  `{detail_content}` injection in `_stream()` on a partial/success perception
+  search (`domain="perception"`, `opposed_npc_id=None`); `ambient` content
+  only via the pure predicate `active_signposts` (`scene_format.py`), passed
+  into the MJ establishment call. A hidden `coutume` fact is a TRAP: never
+  add `"hidden"` to `FACETS["coutume"].aspects`; every play reader filters
+  `notorious_at_location` at query construction. [no check]
+- **INV-06** `connects_to` and `borde` are location map topology, never a
+  social signal; their `intensity` means nothing. Every gameplay reader of
+  `relation` keyed on a character/player id is blind to them; the sole
+  gameplay reader is `_location_neighbours`. A new world-wide relation scan
+  MUST exclude both (`MAP_TOPOLOGY_TYPES`). [no check]
+- **INV-07** PC knowledge is written `is_secret=False`; `_normalize_knowledge`
+  is NPC-only and forces `is_secret=True` — never reuse it for a PC.
+  `_normalize_player_knowledge` emits no `is_secret` key; `False` is applied
+  at write time by the accept route (`create_player_character` via
+  `writes.write_knowledge`), never by the generator. [no check]
+- **INV-08** Two canon-write paths for rows: `_apply_mutation` and creator
+  CRUD. A third covers canon STRUCTURE. -- enforced by
+  `single_canon_write.py`, `runtime_ddl_guard.py`
+- **INV-09** `scene_state` is a third, explicitly ephemeral write path:
   `_write_scene_state` archives the previous snapshot to `history[]` before
   every write; cleared to `{}` on conversation close; never canon — durable
-  consequences require a `proposed_mutation`.
-- **`proposed_by='engine'` deterministic proposals**
+  consequences require a `proposed_mutation`. [no check]
+- **INV-10** History is sacred on BOTH write paths: any edit to `relation` or
+  `knowledge` appends the previous state to `change_history`.
+  `entity_type_history` is append-only by construction, with no
+  `change_history` column — the rows ARE the history. [no check]
+- **INV-11** Commit before touching any canon-writing path (`_apply_mutation`,
+  the creator CRUD, the analyzers, and everything they call) — hard.
+  Recommended before the `/say` flow or the interpretation phase. On SQLite,
+  DDL participates in the surrounding transaction — a guarantee of the shared
+  engine (`db.py`), never a per-site precaution. [no check]
+- **INV-12** Hard deletes are a closed, named list; a new hard-delete path is
+  named there, never added silently. -- enforced by `single_canon_write.py`
+- **INV-13** The `ledger` is append-only: INSERT-only on both canon-write
+  paths, corrections are new compensating lines, and no UPDATE/DELETE
+  endpoint or code path touches a `ledger` row. [no check]
+- **INV-14** `proposed_by='engine'` deterministic proposals
   (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
-  review queue as AI proposals — never auto-applied.
-- **`skill_progress` is the one live auto-applied mutation:** a roll's point
-  (`proposed_by='engine_roll'`) applied through `_apply_mutation` at proposal time;
-  `write_skill_progress` moves the rank -- enforced by `skill_progression.py`.
-- **Constraint gating is structural, not instructional:** gagged/restrained/
-  blindfolded effects are enforced in Python before any model call
-  (`_stream` in `app.py`). Blindfolded exclusion is a data exclusion in
-  `assemble_mj_context`, never a "don't describe" prompt.
-- **Condition ladder is monotone for engine writes:** `unharmed -> bruised -> injured ->
-  neutralized` — forward only by violent-verdict code; backward only by creator CRUD.
-- **Frozen scene yields no model calls:** `scene_state.frozen = True` -> `/say` short-circuits
-  with a fixed MJ message. Only the creator panel unfreezes.
-- **`discoverable_detail` is structurally excluded from every assembler,
-  with one consciously narrowed exception:** no assembler or prompt-building
-  path reads the table. `hidden` content reaches a model ONLY via the
-  post-selection `{detail_content}` injection in `_stream()` on a
-  partial/success perception search (`domain="perception"`,
-  `opposed_npc_id=None`). `ambient` content is read only via the pure code
-  predicate `active_signposts` (scene_format.py), passed directly into the MJ
-  establishment call. A hidden `coutume` fact (no `location` default) is a
-  TRAP — never add `"hidden"` to `FACETS["coutume"].aspects`, and every play
-  reader filters `notorious_at_location` at query construction; discoverable
-  content lives ONLY in `discoverable_detail`.
-- **`connects_to` and `borde` are location map topology, never a social
-  signal.** Their `intensity=50` is meaningless. Every gameplay reader of
-  `relation` keyed on a character/player id is structurally blind to them;
-  the sole intentional gameplay reader is `_location_neighbours`. Any new
-  world-wide relation scan MUST exclude both (`MAP_TOPOLOGY_TYPES`).
-- **A location with an active child is a zone, derived, never stored
-  (`zone_rules.py`).** Only `connects_to` is traversable and it never
-  touches a zone; a link touching a zone is `borde`. A geographic link's
-  type is derived from its endpoints (`link_locations`), never chosen. No
-  being, item or discoverable detail is placed in a zone
-  (`require_visitable`, at every placement write) -- `zone_placement.py`.
-- **The `ledger` is append-only.** INSERT-only on both canon-write paths;
-  corrections are new compensating lines. No UPDATE/DELETE endpoint or code
-  path may touch a `ledger` row.
-- **`resource_change` writes two canon tables** (`ledger` + optional
-  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single
-  sanctioned exception to one-branch-one-table. Money leg accumulates
-  (never deduped) and targets the player only, until tracked NPC purses
-  exist; knowledge leg is idempotent, guarded at apply time.
-- **Tick-sourced `proposed_mutation` rows have `source_type='world_tick'`,
-  `proposed_by='local_ai_tick'`, NULL `pass_play_id`/`conversation_id`, and
-  a mandatory `tick_id`** (one UUID per `run_world_tick` invocation).
-  `_find_applied_duplicate`'s tick branch (`cockpit/routes/mutations.py`) is
-  canon-existence-based, never a `tick_id`-scoped history comparison, and
-  must never be extended to `relation_change` (accumulating deltas, never
-  guarded).
-- **`npc_price` rows are seller configuration,** injected ONLY into that
-  seller's own dialogue context — never into `assemble_mj_context` or any
-  other entity's context. A quoted price writes no canon; money moves via
-  `resource_change` through the checkpoint. Catalogue prices are firm and
-  universal; only uncatalogued quotes are relation-modulated.
-- **Membership reaches a model prompt only via `read_public_memberships`;**
-  `is_secret` rows never enter any prompt, including the holder's own —
-  structural filter, no override parameter. The true `role` behind a
-  `cover_role` never enters any prompt: the accessor resolves
-  `cover_role ?? role`. Espionage rides on `goals` prose, never a
-  confessable affiliation label. Declared faction roles live in
-  `faction_role` (relational, never JSON; case-uniqueness is the index's job).
-- **Creator-direct create helpers never commit in their core; the commit
-  boundary belongs to the caller.** `create_entity`, `create_knowledge`,
+  review queue as AI proposals — never auto-applied. [no check]
+- **INV-15** `skill_progress` is the one live auto-applied mutation: a roll's
+  point (`proposed_by='engine_roll'`) applied through `_apply_mutation` at
+  proposal time; `write_skill_progress` moves the rank. -- enforced by
+  `skill_progression.py`
+- **INV-16** A `knowledge` row is identified by its fact: `(entity_id,
+  fact_id)` is unique. -- enforced by `knowledge_identity.py`
+- **INV-17** A `fact_participant` row is the aboutness claim for every
+  `knowledge` row on that fact. `role` is descriptive only, never a filter or
+  a discriminator; `(fact_id, entity_id)` is unique, so every writer reads
+  before it writes. [no check]
+- **INV-18** Creator-direct create helpers never commit in their core; the
+  commit boundary belongs to the caller. `create_entity`, `create_knowledge`,
   `open_entity_membership` each split into a commit-free core plus a thin
-  route wrapper owning the single commit — a structural seam, not a
-  `commit:` flag.
-- **Region generation writes no canon; commit is atomic; resolution is
-  server-authoritative.** `generate_region_draft` proposes factions and
-  locations only — characters retired to the group agent (A1).
-  `POST /api/regions/commit` is the single write point: entities, skeleton
-  (`parent_location_id`, faction role vocabulary via `write_faction_role`)
-  and creator-confirmed links commit in one transaction, all-or-nothing,
-  via the commit-free cores and `write_relation`. No model-emitted id ever
-  reaches a canon row; the accept/reject cascade and link targets are
-  re-derived server-side from raw client state; rejected/uncommitted/
-  unresolved/self-referential targets write nothing.
-- **A lore statement commits whole or not at all, through `lore_write_apply.apply_proposal`.**
-  No model-emitted id reaches a canon row: facts by code, entities by name, both resolved in code
-  and confirmed by the creator; every row written is recorded in `lore_entry_row`.
-- **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is
-  NPC-only and forces `is_secret=True` — never reuse it for a PC.**
-  `_normalize_player_knowledge` emits no `is_secret` key; `False` is
-  applied at write time by the accept route (`create_player_character` via
-  `writes.write_knowledge`), never by the generator.
-- **A PC is excluded from NPC co-presence by construction:** the
-  `H_COMPANY` query in `assemble_npc_context` carries
-  `Character.character_type != "player"`. Do not widen this filter, and do
-  not repoint it at a future NPC-to-NPC observation feature without a
-  deliberate decision.
-- **Creator-CRUD edits that change a character's `current_location_id`, or
-  set an entity's `status` to a non-active value, MUST close that entity's
-  open `gathering_member` rows via `close_open_memberships`** (gatherings
-  are not canon — no `_apply_mutation`, no `change_history`). A location
-  change also attaches the entity to the destination's live open gathering
-  when the open session already holds one there, and, after the commit,
-  dissolves any gathering the move left with no active member. Roster and
-  co-present reads gate on `entity.status='active' AND
-  vital_status='alive'` in addition to `gathering_member.left_at IS NULL`.
-- **An open gathering with no active member is a defect state, not a legal
-  one:** dissolved the moment it is emptied, and ignored by the entry
-  guard where it survives anyway — a location counts as already entered
-  only while one of its open gatherings still holds an active member.
-- Hard deletes are a closed, named list -- enforced by `single_canon_write.py`; any new hard-
-  delete path must be named there, never added silently.
-- **Custom skill lookups filter `skill_definition_id`, by construction:** a
-  base-domain `skill` lookup MUST include `AND skill_definition_id IS NULL`.
-  A custom skill resolves via its `skill_definition.base_domain` — never
-  its own `domain` column — and that resolved `base_domain` is what every
-  base-domain-keyed downstream branch keys off. An NPC holds only the rows it
-  was given; Play's roll reads both sides through `skill_access` (NPC: skill,
-  else base domain, else Initié) -- enforced by `npc_skills.py`.
-- **A `skill_definition` delete always succeeds** (no `ON DELETE RESTRICT`,
-  no `change_history` snapshot): dependent PC `skill` rows then the
-  definition, one transaction. The type-"Oui" modal is the sole safeguard —
-  a named exception to "History is sacred", scoped to one row.
-- **A new open `skill_definition` backfills a default-rank `skill` row onto every
-  existing PC of its world, in the create's own transaction** — the
-  catalogue<->PC alignment of open skills is never partial. A `requires_master`
-  skill is held only once taught (`POST /api/skills`), and `skill_access` locks
-  it in Play until then. Renaming touches no `skill`
-  row (FK-by-id); re-basing (`base_domain` change) updates `domain` on
-  every dependent `skill` row in the same write.
-- **A `skill_definition.name` can never equal a base-domain literal**
-  (`physical`/`agility`/`perception`/`composure`, case-insensitive) — both
-  write paths (creator CRUD and `_normalize_skill_catalogue`) reject/drop
-  it.
-- **A `skill_definition` may carry a `system_id`** (schema v2.01), the body
-  of rules it belongs to; NULL = unaffiliated. `DELETE
-  /api/skill-systems` refuses while any skill is still attached, unlike
-  `DELETE /api/skill-definitions`, which deletes its dependents.
-- **`GET /api/skill-gaps` is read-only** — it performs no write of any
-  kind. It surfaces distinct `unmatched` `skill_resolution.surface_form`
-  rows for the active world; the two arbiter-failure sentinels
-  (`__arbiter_error__`, `__arbiter_empty__`) are excluded from its `gaps`
-  list by design and reported separately in `arbiter_failures`.
-- **All templated model calls resolve through
-  `prompt_registry.effective_model`** — the single model resolver. New
-  prompt usages must add a `PROMPT_REGISTRY` entry
-  (`tooling/verify/checks/prompt_registry.py` enforces).
-- `prompt_template.model` is written ONLY via `PATCH /api/prompts/{id}/model`, validated fail-
-  closed against live Ollama -- enforced by `prompt_model_write.py`.
-- **`_npc_dialogue_system_prompt(system_prompt, context)` in `cockpit/play.py`
-  is the single npc_dialogue system-prompt construction:** every live call
-  site and the Prompts tab's assembled preview call it — never a duplicated
-  inline concatenation.
-- Prompt text lives ONLY in the append-only `prompt_version` table, never
-  UPDATE/DELETE -- enforced by `prompt_version.py`.
-- Affinity tiers are resolved in code (`context.py::_affinity_tier`);
-  prompt templates never carry the tier table.
-- **UI-visible data never lives in JSON** — relational only; enforced
-  fail-closed by `json_ui_boundary` (exceptions justified in that file).
-- **The app refuses to boot when `schema_meta.static_version` !=
-  `EXPECTED_STATIC_SCHEMA_VERSION`, OR when a physical table is neither a static model table nor
-  a registered `entity_type.physical_table`** (fail-closed on both; the second check is
-  `schema_reconcile.unaccounted_tables`, extending the same `cockpit/app.py` startup hook —
-  `_orphan_ext_*` quarantine tables are pattern-accounted, never flagged); `schema_meta` is
-  migration-only infra, never canon, never writable outside a migration script.
-- **Rollback contract (B1):** "Once a runtime type exists, rolling code back past the
-  constructor version requires running `scripts/rollback_quarantine.py` first (after a backup).
-  Roll-forward restoration (`--restore`) is potentially lossy, bounded to rows whose `entity`
-  row was deleted during the rollback window; every lost row is preserved in `_orphan_lost_*`
-  and reported — never silently dropped. This contract is SQLite-scoped (the rebuild-without-FK
-  recipe is SQLite-specific), matching the engine's current single-backend reality." Full
-  rationale: `ARCHITECTURE_DECISIONS.md`, "ENTITY-TYPE CONSTRUCTOR — rollback quarantine (B1)".
-- Every Création page is a `CREATION_TABS` registry entry rendered by the generic dispatcher; no
-  page/tab-specific branch exists outside it — enforced by `page_contract.py`.
-- Every Création surface mounts as a `CREATION_ISLANDS` entry declaring its origin (`migration` or
-  `new`) through `mount.js` alone; `Creation.svelte` imports and renders no component — enforced by
-  `creation_island.py`.
-- The review tree (`review*`, `frontend/src/creation/review/registry.js`) is a generic
-  accept/reject component, never driven by consumer globals — enforced by `review_component.py`.
-- The graph primitive (`frontend/src/graph/Graph.svelte`) is the ONE graph component; a second
-  engine is constructible only by defeating `graph_primitive.py`'s fail-closed lock.
-- A Creation sub-tab change clears the entity sheet from the single dispatcher
-  (`showCreationSubTab`), BEFORE `activeTabKey` moves and on every change, never per
-  registry entry; and `Sheet.svelte` selects its render branch from `sheetType`, the same
-  fact that feeds it, never from `activeTabKey` -- enforced by `creation_tab_switch.py`.
-- A Création tab that owns a single container sizes it in `frontend/public/creation.css`
-  (`flex: 1; min-height: 0`), so its content scrolls instead of being clipped -- enforced by
-  `creation_container_sizing.py`.
-- Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the
-  same body — enforced by `effect_self_write.py`.
-- `passage` is written only by `passages.py`, whose `before_flush` listener records every
-  placement write; `rencontre.last_at` moves forward only, in `encounters.py` -- enforced by
-  `fact_learning.py`.
-- **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches
-  a model — every empty verdict is rendered by code, so an absence is never explained by a model.
-- **The Lore usage journal (`lore_usage_event`) is written only through `lore_usage` and read only
-  by `scripts/export_lore_usage.py`;** no prompt, play or creator path reads it back, and it has no
-  `world_id`, so it outlives its world -- enforced by `lore_usage.py`.
+  route wrapper owning the single commit — never a `commit:` flag. [no check]
+- **INV-19** All templated model calls resolve through
+  `prompt_registry.effective_model`, the single model resolver; a new prompt
+  usage adds a `PROMPT_REGISTRY` entry. -- enforced by `prompt_registry.py`
+- **INV-20** UI-visible data never lives in JSON — relational only
+  (exceptions justified in the check). -- enforced by `json_ui_boundary.py`
+- **INV-21** A location with an active child is a zone, derived, never stored
+  (`zone_rules.py`). Only `connects_to` is traversable and it never touches a
+  zone; a link touching a zone is `borde`. A geographic link's type is
+  derived from its endpoints (`link_locations`), never chosen. No being,
+  item or discoverable detail is placed in a zone (`require_visitable`, at
+  every placement write). -- enforced by `zone_placement.py`,
+  `zone_map_links.py`
+- **INV-22** A model names a fact only by a code from a
+  `fact_refs.code_facts` list; code resolves it. [no check]
 
-## Local model notes
+## Path-scoped rules
 
-Default game model for NPC dialogue and analysis:
-**`huihui_ai/qwen3-abliterated:8b-v2`** via Ollama; authoring model:
-`llama3.1:8b`. Per-template overrides exist (`prompt_template.model`,
-cockpit Prompts tab, live dropdown from `GET /api/ollama/models`); NULL
-resolves to the registry's `default_model` at read time, so env overrides
-show through. `prompt_registry.effective_model` is the sole resolver.
+Invariants and notes that hold for one part of the code live in
+`.claude/rules/<topic>.md`. Claude Code loads a rule file when a session
+reads or edits a file matching its `paths:`; `/review-step` and
+`/close-step` read every one on every commit. An invariant that must hold
+wherever new code lands stays in this file. Invariant ids run on across all
+of them.
 
-- **Abliterated** = refusal mechanisms removed; maximally compliant,
-  including to a player pushing for reveals. This makes it the strictest
-  test of concealed knowledge: if secrets hold here, they hold anywhere.
-  The creator checkpoint remains the real safety net.
-- **Thinking mode:** Qwen3 emits `<think>...</think>` before answering;
-  `ollama_client.strip_think()` handles all malformed variants. Policies by
-  call site:
-  - **NPC dialogue** (`talk.py`): `/no_think` in the user message.
-  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` +
-    `_StreamThinkFilter`; thinking on, filtered before any token is
-    yielded; reply buffered, never raw to the player.
-  - **MJ narration** (`/say`, MJ phase): `chat_stream` + `/no_think` +
-    filter as backstop; narration prose only streams to the player.
-  - **MJ interpretation** (`/say`, phase 0): `chat()` + `/no_think` +
-    `format="json"`; fallback to `dialogue` on any error — a
-    misclassification must never break a turn.
-  - **MJ arbitration** (`/say`, physical turns): `chat()` +
-    `format="json"` + `/no_think`; falls back to
-    `("physical", None, None, False)` on any failure.
-  - **NPC initiative vote:** `chat()` + `format="json"` + `/no_think`;
-    failure is silent.
-  - **NPC initiative act:** `chat()` + `format="json"`, **no** `/no_think`
-    (thinking helps the two-field contract `act_text`/`move`); falls back
-    to `_NPC_INITIATIVE_ACT_FALLBACK` if the template isn't seeded; any
-    error -> silent skip.
-  - **Conversation analysis** (`analyzer.py`): thinking enabled;
-    `strip_think` before JSON parsing.
-- **French quality:** multilingual but not idiomatic-Mistral-grade;
-  acceptable for validating logic. If narrative quality disappoints, that's
-  a model-selection signal, not a code defect.
+- `gatherings.md` — gathering membership, encounters, passages.
+- `mutation-pipeline.md` — analyzers, the world tick, appliers.
+- `context-assembly.md` — NPC and MJ context, the play surface.
+- `skills.md` — skills, definitions, skill gaps.
+- `prompts.md` — prompt text and per-template models.
+- `frontend.md` — the Svelte shell, Création registries, the build.
+- `authoring-lore.md` — region generation, the Lore surface.
+- `schema-migrations.md` — migrations, the boot guard, rollback.
+- `local-models.md` — the local models and their thinking modes.
+- `verify-checks.md` — how a verify check is written.
 
 ## Conventions
 
 ### File structure
 
-One line per file: its role. History lives in the decision registry and the
-schema changelog, never in this tree.
+The top level only. Every Python module, with its role, is listed in the
+generated `tooling/standards/FILE_MAP.md`.
 
 ```
 WG-Nia/
-├── .claude/                 # Claude Code session config
-│   ├── commands/            # /pipeline /brief-exec /verify /review-step /close-step
-│   ├── hooks/               # session-start, block-main-push, block-commit-on-main, block-db-in-git
-│   └── settings.json        # permissions allowlist
-├── frontend/                 # Svelte + Vite sources; build writes the committed static/ output
-│   ├── src/legacy/           # enumerated legacy-mount registry + sole bridge into legacy
-│   ├── src/graph/            # the graph primitive, its consumers, its non-converged registry
-│   └── src/creation/         # Svelte islands + review-tree; registry.js: islands and their origin
-├── src/world_engine/        # the importable package (PYTHONPATH=src)
-│   ├── db.py                # engine + session; URL from env var
-│   ├── schema_version.py    # code-side expected static-schema constant, checked at boot
-│   ├── schema_reconcile.py  # table reconciliation: static ∪ runtime ∪ orphan; boot guard + CLI
-│   ├── models/               # SQLModel table classes, split by canon/faction/ephemeral/pipeline
-│   ├── context*.py          # NPC/MJ assembly + exclusions; context_window.py: sliding-window seam
-│   ├── knowledge_resolve.py, facet_reads.py, prose_*.py  # level resolution; facet reads; tokens
-│   ├── tick*.py             # world-tick: orchestrate/assemble/normalize; sites in world_tick.py
-│   ├── gathering.py, encounters.py, passages.py  # clustering; rencontre's, passage's writers
-│   ├── ollama_client.py     # local Ollama HTTP client; think-stripping; ping()
-│   ├── analyzer*.py         # conversation-bound wrapper + conversation-agnostic judging core
-│   ├── observation_*.py     # observed-lane socle/engine/runner/reads/writes; per-NPC window
-│   ├── resolution.py, ledger.py  # physical-action dice resolution (2d6 bands); ledger read helpers
-│   ├── skill_lexicon.py     # action lexicon: judge/record; Play calls it, never clamps inline
-│   ├── day_plan.py, condition*.py  # day plan + cut; condition forms, tree, text, interpreter
-│   ├── day_extract.py       # day extraction: 3 passes (place/person/faction), never sees registry
-│   ├── day_concordance.py   # day mention resolution: matching rungs, germ emission; never authors
-│   ├── day_rewrite.py       # declaration rewrite: render/resolutions/load_latest, no model call
-│   ├── day_resolve.py       # day step resolution: Python dice, truncation, the frozen fact sheet
-│   ├── day_narration.py     # day narration + rewrite: renders the fact sheet, never decides
-│   ├── day_narration_guard.py  # T1 judge: name containment + outcome survival, Python-only
-│   ├── day_mutations.py     # day-chain mutation emission: proposer only, never applies (V1)
-│   ├── day_feasibility.py   # feasibility veto: downward-only, clamp_verdict is the safety (Y1)
-│   ├── lore_*.py, unbound_facts.py, fact_refs.py  # Lore read/write; unbound facts; fact codes
-│   ├── writes/               # canon-write helpers by domain; schema.py is the DDL authority
-│   ├── prompt_registry.py   # prompt wiring registry; effective_model resolver
-│   ├── prompt_store.py, prompt_load.py, prompt_call.py  # version accessor; loader; JSON call
-│   ├── entity_author.py     # AI authoring assistant (entities, PC, skills, agendas, events)
-│   ├── region_author.py     # region generation orchestrator (proposes names, no canon)
-│   ├── spatial_author.py    # Creation-side door materialization from live connects_to
-│   ├── room_batch_author.py # Room batch orchestrator: manifest, fiches, coherence edges
-│   └── cockpit/             # creator web UI (FastAPI, port 8000, loopback)
-│       ├── app.py           # app factory + router mounting + fail-closed boot guard
-│       ├── play*.py         # say() decomposition: routing, physical branch, narration/initiative
-│       ├── crud/            # creator CRUD routes, split by domain (entities, relations, ...)
-│       ├── legacy.html      # legacy host for Play only now; served at /legacy in the iframe
-│       └── static/          # committed built-frontend output; served at /static, boot-guarded
-├── scripts/
-│   ├── init_db.py           # create tables + indexes (idempotent)
-│   ├── seed_pilot.py        # seed Verkhaal world + prompt templates (idempotent)
-│   ├── talk.py              # CLI conversation with an NPC
-│   ├── analyze_conversation.py  # manual window analysis of a conversation
-│   ├── cockpit.py           # launch the world cockpit
-│   ├── backup.py            # manual DB backup, 2-file rotation
-│   ├── rollback_quarantine.py  # quarantine/restore for runtime entity types (destructive, manual)
-│   └── migrate_*.py         # one idempotent migration per schema step
+├── .claude/        # commands/, hooks/, rules/ (path-scoped), settings.json
+├── frontend/       # Svelte + Vite sources; the build writes cockpit/static/
+├── src/world_engine/  # the importable package (PYTHONPATH=src)
+│   ├── models/     # SQLModel table classes
+│   ├── writes/     # canon-write helpers by domain; schema.py is the DDL authority
+│   └── cockpit/    # creator web UI (FastAPI, port 8000, loopback)
+├── scripts/        # init, seed, backup, CLI tools, one migrate_*.py per schema step
 ├── tooling/
 │   ├── tickets/, lots/, briefs/  # pipeline artifacts (filename is law); recon/ archived
-│   ├── glue/                # gen_decisions_index.py, escalation.py
-│   ├── standards/           # decision registry; generated DECISIONS_INDEX.md, FILE_MAP.md
-│   └── verify/              # run.py, checks/, baselines/, results/
-├── world-engine-schema.md   # single authoritative schema; header = current version
+│   ├── glue/       # gen_decisions_index.py, gen_file_map.py, escalation.py
+│   ├── standards/  # decision registry; generated DECISIONS_INDEX.md, FILE_MAP.md
+│   └── verify/     # run.py, checks/, baselines/, results/
+├── world-engine-schema.md            # single authoritative schema; header = current version
 ├── world-engine-schema-changelog.md  # append-only schema log
-├── CLAUDE.md                # this file (contract-checked)
-├── pyproject.toml           # src-layout package metadata
-├── requirements.txt
-└── .env.example
+├── CLAUDE.md       # this file (contract-checked)
+└── pyproject.toml, requirements.txt, .env.example
 ```
 
 ### Naming
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index b268ed8..5fa72d3 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18737,6 +18737,321 @@ The map is read on demand, never loaded at launch. Nobody maintains it but
 the docstrings: a module that cannot say what it is in one sentence is red.
 `cockpit/__init__.py`, the one module without a docstring, gets one.
 
+## THE LAW IS SPLIT BY WHERE IT HOLDS (TICKET-0117) -- TRANSVERSAL INVARIANTS IN CLAUDE.md, LOCAL ONES IN PATH-SCOPED RULES, EVERY ONE WITH A PERMANENT ID AND ITS CHECK OR `[no check]` (BRIEF-0117-e, no schema change)
+
+**D1, G1, H1, C1, F1, E1.** CLAUDE.md was at 37 202 characters of 38 000
+and 572 lines, loaded whole into every session. It now holds what must hold
+wherever new code lands: the secrets boundary, the write paths, history,
+the model resolver, JSON, zones -- INV-01 to INV-22. Law that holds for one
+part of the code moved to `.claude/rules/<topic>.md`, each with a `paths:`
+list: Claude Code loads it when a session reads or edits a matching file,
+and `/review-step` and `/close-step` read all of them on every commit. A
+directory-level `CLAUDE.md` was rejected (G2): `src/world_engine/` is flat,
+and a directory cannot scope « the condition modules ». The *Local model
+notes* moved whole to `local-models.md`; the retired `verify-authoring`
+skill is replaced by `verify-checks.md`, written to the current standards.
+
+Every invariant has an id `INV-NN` that is never reused: a retired id goes
+to `tooling/verify/baselines/invariant_ids.retired`, and live plus retired
+ids must be exactly INV-01 to the highest. Every invariant ends with
+`-- enforced by <check>.py` or `[no check]`. A link is written only where
+this ticket's RECON read the check's implementation (its failure messages)
+and found the invariant's core enforced there: the eighteen links CLAUDE.md
+already carried, plus `knowledge_identity.py`, `gathering_lifecycle.py`,
+`zone_map_links.py` and `lore_write.py`. `[no check]` means no enforcing
+check has been established -- not that none exists; the list of
+`[no check]` invariants is the debt C1 makes visible. A linked check's
+docstring holds the full law (H1), so a reviewer reads it. Old invariant
+I05 split in two (INV-16, enforced; INV-22, the fact-code rule, not).
+
+Only rationale was cut. The previous Invariants section follows verbatim,
+numbered I01 to I60 in its order, with where each now lives:
+
+~~~~text
+I01->INV-23 I02->INV-24 I03->INV-28 I04->INV-29 I05->INV-16,INV-22 I06->INV-01
+I07->INV-30 I08->INV-08 I09->INV-10 I10->INV-11 I11->INV-02 I12->INV-31
+I13->INV-17 I14->INV-32 I15->INV-09 I16->INV-14 I17->INV-15 I18->INV-35
+I19->INV-36 I20->INV-37 I21->INV-05 I22->INV-06 I23->INV-21 I24->INV-13
+I25->INV-33 I26->INV-34 I27->INV-04 I28->INV-03 I29->INV-18 I30->INV-56
+I31->INV-57 I32->INV-07 I33->INV-38 I34->INV-25 I35->INV-26 I36->INV-12
+I37->INV-41 I38->INV-42 I39->INV-43 I40->INV-44 I41->INV-45 I42->INV-46
+I43->INV-19 I44->INV-47 I45->INV-39 I46->INV-48 I47->INV-40 I48->INV-20
+I49->INV-60 I50->INV-61 I51->INV-49 I52->INV-50 I53->INV-51 I54->INV-52
+I55->INV-53 I56->INV-54 I57->INV-55 I58->INV-27 I59->INV-58 I60->INV-59
+~~~~
+
+~~~~markdown
+
+Law only. Rationale, chantier history, and deferred alternatives live in
+`tooling/standards/ARCHITECTURE_DECISIONS.md`.
+
+- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
+  gathering. Per-NPC, NOT per-location (multiple open gatherings in one
+  location are legal). Defended on every join/migrate path.
+- **Dissolve-before-create lives in the caller** (`enter_location`), never
+  inside `generate_gatherings`.
+- **`relation_change` is owned by window analysis** (`analyze_window`,
+  `proposed_by='local_ai_window'`): at most one `relation_change` per NPC
+  pair per window, proportionate to that window. Never deduplicated against
+  prior windows (not covered by `_mutation_match_key`).
+- **`new_knowledge` / `status_change` are idempotent facts:** identity-based
+  dedup (`entity_id` + `fact_refs.knowledge_key`; `entity_id`) via
+  `_mutation_match_key`, same conversation required.
+- **A `knowledge` row is identified by its fact:** `(entity_id, fact_id)` is unique. A model
+  names a fact only by a code from a `fact_refs.code_facts` list; code resolves it.
+- **Secrets are structurally excluded** from every assembled context — never
+  "guarded by instruction". The creator's note on an entity (a `histoire`
+  fact whose entity holds an `unaware` `is_secret` row on it) is excluded from
+  `facet_reads` by query construction; only the Lore dossier opts in, plus the
+  `creator` regime of `name_index` for name resolution (Lore question, names
+  panel, writing panel, condition interpreter).
+  Token posing never indexes a creator-only or unscoped appellation.
+  What an NPC knows-but-conceals lives in `knowledge` rows with
+  `is_secret = TRUE`,
+  excluded by query construction at every assembler AND every propagation
+  path (`analyze_overhearing` never sources a proposal from an `is_secret`
+  row).
+- **`relation_change`'s `entity_a_id`/`entity_b_id` come from the model's
+  payload.** Missing -> skip and log (`_normalize_to_schema` returns
+  `None`); never attributed via a conversation-level default. Per-item
+  roster resolution is a named deferral.
+- Two canon-write paths for rows: `_apply_mutation`, creator CRUD. A third covers canon STRUCTURE
+  -- closed by `single_canon_write.py` + `runtime_ddl_guard.py`.
+- **History is sacred on BOTH write paths:** any edit to `relation` or `knowledge` appends the
+  previous state to `change_history`; states are preserved, never silently overwritten.
+  `entity_type_history` extends this to the schema grain: append-only by construction, no
+  `change_history` column — the rows ARE the history.
+- **Commit before touching any canon-writing path** (`_apply_mutation`, the creator CRUD, the
+  analyzers, and everything they call) — hard. Recommended: also commit before touching the `/say`
+  flow or the interpretation phase (playability-critical). On SQLite, DDL participates in the
+  surrounding transaction — a structural guarantee of the shared engine (`db.py`), never a per-
+  site precaution.
+- **The MJ context assembler is scoped to the player's perception
+  boundary:** only what the player may perceive or already knows. Never
+  NPC-private knowledge, secrets, internal names, non-public entities, or
+  invisible relations. Enforced by query construction, never by instruction.
+- **Knowledge levels never decrease through the mutation pipeline:**
+  `unaware < rumor < suspicious < partial < knows < fully_understands` is
+  monotone for every `knowledge_change` apply (`_apply_mutation`'s
+  "level already >= proposed" guard). `analyze_overhearing` additionally
+  caps acquired/upgraded levels at `knows` in code; `analyze_window` has no
+  structural cap (named deferral). Downgrades, forgetting, and
+  `is_incorrect` correction are creator CRUD only.
+- **A `fact_participant` row is the aboutness claim for every `knowledge`
+  row on that fact.** `role` is descriptive only, never a filter or a
+  discriminator; `(fact_id, entity_id)` is unique, so every writer reads
+  before it writes.
+- **`new_knowledge`'s `subject_entity_id` is untrusted payload input,**
+  re-validated against an active entity of the mutation's own world at
+  apply, and it is never part of a dedup key.
+- **`scene_state` is a third, explicitly ephemeral write path.**
+  `_write_scene_state` archives the previous snapshot to `history[]` before
+  every write; cleared to `{}` on conversation close; never canon — durable
+  consequences require a `proposed_mutation`.
+- **`proposed_by='engine'` deterministic proposals**
+  (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
+  review queue as AI proposals — never auto-applied.
+- **`skill_progress` is the one live auto-applied mutation:** a roll's point
+  (`proposed_by='engine_roll'`) applied through `_apply_mutation` at proposal time;
+  `write_skill_progress` moves the rank -- enforced by `skill_progression.py`.
+- **Constraint gating is structural, not instructional:** gagged/restrained/
+  blindfolded effects are enforced in Python before any model call
+  (`_stream` in `app.py`). Blindfolded exclusion is a data exclusion in
+  `assemble_mj_context`, never a "don't describe" prompt.
+- **Condition ladder is monotone for engine writes:** `unharmed -> bruised -> injured ->
+  neutralized` — forward only by violent-verdict code; backward only by creator CRUD.
+- **Frozen scene yields no model calls:** `scene_state.frozen = True` -> `/say` short-circuits
+  with a fixed MJ message. Only the creator panel unfreezes.
+- **`discoverable_detail` is structurally excluded from every assembler,
+  with one consciously narrowed exception:** no assembler or prompt-building
+  path reads the table. `hidden` content reaches a model ONLY via the
+  post-selection `{detail_content}` injection in `_stream()` on a
+  partial/success perception search (`domain="perception"`,
+  `opposed_npc_id=None`). `ambient` content is read only via the pure code
+  predicate `active_signposts` (scene_format.py), passed directly into the MJ
+  establishment call. A hidden `coutume` fact (no `location` default) is a
+  TRAP — never add `"hidden"` to `FACETS["coutume"].aspects`, and every play
+  reader filters `notorious_at_location` at query construction; discoverable
+  content lives ONLY in `discoverable_detail`.
+- **`connects_to` and `borde` are location map topology, never a social
+  signal.** Their `intensity=50` is meaningless. Every gameplay reader of
+  `relation` keyed on a character/player id is structurally blind to them;
+  the sole intentional gameplay reader is `_location_neighbours`. Any new
+  world-wide relation scan MUST exclude both (`MAP_TOPOLOGY_TYPES`).
+- **A location with an active child is a zone, derived, never stored
+  (`zone_rules.py`).** Only `connects_to` is traversable and it never
+  touches a zone; a link touching a zone is `borde`. A geographic link's
+  type is derived from its endpoints (`link_locations`), never chosen. No
+  being, item or discoverable detail is placed in a zone
+  (`require_visitable`, at every placement write) -- `zone_placement.py`.
+- **The `ledger` is append-only.** INSERT-only on both canon-write paths;
+  corrections are new compensating lines. No UPDATE/DELETE endpoint or code
+  path may touch a `ledger` row.
+- **`resource_change` writes two canon tables** (`ledger` + optional
+  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single
+  sanctioned exception to one-branch-one-table. Money leg accumulates
+  (never deduped) and targets the player only, until tracked NPC purses
+  exist; knowledge leg is idempotent, guarded at apply time.
+- **Tick-sourced `proposed_mutation` rows have `source_type='world_tick'`,
+  `proposed_by='local_ai_tick'`, NULL `pass_play_id`/`conversation_id`, and
+  a mandatory `tick_id`** (one UUID per `run_world_tick` invocation).
+  `_find_applied_duplicate`'s tick branch (`cockpit/routes/mutations.py`) is
+  canon-existence-based, never a `tick_id`-scoped history comparison, and
+  must never be extended to `relation_change` (accumulating deltas, never
+  guarded).
+- **`npc_price` rows are seller configuration,** injected ONLY into that
+  seller's own dialogue context — never into `assemble_mj_context` or any
+  other entity's context. A quoted price writes no canon; money moves via
+  `resource_change` through the checkpoint. Catalogue prices are firm and
+  universal; only uncatalogued quotes are relation-modulated.
+- **Membership reaches a model prompt only via `read_public_memberships`;**
+  `is_secret` rows never enter any prompt, including the holder's own —
+  structural filter, no override parameter. The true `role` behind a
+  `cover_role` never enters any prompt: the accessor resolves
+  `cover_role ?? role`. Espionage rides on `goals` prose, never a
+  confessable affiliation label. Declared faction roles live in
+  `faction_role` (relational, never JSON; case-uniqueness is the index's job).
+- **Creator-direct create helpers never commit in their core; the commit
+  boundary belongs to the caller.** `create_entity`, `create_knowledge`,
+  `open_entity_membership` each split into a commit-free core plus a thin
+  route wrapper owning the single commit — a structural seam, not a
+  `commit:` flag.
+- **Region generation writes no canon; commit is atomic; resolution is
+  server-authoritative.** `generate_region_draft` proposes factions and
+  locations only — characters retired to the group agent (A1).
+  `POST /api/regions/commit` is the single write point: entities, skeleton
+  (`parent_location_id`, faction role vocabulary via `write_faction_role`)
+  and creator-confirmed links commit in one transaction, all-or-nothing,
+  via the commit-free cores and `write_relation`. No model-emitted id ever
+  reaches a canon row; the accept/reject cascade and link targets are
+  re-derived server-side from raw client state; rejected/uncommitted/
+  unresolved/self-referential targets write nothing.
+- **A lore statement commits whole or not at all, through `lore_write_apply.apply_proposal`.**
+  No model-emitted id reaches a canon row: facts by code, entities by name, both resolved in code
+  and confirmed by the creator; every row written is recorded in `lore_entry_row`.
+- **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is
+  NPC-only and forces `is_secret=True` — never reuse it for a PC.**
+  `_normalize_player_knowledge` emits no `is_secret` key; `False` is
+  applied at write time by the accept route (`create_player_character` via
+  `writes.write_knowledge`), never by the generator.
+- **A PC is excluded from NPC co-presence by construction:** the
+  `H_COMPANY` query in `assemble_npc_context` carries
+  `Character.character_type != "player"`. Do not widen this filter, and do
+  not repoint it at a future NPC-to-NPC observation feature without a
+  deliberate decision.
+- **Creator-CRUD edits that change a character's `current_location_id`, or
+  set an entity's `status` to a non-active value, MUST close that entity's
+  open `gathering_member` rows via `close_open_memberships`** (gatherings
+  are not canon — no `_apply_mutation`, no `change_history`). A location
+  change also attaches the entity to the destination's live open gathering
+  when the open session already holds one there, and, after the commit,
+  dissolves any gathering the move left with no active member. Roster and
+  co-present reads gate on `entity.status='active' AND
+  vital_status='alive'` in addition to `gathering_member.left_at IS NULL`.
+- **An open gathering with no active member is a defect state, not a legal
+  one:** dissolved the moment it is emptied, and ignored by the entry
+  guard where it survives anyway — a location counts as already entered
+  only while one of its open gatherings still holds an active member.
+- Hard deletes are a closed, named list -- enforced by `single_canon_write.py`; any new hard-
+  delete path must be named there, never added silently.
+- **Custom skill lookups filter `skill_definition_id`, by construction:** a
+  base-domain `skill` lookup MUST include `AND skill_definition_id IS NULL`.
+  A custom skill resolves via its `skill_definition.base_domain` — never
+  its own `domain` column — and that resolved `base_domain` is what every
+  base-domain-keyed downstream branch keys off. An NPC holds only the rows it
+  was given; Play's roll reads both sides through `skill_access` (NPC: skill,
+  else base domain, else Initié) -- enforced by `npc_skills.py`.
+- **A `skill_definition` delete always succeeds** (no `ON DELETE RESTRICT`,
+  no `change_history` snapshot): dependent PC `skill` rows then the
+  definition, one transaction. The type-"Oui" modal is the sole safeguard —
+  a named exception to "History is sacred", scoped to one row.
+- **A new open `skill_definition` backfills a default-rank `skill` row onto every
+  existing PC of its world, in the create's own transaction** — the
+  catalogue<->PC alignment of open skills is never partial. A `requires_master`
+  skill is held only once taught (`POST /api/skills`), and `skill_access` locks
+  it in Play until then. Renaming touches no `skill`
+  row (FK-by-id); re-basing (`base_domain` change) updates `domain` on
+  every dependent `skill` row in the same write.
+- **A `skill_definition.name` can never equal a base-domain literal**
+  (`physical`/`agility`/`perception`/`composure`, case-insensitive) — both
+  write paths (creator CRUD and `_normalize_skill_catalogue`) reject/drop
+  it.
+- **A `skill_definition` may carry a `system_id`** (schema v2.01), the body
+  of rules it belongs to; NULL = unaffiliated. `DELETE
+  /api/skill-systems` refuses while any skill is still attached, unlike
+  `DELETE /api/skill-definitions`, which deletes its dependents.
+- **`GET /api/skill-gaps` is read-only** — it performs no write of any
+  kind. It surfaces distinct `unmatched` `skill_resolution.surface_form`
+  rows for the active world; the two arbiter-failure sentinels
+  (`__arbiter_error__`, `__arbiter_empty__`) are excluded from its `gaps`
+  list by design and reported separately in `arbiter_failures`.
+- **All templated model calls resolve through
+  `prompt_registry.effective_model`** — the single model resolver. New
+  prompt usages must add a `PROMPT_REGISTRY` entry
+  (`tooling/verify/checks/prompt_registry.py` enforces).
+- `prompt_template.model` is written ONLY via `PATCH /api/prompts/{id}/model`, validated fail-
+  closed against live Ollama -- enforced by `prompt_model_write.py`.
+- **`_npc_dialogue_system_prompt(system_prompt, context)` in `cockpit/play.py`
+  is the single npc_dialogue system-prompt construction:** every live call
+  site and the Prompts tab's assembled preview call it — never a duplicated
+  inline concatenation.
+- Prompt text lives ONLY in the append-only `prompt_version` table, never
+  UPDATE/DELETE -- enforced by `prompt_version.py`.
+- Affinity tiers are resolved in code (`context.py::_affinity_tier`);
+  prompt templates never carry the tier table.
+- **UI-visible data never lives in JSON** — relational only; enforced
+  fail-closed by `json_ui_boundary` (exceptions justified in that file).
+- **The app refuses to boot when `schema_meta.static_version` !=
+  `EXPECTED_STATIC_SCHEMA_VERSION`, OR when a physical table is neither a static model table nor
+  a registered `entity_type.physical_table`** (fail-closed on both; the second check is
+  `schema_reconcile.unaccounted_tables`, extending the same `cockpit/app.py` startup hook —
+  `_orphan_ext_*` quarantine tables are pattern-accounted, never flagged); `schema_meta` is
+  migration-only infra, never canon, never writable outside a migration script.
+- **Rollback contract (B1):** "Once a runtime type exists, rolling code back past the
+  constructor version requires running `scripts/rollback_quarantine.py` first (after a backup).
+  Roll-forward restoration (`--restore`) is potentially lossy, bounded to rows whose `entity`
+  row was deleted during the rollback window; every lost row is preserved in `_orphan_lost_*`
+  and reported — never silently dropped. This contract is SQLite-scoped (the rebuild-without-FK
+  recipe is SQLite-specific), matching the engine's current single-backend reality." Full
+  rationale: `ARCHITECTURE_DECISIONS.md`, "ENTITY-TYPE CONSTRUCTOR — rollback quarantine (B1)".
+- Every Création page is a `CREATION_TABS` registry entry rendered by the generic dispatcher; no
+  page/tab-specific branch exists outside it — enforced by `page_contract.py`.
+- Every Création surface mounts as a `CREATION_ISLANDS` entry declaring its origin (`migration` or
+  `new`) through `mount.js` alone; `Creation.svelte` imports and renders no component — enforced by
+  `creation_island.py`.
+- The review tree (`review*`, `frontend/src/creation/review/registry.js`) is a generic
+  accept/reject component, never driven by consumer globals — enforced by `review_component.py`.
+- The graph primitive (`frontend/src/graph/Graph.svelte`) is the ONE graph component; a second
+  engine is constructible only by defeating `graph_primitive.py`'s fail-closed lock.
+- A Creation sub-tab change clears the entity sheet from the single dispatcher
+  (`showCreationSubTab`), BEFORE `activeTabKey` moves and on every change, never per
+  registry entry; and `Sheet.svelte` selects its render branch from `sheetType`, the same
+  fact that feeds it, never from `activeTabKey` -- enforced by `creation_tab_switch.py`.
+- A Création tab that owns a single container sizes it in `frontend/public/creation.css`
+  (`flex: 1; min-height: 0`), so its content scrolls instead of being clipped -- enforced by
+  `creation_container_sizing.py`.
+- Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the
+  same body — enforced by `effect_self_write.py`.
+- `passage` is written only by `passages.py`, whose `before_flush` listener records every
+  placement write; `rencontre.last_at` moves forward only, in `encounters.py` -- enforced by
+  `fact_learning.py`.
+- **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches
+  a model — every empty verdict is rendered by code, so an absence is never explained by a model.
+- **The Lore usage journal (`lore_usage_event`) is written only through `lore_usage` and read only
+  by `scripts/export_lore_usage.py`;** no prompt, play or creator path reads it back, and it has no
+  `world_id`, so it outlives its world -- enforced by `lore_usage.py`.
+~~~~
+
+The hand-kept file tree gave way to the generated `FILE_MAP.md`
+(BRIEF-0117-d); CLAUDE.md keeps the top level. `claude_md_contract.py` now
+covers the root and every rule file: budgets (22 000 and 4 000 characters),
+ids and markers, rule globs that still match a file, and the rule files
+listed in the root's « Path-scoped rules » section. `npc_skills.py` B4 reads
+`skills.md`, where `requires_master` and `skill_access` now live. Rejected:
+D2 (compress only, everything in the root; reactivation: a session misses a
+local invariant), D3 (an imported file: loaded at launch anyway), H2 (a
+second full text of each invariant), H3 (cut without keeping the law).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/baselines/invariant_ids.retired b/tooling/verify/baselines/invariant_ids.retired
new file mode 100644
index 0000000..b491422
--- /dev/null
+++ b/tooling/verify/baselines/invariant_ids.retired
@@ -0,0 +1,6 @@
+# TICKET-0117 (F1). Append-only record of every retired invariant id: one
+# line per id, `INV-NN|<ticket>|<one-line reason>`. An id enters this file
+# in the same commit that removes its invariant from CLAUDE.md or
+# .claude/rules/, and is never removed or reused afterward.
+# tooling/verify/checks/claude_md_contract.py requires live and retired ids
+# together to be exactly INV-01 to the highest.
diff --git a/tooling/verify/checks/claude_md_contract.py b/tooling/verify/checks/claude_md_contract.py
index 8eddabb..b56c4c6 100644
--- a/tooling/verify/checks/claude_md_contract.py
+++ b/tooling/verify/checks/claude_md_contract.py
@@ -1,36 +1,41 @@
-"""G1 check for TICKET-0010 (BRIEF-0010-a) — CLAUDE.md structural contract.
+"""G1 check for TICKET-0010 (BRIEF-0010-a), extended by TICKET-0117 -- the
+instruction corpus: the root CLAUDE.md and every `.claude/rules/*.md`.
 
 CLAUDE.md is a law-only, budgeted, contract-checked file: history and
 chantier narrative live in ARCHITECTURE_DECISIONS.md and the schema
-changelog, never here. This check makes "stays up to date" structural
-instead of disciplinary.
-
-Five assertions, all against repo-root CLAUDE.md:
-
-1. Section whitelist, exact and ordered — the H2 set and the H3 set under
-   Conventions. Any missing, extra, or reordered heading fails.
-2. Budgets — total file <= 38 000 characters; no line (fenced blocks
-   included, no exemption) exceeds 100 characters; the "### File
-   structure" section (heading to next heading) <= 80 lines.
-   The budget is a character budget on purpose. A line budget measures a
-   quantity that line length defeats: at 499 lines this file held 47 084
-   characters, three of its lines exceeding 1 000 each, and reflowed at 80
-   columns it would have run 750 lines.
-3. Archaeology ban — File structure section: zero (case-sensitive) matches
-   for `BRIEF-`, `schema v`, or `v\\d+\\.\\d+` within the section.
-   Invariants section: zero matches for `TICKET-\\d` or `BRIEF-\\d`
-   anywhere from its heading to the next H2; an Invariants section that
-   collects zero `- ` bullets is itself a FAILURE, not a pass.
-4. Pointer freshness, `tooling/...` paths — every `tooling/...` path
-   mentioned anywhere in CLAUDE.md exists on disk. Tokens are found by
-   splitting on whitespace and backticks; a `path|alt1|alt2` shorthand
-   (e.g. `tooling/tickets|recon|briefs`) expands each bare alternative as
-   a sibling of the first segment's directory before testing.
-5. Pointer freshness, bare `.py` tokens — every token matching
-   `\\b[a-z0-9_]+\\.py\\b` anywhere in CLAUDE.md resolves to at least one
-   file in the repository, found by filename under the repo root,
-   excluding `.venv/` and `node_modules/`; zero tokens collected is
-   itself a FAILURE.
+changelog, never here. Invariants that hold for one part of the code live
+in path-scoped rule files, loaded by Claude Code when a session touches a
+matching file (TICKET-0117, D1/G1). This check makes "stays up to date"
+structural instead of disciplinary.
+
+1. Section whitelist, exact and ordered -- the root's H2 set and the H3 set
+   under Conventions. Any missing, extra, or reordered heading fails.
+2. Budgets -- root <= 22 000 characters and each rule file <= 4 000; no line
+   of any of them (fenced blocks included) exceeds 100 characters; the
+   root's "### File structure" section (heading to next heading) <= 30
+   lines. The budget counts characters, not bytes or lines.
+3. Archaeology ban -- File structure: zero (case-sensitive) matches for
+   `BRIEF-`, `schema v`, or `v\\d+\\.\\d+`. Every Invariants section (the
+   root's, and each rule file's `## Invariants`): zero matches for
+   `TICKET-\\d` or `BRIEF-\\d`.
+4. Pointer freshness, `tooling/...` paths -- every `tooling/...` path in any
+   file of the corpus exists on disk; a `path|alt1|alt2` shorthand expands
+   each bare alternative as a sibling of the first segment's directory.
+5. Pointer freshness, bare `.py` tokens -- every `\\b[a-z0-9_]+\\.py\\b`
+   token in the corpus names a file somewhere in the repository (excluding
+   `.venv/` and `node_modules/`); zero tokens collected is a FAILURE.
+6. Invariant ids (C1, F1) -- every bullet of every Invariants section starts
+   `- **INV-NN**` and ends with `-- enforced by` and one or more
+   `` `<check>.py` `` naming files under `tooling/verify/checks/`, or with
+   `[no check]`. Ids are unique across the corpus; none is listed in
+   `tooling/verify/baselines/invariant_ids.retired`; live and retired ids
+   together are exactly INV-01 to the highest, so an id is never dropped
+   silently. Zero invariants collected is a FAILURE.
+7. Rule files (G1) -- `.claude/rules/` holds at least one `*.md`; each opens
+   with a front-matter block `---` / `paths:` / one or more `  - "<glob>"`
+   lines / `---`; a glob holds no `{` or `[` and matches at least one file
+   from the repository root. The file names listed in the root's
+   "Path-scoped rules" section equal the files on disk.
 """
 from __future__ import annotations
 
@@ -40,6 +45,9 @@ import sys
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 CLAUDE_MD = ROOT / "CLAUDE.md"
+RULES_DIR = ROOT / ".claude" / "rules"
+CHECKS_DIR = ROOT / "tooling" / "verify" / "checks"
+RETIRED_IDS = ROOT / "tooling" / "verify" / "baselines" / "invariant_ids.retired"
 
 FAILURES: list[str] = []
 
@@ -55,7 +63,7 @@ EXPECTED_H2 = [
     "Ticket pipeline (governance)",
     "Numbering & decisions governance",
     "Invariants (verified at every review)",
-    "Local model notes",
+    "Path-scoped rules",
     "Conventions",
 ]
 
@@ -66,9 +74,10 @@ EXPECTED_H3_UNDER_CONVENTIONS = [
     "How to run / test",
 ]
 
-TOTAL_CHAR_BUDGET = 38_000
+ROOT_CHAR_BUDGET = 22_000
+RULE_CHAR_BUDGET = 4_000
 MAX_LINE_LENGTH = 100
-FILE_STRUCTURE_LINE_BUDGET = 80
+FILE_STRUCTURE_LINE_BUDGET = 30
 
 ARCHAEOLOGY_PATTERNS = [
     re.compile(r"BRIEF-"),
@@ -82,99 +91,158 @@ INVARIANTS_ARCHAEOLOGY_PATTERNS = [
 ]
 
 PY_TOKEN_PATTERN = re.compile(r"\b[a-z0-9_]+\.py\b")
+INV_HEAD = re.compile(r"^- \*\*INV-(\d{2})\*\* ")
+ENFORCED = re.compile(r"-- enforced by ((?:`[a-z0-9_]+\.py`, )*`[a-z0-9_]+\.py`)$")
+NO_CHECK = "[no check]"
+GLOB_LINE = re.compile(r'^  - "([^"]+)"$')
+RULE_LISTING = re.compile(r"^- `([a-z0-9-]+\.md)` — ")
 
 
-def check_section_whitelist(lines: list[str]) -> None:
-    h2 = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
-    if h2 != EXPECTED_H2:
-        fail(f"H2 section set/order mismatch: got {h2!r}, expected {EXPECTED_H2!r}")
-
-    # H3 headings strictly between the "## Conventions" H2 and the next H2
-    # (or EOF) — the whitelisted H3 set applies only there.
-    try:
-        conv_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "## Conventions")
-    except StopIteration:
-        fail("'## Conventions' heading not found — cannot check its H3 subsections")
-        return
-    end_idx = len(lines)
-    for i in range(conv_idx + 1, len(lines)):
-        if lines[i].startswith("## "):
-            end_idx = i
-            break
-    h3 = [ln[4:].strip() for ln in lines[conv_idx + 1:end_idx] if ln.startswith("### ")]
-    if h3 != EXPECTED_H3_UNDER_CONVENTIONS:
-        fail(
-            f"H3 subsection set/order under Conventions mismatch: got {h3!r}, "
-            f"expected {EXPECTED_H3_UNDER_CONVENTIONS!r}"
-        )
-
-
-def _file_structure_section(lines: list[str]) -> list[str]:
+def section(lines: list[str], heading: str, stop: tuple[str, ...]) -> list[str]:
+    """From the line equal to `heading` to the next line starting with any
+    of `stop`; [] when the heading is absent."""
     try:
-        start = next(i for i, ln in enumerate(lines) if ln.strip() == "### File structure")
+        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
     except StopIteration:
-        fail("'### File structure' heading not found")
         return []
     end = len(lines)
     for i in range(start + 1, len(lines)):
-        if lines[i].startswith("## ") or lines[i].startswith("### "):
+        if lines[i].startswith(stop):
             end = i
             break
     return lines[start:end]
 
 
-def _invariants_section(lines: list[str]) -> list[str]:
-    try:
-        start = next(
-            i for i, ln in enumerate(lines)
-            if ln.strip() == "## Invariants (verified at every review)"
+def check_section_whitelist(lines: list[str]) -> None:
+    h2 = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
+    if h2 != EXPECTED_H2:
+        fail(f"H2 section set/order mismatch: got {h2!r}, expected {EXPECTED_H2!r}")
+    conventions = section(lines, "## Conventions", ("## ",))
+    if not conventions:
+        fail("'## Conventions' heading not found — cannot check its H3 subsections")
+        return
+    h3 = [ln[4:].strip() for ln in conventions if ln.startswith("### ")]
+    if h3 != EXPECTED_H3_UNDER_CONVENTIONS:
+        fail(
+            f"H3 subsection set/order under Conventions mismatch: got {h3!r}, "
+            f"expected {EXPECTED_H3_UNDER_CONVENTIONS!r}"
         )
-    except StopIteration:
-        fail("'## Invariants (verified at every review)' heading not found")
-        return []
-    end = len(lines)
-    for i in range(start + 1, len(lines)):
-        if lines[i].startswith("## "):
-            end = i
-            break
-    return lines[start:end]
 
 
-def check_budgets(text: str, lines: list[str], structure_section: list[str]) -> None:
-    if len(text) > TOTAL_CHAR_BUDGET:
-        fail(f"CLAUDE.md is {len(text)} characters, over the {TOTAL_CHAR_BUDGET}-character budget")
-    for i, line in enumerate(lines, start=1):
+def check_budgets(name: str, text: str, budget: int) -> None:
+    if len(text) > budget:
+        fail(f"{name} is {len(text)} characters, over the {budget}-character budget")
+    for i, line in enumerate(text.splitlines(), start=1):
         if len(line) > MAX_LINE_LENGTH:
-            fail(f"line {i} is {len(line)} characters, over the {MAX_LINE_LENGTH}-character ceiling")
-    if len(structure_section) > FILE_STRUCTURE_LINE_BUDGET:
-        fail(
-            f"'### File structure' section is {len(structure_section)} lines, "
-            f"over the {FILE_STRUCTURE_LINE_BUDGET}-line budget"
-        )
+            fail(f"{name} line {i} is {len(line)} characters, over the "
+                 f"{MAX_LINE_LENGTH}-character ceiling")
 
 
-def check_archaeology_ban(structure_section: list[str]) -> None:
-    for offset, line in enumerate(structure_section):
+def check_file_structure(lines: list[str]) -> None:
+    structure = section(lines, "### File structure", ("## ", "### "))
+    if not structure:
+        fail("'### File structure' heading not found")
+        return
+    if len(structure) > FILE_STRUCTURE_LINE_BUDGET:
+        fail(f"'### File structure' section is {len(structure)} lines, "
+             f"over the {FILE_STRUCTURE_LINE_BUDGET}-line budget")
+    for offset, line in enumerate(structure):
         for pattern in ARCHAEOLOGY_PATTERNS:
             if pattern.search(line):
-                fail(
-                    f"'### File structure' line {offset + 1} matches banned "
-                    f"pattern {pattern.pattern!r}: {line.strip()!r}"
-                )
+                fail(f"'### File structure' line {offset + 1} matches banned "
+                     f"pattern {pattern.pattern!r}: {line.strip()!r}")
 
 
-def check_invariants_archaeology(invariants_section: list[str]) -> None:
-    bullets = [ln for ln in invariants_section if ln.strip().startswith("- ")]
-    if not bullets:
-        fail("'## Invariants' section collects zero '- ' bullets — an emptied section is a FAILURE")
-        return
-    for offset, line in enumerate(invariants_section):
+def invariant_bullets(name: str, block: list[str]) -> list[str]:
+    """Each `- ` bullet of an Invariants section, its continuation lines
+    joined with single spaces; archaeology-checked on the way."""
+    bullets: list[str] = []
+    for offset, line in enumerate(block):
         for pattern in INVARIANTS_ARCHAEOLOGY_PATTERNS:
             if pattern.search(line):
-                fail(
-                    f"'## Invariants' line {offset + 1} matches banned "
-                    f"pattern {pattern.pattern!r}: {line.strip()!r}"
-                )
+                fail(f"{name} Invariants line {offset + 1} matches banned "
+                     f"pattern {pattern.pattern!r}: {line.strip()!r}")
+        if line.startswith("- "):
+            bullets.append(line.strip())
+        elif bullets and line.startswith("  ") and line.strip():
+            bullets[-1] += " " + line.strip()
+    return bullets
+
+
+def check_invariant(name: str, bullet: str) -> int | None:
+    head = INV_HEAD.match(bullet)
+    if head is None:
+        fail(f"{name}: invariant without an '- **INV-NN**' id: {bullet[:70]!r}")
+        return None
+    inv_id = f"INV-{head.group(1)}"
+    enforced = ENFORCED.search(bullet)
+    if enforced:
+        for check in re.findall(r"`([a-z0-9_]+\.py)`", enforced.group(1)):
+            if not (CHECKS_DIR / check).exists():
+                fail(f"{name}: {inv_id} is enforced by {check}, not found in tooling/verify/checks/")
+    elif not bullet.endswith(NO_CHECK):
+        fail(f"{name}: {inv_id} ends with neither '-- enforced by `<check>.py`' nor '{NO_CHECK}'")
+    return int(head.group(1))
+
+
+def check_invariant_ids(ids: list[tuple[str, int]]) -> None:
+    if not ids:
+        fail("zero invariants collected across the corpus — an emptied law is a FAILURE")
+        return
+    seen: dict[int, str] = {}
+    for name, number in ids:
+        if number in seen:
+            fail(f"INV-{number:02d} appears in {seen[number]} and {name}")
+        seen[number] = name
+    if not RETIRED_IDS.exists():
+        fail(f"{RETIRED_IDS.relative_to(ROOT).as_posix()} not found")
+        return
+    retired = {
+        int(m.group(1))
+        for line in RETIRED_IDS.read_text(encoding="utf-8").splitlines()
+        if (m := re.match(r"^INV-(\d{2})\b", line))
+    }
+    for number in sorted(retired & set(seen)):
+        fail(f"INV-{number:02d} is retired but still live in {seen[number]}")
+    issued = set(seen) | retired
+    missing = sorted(set(range(1, max(issued) + 1)) - issued)
+    if missing:
+        fail("ids neither live nor retired: " + ", ".join(f"INV-{n:02d}" for n in missing))
+
+
+def rule_paths(name: str, lines: list[str]) -> list[str]:
+    if not lines or lines[0] != "---" or len(lines) < 3 or lines[1] != "paths:":
+        fail(f"{name}: does not open with a '---' / 'paths:' front-matter block")
+        return []
+    globs: list[str] = []
+    for line in lines[2:]:
+        if line == "---":
+            break
+        match = GLOB_LINE.match(line)
+        if match is None:
+            fail(f"{name}: front-matter line {line!r} is not '  - \"<glob>\"'")
+            return []
+        globs.append(match.group(1))
+    else:
+        fail(f"{name}: front-matter block is not closed by '---'")
+    if not globs:
+        fail(f"{name}: 'paths:' lists no glob")
+    return globs
+
+
+def check_rule_globs(name: str, globs: list[str]) -> None:
+    for pattern in globs:
+        if "{" in pattern or "[" in pattern:
+            fail(f"{name}: glob {pattern!r} uses braces or brackets")
+        elif not any(ROOT.glob(pattern)):
+            fail(f"{name}: glob {pattern!r} matches no file")
+
+
+def check_rule_listing(lines: list[str], on_disk: list[str]) -> None:
+    block = section(lines, "## Path-scoped rules", ("## ",))
+    listed = sorted(m.group(1) for line in block if (m := RULE_LISTING.match(line)))
+    if listed != sorted(on_disk):
+        fail(f"'## Path-scoped rules' lists {listed}, .claude/rules/ holds {sorted(on_disk)}")
 
 
 def _expand_pipe_shorthand(token: str) -> list[str]:
@@ -189,58 +257,79 @@ def _expand_pipe_shorthand(token: str) -> list[str]:
     return candidates
 
 
-def check_pointer_freshness(text: str) -> None:
-    tokens = re.split(r"[\s`]+", text)
-    for raw in tokens:
+def check_pointer_freshness(name: str, text: str) -> None:
+    for raw in re.split(r"[\s`]+", text):
         token = raw.strip().rstrip(",.;:)")
         if not token.startswith("tooling/"):
             continue
         for candidate in _expand_pipe_shorthand(token):
             if not (ROOT / candidate).exists():
-                fail(f"CLAUDE.md references {candidate!r} (from token {raw!r}) — not found on disk")
+                fail(f"{name} references {candidate!r} (from token {raw!r}) — not found on disk")
 
 
-def check_py_pointer_freshness(text: str) -> None:
-    tokens = sorted(set(PY_TOKEN_PATTERN.findall(text)))
+def check_py_pointer_freshness(corpus: dict[str, str]) -> None:
+    tokens = {(tok, name) for name, text in corpus.items() for tok in PY_TOKEN_PATTERN.findall(text)}
     if not tokens:
-        fail("zero bare '<name>.py' tokens found in CLAUDE.md — delegation pointers are gone")
+        fail("zero bare '<name>.py' tokens found in the corpus — delegation pointers are gone")
         return
     names_on_disk = {
         p.name
         for p in ROOT.rglob("*.py")
         if ".venv" not in p.parts and "node_modules" not in p.parts
     }
-    for token in tokens:
+    for token, name in sorted(tokens):
         if token not in names_on_disk:
-            fail(f"CLAUDE.md references {token!r} — no file with that name found on disk")
+            fail(f"{name} references {token!r} — no file with that name found on disk")
+
+
+def load_rules() -> dict[str, str]:
+    if not RULES_DIR.is_dir():
+        fail(".claude/rules/ not found")
+        return {}
+    rules = {p.name: p.read_text(encoding="utf-8") for p in sorted(RULES_DIR.glob("*.md"))}
+    if not rules:
+        fail(".claude/rules/ holds no *.md — zero rule files collected")
+    return rules
 
 
 def main() -> int:
     if not CLAUDE_MD.exists():
-        fail("repo-root CLAUDE.md not found")
         print("FAIL: CLAUDE.md not found")
         return 1
-
     text = CLAUDE_MD.read_text(encoding="utf-8")
     lines = text.splitlines()
+    rules = load_rules()
+    corpus = {"CLAUDE.md": text} | {f".claude/rules/{n}": t for n, t in rules.items()}
 
     check_section_whitelist(lines)
-    structure_section = _file_structure_section(lines)
-    invariants_section = _invariants_section(lines)
-    check_budgets(text, lines, structure_section)
-    check_archaeology_ban(structure_section)
-    check_invariants_archaeology(invariants_section)
-    check_pointer_freshness(text)
-    check_py_pointer_freshness(text)
+    check_budgets("CLAUDE.md", text, ROOT_CHAR_BUDGET)
+    check_file_structure(lines)
+    blocks = {"CLAUDE.md": section(lines, "## Invariants (verified at every review)", ("## ",))}
+    for name, body in rules.items():
+        rule_lines = body.splitlines()
+        check_budgets(f".claude/rules/{name}", body, RULE_CHAR_BUDGET)
+        check_rule_globs(name, rule_paths(name, rule_lines))
+        blocks[f".claude/rules/{name}"] = section(rule_lines, "## Invariants", ("## ",))
+    check_rule_listing(lines, list(rules))
+    ids: list[tuple[str, int]] = []
+    for name, block in blocks.items():
+        for bullet in invariant_bullets(name, block):
+            number = check_invariant(name, bullet)
+            if number is not None:
+                ids.append((name, number))
+    check_invariant_ids(ids)
+    for name, body in corpus.items():
+        check_pointer_freshness(name, body)
+    check_py_pointer_freshness(corpus)
 
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print(
-        "PASS: CLAUDE.md contract — section whitelist, character/line "
-        "budgets, File-structure archaeology ban, Invariants archaeology "
-        "ban, tooling/ pointer freshness, .py pointer freshness"
+        f"PASS: CLAUDE.md contract — root and {len(rules)} rule file(s): whitelist, "
+        f"budgets, archaeology bans, {len(ids)} invariants with ids and markers, "
+        "rule globs live, pointers fresh"
     )
     return 0
 
diff --git a/tooling/verify/checks/npc_skills.py b/tooling/verify/checks/npc_skills.py
index 5e67942..11ba484 100644
--- a/tooling/verify/checks/npc_skills.py
+++ b/tooling/verify/checks/npc_skills.py
@@ -63,7 +63,8 @@ B3 -- learning (fixture, C1). `GET /api/skills/learnable` lists, for a
    or the learner as his own master, 422; a second time, 409; without a
    master, the row with `taught_by_id` None; an NPC base domain at rank 4.
    `GET /api/skills` serves `requires_master` and `taught_by_id`.
-B4 -- documentation (static). CLAUDE.md names `requires_master` and
+B4 -- documentation (static). The skills rule file
+   (`.claude/rules/skills.md`, TICKET-0117) names `requires_master` and
    `skill_access`'s lock.
 
 C1 -- the routes the fiche reads (BRIEF-0107-C, fixture).
@@ -527,9 +528,10 @@ def check_b3(engine) -> None:
 
 
 def check_b4() -> None:
-    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
+    rule = ROOT / ".claude" / "rules" / "skills.md"
+    text = rule.read_text(encoding="utf-8") if rule.exists() else ""
     if "requires_master" not in text or "skill_access" not in text:
-        fail("B4: CLAUDE.md does not name requires_master and skill_access")
+        fail("B4: .claude/rules/skills.md does not name requires_master and skill_access")
 
 
 # --- C1-C2 ---------------------------------------------------------------------
diff --git a/tooling/verify/checks/session_config.py b/tooling/verify/checks/session_config.py
index 470086c..26042a7 100644
--- a/tooling/verify/checks/session_config.py
+++ b/tooling/verify/checks/session_config.py
@@ -22,6 +22,10 @@ SC4 -- /pipeline. `pipeline.md` pushes only `ticket/NNNN`, escalates
    mode nor a recon stage.
 SC5 -- retired. `.claude/commands/recon.md` and the skills `recon`,
    `brief` and `verify-authoring` do not exist (L4-L6).
+SC6 -- the whole law (BRIEF-0117-e). `review-step.md` and `close-step.md`
+   each read every `.claude/rules/*.md` besides the root CLAUDE.md, and
+   `review-step.md` sends a reviewer to the docstring of an invariant's
+   enforcing check.
 """
 from __future__ import annotations
 
@@ -142,12 +146,23 @@ def check_retired() -> None:
             fail(f"SC5: {path.relative_to(ROOT).as_posix()} exists; it was retired")
 
 
+def check_whole_law() -> None:
+    for name in ("review-step.md", "close-step.md"):
+        text = flat(read(COMMANDS / name))
+        if text and "`.claude/rules/*.md`" not in text:
+            fail(f"SC6: {name} does not read every .claude/rules/*.md")
+    review = flat(read(COMMANDS / "review-step.md"))
+    if review and "the full law is that check's docstring" not in review:
+        fail("SC6: review-step.md does not send the reviewer to the check's docstring")
+
+
 def main() -> int:
     check_settings()
     check_commit_hook()
     check_chain()
     check_pipeline()
     check_retired()
+    check_whole_law()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
````

## Scope OUT

- Adding, removing or weakening an invariant; changing a `[no check]` into
  a link, or a link into `[no check]`. The 61 bullets are exactly those of
  the diff.
- Writing a new check for a `[no check]` invariant (each is a later
  ticket's).
- A `CLAUDE.md` in any subdirectory (G2, rejected), an `@` import (D3,
  rejected).
- Moving `src/world_engine/` modules (TICKET-0118).
- Any change to `skill_progression.py`: `skill_progress` stays in the root
  (INV-15) and its B4 keeps reading CLAUDE.md.

## Invariants to defend

All of them, by text: this brief rewrites where every invariant lives, so a
lost clause is the failure to fear. `/review-step` for this commit compares
each old bullet (the archived I01-I60 in the decision entry) with its
`INV-NN` (the mapping table there) and argues, per bullet, that only
rationale left. **Secrets** (INV-01 to INV-07) and the **write paths**
(INV-08 to INV-15) stay in the root by construction: a rule file would miss
a new module.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` fails on a file this brief names, other than the ADAPT case below.
- `/review-step` finds a law clause of an old bullet missing from its `INV-NN`.
- A named mutation does not turn its rule red.
- Any check of Done means is red for a reason this brief does not list.

ADAPT:
- `git apply` fails only on `ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry by hand just above the footer, then regenerate the index.
- A rule glob matches no file because a module was renamed since `8aa388e` (the contract names the glob): replace the glob with the new name in this commit and report it; a glob whose module was deleted is a STOP.

REPORT-ONLY:
- CLAUDE.md is still over 200 lines (the documented recommendation); its budget is characters.
- Corpus timing.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists the files of the embedded diff, `tooling/standards/FILE_MAP.md` and `tooling/standards/DECISIONS_INDEX.md`.
- `python tooling/verify/checks/claude_md_contract.py` -> `PASS: CLAUDE.md contract — root and 10 rule file(s): whitelist, budgets, archaeology bans, 61 invariants with ids and markers, rule globs live, pointers fresh`
- `npc_skills.py`, `skill_progression.py`, `session_config.py`, `file_map.py`, `decisions_index.py`, `pipeline_state.py` -> `PASS`.
- `python -c "t=open('CLAUDE.md',encoding='utf-8').read();print(len(t))"` -> `19767`.
- Mutation tests, each red then reverted (`claude_md_contract.py` exits 1):
  - in `CLAUDE.md`, `  invisible relations. [no check]` -> `  invisible relations.` -> `CLAUDE.md: INV-02 ends with neither '-- enforced by `<check>.py`' nor '[no check]'`
  - in `.claude/rules/mutation-pipeline.md`, `- **INV-30**` -> `- **INV-29**` -> `INV-29 appears in … and …` and `ids neither live nor retired: INV-30`
  - in `.claude/rules/context-assembly.md`, `  - "src/world_engine/scene_format.py"` -> `  - "src/world_engine/scene_formats.py"` -> `context-assembly.md: glob 'src/world_engine/scene_formats.py' matches no file`
  - in `CLAUDE.md`, `` `zone_map_links.py` `` (end of INV-21) -> `` `zone_links.py` `` -> `INV-21 is enforced by zone_links.py, not found in tooling/verify/checks/`
  - in `CLAUDE.md`, delete the line ``- `prompts.md` — prompt text and per-template models.`` -> `'## Path-scoped rules' lists [...], .claude/rules/ holds [...]`
  - in `.claude/rules/skills.md`, `skill_access` -> `skill_gate` (every occurrence) -> `npc_skills.py`: `B4: .claude/rules/skills.md does not name requires_master and skill_access`
  - in `.claude/commands/review-step.md`, `the full law is that check's docstring: read` -> `read the check: read` -> `session_config.py`: `SC6: review-step.md does not send the reviewer to the check's docstring`
- Live: in a fresh Claude Code session, after it reads `frontend/src/App.svelte`, it states INV-49 without opening `.claude/rules/frontend.md`.
- `python tooling/verify/checks/corpus_gate.py` -> `147 check(s) discovered, 147 executed, 147 passed`.
- `/review-step` then `/close-step` ran on the commit, in the same turn.

## Docs to update

Decision entry « THE LAW IS SPLIT BY WHERE IT HOLDS (TICKET-0117) … (BRIEF-0117-e, no schema change) » -- in the diff, with the previous Invariants section verbatim. This step IS the CLAUDE.md update. No schema change.
