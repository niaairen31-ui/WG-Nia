---
id: TICKET-0055
title: Frontend build + serving foundation (Svelte/Vite toolchain, static mount, build-freshness gate)
type: feature
status: exec
created: 2026-07-30
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0055-a, BRIEF-0055-b, BRIEF-0055-c, BRIEF-0055-d]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Nous travaillons sur le refactor de l'index. Premier ticket de la serie
> (ticket 0055).

First ticket of the index-split chain (0055 -> 0061) mapped in
`Active_project.md`. Scope as mapped: introduce the Svelte + build toolchain
and a static-asset serving path in `app.py` (the `StaticFiles` mount deferred
at `app.py:66-68`), amend the no-build doctrine, open the
`ARCHITECTURE_DECISIONS.md` entry. Pure enabler: nothing else in the chain can
land without a build + serve path.

## Clarifications resolved (intake)

Locked as `A1(target), B1, C1, D3, E1+check, F3, G3+G1`.

- **A1 as TARGET, islands as TRANSITION.** The end state is a Svelte SPA that
  owns `/` and the router. The transition is necessarily island-shaped -- 11k
  lines of interleaved JS (RECON A2) cannot move atomically -- so every surface
  ticket 0057..0060 converts one island. This distinction costs nothing at
  0055: the deliverable is byte-identical under either reading. It fixes one
  doctrine sentence (BRIEF-0055-d) and it fixes the shape of 0056.
- **B1 -- Play stays a vanilla-JS island**, hard boundary, until its own 3D
  rewrite on its own stack. Correction of record: **there is no HTMX in this
  project.** `grep -c "hx-"` on `index.html` returns 0; no `htmx` token exists
  anywhere under `src/` or `tooling/pipeline_cockpit/`. `CLAUDE.md:17` is
  factually wrong and BRIEF-0055-d corrects it rather than appending to it.
- **B1 consequence, deferred to TICKET-0056 (named, not dropped).** A1 target
  plus a permanently-vanilla Play requires a legacy-mount escape hatch inside
  the SPA. An escape hatch rots unless it is a **monotonically shrinking
  enumerated registry**: a fail-closed check lists the permitted legacy mounts,
  each surface ticket removes one, exactly one (Play) survives at 0061. This is
  TICKET-0056's first open decision. 0055 must not pre-build it and must not
  make it unnecessary-looking.
- **C1 -- serving topology.** `StaticFiles` mounted at `/static`. `GET /`
  keeps serving `index.html` verbatim until 0056. The beachhead island is
  proven at a NEW route `GET /shell`, never by editing `index.html`: leaving
  `index.html` byte-untouched is what keeps the 9 index-anchored checks (RECON
  F9) and `relation_graph.py`'s cross-branch byte-equality assertion (RECON F4,
  `relation_graph.py:192-206`) green with zero re-homing. Under the
  cross-cutting rule, a ticket re-homes checks when its targets move; at 0055
  nothing moves.
- **C3 rejected on structural grounds, recorded.** Extending the per-asset
  vendor whitelist (`app.py:70`) is incompatible with content-hashed bundle
  filenames: either hashing is abandoned or the whitelist becomes dynamic, at
  which point it is no longer a whitelist. Rejected explicitly, not silently.
- **D3 -- cytoscape stays vendored and untouched**, declared external to the
  bundler; the `/vendor/{filename}` route (`app.py:201-205`) is unchanged.
  "Which engine sits under the graph primitive" is TICKET-0057's D-B and is not
  pre-empted here. Keeping the vendored file also keeps `relation_graph.py`
  assertion 1 green without re-homing.
- **E1 -- build output is COMMITTED** to `src/world_engine/cockpit/static/`.
  Rationale: a solo local single-machine tool whose launch procedure must stay
  a copy-pasteable PowerShell block. Building at launch (E2) introduces a
  **fail-open** failure mode -- an absent or stale build yields a blank page,
  not a refusal. A committed artifact is fail-closed by construction.
- **E1's structural cost is paid by a check, not by discipline.**
  `frontend_build_fresh.py` (BRIEF-0055-c) recomputes the frontend source hash
  and compares it to the manifest emitted at build time. Without it, E1 rests
  on remembering to rebuild. This is also **forced** by `tooling/verify/run.py:33-49`:
  a ticket whose Machine section parses to zero criteria is red by
  construction, and no existing check asserts anything about a frontend build.
- **F3 -- narrow permission additions only.** `.claude/settings.json`
  `permissions.allow` gains exactly `npm ci` and `npm run build` -- never a
  bare `npm install`. This makes `CLAUDE.md:17-18`'s "no new dependencies
  without a decision" structural rather than instructional: Claude Code can
  build and reproduce a lockfile, and cannot add a package. Follows the
  TICKET-0005 precedent (enumerated entries, no generic `Bash(*)`).
- **G3 + G1 -- doctrine moves down, CLAUDE.md stays law-only.** The frontend
  doctrine body lands in `ARCHITECTURE_DECISIONS.md`; `CLAUDE.md` keeps
  corrected, shortened law at `:17-18` and `:58`. Measured constraint:
  `CLAUDE.md` is at exactly **500/500** lines against
  `claude_md_contract.py`'s hard budget, so the amendment is net-zero or
  net-negative by construction.
- **CLAUDE.md cleanup is OUT of this ticket, and warranted.** Measured:
  `## Invariants` is 202 lines / 41 bullets / 2619 words (40% of the file), and
  only 7 of the repo's 72 checks are cited in it. The 500-line budget is
  fail-open on content -- `CLAUDE.md:276` is a single 5180-character physical
  line. This is a governance ticket of its own (next free slot after the map),
  not a rider on a frontend-only ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The frontend build output exists, is non-empty, and its manifest matches
      a freshly recomputed hash of the frontend sources; the check fails
      vacuously-closed when sources or manifest are missing
      -> verify/checks/frontend_build_fresh.py
- [ ] `CLAUDE.md` still satisfies its structural contract after the doctrine
      amendment (section whitelist, 500-line budget, File-structure budget,
      archaeology ban, pointer freshness)
      -> verify/checks/claude_md_contract.py
- [ ] `DECISIONS_INDEX.md` remains consistent with the decision corpus after
      the new entry -> verify/checks/decisions_index.py
- [ ] `index.html` is not touched by this ticket: the Creation page contract
      still holds -> verify/checks/page_contract.py
- [ ] `index.html` is not touched by this ticket: the vendored cytoscape file
      and its GET route survive, and the Lieux graph component remains
      byte-identical to `main` -> verify/checks/relation_graph.py
- [ ] `index.html` is not touched by this ticket: the review component boundary
      still holds -> verify/checks/review_component.py
- [ ] `index.html` is not touched by this ticket: the observation surface
      anchors still hold -> verify/checks/observation_surface.py

### Live  ->  human gate (Nia)

- [ ] `npm ci` then `npm run build` complete on the Windows box from a clean
      `frontend/`, and the exact invocation is recorded in the brief's report.
- [ ] `python scripts/cockpit.py` starts with no new warning; `http://127.0.0.1:8000/`
      renders the existing cockpit exactly as before -- all three top views,
      Creation sub-tabs, the NPC relation graph and the Lieux graph all behave
      identically to `main`.
- [ ] `http://127.0.0.1:8000/shell` renders the beachhead Svelte island
      (visible text plus one reactive interaction proving the framework is
      really running, not a static string).
- [ ] `git status` is clean after a build -- i.e. the committed output matches
      what the build produces on Nia's machine, confirming E1 is reproducible
      and not machine-dependent.
- [ ] Editing one frontend source file WITHOUT rebuilding turns
      `frontend_build_fresh.py` red; rebuilding turns it green again.
      (Red-test of the new gate, run live.)
