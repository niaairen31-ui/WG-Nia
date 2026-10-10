---
id: TICKET-0064
title: Creation stylesheet coverage — stranded selectors and the missing partition rule
type: bug
status: live-gate
created: 2026-08-19
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0064-a]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Ticket 0059 est terminer et mergé en entier. Je veux que tu effectue une
review du code. Pour ton information, le visuelle du cockpit a changé, dit
moi si c'Est normal en plus des résultats du review"

The review found the visual change to be half intended (BRIEF-0059-l's chrome
inversion moved Creation out of the legacy document, by design) and half a
defect (ten selectors Creation still uses were left in a stylesheet the Svelte
document never loads). This ticket is the defect half.

## Clarifications resolved (intake)

Measured on `main` @ `6185e3d` (full clone, this session). Every number below
is a measurement, not an inference.

**The defect.** `frontend/src/creation/Creation.svelte` applies `.app-view`
(:77), `.panel-head` (:98, :179, :211), `.layout` (:160), `.sidebar` (:161),
`.sidebar-head` (:162), `.conv-list` (:171, :183), `.right-col` (:174) and
`.transcript-panel` (:210). None of these resolve in the Svelte document.
`Creation.svelte` carries no scoped `<style>`; the built CSS asset
(`static/assets/index-Cvldi7hT.css`, 1238 bytes) defines none of them. They
exist only in `cockpit/index.html`'s inline `<style>` (lines 12–511), which
`static/index.html` does not link. `.layout` is
`display: grid; grid-template-columns: 300px 1fr` — its absence collapses
Creation's two-column layout, which is the reported symptom.

Ten selectors total, adding `.btn-end` (Competences / DiscDetailsEditor /
GoalsEditor / KnowledgeEditor) and `.analyze-status` (QueueFilters).

**Root cause.** `RECON-0063-a-selector-audit.md` classified "Two-column layout
· Sidebar · Right column · Transcript panel · App views" as *stays inline
(Play + legacy chrome)*, reasoning textually that no Creation island applied
them. That was true when the audit was written. TICKET-0063 merged (`65b3f76`)
before `3fa8844` created `Creation.svelte` with exactly those class names. The
audit was invalidated by a later commit inside the same merge train.

**Structural cause.** `stylesheet_partition.py` has six rules covering
existence, disjointness (rule2), token uniqueness, link presence, `creation.css`
link lifetime, and byte parity. None covers *coverage*. The check proves the
three sheets do not overlap; it never proves Creation receives its visual
layer. All nine frontend-scoped checks are green on the defective tree —
including `stylesheet_partition` itself. The guard is fail-open for this
failure mode, and TICKET-0059's own acceptance list states only the
disjointness half.

**Decisions locked (this conversation).**

- `A1` — the ten selectors are redistributed by measured consumer count, not
  by banner. Eight have ≥1 surviving legacy consumer and go to `shared.css`;
  `.layout` and `.right-col` have zero and go to `creation.css`. Movement is
  selector-level: `.conv-item*` and `.transcript-body` share banners with
  movers, are unused by `frontend/src`, and stay inline.
- `B1` — the coverage rule lands as `rule7 (coverage)` inside
  `stylesheet_partition.py`, not as a separate check. Both halves of one
  guarantee stay in one file.
- `C2` — no process rule is added for stale RECON classification. `rule7` makes
  a wrong classification fail closed, which is the structural answer.
- `D1` — dedicated ticket. TICKET-0059 is not reopened.
- `E2` — the extractor reads literal segments of `class="..."` attributes and
  ignores expression-only attributes. No annotation convention.
- `F2` — `rule7` covers class *and* id selectors. Zero ids are stranded today;
  the rule covers them because the escape mechanism is identical.
- `G1` — `rule7` is directional: it covers `frontend/src/**` against the
  Svelte-reachable sheets only. The mirror direction (legacy markup against
  `shared.css` plus the inline block) is a named deferral with an explicit
  reactivation condition: **TICKET-0060, Observation surface migration**.

**Numbering.** `TICKET-0064` is assigned here. The NPC scheduling planning
session that also carried `0064` was never deposited and renumbers when it
opens.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [x] Each of `.app-view`, `.panel-head`, `.sidebar-head`, `.conv-list`,
      `.transcript-panel`, `.btn-end`, `.btn-send`, `.analyze-status`
      appears in `frontend/public/shared.css` and in no other sheet
      -> verify/checks/stylesheet_partition.py
      (amended per `QUESTION-TICKET-0064.md`: `.sidebar` measures zero
      surviving legacy consumers, not one as BRIEF-0064-a's M4 stated —
      routed to `creation.css` instead, per A1's own rule applied to the
      corrected count. `.btn-send` was not one of BRIEF-0064-a's ten named
      selectors -- rule7's own corrected coverage formula found it as a
      real, 24-file stranding; Nia's Decision 2 folded it into this
      ticket rather than a separate one, routed to `shared.css` per A1
      applied to its six measured legacy consumers)
- [x] `.layout`, `.sidebar` and `.right-col` appear in
      `frontend/public/creation.css` and in no other sheet
      -> verify/checks/stylesheet_partition.py
- [x] `.conv-item`, `.conv-item:hover`, `.conv-item.active`,
      `.conv-item .ci-id`, `.conv-item .ci-meta` and `.transcript-body` remain
      in `cockpit/index.html`'s inline `<style>`
      -> verify/checks/stylesheet_partition.py
- [x] Descendant rules travel with their moved parent: `.sidebar-head button`
      lands in `shared.css`, `.panel-head h2` lands in `shared.css`
      -> verify/checks/stylesheet_partition.py
- [x] rule2 still passes: no selector appears in more than one of
      `shared.css` / `creation.css` / inline
      -> verify/checks/stylesheet_partition.py
- [x] `rule7 (coverage)` exists in `stylesheet_partition.py`, is fail-closed,
      and is vacuous-proof: an empty extraction, a missing `frontend/src`, or
      an unparseable sheet FAILS rather than passing silently
      -> verify/checks/stylesheet_partition.py
      (amended per `QUESTION-TICKET-0064.md`'s follow-up / `BRIEF-0064-a`
      Amendment 2: `STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE −
      SCOPED(F)`, REACHABLE/SCOPED strict-base-rule matching, SCOPED
      per-file never unioned — a missing term in the original
      `APPLIED ∩ INLINE` formula, not an exemption)
- [x] `rule7` fails on a deliberately reintroduced stranding (one moved
      selector returned to the inline block) and passes once reverted —
      demonstrated, not asserted  -> verify/checks/stylesheet_partition.py
      (`.right-col` removed from `creation.css`, added to inline: rule7
      FAILs naming `right-col` + `Creation.svelte`; reverted, rule7
      passes)
- [x] `rule7` covers ids as well as classes (F2), demonstrated the same way
      -> verify/checks/stylesheet_partition.py
      (`#creation-shell-title` added to inline, applied by
      `Creation.svelte`, defined nowhere else: rule7 FAILs naming the id
      while rule2 passes; reverted)
- [x] `rule7`'s vacuity guards fire rather than pass silently (one shown,
      per BRIEF-0064-a's own scoping of that requirement)
      -> verify/checks/stylesheet_partition.py
      (`frontend/src` pointed at a non-existent path: rule7 FAILs "not a
      directory" rather than passing; reverted)
- [x] `rule7`'s REACHABLE/SCOPED matching is strict, not loose (Nia's
      Decision 1 correction) -> verify/checks/stylesheet_partition.py
      (`shared.css`'s base `.btn-send` rule temporarily weakened to
      `.some-parent .btn-send`: rule7 FAILs naming `btn-send` — a loose
      substring match would have wrongly PASSed; reverted)
- [x] `static/shared.css` and `static/creation.css` byte-match their
      `frontend/public/` sources (rule6 unbroken)
      -> verify/checks/stylesheet_partition.py
- [x] `npm run build` output is fresh; manifest hash matches
      -> verify/checks/frontend_build_fresh.py
- [x] No file under `src/world_engine/` outside
      `cockpit/index.html` and `cockpit/static/` is modified
      -> git diff review at close
- [x] Full verify suite green  ->  G1 gate

### Live  ->  human gate (Nia)

- [ ] Creation renders its two-column layout: a 300px sidebar left, content
      right, sidebar with panel background and right border.
- [ ] Creation's shell band, pending-creation strip and transcript panel each
      render with their panel background, border and padding — not as bare
      stacked text.
- [ ] The sidebar entity list scrolls independently of the right column; the
      page itself does not scroll.
- [ ] `.btn-end` buttons (Competences, discipline-details, goals, knowledge
      editors) render red-on-dark, not as default buttons.
- [ ] QueueFilters' analyze status line renders muted and on one line.
- [ ] Play is visually unchanged: sidebar, transcript panel, conversation list
      and chat messages identical to before this ticket.
- [ ] Observation is visually unchanged.
- [ ] No console error on cold load of `/creation`, `/play`, `/observation`.

## Notes

TICKET-0059 remains at `status: live-gate` with 0 of 32 criteria checked. This
ticket makes its Creation criteria testable; it does not discharge them.

## Escalations

### E-01 — archived — QUESTION-TICKET-0064.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0064.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0064
Trigger: D1-a
## Context
BRIEF-0064-a's mini-RECON (M4) states expected legacy-consumer counts for
the eight `shared.css`-bound selectors, measured on `main` @ `6185e3d`:

```
.app-view 2   .panel-head 3   .sidebar 1   .sidebar-head 1   .conv-list 1
.transcript-panel 1   .btn-end 1   .analyze-status 1
.layout 0   .right-col 0
```

`ticket/0064` was branched from `main` @ `6185e3d` (verified: `git rev-parse
HEAD~1` == `6185e3d`, the exact commit the brief cites — the tree has not
moved). Re-measuring M4 by scanning every `class="..."` attribute in
`src/world_engine/cockpit/index.html` after the `</style>` tag (line 511),
counting attributes whose token list contains each selector:

```
app-view 2   panel-head 3   sidebar 0   sidebar-head 1   conv-list 1
transcript-panel 1   btn-end 1   analyze-status 1
layout 0   right-col 0
```

Every count matches the brief except `.sidebar`: expected 1, measured 0.
I confirmed by direct search — no `class="sidebar"` (or `class="... sidebar
..."`) attribute exists anywhere in `cockpit/index.html`. The only markup
near the sidebar column (`#play-historique`, index.html:650) wraps
`.sidebar-head` and `.conv-list` directly; the outer `<div>` carries no
`sidebar` class at all — the legacy document never applied `.sidebar` to an
element, only its own bare `<div id="play-historique">`.

The brief's decision rule (A1, from the ticket) is: "the ten selectors are
redistributed by measured consumer count... Eight have ≥1 surviving legacy
consumer and go to `shared.css`; `.layout` and `.right-col` have zero and go
to `creation.css`." Applied literally to the actual (zero) count, `.sidebar`
belongs in `creation.css` alongside `.layout`/`.right-col`, not in
`shared.css` as BRIEF-0064-a's Scope IN 1.1 specifies. The brief itself
names this exact situation as its stop condition (M4): "If one of the other
eight is zero, STOP as well: that selector's destination changes and the
decision is Nia's, not yours." I have made no code changes; nothing has been
touched under Scope IN.

## Question
Should `.sidebar` move to `frontend/public/creation.css` (following A1's
measured-count rule literally, joining `.layout`/`.right-col`), or stay in
`frontend/public/shared.css` as BRIEF-0064-a's Scope IN 1.1 originally
specified (treating the brief's "1" as the intended destination regardless
of the miscount)?

## Options
- A. Route `.sidebar` to `creation.css` — mechanical application of A1's
  rule to the corrected count. `shared.css`'s new "Surface shell" banner
  (1.1) then carries eight rules, not nine; `creation.css`'s banner (1.2)
  carries three (`.layout`, `.right-col`, `.sidebar`).
- B. Keep `.sidebar` in `shared.css` per the brief's original plan —
  override the mechanical count for this one selector (e.g. if `.sidebar`
  is expected to gain a legacy consumer soon, or the miscount reflects
  brief-authoring intent rather than the A1 rule's actual purpose).
- C. Something else Nia specifies.

## Response
Halt was correct. M4 did its job — the mismatch is a defect in the brief,
not tree drift. Resolution: **A — route `.sidebar` to `creation.css`.**

## Root cause of the bad number

My measurement script counted legacy consumers with the pattern
`class="[^"]*\bsidebar\b`. `-` is a non-word character, so `\b` fires between
`sidebar` and `-head`: the count of 1 was a false match on
`class="sidebar-head"` at `index.html:651`.

Re-measured with exact whitespace-delimited token matching over every
`class="..."` attribute after `</style>` (markup and `<script>` template
strings), plus `classList.add/toggle/remove` literals. One cell of the M4
table was wrong. The other nine are confirmed correct.

## Corrected M4 table — replaces the one in BRIEF-0064-a

.app-view 2   .panel-head 3   .sidebar-head 1   .conv-list 1
.transcript-panel 1   .btn-end 1   .analyze-status 1
.layout 0   .right-col 0   .sidebar 0

Stop conditions are unchanged: any deviation from the above is a STOP.
`.layout`, `.right-col` and `.sidebar` at zero is now the justification for
routing all three to `creation.css`.

Corroborating fact, for your re-run: `#play-historique` (`index.html:650`) is
a bare `<div>` with an inline `style` attribute. The legacy document reuses
`.sidebar-head` and `.conv-list` as standalone rules inside a Play sub-tab.
No `.sidebar` container exists anywhere in that document.

## Amendments to Scope IN

**1.1** — the `Surface shell` banner in `frontend/public/shared.css` now
receives **eight** selectors, not nine. `.sidebar` is removed from that list.
Remaining, in order: `.app-view`, `.sidebar-head`, `.sidebar-head button`,
`.conv-list`, `.transcript-panel`, `.panel-head`, `.panel-head h2`,
`.analyze-status`. `.btn-end` still goes to the existing `Buttons` banner.

**1.2** — the `Creation two-column layout` banner in
`frontend/public/creation.css` now receives **three** rules. Order:
`.layout`, `.sidebar`, `.right-col` — grid container first, then its two
children in DOM order. Banner text is unchanged.

**1.4** — unchanged. The `Sidebar` banner in `cockpit/index.html` still
retains `.sidebar-head`, `.sidebar-head button`, `.conv-list` and the
`.conv-item*` family, so its comment stays. Only `Two-column layout`,
`Right column` and `App views` are deleted.

Everything else in the brief stands: Scope OUT, invariants, rule7's
specification, both negative demonstrations, docs to update.

## Amendments to Done means

Commit 1, first checkbox: `.sidebar` moves out of the shared.css list.
Commit 1, third checkbox: reads `.layout`, `.sidebar` and `.right-col` appear
in `frontend/public/creation.css`.

Add one checkbox to commit 1:

- [ ] `cockpit/index.html` renders Play's Historique sub-tab with no
      `.sidebar` rule available to it, and `.sidebar-head` / `.conv-list`
      still resolve from `shared.css`.

## Note on rule7

Rule7 as specified is immune to the error that caused this escalation. Its
extractor (§2.2) tokenises on whitespace and its inline parser (§2.3) captures
whole selector names, so neither can produce a prefix collision. Implement it
as written — do not introduce `\b`-style word-boundary matching anywhere in it.

## Next

Revert `status: escalated` to `exec`, append the resolution to
`QUESTION-TICKET-0064.md` rather than editing the question (history is
sacred), re-run M1–M8 against the corrected table, and proceed if clean.

## Follow-up (rule7 implementation, commit 2) -- appended, first Response untouched

rule7 is implemented exactly per BRIEF-0064-a Sec2.1-Sec2.7 (extractor,
inline-selector parser, STRANDED = APPLIED ∩ INLINE, five vacuity guards).
Running it on the tree after commit 1 (`73caa80`) surfaces 6 FAILs -- two
distinct findings, neither answerable from the brief as written, both hit
the brief's own stop clause: "If the implementation seems to need [an
exemption], the specification has been misread -- STOP and report rather
than introducing a list."

### Finding 1 -- rule7 false-positives on a component's own scoped <style>

`.local-badge`, `.mode-tab`, `.mode-tabs`, `.spacer`, `.sub` are applied by
`frontend/src/Header.svelte` AND survive in `cockpit/index.html`'s inline
block. But `Header.svelte` carries its OWN scoped `<style>` block
(`Header.svelte:55-90`) defining all five identically -- Svelte compiles
scoped CSS per-component, so these elements are already correctly styled
independent of the inline block. Cross-checked: `cockpit/index.html`'s own
(JS-suppressed but present) legacy header markup at lines 449-457 still
carries `class="sub"`, `class="spacer"`, `class="mode-tabs"`,
`class="mode-tab"` -- so the inline rules are NOT dead, they serve that
markup. This is a same-name collision across two independently-styled
surfaces, not a stranding: rule7's spec (Sec2.1-Sec2.4) has no clause for
"the applying component defines this selector in its own scoped <style>",
so it flags the collision anyway.

### Finding 2 -- .btn-send: a real, large-scale stranding outside Scope IN

`.btn-send`'s base declaration (`cockpit/index.html:324`, the visual
identity of every "primary action" button in Creation -- Générer,
Enregistrer, Créer, Commit, +Ajouter, etc.) exists ONLY in the inline
block. `frontend/public/creation.css` carries one compound override
(`.lieux-graph-head .btn-send { margin-left: auto; ... }`) but never the
base rule. `.btn-send` is applied across **24 distinct files** under
`frontend/src/creation/` (Competences, Region, RoomBatch, Prompts,
WorldCrud, DoorsEditor, GoalsEditor, KnowledgeEditor, ... every migrated
Creation island). All of them render inside the Svelte shell post
TICKET-0059, so none can reach the inline block. This is not one of
BRIEF-0064-a's ten named selectors and is an order of magnitude larger in
surface area than the ticket's whole known scope (ten selectors across
~4 files vs. one selector across 24 files).

## Response (follow-up)

Both findings correct, both are defects in BRIEF-0064-a, not in the
implementation. Resolution: **Decision 1 — a missing term, not an
exclusion** (`STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F)`,
`REACHABLE`/`SCOPED` strict base-rule matching, `SCOPED` per-file never
unioned, class/id namespaces kept separate). **Decision 2 — `.btn-send`
is in scope for TICKET-0064**, routed to `shared.css`'s `Buttons` banner
per A1 applied to its six measured Play consumers; `creation.css`'s
`.lieux-graph-head .btn-send` override untouched (rule2 confirmed to key
on full selector text, not bare names). Commits resequenced: commit 2
relocates `.btn-send`; commit 3 lands the corrected rule7 plus a third
negative demonstration proving strictness (weakening `shared.css`'s base
`.btn-send` rule to a compound must make rule7 FAIL). Added STOP
condition (satisfied): rule7 against the branch tip, pre-move, reported
exactly one stranded name, `btn-send`, across 24 files. Full resolution
text, including the corrected formula's derivation and the worked
example, recorded in `BRIEF-0064-a`'s own `## Amendment 2` (appended, the
original brief text untouched) and `ARCHITECTURE_DECISIONS.md`'s
"STYLESHEET COVERAGE" entry. Status reverts to `exec`; brief-exec
resumes.
~~~~
