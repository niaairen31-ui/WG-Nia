# BRIEF — Step "doctrine seal + docs"

Ticket: TICKET-0059. Requires BRIEF-0059-l landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendments 4, 5, 7 and 8**. Cites
RECON-0059-a **M7**, **M8**.

**Anchor convention.** Line numbers are indicative. Locate by heading or
identifier; verify locally.

## Context

The `creation` legacy mount is retired and every Creation surface is Svelte.
This brief writes down what happened, corrects two records that were shown
wrong during execution, and closes the ticket. It ships **no behaviour
change** — one non-doc edit is permitted and is named explicitly in item 8.

Two corrections are load-bearing, because both are the kind of error that
compounds: a planning document that misdescribes the code, and a RECON claim
whose scope was narrower than its wording.

## Scope IN

### Commit 1 — architecture decisions

1. **`ARCHITECTURE_DECISIONS.md`** (append-only) gains one TICKET-0059
   section recording, each in a few lines with its reason, not just its fact:

   - **The bridge-reach seam and its shrinking baseline.** Why the seal is
     scoped to `callLegacy` rather than the string `legacyCall`: eight named
     wrapper exports reach the same primitive, and a check that greps the
     string would have been blind to all of them. Note that `legacy_call.py`
     rule 2 *derives* the reaching surface from `bridge.js` rather than
     hardcoding names, so a tenth wrapper is caught automatically. Record
     that rule 7 structurally ordered the mount retirement after the seam
     closure.
   - **`LocationTree.svelte`** and its lock. Record that the two agent
     pickers were **not** a copy-paste — single-select radio versus
     multi-select checkbox with ancestor inheritance — and that the
     resolution was a row snippet rather than a `mode` enum, because an
     interaction-model enum inside a component is a union type, not a
     convergence.
   - **`Modal.svelte`** and its lock, landed only once the legacy
     implementation died, with no allow-list.
   - **The effect-cycle rule** (TICKET-0062, cross-referenced here because it
     was discovered inside this ticket's live testing): pure derivations of
     props are `$derived`, not `$state`, and assign-then-read of a `$state`
     binding inside one `$effect` body is forbidden by
     `effect_self_write.py`. **Include the observed failure mode** — a flush
     aborted by `effect_update_depth_exceeded` silently stops *sibling*
     components repainting — because the symptom is far from the cause and
     the next person to hit it will not connect them.
   - **The three-surface census rule.** RECON-0059-a M5 claimed no
     cross-reads existed; the claim was a two-surface search (Play,
     Creation), and `observationOpenPrompt` was found only during `-i`'s
     execution. Record the rule that supersedes it: caller censuses cover
     Play, Creation **and** Observation.

2. **Named deferrals**, each with an explicit reactivation condition:

   - **D-0059-prompts-surface** — promoting the prompts tab out of Creation
     into its own top-level surface. Reactivate when a second creator-tooling
     surface appears, or when D-0050 activates and the two would share a
     home.
   - **D-0059-npc-agent-termination** — the NPC agent's run loop detects
     completion by catching an error and string-matching
     `'already fully generated'`, while the link agent reads a `result.done`
     flag. Reactivate when either endpoint's contract is next touched; a
     backend message edit silently breaks the loop today.
   - **D-0050** is **re-stated verbatim, not modified** (Amendment 5): the
     conversation-window config still renders inside the Prompts pane, and
     its reactivation condition is unchanged.

3. **`DECISIONS_INDEX.md`** is regenerated with `gen_decisions_index.py`.
   Never hand-edited; if it conflicts, regenerate rather than resolve.

### Commit 2 — doctrine text

4. **`CLAUDE.md`** — law only, 500-line budget, no inline brief archaeology.

   - Amend the frontend doctrine line: the cockpit is a Svelte application
     with a build step, served from built assets. The no-build assertion and
     the "splitting index.html is a doctrine change, not a refactor" line
     are now historically false and must go.
   - Amend the file-tree note: `index.html` is no longer the single-page UI.
     Describe what it still is — the legacy host for Play and Observation
     until TICKET-0060/0061.
   - Update the check inventory with `legacy_call.py`, `location_tree.py`,
     `modal_primitive.py`, `effect_self_write.py`, and the frontend rule
     added to `module_budget.py`.
   - **Do not add narrative.** If the section would grow past its budget,
     what to cut is the older prose, not the new law.

5. Verify `claude_md_contract.py` still passes, including its pointer
   freshness assertions.

### Commit 3 — record corrections

6. **`Active project.md`** — correct PART A's **A2** interleaving claim for
   the queue cluster. It asserted the batch/mutation review code was wedged
   inside Play scene code at `~2801-3300`; RECON-0059-a M5 measured it and it
   is not — the queue functions form a contiguous cluster after the Play
   scene functions, and `-k` ported them without unpicking anything. Correct
   the text; do not delete the paragraph. A workstream map that quietly loses
   a wrong claim teaches nothing.

7. **`Active project.md`** — correct the TICKET-0059 scope sketch. It
   predicted "region authoring, prompts, intrigues, evenements, competences,
   factions roster, link agent, world CRUD" and predicted region and
   evenements would land here; both landed in TICKET-0058 instead, and the
   agents, the Review Queue and the whole chrome inversion landed here and
   were not in the sketch. State what the ticket actually contained.

8. **`world-engine-schema.md`** is **not** touched. This ticket changed no
   schema; its `schema_version_touched` field is empty and stays empty. Named
   here so that no one adds a courtesy changelog entry for a frontend ticket.

### Commit 4 — ticket closure

9. Set `TICKET-0059`'s `status: done` and fill `brief_ids` with the full
   chain `-a` through `-m`. Record in the ticket that `-b` was reissued as v2
   after RECON-0059-a M1, that `-e` was re-scoped by Amendment 3, that `-k`
   was re-cut by Amendment 4, and that TICKET-0062 was inserted between `-d`
   and `-e`.

10. **The one permitted non-doc edit.** If any check's header comment still
    describes a target that moved during this ticket — `page_contract.py`,
    `creation_island.py`, `creation_return_nav.py` and `legacy_call.py` are
    the candidates — correct the comment text only. **No rule logic changes
    in this brief.** A rule that needs changing is a finding and a separate
    ticket, not a docs commit.

## Scope OUT

- **Any behaviour change**, any component edit, any rule-logic edit. Item 10
  is comment text only.
- **Deleting `index.html`.** TICKET-0061. It still hosts Play and
  Observation.
- **`observation_surface.py` or anything `observation*`.** TICKET-0060.
- **Activating D-0050 or either D-0059 deferral.** Recording a deferral is
  not resolving it.
- **Hand-editing `DECISIONS_INDEX.md`.** Item 3.
- **Adding a schema changelog entry.** Item 8.
- **Rewriting `Active project.md`'s ticket plan for 0060/0061.** Those
  tickets open their own conversations and re-RECON. Correcting a false
  finding about the *past* is in scope; re-planning the future is not.
- **Growing `CLAUDE.md` past its budget.** Item 4.

## Invariants to defend

- **`CLAUDE.md` is law-only.** No brief history, no migration narrative. The
  story goes in `ARCHITECTURE_DECISIONS.md`.
- **`ARCHITECTURE_DECISIONS.md` is append-only**, and every deferral carries
  an explicit reactivation condition — a deferral without one is a decision
  quietly abandoned.
- **`DECISIONS_INDEX.md` is generated.** Regenerate, never edit.
- **Corrections are made visibly.** Items 6 and 7 amend wrong claims in
  place rather than deleting them.
- **Docs describe what shipped**, not what the plan said would ship.

## Done means

- [ ] `ARCHITECTURE_DECISIONS.md` contains the TICKET-0059 section with all
      five recorded decisions and all three deferrals, each with a
      reactivation condition.
- [ ] D-0050's text is byte-identical to its previous statement.
- [ ] `DECISIONS_INDEX.md` regenerated by `gen_decisions_index.py`; `git
      diff` shows only generated content.
- [ ] `CLAUDE.md` contains no assertion that the frontend has no build step,
      and none that splitting `index.html` is a doctrine change.
- [ ] `CLAUDE.md`'s check inventory lists `legacy_call.py`,
      `location_tree.py`, `modal_primitive.py`, `effect_self_write.py`.
- [ ] `CLAUDE.md` is within its 500-line budget;
      `claude_md_contract.py` exits 0.
- [ ] `Active project.md` A2's queue-interleaving claim is corrected in
      place, with the correction attributed to RECON-0059-a M5.
- [ ] `Active project.md`'s TICKET-0059 section describes what the ticket
      actually contained.
- [ ] `world-engine-schema.md` and `world-engine-schema-changelog.md` are
      untouched; `TICKET-0059`'s `schema_version_touched` is empty.
- [ ] `TICKET-0059` is `status: done` with the full `brief_ids` chain and the
      four amendment notes.
- [ ] `git diff --stat` shows only `.md` files, plus at most comment-text
      edits to the four named checks.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] Every live gate criterion in TICKET-0059 is checked off by Nia before
      this brief's closure commit.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

This brief IS the doc update.
