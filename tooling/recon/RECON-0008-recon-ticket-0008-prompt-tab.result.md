# RECON-0008 result — Prompt management tab (read-only)

**REPORT ONLY.** No edit, no fix, no design decision made during this pass.
Every claim below is re-cited `path:line` against the living tree on branch
`ticket/0007` (the spec's citations were made against commit `4fad31d`, no
drift since). Mismatches between the spec's claims and what actually exists
are called out explicitly, per the RECON contract.

Ticket: TICKET-0008. Spec: RECON-0008-recon-ticket-0008-prompt-tab.md.

---

## F1 — Template loading (16 loaders): confirmed, with one correction

All 16 `def`/query-line citations check out exactly:
[entity_author.py:94,97](src/world_engine/entity_author.py#L94),
[:103,106](src/world_engine/entity_author.py#L103),
[:112,115](src/world_engine/entity_author.py#L112),
[:121,124](src/world_engine/entity_author.py#L121);
[region_author.py:50,53](src/world_engine/region_author.py#L50),
[:59,62](src/world_engine/region_author.py#L59);
[cockpit/app.py:1294,1298](src/world_engine/cockpit/app.py#L1294),
[:1512,1516](src/world_engine/cockpit/app.py#L1512),
[:1610,1614](src/world_engine/cockpit/app.py#L1610),
[:1627,1631](src/world_engine/cockpit/app.py#L1627),
[:1644,1648](src/world_engine/cockpit/app.py#L1644),
[:1661,1665](src/world_engine/cockpit/app.py#L1661),
[:1920,1924](src/world_engine/cockpit/app.py#L1920),
[:1962,1966](src/world_engine/cockpit/app.py#L1962);
[gathering.py:39,43](src/world_engine/gathering.py#L39);
[analyzer.py:136](src/world_engine/analyzer.py#L136) (the spec cites `:138` for
the `def` — that line is actually the `world_id` parameter; `def
load_analysis_prompt(` itself opens at `:136`. Minor drift, same function).

**Correction — the "world-specific preferred, else global" framing is not
uniform across all 16.** Read in full:

- The 8 `cockpit/app.py` loaders and `gathering.py:39` all share the same
  body shape: fetch all active rows for the usage, then
  `for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is
  None): ...` — e.g. [app.py:1307-1311](src/world_engine/cockpit/app.py#L1307),
  [gathering.py:49-52](src/world_engine/gathering.py#L49). This **is** the
  world-preferred-else-global chain.
- The 4 `entity_author.py` loaders ([:94](src/world_engine/entity_author.py#L94),
  [:103](src/world_engine/entity_author.py#L103),
  [:112](src/world_engine/entity_author.py#L112),
  [:121](src/world_engine/entity_author.py#L121)) and the 2
  `region_author.py` loaders ([:50](src/world_engine/region_author.py#L50),
  [:59](src/world_engine/region_author.py#L59)) take **no `world_id`
  parameter at all** — each is just
  `select(PromptTemplate).where(usage==...).where(is_active==True)` then
  `.first()`. No world scoping, no preference chain. Authoring-side templates
  are read world-agnostic today.

**Why it matters for the brief:** F1's own conclusion ("the resolver does not
require consolidating these loaders... a single `effective_model(template,
default)` helper applied at each call is the minimal change") still holds —
`effective_model` only needs the resolved `PromptTemplate` row, not the
loader's internal logic. But anyone reading F1's "duplicating the same...
query" line at face value would wrongly assume every loader is world-scoped.
If BRIEF-0008-a's `prompt_registry.py` or verify check ever asserts anything
about *how* a usage resolves per-world, it must special-case these 6
loaders.

## F2 — Model binding: confirmed exactly

- [ollama_client.py:22-23](src/world_engine/ollama_client.py#L22) — `DEFAULT_MODEL`.
- [entity_author.py:37](src/world_engine/entity_author.py#L37) — `AUTHOR_MODEL = "llama3.1:8b"`;
  imported at [region_author.py:35](src/world_engine/region_author.py#L35).
- Used at [entity_author.py:411,536,625,713](src/world_engine/entity_author.py#L411)
  and [region_author.py:337,413](src/world_engine/region_author.py#L337).
- [cockpit/app.py:2463,3902,3938](src/world_engine/cockpit/app.py#L2463) bind
  `model = ollama_client.DEFAULT_MODEL` locally; **except**
  [app.py:2606](src/world_engine/cockpit/app.py#L2606):
  `model = injected.get("model", ollama_client.DEFAULT_MODEL)`.
- [app.py:1747](src/world_engine/cockpit/app.py#L1747) hardcodes
  `model=ollama_client.DEFAULT_MODEL` inline.

All citations exact. No correction.

## F3 — Seeded usages: **count is 17, not 18**; enum gap is 8 items, not 7

[scripts/seed_pilot.py](scripts/seed_pilot.py) has exactly 17
`usage="..."` call sites, one per line 1185, 1202, 1220, 1251, 1274, 1301,
1319, 1336, 1352, 1374, 1391, 1408, 1426, 1444, 1462, 1488, 1508:
`npc_dialogue`, `npc_initiative_act`, `player_narration`,
`mj_interpretation`, `mj_arbitration`, `mj_establishment`, `mj_gathering`,
`mj_speaker_selection`, `mj_initiative`, `conversation_analysis`,
`overhearing_classification`, `entity_generation`, `world_generation`,
`player_generation`, `skill_catalogue`, `region_manifest`,
`region_manifest_topup`. That is 17 named values — matching the spec's own
enumerated list — but the spec's prose says "18 usages." Off-by-one in the
spec, not in the code. Plus the comment-only duplicate block at
[:346](scripts/seed_pilot.py#L346) (`overhearing_classification`) and
[:377](scripts/seed_pilot.py#L377) (`player_narration`), confirmed.

The schema-doc enum comment
([world-engine-schema.md:854-859](world-engine-schema.md#L854)) lists exactly
13 named values + `other`: `pass_play_analysis | lore_coherence |
event_generation | player_narration | session_summary | npc_dialogue |
conversation_analysis | mj_interpretation | overhearing_classification |
mj_arbitration | mj_establishment | entity_generation | region_manifest`.

Diffing that against the 17 seeded usages, **8** are missing from the doc
comment, not 7: `mj_gathering`, `mj_speaker_selection`, `mj_initiative`,
`npc_initiative_act`, `world_generation`, `player_generation`,
`skill_catalogue` — **and `region_manifest_topup`**, which the spec's F3 list
omits. `region_manifest_topup` is seeded ([:1508](scripts/seed_pilot.py#L1508))
but appears in neither the schema-doc enum comment nor the spec's "missing"
list. Both are stale docs-to-update items for the brief.

## F4 — `destination` has zero code consumers: confirmed

Grepped every `destination` hit under `src/`: all in `cockpit/app.py` are
travel-related ([app.py:1468](src/world_engine/cockpit/app.py#L1468),
[:2858](src/world_engine/cockpit/app.py#L2858),
[:3500](src/world_engine/cockpit/app.py#L3500),
[:3675](src/world_engine/cockpit/app.py#L3675),
[:4150](src/world_engine/cockpit/app.py#L4150),
[:4165](src/world_engine/cockpit/app.py#L4165),
[:4169](src/world_engine/cockpit/app.py#L4169),
[:4246](src/world_engine/cockpit/app.py#L4246)); the sole
`PromptTemplate.destination` symbol is the field declaration itself
([models.py:790](src/world_engine/models.py#L790)). No reader anywhere. No
correction.

## F5 — Cockpit shell insertion point: confirmed, with one line-range correction

- `CREATION_TABS` registry: [cockpit/index.html:3009](src/world_engine/cockpit/index.html#L3009).
  Confirmed 10 entries (matches `TAB_KEYS` below).
- `artefacts` entry: [:3084-3091](src/world_engine/cockpit/index.html#L3084),
  `primaryAction: null` at [:3091](src/world_engine/cockpit/index.html#L3091).
- `queue` entry: `primaryAction: null` (append-only) at
  [:3107](src/world_engine/cockpit/index.html#L3107). Confirmed.
- **Correction:** `tooling/verify/checks/page_contract.py`'s `TAB_KEYS` array
  spans [**:11-14**](tooling/verify/checks/page_contract.py#L11), not `:12-15`
  as the spec states — `TAB_KEYS = [` opens at line 11, the two value lines
  are 12-13, the closing `]` is at 14. The spec's range is shifted by one
  line. Contents confirmed exact: `["npc", "pj", "lieux", "factions",
  "objets", "competences", "region", "artefacts", "registre", "queue"]` — 10
  keys.

## F6 — API surface is greenfield: confirmed

No match for `/api/prompt` anywhere under `src/world_engine/cockpit/`
(`app.py` or `crud.py`). Confirmed greenfield.

## F7 — Multiple rows per usage, "effective" resolution: confirmed

[app.py:1307-1311](src/world_engine/cockpit/app.py#L1307) is the cited
preference-chain implementation (see F1) — confirmed exact.

## F8 — C3 dry-run capable usages: confirmed

`assemble_npc_context` at [context.py:134](src/world_engine/context.py#L134),
`assemble_mj_context` at [context.py:373](src/world_engine/context.py#L373).
Both exist as described; the "pure read path, structural exclusion by query
construction" characterization matches the project's standing invariants
(`CLAUDE.md`). No correction.

## F9 — Schema change required: confirmed

`PromptTemplate` in [models.py](src/world_engine/models.py) currently has no
`model` field — grepped the whole class body, only the `destination`/other
existing columns appear. Current schema version is `v1.66`
([world-engine-schema.md:3](world-engine-schema.md#L3)), consistent with the
ticket's `vX.YY` placeholder (Claude Code assigns the number at close-step).
No correction.

---

## Summary of corrections against the spec

| # | Spec claim | Living code | Severity |
|---|---|---|---|
| 1 | F1: all 16 loaders do world-preferred-else-global | 6 loaders (`entity_author.py` ×4, `region_author.py` ×2) have no `world_id` param, filter only `is_active` | Material — affects any future loader-consolidation/resolver design |
| 2 | F3: "18 seeded usages" | 17 distinct usages seeded | Cosmetic |
| 3 | F3: enum comment missing 7 usages | missing 8 — `region_manifest_topup` also absent | Minor doc-accuracy |
| 4 | F1: `analyzer.py:138` for the `def` line | `def` is at `:136`; `:138` is a parameter line | Cosmetic |
| 5 | F5: `page_contract.py:12-15` for `TAB_KEYS` | array spans `:11-14` | Cosmetic |

Everything else in RECON-0008 (F2, F4, F6-F9, and the ticket's acceptance
criteria anchors) is byte-accurate against the current tree. No code was
touched during this pass.
