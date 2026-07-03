# RECON — Pipeline second pass

Report-only reconnaissance for TICKET-NNNN. Findings are NEVER acted on
during this RECON: no fix, no rename, no refactor, however small. Every
finding cites `file:line`. Deliverable: `tooling/recon/RECON-NNNN-pipeline-second-pass.result.md`.

## A. Collision audit (H1 — Nia's explicit instruction)

The pipeline cockpit will live at `tooling/pipeline_cockpit/` as a separate
FastAPI + HTMX app. Before any code is specified, map every collision
surface with the world cockpit:

1. World cockpit module/package names, import roots, and how it is
   launched (entry point, `PYTHONPATH` assumptions). Cite the launcher and
   the app object definition.
2. Port(s) the world cockpit binds (default and any configurable). Confirm
   a free conventional port for the pipeline cockpit (proposal: 8100) —
   report, do not choose.
3. Template and static directory names/paths in the world cockpit. Would a
   sibling app with its own `templates/`/`static/` under
   `tooling/pipeline_cockpit/` collide with any Jinja/StaticFiles
   configuration, or are loaders instance-scoped? Cite configuration lines.
4. Any existing name containing `pipeline` in `src/`, `tooling/`, or
   `.claude/` (files, modules, verify checks, command names) that could be
   confused with `pipeline_cockpit`. List them all.
5. Shared imports: would `tooling/pipeline_cockpit/` importing anything
   from `src/world_engine/` create a coupling that violates the
   world/pipeline domain split? Report what, if anything, it would be
   tempted to import (e.g., DB helpers) — the answer may be "nothing".

## B. `next_id.py` interface (J2)

Intake fact: `tooling/glue/next_id.py` is CLI-print-only; the counting
logic lives inline in `main()`.

6. Confirm at `file:line`. Report the two integration shapes for the
   cockpit — subprocess call vs. extracting a `compute_next_id() -> str`
   function imported by both the CLI and the cockpit — with any constraint
   that favors one (working-directory assumptions, `ROOT` resolution via
   `__file__`). Report only; the brief decides.
7. Atomicity at deposit time: the cockpit computes the number then writes
   one or two files (ticket alone, or ticket + recon spec pasted in
   sequence). Identify any window where two successive deposits could
   collide, and what fact makes it a non-issue or an issue (single
   operator, same process).

## C. `/pipeline` derivation points (C1)

8. Locate Step 0 reconciliation in the `/pipeline` command definition: the
   exact list of observable facts it derives status from today, with
   citations.
9. Where would the recon derivation slot in? Confirm the two target rules
   against current wording: (spec present AND no result → run recon,
   commit result on `ticket/NNNN`, push, stop) and (spec absent → recon
   phase inapplicable by construction, proceed). Report any current wording
   that assumes a recon ALWAYS exists — every site that would need the
   no-recon clause.
10. Does anything push the branch after a recon result is committed today?
    Cite. (The chat read path requires the push.)
11. How is `/recon` defined today (separate command file?) — what parts are
    reusable verbatim by the absorbed flow, what parts duplicate `/pipeline`
    logic and would be retired.

## D. Inter-brief wait (E1-chaining — the CA1 deviation)

12. Locate where `close-step` waits (or `/pipeline` stops) between briefs
    of the same ticket. On TICKET-0005 the chain stopped after -a and -b,
    awaiting a manual `/close-step` each time, despite CA1 ("close-step
    skips its wait in unattended mode"). Cite the exact lines in
    `close-step.md` and/or the `/pipeline` definition where the unattended
    mode fails to apply between briefs. Report whether the deviation is in
    the command wording, the mode detection, or the chaining logic.

## E. QUESTION file contract (D2 + E1 — two writers, one format)

13. Cite the QF1 format as implemented: exact section names, how
    `/pipeline` detects a filled vs. empty `## Response` on relaunch.
14. The cockpit "Questions" surface and the inline in-session transcription
    will BOTH write `## Response`. Report every fact a shared writer
    contract must respect: encoding, trailing content after `## Response`,
    whether anything else ever appends to the file post-resolution, and how
    "open question" is detectable (empty section? status field?).
15. Report how `/pipeline` currently behaves if relaunched while a QUESTION
    is open vs. answered — the resume path the inline E1 flow must
    reproduce without a relaunch.

## F. PR-conflict facts (F1)

16. Current behavior when the opened PR is `CONFLICTING`: does `/pipeline`
    detect it at all today (Step 0 facts?), or was 0005's detection purely
    human? Cite.
17. Enumerate the append-only files eligible for mechanical keep-both
    resolution (ARCHITECTURE_DECISIONS.md, `world-engine-schema-changelog.md`,
    others?) and the derived files needing regeneration after such a merge
    (`DECISIONS_INDEX.md` via `tooling/glue/gen_decisions_index.py`,
    others?). Cite the generators.
18. GH1 permissions audit: which git/gh operations the F1 capability needs
    (`git merge origin/main`, `git fetch`, conflict-state inspection,
    re-push) that are NOT currently in `.claude/settings.json`'s
    `permissions.allow`. Cite the current allowlist verbatim.
19. Detection of "conflict touches `src/`": report the mechanical fact
    available (e.g., `git diff --name-only --diff-filter=U`) — is anything
    equivalent already used in the glue?

## G. Artifact type detection (I1 "Soumettre")

20. Report the header/front-matter shapes that distinguish the three
    artifact types today: tickets (YAML front-matter with `id:`), recon
    specs (`# RECON — ...` title, no number in title), briefs
    (`# BRIEF — Step "..."`). Cite one real example of each and note any
    existing artifact that deviates from its type's nominal shape — the
    detector must handle the real population, not the ideal one
    (G1-lesson from RECON-0002).

## H. Read-channel exposure (A+)

21. Confirm `tooling/tickets|recon|briefs|questions/` are all tracked
    (GT-A revert holds) and that nothing in `.gitignore` would hide any
    pipeline artifact from the public repo. Cite.
22. Report which branch carries what, at each phase, from the chat's
    perspective: recon results land on `ticket/NNNN` (readable only after
    the C1 push), QUESTION files land where and on which branch. The chat
    needs a deterministic raw-URL recipe per artifact type and phase —
    report the facts that fix it.
