# BRIEF — Step "The gaps view: holes in the world, read-only"

## Context

`skill_resolution` has been collecting `unmatched` rows since BRIEF-0084-c —
every time the arbiter named something the world's catalogue does not cover.
Today those rows are only reachable by SQL. This step gives them a surface:
Creation shows the distinct unmatched strings, most frequent first, so Nia can
see what her players keep trying to do that her world has no rules for, and
author a skill for it. Read-only by design — the view never writes, and
creating the skill goes through the catalogue form that already exists.

## Mini-RECON (executor, before any edit)

BRIEF-0084-b and -c have both landed. Run this and **report before editing**;
STOP on any mismatch.

1. Report the final shape of `skill_resolution` as built by BRIEF-0084-c —
   column list, the two CHECK constraints, and the two indexes. Confirm
   `idx_skill_resolution_world_verdict` exists, since this view's query depends
   on it.
2. Report how BRIEF-0084-b implemented the systems list in Creation (files,
   store, fetch/re-fetch mechanism). This view reuses that shape; it does not
   introduce a second one.
3. Report whether Creation has an existing **read-only panel** anywhere (a list
   with no create/edit affordance). If one exists, report its files — this view
   copies it. If none exists, say so and report the closest analogue.
4. Report the exact count of rows currently in `skill_resolution` grouped by
   verdict in the dev DB, and the distinct `unmatched` surface forms present.
   If there are fewer than three distinct unmatched forms, say so — the live
   gate needs real data, and Nia may need to play a few turns first.
5. Report whether the two literals `__arbiter_error__` and `__arbiter_empty__`
   are present among the unmatched rows.

## Scope IN

1. **A read-only "Trous du lexique" panel in Creation**, in the same area as
   the skill catalogue, reusing the pattern reported by mini-RECON step 3.

2. **New endpoint `GET /api/skill-gaps`** in
   `src/world_engine/cockpit/crud/skills.py`, next to the skill-system block.
   Returns, for the active world, one entry per distinct `surface_form` among
   `verdict='unmatched'` rows:

   ```
   { "surface_form": str, "count": int, "last_seen": iso8601 }
   ```

   Ordered by `count` descending, then `last_seen` descending. Read-only: this
   function performs no write of any kind.

3. **The two arbiter-failure literals are excluded from the list and reported
   separately.** `__arbiter_error__` and `__arbiter_empty__` are not holes in
   the world; they are Ollama being unwell. The endpoint returns them in a
   separate field:

   ```
   { "gaps": [...], "arbiter_failures": { "error": int, "empty": int } }
   ```

   The panel renders `gaps` as the list, and the failure counts as a single
   discreet line beneath it, shown only when either count is non-zero. Exact
   wording of that line:

   ```
   Échecs de l'arbitre (hors lexique) : {error} erreur(s), {empty} réponse(s) vide(s)
   ```

4. **Each gap row offers one action: prefill the skill-definition form.**
   Clicking a gap opens the existing catalogue create form with `name`
   prefilled from `surface_form`, `base_domain` unset, `system_id` unset. It
   does not create anything. Nia fills the rest and submits through the
   existing endpoint.

5. **Empty state.** When `gaps` is empty, the panel renders this exact text and
   nothing else:

   ```
   Aucun trou détecté — tout ce que l'arbitre a nommé est déjà dans le catalogue.
   ```

## Scope OUT

- **Any write to `skill_resolution`.** Not a dismiss action, not an "ignore
  this gap" flag, not a resolved marker, not a delete. The table is append-only
  and this step is its reader, full stop. If a gap should disappear from the
  list, it is because a skill now matches it and future turns stop producing
  it — never because this view mutated history.
- **Auto-creating a skill from a gap.** Item 4 prefills a form; a human
  submits it. No one-click creation, no bulk create.
- **Proposing gaps to a model, or germinating them as `ProposedMutation`
  rows.** G2 was considered and rejected in favour of G3; a lexicon hole is
  creator telemetry, not a pending canon mutation.
- **Fuzzy grouping of similar surface forms** ("évocation" and "evocation"
  shown as one gap). That is C3b's territory, still deferred; the list shows
  distinct strings exactly as stored, which is precisely the evidence C3b's
  reactivation condition needs.
- **Retention, pruning, pagination beyond a simple cap, or a date filter.**
- **Showing `base` or `matched` rows anywhere in the UI.** They exist for the
  audit trail and the C3b count, not for display.
- **Anything touching Play, the resolver, or the day chain.**
- **`world.magic_status`.** BRIEF-0084-e.

## Invariants to defend

- **Append-only holds.** `skill_resolution_append_only.py` must still pass
  after this step; the new endpoint adds a read site only.
- **No second write authority.** Item 4 routes through the existing
  `POST /api/skill-definitions`; it does not write a definition itself.
- **`json_ui_boundary.py`** — the endpoint returns a flat list plus a small
  object; check what that rule permits before shaping the response.
- **World scoping.** The query filters on the active world via `_world_id(db)`,
  the same as every other function in that module. A gap from another world
  must never appear.

## Done means

- [ ] `GET /api/skill-gaps` on a world with a live session's rows returns the
      distinct unmatched strings with correct counts, most frequent first,
      verified against `sqlite3 <db> "SELECT surface_form, COUNT(*) FROM
      skill_resolution WHERE verdict='unmatched' AND world_id='<id>' GROUP BY
      surface_form ORDER BY 2 DESC"`.
- [ ] `__arbiter_error__` and `__arbiter_empty__` do NOT appear in `gaps`, and
      their counts appear in `arbiter_failures`.
- [ ] With Ollama stopped, three Play turns increment `arbiter_failures.error`
      by 3 and add nothing to `gaps`.
- [ ] Clicking a gap opens the create form with `name` prefilled and nothing
      submitted; cancelling leaves `skill_definition` row count unchanged.
- [ ] Submitting it creates the skill; the gap remains listed (history is not
      rewritten) but subsequent Play turns naming that term now write
      `matched`, verified by one live turn.
- [ ] On a world with no unmatched rows, the panel shows the exact empty-state
      text from item 5.
- [ ] `SELECT COUNT(*) FROM skill_resolution` is identical before and after a
      full session of browsing the panel.
- [ ] `python -m tooling.verify.checks.skill_resolution_append_only` returns
      PASS.
- [ ] `pytest`, `json_ui_boundary.py`, `stylesheet_partition.py` green.
- [ ] `/review-step` and `/close-step` both run.
- [ ] One commit.

## Docs to update

- No schema change: **no changelog entry, no version bump.**
- `CLAUDE.md` — one line naming `GET /api/skill-gaps` as read-only and stating
  that the two arbiter-failure literals are excluded from the gap list by
  design.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — record that G3 is discharged,
  that G2 (germinating gaps as `ProposedMutation` rows) was considered and
  rejected because a lexicon hole is creator telemetry rather than a pending
  canon mutation, and that its reactivation condition is Nia asking for
  one-click creation from the gaps list.
