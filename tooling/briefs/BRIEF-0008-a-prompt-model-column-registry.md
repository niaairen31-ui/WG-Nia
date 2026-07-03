<!-- slug: prompt-model-column-registry -->
# BRIEF-0008-a — `prompt_template.model` column, `effective_model` resolver, prompt registry

Ticket: TICKET-0008. Companion: RECON-0008 spec + **result** (authoritative
citation set — where the two diverge, the result wins). Execution: Claude
Code. All design decisions below are locked; nothing here is open.

## Context

The cockpit gains a read-only prompt-management tab (BRIEF-0008-b). Before
the reader exists, this brief lays the plumbing whose truth the tab will
display: a nullable `model` override column on `prompt_template` (A2-a2), a
single `effective_model` resolver consulted by every templated model call,
and a code registry (`prompt_registry.py`) declaring per-usage code facts
(surface, default model, resolution semantics, call sites, dry-run
capability). Runtime behavior after this brief is **bit-identical** to
before it: the column is born NULL everywhere and no write path exists.

Locked decisions this brief implements: A2-a2 (nullable authoritative
column, resolver as day-one reader), A2-b (no structural model locks — the
former `region_manifest_topup` "never the game model" hard requirement
downgrades to a default; record this in ARCHITECTURE_DECISIONS.md), A2-c
(DB owns text + override, code owns wiring), B1 (static call sites in the
registry), R1 (`world_scoped` flag encodes each usage's real resolution
semantics — RECON result F1 correction: the 6 authoring loaders are
world-agnostic `.first()`, only the 9 cockpit/gathering loaders + the
analyzer loader do world-preferred-else-global).

## Scope IN

1. **Schema — `prompt_template.model`.** `Optional[str]` SQLModel field,
   `TEXT NULL`, no default value semantics beyond NULL (`models.py`,
   `PromptTemplate`, beside `destination` at models.py:790). Additive
   migration; seed untouched. Schema version bump `vX.YY` (Claude Code
   assigns; current is v1.66 per RECON result F9).

2. **Resolver.** In the new `src/world_engine/prompt_registry.py`:
   `def effective_model(template: PromptTemplate | None, default: str) ->
   str: return template.model if (template is not None and template.model)
   else default`. Pure, no DB access, no import of cockpit modules.

3. **Wire the resolver at every templated model call**, passing the call
   site's current default unchanged:
   - `entity_author.py:411,536,625,713` → `model=effective_model(template,
     AUTHOR_MODEL)`
   - `region_author.py:337,413` → same with the loaded manifest/topup
     template
   - `analyzer.py` both `chat()` calls (:472, :749 region) → default = the
     existing `model` parameter value
   - `gathering.py:95` → default = current binding
   - All `cockpit/app.py` chat/chat_stream calls whose messages are built
     from a loaded `PromptTemplate` (the sites enumerated in RECON F2,
     including the inline `app.py:1747`) → default = the local `model`
     binding they use today.
   - **Exemption, by construction:** the call path whose model comes from
     `injected.get("model", DEFAULT_MODEL)` (app.py:2606) is NOT wired
     through the resolver. Wiring it would silently encode a
     `template.model` vs `injected_context["model"]` precedence — a
     decision explicitly deferred to the write-path chantier. The exemption
     is listed by function name in the verify check's allowlist with a
     comment naming the deferral.

4. **`prompt_registry.py` — `PROMPT_REGISTRY: dict[str, PromptSpec]`**, one
   entry per seeded usage (17: `npc_dialogue`, `npc_initiative_act`,
   `player_narration`, `mj_interpretation`, `mj_arbitration`,
   `mj_establishment`, `mj_gathering`, `mj_speaker_selection`,
   `mj_initiative`, `conversation_analysis`, `overhearing_classification`,
   `entity_generation`, `world_generation`, `player_generation`,
   `skill_catalogue`, `region_manifest`, `region_manifest_topup`). Fields:
   - `surface`: `"play" | "authoring"`
   - `default_model`: resolved at read time from the same symbols the call
     sites use (`ollama_client.DEFAULT_MODEL` / `entity_author.AUTHOR_MODEL`)
     — never a copied string literal, so an env override of
     `WORLD_ENGINE_OLLAMA_MODEL` shows through
   - `world_scoped`: bool (R1). `True` for the 9 cockpit/gathering usages +
     `conversation_analysis`/`overhearing_classification` (analyzer's
     generic loader is world-preferred); `False` for the 6 authoring usages
     (`entity_generation`, `world_generation`, `player_generation`,
     `skill_catalogue`, `region_manifest`, `region_manifest_topup`) — match
     the actual loader bodies per RECON result F1, do not idealize
   - `dry_run_capable`: `True` only for `npc_dialogue` and
     `player_narration` (C3)
   - `call_sites`: list of `"path:function"` strings (B1), sourced from the
     RECON result's verified citations
   Plain module-level dict + a small frozen dataclass; no DB access at
   import time.

5. **Verify check `tooling/verify/checks/prompt_registry.py`** (G1,
   exit 0/1, one line per failure, same conventions as `page_contract.py`):
   - Bijection: usages parsed statically from `scripts/seed_pilot.py`
     (`usage="..."` occurrences) == `PROMPT_REGISTRY` keys, both directions
   - Every registry entry has all five fields; `call_sites` non-empty;
     each `path` exists and `def <function>` is present in that file
   - Static wiring scan: in the files listed above, every
     `ollama_client.chat(`/`chat(`/`chat_stream(` call carrying a `model=`
     argument uses `model=effective_model(` — except functions on the
     explicit exemption allowlist (the injected-context path)
   - Resolver default behavior: `effective_model(None, d) == d` and a
     stub template with `model=None` returns `d` (pure-function assertion,
     no DB)

## Scope OUT (named)

- Write/edit path for `model` (Ollama `/api/tags` live list; precedence
  `template.model` vs `injected_context["model"]`; re-recording the
  downgraded top-up requirement becomes ACTIVE at that point — this brief
  only *records* the downgrade)
- A2-a3 (NOT NULL authoritative column)
- Category-level model defaults ("all NPC", "PC creation"…)
- Runtime invocation journal (B2)
- Loader consolidation (F1) / `render_prompt` chokepoint refactor
- `ORDER BY` determinism fix for the authoring loaders' `.first()`
  (observation recorded, no code change)
- `destination` column fate (subsumption by `model`, reactivation as
  routing discriminant, or removal — write-path chantier). The column is
  untouched here.
- Everything in BRIEF-0008-b (tab, API, previews)

## Invariants to defend

- **Bit-identical runtime.** With `model` NULL on every row (guaranteed:
  no write path, seed untouched), every call site resolves to exactly the
  model it used before this brief. No behavior change of any kind.
- **Two sanctioned canon-write paths only; this brief adds zero writes.**
  No `_apply_mutation`, no `change_history`, no seed change.
- **Model proposes, code judges** — untouched; this brief never touches
  prompt *content* or parsing.
- **Structural over disciplinary:** registry↔DB coherence is enforced by
  the verify check (mechanical bijection), not by convention; the
  precedence deferral is enforced by an explicit allowlist, not by memory.
- **No structure without a reader:** every registry field has its reader —
  `default_model`/`world_scoped`/`dry_run_capable`/`call_sites` are
  consumed by BRIEF-0008-b's API in the same ticket; `model` is consumed
  by the resolver now.

## Done-means checklist

- [ ] `python tooling/verify/run.py` passes, including the new
      `prompt_registry` check
- [ ] Existing checks (`page_contract`, `pipeline_state`, canon-write
      policy baseline) unchanged and passing
- [ ] Grep gate: no remaining `model=AUTHOR_MODEL` or
      `model=ollama_client.DEFAULT_MODEL`/`model=DEFAULT_MODEL` at a
      templated chat call outside the exemption allowlist
- [ ] Live smoke (Nia): one play turn (`/say` dialogue) and one entity
      generation run behave exactly as before; Ollama logs show the same
      models as pre-brief
- [ ] Schema version header bumped once (`world-engine-schema.md:3`),
      changelog entry appended

## Docs to update

- `world-engine-schema.md`: `prompt_template` section — add `model` column
  with the A2-a2 NULL-semantics note; **fix the stale `usage` enum
  comment** (8 missing values incl. `region_manifest_topup`, per RECON
  result F3); bump the version header. Changelog entry in
  `world-engine-schema-changelog.md`.
- `ARCHITECTURE_DECISIONS.md` (append-only): record A2-a2/A2-b/A2-c/R1,
  the top-up hard-requirement downgrade, and the named precedence deferral.
- `CLAUDE.md`: one line — "all templated model calls resolve through
  `prompt_registry.effective_model`; new prompt usages must add a registry
  entry (verify-enforced)."
