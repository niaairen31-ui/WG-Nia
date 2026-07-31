# BRIEF — Step "doctrine entry + CLAUDE.md amendment + launch docs"

## MINI-RECON — run before executing this brief

Report-only. Confirm empirically; on any failure STOP and escalate.

```bash
git log --oneline -4                       # BRIEF-0056-c is the tip
wc -l CLAUDE.md                            # budget headroom against the 500 hard cap
grep -n "Frontend: vanilla-JS single-page" -A 1 CLAUDE.md
grep -n "The frontend is mid-migration" CLAUDE.md
grep -n "index.html       # legacy single-page UI" CLAUDE.md
awk '/^### File structure/{f=1;n=0} f{n++} f&&/^### /&&n>1{print "File-structure section lines:", n-1; exit}' CLAUDE.md
tail -5 tooling/standards/DECISIONS_INDEX.md
python tooling/verify/checks/claude_md_contract.py
python tooling/verify/checks/decisions_index.py
```

Assertions that must hold:

1. `CLAUDE.md` is at **494** lines against `claude_md_contract.py`'s hard cap
   of 500 — i.e. **6 lines of headroom, and no more**. If the count differs,
   recompute the headroom before editing; if it is at 500, the amendment MUST
   be net-zero or net-negative and any addition must be paid for by a deletion
   in the same edit.
2. The three target lines exist as described (frontend stack law, the
   mid-migration sentence, the file-tree `index.html` line).
3. The `### File structure` section is within its 80-line budget before the
   edit.
4. Both checks are green before any edit.

## Context

TICKET-0056 is functionally complete: the shell owns `/`, the legacy cockpit is
one governed iframe entry in a shrinking registry, and routing is enumerated on
both sides. The doctrine still describes the pre-0056 world. This step writes
it once, against the finished shape, rather than four times as the briefs
landed.

## Scope IN

1. **`tooling/standards/ARCHITECTURE_DECISIONS.md` — one new entry, appended
   before the closing `*Co-built with Claude, June 2026.*` line.** The header
   must satisfy `decisions_index.py`'s strict pattern verbatim:

   ```
   ## COCKPIT SHELL — legacy-mount registry, iframe boundary, enumerated routing (BRIEF-0056-a, BRIEF-0056-b, BRIEF-0056-c, BRIEF-0056-d, no schema change)
   ```

   Body, in the house style (bolded lead, then the reasoning), covering exactly
   these points and no others:

   - **The registry is three entries, not one (A2).** Why a single "monolith"
     entry cannot discharge TICKET-0055's deferral: it vanishes rather than
     shrinks, so the count stops being a measurable gate. `creation` is retired
     by TICKET-0059, `observation` by TICKET-0060, `play` survives to
     TICKET-0061 and beyond, until its own rewrite.
   - **One iframe, and `index.html` byte-untouched (B1).** The three views are
     `display:none` siblings over one global scope; "load only Play's JS" is
     not constructible. The iframe isolates JS and CSS by construction, so 319
     inline handlers and 175 globals keep working with zero edits and the nine
     index-anchored checks stay green by non-event. B2 (same-document
     injection) rejected: it would merge 175 globals and 1039 lines of unscoped
     CSS into the new surface.
   - **No `postMessage`: same-origin direct invocation, confined.** Why
     confinement is a check (`legacy_mount.py` assertion 5) and not a
     convention.
   - **The history trap, and why the frame `src` is written once.** An iframe
     navigation pushes onto the PARENT history stack; reassigning `src` to
     switch surfaces would make Back replay legacy boots. Enforced by
     assertion 6, not by memory.
   - **C3: the server stays the authority.** The shell delegates the whole
     switch cascade to the legacy `activateWorld()` rather than re-POSTing, and
     mirrors `/api/bootstrap` afterwards. Named contrast: the legacy
     `loadBootstrap()` swallows every error; the mirror refuses visibly.
   - **D3b and the death of the catch-all.** The measured fact that decides it:
     the 151 API route literals do not carry `/api` in their text
     (`crud/_router.py` declares the prefix at mount time), so a catch-all's
     exclusion list is a convention with a silent failure mode. D2 (hash) is
     fail-open in the other direction. Enumeration makes both a surface typo
     and an API typo real 404s.
   - **The server never learns the tab vocabulary (D-ii).** `{sub_tab}` is
     opaque server-side and resolved against `CREATION_TABS` client-side, so a
     runtime entity type is deep-linkable with no server change — the same
     rule `page_contract` already enforces on the tab mechanism. The `'npc'`
     fallback is reused from `activateWorld`, not invented.
   - **The URL is authoritative on entry, not continuously synchronized**, and
     why: continuous sync would require the legacy document to call out to the
     shell, i.e. an edit to `index.html`. Deferred to TICKET-0058 with the
     Creation surface itself. **Named deferral, logged here.**
   - **G1: no check re-homed.** Nothing structural moved. Names
     `relation_graph.py`'s Lieux-graph byte-equality assertion against `main`
     as a live gate the next editor of those functions will meet.
   - **Two records corrected.** (i) The map's "Play preserved as an HTMX
     island" is wrong — no HTMX ever existed, already established at
     TICKET-0055; Play is a vanilla-JS island. (ii) The 3D guard-rail is NOT
     restated here: TICKET-0055's entry already re-nailed it, and restating
     doctrine is how doctrine drifts. Cross-reference only.
   - **Renaming `index.html` is deferred to TICKET-0061** (three files now
     share the name); the rename touches all nine index-anchored checks, which
     that ticket retires anyway. **Named deferral, logged here.**

2. **Regenerate `DECISIONS_INDEX.md`**: `python tooling/glue/gen_decisions_index.py`.
   Do not hand-edit it.

3. **`CLAUDE.md` — three surgical amendments, net line change ≤ +6 (measure
   before and after; if the file was at 500, net ≤ 0).** Law only: no
   narrative, no `BRIEF-` tokens inside the `### File structure` section
   (archaeology ban), every `tooling/...` path mentioned must exist.

   - The frontend stack line: state the current law — the shell (built Svelte
     under `frontend/`) serves `/`; the legacy vanilla-JS document is served at
     `/legacy` and hosted in one governed iframe; no new dependency without a
     decision.
   - The mid-migration sentence: replace the "`index.html` is the legacy
     surface, `frontend/` is the built app" clause with the registry law —
     legacy surfaces are an enumerated, monotonically shrinking registry
     (`frontend/src/legacy/registry.js`), legacy access is confined to
     `frontend/src/legacy/bridge.js`, the shell route vocabulary is mirrored in
     `app.py` and `router.js`, all enforced fail-closed by
     `tooling/verify/checks/legacy_mount.py`. Play stays vanilla-JS until its
     own rewrite. Keep the existing pointer to `ARCHITECTURE_DECISIONS.md`.
   - The file-tree line for `index.html`: mark it as served at `/legacy` and
     hosted in the shell's iframe. Add `frontend/src/legacy/` to the tree ONLY
     if the File-structure section stays within its 80-line budget; if it does
     not, leave the tree unchanged and say so in the report.

4. **`docs/launch-procedure.md`** — add to the "Frontend build" section that
   after launch `http://127.0.0.1:8000/` serves the shell and
   `http://127.0.0.1:8000/legacy` serves the legacy cockpit directly (escape
   hatch). Two sentences; the prod block itself is unchanged and still needs no
   Node.

5. **`Active_project.md` — REPORT ONLY.** It is Nia's local workstream map, not
   a repo file. Produce, in the step report, the exact replacement text for
   TICKET-0056's entry: strike "HTMX island" (Play is vanilla-JS), strike
   "Reaffirm the 3D coordinate guard-rail" (done at TICKET-0055), and mark the
   four open decisions D-A..D-D as resolved with the locked codes
   `A2, B1, C3, D3b, D-i(1), D-ii, E1, F3, G1`. Do not attempt to edit any file
   outside the repo.

## Scope OUT

- **Any code change.** No `frontend/`, no `app.py`, no check edits. If a
  doctrine sentence cannot be written truthfully about the code as it stands,
  that is an escalation — never a small code adjustment to make the sentence
  true.
- **Restating the 3D guard-rail.** Cross-reference TICKET-0055's entry.
- **Rewriting or shortening `CLAUDE.md`'s `## Invariants` section.** It is 202
  lines / 40% of the file and warrants its own governance ticket (recorded at
  TICKET-0055); it is not a rider here.
- **Hand-editing `DECISIONS_INDEX.md`.**
- **Renaming `index.html`.** TICKET-0061.
- **Writing anything about TICKET-0057's graph primitive**, including
  "preparatory" doctrine about graphs. That ticket owns its own vocabulary.
- **A CLAUDE.md entry for the `/creation/{sub_tab}` URL contract** beyond the
  law above — the detail lives in `ARCHITECTURE_DECISIONS.md`.

## Invariants to defend

- **CLAUDE.md is law-only and budgeted.** Narrative goes down into
  `ARCHITECTURE_DECISIONS.md`; the 500-line cap is hard and there are 6 lines
  of headroom.
- **Deferrals are named, never dropped** — two are logged here (continuous URL
  sync -> TICKET-0058; `index.html` rename -> TICKET-0061).
- **Doctrine is written once.** Restating an existing invariant in a second
  place is how it drifts.

## Done means

- [ ] `python tooling/verify/checks/decisions_index.py` green (index matches
      archive; the new header passes the strict pattern).
- [ ] `python tooling/verify/checks/claude_md_contract.py` green.
- [ ] `wc -l CLAUDE.md` reported before and after, with the net delta stated
      and ≤ +6 (≤ 0 if the file was at 500).
- [ ] `git diff` for this brief touches ONLY `CLAUDE.md`,
      `tooling/standards/ARCHITECTURE_DECISIONS.md`,
      `tooling/standards/DECISIONS_INDEX.md`, `docs/launch-procedure.md`.
- [ ] `python -m tooling.verify.run --ticket TICKET-0056-cockpit-shell-surface-boundary`
      is GREEN across every criterion in the ticket's Machine section.
- [ ] The step report contains the verbatim replacement text for
      `Active_project.md`'s TICKET-0056 entry.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

This step IS the doc update.
