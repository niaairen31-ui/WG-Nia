<!-- slug: trial-surfaces -->
# BRIEF 0116-F — "Where Nia sees a trial: Compétences, the fiche, the requests panel, the review card"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: BRIEF-0116-B (the CRUD shapes, `trial_ready`), BRIEF-0116-D (the `trial` trigger), BRIEF-0116-E (the proposal's `source_type` and `trial` key)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `GET /api/skill-ranks` serves `trial_to_next`; `GET /api/skill-systems` and `/api/skill-definitions` serve `trial_to_rank_1..5`; `GET /api/skills` serves `trial_ready` (B landed: `cockpit/crud/skills.py` `_rank_step_dict`, `_rank_points`, `_skill_dict`).
- `src/world_engine/quest_designer.py` -> `_trial_payload` adds the `trial` key; a trial's proposal is `source_type="quest_request"` (E landed).
- `frontend/src/creation/competences.svelte.js:59` -> `RANK_POINT_KEYS`; `:61-65` `rankPoints`; `:69-77` `inheritedPoints`; `:90-138` the records (`skillRecord`, `systemRecord`, `ranksRecord`, `draftRecord`, `blankRecord`); `:245-249` `pointsBody`; `:257-278` `saveSkill`, `saveSystem` (each body spreads `...pointsBody(record)`); `:280-293` `saveRanks`.
- `frontend/src/creation/CompetencesSheet.svelte:89-105` -> the `thresholds` snippet (one `field-row` per `RANK_POINT_KEYS` key); `:107-128` the `ranks` record; `:187`, `:209` its two `{@render thresholds()}`; `:29-31` the import from `./competences.svelte.js`.
- `frontend/src/creation/PjSkillFiche.svelte:129-133` -> `pointsLine(s)`.
- `frontend/src/creation/QuestRequests.svelte:16-18` -> `TRIGGER_LABEL` of `route`, `blocked`, `dropped`.
- `frontend/src/creation/QueueCard.svelte:302-307` -> the `TICK` and `JOURNÉE` badges; `:391-395` the quest block (`{#if quest && editable}` ... `{#if questDraft}`).
- `frontend/src/creation/questOffers.svelte.js:185-186` -> `REVIEW_KEYS`.
- `frontend/public/shared.css:150-152` -> `.b-tick`, `.b-pass-play`.

## Facts carried

### R-13 — a proposal's source and the queue [M]
Opened: `src/world_engine/models/pipeline.py:98-150`; `src/world_engine/cockpit/routes/mutations.py:106-123` (`_mutation_dict` serves `source_type`, the three sources); `frontend/src/creation/QueueCard.svelte:159-176`, `:296-312`, `:391-410`; `frontend/src/creation/queue.svelte.js` (filters by status).
Finding: the card shows a « TICK » badge for `world_tick` and « JOURNÉE » for `pass_play`; a proposal with no source shows neither and no `sourceRef`.
Consequence: a trial's proposal (`source_type="quest_request"`) gets its own badge.

### R-14 — Création › Compétences and the fiche [M]
Opened: `frontend/src/creation/competences.svelte.js:1-326`; `frontend/src/creation/CompetencesSheet.svelte:89-128`, `:187`, `:209`; `frontend/src/creation/PjSkillFiche.svelte:129-133`, `:213`.
Finding: thresholds are edited in one snippet rendered on the skill and the system fiche; the ladder record edits each rank's label and points; the fiche reads `GET /api/skills`.
Consequence: the trial selects live in the same snippet (its two renders stay two), the ladder record gains one checkbox per rank below Maître, the fiche's points line names a waiting skill.

### R-16 — the requests panel [M]
Opened: `frontend/src/creation/QuestRequests.svelte:16-18` (`TRIGGER_LABEL` of three triggers, unknown shown raw), `:76-78` (« Jour {r.day_number ?? '—'} »).
Consequence: one label more; a trial row reads « Jour — ».

### R-17 — the existing checks (the lines this brief needs) [M]
- `skill_progression.py:444-446` (A4: no word `tier` in `PjSkillFiche.svelte`), `:742-750` (C3: `sheet.count("{@render thresholds()}") == 2`, `state.count("...pointsBody(record)") == 2`, « Rangs du monde » in the bundle), `:789-797` (D2: `s.xp`, `s.points_to_next`, « rang maximal »);
- `npc_skills.py:576-589` (C2: the fiche's, sheet's and state's patterns);
- `quest_review_card.py` RC1-RC4 (`QueueCard.svelte` names `quest_offer_creation`, `<OfferEditor`, `/api/conditions/view`, `is_character`, `has_met`, `flags_confirmed`, `giver_suggestions`, `proposalBody(`; `proposalBody` copies `request_id`, `pending_drafts`, `flags`, `flags_confirmed`);
- `quest_request_panel.py` RP1 (the five statuses' labels, the three answers' values);
- `event_editor.py`, `event_analyzer.py` EH4 (`QueueCard.svelte`'s event patterns); `page_contract.py`, `graph_primitive.py` (forbidden names); `stylesheet_partition.py` rule2 (a selector defined once across the sheets).

## Contracts

### C-04 — the CRUD shapes (consumed)
`GET/PUT /api/skill-ranks` steps `{rank, label, points_to_next, trial_to_next}`; systems and definitions serve and take `trial_to_rank_1..5` (`null` inherits; a PUT without them clears them); `GET /api/skills` rows carry `trial_ready`.

### C-08 — the trial's proposal (consumed)
`source_type = "quest_request"`; `payload.trial = {skill_key, target_rank, skill_label, rank_label}`.

### C-09 — the surfaces
Produced by: BRIEF-0116-F   Consumed by: Nia
- `competences.svelte.js`: `RANK_TRIAL_KEYS`, `rankTrials(row)` in the skill, system, draft and blank records, `inheritedTrial(record, n)`, `trialsBody(record)` spread as `...trialsBody(record)` in `saveSkill` and `saveSystem`; `saveRanks` sends `trial_to_next`.
- `CompetencesSheet.svelte`: the `thresholds` snippet gains one select per rank (`''` « hérité (oui|non) », `'true'` « Épreuve », `'false'` « Sans épreuve »); the ranks record one checkbox per rank below Maître, « Épreuve pour passer au rang suivant ».
- `PjSkillFiche.svelte`: `pointsLine(s)` ends « · épreuve de rang à passer » when `s.trial_ready`.
- `QuestRequests.svelte`: `TRIGGER_LABEL.trial = 'épreuve de rang'`.
- `QueueCard.svelte`: a « ÉPREUVE » badge for `source_type === 'quest_request'`; in the quest block, « Épreuve de rang : « <skill> » vers <rank> » from `questPayload.trial`.
- `questOffers.svelte.js`: `REVIEW_KEYS` gains `'trial'`.

## Context

The engine half of the trials is in place (A to E). This last step lets Nia
set where a world asks trials (Création › Compétences), see a waiting skill
on the fiche, recognize a trial request and a trial proposal, and keep the
proposal's `trial` key through her edits in the card.

## Scope IN

1. `frontend/src/creation/competences.svelte.js` -- C-09:
   ```js
   // TICKET-0116 (BRIEF-0116-F, B1): `trial_to_rank_<n>` says whether reaching
   // rank n asks a trial -- true, false, or null to inherit (skill, system, world).
   export const RANK_TRIAL_KEYS = [1, 2, 3, 4, 5].map((n) => `trial_to_rank_${n}`);

   function rankTrials(row) {
     const trials = {};
     for (const key of RANK_TRIAL_KEYS) trials[key] = row?.[key] ?? null;
     return trials;
   }

   /** The trial a blank select inherits (B1): for a skill, its system's;
    *  then the world's ladder. `n` is the rank reached (1-5). */
   export function inheritedTrial(record, n) {
     const key = RANK_TRIAL_KEYS[n - 1];
     if (record.kind === 'skill' && record.system_id) {
       const sys = competencesState.systems.find((s) => s.id === record.system_id);
       if (sys && sys[key] != null) return !!sys[key];
     }
     const step = competencesState.ranks[n - 1];
     return step ? !!step.trial_to_next : false;
   }

   function trialsBody(record) {
     const trials = {};
     for (const key of RANK_TRIAL_KEYS) trials[key] = record[key] === null || record[key] === undefined ? null : !!record[key];
     return trials;
   }
   ```
   placed after `inheritedPoints`; `skillRecord`, `systemRecord`, `draftRecord` and both branches of `blankRecord` spread `...rankTrials(row)` (`rankTrials(null)` for the draft and the blanks) after their `...rankPoints(...)`; `saveSkill`'s and `saveSystem`'s bodies spread `...trialsBody(record)` after `...pointsBody(record)` (two `...pointsBody(record)` remain, C3); `saveRanks` maps each step to `{ rank, label, points_to_next: ..., trial_to_next: step.rank < 5 ? !!step.trial_to_next : false }`. The header comment gains « TICKET-0116 (BRIEF-0116-F): a skill, a system and each rank of the ladder say whether reaching a rank asks a trial (`RANK_TRIAL_KEYS`, `trial_to_next`). »
2. `frontend/src/creation/CompetencesSheet.svelte` -- C-09: import `RANK_TRIAL_KEYS` and `inheritedTrial`; the `thresholds` snippet's intro text becomes « Points pour atteindre chaque rang — vide : hérité (valeur grisée). Une épreuve : le rang se mérite par une quête. »; inside its `{#each RANK_POINT_KEYS as key, i (key)}`, after the points `field-row`:
   ```svelte
   <div class="field-row">
     <label for="competence-f-{RANK_TRIAL_KEYS[i]}">Épreuve vers {competencesState.ranks[i + 1]?.label ?? `rang ${i + 1}`}</label>
     <select id="competence-f-{RANK_TRIAL_KEYS[i]}"
       value={rec[RANK_TRIAL_KEYS[i]] == null ? '' : String(rec[RANK_TRIAL_KEYS[i]])}
       onchange={(e) => { creationState.sheetDetail[RANK_TRIAL_KEYS[i]] = e.currentTarget.value === '' ? null : e.currentTarget.value === 'true'; }}>
       <option value="">hérité ({inheritedTrial(rec, i + 1) ? 'oui' : 'non'})</option>
       <option value="true">Épreuve</option>
       <option value="false">Sans épreuve</option>
     </select>
   </div>
   ```
   in the `ranks` record, the intro text gains « Cocher « Épreuve » : le rang suivant se mérite par une quête ; un système ou une compétence peut en décider autrement sur sa fiche. » and, inside its `{#each rec.steps as step, i (step.rank)}`, after the points `field-row`:
   ```svelte
   {#if step.rank < 5}
     <div class="field-row checkbox">
       <input id="rank-f-trial-{step.rank}" type="checkbox" bind:checked={creationState.sheetDetail.steps[i].trial_to_next}>
       <label for="rank-f-trial-{step.rank}">Épreuve pour passer au rang suivant</label>
     </div>
   {/if}
   ```
   The header comment gains « TICKET-0116 (BRIEF-0116-F): each threshold has its trial (inherited, « Épreuve », « Sans épreuve »); the ladder ticks the ranks whose next asks one. » `{@render thresholds()}` stays rendered twice.
3. `frontend/src/creation/PjSkillFiche.svelte`, `pointsLine(s)`:
   ```js
   function pointsLine(s) {
     if (s.points_to_next == null) return `${s.xp} pt · rang maximal`;
     const line = `${s.xp} / ${s.points_to_next} pts`;
     // TICKET-0116 (F1-c): the points wait for a rank trial.
     return s.trial_ready ? `${line} · épreuve de rang à passer` : line;
   }
   ```
4. `frontend/src/creation/QuestRequests.svelte`: `TRIGGER_LABEL` gains `trial: 'épreuve de rang'`; the header comment: « ... every request the days and the rank trials opened ... ».
5. `frontend/src/creation/QueueCard.svelte`: after the `JOURNÉE` badge's `{/if}`:
   ```svelte
   {#if mutation.source_type === 'quest_request'}
     <span class="badge b-trial" title="épreuve de rang">ÉPREUVE</span>
   {/if}
   ```
   and right after `{#if questDraft}` in the quest block:
   ```svelte
   {#if questPayload.trial}
     <div class="q-line">Épreuve de rang : « {questPayload.trial.skill_label} » vers {questPayload.trial.rank_label}</div>
   {/if}
   ```
   The quest block's comment gains « a rank trial (TICKET-0116) names its skill and rank; its rank reward is in the terms, kept by the applier ».
6. `frontend/src/creation/questOffers.svelte.js`: `REVIEW_KEYS` gains `'trial'`, last.
7. `frontend/public/shared.css`, right after `.b-pass-play`: `/* rank trial source badge (TICKET-0116/BRIEF-0116-F) */` and `.b-trial          { background:#1e1130; color:#d2a8ff; border:1px solid #6e40c9; }`.
8. `cd frontend; npm ci; npm run build`; the built output committed.
9. `tooling/verify/checks/rank_trials.py` -- its docstring gains, and `main()` runs after TE, these static rules (a missing file or a pattern found zero times fails):
   - **TF1** -- `competences.svelte.js` exports `RANK_TRIAL_KEYS` and `inheritedTrial`, defines `trialsBody`, holds `...trialsBody(record)` exactly twice and `...pointsBody(record)` exactly twice, and `saveRanks` names `trial_to_next`.
   - **TF2** -- `CompetencesSheet.svelte` names `RANK_TRIAL_KEYS`, `inheritedTrial(`, « Sans épreuve », « Épreuve pour passer au rang suivant », `trial_to_next`, and `{@render thresholds()}` exactly twice.
   - **TF3** -- `PjSkillFiche.svelte` names `s.trial_ready` and « épreuve de rang à passer »; `QuestRequests.svelte`'s `TRIGGER_LABEL` holds `trial: 'épreuve de rang'`; `QueueCard.svelte` names `mutation.source_type === 'quest_request'`, « ÉPREUVE » and `questPayload.trial`; `questOffers.svelte.js`'s `REVIEW_KEYS` holds `'trial'`; `frontend/public/shared.css` defines `.b-trial` once.
   - **TF4** -- the built bundle (`src/world_engine/cockpit/static/assets/*.js`) carries « Épreuve pour passer au rang suivant », « épreuve de rang à passer » and « ÉPREUVE ».
10. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the footer, header verbatim `## A TRIAL IS SEEN WHERE THE CREATOR WORKS (TICKET-0116) -- COMPÉTENCES, THE FICHE, THE REQUESTS PANEL, THE REVIEW CARD (BRIEF-0116-f, no schema change)`; body: B1 edited where the points are, F1-c (the fiche, never the request), the badge, `trial` kept through the card's edits (display only: the applier reads the request). Then `gen_decisions_index.py`, `gen_file_map.py`.

## Scope OUT

- Any backend file: every route these surfaces read exists after B, D, E.
- Showing anything of a trial request on a player surface (F1-c) -- Journée lists the offer only once confirmed, through `available_offers` (C).
- Warning in the offer editor that a point reward gives nothing to a waiting skill (« le silence me convient »).
- The day's account in Journée (`account.gains.skill.produced`), unchanged (lot drafting decision 11).
- A new Création tab or island (INV-49, INV-50): every change is inside existing components.

## Invariants to defend

- **INV-49 / INV-50** -- no new Création tab or island; the panel stays a child of `Queue.svelte`.
- **INV-55** -- no `$effect` assigns a `$state` it reads afterwards; this brief adds no `$effect`.
- **INV-62** -- the fiche is a creator surface; no player surface shows a request (F1-c).
- **INV-20** -- every field read here is relational (`trial_to_next`, `trial_to_rank_<n>`, `trial_ready`); the proposal's `trial` key rides 0121's payload exemption, read only in the card.

## Decision rights

STOP:
- an anchor does not hold;
- `skill_progression.py` C3/D2, `npc_skills.py` C2, `quest_review_card.py`, `quest_request_panel.py`, `event_editor.py`, `event_analyzer.py` or `stylesheet_partition.py` go red.
ADAPT:
- `npm ci` changes `package-lock.json`: commit only the built output and the sources; restore the lock file; report.
- the `thresholds` snippet's grid wraps the added selects onto a new line at the fiche's width: keep the markup of item 2 (one `field-row` each); report.
REPORT-ONLY:
- a visual misalignment of the badge in the card's head.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/rank_trials.py` -> `PASS` (TB to TF).
- [ ] Named mutations, each red then reverted: `...trialsBody(record)` removed from `saveSystem` -> TF1 red; the trial select removed from the snippet -> TF2 red; `pointsLine`'s trial branch removed -> TF3 red; the bundle not rebuilt after a source edit -> `frontend_build_fresh.py` red.
- [ ] `skill_progression.py`, `npc_skills.py`, `quest_review_card.py`, `quest_request_panel.py`, `event_editor.py`, `event_analyzer.py`, `page_contract.py`, `graph_primitive.py`, `stylesheet_partition.py`, `creation_island.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `module_budget.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] Live (cockpit, test DB): Création › Compétences › Rangs du monde shows the checkboxes; a system fiche's « Épreuve vers Expert » reads « hérité (oui) » once Confirmé is ticked; saving « Sans épreuve » and reloading keeps it.
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 10); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change.
