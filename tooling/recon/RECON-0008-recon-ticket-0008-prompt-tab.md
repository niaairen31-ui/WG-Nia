<!-- slug: recon-ticket-0008-prompt-tab -->
# RECON-0008 — TICKET-0008: Prompt management tab (read-only)

**Mode:** report-only. No actions taken. All citations against commit `4fad31ddb7895b4a59e14fb7a890fc65cd4e3b45` (2026-07-03, main).

**Locked design (chat):** A2-a2 (nullable `model` column, authoritative-by-resolution, write path deferred), B1 (static call sites via code registry), C3 (hybrid preview: raw default, assembled dry-run where an assembler already exists), D1 (lazy master list + one-detail-at-a-time), E1 (standard shell header, post-0005-c). Creator holds full model authority — no structural model locks (former top-up "hard requirement" downgrades to a default; must be re-recorded in ARCHITECTURE_DECISIONS.md when the write path ships). Scope: `prompt_template` rows only; Python-built context blocks visible only *through* assembled previews.

---

## F1 — Template loading is 16 near-identical copy-pasted loaders

Every call site loads its template through a private loader duplicating the same
"active, world-specific preferred, else global" query:

- `entity_author.py:94` `_load_template` (usage `entity_generation`, query at :97)
- `entity_author.py:103` `_load_world_template` (`world_generation`, :106)
- `entity_author.py:112` `_load_player_template` (`player_generation`, :115)
- `entity_author.py:121` `_load_skill_catalogue_template` (`skill_catalogue`, :124)
- `region_author.py:50` `_load_manifest_template` (`region_manifest`, :53)
- `region_author.py:59` `_load_manifest_topup_template` (`region_manifest_topup`, :62)
- `cockpit/app.py:1294` `_load_npc_dialogue_template` (:1298)
- `cockpit/app.py:1512` `_load_mj_speaker_template` (:1516)
- `cockpit/app.py:1610` `_load_mj_initiative_template` (:1614)
- `cockpit/app.py:1627` `_load_npc_initiative_act_template` (:1631)
- `cockpit/app.py:1644` `_load_mj_arbiter_template` (:1648)
- `cockpit/app.py:1661` `_load_mj_establishment_template` (:1665)
- `cockpit/app.py:1920` `_load_mj_narration_template` (:1924)
- `cockpit/app.py:1962` `_load_mj_interpret_template` (:1966)
- `gathering.py:39` `_load_gathering_template` (`mj_gathering`, :43)
- `analyzer.py:138` `load_analysis_prompt` — the one *generic* loader (`usage` param; used at :460 for `overhearing_classification` and for `conversation_analysis`)

**Implication for A2-a2:** the resolver does not require consolidating these
loaders. A single helper (e.g. `effective_model(template, default)`) applied at
each `chat`/`chat_stream` call is the minimal mechanical change. Loader
consolidation is a separate, optional chantier — out of scope unless Nia pulls
it in.

## F2 — Model binding today: two constants, one pre-existing override channel

- Play/game default: `DEFAULT_MODEL`, env-overridable
  (`ollama_client.py:22-23`, `WORLD_ENGINE_OLLAMA_MODEL`).
- Authoring: `AUTHOR_MODEL = "llama3.1:8b"` (`entity_author.py:37`), imported by
  `region_author.py:35`; used at `entity_author.py:411,536,625,713` and
  `region_author.py:337,413`.
- Cockpit play call sites bind a local `model` from `DEFAULT_MODEL`
  (`app.py:2463,3902,3938`) — **except** `app.py:2606`:
  `model = injected.get("model", ollama_client.DEFAULT_MODEL)` — the
  conversation's `injected_context` snapshot already carries an optional
  per-conversation model override. **Open precedence question for the deferred
  write path:** `template.model` vs `injected_context["model"]`. Must be named
  in Scope OUT, not silently resolved.
- One call site hardcodes the default inline: `app.py:1747`
  (`model=ollama_client.DEFAULT_MODEL`).

## F3 — 18 seeded usages; schema-doc enum is stale

`scripts/seed_pilot.py` seeds 18 usages (lines 1185–1508): `npc_dialogue`,
`npc_initiative_act`, `player_narration`, `mj_interpretation`,
`mj_arbitration`, `mj_establishment`, `mj_gathering`, `mj_speaker_selection`,
`mj_initiative`, `conversation_analysis`, `overhearing_classification`,
`entity_generation`, `world_generation`, `player_generation`,
`skill_catalogue`, `region_manifest`, `region_manifest_topup` (+1 comment-only
block at :346/:377 duplicating listed usages). The `usage` enum comment in
`world-engine-schema.md` (`prompt_template` section) lists only ~13 values and
is missing at least `mj_gathering`, `mj_speaker_selection`, `mj_initiative`,
`npc_initiative_act`, `world_generation`, `player_generation`,
`skill_catalogue`. → Docs-to-update item in the brief.

## F4 — `destination` column has zero code consumers

No Python file reads `PromptTemplate.destination` (all `destination` hits in
`app.py` are travel-related). Pre-existing structure-without-reader; the new
tab may display it as inert metadata or omit it. Observation only, no action.

## F5 — Cockpit shell insertion point (post-0005-c, confirmed merged)

- Tab registry: `CREATION_TABS` (`cockpit/index.html:3009`), 10 entries, each
  with `label / archetype / containers / loader / state / createPanel /
  primaryAction / slots`.
- Read-only precedent exists: `artefacts` (`index.html:3091`,
  `primaryAction: null`) and `queue` (`:3107`, "append-only by design"). The
  prompts tab follows the same shape: `primaryAction: null` until the write
  path ships.
- **Verify-check coupling:** `tooling/verify/checks/page_contract.py:12-15`
  hardcodes `TAB_KEYS` (10 keys). Adding a `prompts` tab requires appending the
  key there, and the new entry must satisfy the contract the check enforces.

## F6 — API surface is greenfield

No `/api/prompt*` route exists in `cockpit/app.py` or `cockpit/crud.py`.
Proposed (per D1): `GET /api/prompts` (master list: id, name, usage, surface,
version, is_active, effective model, world_id) + `GET /api/prompts/{id}`
(detail: system_prompt, user_template, variables, notes, call sites from
registry, preview affordances). Both read-only end to end — no
`_apply_mutation`, no `change_history`.

## F7 — Multiple rows per usage are legal; the tab must show "effective"

The loader preference chain (world-specific > global, `is_active` filter, e.g.
`app.py:1307-1311`) means a usage can have several rows with one *effective*
template per world. The master list should group by usage and mark the
effective row for the active world; shadowed/inactive rows remain visible but
badged. Effective-model display = `template.model ?? call-site default`
(registry-provided default), never a guess.

## F8 — C3 dry-run capable usages

`assemble_npc_context` and `assemble_mj_context` live in `context.py` and are
pure read paths per ARCHITECTURE_DECISIONS.md (structural exclusions by query
construction). Candidates for assembled preview: `npc_dialogue` (needs an
NPC + interlocutor + location selector) and `player_narration` (needs the
active PC + location). All other usages: raw preview only, `{variables}`
highlighted from the `variables` JSON column. `dry_run_capable` is a registry
flag, per-usage.

## F9 — Schema change required

`prompt_template.model TEXT NULL` (SQLModel field, `server_default` NULL) —
schema version bump `vX.YY` (Claude Code assigns). Seed untouched: column
born NULL everywhere ⇒ runtime bit-identical until a write path exists.
Migration is additive; append-only history unaffected (prompt_template carries
no change_history today — templates are config, same category as
metadata-config per existing doctrine).

---

## Proposed brief split (for Nia's arbitration — one chantier per brief)

- **BRIEF-0008-a:** schema `model` column + `effective_model` resolver applied
  at all 22 chat/chat_stream call sites + `prompt_registry.py` (usage →
  surface, call_sites, default_model, dry_run_capable) + registry↔DB bijection
  verify check.
- **BRIEF-0008-b:** cockpit tab (CREATION_TABS entry, `primaryAction: null`,
  TAB_KEYS update in page_contract.py) + `GET /api/prompts` +
  `GET /api/prompts/{id}` + raw preview + C3 assembled preview for the two
  dry-run usages.

## Scope OUT (named, all briefs)

- Write/edit path for `model` and template text (deferred, targeted — Nia's
  words). Includes: Ollama `/api/tags` live model list, precedence
  `template.model` vs `injected_context["model"]` (F2), re-recording the
  downgraded top-up requirement in ARCHITECTURE_DECISIONS.md.
- A2-a3 (NOT NULL authoritative column).
- Category-level model defaults ("all NPC", "PC creation"…) — `usage` is the
  natural key; resolution `prompt override ?? category default ?? code
  default` when it comes.
- Runtime invocation journal (B2 / `prompt_invocation`).
- Promotion of Python-built context blocks to first-class objects.
- Loader consolidation (F1) / full `render_prompt` chokepoint refactor.
- `destination` column cleanup (F4).