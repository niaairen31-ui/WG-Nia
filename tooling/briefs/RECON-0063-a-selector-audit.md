<!-- slug: cockpit-stylesheet-partition-audit -->
# RECON-0063-a — selector audit

Read against `cockpit/index.html`'s `<style>` block (lines 6-1056, confirmed
range matches the brief's anchor) on `ticket/0063` at the time of this audit.
Method: for every section banner, grepped its selectors (classes/ids) across
`cockpit/index.html`'s own body markup, `frontend/src/**`, and
`frontend/index.html`/`App.svelte`/`Header.svelte`/`LegacyFrame.svelte`
(the shell's current hand-written chrome). No code changed in this step.

## Governing test (used to resolve every section, not just the hypothesis)

`shared.css` is not "whatever isn't obviously Creation." It is: **would
`frontend/index.html`'s document — either its existing shell chrome, or a
Creation island's own generated markup, which will render inside that
document once BRIEF-0059-l lands — break or look different without this
rule?** Two classes of selector pass that test:

1. Rules a Creation island's generated markup (or something it inherits
   from) references directly — buttons, badges, queue-panel, form fields,
   design tokens, the foundational reset/font cascade.
2. Rules needed by *any* content reachable regardless of which of the three
   surfaces is active — see the Generic modal correction below.

Selectors that exist **only** inside `cockpit/index.html`'s own hand-written
body chrome (its `<header>`, its `.mode-tabs`, its `.app-view` wrapper divs)
and are never referenced by an island's own markup fail this test even
though they're "not Creation." The shell already has its own independent
replacement for that chrome (`Header.svelte`, `App.svelte`, `LegacyFrame.svelte`)
— fully scoped, fully independent, in `Header.svelte`'s case not even
sharing the same color values. `frontend/index.html` will never delegate
that job to these legacy rules, on any timeline.

## Corrections to the planning hypothesis

**1. Header (~38) and Mode tabs (~771): shared.css → stays inline.**
`frontend/src/Header.svelte` has its own complete scoped `<style>` block
(lines 54-97) reimplementing `header`, `.mode-tabs`, `.mode-tab`,
`.local-badge` — with independent, hardcoded hex colors, not even the
shared `var(--*)` tokens. `App.svelte`'s own `<style>` supplies
`--header-height` locally. No Creation island renders a `<header>` or
`.mode-tab` element. `frontend/index.html` has zero dependency on these two
sections, today or on any future timeline — the shell's header is
permanently a different implementation. Both stay in `cockpit/index.html`'s
inline `<style>`.

**2. App views (~916, `.app-view`): shared.css → stays inline.** Applied
only to `cockpit/index.html`'s own `#play-view` / `#creation-view` /
`#observation-view` wrapper divs. No Creation island applies `.app-view` to
its own root — islands mount *into* these containers, they don't *become*
one. Same reasoning as #1.

**3. Generic modal (~1024): creation.css → shared.css.** The brief's hazard
question asked to confirm no Play/Observation *markup* uses
`.modal-backdrop`/`.modal-close` — true taken literally, but the wrong
question. `Header.svelte`'s "+ Monde" / "🗑 Monde" buttons (visible on
**every** surface, not Creation-scoped — they're shell-header-level) call
`openWorldCreate`/`openWorldDelete` (`frontend/src/legacy/bridge.js:45-50`),
which call `worldCreateOpen`/`worldDeleteOpen` **in the legacy document**
(`cockpit/index.html:5778,5872`) — both call `genericModalOpen`, which
renders into `#generic-modal-backdrop`. That element sits at the legacy
document's `<body>` level (`cockpit/index.html:6280`, after `</script>`,
outside all three `.app-view` divs), `position: fixed; inset: 0`. It
overlays whichever `.app-view` is currently visible — **the world
create/delete modal is reachable, and must render correctly, while Play or
Observation is the active surface.** Leaving `.modal-backdrop` et al. in
creation.css would work today (creation.css is linked from both documents
"for now"), but BRIEF-0059-l removes creation.css's `<link>` from
`cockpit/index.html` (Scope OUT of this brief, gated by rule5) — the day
that lands, the world create/delete modal would render unstyled every time
it's opened from Play or Observation, since `cockpit/index.html` never
stops hosting those two. Moving Generic modal to shared.css (linked
unconditionally, forever, per rule4) is the only placement that stays
correct after -l. `Modal.svelte` (a real Creation island, confirmed
consumer via its own `.modal-backdrop` usage) is unaffected — shared.css is
linked in `frontend/index.html` unconditionally too.

No other section required a split or hit the three-way-override STOP
condition (brief item 2, third bullet). No genuine conflicting redefinition
was found anywhere in the block.

## Hazards (brief item 2), resolved

- **Queue panel — YES, shared.css.** Confirmed both ways: `#obs-launch-panel`
  (Observation's own legacy markup, `cockpit/index.html:1448`) carries
  `class="queue-panel"`, **and**, independently, four Creation islands
  render `class="queue-panel"` on their own root
  (`Competences.svelte:115`, `ConversationWindowConfig.svelte:61`,
  `Registre.svelte:138`, `Prompts.svelte:206`). Checked whether Observation
  additionally consumes Batch review / Mutation card / Apply-error /
  Badges: **no** — `_obsLoadProposals` (`cockpit/index.html:6254-6270`)
  renders its proposal rows with inline `style="..."`, `.badge b-*`
  (Badges — already shared) and `.target-ref` (Badges section's trailing
  rule, already shared); it renders no `.card`, `.batch-*`, `.card-apply-error`
  or `.card-dup-warn` element. Those four sections stay creation.css
  unchanged.
- **Generic modal — corrected to shared.css**, reasoning above (not the
  yes/no the brief anticipated; the literal question's answer is "no
  Play/Observation *view* markup uses it," but the selector is still
  reachable from every surface via the shell header, which changes the
  placement).

## Final partition (by banner)

**→ `shared.css`**
Reset (7-9) · Design tokens / `:root` (11-25) · Base (27-36) · Queue panel
(240-268) · Badges (400-445, all subsections: mutation_type, world-tick,
status, conversation, item-equip, event.knowledge_status,
observation_beat.outcome, `.target-ref`) · Buttons (447-487) · Empty / info
states (516-521) · Scrollbars (523-526) · Mode tabs — see correction #1,
**excluded**, stays inline · App views — see correction #2, **excluded**,
stays inline · **Generic modal (1024-1044)** — see correction #3, moved here
from the creation.css hypothesis.

**→ `creation.css`**
Batch review (270-295) · Mutation card (297-398) · Apply-error block
(489-514) · Author view (785-846, includes two dead rules noted below) ·
Lieux hierarchy browse (848-914) · Création sub-tab bar (955-966) ·
Création content areas (968-978) · Région review tree (980-984) · Lieux
graph panel (986-1022, includes the NPC link/group agent block) · Region
full-sheet (1046-1055).

**→ stays inline (`cockpit/index.html`, Play + legacy chrome)**
Header (38-57) · Two-column layout (59-66) · Sidebar (68-104) · Right
column (106-111) · Transcript panel (113-141) · Chat messages (143-209) ·
Scene state panel (211-238) · Play input (528-720) · Scene view (554-720,
overlapping the Play input banner range — both are Play-exclusive, no split
needed since both land in the same bucket) · Start-conversation panel
(731-769) · Mode tabs (771-783) · Play view header (919-933) · Play
sub-panes (935-938) · Play spatiale (940-947) · Proximity affordance
(948-953) · App views (916-917).

## Notes (reported, not fixed — Scope OUT)

- **Dead CSS:** `.author-type-tabs` (786-792) and `.author-new-row`
  (793-799) have zero markup consumers anywhere in `cockpit/index.html` or
  `frontend/src/**`. Moved verbatim into `creation.css` with the rest of
  Author view; not deleted, per Scope OUT ("dead rules for removed markup
  — REPORT them").
- **Pre-existing undefined token:** `.scene-gathering-card` (line ~601)
  reads `var(--surface)`, which is not declared anywhere in the `:root`
  block (`--bg`, `--panel`, `--card`, `--border`, `--text`, `--muted`,
  `--accent`, `--green`, `--yellow`, `--red`, `--radius`, `--mono` only).
  Pre-existing, not introduced by this move, not fixed here.
- `Header.svelte` duplicates `.local-badge` under its own scoped styling
  with different (hardcoded) colors than the shared `.local-badge` this
  ticket keeps inline in `cockpit/index.html`. Two independent
  implementations of one visual idea; not this ticket's job to reconcile
  (Scope OUT: no consolidation of near-duplicates).
