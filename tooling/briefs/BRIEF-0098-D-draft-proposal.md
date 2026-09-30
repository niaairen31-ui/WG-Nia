<!-- slug: draft-proposal -->
# BRIEF 0098-D — "Draft a proposal: two prompts, one shared loader"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: BRIEF-0098-C (`validate`, `lore_write_apply.py` joins the panel list)
Commit header for decisions: `(BRIEF-0098-d, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `src/world_engine/lore_prompt.py:45` → `def load(db: Session, usage: str) -> RenderSpec:`; `:52` → `        select(PromptTemplate)`
- `tooling/verify/checks/lore_isolation.py:85` → `LORE_PROMPT_FILE = SRC / "lore_prompt.py"`; `:92` → `    SRC / "cockpit" / "routes" / "lore_choices.py",` then `)`; `:662` → `def check_prompt_loader_scoped_to_prompt_tables() -> None:`
- `tooling/verify/checks/name_index.py:57` → `    "src/world_engine/writes/facets.py",` then `}`
- `src/world_engine/prompt_registry.py:275` → `    "world_tick": PromptSpec(`
- `scripts/seed_pilot.py:1812` → `# ----- day chain prompt text (TICKET-0075; hoisted to module level, TICKET-0076) -----`; `:2800` → `    # ----- prompt template: world tick — off-screen NPC advancement ----------`
- `CLAUDE.md:153` → `  panel). Token posing never indexes a creator-only or unscoped appellation.`; `:447` → the `lore_*.py, unbound_facts.py, fact_refs.py` line; `:450` → the `prompt_store.py` line
- `tooling/verify/checks/lore_write.py:65` → `    "lore_write_apply.py", "writes/lore_entries.py",`
- `src/world_engine/prompt_load.py`, `src/world_engine/lore_write_draft.py`, `scripts/apply_ticket_0098_lore_write_prompts.py` → do not exist

## Facts carried

### R-12 — name resolution [M]
Opened: `src/world_engine/lore_resolve.py:30-60`, `:135-176`
(`resolve_named`), `:178-228` (`near_candidates`);
`tooling/verify/checks/name_index.py:17-20`, `:53-58` (R5 `CREATOR_ALLOWED`).
Finding: categories `place/person/faction/object/other` map to
`location/character/faction/item/(none)`; `resolve_named` returns
`matched/ambiguous/unmatched`, never picks; `near_candidates` is creator
only. R5 pins the files allowed to use the creator regime.
Consequence: D resolves names there and adds `lore_write_draft.py` to R5's
list in the same commit.

### R-13 — fact codes [M]
Opened: `src/world_engine/fact_refs.py` (whole, 115 lines).
Finding: `code_facts(db, ids)` codes in order (`f1 — <rendered text>`),
`resolve(code)` tolerates brackets and case, returns None off-list.
Consequence: D codes the L1 list and resolves every model code; an unlisted
code is dropped (CLAUDE.md invariant).

### R-14 — tokens and creator-only facts [M]
Opened: `src/world_engine/prose_render.py:27` (`TOKEN_RE`),
`src/world_engine/prose_tokens.py:194-225` (`tokenize`, read-only, regimes
`prose`/`names_only`); `src/world_engine/facet_reads.py:42-61`
(`creator_only_fact_ids`).
Finding: `tokenize` writes nothing and returns tokenized text; a creator-only
fact is one whose participant holds an `unaware` `is_secret` row on it.
Consequence: D finds the named entities with `tokenize` + `TOKEN_RE` and
excludes creator-only facts from the model's list.

### R-15 — prompt loading and shipping [M]
Opened: `src/world_engine/lore_prompt.py` (whole, 64 lines);
`tooling/verify/checks/lore_isolation.py:57-66` (R17), `:85-95`
(`PANEL_FILES`, `PIPELINE_FILES`), `:662-692` (R15, vacuity-guarded);
`tooling/verify/checks/prompt_registry.py:1-80` (`USAGE_LINE`,
`WIRED_FILES`); `src/world_engine/prompt_registry.py:246-275`;
`scripts/seed_pilot.py:132-175` (`upsert_prompt_template`, S2), `:2182`
(`DAY_PROMPT_HEADS`); `scripts/apply_ticket_0094_mention_choice_seed.py`.
Finding: the only loader for authoring prompts on the Lore shell is
`lore_prompt.load` (callers: enumeration E3), and R17 forbids a panel module
to import it; R15 fails on zero `select(` in its target. The seed ships new
heads through a module-level tuple read by an `apply_ticket_*` script.
`lore_plan.py` calls `chat(model=spec.model)` and is not in `WIRED_FILES`.
Consequence: N1 — `prompt_load.py` holds the loader verbatim, `lore_prompt.py`
re-exports it, R15 targets `prompt_load.py` and also forbids `select(` in the
re-export; the writing heads ship as `LORE_WRITE_PROMPT_HEADS`.

### R-19 — prod canon size (Nia's machine, 2026-09-29, `mode=ro`) [M]
Opened: Nia's run of `measure_0098.py` on `~/.world_engine/world_engine.db`.
Finding (excerpts): largest active world Silka 297 facts / 186 free /
17 028 characters of free non-reserved facts; per participant entity p90 ≤ 7
facts, max 16 (Valnir), max 1 424 characters; world-level facts with no
participant 2-32 per world; `(entity, bloc facet)` pairs with >1 fact: 0 in
every world; legacy slugs up to 32 (Verkhaal, no longer played).
Consequence: L1 (named entities' facts + world-level facts) stays in the
low thousands of characters; the cap `MAX_CODED_FACTS = 200` is never hit on
measured data; Q19d holds, so a `bloc` edit is a rewrite.

## Contracts

### C-05 — the draft
Produced by: D   Consumed by: E, F
- `lore_write_draft`: `QUESTIONS_USAGE = "lore_statement_questions"`,
  `PROPOSAL_USAGE = "lore_statement_to_proposal"`, `MAX_QUESTIONS = 3`,
  `MAX_CODED_FACTS = 200`, `WRITE_UNAVAILABLE_MESSAGE` (French),
  `CATEGORY_TYPE`.
- `draft_context(db, world_id, statement) -> DraftContext(entity_lines,
  coded)`; `draft_questions(db, world_id, statement) -> list[str]`;
  `draft_proposal(db, world_id, statement, answers="") -> dict` with keys
  `statement, answers, entities, facts, memberships, controls, notes,
  facets`. Each entity carries `status`: `matched` (`action: existing`,
  `entity_id`, `name`, `type`), `ambiguous` (`action: null`, `candidates`
  [{entity_id,name,type}]) or `new` (`action: create`, `type` from the
  category or null, `near` [{entity_id,name,type,score}]). Facts follow
  C-02 with `fact_id` resolved from the model's `code`. `facets` =
  [{name, label}] of the non-typed `FACETS`. `OllamaError` and
  `LlmParseError` propagate.
- Prompt variables: questions `statement, entities, facts`; proposal
  `facets, entities, facts, statement, answers`.

### C-07 — the shared prompt loader
Produced by: D   Consumed by: `lore_prompt` (re-export), `lore_write_draft`
`prompt_load.RenderSpec(system_prompt, user_template, model)`;
`prompt_load.load(db, usage) -> RenderSpec` (body moved verbatim from
`lore_prompt.load`; raises `LlmParseError` on a missing head);
`lore_prompt.py` = `from .prompt_load import RenderSpec, load`.

## Context

The model side, which never writes: at most three questions, then a draft in which every name and every fact code is resolved in code. The consultation's prompt loader moves to a shared module first (N1), because the writing panel may not import the pipeline.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `prompt_load.py` (C-07, `lore_prompt.load` verbatim) and reduces `lore_prompt.py` to a re-export; retargets `lore_isolation.py` R15 to `prompt_load.py` (and forbids `select(` in the re-export) and adds `lore_write_apply.py`, `lore_write_draft.py` to `PANEL_FILES`; adds `lore_write_draft.py` to `name_index.py` R5's `CREATOR_ALLOWED`; creates `lore_write_draft.py` (C-05); adds the two prompt texts and `LORE_WRITE_PROMPT_HEADS` to `seed_pilot.py` and seeds them in a loop; adds two `PROMPT_REGISTRY` entries; creates `scripts/apply_ticket_0098_lore_write_prompts.py`; edits CLAUDE.md lines 153, 447 and 450; extends `lore_write.py` (census: three files; D1, D2; C2's draft half); appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): draft a lore proposal with two prompts; shared prompt loader (BRIEF-0098-d)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 726fb0b..96a2b70 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -150,7 +150,7 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   fact whose entity holds an `unaware` `is_secret` row on it) is excluded from
   `facet_reads` by query construction; only the Lore dossier opts in, plus the
   `creator` regime of `name_index` for name resolution (Lore question, names
-  panel). Token posing never indexes a creator-only or unscoped appellation.
+  panel, writing panel). Token posing never indexes a creator-only or unscoped appellation.
   What an NPC knows-but-conceals lives in `knowledge` rows with
   `is_secret = TRUE`,
   excluded by query construction at every assembler AND every propagation
@@ -444,10 +444,10 @@ WG-Nia/
 │   ├── day_narration_guard.py  # T1 judge: name containment + outcome survival, Python-only
 │   ├── day_mutations.py     # day-chain mutation emission: proposer only, never applies (V1)
 │   ├── day_feasibility.py   # feasibility veto: downward-only, clamp_verdict is the safety (Y1)
-│   ├── lore_*.py, unbound_facts.py, fact_refs.py  # Lore reads; unbound facts; fact codes/keys
+│   ├── lore_*.py, unbound_facts.py, fact_refs.py  # Lore read/write; unbound facts; fact codes
 │   ├── writes/               # canon-write helpers by domain; schema.py is the DDL authority
 │   ├── prompt_registry.py   # prompt wiring registry; effective_model resolver
-│   ├── prompt_store.py      # prompt_version read accessor (current_prompt et al.)
+│   ├── prompt_store.py, prompt_load.py  # prompt_version accessor; Lore-shell prompt loader
 │   ├── entity_author.py     # AI authoring assistant (entities, PC, skills, agendas, events)
 │   ├── region_author.py     # region generation orchestrator (proposes names, no canon)
 │   ├── spatial_author.py    # Creation-side door materialization from live connects_to
diff --git a/scripts/apply_ticket_0098_lore_write_prompts.py b/scripts/apply_ticket_0098_lore_write_prompts.py
new file mode 100644
index 0000000..470f570
--- /dev/null
+++ b/scripts/apply_ticket_0098_lore_write_prompts.py
@@ -0,0 +1,59 @@
+"""One-shot, idempotent delivery of the TICKET-0098 lore writing prompt heads
+onto the live DB (BRIEF-0098-D).
+
+Same CREATE-HEAD pattern as apply_ticket_0094_mention_choice_seed.py: it
+embeds NO prompt text and NO head fields -- both come from
+seed_pilot.LORE_WRITE_PROMPT_HEADS (single source) -- and relies on
+upsert_prompt_template's idempotence (S2): a first run reports both heads
+`created`, a second run `existing`, and an existing head's text is never
+touched.
+
+Touches nothing else: no canon row, no other template.
+
+Safe to re-run.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0098_lore_write_prompts.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+from sqlmodel import Session  # noqa: E402
+
+import seed_pilot  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+
+def main() -> None:
+    with Session(engine) as session:
+        before_created = len(seed_pilot._created)
+        before_updated = len(seed_pilot._updated)
+        before_existing = len(seed_pilot._existing)
+
+        for entry in seed_pilot.LORE_WRITE_PROMPT_HEADS:
+            seed_pilot.upsert_prompt_template(session, **entry)
+        session.commit()
+
+        for table, id_ in seed_pilot._created[before_created:]:
+            print(f"created  {table}/{id_}")
+        for table, id_ in seed_pilot._updated[before_updated:]:
+            print(f"updated  {table}/{id_}")
+        for table, id_ in seed_pilot._existing[before_existing:]:
+            print(f"existing {table}/{id_}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index ed17ecc..9ce91a5 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1809,6 +1809,139 @@ Lignes disponibles :
 """
 
 
+# ----- prompt template: lore writing -- clarification questions (TICKET-0098, BRIEF-0098-D) --
+# usage = "lore_statement_questions". world_id = NULL: the prompt carries no
+# world content of its own; the statement, the named entities and the coded
+# facts arrive as variables. First of the two writing calls (O1): at most
+# three questions, never a proposal (lore_write_draft.draft_questions).
+LORE_STATEMENT_QUESTIONS_SYSTEM_PROMPT = """\
+Tu aides la créatrice d'un monde de jeu de rôle à ajouter du lore. Elle \
+vient d'écrire un texte. Avant qu'on le découpe en faits, tu lui poses au \
+plus trois questions courtes, en français, sur ce qui reste flou pour \
+l'écrire correctement.
+
+Pose en priorité les questions qui changent qui connaît quoi : tout le \
+monde, les membres d'une faction, les personnes présentes dans un lieu, \
+ceux qui ont rencontré quelqu'un, ou seulement certains personnages ; un \
+secret ; une croyance fausse. Demande aussi si un nom désigne une chose \
+déjà connue ou une chose nouvelle, et si une règle appartient à une \
+personne ou au lieu où elle s'applique.
+
+Quand le texte est déjà clair, rends une liste vide.
+
+Réponds UNIQUEMENT avec ce JSON :
+{"questions": ["...", "..."]}\
+"""
+
+LORE_STATEMENT_QUESTIONS_USER_TEMPLATE = """\
+Texte de la créatrice :
+{statement}
+
+Entités connues que le texte nomme :
+{entities}
+
+Faits déjà connus (code — texte) :
+{facts}\
+"""
+
+# ----- prompt template: lore writing -- statement to proposal (TICKET-0098, BRIEF-0098-D) --
+# usage = "lore_statement_to_proposal". world_id = NULL. Second writing call
+# (O1): turns the statement and the creator's answers into a draft. The
+# model names entities by name and existing facts by code only; code
+# resolves both and the creator confirms before anything is written
+# (lore_write_draft.draft_proposal, lore_write_apply.apply_proposal).
+LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT = """\
+Tu découpes le lore écrit par la créatrice d'un monde de jeu de rôle en \
+faits courts et apprenables un par un. Chaque fait est une phrase complète \
+en français, qui nomme les choses par leur nom.
+
+ENTITÉS. Liste chaque personne, lieu, faction ou objet que tes faits \
+concernent, avec un "ref" (e1, e2, ...), son nom tel qu'écrit et une \
+catégorie parmi "person", "place", "faction", "object", "other". Une \
+occupation partagée par un groupe (les dockers, les gardes) est une \
+"faction".
+
+FAITS. Chaque fait porte :
+- "action" : "create" pour un fait nouveau ; "existing" pour ajouter des \
+personnes qui savent un fait déjà connu, désigné par son "code" ; \
+"rewrite" pour réécrire un fait de facette bloc déjà connu, désigné par \
+son "code", avec le nouveau "content" complet ;
+- "content" et "facet" (choisie dans la liste des facettes) pour un fait \
+nouveau, avec "aspect" pour une coutume ;
+- "participants" : les refs des entités dont parle le fait (aucune pour \
+une vérité générale du monde) ;
+- "defaults" : qui le sait par défaut, parmi {"scope_type": "world"}, \
+{"scope_type": "faction", "scope_ref": "e3"}, {"scope_type": "location", \
+"scope_ref": "e2"}, {"scope_type": "rencontre", "scope_ref": "e1"} (ceux \
+qui ont rencontré e1) ;
+- "knowers" : les entités précises qui le savent, avec "level" parmi \
+"rumor", "suspicious", "partial", "knows", "fully_understands", \
+"is_secret" (vrai si elle le cache) et "is_incorrect" (vrai si c'est une \
+croyance fausse).
+Un secret ou une croyance fausse passe toujours par "knowers". Une facette \
+bloc (physique, tenue, description, doctrine, organisation) a un seul \
+participant ; si ce bloc existe déjà dans la liste des faits connus, \
+réécris-le avec "rewrite".
+
+APPARTENANCES ET POSSESSIONS. "memberships" liste les personnes qui \
+entrent dans une faction ({"entity_ref", "faction_ref"}) ; "controls" \
+liste qui possède ou dirige un lieu ({"owner_ref", "location_ref"}). La \
+possession s'écrit aussi comme un fait de facette "statut".
+
+Suis les réponses de la créatrice à la lettre. Réponds UNIQUEMENT avec ce \
+JSON :
+{"entities": [{"ref": "e1", "name": "...", "category": "person"}],
+ "facts": [{"action": "create", "content": "...", "facet": "preference",
+   "participants": ["e1"], "defaults": [{"scope_type": "rencontre",
+   "scope_ref": "e1"}], "knowers": []}],
+ "memberships": [], "controls": []}\
+"""
+
+LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE = """\
+Facettes :
+{facets}
+
+Entités connues que le texte nomme :
+{entities}
+
+Faits déjà connus (code — texte) :
+{facts}
+
+Texte de la créatrice :
+{statement}
+
+Réponses de la créatrice aux questions :
+{answers}\
+"""
+
+
+# The lore writing heads, one tuple read by the seed and by
+# scripts/apply_ticket_0098_lore_write_prompts.py (single source, the
+# DAY_PROMPT_HEADS precedent).
+LORE_WRITE_PROMPT_HEADS = (
+    dict(
+        id="pt-lore-statement-questions",
+        name="Écriture de lore — questions de clarification",
+        usage="lore_statement_questions",
+        world_id=None,
+        system_prompt=LORE_STATEMENT_QUESTIONS_SYSTEM_PROMPT,
+        user_template=LORE_STATEMENT_QUESTIONS_USER_TEMPLATE,
+        variables=["statement", "entities", "facts"],
+        destination="local",
+    ),
+    dict(
+        id="pt-lore-statement-to-proposal",
+        name="Écriture de lore — texte vers proposition",
+        usage="lore_statement_to_proposal",
+        world_id=None,
+        system_prompt=LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT,
+        user_template=LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE,
+        variables=["facets", "entities", "facts", "statement", "answers"],
+        destination="local",
+    ),
+)
+
+
 # ----- day chain prompt text (TICKET-0075; hoisted to module level, TICKET-0076) -----
 # ----- prompt template: day plan emission (TICKET-0075, BRIEF-0075-b) ---
 # usage = "day_plan". world_id = NULL. ONE call (F1): the model proposes
@@ -2797,6 +2930,10 @@ def seed(session: Session) -> None:
         destination="local",
     )
 
+    # ----- prompt templates: lore writing (TICKET-0098, BRIEF-0098-D) --
+    for entry in LORE_WRITE_PROMPT_HEADS:
+        upsert_prompt_template(session, **entry)
+
     # ----- prompt template: world tick — off-screen NPC advancement ----------
     # (TICKET-0014/BRIEF-0014-a). usage = "world_tick". world_id = NULL.
     # model=NULL (Q1): the runner (BRIEF-0014-b) passes
diff --git a/src/world_engine/lore_prompt.py b/src/world_engine/lore_prompt.py
index 6394218..dae4e44 100644
--- a/src/world_engine/lore_prompt.py
+++ b/src/world_engine/lore_prompt.py
@@ -1,65 +1,14 @@
 """Prompt resolution for the lore consultation chantier (TICKET-0085,
 BRIEF-0085-d).
 
-The one place that touches a `Session` to resolve a `prompt_template` row
-for this chantier's usages. It owns that `Session` and nothing else: no
-canon table, no `Knowledge`, no `Relation`, no `Entity` -- only
-`PromptTemplate` and `PromptVersion`. Callers that must stay Session-free
-(`lore_render.render`, whose isolation is machine-checked) receive a
-`RenderSpec` of plain strings instead of an ORM row: a detached
-`PromptTemplate`/`PromptVersion` is not inert -- it can lazy-load through
-its relationships, which would make it a door back to the database that no
-static check could see. A plain string cannot be.
-
-Both of this chantier's model-calling usages (`lore_question_to_plan`,
-`lore_rows_to_prose`) resolve through `_author_model` -- both are
-`surface="authoring"` in `PROMPT_REGISTRY` -- so `load` hardcodes that
-default rather than taking one as a parameter. A usage needing a different
-default is a reason to add a parameter then, not to guess one now.
+Since TICKET-0098 (BRIEF-0098-D, N1) the loader lives in `prompt_load.py`,
+shared with the Lore shell's writing panel, which may not import this
+pipeline module (`lore_isolation.py` R17). This module re-exports it so the
+consultation pipeline's imports are unchanged.
 """
 
 from __future__ import annotations
 
-from dataclasses import dataclass
-
-from sqlmodel import Session, select
-
-from . import llm_parse
-from .models import PromptTemplate
-from .prompt_registry import effective_model
-from .prompt_store import current_prompt
-
-
-@dataclass(frozen=True)
-class RenderSpec:
-    system_prompt: str
-    user_template: str
-    model: str
-
-
-def _author_model() -> str:
-    from .entity_author import AUTHOR_MODEL  # lazy: avoids the import cycle (prompt_registry precedent)
-    return AUTHOR_MODEL
-
+from .prompt_load import RenderSpec, load
 
-def load(db: Session, usage: str) -> RenderSpec:
-    """Loads the active `prompt_template` head for `usage`, its current
-    `prompt_version` text, and its effective model, and returns them as
-    plain strings. Raises `LlmParseError` on a missing/inactive head --
-    same failure mode `lore_plan.draft_plan` already surfaced for a missing
-    template, now shared by every usage that calls through here."""
-    template = db.exec(
-        select(PromptTemplate)
-        .where(PromptTemplate.usage == usage)
-        .where(PromptTemplate.is_active == True)  # noqa: E712
-    ).first()
-    if template is None:
-        raise llm_parse.LlmParseError(
-            f"lore_prompt: no active prompt_template for usage={usage!r}"
-        )
-    version = current_prompt(db, template)
-    return RenderSpec(
-        system_prompt=version.system_prompt,
-        user_template=version.user_template,
-        model=effective_model(template, _author_model()),
-    )
+__all__ = ["RenderSpec", "load"]
diff --git a/src/world_engine/lore_write_draft.py b/src/world_engine/lore_write_draft.py
new file mode 100644
index 0000000..060ea1c
--- /dev/null
+++ b/src/world_engine/lore_write_draft.py
@@ -0,0 +1,266 @@
+"""The model side of the lore writing path (TICKET-0098, BRIEF-0098-D).
+
+Two model calls, each its own prompt (decision O1): `draft_questions` asks
+the creator at most `MAX_QUESTIONS` clarification questions about her
+statement (J3); `draft_proposal` turns the statement and her answers into a
+draft the writing panel shows for correction. The model sees the statement,
+the answers, the facet vocabulary, the entities the statement names and a
+coded list of the facts already about them (L1) -- never an id. It names
+existing facts only by code (`fact_refs.code_facts`, CLAUDE.md invariant)
+and entities only by name; code resolves both here: a code outside the list
+is dropped, a name goes through `lore_resolve.resolve_named` under the
+creator regime and comes back matched, ambiguous (candidates, the creator
+picks) or new (near names shown, the creator creates, links or keeps it as
+text). Nothing here writes: `lore_write_apply.apply_proposal` validates and
+writes what the creator confirmed.
+
+Ollama down surfaces as `ollama_client.OllamaError` to the route, which
+answers `WRITE_UNAVAILABLE_MESSAGE` (K1: no fallback extractor).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+from sqlmodel import Session, select
+
+from . import llm_parse, prompt_load
+from .facet_reads import creator_only_fact_ids
+from .facets import FACETS
+from .fact_refs import CodedFacts, code_facts
+from .lore_resolve import near_candidates, resolve_named
+from .models import Entity, Fact, FactParticipant
+from .name_index import CREATOR
+from .ollama_client import chat
+from .prose_render import TOKEN_RE
+from .prose_tokens import tokenize
+from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER
+
+QUESTIONS_USAGE = "lore_statement_questions"
+PROPOSAL_USAGE = "lore_statement_to_proposal"
+MAX_QUESTIONS = 3
+MAX_CODED_FACTS = 200
+WRITE_UNAVAILABLE_MESSAGE = (
+    "Le modèle local (Ollama) est indisponible : aucune proposition n'a pu être "
+    "rédigée et rien n'a été écrit. Ton texte est conservé ; relance quand Ollama "
+    "est démarré."
+)
+CATEGORY_TYPE: dict[str, Optional[str]] = {
+    "person": "character", "place": "location", "faction": "faction", "object": "item",
+    "other": None,
+}
+SCOPE_TYPES: tuple[str, ...] = ("world", "faction", "location", "rencontre")
+
+
+def _as_list(value: Any) -> list:
+    return value if isinstance(value, list) else []
+
+
+@dataclass(frozen=True)
+class DraftContext:
+    """What the model may see: the named entities and the coded facts."""
+
+    entity_lines: tuple[str, ...]
+    coded: CodedFacts
+
+
+def named_entity_ids(db: Session, world_id: str, statement: str) -> list[str]:
+    """Entity ids the statement names, in order of first appearance, found by
+    the tokenizer (a read; nothing is recorded)."""
+    tokens = tokenize(db, world_id=world_id, text=statement)
+    ordered: list[str] = []
+    for match in TOKEN_RE.finditer(tokens.text):
+        if match.group(1) not in ordered:
+            ordered.append(match.group(1))
+    return ordered
+
+
+def _world_facts(db: Session, world_id: str) -> list[str]:
+    """Free facts of the world with no participant (world-level lore)."""
+    bound = select(FactParticipant.fact_id)
+    return list(db.exec(select(Fact.id).where(
+        Fact.world_id == world_id, Fact.relation_id.is_(None), Fact.event_id.is_(None),
+        Fact.world_law_id.is_(None), Fact.id.not_in(bound),
+    ).order_by(Fact.created_at, Fact.id)).all())
+
+
+def draft_context(db: Session, world_id: str, statement: str) -> DraftContext:
+    """L1: the facts of the entities the statement names, then the world-level
+    facts, creator-only facts excluded, capped at `MAX_CODED_FACTS`."""
+    entity_ids = named_entity_ids(db, world_id, statement)
+    entity_lines = []
+    fact_ids: list[str] = []
+    for entity_id in entity_ids:
+        entity = db.get(Entity, entity_id)
+        entity_lines.append(f"- {entity.name} ({entity.type})")
+        fact_ids += db.exec(select(FactParticipant.fact_id).where(
+            FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
+    fact_ids += _world_facts(db, world_id)
+    hidden = creator_only_fact_ids(db, fact_ids)
+    kept = [fid for fid in dict.fromkeys(fact_ids) if fid not in hidden][:MAX_CODED_FACTS]
+    return DraftContext(entity_lines=tuple(entity_lines), coded=code_facts(db, kept))
+
+
+def _facet_lines() -> str:
+    return "\n".join(
+        f"- {name} ({spec.granularity}) : {spec.description}"
+        for name, spec in FACETS.items() if spec.granularity != "typed"
+    )
+
+
+def _call(db: Session, usage: str, values: dict[str, str]) -> dict:
+    spec = prompt_load.load(db, usage)
+    user_message = spec.user_template
+    for key, value in values.items():
+        user_message = user_message.replace("{" + key + "}", value)
+    raw = chat(
+        [{"role": "system", "content": spec.system_prompt},
+         {"role": "user", "content": user_message}],
+        model=spec.model, format="json",
+    )
+    return llm_parse.extract_object(raw)
+
+
+def _values(context: DraftContext, statement: str, answers: str = "") -> dict[str, str]:
+    return {
+        "statement": statement.strip(),
+        "answers": answers.strip() or "(aucune réponse)",
+        "entities": "\n".join(context.entity_lines) or "(aucune entité connue nommée)",
+        "facts": "\n".join(context.coded.lines) or "(aucun fait connu)",
+        "facets": _facet_lines(),
+    }
+
+
+def draft_questions(db: Session, world_id: str, statement: str) -> list[str]:
+    """At most `MAX_QUESTIONS` non-empty questions, in the model's order.
+    `OllamaError` and `LlmParseError` propagate."""
+    parsed = _call(db, QUESTIONS_USAGE, _values(draft_context(db, world_id, statement), statement))
+    questions = [q.strip() for q in _as_list(parsed.get("questions"))
+                 if isinstance(q, str) and q.strip()]
+    return questions[:MAX_QUESTIONS]
+
+
+def _entity(db: Session, world_id: str, raw: Any, notes: list[str]) -> Optional[dict]:
+    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not raw["name"].strip():
+        notes.append("Une entité sans nom a été ignorée.")
+        return None
+    ref, name = str(raw.get("ref") or ""), raw["name"].strip()
+    category = raw.get("category") if raw.get("category") in CATEGORY_TYPE else "other"
+    found = resolve_named(name, category, world_id, db, scope=CREATOR)
+    if found.verdict == "unmatched" and category != "other":
+        found = resolve_named(name, "other", world_id, db, scope=CREATOR)
+    item: dict[str, Any] = {"ref": ref, "name": name, "category": category}
+    if found.verdict == "matched":
+        entity = db.get(Entity, found.entity_id)
+        item.update(status="matched", action="existing", entity_id=entity.id,
+                    name=entity.name, type=entity.type)
+    elif found.verdict == "ambiguous":
+        item.update(status="ambiguous", action=None, candidates=[
+            {"entity_id": e.id, "name": e.name, "type": e.type}
+            for e in (db.get(Entity, cid) for cid in found.candidate_ids)])
+    else:
+        near = near_candidates(name, world_id, db, scope=CREATOR)
+        item.update(status="new", action="create", type=CATEGORY_TYPE[category], near=[
+            {"entity_id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
+            for c in near])
+    return item
+
+
+def _refs(raw: Any, known: set[str]) -> list[str]:
+    return [r for r in _as_list(raw) if isinstance(r, str) and r in known]
+
+
+def _scopes(raw: Any, known: set[str]) -> list[dict]:
+    out = []
+    for scope in _as_list(raw):
+        if not isinstance(scope, dict) or scope.get("scope_type") not in SCOPE_TYPES:
+            continue
+        if scope["scope_type"] == "world":
+            out.append({"scope_type": "world"})
+        elif scope.get("scope_ref") in known:
+            out.append({"scope_type": scope["scope_type"], "scope_ref": scope["scope_ref"]})
+    return out
+
+
+def _knowers(raw: Any, known: set[str]) -> list[dict]:
+    out = []
+    for knower in _as_list(raw):
+        if (isinstance(knower, dict) and knower.get("entity_ref") in known
+                and knower.get("level") in KNOWLEDGE_LEVEL_LADDER):
+            out.append({"entity_ref": knower["entity_ref"], "level": knower["level"],
+                        "is_secret": knower.get("is_secret") is True,
+                        "is_incorrect": knower.get("is_incorrect") is True})
+    return out
+
+
+def _fact(raw: Any, coded: CodedFacts, known: set[str], notes: list[str]) -> Optional[dict]:
+    if not isinstance(raw, dict):
+        return None
+    action = raw.get("action")
+    action = action if action in ("create", "existing", "rewrite") else "create"
+    item: dict[str, Any] = {
+        "ref": str(raw.get("ref") or ""), "action": action,
+        "participants": _refs(raw.get("participants"), known),
+        "defaults": _scopes(raw.get("defaults"), known),
+        "knowers": _knowers(raw.get("knowers"), known),
+    }
+    if action != "create":
+        fact_id = coded.resolve(raw.get("code"))
+        if fact_id is None:
+            notes.append(f"Un fait désigné par un code inconnu ({raw.get('code')!r}) a été ignoré.")
+            return None
+        item["fact_id"] = fact_id
+    if action in ("create", "rewrite"):
+        content = raw.get("content")
+        if not isinstance(content, str) or not content.strip():
+            notes.append("Un fait sans texte a été ignoré.")
+            return None
+        item["content"] = content.strip()
+    if action == "create":
+        spec = FACETS.get(raw.get("facet"))
+        if spec is None or spec.granularity == "typed":
+            notes.append(f"Un fait de facette inconnue ({raw.get('facet')!r}) a été ignoré.")
+            return None
+        aspect = raw.get("aspect")
+        item.update(facet=raw["facet"], aspect=aspect if isinstance(aspect, str) else None)
+    return item
+
+
+def _pairs(raw: Any, keys: tuple[str, str], known: set[str]) -> list[dict]:
+    out = []
+    for pair in _as_list(raw):
+        if isinstance(pair, dict) and all(pair.get(k) in known for k in keys):
+            out.append({k: pair[k] for k in keys})
+    return out
+
+
+def draft_proposal(db: Session, world_id: str, statement: str, answers: str = "") -> dict:
+    """The draft the writing panel edits (C-05), with the facet vocabulary the
+    panel offers (names and French labels, from `FACETS`). Every entity carries a
+    `status` (`matched` / `ambiguous` / `new`); every fact code is resolved to
+    an id or dropped with a note. `OllamaError` and `LlmParseError`
+    propagate."""
+    context = draft_context(db, world_id, statement)
+    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers))
+    notes: list[str] = []
+    entities = [e for e in (_entity(db, world_id, raw, notes)
+                            for raw in _as_list(parsed.get("entities"))) if e is not None]
+    seen: set[str] = set()
+    for index, entity in enumerate(entities, start=1):
+        if not entity["ref"] or entity["ref"] in seen:
+            entity["ref"] = f"e{index}"
+        seen.add(entity["ref"])
+    facts = [f for f in (_fact(raw, context.coded, seen, notes)
+                         for raw in _as_list(parsed.get("facts"))) if f is not None]
+    for index, fact in enumerate(facts, start=1):
+        fact["ref"] = f"f{index}"
+    return {
+        "statement": statement.strip(), "answers": answers.strip() or None,
+        "entities": entities, "facts": facts,
+        "memberships": _pairs(parsed.get("memberships"), ("entity_ref", "faction_ref"), seen),
+        "controls": _pairs(parsed.get("controls"), ("owner_ref", "location_ref"), seen),
+        "notes": notes,
+        "facets": [{"name": name, "label": spec.label} for name, spec in FACETS.items()
+                   if spec.granularity != "typed"],
+    }
diff --git a/src/world_engine/prompt_load.py b/src/world_engine/prompt_load.py
new file mode 100644
index 0000000..e7ad465
--- /dev/null
+++ b/src/world_engine/prompt_load.py
@@ -0,0 +1,66 @@
+"""Prompt resolution for creator-side authoring usages (TICKET-0098,
+BRIEF-0098-D, decision N1 -- extracted verbatim from `lore_prompt.py`, which
+now re-exports it for the consultation pipeline).
+
+The one place that touches a `Session` to resolve a `prompt_template` row
+for the Lore shell's usages, consultation and writing alike. It owns that
+`Session` and nothing else: no canon table, no `Knowledge`, no `Relation`,
+no `Entity` -- only `PromptTemplate` and `PromptVersion`
+(`lore_isolation.py` R15). Callers that must stay Session-free
+(`lore_render.render`, whose isolation is machine-checked) receive a
+`RenderSpec` of plain strings instead of an ORM row: a detached
+`PromptTemplate`/`PromptVersion` is not inert -- it can lazy-load through
+its relationships, which would make it a door back to the database that no
+static check could see. A plain string cannot be.
+
+Every usage loaded here resolves through `_author_model` -- all are
+`surface="authoring"` in `PROMPT_REGISTRY` -- so `load` hardcodes that
+default rather than taking one as a parameter. A usage needing a different
+default is a reason to add a parameter then, not to guess one now.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from sqlmodel import Session, select
+
+from . import llm_parse
+from .models import PromptTemplate
+from .prompt_registry import effective_model
+from .prompt_store import current_prompt
+
+
+@dataclass(frozen=True)
+class RenderSpec:
+    system_prompt: str
+    user_template: str
+    model: str
+
+
+def _author_model() -> str:
+    from .entity_author import AUTHOR_MODEL  # lazy: avoids the import cycle (prompt_registry precedent)
+    return AUTHOR_MODEL
+
+
+def load(db: Session, usage: str) -> RenderSpec:
+    """Loads the active `prompt_template` head for `usage`, its current
+    `prompt_version` text, and its effective model, and returns them as
+    plain strings. Raises `LlmParseError` on a missing/inactive head --
+    same failure mode `lore_plan.draft_plan` already surfaced for a missing
+    template, now shared by every usage that calls through here."""
+    template = db.exec(
+        select(PromptTemplate)
+        .where(PromptTemplate.usage == usage)
+        .where(PromptTemplate.is_active == True)  # noqa: E712
+    ).first()
+    if template is None:
+        raise llm_parse.LlmParseError(
+            f"prompt_load: no active prompt_template for usage={usage!r}"
+        )
+    version = current_prompt(db, template)
+    return RenderSpec(
+        system_prompt=version.system_prompt,
+        user_template=version.user_template,
+        model=effective_model(template, _author_model()),
+    )
diff --git a/src/world_engine/prompt_registry.py b/src/world_engine/prompt_registry.py
index 2a2e880..b2a1ae8 100644
--- a/src/world_engine/prompt_registry.py
+++ b/src/world_engine/prompt_registry.py
@@ -272,6 +272,23 @@ PROMPT_REGISTRY: dict[str, PromptSpec] = {
         call_sites=("src/world_engine/lore_render.py:_call_model",),
         default_model=_author_model,
     ),
+    # TICKET-0098 (BRIEF-0098-D, O1): the lore writing path's two calls.
+    # world_scoped=False for the lore_rows_to_prose reason: the job is
+    # fidelity to the creator's statement, not a world's register.
+    "lore_statement_questions": PromptSpec(
+        surface="authoring",
+        world_scoped=False,
+        dry_run_capable=True,
+        call_sites=("src/world_engine/lore_write_draft.py:_call",),
+        default_model=_author_model,
+    ),
+    "lore_statement_to_proposal": PromptSpec(
+        surface="authoring",
+        world_scoped=False,
+        dry_run_capable=True,
+        call_sites=("src/world_engine/lore_write_draft.py:_call",),
+        default_model=_author_model,
+    ),
     "world_tick": PromptSpec(
         surface="play",
         world_scoped=False,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 4ef36dc..f8e5336 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17283,6 +17283,37 @@ this module does not import. No model is called here.
 **Rejected.** R2 (relations, laws, events in the first cut): reactivates
 when a story loses its sense without its relation or law.
 
+## THE MODEL DRAFTS, CODE RESOLVES, THE CREATOR CONFIRMS (TICKET-0098) -- TWO WRITING PROMPTS (BRIEF-0098-d, no schema change)
+
+**O1 + J3.** Two prompts, each editable in Prompts: `lore_statement_questions`
+asks the creator at most three clarification questions about her text;
+`lore_statement_to_proposal` turns the text and her free-text answers into a
+draft. `lore_write_draft.py` holds both calls and never writes.
+
+**L1 -- what the model sees.** The statement, the answers, the facet
+vocabulary, the entities the statement names (found by the tokenizer, a
+read) and a coded list of their facts plus the world-level facts (no
+participant), creator-only facts excluded, capped at 200 lines. It never
+sees an id. It names existing facts by code (CLAUDE.md invariant) and
+entities by name; code resolves a name with `lore_resolve.resolve_named`
+under the creator regime into matched, ambiguous (candidates, the creator
+picks) or new (near names shown). An unlisted code, a typed or unknown
+facet, an unknown level or a dangling ref is dropped, never coerced.
+
+**N1 -- one prompt loader.** `lore_prompt.load` moved to `prompt_load.py`,
+which `lore_prompt.py` re-exports: the writing panel may not import the
+consultation pipeline (`lore_isolation.py` R17), and a second loader would
+drift. R15 now scopes `prompt_load.py` to the prompt tables.
+
+**K1.** Ollama down propagates `OllamaError`; the route answers a named
+French message. No fallback extractor.
+
+**Rejected.** O2 (one prompt returning questions and draft together):
+reactivates if waiting for two calls weighs on the creator. L2 (the whole
+world's facts): reactivates if the model duplicates facts about entities the
+statement did not name. J2 (several clarification rounds): reactivates if
+one round regularly leaves the draft off.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_isolation.py b/tooling/verify/checks/lore_isolation.py
index 28d856a..89b1712 100644
--- a/tooling/verify/checks/lore_isolation.py
+++ b/tooling/verify/checks/lore_isolation.py
@@ -29,7 +29,9 @@ R9 (category vocabulary parity): the category literals in `lore_plan.py`'s
 `_MENTION_CATEGORIES` equal the key set of `lore_resolve.py`'s
 `_CATEGORY_ENTITY_TYPE`.
 R15 (prompt loader scoped to prompt tables): every `select(` in
-`lore_prompt.py` references only `PromptTemplate`/`PromptVersion` -- the
+`prompt_load.py` (the loader `lore_prompt.py` re-exports since TICKET-0098,
+BRIEF-0098-D, N1; `lore_prompt.py` itself holds no `select(`) references
+only `PromptTemplate`/`PromptVersion` -- the
 module that owns the Session for this chantier's prompt resolution must
 never become a canon door by a later edit.
 R16 (ask's Ollama-down message is named, not raw) (BRIEF-0085-f): in
@@ -83,6 +85,7 @@ LORE_PLAN_FILE = SRC / "lore_plan.py"
 LORE_RESOLVE_FILE = SRC / "lore_resolve.py"
 LORE_ROUTE_FILE = SRC / "cockpit" / "routes" / "lore.py"
 LORE_PROMPT_FILE = SRC / "lore_prompt.py"
+PROMPT_LOAD_FILE = SRC / "prompt_load.py"
 LORE_RENDER_FILE = SRC / "lore_render.py"
 PURITY_FILES = (LORE_SELECTORS_FILE, LORE_QUERY_FILE)
 PANEL_FILES = (
@@ -90,6 +93,9 @@ PANEL_FILES = (
     SRC / "lore_mentions_read.py",
     SRC / "lore_choices_read.py",
     SRC / "cockpit" / "routes" / "lore_choices.py",
+    # TICKET-0098 (BRIEF-0098-D): the writing panel's modules.
+    SRC / "lore_write_apply.py",
+    SRC / "lore_write_draft.py",
 )
 PIPELINE_FILES = (LORE_SELECTORS_FILE, LORE_QUERY_FILE, LORE_PLAN_FILE, LORE_RENDER_FILE, LORE_PROMPT_FILE)
 
@@ -660,11 +666,17 @@ def check_render_template_raises_on_unknown_section() -> None:
 
 
 def check_prompt_loader_scoped_to_prompt_tables() -> None:
-    """R15: every `select(` in `lore_prompt.py` references only
+    """R15: every `select(` in `prompt_load.py` references only
     `PromptTemplate`/`PromptVersion` -- the module that owns the Session for
     this chantier's prompt resolution must never become a canon door by a
     later edit."""
-    tree = _parse(LORE_PROMPT_FILE)
+    reexport = _parse(LORE_PROMPT_FILE)
+    if reexport is not None and any(
+        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"
+        for n in ast.walk(reexport)
+    ):
+        fail(f"lore_isolation R15: {_rel(LORE_PROMPT_FILE)} calls select( -- it only re-exports")
+    tree = _parse(PROMPT_LOAD_FILE)
     if tree is None:
         return
     select_calls = [
@@ -672,7 +684,7 @@ def check_prompt_loader_scoped_to_prompt_tables() -> None:
         if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
     ]
     if not select_calls:
-        fail(f"lore_isolation R15: {_rel(LORE_PROMPT_FILE)} contains zero select( calls -- vacuous")
+        fail(f"lore_isolation R15: {_rel(PROMPT_LOAD_FILE)} contains zero select( calls -- vacuous")
         return
     for node in select_calls:
         names = {
@@ -682,7 +694,7 @@ def check_prompt_loader_scoped_to_prompt_tables() -> None:
         forbidden = names - _ALLOWED_PROMPT_MODELS
         if forbidden:
             fail(
-                f"lore_isolation R15: {_rel(LORE_PROMPT_FILE)}:{node.lineno} -- "
+                f"lore_isolation R15: {_rel(PROMPT_LOAD_FILE)}:{node.lineno} -- "
                 f"select( references non-prompt model(s) {sorted(forbidden)!r} -- "
                 "the prompt loader must never become a canon door"
             )
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 1c12d65..df29858 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -36,9 +36,30 @@ C1 -- apply (BRIEF-0098-C, C-02), on a fixture world, through
       the row counts of every recorded table are unchanged;
    e. a proposal refused by a write site (a second `bloc` fact on the same
       entity) raises `ProposalError`; after the rollback nothing remains.
+D1 -- draft (BRIEF-0098-D, C-05), with `lore_write_draft.chat` replaced by a
+   stub that records the messages and returns canned JSON:
+   a. `draft_context` lists the entities the statement names, codes their
+      facts and the world-level facts, and never codes a creator-only fact;
+   b. `draft_questions` keeps at most `MAX_QUESTIONS` non-empty strings;
+   c. `draft_proposal` returns a matched entity as `existing` with its id, a
+      name two entities share as `ambiguous` with both candidates, an
+      unknown name as `new` with the type of its category; resolves a
+      listed code to its fact id; drops an unlisted code and a typed or
+      unknown facet with one note per dropped fact, and silently drops a
+      knower with an unknown level and a ref to no entity;
+   d. no entity id and no fact id appears in any message sent to the model;
+   e. the draft, its ambiguity settled, passes `lore_write_apply.validate`;
+   f. an `OllamaError` from the model propagates out of both calls.
+D2 -- prompts. `seed_pilot.LORE_WRITE_PROMPT_HEADS` holds exactly the usages
+   `QUESTIONS_USAGE` and `PROPOSAL_USAGE`; each head's `variables` equal the
+   `{placeholders}` of its user template; `apply_ticket_0098_lore_write_prompts.py`
+   reads that tuple and embeds no prompt text; `lore_prompt.py` re-exports
+   `prompt_load.load`, the loader the writing path imports.
 C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
    `chat(`, no `.commit(`, and import neither `ollama_client` nor any
-   `cockpit` module.
+   `cockpit` module; `lore_write_draft.py` contains no `db.add(`, no
+   `.commit(`, and calls no writer (`write_`, `add_lore_fact(`,
+   `apply_proposal(`).
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -62,7 +83,7 @@ FAILURES: list[str] = []
 
 _CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
 _LORE_WRITE_FILES: frozenset[str] = frozenset({
-    "lore_write_apply.py", "writes/lore_entries.py",
+    "lore_write_apply.py", "writes/lore_entries.py", "lore_write_draft.py",
 })
 _PURE_FILES = ("lore_write_apply.py", "writes/lore_entries.py")
 _COUNTED_TABLES = ("entity", "fact", "fact_participant", "fact_default", "knowledge",
@@ -353,6 +374,151 @@ def check_c2() -> None:
         for needle in ("chat(", ".commit(", "ollama_client", "cockpit"):
             if needle in text:
                 fail(f"C2: {rel} contains {needle!r}")
+    draft = (SRC / "lore_write_draft.py").read_text(encoding="utf-8")
+    for needle in ("db.add(", ".commit(", "write_knowledge(", "write_lore_entry(",
+                   "add_lore_fact(", "apply_proposal("):
+        if needle in draft:
+            fail(f"C2: lore_write_draft.py contains {needle!r}")
+
+
+class _Stub:
+    def __init__(self, replies):
+        self.replies, self.messages = list(replies), []
+
+    def __call__(self, messages, **kwargs):
+        self.messages.append(messages)
+        reply = self.replies.pop(0)
+        if isinstance(reply, Exception):
+            raise reply
+        return __import__("json").dumps(reply)
+
+
+def check_d1() -> None:
+    from sqlmodel import Session
+
+    from world_engine import lore_write_apply as lwa
+    from world_engine import lore_write_draft as lwd
+    from world_engine.db import engine
+    from world_engine.models import Entity, Knowledge, Location
+    from world_engine.ollama_client import OllamaError
+    from world_engine.writes.facets import add_lore_fact
+
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+
+    with Session(engine) as db:
+        for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
+            if db.get(__import__("world_engine.models", fromlist=["PromptTemplate"]).PromptTemplate,
+                      head["id"]) is None:
+                seed_pilot.upsert_prompt_template(db, **head)
+        db.commit()
+        ids = _fixture(db)
+        world = ids["world"]
+        for name in ("Tour Nord", "Tour Nord"):
+            twin = Entity(world_id=world, type="location", name=name)
+            db.add(twin)
+            db.flush()
+            db.add(Location(id=twin.id))
+        general = add_lore_fact(db, world_id=world, facet="information", created_by="fixture",
+                                content="Les marées montent deux fois par nuit.", participant_ids=[])
+        hidden = add_lore_fact(db, world_id=world, facet="histoire", created_by="fixture",
+                               content="Maëlle est une espionne.", participant_ids=[ids["npc"]])
+        db.flush()
+        db.add(Knowledge(entity_id=ids["npc"], fact_id=hidden.fact.id, level="unaware",
+                         is_secret=True))
+        db.commit()
+        statement = "Maëlle dirige le Manoir Gris depuis la Tour Nord."
+        context = lwd.draft_context(db, world, statement)
+        joined = "\n".join(context.coded.lines)
+        if not any("Maëlle" in line for line in context.entity_lines) or \
+                not any("Manoir Gris" in line for line in context.entity_lines):
+            fail(f"D1a: named entities missing: {context.entity_lines}")
+        if context.coded.code_of(ids["bloc"]) is None or context.coded.code_of(general.fact.id) is None:
+            fail("D1a: an entity fact or a world-level fact is not coded")
+        if context.coded.code_of(hidden.fact.id) is not None or "espionne" in joined:
+            fail("D1a: a creator-only fact was coded")
+        bloc_code = context.coded.code_of(ids["bloc"])
+        stub = _Stub([
+            {"questions": ["Q1 ?", "", 3, "Q2 ?", "Q3 ?", "Q4 ?"]},
+            {"entities": [
+                {"ref": "e1", "name": "Maëlle", "category": "person"},
+                {"ref": "e2", "name": "Tour Nord", "category": "place"},
+                {"ref": "e3", "name": "Brume Salée", "category": "object"},
+                {"ref": "e4", "name": "Manoir Gris", "category": "place"}],
+             "facts": [
+                {"action": "create", "content": "Maëlle dirige le manoir.", "facet": "statut",
+                 "participants": ["e1", "e4"], "defaults": [{"scope_type": "location", "scope_ref": "e4"}],
+                 "knowers": [{"entity_ref": "e1", "level": "knows"},
+                             {"entity_ref": "e1", "level": "certain"}]},
+                {"action": "existing", "code": bloc_code, "participants": ["e9"]},
+                {"action": "existing", "code": "f999"},
+                {"action": "create", "content": "Lien.", "facet": "lien"},
+                {"action": "create", "content": "Humeur.", "facet": "humeur"}],
+             "memberships": [{"entity_ref": "e1", "faction_ref": "e9"}],
+             "controls": [{"owner_ref": "e1", "location_ref": "e4"}]},
+            OllamaError("down"), OllamaError("down"),
+        ])
+        original = lwd.chat
+        lwd.chat = stub
+        try:
+            questions = lwd.draft_questions(db, world, statement)
+            draft = lwd.draft_proposal(db, world, statement, "Tout le monde au manoir.")
+            for call in (lambda: lwd.draft_questions(db, world, statement),
+                         lambda: lwd.draft_proposal(db, world, statement)):
+                try:
+                    call()
+                    fail("D1f: an OllamaError did not propagate")
+                except OllamaError:
+                    pass
+        finally:
+            lwd.chat = original
+        if questions != ["Q1 ?", "Q2 ?", "Q3 ?"]:
+            fail(f"D1b: questions {questions!r}")
+        by_ref = {e["ref"]: e for e in draft["entities"]}
+        if by_ref.get("e1", {}).get("entity_id") != ids["npc"] or by_ref["e1"]["action"] != "existing":
+            fail(f"D1c: Maëlle not matched: {by_ref.get('e1')}")
+        if by_ref.get("e2", {}).get("status") != "ambiguous" or len(by_ref["e2"].get("candidates", [])) != 2:
+            fail(f"D1c: Tour Nord not ambiguous with two candidates: {by_ref.get('e2')}")
+        if by_ref.get("e3", {}).get("status") != "new" or by_ref["e3"].get("type") != "item":
+            fail(f"D1c: Brume Salée not new as an item: {by_ref.get('e3')}")
+        facts = draft["facts"]
+        if [f["action"] for f in facts] != ["create", "existing"] or facts[1].get("fact_id") != ids["bloc"]:
+            fail(f"D1c: facts kept {[(f['action'], f.get('fact_id')) for f in facts]}")
+        if len(facts[0]["knowers"]) != 1 or facts[1]["participants"] != [] or draft["memberships"]:
+            fail("D1c: an invalid knower, participant ref or membership survived")
+        if len(draft["notes"]) != 3 or draft["controls"] != [{"owner_ref": "e1", "location_ref": "e4"}]:
+            fail(f"D1c: notes {draft['notes']!r}, controls {draft['controls']!r}")
+        sent = __import__("json").dumps(stub.messages, ensure_ascii=False)
+        for secret_id in (ids["npc"], ids["manor"], ids["bloc"], general.fact.id):
+            if secret_id in sent:
+                fail(f"D1d: id {secret_id} reached the model")
+        by_ref["e2"].update(action="existing", entity_id=by_ref["e2"]["candidates"][0]["entity_id"])
+        try:
+            lwa.validate(db, world, draft)
+        except lwa.ProposalError as exc:
+            fail(f"D1e: the settled draft does not validate: {exc}")
+
+
+def check_d2() -> None:
+    import re as _re
+
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+
+    from world_engine import lore_prompt, lore_write_draft as lwd, prompt_load
+
+    heads = seed_pilot.LORE_WRITE_PROMPT_HEADS
+    if sorted(h["usage"] for h in heads) != sorted([lwd.QUESTIONS_USAGE, lwd.PROPOSAL_USAGE]):
+        fail(f"D2: heads carry usages {[h['usage'] for h in heads]}")
+    for head in heads:
+        found = set(_re.findall(r"\{([a-z_]+)\}", head["user_template"]))
+        if found != set(head["variables"]):
+            fail(f"D2: {head['id']} declares {head['variables']} but uses {sorted(found)}")
+    script = (ROOT / "scripts" / "apply_ticket_0098_lore_write_prompts.py").read_text(encoding="utf-8")
+    if "LORE_WRITE_PROMPT_HEADS" not in script or "Tu " in script:
+        fail("D2: the delivery script does not read the single source, or embeds text")
+    if lore_prompt.load is not prompt_load.load:
+        fail("D2: lore_prompt.load is not prompt_load.load")
 
 
 def main() -> int:
@@ -366,13 +532,16 @@ def main() -> int:
     check_w2(db_path)
     check_c1()
     check_c2()
+    check_d1()
+    check_d2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
           "v2.11 declares the source record and migrates from v2.10 only; a proposal "
-          "writes all or nothing, each row recorded, existing rows skipped")
+          "writes all or nothing, each row recorded, existing rows skipped; the draft "
+          "names things by name and code only and resolves both in code")
     return 0
 
 
diff --git a/tooling/verify/checks/name_index.py b/tooling/verify/checks/name_index.py
index 6ae6c53..6e060ab 100644
--- a/tooling/verify/checks/name_index.py
+++ b/tooling/verify/checks/name_index.py
@@ -18,7 +18,9 @@ R5 (creator confinement) -- across `src/world_engine/**/*.py`, `CREATOR`
    imported from `name_index` (or read as `name_index.CREATOR`) and any
    `NameScope(` call whose regime is the literal `"creator"` occur only in
    `name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
-   `writes/facets.py`. Vacuity guard: at least one file parsed.
+   `writes/facets.py`, `lore_write_draft.py` (the writing panel resolves the
+   names of the creator's own statement, TICKET-0098, BRIEF-0098-D).
+   Vacuity guard: at least one file parsed.
 R6 (explicit scope, BRIEF-0092-b) -- across `src/world_engine/**/*.py`, every
    call whose callee name (a Name, or the last part of an Attribute) is
    `resolve_named` or `near_candidates` passes a `scope=` keyword; every call
@@ -55,6 +57,7 @@ CREATOR_ALLOWED = {
     "src/world_engine/lore_query.py",
     "src/world_engine/lore_mentions_read.py",
     "src/world_engine/writes/facets.py",
+    "src/world_engine/lore_write_draft.py",
 }
 
 FAILURES: list[str] = []
````

## Scope OUT

- Routes and UI (E, F).
- Any change to the consultation pipeline beyond the loader's move (`lore_plan`, `lore_render`, `routes/lore.py` keep their imports).
- A fallback extractor when Ollama is down (K1).
- The whole world's facts in the model's list (L2).
- Adding the writing modules to `prompt_registry.py`'s `WIRED_FILES` (the `lore_plan.py` precedent: the model is already resolved by `prompt_load`).
- Running `apply_ticket_0098_lore_write_prompts.py` on Nia's DB (live gate).
- Every later brief of the lot: BRIEF-0098-E, BRIEF-0098-F.

## Invariants to defend

**A model names a fact only by a code from a `fact_refs.code_facts` list; code resolves it:** an unlisted code is dropped with a note. **Secrets are structurally excluded:** creator-only facts never enter the coded list; the creator regime of `name_index` is used for the creator's own statement only, and R5's allow-list records it. **All templated model calls resolve through `effective_model`:** via `prompt_load.load`. **Prompt text lives only in `prompt_version`:** the apply script embeds no text.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `lore_isolation.py` reports any pipeline module importing a panel module, or a panel module importing `lore_prompt`.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `upsert_prompt_template` raises on an undeclared placeholder in a check fixture: the head's `variables` must equal its `{placeholders}` (D2); fix the fixture, never the seed text, and report.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- Prompt wording Nia may want to tune after the live gate (it is editable in Prompts).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `lore_write.py` → `PASS … the draft names things by name and code only and resolves both in code`.
- `lore_isolation.py`, `name_index.py`, `prompt_registry.py`, `prompt_version.py`, `claude_md_contract.py`, `identity_tokens.py` → `PASS`.
- On a temp DB at v2.11: `apply_ticket_0098_lore_write_prompts.py` twice → `created` twice, then `existing` twice.
- Mutation test: in `_fact`, replace `coded.resolve(raw.get("code"))` by `raw.get("code")`; D1c and D1e fail; revert.
- `corpus_gate.py` → 128/128.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md (writing panel in the creator-regime clause; `prompt_load.py` on the `prompt_store.py` line; Lore read/write on the `lore_*.py` line — no new File structure line). Decision entry `THE MODEL DRAFTS, CODE RESOLVES, THE CREATOR CONFIRMS (TICKET-0098) … (BRIEF-0098-d, no schema change)`.
