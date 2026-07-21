---
id: TICKET-0037
title: NPC group generation agent + region wizard NPC retirement
type: feature
status: live-gate
created: 2026-07-21
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
brief_ids: [BRIEF-0037-a, BRIEF-0037-b, BRIEF-0037-c, BRIEF-0037-d, BRIEF-0037-e]
schema_version_touched: vX.YY (npc_batch / npc_batch_row, brief a)
retry_count: 1
---

## Request (verbatim, as Nia stated it)

"On refechis a changer la facon dont on cree les region. On retire les NPC
et on se fait quelquechose qui ressemble a ce que l'on viens de faire mais
ajoute des NPC au monde (par exemple je decrit le goupe de npc que je veux
avec des chiffres) et on me le genere avec des choses qui font du sens dans
le monde (factions et lieux). Ca deviens donc regions -> NPC -> liens NPC."

## Clarifications resolved (intake)

Locked decisions (chat, 2026-07-21):

- **A1** -- hard retirement of the region pipeline's NPC machinery. The
  manifest loses its `npcs` section; Stage 3, the density floor (BRIEF-39)
  and the top-up clamp (BRIEF-40) are REMOVED, not bypassed (S-norme: no
  dead code). Explicit retirement list anchored by RECON, below.
- **B1** -- structured count spec + prose: the creator submits lines
  `{count, description, faction?, location?}` plus a free group brief.
  The count is a contract: code generates exactly N per line by
  construction (one generation call per NPC, loop of N) -- no floor, no
  clamp, no numeric steering prompt.
- **C1** -- placement authority is per line. Creator-anchored lines pin
  faction/location by canon id (dropdowns). Unanchored lines let the model
  place, resolved BY NAME against existing canon only, S1 posture
  (chantier 3): a miss is a skipped row with a note, never an
  auto-created entity.
- **D** -- reuse the TICKET-0036 staging pattern (confirmed by RECON:
  `link_batch`/`link_batch_row`, ephemeral stratum, last-2 retention
  purge at startup, append-only journal).
- **E1 / J1** -- composition handoff: batch commit offers "Generer les
  liens" prefilled with the group's region `root_location_ids` -- the
  link roster then includes pre-existing residents (desired: new NPCs
  link to the existing fabric) and F1 skips already-canon pairs.
- **F** -- goals generated at draft time and written at commit in the
  SAME transaction as the NPC (G1 posture, `_commit_region_npcs`
  precedent); knowledge is NOT generated here -- inter-NPC knowledge is
  the link agent's territory, downstream.
- **G1** -- sibling ephemeral tables `npc_batch` / `npc_batch_row`
  (payload = full NPC draft per row), never a generalization of
  `link_batch` (pair grain vs entity grain). Same retention (last 2,
  purge extended), same journal posture
  (`~/.world_engine/npc_agent_journal/`).
- **H1** -- direct-to-draft, one `generate_entity_draft("character")`
  call per NPC. Each NPC's composite brief = group prose + its own line
  + the other lines + names/one-liners of ALREADY-GENERATED siblings of
  the same line, with an explicit differentiation instruction
  (anti-clone). Name dedup intra-batch + against canon (BRIEF-42
  name-key precedent).
- **I1** -- no model coherence pass in v1; mechanical checks only (name
  dedup, location/faction resolution). Social coherence belongs to the
  downstream link agent's existing coherence pass.
- **One open batch per world PER AGENT** -- an open `npc_batch` and an
  open `link_batch` may coexist; each table enforces its own 409.
- **Scope: intra-region v1** -- a batch is anchored to one region root;
  placement vocabulary = BFS expansion of that root
  (`resolve_roster`-style descent, link_author.py:74-107).

## RECON anchors (main @ 2026-07-21)

Reused machinery:
- Staging pattern: `models/ephemeral.py:168-209` (LinkBatch/LinkBatchRow),
  purge `cockpit/app.py:76-100`, journal `link_author.py:110-114`,
  one-open-409 `routes/link_agent.py:63-76`, preview `link_agent.py:52-59`.
- BFS scope: `link_author.py:74-107` (`resolve_roster`).
- Atomic generator: `entity_author.py:506` (`generate_entity_draft`),
  goals `entity_author.py:770` (`generate_npc_goals`, gains one caller).
- Commit plumbing template: `routes/regions.py:230-303`
  (`_commit_region_npcs`); membership via `extension.faction_id` ->
  `write_membership` inside `_create_entity_core`
  (`crud/entities.py:540-583`); goals via `write_npc_goal`.
- Composite-brief pattern: `region_author.py:262-282`
  (`_compose_npc_brief`) -- adapted, not reused verbatim (peers become
  spec lines + generated siblings, not manifest one-liners).

Retirement list (brief d):
- `region_author.py`: MIN_NPCS_PER_FACTION / MIN_FACTIONLESS (43-44),
  `_load_manifest_topup_template` (61), `_normalize_npc_placement` (161),
  npcs handling in `_normalize_manifest` (198-211), `_compose_npc_brief`
  (262), `_npc_deficits` (287), `_topup_blocks` (305), `_run_npc_topup`
  (321) + its call site (442), `_draft_one_npc` (504), `_draft_npcs`
  (576), `npcs_in` in `generate_region_draft` (624).
- `routes/regions.py`: `_commit_region_npcs` (230-303) and its call;
  `write_npc_goal` import if it becomes unused there.
- `index.html`: `regionManifestAddNpc` (6009), the manifest PNJ section,
  NPC nodes in the review tree, NPC-related client state.
- `prompt_registry.py:197`: `region_manifest_topup` entry retired;
  `pt-region-manifest` seed rewritten without the npcs section and
  without floor text; `pt-region-manifest-topup` seed removed.
- `npc_goal_generation` SURVIVES (single-NPC pre-fill and backfill remain
  readers; the region G1 call site is replaced by the new agent's).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `npc_batch`/`npc_batch_row` live in the ephemeral stratum and appear
      nowhere in `canon_write_policy.txt` -> verify/checks/npc_agent_strata.py
      (guarantee 1: policy-file + writes/ module exclusion)
- [ ] The new commit route's entity/membership/goal writes ride only
      already-sanctioned sites -- no unattributed or undeclared canon write
      site exists -> verify/checks/single_canon_write.py
- [ ] Startup purge covers `npc_batch` with last-2 retention (shared or
      sibling of `purge_closed_link_batches`) -> verify/checks/npc_batch_purge.py
- [ ] `region_author.py` contains zero references to npcs, MIN_NPCS_PER_FACTION,
      MIN_FACTIONLESS, topup after brief d -> verify/checks/region_npc_retirement.py
      (fail-closed: missing file or zero criteria parsed = failure)
- [ ] `region_manifest_topup` absent from PROMPT_REGISTRY; every remaining
      registry entry still resolves its call sites -> verify/checks/prompt_registry.py
- [ ] Exact-count invariant: batch run produces exactly sum(count) staged
      rows OR per-line failure notes -- never a silent shortfall
      -> verify/checks/npc_batch_count_contract.py (static: loop-per-count
      structure present, no floor/top-up constructs in npc group author)
- [ ] Module budgets hold (R5: 1000 lines / 40 functions) for the new
      author module and touched route modules -> verify/checks/module_budget.py
- [ ] R1 80-line ceiling holds on all new functions -> verify/checks/function_length.py
- [ ] The shared retention purge (`_purge_closed_batches`) deletes each
      purged batch's row-children BEFORE the batch, under real SQLite FK
      enforcement, for BOTH agents (link + npc), with >2 closed batches
      present -- app boots clean, no `IntegrityError`
      -> verify/checks/purge_fk_ordering.py (runtime, real FK-enforcing
      temp DB; fails against the pre-fix helper body)

### Live  ->  human gate (Nia)
- [ ] Create a batch "5 gardes (faction pinned, location pinned) + 2
      marchands (location pinned, no faction) + 1 line unanchored" on a
      region root: exactly 8 NPCs staged, siblings of the 5-line are
      differentiated (no clones), unanchored line placed only inside the
      BFS-expanded region
- [ ] Reject 1 row, edit 1 row, commit: exactly 7 NPCs in canon, each
      with membership (where pinned/resolved) and goals, all in one
      transaction; rejected row writes nothing
- [ ] Region wizard generates factions + locations only; manifest screen
      shows no PNJ section; commit writes no character rows
- [ ] J1 handoff: post-commit button opens a prefilled link batch on the
      region's root; roster includes pre-existing residents; F1 skips
      canon pairs
- [ ] Restart app twice after closing 3+ batches: only last 2 retained,
      journal files intact
- [ ] Deployment sequence executed (danger_class migration): backup ->
      migration (schema vX.YY) -> seed (pt-region-manifest rewrite,
      topup template removal) -> verify suite green

## Brief plan

- **BRIEF-0037-a-npc-batch-staging-schema** -- schema vX.YY: `npc_batch`
  (world_id, status open|committed|abandoned, scope {root_location_id,
  expanded_location_ids, lines, group_brief}, counts, timestamps) +
  `npc_batch_row` (batch_id, line_index, kind draft|failed, payload = full
  draft incl. goals block, row_status proposed|edited|rejected|committed);
  purge extension; journal dir; routes: preview (vocabulary + count
  summary, read-only), create (409 if open), list, get, abandon.
- **BRIEF-0037-b-npc-group-generation-run** -- `npc_group_author.py`:
  per-NPC generation loop (H1), composite brief composer, anti-clone
  sibling injection, name dedup (intra-batch + canon), unanchored
  placement resolution (C1/S1), goals attach per draft (F), run-next
  route + row patch (patch_row precedent, link_author.py:451).
- **BRIEF-0037-c-commit-and-handoff** -- commit_batch: accepted rows ->
  `_create_entity_core` (+membership) + `write_npc_goal`, single
  transaction, server-authoritative re-validation of client state;
  frontend surface (line editor, run progress, review rows, commit);
  J1 prefilled handoff button to the link agent.
- **BRIEF-0037-d-region-npc-retirement** -- A1 retirement list above,
  `pt-region-manifest` rewrite, registry cleanup, frontend region
  cleanup, retirement verify check. Ordered LAST so the wizard stays
  functional until the agent passes its live gate.

## Deferrals (named)

- **D-0037-1 (cross-region groups)**: multi-root or world-wide batches
  (e.g. a spy network spread over three regions). Trigger: first real
  need for a group whose placement vocabulary exceeds one region root.
- **D-0037-2 (H2 mini-manifest checkpoint)**: a names+one-liners
  checkpoint before full drafts (BRIEF-38 quality lever). Trigger: H1
  direct-to-draft quality judged insufficient at live gate.

## Docs to update

- `world-engine-schema.md` + changelog (vX.YY, brief a)
- `ARCHITECTURE_DECISIONS.md` (one entry per brief) + `DECISIONS_INDEX.md`
- `CLAUDE.md` only if a standing law changes (retirement of the region
  NPC floor doctrine reference, if present)
- `canon_write_policy.txt` (brief c ALLOWED_SITES)
