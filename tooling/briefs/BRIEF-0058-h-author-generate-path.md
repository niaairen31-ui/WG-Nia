# BRIEF — Step "entity sheet: AI draft path"

Ticket: TICKET-0058. Requires BRIEF-0058-g landed.

## Context

`authorRenderGeneratePanel` (`index.html:7771`), `authorGenerateEntity`
(`7785`) and the three `authorApply*Draft` functions are the sheet's AI
assist: a model drafts a character, location or faction, the creator sees the
draft in the form, and nothing reaches canon until the creator submits.

This is the part of the sheet where the project's central doctrine is
visible in the UI, so it is migrated last and alone. The failure mode to
avoid is not visual: it is a port that quietly lets a draft reach a save
call without the creator's submit.

## Scope IN

1. **`frontend/src/creation/GeneratePanel.svelte`.** Port the panel and the
   generate call. Preserved exactly:
   - The draft populates FORM STATE only. There is no path from a model
     response to a write call in this component. The only save is the one
     brief -f already owns, triggered by the creator.
   - `authorApplyCharacterDraft` / `authorApplyLocationDraft` /
     `authorApplyFactionDraft` become one apply step per target type, each
     mapping declared fields; an unknown field in a draft is ignored, never
     written blind.
   - Generation notes (`authorRenderGenNotes`) render as creator-facing
     annotation, not as canon.
   - Prompt selection and model dispatch continue through the existing
     endpoints; no prompt text moves into the frontend.

2. **Structural link ids stay server-side.** The model never resolves an
   entity id or a relation target in this path. If the port surfaces any
   place where a draft carries an id that the frontend resolves, STOP and
   escalate - that is a doctrine violation to report, not to preserve.

3. **`index.html`.** Delete the ported functions; extend the island entry's
   retired coverage.

4. **Retire the reverse-direction save bridge** if brief -j has already
   landed and no legacy caller of `_authorSaveSubmit` remains. If callers
   remain, leave it and say so.

## Scope OUT

- **Changing any prompt, model, or rubric.** `prompt_registry.py`,
  `prompt_version.py`, `prompt_lean.py` and `prompt_model_write.py` must
  pass unchanged.
- **Adding an auto-apply, auto-save, or "accept all" control.** The creator
  submits, one record at a time, as today.
- **Touching `proposed_mutation` or the review queue.** Brief -i.
- **Any backend change.**

## Invariants to defend

- **Model proposes, code judges.** The single most important line in this
  brief.
- **AI never authors canon directly.** The draft path ends at form state.
- **`proposed_mutation` is the sole gate for AI-proposed changes** - this
  path is creator-CRUD after a creator's submit, and must not become a
  second route into canon.
- **Model extracts, code judges** - no id resolution client-side.

## Done means

- [ ] `python tooling/verify/checks/prompt_model_write.py`,
      `prompt_registry.py`, `prompt_lean.py` exit 0.
- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0.
- [ ] Live: generate a character draft; confirm the form is populated and
      NOTHING is persisted until save; navigate away without saving and
      confirm no record was created.
- [ ] Live: same for a location and a faction.
- [ ] Live: generation notes render and are not persisted as canon.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None. Brief -l.
