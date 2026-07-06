# BRIEF-0011-b — Cockpit prompt editing UI: edit mode, history list, restore

Ticket: TICKET-0011. Predecessor: BRIEF-0011-a (CLOSED — main @ v1.68).
Locked UI decisions: **U1** (explicit edit mode), **V1** (collapsible lazy
history + per-version read-only view), **W1** (one-click restore with
self-explanatory label), **X1** (dirty guard on selection change).
Non-optional invariant: a 422 is shown **inline under the form** with the
offending placeholder names — fail-closed must be visible, never silent.

All anchors below verified against pushed main (2026-07-06, schema v1.68).
Single file touched: `src/world_engine/cockpit/index.html` (+ small doc
append). No Python changes — the API shipped in -a is consumed as-is.

---

## Context — what -a delivered (consumed here, not modified)

- `GET  /api/prompts/{id}` (crud.py:1629) → detail incl. `version`
  (current number), `system_prompt`, `user_template`, `variables`.
- `GET  /api/prompts/{id}/versions` (crud.py:1680) → newest-first
  `{versions: [{version_number, created_at, note, is_current}]}` — no bodies.
- `GET  /api/prompts/{id}/versions/{n}` (crud.py:1697) → summary + bodies.
- `PATCH /api/prompts/{id}/text` (crud.py:1724) — body
  `{system_prompt, user_template, note?}` → 200 version summary; **422**
  `detail: "Undeclared placeholder(s): a, b"`; 404 unknown head.
- `POST /api/prompts/{id}/versions/{n}/restore` (crud.py:1752) → 200 new
  summary (note auto `restored from v{n}`); 422 possible (C1 re-validates).

Client machinery in place:
- `api()` helper (index.html:1419) throws `Error(data.detail)` — the 422
  message arrives as `err.message`.
- Detail pane: `#prompts-detail-body` (index.html:1360), state
  `promptsSelectedId` / `promptsCurrentDetail` (3552/3558), loader
  `promptsSelectDetail` (3644), single renderer `_promptsRenderDetail`
  (3725) — bodies rendered as two `<pre>` blocks with
  `_promptsHighlightTokens`.
- Token helpers already exist for the drift panel:
  `_promptsExtractTokens`, `_promptsHighlightTokens` (used at 3726-3734).
- Write-flow precedent: model PATCH handler (3701-3712) — call `api()`,
  update state, re-render the detail pane.

## Scope IN

### 1. Edit mode (U1)

- New state: `promptsEditMode` (bool), `promptsEditDirty` (bool) — reset in
  the tab-reset block (3562-3565) and on every `promptsSelectDetail`.
- `_promptsRenderDetail` gains an *Edit* button next to the bodies when
  `!promptsEditMode`. Clicking it re-renders the SAME pane in edit state —
  **one renderer, two states**; no duplicate detail renderer may be
  introduced (the fidelity lesson: a second render path is where drift
  breeds).
- Edit state replaces the two `<pre>` bodies with two `<textarea>`
  prefilled from `promptsCurrentDetail.system_prompt` / `.user_template`,
  plus one optional single-line *note* input, plus *Save* / *Cancel*.
  Everything else in the pane (model selector, call sites, preview panel)
  renders unchanged and stays functional.
- Any input in either textarea or the note sets `promptsEditDirty = true`.
- *Cancel* → confirm if dirty (same wording as X1 guard), then re-render
  read state from the unchanged `promptsCurrentDetail`.

### 2. Live placeholder hint (advisory only — server stays the judge)

On textarea input, run `_promptsExtractTokens` over both drafts; any token
not in `promptsCurrentDetail.variables` renders a small warning line under
the form: `Will be rejected: {names}` (muted/warning style, same visual
family as the existing drift panel at 3731-3734). This is a courtesy
preview of C1 — it must NOT block *Save*; the server's 422 is the only
authoritative refusal.

### 3. Save flow

- *Save* → `PATCH /api/prompts/{id}/text` via `api()` with the two drafts +
  note (omit note if empty).
- Success → clear edit state, then **refetch** the detail through the
  existing `promptsSelectDetail(promptId)` — never patch
  `promptsCurrentDetail` locally with draft text; the server's canonical
  read is the single source (mirrors the fidelity doctrine, and picks up
  the new version number for free). If the history section is expanded,
  refresh it too (§4).
- Failure → stay in edit mode, drafts intact, and render the error inline
  under the form: `err.message` in an error-styled div (the 422 arrives as
  `Undeclared placeholder(s): …`). No alert(), no console-only failure.

### 4. History section (V1)

- New collapsible section *History* at the bottom of the detail pane
  (below the drift panel / preview panel), collapsed by default.
- First expansion → `GET /api/prompts/{id}/versions` (lazy — never fetched
  for a prompt whose history is not opened). Cache per selected prompt;
  invalidate + refetch after every successful save or restore while
  expanded.
- Each entry: `v{version_number} · {created_at} · {note ?? ''}` + a
  `current` badge on `is_current` (accent style, same family as the
  `effectif` badge at 3744).
- Clicking an entry → `GET /api/prompts/{id}/versions/{n}` → read-only
  body view for that version (two `<pre>` with `_promptsHighlightTokens`,
  same styling as the current bodies), inside the history section, with
  the restore control (§5). Clicking the current version shows it without
  a restore control (restoring the current version is a no-op by
  definition — don't offer it).

### 5. Restore (W1)

- Button label is self-explanatory and computed:
  `Restore v{n} as new v{next}` where `next = current + 1` from the loaded
  history. One click, no modal — append-only makes it non-destructive by
  construction.
- → `POST /api/prompts/{id}/versions/{n}/restore`; success → refetch
  detail (promptsSelectDetail) + refresh history. 422 → same inline error
  treatment as §3, rendered inside the history section next to the button.

### 6. Dirty guard (X1)

- If `promptsEditDirty` and the user clicks another prompt in the master
  list (`promptsSelectDetail`) — or the tab-reset path fires — `confirm()`
  before discarding: "Unsaved prompt edit will be lost — continue?".
  Decline → abort the selection change, edit state untouched.
- Nothing more: no beforeunload hook, no draft persistence (Scope OUT).

### 7. Docs

- `ARCHITECTURE_DECISIONS.md` — append the U1/V1/W1/X1 record under the
  TICKET-0011 entry (one short block; registry is append-only).
- `CLAUDE.md` — no change expected (no new invariant beyond -a's; the
  single-renderer rule in §1 is brief-local guidance). If the executor
  believes a CLAUDE.md line is warranted, it must fit the existing line
  budget (claude_md_contract check).

## Scope OUT (named)

- Version diff view (side-by-side or unified) — no ticket, no reader yet.
- Editing `variables`, `name`, `usage`, `notes`, `is_active` — B2
  territory and beyond; the text route writes text only.
- Draft persistence / autosave / localStorage — nothing survives a reload.
- History pagination — 18 global templates, low edit volume; revisit only
  if a real prompt accumulates unwieldy history.
- Keyboard shortcuts, mobile layout, animations.
- Any change to Python files, routes, schema, or seed.

## Invariants to defend

1. One detail renderer (`_promptsRenderDetail`), two states — no duplicate
   render path for the detail pane.
2. Server C1 is the sole authoritative validation; the client hint never
   blocks and never substitutes.
3. After any successful write, displayed state comes from a fresh server
   read — never from locally-patched drafts.
4. History is lazy: zero version fetches for prompts whose history is
   never opened.
5. 422 failures are visible inline where the action happened; drafts are
   never lost on failure.
6. The restore control never appears on the current version.

## Done means (live gates — Nia)

- [ ] Edit `pt-mj-narration`, save → detail shows v+1; the next assembled
      preview / model call uses the new text.
- [ ] Save text containing `{typo_var}` → inline error naming `typo_var`,
      drafts still in the textareas, version list unchanged.
- [ ] Expand History → all versions newest-first with `current` badge;
      open v1 → read-only body; `Restore v1 as new v{next}` → history now
      shows the new head with note `restored from v1`.
- [ ] Start an edit, click another prompt → confirm dialog; decline keeps
      the edit intact; accept discards it.
- [ ] Collapse/never-open History on another prompt → no `/versions`
      request fired (network tab).
- [ ] Verify suite green (page_contract + claude_md_contract untouched or
      still passing).
