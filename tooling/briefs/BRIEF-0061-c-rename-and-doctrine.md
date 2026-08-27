# BRIEF — Step "the rename and the doctrine"

Ticket: TICKET-0061 · Brief: BRIEF-0061-c · Branch: `ticket/0061`

## Context

Last brief of the ticket, and last of the seven-ticket refactor series.

Two jobs. First, `cockpit/index.html` becomes `cockpit/legacy.html` (E1):
three files in this repo are called `index.html` — the Vite entry, the legacy
surface, the build output — and the deferral that postponed the rename gave
as its reason "the rename touches all nine index-anchored checks, which that
ticket retires anyway" (`ARCHITECTURE_DECISIONS.md:11042`). Under A3 those
checks are **not** retired, so the reason has expired and the rename lands
here.

Second, the doctrine. `CLAUDE.md` describes a state that no longer exists —
measured, three separate false claims — and the decision registry contains
two entries that directly contradict each other on Play's fate. Both are
repaired: the file by editing, the registry by supplement.

The rename goes last on purpose: it touches eight checks, and doing it before
briefs -a and -b would collide their churn with this one's.

Three commits.

---

## Mini-RECON — anchors measured on `main`, 2026-08-20, post-TICKET-0067

Tree-specific claims. **Verify each locally.** If any has drifted, STOP.

**The nine path sites** (8 checks + `app.py`):

| File | Line | Constant |
|---|---|---|
| `tooling/verify/checks/creation_island.py` | 107 | `INDEX_HTML` |
| `tooling/verify/checks/faction_roster_panel.py` | 27 | `INDEX_HTML` |
| `tooling/verify/checks/graph_primitive.py` | 97 | `INDEX_HTML` |
| `tooling/verify/checks/legacy_mount.py` | 38 | `LEGACY_INDEX` |
| `tooling/verify/checks/page_contract.py` | 25 | `INDEX_HTML` |
| `tooling/verify/checks/review_component.py` | 46 | `INDEX_HTML` |
| `tooling/verify/checks/schema_0024.py` | 23 | `INDEX_HTML` |
| `tooling/verify/checks/stylesheet_partition.py` | 141 | `COCKPIT_INDEX` |
| `src/world_engine/cockpit/app.py` | 66 | `_INDEX_HTML` |

Plus whatever brief -b's ratchet constant added to `module_budget.py` —
**a tenth site this brief must carry**, and one that did not exist when
TICKET-0061 was written. Verify it.

**The three false `CLAUDE.md` claims** — every symbol's *only* trace in the
legacy document is a comment recording its departure:

| CLAUDE.md | Claim | Measured in `index.html` | Actually lives in |
|---|---|---|---|
| `:53` | `showCreationSubTab` (`cockpit/index.html`) | 1 hit, comment `:2462` "…are gone" | `frontend/src/creation/tabs.js` |
| `:57` | `_buildRuntimeCreationTabs()`/`refreshCreationTabs()` (`index.html`) | 1 hit each, comment `:2549-2550` "…are gone" | `frontend/src/creation/tabs.js`, as **`buildRuntimeCreationTabs`** (no leading underscore) — `page_contract.py:195` asserts `export function buildRuntimeCreationTabs` there |
| `:58` | `batchRenderAll`/`batchReviewDescriptor` (`index.html`), `reviewRegister`, a legacy-window bridge installed by `creation/mount.js` | **0 hits each**; no such bridge in `mount.js` | `frontend/src/creation/RoomBatch.svelte`, `frontend/src/creation/review/registry.js` |

**Budget**: `CLAUDE.md` is 498 lines (`wc -l`) against `claude_md_contract.py`
rule 2's 500-line cap. `### File structure` is 68 lines against its 80-line
cap. Line 58 alone is **3 438 characters**; line 278 is **5 180**.

**The registry contradiction**:
`ARCHITECTURE_DECISIONS.md:10973` (TICKET-0056 entry) — "`play` survives to
TICKET-0061 **and beyond**, until its own rewrite."
`ARCHITECTURE_DECISIONS.md:12015` (TICKET-0060 entry) — "`TICKET-0061`
**empties `LEGACY_MOUNTS` and retires `cockpit/index.html` entirely**."

**TICKET-0066's expired exclusion**: `ARCHITECTURE_DECISIONS.md:11785` —
`shared.css`/`creation.css` keep unhashed names because the legacy document
links them by fixed path, "that constraint expires on its own at
TICKET-0061." Under A3 it does not expire.

### Hard STOP conditions

1. **Briefs -a and -b are not merged.** This brief renames constants that
   brief -b just edited.
2. **A tenth path site exists that this brief does not list.** Grep for the
   literal `"index.html"` across `tooling/` and `src/` before editing; the
   count must be the nine above plus brief -b's ratchet constant, plus the
   three legitimate references to *other* files (`frontend/index.html`,
   `cockpit/static/index.html` — `frontend_build_fresh.py:38,112`,
   `shell_height_chain.py:33`, `stylesheet_partition.py:140`). **Do not
   rename those.**
3. **`GET /legacy` does not return the same bytes after the rename.** The
   document is a path change and nothing else.
4. **`CLAUDE.md` grows.** The rewrite is net-neutral or reducing. If a
   correct replacement cannot fit, STOP and report rather than spending the
   last two lines of the budget.
5. **Any check goes red that was green after brief -b.**

---

## Scope IN

### Commit 1 — the rename (E1)

**1.1 — `git mv src/world_engine/cockpit/index.html src/world_engine/cockpit/legacy.html`.**
Not one byte of content changes. Verify with a content hash before and after.

**1.2 — The nine path constants** (plus brief -b's ratchet constant) point at
`legacy.html`. The constant NAMES stay as they are — `INDEX_HTML`,
`LEGACY_INDEX`, `COCKPIT_INDEX`, `_INDEX_HTML`. Renaming ten identifiers
across eight checks in the same commit as a file move makes the diff
unreviewable, and the names are not what was ambiguous; the filename was.
Record that choice in the commit message so the next editor does not read it
as an oversight.

**1.3 — Failure messages that print the path** now print the new one
automatically (they interpolate the constant). Verify none hard-codes the
string `index.html` in prose; if one does, update the prose.

**1.4 — `app.py`'s `serve_legacy` docstring** names `index.html` in text
(`:259`). Update to `legacy.html`. The route path `/legacy` is unchanged.

### Commit 2 — `CLAUDE.md` (F1)

Four edits, all net-neutral or reducing.

**2.1 — Line 53.** `showCreationSubTab` is in `frontend/src/creation/tabs.js`.
Replace `cockpit/index.html` with that path.

**2.2 — Line 57.** Two errors: the file, and the symbol name. Replace
`_buildRuntimeCreationTabs()`/`refreshCreationTabs()` (`index.html`) with
`buildRuntimeCreationTabs()`/`refreshCreationTabs()`
(`frontend/src/creation/tabs.js`). Verify the exact exported name against
`page_contract.py`'s own regex before writing it — that check is what makes
the claim testable, so the doctrine must quote what the check asserts.

**2.3 — Line 58.** The room-batch sentence is false in three ways: the
symbols are not in the legacy document (0 occurrences), `RoomBatch.svelte`
carries them, and no legacy-window bridge exists in `creation/mount.js`.
Rewrite that clause to name `frontend/src/creation/RoomBatch.svelte` and
delete the bridge sentence entirely. Deleting it *shrinks* the line, which
is exactly the budget headroom the other edits need.

**2.4 — Lines 17-18 and 414: the sealed posture.** Both currently say Play
stays legacy "until its own ticket (TICKET-0061)". Under A3 that ticket is
TICKET-0069, and the filename is now `legacy.html`. Line 414's file-tree
entry becomes, in substance: *legacy host for Play until TICKET-0069;
TICKET-0059 retired Creation, TICKET-0060 retired Observation,
TICKET-0061 sealed and renamed it; served at `/legacy` inside the shell's
iframe.* Keep it to one line — the `### File structure` section has 12 lines
of headroom but the file has 2.

**Do NOT** add a line about the N1 doctrine, the graph primitive, or anything
else this ticket touched. `CLAUDE.md` is law-only and at 99.6% of its budget;
TICKET-0071 is the pass that makes room.

### Commit 3 — the decision registry (one appended supplement)

One entry, appended at the end of
`tooling/standards/ARCHITECTURE_DECISIONS.md`. **Nothing existing is edited,
annotated in place, or reconciled by rewriting** — including the two entries
that contradict each other. The supplement is the reconciliation.

It must record, at minimum:

- **The Play-fate contradiction, resolved.** Quote both entries by line, name
  TICKET-0056's as the one that stands, and say why: Q2 of the workstream map
  locked it, and PART C rule 1 makes the seal ticket the wrong place for the
  largest migration of the series.
- **A3 and 3b together.** The point of 3b is that `retiredBy` was validated
  by format only, so a sealed pointer at a finished ticket would have been a
  well-formed falsehood a green check blessed. Record that the accessor to
  this guarantee is the ticket file's existence and non-`done` status, and
  that this rule is **inexpressible** under the alternative where `retiredBy`
  names TICKET-0061 itself.
- **The ratchet on the legacy document**, and the measurement that motivated
  it: 2 762 lines against a 1000-line cap that no baseline exempts, plus
  `function_length.py`'s 80-line cap that `sendPlayerLine` (~247 lines)
  escapes. Record the per-function deferral and its reactivation condition
  (TICKET-0069).
- **`legacyCall` stays.** Record the measured reason (rule 6 requires it,
  measured `FAIL: rule6: legacyCall is defined 0 time(s)`) and that a
  zero-call-site export here is the confinement rule working, not dead code.
  This corrects a specification error in TICKET-0067's decision table and
  TICKET-0061's brief decomposition; correct by supplement, do not edit
  either.
- **C3's two halves and what produced them.** The declared external-tool
  contract (measured: `fastapi`, `httpx`, `pyflakes`, `sqlalchemy`,
  `sqlmodel`; and the measured misclassification — five absent dependencies
  yielding `0 environment … 6 other`), and the CRASH class with recovered
  failures, which exists because TICKET-0067 found a check whose first defect
  hid its second. Record the harness's `sys.path[0]` restoration as
  load-bearing, discovered by `stylesheet_partition.py`'s sibling import
  crashing without it.
- **TICKET-0066's exclusion has NOT expired.** `:11785` says the unhashed
  stylesheet names expire "on its own at TICKET-0061"; under A3 they do not.
  Correct by supplement.
- **D-0063-scoped-component-styles has NOT reactivated.** Its condition — no
  document outside the shell consumes `creation.css` — remains false.
- **The four named deferrals**, each with its reactivation condition, and the
  3D one recorded explicitly as a **HUMAN gate** rather than a structural
  condition: TICKET-0068 (Play's stale `WORLD_ID`), TICKET-0069 (Play
  migration — human gate, Nia's request, horizon 1 year+), TICKET-0070
  (symbol-location rule), TICKET-0071 (`CLAUDE.md` hygiene, including the
  measurement that its 500-line budget is contourned by line length: 8 lines
  carry 30% of 45 979 characters).
- **The lapsed-guard pattern, third instance.**
  `observation_surface.py` (TICKET-0059→0060), `npc_goal_read.py`
  (TICKET-0051/0053→0067), and the corpus gate itself, which TICKET-0060's
  own Machine section did not link. Cross-reference C1 as the closure. Do
  **not** restate the pattern's general lesson — it already has an entry.
- **The 3D guard rail: cross-reference only.** TICKET-0055, -0056 and -0057
  each held this line. The seal is the strongest temptation to re-nail it.
  Do not.

Then regenerate `tooling/standards/DECISIONS_INDEX.md` mechanically and run
`decisions_index.py`.

---

## Scope OUT

REPORT ONLY:

- **`frontend/index.html` and `cockpit/static/index.html`.** Two other files
  with the same name, referenced by `frontend_build_fresh.py`,
  `shell_height_chain.py` and `stylesheet_partition.py:140`. Not renamed, not
  touched. The rename was deferred *because* three files share the name; it
  resolves the ambiguity by renaming the one that is not an entry point.
- **Renaming the ten path CONSTANTS** (`INDEX_HTML` → `LEGACY_HTML`, etc.).
  Deliberate, recorded in 1.2. If it is ever wanted, it is a mechanical
  ticket of its own.
- **Restructuring `CLAUDE.md`, moving content to other documents, or
  touching its budget.** TICKET-0071. This brief repairs three false claims
  and updates two lines for the seal — nothing else.
- **Adding any doctrine line for the N1 accessor, the graph primitive, the
  ratchet, or C3.** The registry supplement is where those live.
- **Opening TICKET-0068/-0069/-0070/-0071.** They are named in the
  supplement; depositing them is Nia's.
- **F3** (`start_run` deriving the active world server-side). Its condition —
  "a ticket opened after TICKET-0061" — becomes satisfiable. Opening it is
  not this brief's job.
- **Hashing `shared.css`/`creation.css`.** The supplement records that the
  exclusion did not expire; it does not implement anything.
- **`stylesheet_partition.py` rule7 (legacy).** Not retired. Its alarm stays
  silent and armed.
- **Backend, schema, canon-write.** The only `src/` edits are `app.py:66`'s
  path constant and its docstring.

---

## Invariants to defend

- **History is sacred.** One appended supplement. The TICKET-0056 and
  TICKET-0060 entries are not edited. Neither is TICKET-0067's decision
  table nor TICKET-0061's brief decomposition — the `legacyCall` correction
  is recorded, not retrofitted.
- **`CLAUDE.md` is law-only and budgeted.** ≤ 500 lines (currently 498),
  `### File structure` ≤ 80 (currently 68). Net-neutral or reducing.
- **The 3D guard rail is cross-referenced, never restated.** Restating
  doctrine is how doctrine drifts — three prior tickets held this line at
  less temptation than this one.
- **Fail-closed guards never lapse.** The rename re-points constants; it
  weakens no assertion. All eight index-anchored checks end holding exactly
  what they held before, against a new path.
- **The legacy document is byte-untouched.** A `git mv` and nothing else.

---

## Done means

- [ ] `src/world_engine/cockpit/legacy.html` exists;
      `src/world_engine/cockpit/index.html` does not; the content hash is
      identical to the pre-move file.
- [ ] `grep -rn '"index.html"' tooling/ src/` returns only the legitimate
      references to `frontend/index.html` and `cockpit/static/index.html`.
- [ ] All eight renamed-anchor checks exit 0: `creation_island`,
      `faction_roster_panel`, `graph_primitive`, `legacy_mount`,
      `page_contract`, `review_component`, `schema_0024`,
      `stylesheet_partition` — plus `module_budget` for brief -b's ratchet.
- [ ] `GET /legacy` returns 200 and the same bytes as before the rename.
- [ ] `grep -n "batchRenderAll\|_buildRuntimeCreationTabs" CLAUDE.md`
      returns no claim placing either in the legacy document.
- [ ] `claude_md_contract.py` exits 0; `wc -l CLAUDE.md` ≤ 498.
- [ ] `decisions_index.py` exits 0 after the supplement and the regenerated
      index.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits **0**.
- [ ] Three commits on `ticket/0061`, each green on its own.
- [ ] `/review-step` and `/close-step` run.

---

## Docs to update

This brief **is** the doc update. `CLAUDE.md` (commit 2),
`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (commit 3).

One document is deliberately left for Nia rather than edited here:
`Active_project.md`. Its PART B entry for TICKET-0061 and its PART D Q2 both
still carry the pre-seal reading. It is the workstream map, not a governed
artifact, and whether it is corrected or kept as a historical record is the
creator's call — report its state, do not edit it.

No schema changelog entry: `schema_version_touched: none`.
