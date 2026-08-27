# BRIEF — Step "stylesheet partition"

Ticket: TICKET-0063. Single brief. **Executes before BRIEF-0059-l.** Locks:
**R1 (amended to three files), S1**.

**Anchor convention.** Every line number below is indicative, read from a
tarball of `main` this session. Your working tree may be ahead of it. Locate
by section banner text; verify every range locally before cutting.

## Context

`cockpit/index.html` carries one `<style>` block, indicatively lines 6-1056,
sectioned by `/* ── Name ── */` banners. It styles all three surfaces.

The shell document (`static/index.html`, built from `frontend/index.html`)
loads only Vite's hashed bundle. The Creation islands mount into the **iframe**
document, so the bundle's scoped CSS never reaches them — which is why no
Creation component has a `<style>` block, a constraint several of them
document in their own headers. Everything Creation looks like today comes from
`index.html`'s inline stylesheet.

BRIEF-0059-l item 11 moves Creation out of that iframe. Without this ticket,
Creation loses its entire visual layer — tokens included — and no check
notices.

This brief is a **pure extraction**. Nothing should look different anywhere
when it lands. That is the whole acceptance standard.

## Scope IN

### Step 0 — the audit (no code change, no commit)

1. Produce `tooling/briefs/RECON-0063-a-selector-audit.md`. For **every**
   section banner in `index.html`'s `<style>`, record: its line range, and
   which of the three surfaces actually consumes its selectors, established
   by grepping each selector's class or id across `index.html`'s markup,
   `frontend/src/**`, and the built `static/index.html`.

   The starting partition below is a hypothesis from a planning RECON. Confirm
   or correct each line.

   **-> `shared.css`:** Reset (~7), Design tokens (~11), Base (~27), Header
   (~38), Queue panel (~240), Badges (~400), Buttons (~447), Empty / info
   states (~516), Scrollbars (~523), Mode tabs (~771), App views (~916).

   **-> `creation.css`:** Batch review (~270), Mutation card (~297),
   Apply-error block (~489), Author view (~785), Lieux hierarchy browse
   (~848), Création sub-tab bar (~955), Création content areas (~968),
   Région review tree (~980), Lieux graph panel (~986), NPC relation
   ego-graph panel (~988), NPC link agent + group agent panels (~999),
   Generic modal (~1024), Region full-sheet (~1046).

   **-> stays inline (Play):** Two-column layout (~59), Sidebar (~68), Right
   column (~106), Transcript panel (~113), Chat messages (~143), Scene state
   panel (~211), Play input (~528), Scene view (~554), Start-conversation
   panel (~731), Play view header (~919), Play sub-panes (~935), Play
   spatiale (~940), Proximity affordance (~948).

2. **Three specific hazards to settle, each with a yes/no answer:**

   - **Queue panel.** `#obs-launch-panel` carries `class="queue-panel"`, so
     the section is claimed shared. Confirm, and check whether Observation
     also consumes Batch review, Mutation card, Apply-error or Badges
     selectors — `_obsLoadProposals` renders a proposals list and may reuse
     the card chrome. **If Observation consumes any section listed for
     `creation.css`, that section moves to `shared.css` instead**, and say so.
   - **Generic modal.** Listed for `creation.css` on the assumption its only
     consumers are Creation's world CRUD and `Modal.svelte`. Confirm no
     Play or Observation markup uses `.modal-backdrop` / `.modal-close`.
   - **Sections spanning two concerns.** A banner's range may contain rules
     for more than one surface. Where that happens, **split the section**,
     recording both halves; do not send a mixed section wholesale to one
     destination.

3. **STOP and escalate, changing nothing, if:** a selector is consumed by all
   three surfaces *and* one of them overrides it (a genuine three-way
   dependency needing a cascade decision), or a section resists a clean split.

### Commit 1 — extract `shared.css`

4. Create `frontend/public/shared.css` with a header comment, verbatim:

   > TICKET-0063 (BRIEF-0063-a). The layer the shell document and the legacy
   > document BOTH need. Moved, not copied, out of cockpit/index.html's
   > inline <style>: stylesheet_partition.py forbids any selector from
   > appearing in more than one of shared.css, creation.css and that inline
   > block, so there is exactly one definition of every rule and load order
   > cannot decide a conflict. Plain CSS in publicDir, copied unhashed by
   > Vite, because cockpit/index.html cannot link a content-hashed asset.

   Move — **cut, never copy** — every section the audit assigns to it,
   preserving each section's banner and its internal order.

5. Add to **both** documents, as the first stylesheet reference in `<head>`:

   ```html
   <link rel="stylesheet" href="/static/shared.css">
   ```

   Absolute path in both, so Vite does not rewrite it against `base:
   '/static/'`.

6. **Verify the dev server serves it.** Vite's dev server serves `publicDir`
   at `/`, not at `/static/`, so `/static/shared.css` may 404 in dev even
   though it resolves in prod through the `StaticFiles` mount at
   `app.py`'s `_STATIC_DIR`. Check whether a dev workflow exists in
   `frontend/scripts/` or `package.json` and whether this breaks it. If it
   does, report the breakage and the option you took; **do not silently make
   prod worse to keep dev working.**

### Commit 2 — extract `creation.css`

7. Create `frontend/public/creation.css` the same way, with a header comment,
   verbatim:

   > TICKET-0063 (BRIEF-0063-a). Creation-only rules, extracted from
   > cockpit/index.html so that BRIEF-0059-l's mount retirement does not
   > take Creation's entire visual layer with it. Linked by BOTH documents
   > while Creation still renders inside the legacy iframe; BRIEF-0059-l
   > removes the legacy <link> and nothing else. These rules are NOT moved
   > into per-component scoped <style> blocks: that would stop them reaching
   > the iframe the day it was written. Named deferral
   > D-0063-scoped-component-styles, reactivate after TICKET-0061.

8. Link it from **both** documents, after `shared.css`.

### Commit 3 — the guard

9. Create `tooling/verify/checks/stylesheet_partition.py`, following the
   project idiom: module-level `FAILURES`, `fail()`, `_report_and_exit()`,
   `ROOT` via `parents[3]`.

   - **rule1 (scan is real).** `frontend/public/shared.css`,
     `frontend/public/creation.css` and `cockpit/index.html` all exist; the
     two sheets are non-empty; the inline `<style>` block parses and is
     non-empty. Any failure -> FAIL, "vacuous scan".
   - **rule2 (no duplicate selectors).** Extract top-level selectors from all
     three sources. A selector appearing in more than one -> FAIL, naming the
     selector and both locations. This is the rule that makes load order
     irrelevant.
   - **rule3 (tokens moved, not copied).** No `:root { ... }` custom-property
     block in `cockpit/index.html`. Design tokens exist once, in
     `shared.css`.
   - **rule4 (both documents link shared).** `frontend/index.html` and
     `cockpit/index.html` each contain the exact
     `<link rel="stylesheet" href="/static/shared.css">`.
   - **rule5 (creation link tracks the mount).** `cockpit/index.html` links
     `/static/creation.css` **if and only if** `frontend/src/legacy/registry.js`'s
     `LEGACY_MOUNTS` declares `creation`. Both directions FAIL. This is what
     makes BRIEF-0059-l's single deleted `<link>` structurally required
     rather than remembered.
   - **rule6 (built copies are fresh).** `static/shared.css` and
     `static/creation.css` exist and byte-match their `frontend/public/`
     sources. **No line-ending normalisation** — a byte comparison that
     normalises is fail-open, and `.gitattributes` already governs EOLs here.

10. Register the check in `tooling/verify/run.py`.

## Scope OUT

- **Any visual change.** Not one colour, radius, spacing value or media
  query. If a rule looks wrong, REPORT it; a stylesheet extraction is not
  the place to fix CSS.
- **Moving anything into per-component scoped `<style>` blocks.** Item 7's
  comment states why. D-0063-scoped-component-styles.
- **Deleting the `creation.css` `<link>` from `cockpit/index.html`.**
  BRIEF-0059-l, gated by rule5.
- **Splitting Play's rules into a third file.** Play still lives in
  `index.html` and has one consumer. A `play.css` would be structure without
  a reader (E2). TICKET-0060/0061.
- **Touching Play or Observation markup, JS, or checks.** This brief moves
  their *rules* between files and changes nothing they do.
- **Consolidating near-duplicate rules found during the audit** (two
  selectors doing the same thing, dead rules for removed markup). REPORT
  them; a cleanup mixed into an extraction makes the visual gate
  unattributable.
- **Bundling the two sheets through Vite's asset pipeline.** They are plain
  CSS in `publicDir` precisely so they stay unhashed.
- **Adding a cache-busting query string.** Report the caching behaviour of
  the `StaticFiles` mount if it looks like a problem; do not invent a
  versioning scheme here.
- **Any backend change**, including the `StaticFiles` mount. It already
  serves `_STATIC_DIR`; `publicDir` output lands inside it.

## Invariants to defend

- **One thing is one thing.** rule2 is the ticket's whole point: after this
  brief, every CSS rule in the cockpit has exactly one definition, and the
  two documents share it rather than each holding a copy.
- **Fail-closed and vacuous-proof.** rule1 guards the scan. A check that
  parses nothing must fail, not pass.
- **Structural over disciplinary.** rule5 ties the `creation.css` link's
  lifetime to `LEGACY_MOUNTS`, so BRIEF-0059-l cannot retire the mount
  without removing the link, and cannot remove the link early.
- **Byte-level comparison, unnormalised.** rule6. Line-ending normalisation
  in a freshness check is structurally unsound; `.gitattributes` already
  covers `frontend/**` and `cockpit/static/**`.
- **Moved, never copied.** Items 4 and 7. A section that ends up in two
  places has failed the ticket even if it renders correctly.
- **No behaviour change.** The live gate is a pixel comparison across all
  three surfaces.

## Done means

- [ ] `tooling/briefs/RECON-0063-a-selector-audit.md` exists, covers every
      section banner, and answers all three Step-0 hazards with a yes/no.
- [ ] `python tooling/verify/checks/stylesheet_partition.py` exits 0.
- [ ] Scratch A: copy one selector from `shared.css` back into
      `cockpit/index.html`'s `<style>`; exits non-zero naming rule2 and both
      locations; revert.
- [ ] Scratch B: restore a `:root` block to `cockpit/index.html`; exits
      non-zero naming rule3; revert.
- [ ] Scratch C: remove `creation` from `LEGACY_MOUNTS` while the legacy
      `creation.css` link is still present; exits non-zero naming rule5;
      restore. Then remove the link while `creation` is still declared;
      exits non-zero naming rule5; restore.
- [ ] Scratch D: edit `frontend/public/shared.css` without rebuilding; exits
      non-zero naming rule6; rebuild.
- [ ] Scratch E: empty `frontend/public/creation.css`; exits non-zero naming
      rule1, never 0; restore.
- [ ] `cockpit/index.html`'s `<style>` block contains only Play sections;
      report its new line count against the previous 1051.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] Live, with cache disabled, compared against `main` before this brief:
      Play renders identically — transcript, chat messages, MJ narration,
      initiative narration, NPC raw annotation, verdict annotation, scene
      state, scene view, spatiale canvas, proximity affordance,
      start-conversation panel, play input.
- [ ] Live: Observation renders identically, including `#obs-launch-panel`
      and the observed-proposals list.
- [ ] Live: all fourteen Creation sub-tabs render identically, plus one
      runtime entity type's tab.
- [ ] Live: mutation cards, badges, apply-error block and duplicate-risk
      banner unchanged; the green healthy-empty state still green.
- [ ] Live: both agent panels, relation graph, lieux graph, region review
      tree, region full-sheet unchanged.
- [ ] Live: `Modal.svelte`'s dialogs unchanged.
- [ ] Live: shell header and mode tabs unchanged.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

`ARCHITECTURE_DECISIONS.md` gains one TICKET-0063 entry: the partition, why
the shared layer is moved rather than duplicated, why the two sheets are
unhashed `publicDir` assets, and why rule5 binds the `creation.css` link to
`LEGACY_MOUNTS`. Record **D-0063-scoped-component-styles** with its
reactivation condition (after TICKET-0061, when no document outside the shell
consumes those rules).

`CLAUDE.md` gains `stylesheet_partition.py` in its check inventory if that
inventory enumerates checks by name, and nothing else — 500-line budget,
law only.
