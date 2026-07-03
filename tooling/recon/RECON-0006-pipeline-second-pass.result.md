# RECON-0006 result — Pipeline second pass

**REPORT ONLY.** No edit, no fix, no design decision made during this pass.
Every claim below is cited `path:line` against the living tree (branch
`ticket/0005`, HEAD `43aaf48`). Mismatches between the recon spec's
assumptions and what actually exists are called out explicitly.

Ticket: TICKET-0006. Spec: RECON-0006-pipeline-second-pass.md.

---

## A. Collision audit (H1)

**1. World cockpit module/package names, import roots, launcher.**
Launcher: [scripts/cockpit.py](scripts/cockpit.py) — inserts `src/` onto
`sys.path` ([scripts/cockpit.py:19-20](scripts/cockpit.py#L19)), imports
`world_engine.cockpit.app.app` ([scripts/cockpit.py:24](scripts/cockpit.py#L24)),
runs it via `uvicorn.run(app, host="127.0.0.1", port=8000, ...)`
([scripts/cockpit.py:38-44](scripts/cockpit.py#L38)). The app object is
declared at `src/world_engine/cockpit/app.py:97`:
`app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)`,
with `app.include_router(_crud.router)` at line 98. Package root is
`world_engine.cockpit` (`src/world_engine/cockpit/__init__.py`,
`app.py`, `crud.py`, `index.html`) — a single flat package, no
`templates/`/`static/` subpackage.

**2. Port(s).** Exactly one, hardcoded: `HOST = "127.0.0.1"`, `PORT = 8000`
at [scripts/cockpit.py:32-33](scripts/cockpit.py#L32). No env var, no CLI
flag. Port 8100 (the spec's proposal) is free — grepped the whole tree,
zero hits for `8100`. No other process in this repo binds a port.

**3. Template/static directories.** None exist. The world cockpit has no
`Jinja2Templates` and no `StaticFiles` mount anywhere in `app.py` — confirmed
by grep (`StaticFiles`, `Jinja2Templates`, `mount(` : zero matches). It
serves the UI as one static string: `_INDEX_HTML = Path(__file__).parent /
"index.html"` ([app.py:94](src/world_engine/cockpit/app.py#L94)), returned
verbatim by `GET /` → `HTMLResponse` at
[app.py:961-963](src/world_engine/cockpit/app.py#L961):
```
@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")
```
The `templates` identifier that appears ~10 times elsewhere in `app.py`
(e.g. lines 1296, 1514, 1612...) is the DB table `prompt_template`
(NPC/MJ prompt rows), unrelated to Jinja. **No collision possible**: there
is no loader to collide with. A sibling `tooling/pipeline_cockpit/` can
freely have its own `templates/`/`static/` or repeat the same
read-file-as-string pattern.

**4. Existing `pipeline`-named things.** Grepped the whole tree
case-insensitively for `pipeline`. Non-doc, non-artifact hits:
- [tooling/verify/checks/pipeline_state.py](tooling/verify/checks/pipeline_state.py) —
  the G1 check for ticket front-matter conformity (module name
  `pipeline_state`, not `pipeline_cockpit` — no direct collision, but same
  root word).
- `.claude/commands/pipeline.md` — the `/pipeline` command definition.
No `pipeline` package, module, or directory exists under `src/` or
`tooling/`. `tooling/pipeline_cockpit/` does not exist yet (confirmed:
`find ... -iname "*pipeline*" -type d` returns nothing under `src/` or
repo root besides `.claude/commands`, which is not a directory named
`pipeline*`). **No naming collision on disk today.**

**5. Shared imports from `src/world_engine/`.** Nothing in the ticket
pipeline's stated scope (deposit/numbering, QUESTION read/write) needs any
world-engine DB helper, model, or context assembler — it is pure
filesystem + string manipulation over `tooling/`. A pipeline cockpit
importing from `src/world_engine/` would be a new, currently-nonexistent
coupling; nothing today imports across that boundary in either direction.
Report only, per the spec — the brief should decide whether to forbid it
structurally (e.g., a verify check) or just not do it.

---

## B. `next_id.py` interface (J2)

**6. Confirmed CLI-print-only.** [tooling/glue/next_id.py:18-31](tooling/glue/next_id.py#L18):
```python
def main():
    max_id = 0
    for d in DIRS:
        ...
    print(f"{max_id + 1:04d}")

if __name__ == "__main__":
    main()
```
The counting loop lives inline inside `main()`; there is no importable
`compute_next_id() -> str` today. `ROOT` is resolved via
`pathlib.Path(__file__).resolve().parents[2]` ([next_id.py:9](tooling/glue/next_id.py#L9))
— **working-directory independent**, so both integration shapes are
viable with no CWD constraint:
- *Subprocess*: `python tooling/glue/next_id.py` from anywhere, parse
  stdout. Already the shape `.claude/settings.json` allowlists
  (`"Bash(python tooling/glue/*)"`, [settings.json:6](.claude/settings.json#L6)).
- *Extracted function*: refactor `main()`'s body into
  `compute_next_id() -> str` returning the same zero-padded string,
  `main()` becomes `print(compute_next_id())`. `ROOT`'s `__file__`-relative
  resolution is unaffected either way since it doesn't depend on the
  caller's CWD.
No fact favors one over the other structurally; the CLI callers (glue,
possibly `/pipeline` itself) keep working unchanged under the extraction
option since `main()` is preserved as a thin wrapper. Report only, per the
spec.

**7. Atomicity at deposit time.** `next_id.py` only *reads* the three
directories and prints a number — it never writes. Nothing today makes
"compute number, then write file(s)" atomic; that read-then-write gap
exists wherever `next_id.py`'s result is consumed (currently: a human
running it manually before authoring a ticket/recon/brief by hand — see
`.claude/settings.json`'s narrow allow entry for it). Whether the window
is an issue depends entirely on a fact this RECON can only report, not
resolve: today there is exactly one operator (Nia) and one Claude Code
session acting at a time in this repo — no evidence anywhere (git log,
running processes, or code) of concurrent writers. If the pipeline
cockpit is a single-process FastAPI app handling one deposit request at a
time (no async concurrency inside the deposit route), the compute+write
can be made atomic trivially (compute number, write file(s), all inside
one request handler, no `await` between the two). The spec's own
"single operator, same process" framing matches the current reality
exactly.

---

## C. `/pipeline` derivation points (C1)

**8. Step 0 reconciliation — exact facts, cited.**
[.claude/commands/pipeline.md:8-24](.claude/commands/pipeline.md#L8):
precedence order derives `status` from: (1) `ticket/NNNN` merged into
`main` → `done`; (2) verdict JSON at
`tooling/verify/results/<slug>.json` green AND a PR exists
(`gh pr list --head ticket/NNNN`) → `live-gate`; (3) a
`tooling/questions/QUESTION-TICKET-NNNN.md` exists with an empty
`## Response` → `escalated`; (4) brief file(s)
`tooling/briefs/BRIEF-NNNN*.md` exist → eligible for `exec`; (5) a recon
**result** (`tooling/recon/RECON-NNNN*.result.md`) exists → `brief`; (6) a
recon **spec** (`tooling/recon/RECON-NNNN*.md`) exists → `recon`; (7)
otherwise → `intake`.

**9. Where the recon derivation slots in, and current wording gaps.**
Rules 5 and 6 already assume a recon spec may or may not exist and handle
both — rule 6 fires only when a spec exists with no result yet, rule 7 is
the fallback when neither exists. **However, nothing in Step 1
("act by status", [pipeline.md:33-46](.claude/commands/pipeline.md#L33))
currently tells the executor what to DO when status resolves to `recon`.**
Step 1's current text: `` `brief` / `recon` / `intake` -> name the missing
artifact (brief, recon spec, or recon result), stop. Those stages are
chat-side per P1 — this command does not author them. `` — i.e. today,
landing on status `recon` makes `/pipeline` **stop and say a recon result
is missing**, never run it. This is the exact gap TICKET-0006's C1 clause
needs to close: today's wording treats recon as chat-authored-only
(consistent with the *old* P1 division of labor), not as something
`/pipeline` itself can execute. The ticket's two target rules (spec+no
result → run recon/commit/push/stop; spec absent → inapplicable, proceed)
are **not yet present anywhere in `pipeline.md`** — this is new logic to
add, not a tweak of existing wording. No site assumes a recon ALWAYS
exists (rule 7's `intake` fallback already covers "spec absent"), so the
only change needed is Step 1's `recon` branch, from "stop, name the
missing artifact" to "execute it".

**10. Does anything push the branch after a recon result is committed
today?** No. The **only** `git push` in the entire command surface is
[pipeline.md:62](.claude/commands/pipeline.md#L62), `` `git push origin
ticket/NNNN`. ``, inside Step 3 ("open the PR"), which runs only after a
green `/verify` following full brief execution. Grepped every command
file in `.claude/commands/` for `push`: the only other hits are
`brief-exec.md:11` ("Never push to main.") and `pipeline.md:70-71`
(reiterating never-push-to-main). **Confirmed: TICKET-0006's "push the
branch so chat can read the result" requirement, at the recon stage, is a
wholly new push site** — today a recon result committed on `ticket/NNNN`
is invisible to the chat-side raw-URL read channel until Step 3, i.e.
until every brief on the ticket has ALSO been executed and verified. This
directly contradicts the ticket's intent (recon should be readable before
briefs are even written).

**11. How `/recon` is defined today; what's reusable vs. retired.**
[.claude/commands/recon.md](.claude/commands/recon.md) is a separate,
short command file (15 lines): read the named spec, for each anchor find
`path:line`, note spec-vs-actual mismatches, write
`tooling/recon/<id>.result.md`, never edit/act/branch. Fully reusable
verbatim as the *body* of the absorbed flow — none of its instructions
duplicate anything in `pipeline.md` today (pipeline.md currently has zero
recon-execution logic per finding 9). Nothing to retire; `/recon.md`
becomes the payload that `/pipeline`'s new `recon` branch invokes
in-session, and the standalone `/recon` command can keep existing
unchanged for any chat-side ad-hoc use.

---

## D. Inter-brief wait (E1-chaining — the CA1 deviation)

**12. Where the wait actually happens.** The deviation is **not** in
`pipeline.md`'s CA1 wording taken alone — it's in where that wording is
(and isn't) threaded through the actual call chain. Trace:
- `pipeline.md` Step 1 ([pipeline.md:42-46](.claude/commands/pipeline.md#L42)):
  "Eligible for `exec` -> run the `/brief-exec` protocol for each brief in
  suffix order ... When invoking `/review-step` and `/close-step` **from
  within this chain**, state explicitly that the invocation is unattended
  (CA1)."  This sentence talks about `/pipeline` invoking `/review-step`
  and `/close-step` **directly**.
- But `/pipeline` never invokes those two commands directly — it invokes
  `/brief-exec` per brief, and `/brief-exec` is the one that actually
  calls them:
  [.claude/commands/brief-exec.md:11](.claude/commands/brief-exec.md#L11) —
  "3. Commit with the mandatory protocol: /review-step then /close-step."
- **`brief-exec.md` contains no mention of CA1, "unattended", or
  `/pipeline` at all** — it is written as a standalone, always-interactive
  protocol. So when `/pipeline` "runs the `/brief-exec` protocol" for
  brief `-a`, then again for `-b`, each of those inner invocations reaches
  `close-step` with no structural signal attached — whether the
  unattended flag actually gets restated depends on the executing session
  remembering to say so at that inner call site, not on anything the
  command files themselves guarantee.
- `close-step.md`'s own unattended clause
  ([.claude/commands/close-step.md:24-26](.claude/commands/close-step.md#L24))
  reinforces this fragility: "when invoked from /pipeline (**the invoker
  will say so**)". It is a spoken-convention contract, not a parameter
  `/brief-exec` or `/pipeline` mechanically passes down.

**Conclusion:** the CA1 deviation observed on TICKET-0005 (chain stopped
after `-a` and after `-b`, each needing a manual `/close-step`) is
explained structurally: CA1's unattended-mode statement is written at the
`/pipeline` ↔ `/close-step` boundary, but the real call path is
`/pipeline` → `/brief-exec` (once per brief, looped) → `/review-step` +
`/close-step`, and `brief-exec.md` — the file that actually fires
per-brief — carries zero wiring for it. Fixing this requires either (a)
`brief-exec.md` gaining an "if invoked from `/pipeline`, forward
unattended" clause it can restate to `close-step`, or (b) `pipeline.md`'s
per-brief loop calling `/review-step`/`/close-step` directly instead of
through `/brief-exec`'s bundled step 3. Report only — the brief decides
which.

---

## E. QUESTION file contract (D2 + E1)

**13. QF1 format as implemented.** The skeleton is defined inline in
`pipeline.md`, not in a separate template file:
[pipeline.md:93-107](.claude/commands/pipeline.md#L93) — sections `#
QUESTION — TICKET-NNNN`, `Trigger:`, `## Context`, `## Question`, `##
Options`, `## Response`. Detection of filled-vs-empty is **prose-only**:
Step 0 rule 3 says a QUESTION file "exists with an empty `## Response`
section" → `escalated` ([pipeline.md:17-18](.claude/commands/pipeline.md#L17));
Step 1 says "`escalated` with a filled `## Response`" → resume
([pipeline.md:40-41](.claude/commands/pipeline.md#L40)). **There is no
code anywhere that parses this** — no verify check, no glue script reads
`## Response`'s content. [tooling/verify/checks/pipeline_state.py](tooling/verify/checks/pipeline_state.py#L75-85)
only checks that the QUESTION file **exists** when `status: escalated`
(`fail(...does not exist)` at line 82-85) — it never inspects whether
`## Response` is empty or filled. "Empty" today means whatever the
executing LLM session judges empty (e.g. whitespace-only after the
header) — there is no regex, no sentinel value, nothing machine-exact.

**14. Facts a shared writer (cockpit + inline E1) must respect.**
- No QUESTION file has ever actually been written in this repo's history —
  confirmed via `git log --all --diff-filter=A --name-only | grep -i
  QUESTION`: the only match across all history is
  `tooling/questions/.gitkeep`. So the format below is **spec-only,
  never yet exercised against a real file** — treat every claim in this
  section as "what the prose says," not "what's been battle-tested."
- Encoding: no file exists to check; the rest of the repo's markdown is
  plain UTF-8 (e.g. every ticket/brief/recon file), so a writer should
  assume the same absent evidence otherwise.
- Whether anything appends post-resolution: `pipeline.md:109-111` states
  "The file persists after resolution — it is an append-only trace, never
  deleted or rewritten, even once `## Response` is filled" — this is
  policy, not enforced by any check. `pipeline_state.py` never inspects
  QUESTION file bodies, so nothing currently prevents a second writer from
  clobbering `## Response` — enforcement (e.g. "refuse to touch a
  non-empty `## Response`", per the ticket's acceptance criterion) does
  not exist yet anywhere.
- "Open question" detectability: purely "is there text after the `##
  Response` header" — no `status:` field on the QUESTION file itself (unlike
  tickets, which have YAML front-matter). A shared writer contract needs to
  agree on what counts as "empty" (e.g. strip whitespace, compare to `""`)
  since nothing codifies that today.

**15. Resume path on relaunch — spec only, unverified.** `pipeline.md`
Step 0 rule 3 and Step 1's `escalated` branch describe the *intended*
resume behavior (re-derive `escalated`, check `## Response`, resume
applying it and continue the chain from where it left off), but since no
QUESTION file has ever existed in this repo, **this path has never
actually been run**. RECON reports this as a genuine gap: E1's inline
in-session flow has no prior real execution to mirror faithfully — the
brief will be designing against prose, not observed behavior.

---

## F. PR-conflict facts (F1)

**16. Current `CONFLICTING` detection.** Nothing in `pipeline.md`'s Step 0
facts (finding 8) checks PR mergeable-state at all — rule 2 only checks
verdict-green + "a PR exists" via `gh pr list --head ticket/NNNN`
([pipeline.md:15-16](.claude/commands/pipeline.md#L15)), not its
mergeability. TICKET-0005's actual conflict resolution was **100% human**:
`git log` shows commit `bbbad17`, `` Merge remote-tracking branch
'origin/main' into ticket/0005 ``, authored by `Nia
<nia.airen31@gmail.com>` (not a Claude Code commit), with the conflict
marker comment `# Conflicts: # tooling/standards/ARCHITECTURE_DECISIONS.md`
in the merge commit message. **Confirmed: 0005's resolution was purely
manual, exactly as the ticket's own "Observed on 0005" note states** — no
automated detection exists today.

**17. Append-only files eligible for keep-both, and the asymmetry between
them.** Two exist today:
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new records are
  **appended at the end** of the file (confirmed: `bbbad17`'s actual
  conflict diff, `git show bbbad17 -- tooling/standards/ARCHITECTURE_DECISIONS.md`,
  shows both branches' new `## ` sections inserted at the same anchor near
  line 3423, both as pure additions — the file is 3893 lines total, and
  the newest content sits at the tail, e.g. the "Converging
  `activate_world`/`create_world`..." (BRIEF-54) record near the current
  end of file).
- `world-engine-schema-changelog.md` — the **opposite** direction: entries
  are **prepended**, newest-first, directly under the `## CHANGELOG`
  header. Confirmed both by the file itself (top entry is `v1.66`, the
  highest version) and by `close-step.md:6-7`: "compute the new version
  ..., **prepend** the new entry to `world-engine-schema-changelog.md`."
This directional asymmetry (append-at-end vs. prepend-at-top) means a
single generic "keep-both" merge strategy cannot treat both files
identically — a naive line-based union could still land entries in the
wrong relative order for one of the two files. Derived files needing
regeneration after such a merge: `tooling/standards/DECISIONS_INDEX.md`
via [tooling/glue/gen_decisions_index.py](tooling/glue/gen_decisions_index.py) —
confirmed as the sole generator (`close-step.md:11-14` cites this exact
command). No other generated-from-`ARCHITECTURE_DECISIONS.md` (or
-changelog) artifact exists in the tree.

**18. GH1 permissions audit — current allowlist, verbatim.**
[.claude/settings.json:3-10](.claude/settings.json#L3):
```
"permissions": { "allow": [
  "Bash(gh pr create:*)",
  "Bash(git push origin ticket/*)",
  "Bash(python tooling/glue/*)",
  "Bash(python -m tooling.verify.run:*)",
  "Bash(git branch:*)",
  "Bash(git log:*)"
]}
```
Missing for F1: `git fetch`, `git merge` (or `git merge origin/main`),
any conflict-state inspection (`git diff --name-only --diff-filter=U`,
`git status` in a conflicted state), and a re-push after resolution (the
existing `git push origin ticket/*` entry already covers re-push, so that
one's fine). Note: a broader, machine-local
`.claude/settings.local.json` exists with `git checkout *`, `git push *`,
etc. ([.claude/settings.local.json:5-15](.claude/settings.local.json#L5)),
but it is **git-ignored** (`git check-ignore -v` confirms
`.config/git/ignore` excludes it) — it is this one machine's override,
not part of the committed governance surface the brief should reason
about.

**19. "Conflict touches `src/`" detection.** No mechanical equivalent
exists anywhere in the glue today — grepped the whole tree for
`diff-filter`, `--name-only`, and `git diff`: the only hits are inside
`RECON-0006-pipeline-second-pass.md` itself (the spec asking the
question). `git diff --name-only --diff-filter=U` (listing unmerged/
conflicted paths) is a standard, available git primitive but is not
wired into any script or command file today. This is new capability to
build, not an extension of existing code.

---

## G. Artifact type detection (I1 "Soumettre")

**20. Header/front-matter shapes — real population, with deviations.**
- **Tickets:** YAML front-matter with `id: TICKET-NNNN`
  ([tooling/tickets/TEMPLATE.md:1-11](tooling/tickets/TEMPLATE.md#L1)),
  e.g. [TICKET-0005-creation-page-contract.md:1-5](tooling/tickets/TICKET-0005-creation-page-contract.md#L1)
  (`id: TICKET-0005`). **Deviation found:** the body's own H1 heading still
  literally reads `# TICKET-XXXX — ...` in
  [TICKET-0001-doc-partition.md:14](tooling/tickets/TICKET-0001-doc-partition.md#L14)
  (front-matter says `id: TICKET-0001`, but the prose title kept the
  template's placeholder `XXXX` verbatim) — a naive detector keying off
  the H1 text for the number would get it wrong; the YAML `id:` field is
  the only reliable source.
- **Recon specs:** the spec's assumed shape is `` # RECON — ... `` (no
  number in title) — true for RECON-0005
  ([tooling/recon/RECON-0005-creation-page-contract.md:1](tooling/recon/RECON-0005-creation-page-contract.md#L1),
  `# RECON — Création sub-tab layout map...`) and for this ticket's own
  RECON-0006 spec. **Deviation found:** RECON-0003 and RECON-0004 both put
  the number directly in the title instead —
  [RECON-0003-canon-write-map.md:1](tooling/recon/RECON-0003-canon-write-map.md#L1)
  `# RECON-0003 — Canon-write paths...` and
  [RECON-0004-glue-ground-truth.md:1](tooling/recon/RECON-0004-glue-ground-truth.md#L1)
  `# RECON-0004 — Scaffold ground truth...`. So the "population" actually
  contains **both** shapes (numbered and unnumbered titles) — a detector
  must not assume the title is number-free; it should key off the
  filename or, if parsing the body, accept either shape.
- **Briefs:** `` # BRIEF — Step "..." (BRIEF-NNNN[-x]) `` — true for
  BRIEF-0001-a/b, BRIEF-0003-a/b, BRIEF-0004 (e.g.
  [BRIEF-0004-pipeline-glue.md:1](tooling/briefs/BRIEF-0004-pipeline-glue.md#L1)).
  **Deviation found:** BRIEF-0005-a/-b/-c drop the trailing `(BRIEF-NNNN-x)`
  entirely — e.g.
  [BRIEF-0005-a-creation-tab-registry.md:1](tooling/briefs/BRIEF-0005-a-creation-tab-registry.md#L1)
  reads `` # BRIEF — Step "Création tab registry, generic dispatcher, state
  contract, entity archetype" `` with no id suffix at all. Again, the
  filename is the only reliable id source across the real population;
  the H1 text alone is not.

This directly reconfirms the ticket's own G1-lesson citation
(RECON-0002 found 20/47 ARCHITECTURE_DECISIONS.md headers deviating in
three ways) — the artifact population here shows the same pattern:
**detect type from front-matter presence/shape + filename prefix
(`TICKET-`/`RECON-`/`BRIEF-`), never from the H1 prose,** since the H1 is
demonstrably inconsistent across real files for all three types.

---

## H. Read-channel exposure (A+)

**21. Tracking and `.gitignore` audit.** [.gitignore](.gitignore) (10
lines total) excludes only Python cache/venv artifacts, `.env`, and
DB files (`*.db`, `*.sqlite*`) — nothing under `tooling/`. Confirmed live:
`tooling/tickets/`, `tooling/recon/`, `tooling/briefs/`, and
`tooling/questions/` are all tracked — the questions directory holds a
tracked `.gitkeep`
([tooling/questions/.gitkeep](tooling/questions/.gitkeep), confirmed
present via `git log --diff-filter=A` showing it added in commit
`36502db docs(tickets): revert tooling gitignore exclusion, track
pipeline artifacts...` — the commit message itself documents that a
prior gitignore exclusion was deliberately reverted for this exact
reason). GT-A revert holds; nothing hides pipeline artifacts from the
public repo.

**22. What lands where, per phase, from chat's read perspective.**
Traced via `git log --oneline --all -- <path>`:
- Tickets/recon specs today are **not** committed standalone before exec
  starts — TICKET-0005's ticket file's earliest commit on any branch is
  `f33dea7 feat(cockpit): Création tab registry + generic dispatcher
  (BRIEF-0005-a)` — i.e. it landed **bundled into the first brief's own
  implementation commit**, not as its own preceding commit. There is no
  git evidence of "ticket deposited, then separately recon'd, then
  separately briefed" as isolated commits on this repo's actual history;
  it's been coarser in practice.
  - Recon **results** likewise: RECON-0004's result
    (`RECON-0004-glue-ground-truth.result.md`) first appears in commit
    `36502db docs(tickets): revert tooling gitignore exclusion, track
    pipeline artifacts, backfill TICKET-0001 front-matter` — a
    documentation/governance commit, not a dedicated "recon result" commit.
  - Combined with finding 10 (the only push is Step 3, after full
    verify): **today, none of ticket / recon spec / recon result /
    briefs reach the public remote (and thus a raw-URL-readable state)
    until the entire ticket's brief chain is done and verified** — the
    branch is pushed exactly once, at the very end. This is the core fact
    TICKET-0006's C1 "push after recon" clause needs to change: it
    introduces the **first-ever early push point**, before any brief
    exists.
  - QUESTION files: no QUESTION file has ever been committed (finding 14) —
    there's no historical branch/commit pattern to report for them; C1's
    "commit result, push, stop" pattern for recon does not obviously
    extend to QUESTION files (D2/E1 don't specify a push at escalation
    time), so the raw-URL recipe for an in-flight QUESTION file is an open
    question the brief should settle, not something this RECON can derive
    from precedent.
