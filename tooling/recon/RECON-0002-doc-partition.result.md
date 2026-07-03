# RECON-0002 — result

Report-only. All anchors below are real `path:line` in the code as it stands
today. No code was changed, no fix or refactor attempted.

---

## Zone A — CHANGELOG boundaries in `world-engine-schema.md`

**A1 — exact CHANGELOG boundaries.**

- Header: `world-engine-schema.md:985` — `## CHANGELOG`.
- First entry: `world-engine-schema.md:987` — `- **v1.66** — ...`.
- Last entry: `world-engine-schema.md:2221` — `- **v1.1** — Initial local-phase schema.`
- After the last entry: `world-engine-schema.md:2222` is blank, then
  `world-engine-schema.md:2223` — `*Version 1.16 — Co-built with Claude, June 2026*`
  — a trailing signature/footer line, NOT part of any changelog entry. Nothing
  else follows it; line 2223 is the last line of the file.

So the section runs `985–2221` (entries) with a lone footer line at `2223`
after it. The A1 brief must decide what happens to that footer line — it
currently carries a THIRD, different version number (see A2).

**A2 — every version number asserted inside `world-engine-schema.md`.**

Three different numbers appear, in three different places, and they
disagree with each other:

| Location | `file:line` | Text |
|---|---|---|
| Intro line, top of file | `world-engine-schema.md:3` | `*Version 1.25 — Local phase (SQLite → Supabase)*` |
| Newest CHANGELOG entry | `world-engine-schema.md:987` | `- **v1.66** — ...` |
| Footer, end of file | `world-engine-schema.md:2223` | `*Version 1.16 — Co-built with Claude, June 2026*` |

The newest changelog entry (`v1.66`) matches the latest commit on `main`
(`add4c35 ... BRIEF-56 display`, and CLAUDE.md's own file-tree comments cite
v1.64 as the newest *tracked-in-CLAUDE.md* state — schema.md is one version
ahead of CLAUDE.md's tree comments as of today). Neither the intro line
(`1.25`) nor the footer (`1.16`) has been updated in a long time — both are
stale relative to `987`. This is exactly the drift the planned
`Current schema version: vX.YY` header line (A1-guard) is meant to
eliminate — today there is no single source, there are three, and they
disagree.

**A3 — inline version/BRIEF references inside TABLES / INDEXES / RELATIONS /
MIGRATION (i.e. everything between `## TABLES` at `world-engine-schema.md:17`
and `## CHANGELOG` at `world-engine-schema.md:985`).**

All occurrences found (`file:line` + context). None of these are inside
INDEXES (`873`), KEY RELATIONS (`945`), or MIGRATION NOTES (`973`) except one
(`896`, inside INDEXES) — every other hit is inside TABLES:

| `file:line` | Context |
|---|---|
| `34` | `-- the single globally-active world (v1.54)` |
| `83-84` | `-- table (schema v1.57, BRIEF-46)` |
| `92` | `-- (schema v1.44, BRIEF-33):` |
| `148` | `DORMANT (BRIEF-26, schema v1.38):` |
| `160` | `DORMANT (schema v1.44, BRIEF-33): prose dual of` |
| `174` | `Durable member <-> faction roster (schema v1.39, BRIEF-27).` |
| `188` | `v1.41, BRIEF-30).` |
| `193` | `is set (schema v1.41, BRIEF-30).` |
| `217` | `-- \`parent_faction_id\`'s job (schema v1.38), not this table.` |
| `223` | `-- structural secret-exclusion this step (Scope OUT, BRIEF-27); both are the` |
| `264` | `-- (controller -> controlled asset, schema v1.38/BRIEF-26) are` |
| `315` | `Conserved currency, append-only (schema v1.31, BRIEF-18). Balance is ...` |
| `328` | `-- branch, BRIEF-19/v1.32; 'pass_play'` |
| `559` | `-- (analyze_window, v1.21).` |
| `576` | `-- upgrades, v1.17)` |
| `580` | `-- since BRIEF-08/D2a.1,` |
| `587` | `-- removed in v1.21).` |
| `594` | `-- removed in v1.21).` |
| `659` | `Mundane tracked objects — static possession (schema v1.18). Extension of` |
| `684` | `World-scoped custom skill catalogue (schema v1.63, BRIEF-55). One row = one` |
| `716` | `The player character's skill sheet (schema v1.22) — physical/sensory domains` |
| `718` | `schema v1.63 distinguishes a base-domain row (NULL) from a custom-skill row` |
| `759` | `searches (schema v1.26, BRIEF-13). \`ambient\` rows additionally form` |
| `761` | `silence predicate on location entry (schema v1.30, BRIEF-17).` |
| `773` | `-- roll. ACTIVE since v1.30 — read by the` |
| `798` | `signpost_group value (schema v1.30, BRIEF-17, D1: one` |
| `809` | `-- NOTE (narrowed in v1.30 — see CHANGELOG): this table is NEVER read by any` |
| `896` (INDEXES) | `-- one player character per user per world (BRIEF-46), multiplayer-safe` |

All 27 occurrences read as *pointers* (a table-comment citing which
BRIEF/version introduced or changed a column) rather than facts stated only
there — every one of them has a fuller, matching prose entry in the
CHANGELOG section (spot-checked: `v1.54`→`987` area no, `v1.54` entry is at
`1210`; `v1.63`→`1040`; `v1.31`→`1605`; `v1.18`→`1938`; `v1.30`→`1627`, etc.,
all present). One exception worth flagging: `world-engine-schema.md:809`
explicitly says `"see CHANGELOG"` — a same-file cross-reference that stays
valid only if the split brief either (a) keeps that phrase generic enough to
still resolve to the new changelog file, or (b) rewrites it to name the file.
Classification (pointer vs. fact-only-there) is reported, not decided, per
recon scope.

---

## Zone B — Decision-record header pattern in `tooling/standards/ARCHITECTURE_DECISIONS.md`

**B1 — header count and pattern conformance.**

Total `## ` headers: **47** (`tooling/standards/ARCHITECTURE_DECISIONS.md`,
grep count).

Headers matching `## TITLE … (BRIEF-NN[, schema vX.YY | no schema change])`
cleanly (BRIEF-NN as the sole/last parenthetical token, in that order): **27**.

Headers that do **NOT** match cleanly: **20** (42.6% of 47) — verbatim,
`file:line`:

| `file:line` | Header (verbatim) | Why it doesn't match |
|---|---|---|
| `7` | `## CONTEXT` | No BRIEF-NN at all |
| `18` | `## CORE DECISION — Free dialogue, controlled consequences` | No BRIEF-NN |
| `31` | `## SCHEMA ADJUSTMENTS` | No BRIEF-NN |
| `213` | `## CREATOR REVIEW COCKPIT` | No BRIEF-NN |
| `581` | `## MULTI-NPC SCENES — Gatherings (schema v1.8, Tier 1)` | No BRIEF-NN; trailing `Tier 1` not `schema`/`no schema change` |
| `662` | `## NPC INITIATIVE — Spontaneous bystander actions (Tier 3)` | No BRIEF-NN, no schema tag |
| `761` | `## MJ CONTEXT — the player's perception boundary (schema v1.12, scope D-b3)` | No BRIEF-NN; trailing `scope D-b3` |
| `816` | `## OBJECT PERMANENCE — ambient props vs tracked items (schema v1.18, BRIEF-06)` | Order reversed: schema before BRIEF |
| `869` | `## PHYSICAL LAYER — skill sheet (schema v1.22, BRIEF-10)` | Order reversed |
| `1336` | `## WORLD MAP — location adjacency (Step A, BRIEF-15, schema v1.28)` | Extra leading token `Step A,` inside parens |
| `1381` | `## WORLD MAP — travel (Step B, BRIEF-16, schema v1.29)` | Extra leading token `Step B,` |
| `1472` | `## ECONOMY — ledger (currency, schema v1.31, BRIEF-18)` | Extra leading token `currency,`; order reversed |
| `1650` | `## AI entity-authoring assistant (NPC, Location, Faction) (schema v1.36–v1.37, v1.43, BRIEF-24, BRIEF-25, BRIEF-32)` | Two parenthetical groups; version range; THREE BRIEF numbers |
| `2196` | `## REGION GENERATION — orchestrator (chantier 1) (BRIEF-34, schema v1.45)` | Extra parenthetical group `(chantier 1)` before the BRIEF one |
| `2677` | `## REGION REVIEW — read-only full-sheet modal (BRIEF-41, R4a, schema v1.52)` | Extra middle token `R4a,` |
| `3076` | `## GATHERING LIFECYCLE RECONCILIATION (BRIEF-53, application-layer, no schema change)` | Extra middle token `application-layer,` |
| `3349` | `## V1 SCOPE — Minimal playable` | No BRIEF-NN |
| `3369` | `## DESIGN CONSTRAINTS CARRIED FORWARD` | No BRIEF-NN |
| `3378` | `## DATABASE CARRIER FILE — out-of-tree relocation (incident 2026-06-19)` | No BRIEF-NN; uses `(incident DATE)` instead |
| `3426` | `## Deferred decisions` | No BRIEF-NN |

**BLOCKING FINDING (B1):** 20/47 = 42.6% of headers are pattern exceptions,
more than double the ~20% threshold the spec sets as the trigger for
reconsidering the generator design. The exceptions aren't uniform either —
they split into at least three distinct shapes: (a) no BRIEF-NN at all (9
headers — mostly front-matter/scope sections and a few early feature
records), (b) BRIEF-NN present but with extra tokens or reversed order
inside the parenthetical (9 headers), (c) multi-BRIEF/multi-version single
record (`1650`, 1 header covering BRIEF-24/25/32 together). A generator
that only recognizes the clean pattern will silently drop or mis-parse
close to half the archive.

**B2 — false-positive `## ` inside fenced code blocks.**

Fenced code blocks found in the file: `187–192`, `1012–1017` (` ```json `),
`1069–1074` (` ```json `). None of the 47 `## `-prefixed lines fall inside
any of these three ranges. **No false positives found** — every `## ` line
is a real header.

**B3 — duplicate header titles.**

No two headers share an identical title string. Several share a topic
prefix with a distinguishing suffix (`PHYSICAL LAYER` ×4: `816`/`923`/`1003`/
`1114`; `WORLD MAP` ×2: `1336`/`1381`; `FACTION MEMBERSHIP` ×3: `1924`/`2046`/
`2089`; `REGION GENERATION` ×2: `2196`/`2473`; `WORLD-SCOPED CUSTOM SKILL
CATALOGUE` ×2: `3217`/`3294`) but every full title is unique, so anchor
generation (e.g. slug-from-title) will not collide — as long as the anchor
scheme includes the full title, not just the topic prefix.

---

## Zone C — Stale references inventory (feeds the separate sweep ticket)

**C1 — references to `ARCHITECTURE_DECISIONS.md` repo-wide.**

14 files match. Path form and staleness assessed per hit:

| `file:line` | Path form used | New location? |
|---|---|---|
| `README.md:24` | Bare filename, in a project-structure tree that places it at repo root | **STALE — implies OLD (root) location**; actual file is at `tooling/standards/ARCHITECTURE_DECISIONS.md` |
| `CLAUDE.md:9,39,63,97,130,548,734` | Full path `tooling/standards/ARCHITECTURE_DECISIONS.md` | Correct (NEW location), not stale |
| `.claude/commands/close-step.md:7` | Full path `tooling/standards/ARCHITECTURE_DECISIONS.md` | Correct, not stale |
| `world-engine-schema.md:1278,1813,1834,1908,1937,1955,2088,2101,2130,2218` | Bare filename, no directory | Ambiguous — doesn't assert either path, just names the file |
| `src/world_engine/context.py:663` | Bare filename | Ambiguous |
| `src/world_engine/gathering.py:16` | Bare filename | Ambiguous |
| `src/world_engine/entity_author.py:10` | Bare filename | Ambiguous |
| `src/world_engine/region_author.py:18` | Bare filename | Ambiguous |
| `src/world_engine/cockpit/app.py:595,668,709,2762,3643` | Bare filename | Ambiguous |
| `src/world_engine/cockpit/index.html:2116,2229` | Bare filename | Ambiguous |
| `src/world_engine/models.py:196` | Bare filename | Ambiguous |
| `tooling/tickets/TICKET-0001-doc-partition.md:27,45` | Bare filename | This ticket's own text, not a sweep target |
| `tooling/recon/RECON-0001.result.md:202` | Full path (used correctly to cite the F2 record — see Zone F) | Correct |
| `tooling/recon/RECON-0002-doc-partition.md:14,39,56,87` | Full path | This spec's own text, not a sweep target |

Only one confirmed stale-location hit today: `README.md:24`. Everything else
either already uses the correct `tooling/standards/` path or names the file
without a directory (can't be classified as stale-vs-current from the text
alone).

**C2 — references to "schema changelog" / "changelog entry" / similar phrases.**

6 files match:

| `file:line` | Text |
|---|---|
| `CLAUDE.md:38` | `"Step closure: every closed step updates the schema changelog (if schema-touching)..."` — generic phrase, will need rewording once the changelog is a separate file (A1-guard) |
| `world-engine-schema.md:1035` | `"Closes the chantier-2 deferral noted in BRIEF-55/v1.63's CHANGELOG entry"` — a changelog entry cross-referencing an earlier changelog entry; both move together under A1, stays internally consistent |
| `tooling/standards/ARCHITECTURE_DECISIONS.md:3406` | `"This changelog entry (schema v1.34) — the doc record of the..."` — a decision record pointing at a `world-engine-schema.md` changelog entry by version number only, no file path; stays resolvable after the split since it doesn't name a path |
| `tooling/tickets/TICKET-0001-doc-partition.md:1,55` | This ticket's own text |
| `tooling/recon/RECON-0002-doc-partition.md:1,63-64` | This spec's own text |

**Cross-reference (not asked by C2 directly, but adjacent and load-bearing):**
`.claude/commands/close-step.md:5-6` — `"Changelog — if the schema was
touched, add a version entry to \`world-engine-schema.md\`."` — does not
contain the literal word "changelog" as a phrase-match target but IS a
changelog-writing instruction pointed at the pre-split file. See Zone D.

**Naming-collision fact for the brief (not in the RECON's original zones,
but directly relevant to A1):** a `CHANGELOG.md` already exists at the repo
root (`CHANGELOG.md:1-30`, read in full) — a pre-existing, unrelated,
French-language *application-level* changelog ("Addendum applicatif —
2026-06-09", NPC-initiative feature notes), not the schema changelog. The
ticket's planned filename `world-engine-schema-changelog.md` is distinct
from this file, but the brief should be aware `CHANGELOG.md` is already
taken by something else so the new file is never confused with it or
merged into it.

---

## Zone D — Where Claude Code learns the current schema version today

Two instruction sites found (both inside the CLAUDE.md/.claude scope; no
hook or script encodes version-bump logic — checked `.claude/hooks/
session-start.ps1`, `block-main-push.ps1`, `block-db-in-git.ps1`, none
mention schema/version/changelog):

1. `CLAUDE.md:59-60` (verbatim): `"...a ticket ends with \`/verify\`. Claude
   Code owns schema version numbers (\`vX.YY\`), recorded in
   \`tooling/standards/schema_changelog.md\`."`
2. `.claude/commands/close-step.md:5-6` (verbatim): `"**Changelog** — if the
   schema was touched, add a version entry to \`world-engine-schema.md\`.
   If not, confirm no entry is needed."`

**BLOCKING FINDING (D1):** these two instructions already disagree with each
other, independent of this ticket. (1) says the version log lives at
`tooling/standards/schema_changelog.md` — **that file does not exist**
(confirmed: `Glob tooling/standards/schema_changelog.md` → no match). (2)
says to append to `world-engine-schema.md` directly, which is where the
CHANGELOG section actually lives today. So today, before any split: (a) one
governance line names a changelog file that has never existed, and (b) the
one instruction that's actually followed (`close-step.md`) will become
**wrong** the moment A1 extracts the CHANGELOG section, since it will still
say "add a version entry to `world-engine-schema.md`" after that section no
longer lives there. Both `CLAUDE.md:60` and `close-step.md:5-6` need to be
reconciled and repointed at whatever the A1 brief names the real changelog
file — and the brief should settle whether that file is meant to be the
same thing as the never-created `schema_changelog.md`, or whether `CLAUDE.md:63`'s separate mention of `schema_changelog.md` (in the "where things
live" list, alongside `ARCHITECTURE_DECISIONS.md` and `code_standards.md`)
is simply a naming mismatch to fix as part of A1-guard.

No other `.claude/commands/*` or `.claude/skills/*` file mentions schema
version or changelog (`brief-exec.md`, `verify.md`, `review-step.md`,
`recon.md`, skills `recon`, `brief`, `verify-authoring` — all read in full,
none reference it).

---

## Zone E — Verify harness seam for the B1 index check

`tooling/verify/run.py` (54 lines, read in full):

- A ticket's own markdown file (`tooling/tickets/<TICKET-ID>.md`) declares
  its machine-checkable criteria under a `### Machine` heading
  (`run.py:17-22`, `machine_checks()`); each line matching the regex
  `-> verify/checks/([A-Za-z0-9_./-]+\.py)` (`run.py:10`) is collected as a
  check to run, in the order encountered, de-duplicated by filename.
- There is **no separate check registry file** — a check "plugs in" simply
  by (a) existing as a `.py` file under `tooling/verify/checks/` and (b)
  being referenced by a `-> verify/checks/<name>.py` line inside some
  ticket's `### Machine` section (`run.py:33-34` resolves the check purely
  by filename, ignoring any path prefix in the link text).
- Each check is invoked as `subprocess.run([sys.executable, path])`
  (`run.py:37`); pass/fail is read from the process exit code only
  (`run.py:38`); the last non-empty line of stdout/stderr becomes the
  reported message (`run.py:41`).
- Verdict JSON is written to `tooling/verify/results/<TICKET-ID>.json`
  (`run.py:44-45`) and also printed; process exit code mirrors the overall
  verdict (`run.py:47`).
- `tooling/verify/checks/` currently contains **only `.gitkeep`** — no
  existing check file to use as a model for the new `decisions_index`
  check's shape; `.claude/skills/verify-authoring/SKILL.md` (read in full)
  gives the general kinds (DB assertion / File check / Command verdict /
  Structural invariant) and the runtime contract (`venv` + `PYTHONPATH=src`,
  deterministic, no LLM calls) but there is no prior example in this repo
  yet for a check that compares a generated artifact (`DECISIONS_INDEX.md`)
  against a parsed source file (`ARCHITECTURE_DECISIONS.md` headers) — the
  `decisions_index` check would be the first "regenerate and diff" style
  check in the repo, not a variant of an existing one.

Registration point for the new check: add
`tooling/verify/checks/decisions_index.py` (a plain Python file, exit 0/1),
and reference it from the relevant ticket's `### Machine` section as
`-> verify/checks/decisions_index.py`. No other wiring exists or is needed.

---

## Zone F — Decision F2 retrieval (input for pending decision H)

Found: `tooling/standards/ARCHITECTURE_DECISIONS.md:3203-3208`, inside the
`## WORLD BLOCK DELETION (BRIEF-54, schema v1.62)` record (header at
`tooling/standards/ARCHITECTURE_DECISIONS.md:3130`). Sibling decisions in
the same record, confirmed present: A1 (hard delete, `:3140-3148`), B2′
(type-`Oui` confirm, `:3150-3156`), G1 (re-activation, `:3210-3213`) — all
as the RECON spec's framing expected.

Verbatim, full paragraph:

> **F2 — no auto-backup.** `scripts/backup.py` exists, is documented as a
> manual pre-session step, and has zero existing call-sites (confirmed by
> the prior RECON, section 10). BRIEF-54 does not import it or call it from
> the delete path — an automatic backup before an irreversible action was
> considered and explicitly rejected; the creator is expected to back up
> manually if they want a safety net before deleting a world.

(`tooling/standards/ARCHITECTURE_DECISIONS.md:3203-3208`, quoted exactly as
written, no paraphrase.)

---

## BLOCKING FINDINGS recap

1. **Zone B1** — 20 of 47 decision-record headers (42.6%) don't match the
   expected `## TITLE … (BRIEF-NN[, schema vX.YY | no schema change])`
   pattern, well past the ~20% threshold the spec sets for reconsidering the
   index-generator design. The exceptions fall into three distinct shapes
   (no BRIEF-NN at all; BRIEF-NN present but reordered/with extra tokens;
   one multi-BRIEF record) — a single regex will not cleanly handle all
   three.
2. **Zone D1** — the two existing instructions for "where the schema
   version lives" already contradict each other and one names a file that
   doesn't exist: `CLAUDE.md:59-60` says the version log is
   `tooling/standards/schema_changelog.md` (confirmed absent from the repo),
   while `.claude/commands/close-step.md:5-6` — the instruction actually
   exercised at every step-closure — says to append directly to
   `world-engine-schema.md`. The A1-guard rewording must fix `close-step.md`
   too, not only `CLAUDE.md`, and must decide whether the new changelog file
   the ticket is about to create is the same file `CLAUDE.md:63` already
   calls `schema_changelog.md`.

No other zone produced a blocking finding. Zone A's version-number
inconsistency (three different numbers in `world-engine-schema.md`: `1.25`
intro, `1.66` newest entry, `1.16` footer) and the pre-existing root-level
`CHANGELOG.md` naming collision are reported as findings but not flagged
blocking — they don't prevent either planned brief from proceeding, they're
just facts the briefs need to account for.
