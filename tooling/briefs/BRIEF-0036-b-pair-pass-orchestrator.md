# BRIEF — Step "Link-agent pair pass" (BRIEF-0036-b)

Ticket: TICKET-0036. Anchored on RECON-0036. Requires 0036-a landed.

## Context

Staging exists (0036-a). This step makes the agent generate: for each
NPC pair in the batch scope, one LLM call proposes relations and
knowledge, validated and clamped by code, written to link_batch_row.
Coverage is decided entirely by code; the model may return an explicit
"no links" verdict. Everything is journaled.

## Pre-exec verification (report, then proceed or stop)

- entity_author.py:414-419 call shape (chat + format="json" +
  llm_parse.extract_object) and :39 AUTHOR_MODEL unchanged.
- prompt_registry.py PromptSpec fields unchanged (RECON-0036 s.3).
- writes/relations.py:36 _find_relation_pair still both-directions.
- 0036-a landed: LinkBatch models + link_author.py + journal helper
  present on live main.
If any anchor fails: STOP, report, no code.

## Scope IN

1. Prompt registration: add to PROMPT_REGISTRY key "npc_link_pair",
   surface="authoring", world_scoped=True, dry_run_capable=False,
   call_sites=("src/world_engine/link_author.py:_load_pair_template",),
   default_model=_author_model. Seed default template (prompt_store
   mechanism, same as other authoring prompts) with this initial text
   verbatim (editable later in the prompts UI):

   "You are the world-building assistant for the world {world_name}.
   Two NPCs may or may not know each other. Propose the links between
   them, or none.

   NPC A: {a_sheet}
   NPC B: {b_sheet}
   Shared context: {shared_context}

   Reply ONLY with JSON:
   {\"verdict\": \"links\" or \"no_links\", \"links\": [ ... ]}
   Each link is one of:
   {\"kind\":\"relation\",\"type\":<one of: ally, enemy, debt, fear,
   fascination, shared_secret, instrumentalizes, interest, indifference,
   rejection, passive_attention, other>,\"direction\":\"mutual\"|
   \"a_to_b\"|\"b_to_a\",\"intensity\":1-100,\"visible_to_b\":true|false,
   \"notes\":\"...\"}
   {\"kind\":\"knowledge\",\"holder\":\"a\"|\"b\",\"level\":<unaware,
   rumor, suspicious, partial, knows, fully_understands>,\"content\":
   \"what the holder knows about the other\",\"source\":\"how they
   learned it\",\"is_incorrect\":true|false,\"is_secret\":true|false,
   \"share_threshold\":1-100}
   Prefer asymmetry and imperfection where the sheets justify it: a
   relation one side hides (visible_to_b false), a wrong belief
   (is_incorrect), a guarded secret (is_secret). If nothing plausibly
   connects them, verdict no_links with an empty links array."

2. Context assembly in link_author.py, function build_pair_context(db,
   a_id, b_id) -> dict, code-owned:
   - Per NPC: entity.name/description, character.appearance, backstory,
     aversion, vital_status; active faction memberships (roles included);
     current location name + its parent chain names.
   - Shared context: same-location flag, shared factions, existing
     knowledge rows each holds ABOUT third parties is EXCLUDED (pair
     scope only); existing knowledge with is_secret=TRUE about the OTHER
     member of the pair is INCLUDED (creator-surface exception, named:
     RECON-0036 R-4).
   - STRUCTURAL EXCLUSION, add this comment verbatim at the top of the
     function: "# character.secrets (creator meta-narrative) is NEVER
     read here -- same exclusion as every context assembler. Only
     knowledge rows may enter, including is_secret=TRUE rows: this is a
     CREATOR-SURFACE exception, valid solely because the link agent's
     output is reviewed by the creator before commit."

3. Pair enumeration + F1, function enumerate_pairs(db, batch) ->
   list[tuple[a_id, b_id]]: all unordered pairs from scope.npc_ids in
   deterministic order (sorted ids), MINUS pairs where a relation row
   already exists in either direction (reuse _find_relation_pair's
   both-directions semantics via a single query over the id set -- do
   not call it N^2 times). Excluded pairs are journaled
   (event=pair_skipped_existing) but consume no LLM call.

4. Endpoint POST /api/link-batches/{id}/run-next (routes/link_agent.py):
   processes exactly ONE pending pair then returns {pairs_done,
   pairs_total, last_pair:{a,b,verdict,row_count}}. Pending = enumerated
   pairs minus pairs already having rows or a no_links row in this
   batch, recomputed each call -- this makes resume-after-restart free.
   Returns {done:true} when nothing is pending. Refuses on non-open
   batch. The frontend loop (0036-d) drives repetition; no server-side
   loop.

5. Pair processing, function run_pair(db, batch, a_id, b_id):
   - journal event=pair_call with the fully rendered prompt.
   - chat(messages, model=effective_model(template, AUTHOR_MODEL),
     format="json"); parse via llm_parse.extract_object ONLY.
   - verdict validation: "no_links" -> one link_batch_row kind='no_links'
     payload '{}'. Parse failure or missing verdict -> journal
     event=pair_parse_error, write NO row, re-raise as a 502 with the
     pair identified; the pair stays pending (retry = call run-next
     again). A silence is never a verdict.
   - link validation, code-owned clamps: relation type in the closed
     vocab above (connects_to/controls structurally impossible: not in
     vocab AND assert-rejected), intensity/share_threshold clamped 1-100,
     level in vocab, direction in vocab; holder in (a,b). Invalid link
     items are dropped INDIVIDUALLY and journaled
     (event=link_item_rejected, reason); valid ones proceed.
   - Row writing: relation payload stores the full write_relation
     mode="set" argument set with real entity ids resolved from pair
     order; knowledge payload stores the full write_knowledge
     mode="update" argument set with entity_id = holder's id and
     subject = "npc:" + other id -- CODE-STAMPED (D3), the model never
     emits ids or subjects.
   - journal event=pair_result with raw response + kept/dropped counts;
     increment pairs_done.

6. Extend link_agent_strata.py check: FAIL if any staged knowledge
   payload path can bypass the subject stamp -- statically, assert the
   only construction site of knowledge payloads is the stamped one
   (single function, AST check on link_author.py). Keep fail-closed and
   vacuous-proof.

## Scope OUT

- Coherence pass, findings, patches, commit (0036-c).
- Frontend launcher/loop/review (0036-d) -- run-next is testable by curl.
- Relation-evolution proposals on existing pairs (named deferral).
- Parallel pair calls, batching several pairs per call, retry budgets:
  one pair per call, retries are manual re-invocations.
- No new knowledge levels, relation types, or schema columns.
- No prompt-content iteration beyond the seeded default: wording tuning
  happens in the prompts UI, not in code.

## Invariants to defend

- Single llm_parse chokepoint (R2) -- run_pair parses nothing itself.
- Model proposes, code judges: enumeration, ids, subjects, clamps, and
  vocab are code-owned; the check in item 6 makes the subject stamp
  structural.
- Secrets structurally excluded: character.secrets never in context
  (verbatim comment, item 2).
- Module budget: link_author.py stays under 1000/40; extract a
  link_context.py sibling if context assembly pushes it over (R7
  domain-prefixed).

## Done means

- [ ] Batch of >=3 NPCs incl. one existing canon relation between two of
      them: enumerate excludes that pair (journal shows
      pair_skipped_existing), run-next loop completes the rest.
- [ ] At least one pair yields kind='no_links' rendered in GET batch.
- [ ] Staged knowledge rows all carry subject npc:{other_id}; staged
      relation payloads carry real entity ids in pair order.
- [ ] Forced malformed model output (temporary template edit in the UI)
      -> 502, journal pair_parse_error, no row written, pair still
      pending; reverting the template and re-running succeeds.
- [ ] Journal contains pair_call/pair_result lines with full prompt and
      raw response for every processed pair.
- [ ] npc_link_pair visible and editable in the prompts UI; prompt_*
      verify checks green.
- [ ] Full verify suite green; /review-step and /close-step run.

## Docs to update

- ARCHITECTURE_DECISIONS.md: append to the 0036 record -- pair-pass
  contract (code-owned coverage, explicit no_links verdict, per-item
  drop policy, creator-surface is_secret inclusion).
- CLAUDE.md pointers if new sibling module extracted.
- No schema change expected; if the executor believes one is needed,
  STOP and report instead.
