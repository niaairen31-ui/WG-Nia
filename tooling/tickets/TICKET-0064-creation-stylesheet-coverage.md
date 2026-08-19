---
id: TICKET-0064
title: Creation stylesheet coverage — stranded selectors and the missing partition rule
type: bug
status: exec
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
      `.transcript-panel`, `.btn-end`, `.analyze-status` appears in
      `frontend/public/shared.css` and in no other sheet
      -> verify/checks/stylesheet_partition.py
      (amended per `QUESTION-TICKET-0064.md`: `.sidebar` measures zero
      surviving legacy consumers, not one as BRIEF-0064-a's M4 stated —
      routed to `creation.css` instead, per A1's own rule applied to the
      corrected count)
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
- [ ] `rule7 (coverage)` exists in `stylesheet_partition.py`, is fail-closed,
      and is vacuous-proof: an empty extraction, a missing `frontend/src`, or
      an unparseable sheet FAILS rather than passing silently
      -> verify/checks/stylesheet_partition.py
- [ ] `rule7` fails on a deliberately reintroduced stranding (one moved
      selector returned to the inline block) and passes once reverted —
      demonstrated, not asserted  -> verify/checks/stylesheet_partition.py
- [ ] `rule7` covers ids as well as classes (F2), demonstrated the same way
      -> verify/checks/stylesheet_partition.py
- [x] `static/shared.css` and `static/creation.css` byte-match their
      `frontend/public/` sources (rule6 unbroken)
      -> verify/checks/stylesheet_partition.py
- [x] `npm run build` output is fresh; manifest hash matches
      -> verify/checks/frontend_build_fresh.py
- [ ] No file under `src/world_engine/` outside
      `cockpit/index.html` and `cockpit/static/` is modified
      -> git diff review at close
- [ ] Full verify suite green  ->  G1 gate

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
