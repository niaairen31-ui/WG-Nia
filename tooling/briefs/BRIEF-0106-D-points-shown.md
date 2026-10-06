<!-- slug: points-shown -->
# BRIEF 0106-D — "The points are shown: on the PC's fiche and in the day's account"

Lot: LOT-0106-skill-progression.md (authoritative on conflict)
Depends on: BRIEF-0106-A, BRIEF-0106-B, BRIEF-0106-C
Commit header for decisions: `(BRIEF-0106-d, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0106`, on the tree BRIEF-0106-C left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/cockpit/routes/day.py:231` → `def _account_gains(mutations: list[ProposedMutation]) -> dict:`; `:263` → `            "produced": [],`; `:345` → `        "gains": _account_gains(mutations),`; `AgendaStep` is imported from `...models`.
- `frontend/src/journee/Journee.svelte:156` → the `{#if account.gains.resource.length === 0 && account.gains.knowledge.length === 0 && account.gains.relation.length === 0}` line; `:160` → `              <p class="muted">{account.gains.skill.note}</p>`.
- `frontend/src/creation/PjSkillFiche.svelte:107` → `  async function saveRank(skillId, rank) {`; `:157` → `            <input type="text" value={s.rank_label} disabled>`.
- `GET /api/skills` serves `xp` and `points_to_next` (`cockpit/crud/skills.py::_skill_dict`).
- `src/world_engine/cockpit/mutations.py` calls `grant_step_roll(` in `_mutation_apply_agenda_step_change`.

## Facts carried

### R-06 — a day writes no canon until approved [M]
Opened: `src/world_engine/day_resolve.py:1-56` (module docstring: REPLAY
re-rolls, V1 no canon), `:165-177` (`_step_player_tier`), `:206-228`;
`src/world_engine/day_mutations.py:106-145` (`_step_action`: a blocked step
emits no `agenda_step_change`; failure → `fail`, else `complete`);
`src/world_engine/cockpit/mutations.py:827-884`
(`_mutation_apply_agenda_step_change`: stale guard `step.status ==
"active"`, then status writes).
Finding: every emitted `agenda_step_change` whose step has a `domain` was
rolled; replays re-propose, and the stale guard applies one per step.
Consequence: the day's point is granted inside that applier, from
`step.domain`, never at the roll and never from the payload.

### R-15 — the day's account [M]
Opened: `src/world_engine/cockpit/routes/day.py:231-266` (`_account_gains`,
skill block `produced: []` and the « pas encore » note), `:309-347`
(`_day_account_dict`, the one caller, holds `db`);
`frontend/src/journee/Journee.svelte:145-160`.
Consequence: `_account_gains` takes `db` and reads each step's `domain`.

### R-10 — Play is sealed [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:12263-12267` (A3:
`legacy.html` byte-untouched); `tooling/verify/checks/module_budget.py:61-65`
(`LEGACY_DOCUMENT_LINE_CEILING = 2762`, fails on growth and on shrinkage);
`src/world_engine/cockpit/legacy.html:1269-1273` (stores `token.verdict`),
`:1408-1421` (`_appendVerdict` reads `domain, dice, modifier, total,
band`).
Finding: an extra key on the verdict object is ignored by the client.
Consequence: Y1b — `progress` rides on the verdict event; `legacy.html` is
not in any diff.

## Contracts

### C-04 — the PC sheet API
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-D, the PC fiche
`GET /api/skill-ranks` → six `{rank, label, points_to_next}` of the active
world. `GET /api/skills?character_id=` → per row `{id, character_id,
domain, skill_definition_id, definition_name, rank, rank_label, xp,
points_to_next, change_history, updated_at}`, ladder of the character's
world, `points_to_next` per C-02.

### C-07 — the day's point
Produced by: BRIEF-0106-B   Consumed by: `_mutation_apply_agenda_step_change`
`cockpit/skill_progress.grant_step_roll(db, *, step, owner_id, world_id,
mutation_id) -> None`: nothing when `step.domain` is None, the owner has no
base row for it (`skill_definition_id IS NULL`), or the row is at MAX_RANK;
else C-05 with 1 point. Called for `complete` and `fail`, after the stale
guard, before the status writes.

### C-11 — the displays
Produced by: BRIEF-0106-D   Consumed by: Nia
`routes/day._account_gains(mutations, db)`: `skill.produced` = one
`{mutation_id, status, domain, points: 1}` per `agenda_step_change` whose
step has a `domain`; `skill.note` = « Un point par jet, donné à
l'approbation de l'étape. ». `Journee.svelte` lists them (« acquis » /
« à l'approbation »). `PjSkillFiche.svelte`: `xp / points_to_next pts`, or
`xp pt · rang maximal`.

## Context

A point is earned in Play and at a day step's approval (B), and the creator sets the ladder (C). Nia accepted Y1b on one condition: « tant que cela fonctionne pour les journées ». This brief makes the points visible where she plays them: the day's account lists one point per rolled step with its status, and the PC's fiche shows the points earned within each rank out of the points needed to leave it.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `routes/day.py`, gives `_account_gains` the `db` its caller holds and fills `skill.produced` from each `agenda_step_change` whose step has a `domain` (C-11); the « pas encore » note is replaced;
   - in `Journee.svelte`, lists the skill gains (« acquis » / « à l'approbation ») and counts them in the « Rien pour l'instant » test;
   - in `PjSkillFiche.svelte`, shows `xp / points_to_next pts`, or `xp pt · rang maximal`, under each rank;
   - appends the decision entry above the footer;
   - adds D1-D2 to `skill_progression.py`.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm run build`.
4. Commit message: `feat(skills): the points earned are shown on the PC fiche and in the day's account (BRIEF-0106-d)`.

````diff
diff --git a/frontend/src/creation/PjSkillFiche.svelte b/frontend/src/creation/PjSkillFiche.svelte
index 7198031..bad5d16 100644
--- a/frontend/src/creation/PjSkillFiche.svelte
+++ b/frontend/src/creation/PjSkillFiche.svelte
@@ -104,6 +104,12 @@
     selectCharacter(ev.currentTarget.value);
   }
 
+  // TICKET-0106 (BRIEF-0106-D): the points earned within the rank, out of
+  // the points needed to leave it (null at the top rank).
+  function pointsLine(s) {
+    return s.points_to_next == null ? `${s.xp} pt · rang maximal` : `${s.xp} / ${s.points_to_next} pts`;
+  }
+
   async function saveRank(skillId, rank) {
     try {
       const updated = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
@@ -162,6 +168,7 @@
               {/each}
             </select>
           {/if}
+          <small style="color:var(--muted)">{pointsLine(s)}</small>
         </div>
       {/each}
     </div></div>
diff --git a/frontend/src/journee/Journee.svelte b/frontend/src/journee/Journee.svelte
index c44f550..5ab58b4 100644
--- a/frontend/src/journee/Journee.svelte
+++ b/frontend/src/journee/Journee.svelte
@@ -153,7 +153,11 @@
                 {#each account.gains.relation as g}
                   <li><span class="badge b-other">relation</span> {g.status} — {JSON.stringify(g.detail)}</li>
                 {/each}
-                {#if account.gains.resource.length === 0 && account.gains.knowledge.length === 0 && account.gains.relation.length === 0}
+                {#each account.gains.skill.produced as g}
+                  <li><span class="badge b-other">compétence</span> {g.domain} +{g.points} point
+                    ({g.status === 'applied' ? 'acquis' : g.status === 'proposed' ? "à l'approbation" : g.status})</li>
+                {/each}
+                {#if account.gains.resource.length === 0 && account.gains.knowledge.length === 0 && account.gains.relation.length === 0 && account.gains.skill.produced.length === 0}
                   <li class="muted">Rien pour l'instant.</li>
                 {/if}
               </ul>
diff --git a/src/world_engine/cockpit/routes/day.py b/src/world_engine/cockpit/routes/day.py
index bda2b01..e52e482 100644
--- a/src/world_engine/cockpit/routes/day.py
+++ b/src/world_engine/cockpit/routes/day.py
@@ -228,19 +228,24 @@ def list_days(db: Session = Depends(get_session)) -> list[dict]:
     return [_day_dict(batch, pass_play) for batch, pass_play in rows]
 
 
-def _account_gains(mutations: list[ProposedMutation]) -> dict:
+def _account_gains(mutations: list[ProposedMutation], db: Session) -> dict:
     """Gains block (Scope IN item 4): resource/relation gains are read from
     the `effects` embedded in `agenda_step_change` payloads (the delta
     contract, BRIEF-0075-e-amendment-1) plus any standalone
     `relation_change` row; knowledge gains are the rendezvous
-    `knowledge_change` rows. Skill deltas have no carrier in v1 (X1) —
-    reported positively, never silently omitted."""
+    `knowledge_change` rows. Skill gains (TICKET-0106, BRIEF-0106-D): one
+    point per `agenda_step_change` whose step was rolled (its own `domain`),
+    given when that mutation is approved (`grant_step_roll`)."""
     resource: list[dict] = []
     relation: list[dict] = []
     knowledge: list[dict] = []
+    skill: list[dict] = []
     for m in mutations:
         payload = m.payload if isinstance(m.payload, dict) else {}
         if m.mutation_type == "agenda_step_change":
+            step = db.get(AgendaStep, payload.get("step_id")) if payload.get("step_id") else None
+            if step is not None and step.domain is not None:
+                skill.append({"mutation_id": m.id, "status": m.status, "domain": step.domain, "points": 1})
             for eff in payload.get("effects") or []:
                 if not isinstance(eff, dict):
                     continue
@@ -260,8 +265,8 @@ def _account_gains(mutations: list[ProposedMutation]) -> dict:
         "relation": relation,
         "knowledge": knowledge,
         "skill": {
-            "produced": [],
-            "note": "La résolution de journée ne produit pas encore de gain de compétence.",
+            "produced": skill,
+            "note": "Un point par jet, donné à l'approbation de l'étape.",
         },
     }
 
@@ -342,7 +347,7 @@ def _day_account_dict(pass_play: PassPlay, batch: Batch, db: Session) -> dict:
         "npcs": fact_sheet.get("npcs", []),
         "locations": fact_sheet.get("locations", []),
         "role_hints": fact_sheet.get("role_hints", []),
-        "gains": _account_gains(mutations),
+        "gains": _account_gains(mutations, db),
         "pending_review": pending_review,
         "germs": germs,
         "rendezvous": _account_rendezvous(mutations, db),
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index ea20b77..3e52fbc 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17960,6 +17960,17 @@ body.
 **Rejected.** Labels per system (P1): one ladder per world is simpler to
 edit; reactivates if two systems of one world need different rank names.
 
+
+## THE POINTS ARE SHOWN (TICKET-0106) -- ON THE PC'S FICHE AND IN THE DAY'S ACCOUNT (BRIEF-0106-d, no schema change)
+
+**Y1b.** Until Play's migration shows the verdict's `progress`, the points
+are seen in two places. The PC's skill fiche shows, beside each rank, the
+points earned within it out of the points needed to leave it (« rang
+maximal » at Maître). The day's account lists one point per rolled step --
+an `agenda_step_change` whose step has a `domain` -- with that mutation's
+status: proposed, the point waits for the approval; applied, it is earned.
+The former « pas encore de gain de compétence » note is retired.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/skill_progression.py b/tooling/verify/checks/skill_progression.py
index 7cd4bdc..aaff72e 100644
--- a/tooling/verify/checks/skill_progression.py
+++ b/tooling/verify/checks/skill_progression.py
@@ -88,6 +88,15 @@ C3 -- the Compétences UI (static). `CompetencesList.svelte` lists « Rangs
    `/api/skill-ranks` and sends `pointsBody(record)` with a skill and with a
    system; the built bundle carries « Rangs du monde ».
 
+D1 -- the day's account (BRIEF-0106-D, fixture). `routes/day._account_gains`
+   lists under `skill.produced` one {mutation_id, status, domain, points 1}
+   per `agenda_step_change` whose step has a domain, none for a step
+   without one, and its `note` is no longer the « pas encore » text.
+D2 -- the displays (static). `Journee.svelte` renders
+   `account.gains.skill.produced`; `PjSkillFiche.svelte` shows `s.xp` out
+   of `s.points_to_next`, « rang maximal » at the top; the built bundle
+   carries « rang maximal ».
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -745,6 +754,49 @@ def check_c3() -> None:
         fail("C3: the built bundle does not carry « Rangs du monde »")
 
 
+# --- D1-D2 ---------------------------------------------------------------------
+
+def check_d1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes.day import _account_gains
+    from world_engine.models import Agenda, AgendaStep, ProposedMutation
+
+    with Session(engine) as session:
+        ids = _b_world(session)
+        plan = Agenda(world_id=ids["world"], owner_entity_id=ids["pc"], title="Journée D")
+        session.add(plan)
+        session.flush()
+        rolled = AgendaStep(agenda_id=plan.id, step_order=1, objective="courir", status="active", domain="agility")
+        talked = AgendaStep(agenda_id=plan.id, step_order=2, objective="parler", status="pending", domain=None)
+        session.add(rolled)
+        session.add(talked)
+        session.flush()
+        muts = [ProposedMutation(id=f"m-{n}", world_id=ids["world"], source_type="pass_play",
+                                 mutation_type="agenda_step_change", status=status,
+                                 payload={"step_id": step.id, "action": "complete"})
+                for n, (step, status) in enumerate(((rolled, "proposed"), (talked, "applied")))]
+        gains = _account_gains(muts, session)
+        produced = gains["skill"]["produced"]
+        if produced != [{"mutation_id": "m-0", "status": "proposed", "domain": "agility", "points": 1}]:
+            fail(f"D1: skill.produced is {produced}")
+        if "pas encore" in gains["skill"]["note"]:
+            fail(f"D1: the note still says {gains['skill']['note']!r}")
+
+
+def check_d2() -> None:
+    journee = (ROOT / "frontend" / "src" / "journee" / "Journee.svelte").read_text(encoding="utf-8")
+    fiche = (ROOT / "frontend" / "src" / "creation" / "PjSkillFiche.svelte").read_text(encoding="utf-8")
+    if "account.gains.skill.produced" not in journee:
+        fail("D2: Journee.svelte does not render the skill gains")
+    if "s.xp" not in fiche or "s.points_to_next" not in fiche or "rang maximal" not in fiche:
+        fail("D2: PjSkillFiche.svelte does not show the points within the rank")
+    bundle = "".join(p.read_text(encoding="utf-8") for p in
+                     (ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets").glob("*.js"))
+    if "rang maximal" not in bundle:
+        fail("D2: the built bundle does not carry « rang maximal »")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -761,6 +813,8 @@ def main() -> int:
     check_c1(engine)
     check_c2(engine)
     check_c3()
+    check_d1(engine)
+    check_d2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -769,7 +823,8 @@ def main() -> int:
           "its tier, keeps every former tier's roll, lets a world, a system and a skill set "
           "the points of each rank, and migrates from v2.14 only; every roll earns a point, "
           "auto-applied in Play and given at a day step's approval, and a threshold moves the rank; "
-          "the creator names the ranks and sets their points per world, system and skill")
+          "the creator names the ranks and sets their points per world, system and skill; the PC's "
+          "fiche shows the points within the rank and the day's account the points earned")
     return 0
 
 
````

## Scope OUT

- Showing points in Play (`legacy.html`, sealed; TICKET-0069).
- Editing a skill's points by hand on the fiche (only its rank).
- Changing what a day proposes or how a step is approved.
- Any other block of the day's account.

## Invariants to defend

**Play is sealed:** `legacy.html` is not touched. **The day writes no canon:** `_account_gains` only reads. None of the CLAUDE.md invariants is otherwise near this change.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/skill_progression.py` → `PASS: skill_progression -- … the PC's fiche shows the points within the rank and the day's account the points earned`.
- `module_budget.py`, `function_length.py`, `frontend_build_fresh.py`, `decisions_index.py`, `pipeline_wiring.py` → `PASS`.
- Mutation test, red then reverted: in `_account_gains`, `            "produced": skill,` → `            "produced": [],` → `D1`.
- `WORLD_ENGINE_ENV=test python tooling/verify/run.py --ticket TICKET-0106-skill-progression` → green.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 139/139.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE POINTS ARE SHOWN (TICKET-0106) -- ON THE PC'S FICHE AND IN THE DAY'S ACCOUNT (BRIEF-0106-d, no schema change)` — in the diff. CLAUDE.md: nothing.
