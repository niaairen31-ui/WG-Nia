# RECON-0036 — NPC link agent (batch relation/knowledge authoring)

Report-only. Live main-branch tarball fetched 2026-07-20 via
codeload.github.com/niaairen31-ui/WG-Nia. Schema header: v1.81
(world-engine-schema.md:3). No actions taken.

Scope: ground the locked design (A1-npc-tab, B1-multi-lieux-exhaustif,
C1-llama-template, D1+D2+D3, E1-tout-le-graphe, F1, R1+journal, W-ok,
G-ok, S1) in real file:line anchors before ticket/brief authoring.

-----

## 1. Canon-write path for the commit step — exists, unchanged

- writes/relations.py:113 `write_relation` -- mode="set" is the author-CRUD
  shape: creates a new edge with clamp(value) intensity, or updates in
  place with prior state appended to change_history first. This is the
  commit target for staged relation rows AND for one-click coherence
  patches on canon relations (W decision).
- writes/knowledge.py:148 `write_knowledge` -- mode="update" is the
  creator-CRUD/new_knowledge shape; commit target for staged knowledge
  rows. Full field coverage: is_incorrect, is_secret, share_threshold
  (D2 needs all three).
- Both are listed in tooling/verify/canon_write_policy.txt [ALLOWED_SITES]
  (relations line, knowledge line). The link agent adds ZERO new canon
  write sites -- commit and patch both route through these two helpers.
  This is the central structural claim of the whole ticket.
- Pair lookup precedent for F1: writes/relations.py:36
  `_find_relation_pair` searches both directions for an existing
  (a, b) pair. The pair-exclusion filter (F1) must reuse this exact
  both-directions semantic, applied per relation-existence (any type),
  at enumeration time in code -- before any model call.

## 2. Authoring LLM call pattern — copy entity_author.py

- entity_author.py:39 `AUTHOR_MODEL = "llama3.1:8b"`.
- entity_author.py:414-419: `chat(messages, model=effective_model(
  template, AUTHOR_MODEL), format="json")` then
  `llm_parse.extract_object(raw)`. This is the sanctioned shape: R2
  chokepoint respected, template override respected.
- llm_parse.py exposes extract_object (:44) and extract_array (:81) with
  LlmParseError (:21). The pair pass returns an array of proposals; the
  "no links" verdict must be an explicit parsed value (e.g. an object
  with links: [] plus a verdict field), never an empty/failed parse --
  parse failure raises, verdict does not.

## 3. Prompt registry — two new authoring keys

- prompt_registry.py:55 PromptSpec (surface, world_scoped,
  dry_run_capable, call_sites, default_model); :63 PROMPT_REGISTRY.
  Existing authoring keys (entity_generation, region_manifest, ...) use
  default_model=_author_model (:49).
- New keys: `npc_link_pair` and `npc_link_coherence`, surface=
  "authoring", default_model=_author_model, call_sites pointing at the
  new orchestrator module. Editable in the prompts UI like all others
  (C1 requirement) -- no UI work needed beyond registration, the prompts
  tab is registry-driven.
- Verify checks prompt_registry.py / prompt_model_write.py /
  prompt_version.py / prompt_lean.py exist in tooling/verify/checks/ and
  will pick the new keys up; briefs must state the registration so the
  checks pass, not get exempted.

## 4. UI surface — the NPC relation graph panel already exists

- index.html:1267-1281: `#creation-npc-relgraph` panel (ego mode
  BRIEF-0023-b, global mode BRIEF-0033-e), with mode toggle, "Lier"
  link-mode button, intensity bucket filters. This panel is the A1 home:
  the agent launcher + batch review attach here, NOT a new creation tab
  -- page_contract.py (CREATION_TABS registry) is expected untouched;
  exec must verify.
- Global graph endpoint: cockpit/crud/relations.py:262
  `get_global_relation_graph` -- structural exclusion of
  `_RELATION_GRAPH_EXCLUDED_TYPES` (connects_to, controls) in the WHERE
  clause, never post-filtered. The coherence pass's canon-graph read
  (E1-tout-le-graphe) MUST reuse this exclusion pattern -- ideally the
  same helper -- so the agent is structurally blind to topology/control
  edges, same as every other character-keyed reader.
- cockpit/crud/relations.py is 295 lines -- room under the module budget,
  but new agent endpoints belong in a new domain module anyway (R6):
  routes/creator.py is at 688 lines and must not become a catch-all.

## 5. Ephemeral stratum — the staging tables' home

- models/ephemeral.py:1-9 docstring: ephemeral tables carry no
  canon_write_policy.txt entries by construction; session/scene
  bookkeeping, not durable canon. `link_batch` + `link_batch_row` join
  this stratum (alongside a schema-doc section flagging them ephemeral,
  as gathering/pass_play are). Purge of closed batches (keep last 2) is
  therefore legal by construction -- "history is sacred" governs canon;
  the append-only generation journal carries long memory instead.
- New tables => schema version bump + migration => danger_class
  migration => explicit deployment sequence (backup -> migration ->
  seed -> verify) in the schema brief's Done means.

## 6. Journal path convention

- db.py:28 `DEFAULT_DB_PATH = Path.home() / ".world_engine" /
  "world_engine.db"`. Journal follows the same convention:
  `~/.world_engine/link_agent_journal/` (absolute home path, outside the
  git tree by construction -- .gitignore needs no entry; the existing
  .gitignore only guards *.db patterns and the June-19 incident note
  confirms the out-of-tree doctrine). Brief locks the path as absolute,
  never repo-relative.

## 7. Location subtree expansion (S1) — does not exist yet

- parent_location_id read sites are CRUD/display only
  (cockpit/crud/locations.py:277, entities.py, routes/regions.py,
  writes/worlds.py, models/canon.py). No recursive descent helper
  anywhere in src/. S1 needs a new roster resolver: BFS over
  parent_location_id from the selected root set, then characters where
  current_location_id is in the expanded set, character_type='npc',
  vital_status='alive', entity.status='active'. Code-owned, deterministic,
  pair count surfaced to the UI before launch.

## 8. Knowledge subject convention (D3) — new, no precedent

- No `npc:{id}`-style subject exists anywhere in src/ (grep confirms).
  context.py reads subjects as opaque strings (:112, :581). Convention
  `npc:{entity_id}` is therefore new and non-breaking; the code stamps
  the subject at staging time from the pair context -- the model NEVER
  emits the subject field. A verify check should enforce the stamp
  (fail-closed: a staged knowledge row whose subject was not
  code-derived fails).

## 9. Duplicate-guard precedent for F1

- Changelog (v1.5-era entry, world-engine-schema-changelog.md tail):
  `_apply_mutation` duplicate guard matches new_knowledge on
  entity_id+subject and relation_change on unordered pair+type. F1 pair
  exclusion at enumeration time is the batch-side mirror of the same
  idea; the commit step additionally re-checks (a staged row whose pair
  gained a canon relation between generation and commit is surfaced,
  not silently double-written).

## 10. Verify toolchain touchpoints

- tooling/verify/checks/ has 36 checks incl. relation_graph.py,
  llm_parse_chokepoint.py, single_canon_write.py, module_budget.py,
  function_length.py, prompt_* family, page_contract.py. New checks
  expected from this ticket: staging-strata guard (link_batch* absent
  from canon policy AND absent from any writes/ module), D3 subject
  stamp, fail-closed patch validation (a rendered one-click button
  implies a pre-validated patch). Exact check names owned by briefs.

-----

## Risks / flags for ticket

- R-1: coherence pass reads staged + full canon character graph; on a
  large world the prompt may exceed the author model's context. Brief
  must define a deterministic serialization budget (code-owned
  truncation with explicit "graph truncated" marker in the journal),
  fail-closed: a truncated coherence pass is labeled partial, never
  silently complete.
- R-2: one-click canon patches (W) are creator-direct-authority writes
  triggered from agent output. The pre-validation gate (parse ->
  validate -> only then render button) is the whole safety story; the
  brief must make the invalid-patch path a first-class rendered state
  ("patch rejected: reason"), not a silent drop.
- R-3: exhaustive pairs (B1) at 30+ NPCs = 435+ calls. Confirmed
  acceptable by Nia; UI confirmation with pair count is locked (S1).
  Journal makes reruns auditable.
- R-4: character.secrets (creator meta-narrative) must NOT enter the
  pair context (structural exclusion at context assembly -- same rule
  as every assembler; models/canon.py character docstring). Existing
  knowledge rows with is_secret=TRUE MAY enter (creator-tool surface,
  Nia's earlier decision) but the brief must name this inclusion
  explicitly as a creator-surface exception.
