---
id: TICKET-0063
title: Cockpit stylesheet partition — one shared sheet, two documents
type: feature
status: live-gate
created: 2026-08-06
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0063-a]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Escalation raised by Claude Code during BRIEF-0059-l reconnaissance:

"Creation's entire visual styling (buttons, cards, form fields, CSS custom
properties like `--border`/`--text`/`--muted`) lives in one ~1050-line
`<style>` block inside `index.html`, shared by Play/Observation/Creation
alike. Once Creation.svelte mounts directly in the shell (outside the legacy
iframe, per item 11's mount retirement), none of that CSS reaches it — the
shell's own `frontend/index.html` loads no stylesheet at all today."

Nia: "R1, S1, rédige le ticket et son brief, je les exécute dans une autre
session claude code avant de relancer la session sur le brief l."

## Clarifications resolved (intake)

**The finding is confirmed and is larger than reported.** Verified against
`main` this session: **no Creation island has a scoped `<style>` block at
all.** Several components document the constraint in their own headers —
`Registre.svelte`, `Artefacts.svelte` and `LocationTree.svelte` each carry a
variant of:

> No scoped `<style>` block: like every other Creation island, this renders
> inside the legacy iframe document, where Svelte's shell-injected scoped CSS
> never reaches.

Vite compiles component CSS into `static/assets/index-*.css`, linked from the
**shell** document (`static/index.html`). The islands mount into the
**iframe** document (`GET /legacy` -> `cockpit/index.html`). The only bridge
between the two is `hideLegacyHeader()` in `bridge.js`, which injects a single
`header { display: none !important; }` rule. Nothing else crosses.

So BRIEF-0059-l item 11 does not lose a fraction of Creation's styling. It
loses all of it, including the `:root` design tokens, and no check in the
tree would notice.

**S1 — its own ticket, executed before BRIEF-0059-l.**

It touches Play and Observation, which every brief in TICKET-0059 declares out
of scope (cross-cutting rule 2 scopes that ticket to the Creation surface). It
requires a rule-by-rule audit of a 1051-line stylesheet. And BRIEF-0059-l is
already the largest brief of that ticket — chrome inversion, world CRUD, the
modal seal, four check re-homings and the mount retirement across four
commits. Stacking a cross-surface stylesheet partition on top is the brief
that breaks.

Precedent: TICKET-0062 was inserted between BRIEF-0059-d and `-e` on the same
reasoning and it worked.

**R1 — one source of truth, two consumers, amended to three files.**

The stylesheet is `index.html:6-1056`, sectioned by banners. It partitions
three ways, with real overlap (Observation's `#obs-launch-panel` carries
`class="queue-panel"`, a class the Creation Review Queue also uses).

- **`shared.css`** — the layer both surviving documents need: reset, design
  tokens, base, header, mode tabs, buttons, badges, empty/info states,
  scrollbars, app views, queue panel. Linked by `frontend/index.html` and by
  `cockpit/index.html`, and deleted from the latter's inline `<style>`.
- **`creation.css`** — the Creation-only layer. Linked by **both** documents
  for now; BRIEF-0059-l removes the legacy `<link>` and nothing else.
- **`cockpit/index.html`'s `<style>`** — keeps Play-only rules until
  TICKET-0060/0061.

**Amendment to R1 as originally proposed: no migration to scoped component
`<style>` blocks in this ticket.** The original proposal had Creation-specific
rules descend into the components. That cannot happen here: this ticket runs
*before* BRIEF-0059-l, so Creation is still inside the iframe, and a scoped
style would stop reaching it the day it was written. The `creation.css`
intermediate avoids the timing hazard entirely and reduces BRIEF-0059-l's CSS
work to one deleted `<link>` tag.

Recorded as named deferral **D-0063-scoped-component-styles**: moving
`creation.css`'s rules into per-component scoped `<style>` blocks. Reactivate
after TICKET-0061, when no document outside the shell consumes them.

Rejected: duplicating the design tokens across both documents and
reconciling at TICKET-0061 (R2). It is two copies of the most cross-cutting
layer in the product, live for two tickets, in a codebase whose stated axiom
is that one thing should be one thing.

Rejected: per-component scoped styles only (R3). Custom properties are not
scopable and would be redeclared everywhere.

**Asset naming: unhashed, via `publicDir`.** `static/assets/index-*.css` is
content-hashed, so a `<link>` in `cockpit/index.html` would break on every
rebuild. The two new sheets live in `frontend/public/` and Vite copies them
verbatim to `static/`, unhashed, referenced by absolute path
`/static/shared.css`. They are plain CSS and need no bundler processing.

**Cascade order is made moot by the check, not by luck.** Moving sections
into two external sheets changes their relative order (e.g. Badges, a shared
section, currently sits after Mutation card, a Creation section). Rather than
reasoning about it, `stylesheet_partition.py` forbids any selector from
appearing in more than one of the three destinations. If no selector appears
twice, load order cannot decide a conflict. Remaining same-specificity
collisions between *different* selectors on one element are caught by the
live visual gate.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `stylesheet_partition.py` exists, is fail-closed, with its vacuity
      guard on the SCAN (missing file, empty file, or unparsed `<style>`
      block -> FAIL)  ->  verify/checks/stylesheet_partition.py
- [ ] No selector appears in more than one of `shared.css`, `creation.css`
      and `cockpit/index.html`'s inline `<style>`  ->
      verify/checks/stylesheet_partition.py
- [ ] No `:root` custom-property block remains in `cockpit/index.html`  ->
      verify/checks/stylesheet_partition.py
- [ ] Both documents carry the exact `shared.css` `<link>`  ->
      verify/checks/stylesheet_partition.py
- [ ] `cockpit/index.html` links `creation.css` **iff** `LEGACY_MOUNTS`
      declares `creation` — the link's lifetime is tied to the mount's, not
      to a comment  ->  verify/checks/stylesheet_partition.py
- [ ] `static/shared.css` and `static/creation.css` exist and byte-match
      their sources under `frontend/public/`  ->
      verify/checks/stylesheet_partition.py
- [ ] `npm run build` output is fresh  ->  verify/checks/frontend_build_fresh.py
- [ ] `python tooling/verify/run.py` exits 0

### Live  ->  human gate (Nia)

- [ ] Play renders pixel-identically: transcript, chat messages, MJ
      narration, scene state, scene view, spatiale canvas, proximity
      affordance, start-conversation panel, play input.
- [ ] Observation renders pixel-identically, including `#obs-launch-panel`'s
      `queue-panel` chrome and the observed-proposals list.
- [ ] Every Creation sub-tab renders pixel-identically — all fourteen,
      plus a runtime entity type's tab.
- [ ] The Review Queue's mutation cards, badges, apply-error block and
      duplicate-risk banner are unchanged.
- [ ] Both agent panels, the relation graph, the lieux graph and the region
      review tree are unchanged.
- [ ] `Modal.svelte`'s dialogs (competences delete, location type) render
      unchanged.
- [ ] The shell header and mode tabs are unchanged.
- [ ] A hard reload with cache disabled produces the same result — no rule
      is surviving only from a cached hashed bundle.
