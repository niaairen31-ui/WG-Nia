---
id: TICKET-0117
title: The instruction corpus split by where it holds, and the pipeline as practised -- path-scoped rules with INV ids, a generated module map, escalations in the ticket, pre-authorized commits
type: feature
status: live-gate
created: 2026-10-10
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0117-claude-md-restructure.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched:
retry_count: 0
slug: claude-md-restructure
---

## Request (verbatim, as Nia stated it)

2026-10-10, in the planning conversation:

> Donne moi les recommandation pour le contenue du Claude.md d'un projet comme le miens.

After the recommendations and the first decision blocks:

> A1 un ticket dédié, mais son numéro est le 0117 parce que les autres sont
> réservé sur une série que je fais. B1 lui permettra d'existé librement sans
> que je n'ai d'Actions a posé, c'est cela ? C1.

> D1, E j'utilise souvent /*brief-execution et /*pipeline pour faire mes
> demandes d'exection de briefs. , je n'utilise plus le truc sur les
> questions, F1.

> G1 mais pourquoi on ne change pas la forme du dossier pour qu'il ne soit
> plus plat?, H1, J2 ajoute un brief pour la modification du/pipeline.

> K1, Ja, Retire tous ce qui ne sert a rien. Je ne veux pas grader des choses
> qui pourraient entrainer de la confusion.

> Parfait, puisque nous somme dans la documenttion, je veux aussi que tu
> mette a jour un comportement que j'observe. Claude code s'arrête souvent
> entre le /review et le /close step. Aussi il me demande l'autorisation de
> commité dans les /brief exec et pas dans les pipeleine ( je veux les commit
> pré-authorisé dans les execution aussi). . L Comme décrité

> M1

## Clarifications resolved (intake)

- **The budget was nearer than reported.** The 37 839 of the series handover
  counted bytes; `claude_md_contract.py` counts characters (`len(text)`):
  `main` at `8aa388e` holds 37 202 of 38 000 -- 798 left (R-01).
- **What B1 asks of Nia: nothing.** The executor regenerates the map: the
  freshness check makes the regeneration part of the commit that changes a
  module, the way `frontend_build_fresh.py` makes the build part of a
  frontend commit.
- **Why not reshape `src/world_engine/` into packages now (her question on
  G).** Measured: 732 hard-coded `src/world_engine/...` paths across the
  verify checks and glue, `canon_write_policy.txt` naming writers by module,
  `prompt_registry` naming call sites by file, and the imports of 183
  modules. A real series, worth doing, and cheaper once this ticket lands:
  the generated map needs no hand rewrite and a rule moves by changing one
  glob. K1 makes it TICKET-0118.
- **The questions mechanism was not dead.** `/pipeline` wrote
  `QUESTION-TICKET-0111.md` two days before this ticket; Nia answers in the
  session and the file was its trace. J2-a keeps the trace, in the ticket.
- **Why Claude Code asked to commit in `/brief-exec` and not in `/pipeline`.**
  `/close-step` step 6 waited for approval unless invoked « unattended »,
  which only `/pipeline` announced (R-04). **Why it stopped between review
  and close.** `/review-step` ended on its verdict and nothing told it to go
  on (R-04).
- **Pre-authorized commits remove a net.** Approving each commit was what
  kept a commit off `main`; `block-main-push.ps1` matches only a command that
  names `main` (R-11). M1 adds `block-commit-on-main.ps1`.
- **Prototype.** Every brief of the lot was applied to a private clone of
  `main` at `8aa388e` and the full corpus run after each (145, 146, 146, 147,
  147 checks, all green, on Linux). The briefs embed those diffs. The
  PowerShell hook could not run there: its proof is a live gate.

## Decisions locked (do not re-litigate without Nia)

- **A1** -- a dedicated ticket, numbered 0117 (0112-0116 are reserved for
  the conditions series).
- **B1** -- the module map is generated from module docstrings into
  `tooling/standards/FILE_MAP.md`, red when stale; CLAUDE.md keeps the top
  level only.
- **C1** -- every invariant ends with `-- enforced by <check>.py` or
  `[no check]`, and the contract check requires one of the two.
- **D1** -- compress the invariants, keep transversal law in the root, move
  local law out of it. Rejected: D2 (compress only; reactivation: a session
  misses a local invariant), D3 (an imported file loads at launch anyway).
- **E1** -- the pipeline section is rewritten to current practice
  (`/brief-exec` and `/pipeline` are how Nia executes).
- **F1** -- invariant ids `INV-NN`, never reused; retired ids are recorded
  and the contract requires live plus retired to be exactly INV-01 to the
  highest.
- **G1** -- local law lives in `.claude/rules/<topic>.md` with a `paths:`
  list. Rejected: G2 (directory `CLAUDE.md`: `src/world_engine/` is flat),
  G3 (both).
- **H1** -- a linked invariant's full law is its check's docstring; an
  unlinked one keeps its law in its line and loses only rationale. Rejected:
  H2 (a second full text that drifts), H3 (cut without keeping the law).
- **J2-a** -- an escalation is an entry of the ticket's own `## Escalations`
  section, written only by `tooling/glue/escalation.py`; `tooling/questions/`
  is archived into the tickets and deleted. Rejected: J1 (describe only),
  J2-b (no trace).
- **K1** -- reshaping `src/world_engine/` into packages is TICKET-0118,
  designed after this ticket merges.
- **L** -- as described (L1-L10): remove what serves nothing and could
  mislead -- the pipeline cockpit, `question_response.py`, `/recon` and the
  `recon`, `brief` and `verify-authoring` skills, `next_id.py`, the bug log
  (archived here first), `CHANGELOG.md`; rewrite the model lanes. Keep
  `tooling/recon/` as the archive of earlier tickets and every past ticket,
  brief, lot and decision entry as written. For this perimeter the rule
  « dormant code is kept while reactivation is plausible » is reversed:
  confusion is the cost Nia named.
- **M1** -- `/close-step` always commits without approval; `/review-step`
  continues to `/close-step` in the same turn on CLEAN or ATTENTION and stops
  on VIOLATION; `settings.json` allows `git switch`, `git add`, `git commit`;
  a hook refuses a commit on `main`. Rejected: M2 (ATTENTION stops too;
  reactivation: an ATTENTION commit turns out to have been a violation).

## Carried forward / open

- **TICKET-0118 -- `src/world_engine/` into packages (K1).** Its first RECON
  enumerates the 732 path references; pure-move commits with the
  `static_table_names()` proof.
- **Two open bugs from the retired bug log.** Both deserve a ticket of their
  own if Nia still sees them: (1) a structured 422 from `POST
  /api/day/{batch_id}/resolve` shows as « [object Object] »; (2) the live 8B
  model lower-cases the whole prose instead of the listed words in the day
  narration repair pass. The log follows verbatim, the only place it
  survives outside git history:

~~~~json
{"date": "2026-07-03", "found_during": "TICKET-0008/BRIEF-0008-b live verification", "location": "src/world_engine/context.py:214-218 (assemble_npc_context)", "description": "When location.subculture[\"values\"] is a list (some AI-generated locations store it that way) instead of a string, setting_lines.append(values) appends the list itself, and the later \" \".join(setting_lines) raises TypeError: sequence item N: expected str instance, list found. Crashes assemble_npc_context for any NPC at that location — both live /say and the BRIEF-0008-b dry-run preview hit it identically (confirmed on several Verkhaal-world locations).", "severity": "live-play-breaking for affected locations, not universal", "suggested_fix": "Normalize subculture[\"values\"] to a string at the read site (join a list) or at the write/generation site (entity_author.py) so it never reaches this join as a non-string.", "status": "fixed (BRIEF-0025-d, v1.78)"}
{"date": "2026-09-01", "found_during": "TICKET-0079/BRIEF-0079-b live verification (item 8, report-only per brief)", "location": "frontend/src/creation/sheetRequest.svelte.js:33 (api()), consumed by frontend/src/journee/journee.svelte.js:88-99 (resolveDay)", "description": "POST /api/day/{batch_id}/resolve's 422 detail became a structured dict ({message, reason, offending_words, prose}) in BRIEF-0079-b. api() still does: throw new Error(data.detail || JSON.stringify(data)); passing a dict to Error() coerces it via String() to the literal text '[object Object]', so journeeState.resolveError displays that instead of the rejection reason. Confirmed live: resolving a rejected day through the actual Journee UI rendered exactly '[object Object]'.", "severity": "user-visible but not blocking -- the day stays retryable, only the error message is unreadable", "suggested_fix": "Teach api() (or a day-specific caller) to render data.detail.message when detail is an object, falling back to the string case for other endpoints' plain-string details.", "status": "open"}
{"date": "2026-09-01", "found_during": "TICKET-0079/BRIEF-0079-b live verification", "location": "src/world_engine/day_narration.py:repair (day_narration_repair prompt), live model huihui_ai/qwen3-abliterated:8b-v2", "description": "The bounded repair pass's directive ('lower-case only the listed offending words') is not reliably followed by the live game model: measured on a 6-sample live probe reproducing TICKET-0079's exact scenario, 4 of 6 resolutions drew a name-containment rejection needing repair, and 0 of 4 repairs succeeded -- the model consistently lower-cased the ENTIRE prose instead of only the offending words, which then fails the judge's anti-vacuity guard (zero names extracted). Every failure still degrades correctly to a structured 422 (fail-closed held), so this is a narration-quality/model-compliance gap, not a code defect. It is above BRIEF-0079-b's own B1/B3 reactivation threshold ('rejects after repair on more than 2 of 10 resolved days').", "severity": "reduces the practical benefit of the repair pass -- days needing repair mostly still end in a 422, requiring the player/creator to retry the whole day", "suggested_fix": "Revisit B1/B3 per TICKET-0079's own reactivation condition (a deliberate de-capitalisation pre-pass or determiner exemption), or try a stronger/more compliant local model for the day_narration_repair usage specifically (per-template model override already exists via prompt_template.model).", "status": "open"}
~~~~

- **The `[no check]` invariants are a debt list (C1).** 39 of 61 carry no
  enforcing check after this ticket; each one that gains a check changes its
  marker in the same commit.
- **Historical documents still name retired paths** (`ARCHITECTURE_DECISIONS.md`
  entries, the schema changelog, migration docstrings, verdict JSONs). They
  are history and stay as written; the new decision entries say where the
  content went.
- **The project's `TEMPLATE.md` in claude.ai** still lacks the `slug:` field
  and the `## Escalations` note the repository template gains in BRIEF-A.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] An escalation is appended to and answered in its own ticket by one writer; an escalated ticket holds an open entry; escalation ids run E-01 upward with one response marker each (J2-a)  -> verify/checks/escalation_writer.py
- [ ] Ticket front-matter, section shape, escalations, and arrows to retired checks recorded in `checks.retired` (J2-a, L1)  -> verify/checks/pipeline_state.py
- [ ] Commits pre-authorized behind a no-commit-on-main hook; review chains to close in one turn; /pipeline escalates into the ticket; the recon command and the three skills are gone; the review commands read every rule file (M1, L4-L6)  -> verify/checks/session_config.py
- [ ] Every Python module has a docstring and `FILE_MAP.md` is fresh (B1)  -> verify/checks/file_map.py
- [ ] Root and rule files within budget; every invariant has a unique `INV-NN` and a check or `[no check]`; rule globs match files; the listed rule files equal those on disk (C1, D1, F1, G1)  -> verify/checks/claude_md_contract.py
- [ ] The skills rule names `requires_master` and `skill_access`  -> verify/checks/npc_skills.py
- [ ] Decision entries pass the strict header gate and the index is fresh  -> verify/checks/decisions_index.py
- [ ] The full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] `/brief-exec` on a scratch brief commits without asking, and goes from `/review-step` to `/close-step` without handing the turn back.
- [ ] In a Claude Code session in the project, after `git switch main`, `git commit --allow-empty -m test` is refused with the M1 message; after `git switch ticket/0117` the same commit goes through (then `git reset --soft HEAD~1`).
- [ ] In a fresh Claude Code session, after it reads `frontend/src/App.svelte`, it states INV-49 without opening `.claude/rules/frontend.md`.
- [ ] CLAUDE.md reads, to Nia, as the law that holds everywhere and nothing else.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
