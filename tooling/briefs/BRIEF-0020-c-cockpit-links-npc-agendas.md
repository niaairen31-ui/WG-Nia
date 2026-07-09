# BRIEF — Step "cockpit: NPC-owned intrigues, link attach/detach, review rendering (BRIEF-0020-c-cockpit-links-npc-agendas)"

## Context

Structure (0020-a) and tick readers (0020-b) are live; the creator's
half of C4 is not: the cockpit cannot author an NPC intrigue, cannot
attach or detach a goal<->agenda link, and renders `agenda_delegation`
proposals as raw payloads. This brief closes the creator loop.
Grounding: Intrigues surface + CRUD (crud.py:544-560, 1125+;
index.html agenda blocks); creator supremacy = the creator can do by
hand everything the tick can propose, plus detach.

## Scope IN

1. **CRUD (`src/world_engine/cockpit/crud.py`)**:
   - Agenda creation endpoint: accept character owners — validation
     already lives in `write_agenda` (0020-a); surface the helper's
     ValueError (one-active-personal-agenda, wrong type) as the
     endpoint's error message, not a 500.
   - `_agenda_dict`: add `owner_type` and `owner_name` (resolved via
     Entity) so the UI can group/badge faction vs personal intrigues;
     add `linked_goals`: active links with goal id, description,
     status, and link id.
   - New endpoints, thin wrappers over the 0020-a helpers only:
     `POST .../goal-agenda-links` (goal_id, agenda_id) ->
     `write_goal_agenda_link(created_by="creator")`;
     `POST .../goal-agenda-links/{link_id}/detach` ->
     `detach_goal_agenda_link(detached_by="creator")`. ValueErrors
     surface as 4xx messages. NO delete endpoint exists.
   - Goal payloads (wherever goals are listed for a character sheet)
     gain their active links (agenda id + title + link id).

2. **UI (`src/world_engine/cockpit/index.html`)**:
   - Intrigues surface: owner picker offers factions AND active
     characters (grouped, labelled); list badges personal intrigues
     (owner name) vs faction ones; agenda card lists linked goals
     (description + owning NPC) with a detach control per link.
   - Character sheet goal rows: render `(sert : « <title> »)` for
     active links + an attach control (select among ACTIVE agendas)
     and detach per link. Creator view is FULL — no D1 gating in the
     cockpit (the gate is a prompt-boundary rule, not a creator one).
   - Confirm dialog on detach (soft, reversible — say so in the
     dialog text).

3. **Review queue rendering (`index.html` + any payload-preview
   helper)**: `agenda_delegation` proposals render human-readably:
   NPC name, goal text, horizon, agenda title (ids resolved), plus
   the rationale — same treatment level as agenda_step_change cards.
   Per-NPC `agenda_creation` cards show the forced owner's name.

4. **Docs**: this step IS the doc update for the cockpit surface;
   append one ARCHITECTURE_DECISIONS line only if a drafting deviation
   occurs (none expected).

## Scope OUT

- No new write logic: every canon write goes through the 0020-a
  helpers; the cockpit adds zero business rules.
- No hard delete of links anywhere, including admin affordances.
- No editing of link rows (no re-pointing a link — detach + attach).
- No dialogue/tick/prompt changes (0020-b closed them).
- No bulk link operations, no link display in the pipeline cockpit.

## Invariants to defend

- **Single canon-write paths**: endpoints are wrappers; a
  GoalAgendaLink constructed in crud.py fails
  `single_canon_write.py`.
- **Creator supremacy**: manual close of an agenda still cascades
  (0020-a behaviour) — the UI must not "protect" the creator from it;
  the confirm dialog on closing an agenda WITH active links states
  that linked single-parent goals will follow (M1).
- **History is sacred**: detach-only, no delete.

## Done means

- [ ] Create a personal intrigue for an NPC in the cockpit; creating
      a second one for the same NPC surfaces the helper's error
      message verbatim (no 500).
- [ ] Attach a goal to two agendas; detach one; re-attach it —
      all through the UI; DB shows detached row preserved
      (detached_at/by set) plus the new active row.
- [ ] Close an agenda from the cockpit with one single-parent linked
      goal: confirm dialog mentions the cascade; after confirm, the
      goal is transitioned (M1) — visible on the character sheet.
- [ ] An `agenda_delegation` proposal renders with resolved names in
      the review queue; approving it from the queue works end-to-end
      (regression on 0020-b).
- [ ] Full suite green: `tooling/verify/run.py` (single_canon_write
      must pass with the new endpoints present).
- [ ] /review-step and /close-step run.

## Docs to update

None beyond Scope IN item 4 — no schema, no doctrine change.
