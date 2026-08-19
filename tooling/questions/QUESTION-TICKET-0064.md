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

