---
id: TICKET-0036
title: NPC link agent — batch relation/knowledge authoring with coherence pass
type: feature
status: recon        # RECON-0036 delivered; briefs next
created: 2026-07-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0036-a, BRIEF-0036-b, BRIEF-0036-c, BRIEF-0036-d]
schema_version_touched: vX.YY   # Claude Code owns the number (V1)
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Je veux faire un test avec un nouveau type d'AI dans mon outil createur.
Pour commencer, celui-ci servira a me generer les liens entre mes NPC. On
lui donne des groupes de NPC, il lie les fiches et cree des liens entre
les NPC's (relations et knowledge sur cette personne). Dans mon outil
createur, je ne suis pas inquiete sur le temps que cela prend et sur le
nombre d'appels necessaires pour finir une tache. Dans mon monde ideal,
il y aurait une passe finale pour s'assurer la coherence de tout ce qui a
ete fait a la fin."

## Clarifications resolved (intake)

- A1-npc-tab -- lives on the existing NPC relation graph panel
  (index.html #creation-npc-relgraph); NOT added to the region wizard
  (G-ok: pre-commit entities lack DB context/FKs; that port is the D2
  deferral, which will reuse this machinery with staged ids).
- B1-multi-lieux-exhaustif -- roster = NPCs in a multi-selected location
  set; S1: selection expands location subtrees via parent_location_id;
  pair coverage is exhaustive N(N-1)/2, decided by CODE, with the pair
  count displayed for confirmation before launch. The model may return
  an explicit "no links" verdict per pair (distinct from parse failure).
- C1-llama-template -- author model llama3.1:8b via two new
  prompt_template registry keys (npc_link_pair, npc_link_coherence),
  editable in the prompts UI like every other template.
- D1+D2+D3 -- asymmetric relations (a_to_b/b_to_a, visible_to_b) and
  imperfect knowledge (is_incorrect, is_secret, share_threshold) are in
  scope from v1; knowledge-about-person subject is code-stamped as
  npc:{entity_id}, never model-emitted.
- E1-tout-le-graphe -- coherence pass reads the staged batch PLUS the
  full canon character relation/knowledge graph (structural exclusion of
  connects_to/controls, same as the relation-graph endpoints). Emits
  mechanical fail-closed findings (code) and narrative flags (model) as
  structured patches; every rendered one-click button is pre-validated
  (W-ok); patches on canon rows route through writes.py
  creator-direct authority with change_history snapshots.
- F1 -- pairs with any existing canon relation are excluded at
  enumeration time (both-directions semantics of _find_relation_pair);
  proposing evolutions on existing relations is a NAMED DEFERRAL
  (trigger: Nia requests rerun-with-evolution after v1 proves out).
- R1+journal -- staging = ephemeral-stratum tables link_batch +
  link_batch_row; open batches persist across restarts; on close, the
  last 2 closed batches are retained, older purged at startup.
  Append-only generation journal (prompts, raw responses, verdicts,
  patch decisions) under ~/.world_engine/link_agent_journal/ --
  absolute home path, outside the git tree by construction, never
  repo-relative.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] link_batch/link_batch_row appear in NO canon_write_policy entry and
      NO writes/ module; commit + patch paths call only write_relation /
      write_knowledge  -> verify/checks/link_agent_strata.py
- [ ] every staged knowledge row targeting a person carries a
      code-stamped subject npc:{entity_id}  -> same check or dedicated
- [ ] both new prompt keys registered with authoring surface and
      call_sites resolving to real functions  -> existing prompt_registry
      check extended
- [ ] coherence patch pipeline is fail-closed: unparseable or
      invalid-target patches are rendered as rejected findings, never as
      actionable buttons; zero machine-checkable criteria parsed = FAIL
- [ ] all LLM parsing routes through llm_parse.py  -> existing
      llm_parse_chokepoint check must stay green
- [ ] module budgets and 80-line ceiling hold on all new modules
      -> existing module_budget / function_length checks

### Live  ->  human gate (Nia)
- [ ] select 2+ locations incl. one with children; displayed roster and
      pair count match expectation; launch; batch completes
- [ ] at least one pair returns an explicit "no links" verdict rendered
      as such (not an error)
- [ ] review a staged batch: edit a row, reject a row, commit; committed
      rows visible in the relation graph and entity sheets
- [ ] coherence pass flags at least one seeded contradiction across
      staged+canon; one-click patch on a CANON relation applies and its
      change_history shows the snapshot
- [ ] close cockpit mid-batch (open), reopen, resume; then verify only
      last 2 closed batches survive a restart
- [ ] journal files exist under ~/.world_engine/link_agent_journal/ and
      contain the full trace of the run; nothing under the repo tree
