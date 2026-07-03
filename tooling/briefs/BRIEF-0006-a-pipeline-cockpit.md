<!-- slug: pipeline-cockpit -->
# BRIEF — Step "Pipeline cockpit, question-response glue, next_id extraction" (BRIEF-0006-a)

## Context
TICKET-0006 second pipeline pass. Chat→repo writes are covered by a paste
gesture into a new, separate pipeline cockpit (H1/I1); the deposit gesture
remains Nia's green light (SM1 unamended). RECON-0006 confirmed: no naming,
port, template, or loader collision with the world cockpit (findings 1-4);
`next_id.py` is CLI-print-only (finding 6); no QUESTION file has ever
existed and nothing enforces its append-only contract (findings 13-15).
This brief builds the cockpit and the code-level contracts. BRIEF-0006-b
(command surface) depends on `question_response.py` from this brief.

## Scope IN

1. **`tooling/glue/next_id.py` — extract `compute_next_id()` (L1).**
   Move the body of `main()` into `compute_next_id() -> str` returning the
   same zero-padded 4-digit string; `main()` becomes
   `print(compute_next_id())`. Docstring, `ROOT` (`__file__`-relative,
   RECON finding 6), `DIRS`, `ID_RE` unchanged. CLI behavior byte-identical.

2. **New module `tooling/glue/question_response.py` (N1) — the single
   QUESTION writer.** Stdlib only. UTF-8. Functions:
   - `response_section(text: str) -> str`: returns the content after the
     `## Response` header line, up to the next `## ` header or EOF.
   - `is_open(path: Path) -> bool`: True iff
     `response_section(path.read_text(encoding="utf-8")).strip() == ""`.
     This IS the machine definition of "empty `## Response`" (RECON
     finding 13: none exists today); all consumers point here.
   - `list_open_questions(root: Path) -> list[Path]`: every
     `tooling/questions/QUESTION-*.md` where `is_open` is True, sorted by
     name.
   - `write_response(path: Path, text: str) -> None`: raises
     `ResponseAlreadyFilled` if not `is_open(path)`; raises
     `MalformedQuestion` if no `## Response` header exists; otherwise
     inserts `text` (stripped, plus trailing newline) immediately after the
     `## Response` header line. Nothing above `## Response` is ever
     modified.
   - CLI: `python tooling/glue/question_response.py list` (prints open
     files, one per line) and
     `python tooling/glue/question_response.py answer <file>` (response
     text read from stdin). Exit codes: `0` written, `1` refused
     (already filled), `2` missing/malformed file. Both the cockpit route
     and the inline escalation flow (BRIEF-0006-b) invoke this module —
     one writer, two invokers.

3. **Pipeline cockpit app — `tooling/pipeline_cockpit/` (H1, I1).**
   - `__init__.py`, `app.py`, `deposit.py`, `index.html`. FastAPI
     `app = FastAPI(title="Pipeline Cockpit", docs_url=None,
     redoc_url=None)`. UI served exactly like the world cockpit
     (finding 3): `index.html` read as a string by `GET /`. No Jinja, no
     StaticFiles, no new dependencies. NOTHING under
     `tooling/pipeline_cockpit/` imports from `src/world_engine/` (K1,
     enforced by the check in item 5).
   - **`deposit.py` — pure functions, no I/O beyond what's injected**
     (routes stay thin; the verify check tests these directly):
     - `detect_type(body: str) -> str`: `"ticket"` if a YAML front-matter
       block contains a line matching `^id:\s*TICKET-`; `"recon"` if the
       first H1 starts with `# RECON`; `"brief"` if the first H1 starts
       with `# BRIEF`; else raise `UnknownArtifactType`. Producer contract
       (P1): chat guarantees these shapes for all NEW artifacts; legacy
       files are never re-ingested (RECON finding 20 deviations are
       irrelevant here).
     - `extract_slug(body: str, type_: str) -> str`: tickets → front-matter
       `slug:` field; recon/briefs → first-line HTML comment
       `<!-- slug: ... -->`. Missing → raise `MissingSlug`. No guessing,
       no slugification fallback.
     - `assign_number(body: str, type_: str, root: Path,
       bound_ticket: str | None) -> tuple[str, str]`: tickets → number =
       `compute_next_id()` (imported, L1); recon/briefs containing the
       `NNNN` placeholder → number = `bound_ticket` (see route below),
       error if `bound_ticket` is None; recon/briefs already carrying a
       concrete 4-digit number in their body → that number, as-is.
       Substitutes the number for every `NNNN` occurrence in the body.
       Returns `(numbered_body, number)`.
     - `target_path(type_: str, number: str, slug: str, body: str,
       root: Path) -> Path`: `tooling/tickets/TICKET-<n>-<slug>.md` /
       `tooling/recon/RECON-<n>-<slug>.md` /
       `tooling/briefs/BRIEF-<n>[-<suffix>]-<slug>.md`. The brief suffix
       (`-a`, `-b`, ...) is read from the H1's `(BRIEF-....-x)` tag when
       present; absent tag → no suffix. Refuse to overwrite an existing
       file (`TargetExists`).
   - **Route `POST /api/submit`** (body = pasted text): runs detect →
     slug → assign → write, all inside the one handler (compute+write
     atomicity per RECON finding 7: single process, no `await` between
     compute and write). On a ticket deposit, the assigned number becomes
     the page's `bound_ticket` (returned in the response, kept in page
     state, shown in a visible, editable field pre-filling subsequent
     recon/brief deposits). Response: created filename(s) + assigned
     number, rendered in the UI. Errors surface verbatim in the UI; no
     silent fallback.
   - **Questions surface**: `GET /api/questions` lists open QUESTION files
     via `list_open_questions` (filename + the `## Question` section text);
     `POST /api/questions/answer` calls `write_response`; a
     `ResponseAlreadyFilled` refusal is displayed, never overridden. (D2)
   - **Launcher `scripts/pipeline_cockpit.py`**: mirrors
     `scripts/cockpit.py`, inserts the repo root (not `src/`) onto
     `sys.path`, imports `tooling.pipeline_cockpit.app.app`,
     `uvicorn.run(app, host="127.0.0.1", port=8100)` (port confirmed free,
     RECON finding 2).

4. **Producer contract, documented (P1).** Add a short "Artifact producer
   contract" block to `CLAUDE.md`: every chat-produced artifact embeds a
   machine-readable slug (`slug:` front-matter field for tickets; line-1
   `<!-- slug: ... -->` comment for recon specs and briefs); type is
   detected from body shape (front-matter `id:` / H1 `# RECON` / H1
   `# BRIEF`), never from H1 prose; `NNNN` placeholders are resolved by the
   cockpit at deposit (J2).

5. **Verify check `tooling/verify/checks/pipeline_cockpit.py`** (G1 gate,
   deterministic, no network, temp-dir only):
   - imports `tooling.pipeline_cockpit.app` cleanly; asserts its port
     constant is `8100` (≠ world cockpit's 8000);
   - **K1 import boundary**: scans every `.py` under
     `tooling/pipeline_cockpit/` (stdlib `ast`) — any `import`/`from`
     referencing `world_engine` fails the check;
   - deposit round-trip in a temp tree: a pasted ticket body with `NNNN`
     placeholders and `slug: check-fixture` lands at
     `tooling/tickets/TICKET-<computed>-check-fixture.md` with the number
     substituted in body and name; a recon body with `bound_ticket` set
     lands under that ticket's number;
   - QUESTION writer guard: `write_response` on a temp QUESTION file with a
     filled `## Response` raises `ResponseAlreadyFilled` and leaves the
     file byte-identical; on an empty one it writes and a second call then
     refuses.

## Scope OUT
- No git operation of any kind inside the cockpit (no add/commit/push) —
  deposit writes working-tree files only; commits happen through the
  existing command surface.
- No ticket status board (I2 — deferred, named in TICKET-0006).
- No `/pipeline` launcher button (I3 — rejected).
- No authentication (localhost bind only, like the world cockpit).
- No re-ingestion, renaming, or normalization of legacy artifacts
  (grandfathered population stays untouched).
- No changes to `.claude/commands/*`, `.claude/settings.json`, or any
  verify check other than the new `pipeline_cockpit.py` — that is
  BRIEF-0006-b.
- No styling work beyond minimal functional HTMX (mirror the world
  cockpit's plainness).
- No `pipeline_state.py` inspection of `## Response` content (deferred;
  existence check stands as-is).

## Invariants to defend
- **Append-only / history is sacred**: `write_response` is the sole
  QUESTION writer and structurally refuses non-empty sections; nothing in
  this brief ever rewrites an existing artifact (deposit refuses to
  overwrite, `TargetExists`).
- **Single source of truth**: `compute_next_id()` is the one counter
  authority (CLI and cockpit import the same function); `is_open()` is the
  one definition of "empty response".
- **Structural over disciplinary**: K1 boundary and the writer guard are
  verify-enforced, not documented conventions.
- **World DB untouched**: this brief never opens
  `~/.world_engine/world_engine.db`; canon-write doctrine is not in play.

## Done means
- [ ] `python tooling/glue/next_id.py` prints the same value as before the
      refactor (run before/after, compare).
- [ ] `scripts/pipeline_cockpit.py` starts; `http://127.0.0.1:8100/` serves
      the two surfaces; world cockpit on 8000 runs simultaneously without
      interference.
- [ ] Live: pasting a ticket body (NNNN placeholders + slug) creates the
      correctly numbered file in `tooling/tickets/` and displays the
      number; pasting a recon body right after lands under the same number
      in `tooling/recon/`.
- [ ] Live: a fixture QUESTION file with empty `## Response` appears in the
      Questions surface; answering it writes under `## Response`; answering
      again is refused with a visible message.
- [ ] `python -m tooling.verify.run` green, including
      `pipeline_cockpit.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- `CLAUDE.md`: the producer-contract block (Scope IN item 4).
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: new section "PIPELINE
  COCKPIT — deposit surface, question writer, structural boundaries
  (BRIEF-0006-a, no schema change)" recording H1, I1 (+I2 deferred), J2,
  K1, L1, N1 (writer half), P1. Header must pass the strict gate;
  regenerate `DECISIONS_INDEX.md` per close-step.
- No schema change; no changelog entry.
