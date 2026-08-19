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

