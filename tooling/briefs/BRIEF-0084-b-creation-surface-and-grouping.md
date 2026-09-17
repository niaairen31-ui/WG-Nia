# BRIEF — Step "Creation surface for skill systems, and catalogue grouping"

## Context

BRIEF-0084-a landed `skill_system` and `skill_definition.system_id` with a CRUD
but no surface, so the table is one commit old and still unread. This step is
its reader: Creation gains a system editor, and the skill catalogue displays
grouped by system. Nothing mechanical changes — no roll, no prompt, no
resolution. After this step a creator can say "magic exists in this world" by
creating a system and hanging skills under it, which is the whole of B3's
ergonomics.

## Mini-RECON (executor, before any edit)

BRIEF-0084-a moved lines in `crud/skills.py` and `models/canon.py`, and the
frontend was never surveyed for this ticket. Run this first and **report the
findings before editing**; if any of the five come back differently than the
assumptions in Scope IN, STOP and report rather than adapting silently.

1. Where does Creation render the skill catalogue today? Find the Svelte
   component and the store that hold `skill-definitions`, and report the file
   paths plus how the list is fetched and re-fetched after a write.
2. What is the established pattern in Creation for a **two-level list** (a
   container and its children) — does one already exist (factions and their
   roles? locations and their subcultures?), and if so which files implement
   it? Report the pattern to be copied; do not invent a new one.
3. How does Creation handle a **409 from a delete** today? Find one existing
   refusal path and report how the message reaches the user (toast, inline,
   modal). The system-delete refusal must reuse it, not add a new idiom.
4. Confirm `GET /api/skill-systems` returns `skill_count` as specified in
   BRIEF-0084-a item 4, and report the exact JSON shape of both
   `/api/skill-systems` and `/api/skill-definitions` as they now stand.
5. Report whether any stylesheet partition rule applies to the files you are
   about to touch (`tooling/verify/checks/stylesheet_partition.py` exists —
   read what it enforces before adding a class).

## Scope IN

1. **A system editor in Creation**, following the pattern reported by
   mini-RECON step 2. List of the world's systems, each showing `name`,
   `description`, and `skill_count`. Create, rename, edit description, delete.
   All four call the endpoints from BRIEF-0084-a; no new endpoint is added in
   this step.

2. **Delete refusal surfaced legibly.** A 409 from
   `DELETE /api/skill-systems/{id}` shows the server's message verbatim through
   the existing refusal idiom found in mini-RECON step 3. The list does not
   optimistically remove the row before the server answers.

3. **The skill catalogue renders grouped by system.** One group per system,
   ordered by system name, each group headed by the system `name` with the
   `description` as its subtitle. Skills sort by name within a group. Skills
   with `system_id` NULL appear last, under a group whose header is exactly:

   ```
   Sans système
   ```

   That group is always rendered when it is non-empty, and never rendered when
   it is empty. An empty system (`skill_count` 0) IS still rendered, with its
   header and an empty body — a system Nia just created must be visible before
   she has anything to put in it.

4. **The skill-definition form gains a system selector.** A dropdown listing
   the world's systems plus an explicit no-system option labelled exactly:

   ```
   Sans système
   ```

   It submits `system_id` (or `null`) on both create and edit. Default on a
   fresh form is no system.

5. **No fetch storm.** Systems are fetched once per Creation load and
   re-fetched after any system write, using whatever re-fetch mechanism
   mini-RECON step 1 reports for skill definitions. Do not fetch systems per
   skill row.

## Scope OUT

- **Any backend change.** No new endpoint, no change to a response shape, no
  model change, no migration. If the frontend needs a field that does not
  exist, STOP and report — do not add it here.
- **Drag-and-drop reassignment, bulk move, or reordering systems.** The
  dropdown in item 4 is the only way to attach a skill in this step.
- **Showing `base_domain` differently, collapsing groups, or any other redesign
  of the existing skill list** beyond adding the grouping level.
- **`roll_spec`, rules text, or lore fields on the system editor.** The system
  has `name` and `description` and nothing else.
- **The gaps view.** BRIEF-0084-d.
- **Anything in `cockpit/play_physical.py` or the resolver.** BRIEF-0084-c.
- **`world.magic_status`.** BRIEF-0084-e.
- **The world-creation form.** Not touched, in any brief of this ticket.

## Invariants to defend

- **"JSON never crosses the UI boundary as structure"** —
  `tooling/verify/checks/json_ui_boundary.py` exists and this step adds a
  nested rendering. Read what that check enforces before shaping the grouped
  payload, and group in the component from two flat lists rather than inventing
  a nested endpoint response.
- **No second write authority.** The frontend calls the CRUD from
  BRIEF-0084-a. It does not write to any other endpoint to achieve the same
  effect.
- **Static asset freshness** — `static_asset_freshness.py` is an existing
  check; whatever build or copy step it guards must be run before the live
  gate, or the surface will not be what is tested.
- **"No structure without a reader"** is discharged by this step: after it,
  every column of `skill_system` is displayed.

## Done means

- [ ] Creation shows a systems list; creating "Magie" makes it appear without a
      page reload.
- [ ] Renaming it to "L'Art" is reflected in both the systems list and the
      catalogue group header.
- [ ] A system with zero skills renders with its header and an empty body.
- [ ] Creating a skill with the system selector set to "Magie" places it under
      the Magie group; setting it back to "Sans système" moves it to the last
      group.
- [ ] `DELETE` on a system with skills attached shows the server's refusal
      message and the row stays in the list.
- [ ] After detaching its last skill, deleting the system removes it, and the
      detached skill appears under "Sans système".
- [ ] A world with no systems at all renders the catalogue exactly as it did
      before this step, under a single "Sans système" group.
- [ ] `python -m tooling.verify.checks.json_ui_boundary` and
      `stylesheet_partition` return PASS.
- [ ] `pytest` green; `/review-step` and `/close-step` both run.
- [ ] One commit.

## Docs to update

- No schema change, so **no changelog entry and no version bump.**
- `CLAUDE.md` — one line in the Creation paragraph naming the systems editor
  and the grouped catalogue, and stating that "Sans système" is a rendered
  group, not a stored row.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — append to this ticket's
  section that F2 is discharged: `skill_system`'s first and only reader is the
  Creation surface, and it is a display reader by design; no assembler, guard,
  or roll reads this table as of TICKET-0084.
