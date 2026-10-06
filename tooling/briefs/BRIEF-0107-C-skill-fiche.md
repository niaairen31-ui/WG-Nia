<!-- slug: skill-fiche -->
# BRIEF 0107-C — "One skill fiche for every character: NPCs given skills, players taught"

Lot: LOT-0107-npc-skills-masters.md (authoritative on conflict)
Depends on: BRIEF-0107-A, BRIEF-0107-B
Commit header for decisions: `(BRIEF-0107-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0107`, on the tree BRIEF-0107-B left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/cockpit/crud/skills.py:276` -> `    return [_skill_dict(s, ladder, d, sys) for s, d, sys in rows]`; `GET /api/skills/learnable` and `POST /api/skills` exist.
- `frontend/src/creation/PjSkillFiche.svelte:44` -> `  let playerMode = $state(false);`; `:63` -> `      fetched = await api('/api/skills/player-characters');`; `:130` -> `  <h2 style="font-size:12px">Fiche de compétences</h2>`; `:149` -> `  {:else if rows.length === 0}`.
- `frontend/src/creation/tabs.js:205` -> the `npc` entry's `islands:` line ending `{ key: 'linkAgent', containerId: 'linkagent-panel' }],`.
- `frontend/src/creation/CompetencesSheet.svelte:178` -> `        <label for="competence-f-description">Description</label>`.
- `frontend/src/creation/competences.svelte.js:259` -> `    description: record.description || '', ...pointsBody(record),`.
- The string « Ajouter une compétence » appears exactly once under `frontend/src/creation` (`page_contract.py`).

## Facts carried

### R-09 — the skill fiche island [M]
Opened: `frontend/src/creation/tabs.js:199-229` (`npc` and `pj` entries;
the fiche is an island and a slot of `pj` only); `mount.js:68-95` (an
island mounts once and is shared across tabs, `entityList` the precedent);
`tabs.js:409-419` (`containerVisible` reads the active entry's slots);
`frontend/src/creation/PjSkillFiche.svelte`.
Consequence: the `npc` entry declares the same island and slot; the
component follows `activeTabKey`.

### R-10 — the checks the lot passes [M]
Opened: E3; `single_canon_write.py` and `canon_write_policy.txt`;
`page_contract.py` (« Ajouter une compétence » must appear once — the NPC
section is titled « Compétences à donner »); `creation_island.py`;
`effect_self_write.py`; `claude_md_contract.py` (CLAUDE.md 37 647 of 38
000 characters); `skill_progression.py` (TICKET-0106's A2 rebuilds the
skill tables from the current models, so it keeps passing).

## Contracts

### C-07 — learning (C1)
Produced by: BRIEF-0107-B   Consumed by: C
`GET /api/skills/learnable?character_id=` → `[{domain,
skill_definition_id, name, requires_master, masters: [{id, name}]}]`: a
player's master skills he lacks; an NPC's missing base domains and
definitions. `POST /api/skills` body `{character_id, skill_definition_id |
domain, rank = 0, taught_by_id?}` → the row (C-08 shape) 201; 422 on a
character or definition outside the world, a teacher who is the learner or
not at Maître in that skill; 409 on a skill held. `GET /api/skills` rows
add `requires_master`, `taught_by_id`.

### C-08 — the fiche (F1)
Produced by: BRIEF-0107-C   Consumed by: Nia
`GET /api/skills/player-characters?character_type=player|npc` (default
`player`, 422 otherwise); `GET /api/skills` rows add `taught_by_name`.
`PjSkillFiche.svelte` on `pj` and `npc` (C-07 routes; a player's grant at
rank 0); `CompetencesSheet.svelte` « Exige un maître »;
`competences.svelte.js` sends `requires_master`.

## Context

The routes exist (B). Nia locked F1: one fiche for players and NPCs, with her creator's bypass. This brief mounts the skill fiche on the NPC tab, lists what each character may be given — « À apprendre » for a player's master skills, « Compétences à donner » for an NPC — names each row's master, and adds « Exige un maître » to a skill's fiche.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `crud/skills.py`, adds `taught_by_name` to `GET /api/skills` rows;
   - in `tabs.js`, declares the `pjSkillFiche` island and its `fiche` slot on the `npc` entry;
   - in `PjSkillFiche.svelte`, follows `activeTabKey` (`characterType`), loads `/api/skills/learnable`, grants through `POST /api/skills` (rank 0 for a player, the picked rank for an NPC; a master or « Sans maître »), names each row's master;
   - in `competences.svelte.js`, `CompetencesSheet.svelte` and `CompetencesList.svelte`, the `requires_master` field, its box and its list mark;
   - appends the decision entry above the footer;
   - adds C1-C2 to `npc_skills.py`.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm run build`.
4. Commit message: `feat(skills): one skill fiche for players and NPCs, taught from it (BRIEF-0107-c)`.

````diff
diff --git a/frontend/src/creation/CompetencesList.svelte b/frontend/src/creation/CompetencesList.svelte
index b648a68..3f7b853 100644
--- a/frontend/src/creation/CompetencesList.svelte
+++ b/frontend/src/creation/CompetencesList.svelte
@@ -86,7 +86,7 @@
            style="padding-left:28px" role="button" tabindex="0"
            onclick={() => onSelect(skillRecord(row))} onkeydown={(ev) => onKey(ev, skillRecord(row))}>
         <div class="ali-name">{row.name}</div>
-        <div class="ali-meta">{row.base_domain}</div>
+        <div class="ali-meta">{row.base_domain}{row.requires_master ? ' · exige un maître' : ''}</div>
       </div>
     {/each}
   {/each}
diff --git a/frontend/src/creation/CompetencesSheet.svelte b/frontend/src/creation/CompetencesSheet.svelte
index 1f73168..19bbd21 100644
--- a/frontend/src/creation/CompetencesSheet.svelte
+++ b/frontend/src/creation/CompetencesSheet.svelte
@@ -174,6 +174,10 @@
           {/each}
         </select>
       </div>
+      <div class="field-row checkbox">
+        <input id="competence-f-master" type="checkbox" bind:checked={creationState.sheetDetail.requires_master}>
+        <label for="competence-f-master">Exige un maître — un personnage joueur ne l'a pas tant qu'on ne la lui a pas apprise</label>
+      </div>
       <div class="field-row" style="grid-column:1/-1">
         <label for="competence-f-description">Description</label>
         <textarea id="competence-f-description" rows="3" bind:value={creationState.sheetDetail.description}></textarea>
diff --git a/frontend/src/creation/PjSkillFiche.svelte b/frontend/src/creation/PjSkillFiche.svelte
index bad5d16..bf22c82 100644
--- a/frontend/src/creation/PjSkillFiche.svelte
+++ b/frontend/src/creation/PjSkillFiche.svelte
@@ -21,6 +21,14 @@
      role_closed_vocab.py greps index.html or mentions "skill", so no
      re-homing is triggered.
 
+     TICKET-0107 (BRIEF-0107-C): the same fiche serves the npc tab (an
+     island of both entries; its character list follows activeTabKey). A
+     player's master skills he was never taught are listed under « À
+     apprendre » with their masters; « Apprendre » grants the row at
+     Inexpérimenté (rank 0), from a master or without one (the creator's
+     bypass). An NPC lists every skill it lacks under « Ajouter », at the
+     rank the creator picks.
+
      No scoped <style> block: like every other Creation island, this
      renders inside the legacy iframe document. */
   import { creationState } from './state.svelte.js';
@@ -42,15 +50,28 @@
   let rowsLoading = $state(false);
   let rowsError = $state('');
   let playerMode = $state(false);
+  let learnable = $state([]);
+  let teacherFor = $state({}); // learnable key -> chosen master id ('' = without a master)
+  let rankFor = $state({}); // learnable key -> rank for an NPC grant
+  let grantError = $state('');
+
+  const characterType = $derived(creationState.activeTabKey === 'npc' ? 'npc' : 'player');
+
+  function learnKey(entry) {
+    return entry.skill_definition_id || `domain:${entry.domain}`;
+  }
 
   async function selectCharacter(id) {
     characterId = id;
     rowsLoading = true;
     rowsError = '';
+    grantError = '';
     try {
       rows = await api(`/api/skills?character_id=${encodeURIComponent(id)}`);
+      learnable = await api(`/api/skills/learnable?character_id=${encodeURIComponent(id)}`);
     } catch (e) {
       rows = [];
+      learnable = [];
       rowsError = e.message;
     }
     rowsLoading = false;
@@ -60,7 +81,7 @@
     let fetched;
     try {
       ranks = await api('/api/skill-ranks');
-      fetched = await api('/api/skills/player-characters');
+      fetched = await api(`/api/skills/player-characters?character_type=${characterType}`);
       loadError = '';
     } catch (e) {
       characters = [];
@@ -81,6 +102,7 @@
   // per-activation loader.
   $effect(() => {
     void serverState.worldId;
+    void characterType;
     characterId = null;
     rows = [];
     loadCharacters();
@@ -110,6 +132,26 @@
     return s.points_to_next == null ? `${s.xp} pt · rang maximal` : `${s.xp} / ${s.points_to_next} pts`;
   }
 
+  async function grant(entry) {
+    grantError = '';
+    const key = learnKey(entry);
+    const body = {
+      character_id: characterId,
+      skill_definition_id: entry.skill_definition_id,
+      domain: entry.skill_definition_id ? null : entry.domain,
+      rank: characterType === 'player' ? 0 : Number(rankFor[key] ?? 1),
+      taught_by_id: teacherFor[key] || null,
+    };
+    try {
+      await api('/api/skills', {
+        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
+      });
+      await selectCharacter(characterId);
+    } catch (e) {
+      grantError = e.message;
+    }
+  }
+
   async function saveRank(skillId, rank) {
     try {
       const updated = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
@@ -127,7 +169,7 @@
 </script>
 
 <div class="panel-head" style="flex-shrink:0; border-top:2px solid var(--border)">
-  <h2 style="font-size:12px">Fiche de compétences</h2>
+  <h2 style="font-size:12px">Fiche de compétences{characterType === 'npc' ? ' (PNJ)' : ''}</h2>
   <select value={characterId ?? ''} onchange={onCharacterChange}>
     {#each characters as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
   </select>
@@ -146,9 +188,10 @@
     <div class="empty"><span class="spin">⟳</span></div>
   {:else if rowsError}
     <div class="empty">{rowsError}</div>
-  {:else if rows.length === 0}
-    <div class="empty">No skill rows for this character.</div>
   {:else}
+    {#if rows.length === 0}
+      <div class="empty">{characterType === 'npc' ? 'Aucune compétence : Initié dans chaque domaine de base.' : 'Aucune compétence.'}</div>
+    {/if}
     <div class="field-section"><div class="field-grid">
       {#each rows as s (s.id)}
         <div class="field-row">
@@ -168,9 +211,36 @@
               {/each}
             </select>
           {/if}
-          <small style="color:var(--muted)">{pointsLine(s)}</small>
+          <small style="color:var(--muted)">{pointsLine(s)}{s.taught_by_name ? ` · enseignée par ${s.taught_by_name}` : (s.requires_master ? ' · accordée sans maître' : '')}</small>
         </div>
       {/each}
     </div></div>
+    {#if learnable.length && !playerMode}
+      <div class="field-section">
+        <div style="font-size:12px; font-weight:600; margin-bottom:4px">
+          {characterType === 'player' ? 'À apprendre (exige un maître)' : 'Compétences à donner'}
+        </div>
+        {#each learnable as entry (learnKey(entry))}
+          <div class="field-row" style="display:flex; gap:6px; align-items:center; flex-wrap:wrap">
+            <span style="min-width:120px">{SKILL_DOMAIN_LABELS[entry.name] || entry.name}</span>
+            <select title="Maître" onchange={(ev) => { teacherFor[learnKey(entry)] = ev.currentTarget.value; }}>
+              <option value="">Sans maître (créatrice)</option>
+              {#each entry.masters.filter((m) => m.id !== characterId) as m (m.id)}
+                <option value={m.id}>{m.name}</option>
+              {/each}
+            </select>
+            {#if characterType === 'npc'}
+              <select title="Rang" onchange={(ev) => { rankFor[learnKey(entry)] = ev.currentTarget.value; }}>
+                {#each ranks as r (r.rank)}
+                  <option value={r.rank} selected={r.rank === 1}>{r.label}</option>
+                {/each}
+              </select>
+            {/if}
+            <button class="btn-ghost" onclick={() => grant(entry)}>{characterType === 'player' ? 'Apprendre' : 'Ajouter'}</button>
+          </div>
+        {/each}
+        {#if grantError}<div style="color:var(--red); font-size:12px">{grantError}</div>{/if}
+      </div>
+    {/if}
   {/if}
 </div>
diff --git a/frontend/src/creation/competences.svelte.js b/frontend/src/creation/competences.svelte.js
index ea6df9d..529c9c9 100644
--- a/frontend/src/creation/competences.svelte.js
+++ b/frontend/src/creation/competences.svelte.js
@@ -28,7 +28,10 @@
    optional rank thresholds (`points_to_rank_1..5`, null = inherit), and a
    third record kind, 'ranks', edits the world's ladder (GET/PUT
    /api/skill-ranks): each rank's name and the points to leave it. The most
-   specific value wins -- skill, then system, then world. */
+   specific value wins -- skill, then system, then world.
+
+   TICKET-0107 (BRIEF-0107-C, A2): a skill record carries `requires_master`
+   (« Exige un maître »): no player holds it until taught. */
 import { serverState } from '../lib/serverState.svelte.js';
 
 export const competencesState = $state({
@@ -88,7 +91,7 @@ export function skillRecord(row) {
   return {
     kind: 'skill', persisted: true, id: row.id, draftKey: null,
     name: row.name, base_domain: row.base_domain, system_id: row.system_id ?? null,
-    description: row.description ?? '', ...rankPoints(row),
+    description: row.description ?? '', requires_master: !!row.requires_master, ...rankPoints(row),
   };
 }
 
@@ -111,7 +114,7 @@ export function draftRecord(d) {
   return {
     kind: 'skill', persisted: false, id: `draft:${d.key}`, draftKey: d.key,
     name: d.name ?? '', base_domain: d.base_domain ?? '', system_id: d.system_id ?? null,
-    description: d.description ?? '', ...rankPoints(null),
+    description: d.description ?? '', requires_master: false, ...rankPoints(null),
   };
 }
 
@@ -130,7 +133,7 @@ export function blankRecord(kind) {
   }
   return {
     kind: 'skill', persisted: false, id: null, draftKey: null,
-    name: '', base_domain: 'physical', system_id: null, description: '', ...rankPoints(null),
+    name: '', base_domain: 'physical', system_id: null, description: '', requires_master: false, ...rankPoints(null),
   };
 }
 
@@ -256,7 +259,7 @@ async function saveSkill(record) {
   if (!COMPETENCES_DOMAINS.includes(record.base_domain)) throw new Error('Domaine de base requis.');
   const body = JSON.stringify({
     name, base_domain: record.base_domain, system_id: record.system_id || null,
-    description: record.description || '', ...pointsBody(record),
+    description: record.description || '', requires_master: !!record.requires_master, ...pointsBody(record),
   });
   const saved = record.persisted
     ? await api(`/api/skill-definitions/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 458feab..840ca1e 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -202,7 +202,7 @@ export const CREATION_TABS = {
     containers: ['creation-editor-area'],
     loader: null,
     state: { onTabEnter: () => _npcTabEnterReset(), onWorldSwitch: null },
-    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }, { key: 'npcAgent', containerId: 'npcagent-panel' }, { key: 'linkAgent', containerId: 'linkagent-panel' }],
+    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }, { key: 'npcAgent', containerId: 'npcagent-panel' }, { key: 'linkAgent', containerId: 'linkagent-panel' }, { key: 'pjSkillFiche', containerId: 'creation-pj-skill' }],
     type: 'character',
     entityFilter: (entities) => entities.filter(e => e.type === 'character' && !creationState.playerCharIds.has(e.id)),
     createPanel: null,
@@ -212,7 +212,9 @@ export const CREATION_TABS = {
               onSelect: (id) => document.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'relations', meta: { id } } })),
               onOpen: null,
               display: 'on_demand', toggleLabel: 'Voir le graphe',
-              graph: { consumer: 'relations', mountId: 'relgraph-mount' } }],
+              graph: { consumer: 'relations', mountId: 'relgraph-mount' } },
+            // TICKET-0107 (BRIEF-0107-C): the skill fiche, shared with pj.
+            { id: 'fiche', containerId: 'creation-pj-skill', loader: null, onSelect: null }],
   },
   pj: {
     label: 'Personnages joueurs',
diff --git a/src/world_engine/cockpit/crud/skills.py b/src/world_engine/cockpit/crud/skills.py
index d4fce1d..efbb2fa 100644
--- a/src/world_engine/cockpit/crud/skills.py
+++ b/src/world_engine/cockpit/crud/skills.py
@@ -273,7 +273,10 @@ def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_sess
     ).all()
     order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
     rows.sort(key=lambda r: order.get(r[0].domain, len(SKILL_DOMAINS)))
-    return [_skill_dict(s, ladder, d, sys) for s, d, sys in rows]
+    teachers = {r[0].taught_by_id for r in rows if r[0].taught_by_id}
+    names = {e.id: e.name for e in db.exec(select(Entity).where(Entity.id.in_(teachers))).all()} if teachers else {}
+    # TICKET-0107 (BRIEF-0107-C): the master's name, for the fiche.
+    return [{**_skill_dict(s, ladder, d, sys), "taught_by_name": names.get(s.taught_by_id)} for s, d, sys in rows]
 
 
 class SkillRankBody(BaseModel):
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 9f42264..3260dd4 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18024,6 +18024,21 @@ keeps open skills. B2, rolling the base domain for a locked skill:
 « impossible à lancer ». Learning through a conversation's proposal (C2):
 deferred to quests.
 
+
+## ONE SKILL FICHE FOR EVERY CHARACTER (TICKET-0107) -- NPCS GIVEN SKILLS, PLAYERS TAUGHT (BRIEF-0107-c, no schema change)
+
+**F1.** The skill fiche is an island of both the `pj` and `npc` tabs (mounted
+once, its character list following `activeTabKey`). An NPC lists the
+skills it lacks under « Compétences à donner », at the rank the creator
+picks, from a master or none. A player lists the master skills he was never
+taught under « À apprendre »; « Apprendre » grants the row at
+Inexpérimenté, from a master of the world or « sans maître » -- the
+creator's bypass. Each row names its master. A skill's fiche carries
+« Exige un maître ».
+
+**Rejected.** A second component for NPC sheets: the same rows, the same
+routes, two places to keep in step.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/npc_skills.py b/tooling/verify/checks/npc_skills.py
index 2efc0fd..4d4138d 100644
--- a/tooling/verify/checks/npc_skills.py
+++ b/tooling/verify/checks/npc_skills.py
@@ -63,6 +63,19 @@ B3 -- learning (fixture, C1). `GET /api/skills/learnable` lists, for a
 B4 -- documentation (static). CLAUDE.md names `requires_master` and
    `skill_access`'s lock.
 
+C1 -- the routes the fiche reads (BRIEF-0107-C, fixture).
+   `GET /api/skills/player-characters?character_type=npc` lists the
+   world's NPCs only, `player` its players only, another value 422; `GET
+   /api/skills` serves `taught_by_name` (the master's name, None without
+   one).
+C2 -- the UI (static). `tabs.js`'s `npc` entry mounts the `pjSkillFiche`
+   island and declares its `fiche` slot; `PjSkillFiche.svelte` asks for
+   `character_type=${characterType}`, reads `/api/skills/learnable`, POSTs
+   `/api/skills` with rank 0 for a player, offers « Apprendre » and « Sans
+   maître »; `CompetencesSheet.svelte` binds `requires_master`;
+   `competences.svelte.js` sends it; the built bundle carries « Exige un
+   maître » and « À apprendre ».
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -511,6 +524,61 @@ def check_b4() -> None:
         fail("B4: CLAUDE.md does not name requires_master and skill_access")
 
 
+# --- C1-C2 ---------------------------------------------------------------------
+
+def check_c1(engine) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine.cockpit.crud.skills import list_skill_player_characters, list_skills
+    from world_engine.models import Skill
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+        npcs = {c["id"] for c in list_skill_player_characters("npc", session)}
+        players = {c["id"] for c in list_skill_player_characters("player", session)}
+        if npcs != {ids["master"], ids["brute"], ids["plain"]} or players != {ids["pc"]}:
+            fail(f"C1: npc list {npcs}, player list {players}")
+        try:
+            list_skill_player_characters("monster", session)
+            fail("C1: an unknown character_type was accepted")
+        except HTTPException as exc:
+            if exc.status_code != 422:
+                fail(f"C1: an unknown character_type answered {exc.status_code}")
+        row = session.get(Skill, ids["brute_phys"])
+        row.taught_by_id = ids["master"]
+        session.add(row)
+        session.commit()
+        names = {r["id"]: r["taught_by_name"] for r in list_skills(character_id=ids["brute"], db=session)}
+        if names.get(ids["brute_phys"]) != "master":
+            fail(f"C1: taught_by_name is {names}")
+        others = [r["taught_by_name"] for r in list_skills(character_id=ids["pc"], db=session)]
+        if any(others) or not others:
+            fail(f"C1: rows without a master serve {others}")
+
+
+def check_c2() -> None:
+    root = ROOT / "frontend" / "src" / "creation"
+    tabs = (root / "tabs.js").read_text(encoding="utf-8")
+    npc = tabs[tabs.index("  npc: {"):tabs.index("  pj: {")]
+    if "key: 'pjSkillFiche'" not in npc or "id: 'fiche', containerId: 'creation-pj-skill'" not in npc:
+        fail("C2: the npc tab does not mount the skill fiche")
+    fiche = (root / "PjSkillFiche.svelte").read_text(encoding="utf-8")
+    for needle in ("character_type=${characterType}", "/api/skills/learnable", "method: 'POST'",
+                   "characterType === 'player' ? 0", "'Apprendre'", "Sans maître"):
+        if needle not in fiche:
+            fail(f"C2: PjSkillFiche.svelte lacks {needle!r}")
+    if "bind:checked={creationState.sheetDetail.requires_master}" not in (root / "CompetencesSheet.svelte").read_text(encoding="utf-8"):
+        fail("C2: CompetencesSheet.svelte does not bind requires_master")
+    if "requires_master: !!record.requires_master" not in (root / "competences.svelte.js").read_text(encoding="utf-8"):
+        fail("C2: competences.svelte.js does not send requires_master")
+    bundle = "".join(p.read_text(encoding="utf-8") for p in
+                     (ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets").glob("*.js"))
+    for needle in ("Exige un maître", "À apprendre"):
+        if needle not in bundle:
+            fail(f"C2: the built bundle does not carry « {needle} »")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -523,6 +591,8 @@ def main() -> int:
     check_b2(engine)
     check_b3(engine)
     check_b4()
+    check_c1(engine)
+    check_c2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -531,7 +601,7 @@ def main() -> int:
           "every carrure to a physical row from v2.15 only, and an opposing NPC rolls its own "
           "row for the skill, else its base domain, else Initié; a skill that requires a master "
           "is held only once taught, cannot be rolled until then, and is taught by a Maître or "
-          "granted by the creator")
+          "granted by the creator; the fiche serves NPCs and players, and teaches from it")
     return 0
 
 
````

## Scope OUT

- Renaming `PjSkillFiche.svelte` or its island key (`registry.js`'s retired prefixes name it).
- Removing a row from the fiche.
- Any server rule (B owns them).

## Invariants to defend

**Every Création page is a `CREATION_TABS` registry entry:** the fiche is declared on the `npc` entry, no page branch. **Every Création surface mounts through `mount.js`:** the island is the existing one. **Inside a `$effect`, a `$state` assigned is not read afterwards:** the world-switch effect only reads `characterType`, a `$derived`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `page_contract.py`, `creation_island.py`, `creation_tab_switch.py` or `effect_self_write.py` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- The pre-existing Svelte warning on `<option value="">`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/npc_skills.py` -> `PASS: npc_skills -- … the fiche serves NPCs and players, and teaches from it`.
- `page_contract.py`, `creation_island.py`, `creation_tab_switch.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` -> `PASS`.
- Mutation test, red then reverted: in `list_skills`, `"taught_by_name": names.get(s.taught_by_id)` -> `"taught_by_name": None` -> `C1`.
- `WORLD_ENGINE_ENV=test python tooling/verify/run.py --ticket TICKET-0107-npc-skills-masters` -> green.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 140/140.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `ONE SKILL FICHE FOR EVERY CHARACTER (TICKET-0107) -- NPCS GIVEN SKILLS, PLAYERS TAUGHT (BRIEF-0107-c, no schema change)` — in the diff. CLAUDE.md: nothing.
