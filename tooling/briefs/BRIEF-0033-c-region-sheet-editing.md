# BRIEF — Step "Region review: editable zoom sheet" (BRIEF-0033-c)

## Context

The review-screen zoom sheet (`regionRenderSheet`, `index.html:9233`) is
display-only (`_sheetField` renders text). The commit route consumes the
client-held draft and re-derives the whole cascade server-side
(`routes/regions.py:359` docstring: "untrusted client-held state — re-sent,
not server-persisted"), so edits written into `regionDraft` flow to the
committed entities with NO backend change. Locked: B1 (sheet becomes the
editing surface; the tree stays scannable) + F1 (faction roles editable in
the sheet, landed by BRIEF-0033-a's commit fix). Depends on -a being merged
first (roles otherwise edited into the void).

## Scope IN

1. `regionRenderSheet` becomes an editable form. Every field currently
   rendered via `_sheetField` / `_sheetListSection` gets an input bound by
   `oninput` directly to the draft object (`node.result.draft.public.X` /
   `.secret.X`) — same direct-mutation pattern as the manifest checkpoint.
   Single-line fields (name, physical_tier, faction_type...) -> `<input>`;
   prose fields (description, appearance, backstory, aversion, philosophy,
   internal_structure, internal_tensions, goals, creator_meta) ->
   `<textarea rows=3>`.
2. NPC reassignment: `Faction` and `Lieu` become `<select>`s over the
   draft's factions/locations (`local_id` values; faction has a `--` =
   null option), writing `node.faction_local_id` / `node.location_local_id`
   respectively. Options show current draft names; rejected entities are
   listed too (accept/reject cascade is re-derived at commit — existing
   contract, keep it; visually suffix rejected options with " (rejete)").
3. Location sheet: parent reassignment via the same pattern —
   `node.parent_local_id` select over other locations plus `--` (root
   fallback, matching the commit's re-parent-to-root cascade).
4. F1 — faction roles editor in the faction sheet: rows of
   `{name (input), description (input)}` bound to
   `draft.public.roles[i]`, with per-row remove and "+ Ajouter un role",
   plus up/down reorder buttons (order = committed position, per -a).
   Mirror the look of the NEW-faction roles editor
   (`authorRenderRolesEditor`, `index.html:7316`) but bound to the draft
   array, NOT to `authorFactionRolesDraft`.
5. NPC knowledge rows (secret): each row's subject/level/content editable
   (`level` as a select over `KNOWLEDGE_LEVELS` values already exposed to
   the frontend; if not exposed, a plain input — do not add an endpoint),
   `is_secret` checkbox; per-row remove and "+ Ajouter un savoir" pushing
   `{ subject: '', level: null, content: '', is_secret: true }`.
6. NPC goals: `long` textarea + one input per `shorts` entry with
   add/remove, bound to `draft.public.goals`.
7. On modal close (existing generic-modal close path), call
   `regionRenderAll()` so tree cards reflect renamed entities and
   reassignments. No save button — the draft IS the state.
8. Read-only remnants: `shared_with` suggestions and sensed-links stay
   display-only (they are confirm-by-creator judgment surfaces, not draft
   fields).

## Scope OUT

- NO backend change of any kind: commit route, cores, writes untouched.
- No editing from the tree cards (B2 rejected).
- No pre-commit graphs (that is -d) and no NPC relation editing (that is
  -e; pre-commit staged NPC links are the NAMED DEFERRAL D2 -> next
  ticket — do not build any part of it).
- No new draft fields: only fields the draft already carries become
  editable. If a sheet field has no draft key, it stays read-only.
- No client-side re-validation of knowledge levels or physical tiers
  beyond what the commit path already enforces.

## Invariants to defend

- Single canon-write paths: everything flows through the existing commit
  route and its cores; this step adds zero write calls.
- History is sacred: no mutation of committed entities here — edits apply
  only to the ephemeral pre-commit draft.
- Secrets: secret fields remain in `draft.secret` and are committed
  through the same channels as today; no secret content moves into public
  keys.

## Done means

- [ ] Live: rename an NPC, rewrite its backstory, reassign its faction and
      location, edit a knowledge row, add a goal short; rename a faction
      and edit its roles (add one, remove one, reorder); reparent a
      location -> commit -> every edit is visible on the committed
      entities (entity fields, memberships, current_location_id,
      parent_location_id, knowledge, goals, `GET /api/factions/{id}/roles`
      order matches the sheet).
- [ ] Live: closing the sheet updates the tree card names immediately.
- [ ] `/review-step` and `/close-step` run.
- [ ] All verify checks pass.

## Docs to update

- ARCHITECTURE_DECISIONS.md, TICKET-0033 section: B1 + F1 recorded — the
  zoom sheet is the region-review editing surface; draft-object direct
  mutation; commit path unchanged.
