<!-- slug: analyzer-events -->
# BRIEF 0114-H — "Play's analyzer proposes typed events, and may propose their type, approved with the event"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-G (C-10), BRIEF-0114-C (C-06), BRIEF-0114-F (C-09)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-G's commit).

- `src/world_engine/analyzer_transcript.py:455` -> `def _apply_type_guards(item: dict, attribution: AttributionContext) -> tuple[dict | None, bool]:`
- `scripts/seed_pilot.py:414` -> `CONVERSATION_ANALYSIS_USER_TEMPLATE = """\`
- `src/world_engine/event_payloads.py:55` -> `def _typed(payload: dict) -> EventSpec:`; `:89` -> `def spec_from_payload(`
- `src/world_engine/cockpit/routes/mutations.py` -> `_approve_apply_and_commit` with `with db.begin_nested():`
- No `src/world_engine/event_analysis.py`, no `scripts/apply_ticket_0114_analysis_prompt.py`.

## Facts carried

### R-04 — the event writers and the applier
Opened: `src/world_engine/writes/events.py:23` (`write_event(db, *,
world_id, title, description, type, knowledge_status, involved_entities,
location_id, mutation_id)`, no fact written), `write_event_update` (the
creator's correction); `src/world_engine/cockpit/mutations.py`
`_mutation_apply_event_creation` (calls `write_event` from the payload);
`src/world_engine/cockpit/routes/mutations.py:598`
(`_approve_apply_and_commit`: `with db.begin_nested()`, an applier's
error string raises, the savepoint rolls back, canon clean);
`tooling/verify/canon_write_policy.txt:85-86` (both writers write
`event`).
Consequence: C rewrites both writers on a spec (C-05), the applier reads
a payload into it (C-06); H's proposed type is written inside that same
savepoint.

### R-12 — Play's analysis [M]
Opened: `src/world_engine/analyzer_transcript.py:308`
(`_build_payload_event_creation`, untyped), `_apply_type_guards`,
`_normalize_to_schema`, `_window_call_model` (`str.replace` of
`{transcript}`, `{injected_context}`), `analyze_transcript`;
`scripts/seed_pilot.py:276` / `:414` (`CONVERSATION_ANALYSIS_*`, literal
constants); `tooling/verify/checks/prompt_lean.py` (reads them as literal
constants by AST: exactly 5 `=== EXEMPLE`, four rubric headers);
`scripts/apply_ticket_0097_fact_code_prompts.py` (re-delivers the seed's
whole analysis text with its own variable list).
Consequence: H edits the literal texts in place and keeps the fragments
beside them (EH1 keeps them equal); the 0097 script reads the seed's
variable list, so a re-run never lands a placeholder undeclared.

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contracts

### C-06 — an `event_creation` payload
Produced by: BRIEF-0114-C (H adds `new_type`, `sorte_name`)   Consumed by: H
`event_payloads.spec_from_payload(db, world_id, payload, *,
session_id=None, batch_id=None) -> EventSpec`; `provenance(db, mut) ->
(session_id, batch_id)`. Typed: `type_id`, `participants` [{role_id,
entity_id | sorte_id, secret}], `quantity`, `location_id`. Untyped: `type`
(a category), `involved_entities`, `knowledge_status` -- typed by its
domain (`ensure_domain_type`), its entities in « Impliqué », a `world`
scope at `knows` when `public`/`confirmed`. H: `new_type` (a definition,
C-10's `type_definition` form) instead of `type_id`, participants naming
its roles by `role`; `sorte_name` for a sorte the world lacks -- written in
the applier's savepoint, a same-named one used.

### C-09 — the interpreter's `t` list and the leaf in the model's form
Produced by: BRIEF-0114-F   Consumed by: G, H
`CODE_LISTS["event"] = "t"`; `InterpreterContext.event_types` (id ->
view), `.sortes` (id -> name); `interpreter_events.event_type_line(view,
types)` (« Chasse (rôles : Chasseur — personnage ; Proie — personnage ou
une sorte ; compte une quantité) »), `encode_event`, `read_event`,
`filters_waiting`, `bind_filters`. Model leaf: `{"op": "leaf", "form":
"event", "subject", "target": {"code": "t1"}, "value": a role's name |
null, "threshold", "place": {"name", "kind"} | null, "since", "with":
[{"role", "sorte"} | {"role", "name", "kind"} | {"role", "code"}]}`.
Prompt variables `event_types`, `sortes`; three fragments of
`CONDITION_INTERPRET_FRAGMENTS`.

### C-10 — proposed types and sortes
Produced by: BRIEF-0114-G   Consumed by: H
`event_proposals.type_spec(raw) -> EventTypeSpec` (model form: name,
domain (unknown -> `other`), roles [{name, for, sorte}], quantity,
chronicle, secret); `type_definition(spec) -> dict` (`typeDraft`'s
form); `read_vocabulary(db, world_id, types_raw, sortes_raw) ->
Vocabulary(proposals [{ref v1.. | o1.., kind, definition, near}], refs,
errors)` -- a name the world has binds silently; `bind_vocabulary(db,
world_id, pending, bindings) -> (pending, errors)` (`ValueError` on a
missing or foreign pick); `vocab_waiting(leaf)`. Pending leaf keys
`type_define`, `role_name`, a filter's `sorte_define` / `role_name`.
`Interpretation.vocabulary`; `PAYLOAD_KEYS` gains `vocabulary`;
`resolve(..., vocabulary=())`; the route answers `vocabulary`.

### C-11 — the analyzer's typed proposal
Produced by: BRIEF-0114-H   Consumed by: (TICKET-0119)
`event_analysis.AnalysisVocabulary(codes, types, sortes)` with
`prompt_values()`; `analysis_vocabulary(db, world_id)`;
`typed_payload(db, world_id, payload, vocab) -> Optional[dict]` -- None
drops it; a payload naming no type is returned unchanged; otherwise
`{title, description, type_id | None, type_name, participants [{role_id |
None, role, entity_id, sorte_id, sorte_name, secret}], quantity,
location_id, new_type?}`. Seed: `CONVERSATION_ANALYSIS_VARIABLES`,
`CONVERSATION_ANALYSIS_FRAGMENTS_0114`.

## Context

R1 in Play: the conversation analysis names an event's type by code and its participants by role, read fail-closed (an unknown code drops the proposal, a wrong participant is left out, never guessed). I2: when no type says what happened, it proposes one; the queue's card names it with its roles, the creator approves type and event together, and the applier writes both in its one savepoint. An untyped proposal keeps working (the tick's, until 0119).

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `event_analysis.py` (new, C-11): `AnalysisVocabulary`, `analysis_vocabulary`, `typed_payload`;
   - `analyzer_transcript.py`: `analyze_transcript` reads the vocabulary once and hands it to `_window_call_model` (the two placeholders) and to the builder; `_apply_type_guards` reads a typed `event_creation` through `typed_payload`;
   - `event_payloads.py`: `_typed(db, world_id, payload)` writes a proposed `new_type` (or uses the same-named one) and a `sorte_name` (likewise), resolves roles by name; `spec_from_payload` takes `new_type`;
   - `seed_pilot.py`: the analysis texts edited in place (the typed shape, an « EVENT_CREATION RUBRIC », the two lists), `CONVERSATION_ANALYSIS_VARIABLES`, `CONVERSATION_ANALYSIS_FRAGMENTS_0114`; `scripts/apply_ticket_0114_analysis_prompt.py` (new); `scripts/apply_ticket_0097_fact_code_prompts.py` reads the seed's variable list;
   - frontend: `QueueCard.svelte` (`eventSummary`: the type, a proposed type's badge and roles, participants by role, a sorte to create);
   - creates check `event_analyzer.py` (EH1-EH4);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/QueueCard.svelte
   - scripts/apply_ticket_0097_fact_code_prompts.py
   - scripts/apply_ticket_0114_analysis_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/analyzer_transcript.py
   - src/world_engine/event_analysis.py
   - src/world_engine/event_payloads.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_analyzer.py

````diff
diff --git a/frontend/src/creation/QueueCard.svelte b/frontend/src/creation/QueueCard.svelte
index 2d51cb0..5a1f776 100644
--- a/frontend/src/creation/QueueCard.svelte
+++ b/frontend/src/creation/QueueCard.svelte
@@ -105,7 +105,29 @@
     return null;
   }
 
+  /** TICKET-0114 (BRIEF-0114-H, I2): a typed event_creation read for the
+   *  creator -- its type (a proposed one with its roles, approved with the
+   *  event), each participant by role, its quantity. null otherwise (an
+   *  untyped proposal shows its payload only). */
+  function eventSummary(m) {
+    if (m.mutation_type !== 'event_creation') return null;
+    const p = m.payload || {};
+    if (!p.type_name) return null;
+    return {
+      typeName: p.type_name,
+      newType: p.new_type && typeof p.new_type === 'object' ? p.new_type : null,
+      participants: (p.participants || []).map((x) => ({
+        role: x.role || '',
+        name: x.entity_id ? mutationEntityName(x.entity_id) : (x.sorte_name || ''),
+        newSorte: !x.entity_id && !x.sorte_id && !!x.sorte_name,
+      })),
+      quantity: p.quantity || null,
+      place: p.location_id ? mutationEntityName(p.location_id) : '',
+    };
+  }
+
   let resourceLegs = $derived(resourceChangeLegs(mutation));
+  let eventLegs = $derived(eventSummary(mutation));
   let agendaSummary = $derived(agendaProvenanceSummary(mutation));
 
   function onCheckToggle(ev) {
@@ -203,6 +225,26 @@
     </div>
   {/if}
 
+  {#if eventLegs}
+    <div class="card-fields" style="margin-bottom:8px;">
+      <div class="field-label">Événement</div>
+      <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
+        <span style="font-weight:600;">{eventLegs.typeName}</span>
+        {#if eventLegs.newType}<span class="badge b-other">nouveau type — validé avec l'événement</span>{/if}
+        {#if eventLegs.quantity}<span>× {eventLegs.quantity}</span>{/if}
+        {#if eventLegs.place}<span style="font-size:12px; color:var(--muted);">à {eventLegs.place}</span>{/if}
+      </div>
+      {#if eventLegs.newType}
+        <div style="font-size:12px; color:var(--muted);">
+          Rôles : {eventLegs.newType.roles.map((r) => r.name + (r.accepts_sorte ? ' (ou une sorte)' : '')).join(', ')}
+        </div>
+      {/if}
+      {#each eventLegs.participants as x, i (i)}
+        <div style="font-size:12px;">{x.role} : <strong>{x.name}</strong>{#if x.newSorte} <span class="badge b-other">sorte à créer</span>{/if}</div>
+      {/each}
+    </div>
+  {/if}
+
   {#if agendaSummary?.kind === 'delegation'}
     <div class="card-fields" style="margin-bottom:8px;">
       <div class="field-label">Délégation</div>
diff --git a/scripts/apply_ticket_0097_fact_code_prompts.py b/scripts/apply_ticket_0097_fact_code_prompts.py
index e368981..83b5719 100644
--- a/scripts/apply_ticket_0097_fact_code_prompts.py
+++ b/scripts/apply_ticket_0097_fact_code_prompts.py
@@ -74,7 +74,7 @@ _UPDATES: tuple[tuple[str, str, str, list[str], str], ...] = (
         "pt-conversation-analysis",
         seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
         seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE,
-        ["transcript", "injected_context"],
+        list(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES),  # the seed's: its text names them (TICKET-0114)
         "TICKET-0097 BRIEF-0097-F -- no subject, no knowledge_change (M1, N1)",
     ),
     (
diff --git a/scripts/apply_ticket_0114_analysis_prompt.py b/scripts/apply_ticket_0114_analysis_prompt.py
new file mode 100644
index 0000000..2b0d48c
--- /dev/null
+++ b/scripts/apply_ticket_0114_analysis_prompt.py
@@ -0,0 +1,97 @@
+"""One-shot, idempotent delivery of the TICKET-0114 conversation analysis
+prompt update onto the live DB (BRIEF-0114-H): the analyzer reads the
+world's event types -- the `t` list, a new variable `event_types` -- and
+its sortes (`sortes`), names an event's type by code and its participants
+by role, and may propose a type (I2).
+
+Like `apply_ticket_0113_condition_prompt.py`, it edits the CURRENT version
+of `pt-conversation-analysis` fragment by fragment, so an edit the creator
+made in the Prompts tab is kept. The fragments are
+`seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114` (single source: the
+seed's texts hold each new fragment). Per fragment: its new text present ->
+already done (looked for first: an old fragment may stand inside its own
+new text); else its old text present -> replaced; neither -> reported, to
+be edited by hand. The head's variables are first set to the seed's
+(`write_prompt_variables`), since a new version may only use declared
+placeholders.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+
+Run after `migrate_v2_25_event_columns.py`:
+
+    python scripts/apply_ticket_0114_analysis_prompt.py
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
+        "apply_ticket_0114_analysis_prompt.py refuses to run unless "
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
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+from world_engine.writes.prompts import write_prompt_variables  # noqa: E402
+
+HEAD_ID = "pt-conversation-analysis"
+NOTE = "TICKET-0114 BRIEF-0114-H -- typed events by code and role, a proposed type (I2)"
+
+
+def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
+    """`texts` with every fragment applied where its old text stands; the
+    fragments found in neither form."""
+    out = dict(texts)
+    missing = []
+    for field, old, new in seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114:
+        if new in out[field]:
+            continue
+        if old in out[field]:
+            out[field] = out[field].replace(old, new)
+        else:
+            missing.append(f"{field}: {old[:60]}…")
+    return out, missing
+
+
+def main() -> None:
+    with Session(engine) as session:
+        head = session.get(PromptTemplate, HEAD_ID)
+        if head is None:
+            print(f"{HEAD_ID}: head not found -- nothing to do (the seed creates it)")
+            return
+        write_prompt_variables(session, template_id=head.id,
+                               variables=list(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES))
+        current = current_prompt(session, head)
+        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
+                                          "user_template": current.user_template})
+        for line in missing:
+            print(f"{HEAD_ID}: fragment not found, edit by hand -- {line}")
+        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
+            session.commit()
+            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
+            return
+        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
+                                       user_template=texts["user_template"], note=NOTE)
+        session.commit()
+        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index f39d471..51ee6a9 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -288,7 +288,7 @@ Every element must have these EXACT 5 keys — no other keys allowed:
 Payload shapes:
   relation_change  → {"entity_a_id":"…","entity_b_id":"…","relation_type":"…","intensity_delta":<signed int>}
   new_knowledge    → {"entity_id":"…","level":"rumor|partial|knows|…","content":"…","source":"…","subject_entity_id":"…" (OPTIONAL — see rubric below)}
-  event_creation   → {"title":"…","description":"…","type":"social|political|other","involved_entities":[…]}
+  event_creation   → {"title":"…","description":"…","event_type":"t2","participants":[{"role":"…","entity_id":"…"},{"role":"…","sorte":"…"}],"quantity":<int> (OPTIONAL),"location_id":"…" (OPTIONAL),"new_type":{…} (OPTIONAL — see rubric below)}
   resource_change  → {"entity_id":"char-player","amount":<signed int>,"counterparty_id":"…","reason":"…","knowledge":{"entity_id":"…","level":"…","content":"…","source":"…","is_secret":false} (knowledge is OPTIONAL — only when information changed hands)}
   goal_change      → {"action":"complete|abandon|create_short","goal":"…"}
 
@@ -352,6 +352,21 @@ identifiable — une rumeur générale, une information abstraite, un fait qui
 ne désigne aucune entité précise — omets entièrement le champ
 "subject_entity_id" plutôt que d'y mettre une valeur incertaine ou devinée.
 
+=== EVENT_CREATION RUBRIC ===
+event_creation — émets-en un quand il S'EST PASSÉ dans la scène quelque
+chose qui compte pour le monde (un combat, une capture, une découverte, un
+pacte, une mort), pas une simple conversation. "event_type" est le code
+d'un type de la liste TYPES D'ÉVÉNEMENTS ("t2"). Chaque participant tient
+un des rôles du type, nommé par son nom : une entité par son id
+("entity_id", pris dans NPC CONTEXT), ou une sorte anonyme de la liste
+SORTES par son nom ("sorte":"Loup") quand le rôle en accepte une.
+"quantity" seulement si le type se compte (« 3 loups »). Si aucun type de
+la liste ne dit ce qui s'est passé, n'en force pas un : propose-le dans
+"new_type" — {"name":"…","domain":"military|political|magical|criminal|social|mystery|other","roles":[{"name":"…","for":["character"],"sorte":false}],"quantity":false}
+— sans "event_type", ses participants nommant ses rôles. Une sorte absente
+de SORTES se nomme telle quelle : elle sera créée avec l'événement. La
+créatrice valide le type proposé avec l'événement.
+
 === GOAL_CHANGE RUBRIC ===
 goal_change — le bloc NPC CONTEXT peut contenir une section
 « TES OBJECTIFS » listant les objectifs actifs du PNJ. Émets un
@@ -415,11 +430,53 @@ CONVERSATION_ANALYSIS_USER_TEMPLATE = """\
 NPC CONTEXT (what the NPC was authorised to know):
 {injected_context}
 
+TYPES D'ÉVÉNEMENTS (code — nom, rôles) :
+{event_types}
+
+SORTES :
+{sortes}
+
 TRANSCRIPT:
 {transcript}
 
 JSON array of canon mutations ([] if nothing changed):"""
 
+# TICKET-0114 (BRIEF-0114-H, I2, R1): the analyzer names an event's type by
+# code, its participants by role, and may propose a type. The texts above
+# hold each new fragment; scripts/apply_ticket_0114_analysis_prompt.py
+# applies the same (field, old, new) triples to the CURRENT version, so an
+# edit the creator made in the Prompts tab is kept (event_analyzer.py keeps
+# the triples and the texts above equal).
+CONVERSATION_ANALYSIS_VARIABLES: tuple[str, ...] = ("transcript", "injected_context", "event_types", "sortes")
+CONVERSATION_ANALYSIS_FRAGMENTS_0114: tuple[tuple[str, str, str], ...] = (
+    ("system_prompt",
+     '  event_creation   → {"title":"…","description":"…","type":"social|political|other","involved_entities":[…]}',
+     '  event_creation   → {"title":"…","description":"…","event_type":"t2","participants":[{"role":"…",'
+     '"entity_id":"…"},{"role":"…","sorte":"…"}],"quantity":<int> (OPTIONAL),"location_id":"…" (OPTIONAL),'
+     '"new_type":{…} (OPTIONAL — see rubric below)}'),
+    ("system_prompt",
+     "=== GOAL_CHANGE RUBRIC ===",
+     "=== EVENT_CREATION RUBRIC ===\n"
+     "event_creation — émets-en un quand il S'EST PASSÉ dans la scène quelque\n"
+     "chose qui compte pour le monde (un combat, une capture, une découverte, un\n"
+     "pacte, une mort), pas une simple conversation. \"event_type\" est le code\n"
+     "d'un type de la liste TYPES D'ÉVÉNEMENTS (\"t2\"). Chaque participant tient\n"
+     "un des rôles du type, nommé par son nom : une entité par son id\n"
+     "(\"entity_id\", pris dans NPC CONTEXT), ou une sorte anonyme de la liste\n"
+     "SORTES par son nom (\"sorte\":\"Loup\") quand le rôle en accepte une.\n"
+     "\"quantity\" seulement si le type se compte (« 3 loups »). Si aucun type de\n"
+     "la liste ne dit ce qui s'est passé, n'en force pas un : propose-le dans\n"
+     "\"new_type\" — {\"name\":\"…\",\"domain\":\"military|political|magical|criminal|social|mystery|other\","
+     "\"roles\":[{\"name\":\"…\",\"for\":[\"character\"],\"sorte\":false}],\"quantity\":false}\n"
+     "— sans \"event_type\", ses participants nommant ses rôles. Une sorte absente\n"
+     "de SORTES se nomme telle quelle : elle sera créée avec l'événement. La\n"
+     "créatrice valide le type proposé avec l'événement.\n\n"
+     "=== GOAL_CHANGE RUBRIC ==="),
+    ("user_template",
+     "TRANSCRIPT:\n{transcript}",
+     "TYPES D'ÉVÉNEMENTS (code — nom, rôles) :\n{event_types}\n\nSORTES :\n{sortes}\n\nTRANSCRIPT:\n{transcript}"),
+)
+
 
 # Overhearing classification prompt — Tier 4, acquisition-only pass.
 # usage='overhearing_classification', world_id=NULL, destination='local'.
@@ -2884,7 +2941,7 @@ def seed(session: Session) -> None:
         usage="conversation_analysis",
         system_prompt=CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
         user_template=CONVERSATION_ANALYSIS_USER_TEMPLATE,
-        variables=["transcript", "injected_context"],
+        variables=list(CONVERSATION_ANALYSIS_VARIABLES),
         destination="local",
     )
 
diff --git a/src/world_engine/analyzer_transcript.py b/src/world_engine/analyzer_transcript.py
index 1394417..79c2058 100644
--- a/src/world_engine/analyzer_transcript.py
+++ b/src/world_engine/analyzer_transcript.py
@@ -59,6 +59,7 @@ from typing import Any, Optional
 from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
+from .event_analysis import AnalysisVocabulary, analysis_vocabulary, typed_payload
 from .models import Character, Entity, Fact, Knowledge, ProposedMutation, PromptTemplate
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
@@ -452,12 +453,19 @@ def _guard_goal_change(item: dict, attribution: AttributionContext) -> tuple[dic
     return item, False
 
 
-def _apply_type_guards(item: dict, attribution: AttributionContext) -> tuple[dict | None, bool]:
+def _apply_type_guards(item: dict, attribution: AttributionContext, db: Session | None = None,
+                       world_id: str | None = None,
+                       vocab: AnalysisVocabulary | None = None) -> tuple[dict | None, bool]:
     """Type-specific fail-closed guards, run after payload construction.
     Returns (item-or-None, unattributed). Order and rejection semantics
     frozen: every rejection path rejects identically to the
-    pre-decomposition code."""
+    pre-decomposition code. TICKET-0114 (BRIEF-0114-H): a typed
+    `event_creation` is read against the world's event vocabulary
+    (`event_analysis.typed_payload`) when the call showed it."""
     mt = item["mutation_type"]
+    if mt == "event_creation" and vocab is not None and db is not None:
+        item["payload"] = typed_payload(db, world_id, item["payload"], vocab)
+        return (item if item["payload"] is not None else None), False
     if mt == "relation_change":
         return _guard_relation_change(item), False
     if mt == "resource_change":
@@ -480,6 +488,7 @@ def _normalize_to_schema(
     world_id: str,
     attribution: AttributionContext,
     db: Session,
+    vocab: AnalysisVocabulary | None = None,
 ) -> tuple[dict | None, bool, str]:
     """Map a model's natural output object to our ProposedMutation schema fields.
 
@@ -504,7 +513,7 @@ def _normalize_to_schema(
     if not item.get("payload"):
         return None, unattributed, mt
 
-    item, guard_unattributed = _apply_type_guards(item, attribution)
+    item, guard_unattributed = _apply_type_guards(item, attribution, db, world_id, vocab)
     unattributed = unattributed or guard_unattributed
     if item is None:
         return None, unattributed, mt
@@ -556,7 +565,7 @@ def _mutation_match_key(mutation_type: str, payload: dict):
 
 def _window_call_model(
     db: Session, world_id: str, transcript: str, injected_ctx_str: str,
-    model: str, host: str,
+    model: str, host: str, vocab: AnalysisVocabulary | None = None,
 ) -> list:
     """Model call + JSON parse. Raises llm_parse.LlmParseError (logged here
     with the raw snippet) on a parse failure — analyze_transcript does not
@@ -572,6 +581,9 @@ def _window_call_model(
         .replace("{transcript}", transcript)
         .replace("{injected_context}", injected_ctx_str)
     )
+    # TICKET-0114 (BRIEF-0114-H): the world's event types and sortes.
+    for name, value in (vocab.prompt_values() if vocab is not None else {}).items():
+        user_message = user_message.replace("{" + name + "}", value)
     llm_messages = [
         {"role": "system", "content": version.system_prompt},
         {"role": "user", "content": user_message},
@@ -594,13 +606,14 @@ def _window_call_model(
 
 def _window_build_mutations(
     items: list, world_id: str, attribution: AttributionContext, db: Session, covered: set,
+    vocab: AnalysisVocabulary | None = None,
 ) -> tuple[list[ProposedMutation], int, dict[str, int]]:
     now = datetime.now(UTC)
     mutations: list[ProposedMutation] = []
     dropped_unattributed = 0
     dropped_by_type: dict[str, int] = {}
     for i, raw_item in enumerate(items):
-        normalized, unattributed, mt = _normalize_to_schema(raw_item, world_id, attribution, db)
+        normalized, unattributed, mt = _normalize_to_schema(raw_item, world_id, attribution, db, vocab)
         if normalized is None:
             if unattributed:
                 dropped_unattributed += 1
@@ -652,9 +665,10 @@ def analyze_transcript(
     Raises llm_parse.LlmParseError on a model-output parse failure — the
     caller decides what "failure" means for its own marker/commit semantics.
     """
-    items = _window_call_model(db, world_id, transcript, injected_context, model, host)
+    vocab = analysis_vocabulary(db, world_id)
+    items = _window_call_model(db, world_id, transcript, injected_context, model, host, vocab)
     mutations, dropped_unattributed, dropped_by_type = _window_build_mutations(
-        items, world_id, attribution, db, covered_keys,
+        items, world_id, attribution, db, covered_keys, vocab,
     )
     return TranscriptAnalysis(
         mutations=mutations,
diff --git a/src/world_engine/event_analysis.py b/src/world_engine/event_analysis.py
new file mode 100644
index 0000000..a8c67a0
--- /dev/null
+++ b/src/world_engine/event_analysis.py
@@ -0,0 +1,162 @@
+"""The play analyzer's typed events (TICKET-0114, BRIEF-0114-H; decisions
+I2 and R1 of the conditions series).
+
+The conversation analysis (`analyzer_transcript.analyze_transcript`) shows
+the model the world's event types as a coded list (`t`, each with its
+roles) and its sortes by name. Its `event_creation` names a type by code
+(`event_type`), each participant by the NAME of the role it holds -- an
+entity by id, or a sorte by name -- and a quantity when the type counts
+one. When no type says what happened, it may propose one (`new_type`, I2):
+the creator approves the type with the event, and the applier writes both
+in its one savepoint (`event_payloads`).
+
+`typed_payload` reads that proposal into the payload the queue shows and
+the applier reads, fail-closed: an unknown type code, or a proposed type
+the writer refuses, drops the proposal; a participant whose role the type
+lacks, or whose entity is not one of the world's the role accepts, is left
+out, never guessed. A sorte the world lacks keeps its name (`sorte_name`):
+it is created with the event. A payload with neither `event_type` nor
+`new_type` is the former, untyped shape (`event_payloads` types it by its
+domain).
+
+Reads only; writes nothing.
+"""
+
+from __future__ import annotations
+
+import logging
+from dataclasses import dataclass, field
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from .event_proposals import type_definition, type_spec
+from .event_vocab import EventTypeView, role_accepts, world_event_types, world_sortes
+from .fact_refs import CodedRefs, code_refs
+from .interpreter_events import event_type_line
+from .lore_resolve import normalize_surface
+from .models import Entity
+from .writes.event_types import clean_event_type
+
+_log = logging.getLogger(__name__)
+
+
+@dataclass(frozen=True)
+class AnalysisVocabulary:
+    """The world's event vocabulary as one analysis call shows it."""
+
+    codes: CodedRefs
+    types: dict[str, EventTypeView] = field(default_factory=dict)
+    sortes: dict[str, str] = field(default_factory=dict)  # id -> name
+
+    def prompt_values(self) -> dict[str, str]:
+        return {"event_types": "\n".join(self.codes.lines) or "(aucun)",
+                "sortes": ", ".join(self.sortes.values()) or "(aucune)"}
+
+
+def analysis_vocabulary(db: Session, world_id: str) -> AnalysisVocabulary:
+    from .attributes import world_entity_type_labels
+
+    labels = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
+    types = {view.id: view for view in world_event_types(db, world_id)}
+    return AnalysisVocabulary(
+        codes=code_refs("t", ((tid, event_type_line(view, labels)) for tid, view in types.items())),
+        types=types, sortes={s.id: s.name for s in world_sortes(db, world_id)},
+    )
+
+
+@dataclass(frozen=True)
+class _Role:
+    id: Optional[str]
+    name: str
+    entity_types: tuple[str, ...]
+    accepts_sorte: bool
+
+
+def _type_of(db: Session, world_id: str, payload: dict, vocab: AnalysisVocabulary):
+    """(type id, type name, its roles, counts quantity, new type definition)
+    or None when the proposal names no type it may."""
+    code = payload.get("event_type")
+    if code is not None and not isinstance(code, dict):
+        type_id = vocab.codes.resolve(code)
+        if type_id is None:
+            _log.warning("[skip] event_creation: unknown event type code %r", code)
+            return None
+        view = vocab.types[type_id]
+        roles = tuple(_Role(r.id, r.name, r.entity_types, r.accepts_sorte) for r in view.active_roles())
+        return type_id, view.name, roles, view.counts_quantity, None
+    raw = payload.get("new_type")
+    if not isinstance(raw, dict):
+        return None
+    same = next((v for v in vocab.types.values()
+                 if normalize_surface(v.name) == normalize_surface(str(raw.get("name") or ""))), None)
+    if same is not None:  # a type the world has under that very name
+        return _type_of(db, world_id, {"event_type": vocab.codes.code_of(same.id)}, vocab)
+    try:
+        clean = clean_event_type(db, world_id, type_spec(raw))
+    except ValueError as exc:
+        _log.warning("[skip] event_creation: proposed type refused (%s): %r", exc, raw)
+        return None
+    roles = tuple(_Role(None, r.name, r.entity_types, r.accepts_sorte) for r in clean.roles)
+    return None, clean.name, roles, clean.counts_quantity, type_definition(clean)
+
+
+def _participant(db: Session, world_id: str, raw: Any, roles: tuple[_Role, ...],
+                 vocab: AnalysisVocabulary) -> Optional[dict]:
+    if not isinstance(raw, dict):
+        return None
+    key = normalize_surface(str(raw.get("role") or ""))
+    role = next((r for r in roles if key and normalize_surface(r.name) == key), None)
+    if role is None:
+        return None
+    out = {"role_id": role.id, "role": role.name, "entity_id": None, "sorte_id": None, "sorte_name": None,
+           "secret": None}
+    if raw.get("sorte") not in (None, ""):
+        if not role.accepts_sorte:
+            return None
+        name = str(raw["sorte"]).strip()
+        out["sorte_id"] = next((sid for sid, s in vocab.sortes.items()
+                                if normalize_surface(s) == normalize_surface(name)), None)
+        out["sorte_name"] = vocab.sortes.get(out["sorte_id"], name)
+        return out
+    entity = db.get(Entity, raw.get("entity_id")) if isinstance(raw.get("entity_id"), str) else None
+    if entity is None or entity.world_id != world_id or entity.status != "active" \
+            or not role_accepts(role, entity.type):
+        return None
+    out["entity_id"] = entity.id
+    return out
+
+
+def typed_payload(db: Session, world_id: str, payload: dict, vocab: AnalysisVocabulary) -> Optional[dict]:
+    """The queue's payload of one typed `event_creation`, or None to drop it.
+    A payload naming no type at all is returned as it is (the untyped shape)."""
+    if payload.get("event_type") is None and payload.get("new_type") is None:
+        return payload
+    found = _type_of(db, world_id, payload, vocab)
+    if found is None:
+        return None
+    type_id, type_name, roles, counts, definition = found
+    participants: list[dict] = []
+    for raw in payload.get("participants") or []:
+        item = _participant(db, world_id, raw, roles, vocab)
+        if item is None:
+            _log.warning("[skip] event_creation participant left out: %r", raw)
+            continue
+        if not any((p["role"], p["entity_id"], p["sorte_name"]) == (item["role"], item["entity_id"],
+                                                                    item["sorte_name"]) for p in participants):
+            participants.append(item)
+    quantity = payload.get("quantity")
+    quantity = quantity if counts and isinstance(quantity, int) and not isinstance(quantity, bool) \
+        and quantity >= 1 else None
+    place = db.get(Entity, payload.get("location_id")) if isinstance(payload.get("location_id"), str) else None
+    out = {
+        "title": str(payload.get("title") or "").strip() or type_name,
+        "description": payload.get("description") or None,
+        "type_id": type_id, "type_name": type_name,
+        "participants": participants, "quantity": quantity,
+        "location_id": place.id if place is not None and place.world_id == world_id
+        and place.type == "location" else None,
+    }
+    if definition is not None:
+        out["new_type"] = definition
+    return out
diff --git a/src/world_engine/event_payloads.py b/src/world_engine/event_payloads.py
index c066d48..84d1110 100644
--- a/src/world_engine/event_payloads.py
+++ b/src/world_engine/event_payloads.py
@@ -7,7 +7,13 @@ proposal's payload into that writer's `EventSpec`. Two payload shapes:
 
 - typed (the play analyzer since BRIEF-0114-H): `type_id`, `participants`
   (`role_id` with an `entity_id` or a `sorte_id`, and `secret`),
-  `quantity`, `location_id`. Its scopes are its type's (W1).
+  `quantity`, `location_id`. Its scopes are its type's (W1). Or, instead
+  of `type_id`, `new_type` (I2): the type the model proposed, approved with
+  the event -- written first (`write_event_type`; a type the world has by
+  then under that name is used instead), its participants naming its roles
+  by `role`; a participant's `sorte_name` is a sorte the world lacked,
+  written likewise (`write_sorte`) unless it exists by then. All inside the
+  applier's savepoint: refused, nothing is written.
 - untyped (the world tick until TICKET-0119, and every proposal written
   before): `type` (a former category), `involved_entities`,
   `knowledge_status`, `location_id`. It is typed by its domain
@@ -22,7 +28,9 @@ mutation's conversation, or the session and day of its declared action; a
 tick proposal has neither.
 
 Reads, and writes only through `ensure_domain_type` (an untyped proposal
-whose domain has no type yet makes it, inside the applier's savepoint).
+whose domain has no type yet makes it), `write_event_type` and
+`write_sorte` (a typed one's proposed type and sortes) -- each inside the
+applier's savepoint.
 """
 
 from __future__ import annotations
@@ -31,9 +39,11 @@ from typing import Optional
 
 from sqlmodel import Session
 
-from .event_vocab import role_accepts, type_view
+from .event_proposals import type_spec
+from .event_vocab import role_accepts, type_view, world_event_types, world_sortes
+from .lore_resolve import normalize_surface
 from .models import Conversation, Entity, PassPlay, ProposedMutation
-from .writes.event_types import ensure_domain_type
+from .writes.event_types import ensure_domain_type, write_event_type, write_sorte
 from .writes.events import EventScopeSpec, EventSpec, ParticipantSpec
 
 PUBLIC_STATUSES: tuple[str, ...] = ("public", "confirmed")
@@ -52,19 +62,52 @@ def provenance(db: Session, mut: ProposedMutation) -> tuple[Optional[str], Optio
     return None, None
 
 
-def _typed(payload: dict) -> EventSpec:
-    participants = tuple(
-        ParticipantSpec(role_id=str(p.get("role_id") or ""), entity_id=p.get("entity_id") or None,
-                        sorte_id=p.get("sorte_id") or None,
-                        secret=p.get("secret") if isinstance(p.get("secret"), bool) else None)
-        for p in (payload.get("participants") or []) if isinstance(p, dict)
-    )
+def _new_type(db: Session, world_id: str, definition: dict) -> str:
+    """The proposed type's id: the world's type of that name, or the one
+    written now. The card's definition is the writer's spec in the form
+    of `event_proposals.type_definition`."""
+    key = normalize_surface(str(definition.get("name") or ""))
+    same = next((v for v in world_event_types(db, world_id) if normalize_surface(v.name) == key), None)
+    if same is not None:
+        return same.id
+    spec = type_spec({"name": definition.get("name"), "domain": definition.get("domain"),
+                      "quantity": definition.get("counts_quantity"),
+                      "chronicle": definition.get("in_chronicle"), "secret": definition.get("participants_secret"),
+                      "roles": [{"name": r.get("name"), "for": r.get("entity_types") or [],
+                                 "sorte": r.get("accepts_sorte")}
+                                for r in definition.get("roles") or [] if isinstance(r, dict)]})
+    return write_event_type(db, world_id=world_id, spec=spec).id
+
+
+def _sorte(db: Session, world_id: str, name: str) -> str:
+    key = normalize_surface(name)
+    same = next((s for s in world_sortes(db, world_id) if normalize_surface(s.name) == key), None)
+    return same.id if same is not None else write_sorte(db, world_id=world_id, name=name).id
+
+
+def _typed(db: Session, world_id: str, payload: dict) -> EventSpec:
+    type_id = payload.get("type_id")
+    if not type_id and isinstance(payload.get("new_type"), dict):
+        type_id = _new_type(db, world_id, payload["new_type"])
+    view = type_view(db, str(type_id))
+    by_name = {normalize_surface(r.name): r.id for r in view.active_roles()} if view is not None else {}
+    participants = []
+    for p in payload.get("participants") or []:
+        if not isinstance(p, dict):
+            continue
+        role_id = p.get("role_id") or by_name.get(normalize_surface(str(p.get("role") or ""))) or ""
+        sorte_id = p.get("sorte_id") or None
+        if sorte_id is None and str(p.get("sorte_name") or "").strip():
+            sorte_id = _sorte(db, world_id, str(p["sorte_name"]).strip())
+        participants.append(ParticipantSpec(
+            role_id=str(role_id), entity_id=p.get("entity_id") or None, sorte_id=sorte_id,
+            secret=p.get("secret") if isinstance(p.get("secret"), bool) else None))
     quantity = payload.get("quantity")
     return EventSpec(
-        type_id=str(payload.get("type_id")), title=str(payload.get("title") or ""),
+        type_id=str(type_id), title=str(payload.get("title") or ""),
         description=payload.get("description"), location_id=payload.get("location_id") or None,
         quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
-        participants=participants,
+        participants=tuple(participants),
     )
 
 
@@ -89,5 +132,6 @@ def _untyped(db: Session, world_id: str, payload: dict) -> EventSpec:
 def spec_from_payload(db: Session, world_id: str, payload: dict, *, session_id: Optional[str] = None,
                       batch_id: Optional[str] = None) -> EventSpec:
     """The `EventSpec` of one `event_creation` payload, typed or not."""
-    spec = _typed(payload) if payload.get("type_id") else _untyped(db, world_id, payload)
+    typed = payload.get("type_id") or isinstance(payload.get("new_type"), dict)
+    spec = _typed(db, world_id, payload) if typed else _untyped(db, world_id, payload)
     return EventSpec(**{**spec.__dict__, "session_id": session_id, "batch_id": batch_id})
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 01bab8d..fc41b64 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19454,6 +19454,33 @@ ref to a real id keeps one validation path (`clean_leaf`), with no unsaved
 type to carry through the offer's save. A type created for a proposal she
 then discards stays in the vocabulary, where she can retire it.
 
+## PLAY'S ANALYZER PROPOSES TYPED EVENTS, AND MAY PROPOSE THEIR TYPE, APPROVED WITH THE EVENT (TICKET-0114) -- `event_analysis.py` (BRIEF-0114-h, no schema change)
+
+**R1 in Play.** The conversation analysis shows the model the world's event
+types as a coded list (`t`, each with its roles) and its sortes by name.
+Its `event_creation` names the type by code, each participant by the name
+of the role it holds -- an entity by id, a sorte by name -- and a quantity
+when the type counts one. `event_analysis.typed_payload` reads it
+fail-closed: an unknown code drops the proposal; a participant whose role
+the type lacks, or whose entity is not one the role accepts in this world,
+is left out, never guessed; a quantity the type does not count is dropped.
+A payload naming no type keeps the former shape (typed by its domain at
+apply, as the tick's until TICKET-0119).
+
+**I2.** When no type says what happened, the model proposes one
+(`new_type`), cleaned by the writer's own rules when it is read -- refused,
+the proposal is dropped. The queue's card names the proposed type and its
+roles: the creator approves the type with the event, and the applier
+writes both in its one savepoint (`event_payloads`): refused, neither is
+written. A sorte the world lacks keeps its name and is written likewise. A
+type or sorte the world has by then under that very name is used, never
+duplicated.
+
+**Prompt.** Three fragments of `CONVERSATION_ANALYSIS_FRAGMENTS_0114` (the
+typed shape, an EVENT_CREATION RUBRIC, the two lists in the message),
+delivered by `apply_ticket_0114_analysis_prompt.py`, fragment by fragment:
+the creator's edits are kept.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_analyzer.py b/tooling/verify/checks/event_analyzer.py
new file mode 100644
index 0000000..48bfee2
--- /dev/null
+++ b/tooling/verify/checks/event_analyzer.py
@@ -0,0 +1,361 @@
+"""G1 check for TICKET-0114 -- Play's analyzer proposes typed events, and may propose their type, approved with the event.
+
+BRIEF-0114-H's rules.
+
+EH1 -- the prompt (static and fixture). The seed's analysis texts hold each
+   new fragment of `CONVERSATION_ANALYSIS_FRAGMENTS_0114` exactly once and
+   no longer the untyped `event_creation` shape; the head's variables
+   (`CONVERSATION_ANALYSIS_VARIABLES`) are exactly the user template's
+   placeholders and `AnalysisVocabulary.prompt_values` fills the two new
+   ones. `apply_ticket_0114_analysis_prompt.py`, on a head holding the
+   former texts and variables, writes one version equal to the seed's with
+   its variables; a second run is unchanged; on a head the creator edited
+   where a fragment stood, her edit is kept and the fragment reported.
+EH2 -- reading the proposal (fixture). `typed_payload` of an
+   `event_creation` naming a type by code keeps its id and name, each
+   participant by role -- an entity the role accepts, a sorte of the world
+   by id, a sorte it lacks by name --, and the quantity when the type
+   counts one; it leaves out a participant whose role the type lacks, an
+   entity of another type or world, and a quantity the type does not
+   count; an unknown code drops the proposal; a proposed type (`new_type`)
+   is kept cleaned, its roles named, no id; a proposed type the writer
+   refuses drops it; a `new_type` named as a type the world has is that
+   type; a payload naming no type is returned unchanged.
+EH3 -- applying (fixture). An approved proposal with a proposed type and a
+   sorte the world lacks writes the type, the sorte and the event with its
+   participants in their roles; a second one proposing the same type uses
+   it, no second type; one whose proposed type the writer refuses answers
+   an `event_creation:` error and, its savepoint rolled back, writes
+   nothing.
+EH4 -- wiring (static). `analyze_transcript` reads `analysis_vocabulary`
+   once and hands it to the model call and to the builder;
+   `QueueCard.svelte` shows a typed event (`eventSummary`) and a proposed
+   type's badge.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import re
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+SCRIPT = ROOT / "scripts" / "apply_ticket_0114_analysis_prompt.py"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    sys.path.insert(0, str(ROOT / "scripts"))
+
+
+# --- EH1 -----------------------------------------------------------------------
+
+def _former_texts() -> dict[str, str]:
+    import seed_pilot
+
+    texts = {"system_prompt": seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
+             "user_template": seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE}
+    for field, old, new in seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114:
+        texts[field] = texts[field].replace(new, old)
+    return texts
+
+
+def _prompt_db(texts: dict[str, str]) -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import PromptTemplate
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(PromptTemplate(id="pt-conversation-analysis", name="analysis", usage="conversation_analysis",
+                              world_id=None, destination="local"))
+        db.flush()
+        write_prompt_variables(db, template_id="pt-conversation-analysis",
+                               variables=["transcript", "injected_context"])
+        write_prompt_version(db, template_id="pt-conversation-analysis", note="former", **texts)
+        db.commit()
+    eng.dispose()
+    return db_path
+
+
+def _run(db_path: str):
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, select
+
+    from world_engine.models import PromptTemplate, PromptVariable
+    from world_engine.prompt_store import current_prompt
+
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
+                            cwd=str(ROOT), timeout=60)
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as db:
+        version = current_prompt(db, db.get(PromptTemplate, "pt-conversation-analysis"))
+        state = (version.version_number, version.system_prompt, version.user_template,
+                 set(db.exec(select(PromptVariable.name)).all()))
+    eng.dispose()
+    return result, state
+
+
+def check_eh1() -> None:
+    import seed_pilot
+
+    from world_engine.event_analysis import AnalysisVocabulary
+    from world_engine.fact_refs import CodedRefs
+
+    texts = {"system_prompt": seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
+             "user_template": seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE}
+    fragments = seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114
+    if not fragments:
+        fail("EH1: CONVERSATION_ANALYSIS_FRAGMENTS_0114 is empty")
+    for field, old, new in fragments:
+        if texts[field].count(new) != 1:
+            fail(f"EH1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
+    if '"type":"social|political|other","involved_entities"' in texts["system_prompt"]:
+        fail("EH1: the seed still teaches the untyped event_creation shape")
+    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
+    values = AnalysisVocabulary(codes=CodedRefs(codes={}, lines=())).prompt_values()
+    if used != set(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES) or not set(values) <= used:
+        fail(f"EH1: variables {seed_pilot.CONVERSATION_ANALYSIS_VARIABLES}, template {sorted(used)}, "
+             f"values {sorted(values)}")
+    seed = (texts["system_prompt"], texts["user_template"])
+    result, state = _run(_prompt_db(_former_texts()))
+    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
+            or state[3] != set(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES):
+        fail(f"EH1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
+             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
+    db_path = _prompt_db(_former_texts())
+    again, state = _run(db_path)
+    again, state = _run(db_path)
+    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
+        fail(f"EH1: a second run: {again.stdout.strip()[-200:]}")
+    edited = _former_texts()
+    _field, lost, _new = fragments[0]
+    edited["system_prompt"] = edited["system_prompt"].replace(lost, "(retouché à la main)")
+    result, state = _run(_prompt_db(edited))
+    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[1] \
+            or "{event_types}" not in state[2]:
+        fail(f"EH1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")
+
+
+# --- fixture -------------------------------------------------------------------
+
+def _world(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, World
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        ids = {}
+        for key, name in (("world", "Analyse EH"), ("other", "Ailleurs")):
+            world = World(name=name, is_active=key == "world")
+            db.add(world)
+            db.flush()
+            ids[key] = world.id
+        for key, kind, name, world in (("foret", "location", "Forêt", "world"), ("mira", "character", "Mira", "world"),
+                                       ("brakk", "character", "Brakk", "world"),
+                                       ("etranger", "character", "Étranger", "other")):
+            row = Entity(world_id=ids[world], type=kind, name=name)
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Location(id=row.id) if kind == "location" else Character(id=row.id, world_id=ids[world],
+                                                                            character_type="npc"))
+        ids["loup"] = write_sorte(db, world_id=ids["world"], name="Loup").id
+        chasse = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
+            name="Chasse", counts_quantity=True,
+            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
+        duel = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
+            name="Duel", roles=(RoleSpec("Adversaire", ("character",)),)))
+        ids.update(chasse=chasse.id, duel=duel.id)
+        ids["chasseur"], ids["proie"] = (r.id for r in type_view(db, chasse.id).roles)
+        db.commit()
+    return ids
+
+
+def _new_type(**over) -> dict:
+    raw = {"name": "Piéger", "domain": "criminal", "quantity": True,
+           "roles": [{"name": "piégeur", "for": ["character"]}, {"name": "proie", "for": ["character"],
+                                                                 "sorte": True}]}
+    raw.update(over)
+    return raw
+
+
+# --- EH2 -----------------------------------------------------------------------
+
+def check_eh2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_analysis import analysis_vocabulary, typed_payload
+
+    with Session(engine) as db:
+        vocab = analysis_vocabulary(db, ids["world"])
+        if "t1 — Chasse (rôles : Chasseur — personnage ; Proie — personnage ou une sorte ; compte une quantité)" \
+                not in vocab.codes.lines or vocab.prompt_values()["sortes"] != "Loup":
+            fail(f"EH2: the vocabulary reads {vocab.codes.lines}, {vocab.prompt_values()}")
+        out = typed_payload(db, ids["world"], {
+            "title": "Mira chasse", "event_type": "t1", "quantity": 3, "location_id": ids["foret"],
+            "participants": [{"role": "chasseur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "loup"},
+                             {"role": "proie", "sorte": "Ours"}, {"role": "témoin", "entity_id": ids["brakk"]},
+                             {"role": "chasseur", "entity_id": ids["foret"]},
+                             {"role": "chasseur", "entity_id": ids["etranger"]}]}, vocab)
+        got = [(p["role_id"], p["entity_id"], p["sorte_id"], p["sorte_name"]) for p in (out or {}).get(
+            "participants", [])]
+        if out is None or out["type_id"] != ids["chasse"] or out["type_name"] != "Chasse" or out["quantity"] != 3 \
+                or out["location_id"] != ids["foret"] or got != [
+                    (ids["chasseur"], ids["mira"], None, None), (ids["proie"], None, ids["loup"], "Loup"),
+                    (ids["proie"], None, None, "Ours")]:
+            fail(f"EH2: a typed proposal reads {out}")
+        duel = typed_payload(db, ids["world"], {"title": "Duel", "event_type": "t2", "quantity": 4,
+                                                "participants": []}, vocab)
+        if duel is None or duel["quantity"] is not None:
+            fail(f"EH2: a type that counts nothing kept {duel}")
+        if typed_payload(db, ids["world"], {"title": "?", "event_type": "t9"}, vocab) is not None:
+            fail("EH2: an unknown type code was kept")
+        new = typed_payload(db, ids["world"], {"title": "Mira piège", "new_type": _new_type(), "participants": [
+            {"role": "Piégeur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "Lapin"}]}, vocab)
+        if new is None or new["type_id"] is not None or new.get("new_type", {}).get("name") != "Piéger" \
+                or [(p["role_id"], p["role"]) for p in new["participants"]] != [(None, "piégeur"), (None, "proie")]:
+            fail(f"EH2: a proposed type reads {new}")
+        if typed_payload(db, ids["world"], {"title": "?", "new_type": _new_type(roles=[{"name": "x",
+                                                                                         "for": ["dragon"]}])},
+                         vocab) is not None:
+            fail("EH2: a proposed type the writer refuses was kept")
+        same = typed_payload(db, ids["world"], {"title": "?", "new_type": _new_type(name="chasse")}, vocab)
+        if same is None or same["type_id"] != ids["chasse"] or "new_type" in same:
+            fail(f"EH2: a proposed type the world has reads {same}")
+        untyped = {"title": "La fête", "type": "social", "involved_entities": [ids["mira"]]}
+        if typed_payload(db, ids["world"], dict(untyped), vocab) != untyped:
+            fail("EH2: an untyped payload was changed")
+
+
+# --- EH3 -----------------------------------------------------------------------
+
+def check_eh3(engine, ids: dict) -> None:
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.event_analysis import analysis_vocabulary, typed_payload
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Event, EventParticipant, EventSorte, EventType, ProposedMutation
+
+    def mutation(db, payload):
+        mut = ProposedMutation(world_id=ids["world"], source_type="conversation", mutation_type="event_creation",
+                               target_table="event", payload=payload, status="approved")
+        db.add(mut)
+        db.flush()
+        return mut
+
+    def count(db, model):
+        return db.exec(select(func.count()).select_from(model)).one()
+
+    with Session(engine) as db:
+        vocab = analysis_vocabulary(db, ids["world"])
+        payload = typed_payload(db, ids["world"], {"title": "Mira piège trois lapins", "new_type": _new_type(),
+                                                   "quantity": 3, "participants": [
+            {"role": "piégeur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "Lapin"}]}, vocab)
+        with db.begin_nested():
+            error = _apply_mutation(mutation(db, payload), db)
+        db.commit()
+        event = db.exec(select(Event).where(Event.title == "Mira piège trois lapins")).first()
+        view = type_view(db, event.type_id) if event else None
+        rows = {(p.role_id, p.entity_id, p.sorte_id) for p in db.exec(select(EventParticipant).where(
+            EventParticipant.event_id == (event.id if event else "")))}
+        lapin = db.exec(select(EventSorte).where(EventSorte.name == "Lapin")).first()
+        roles = {r.name: r.id for r in view.roles} if view else {}
+        if error or view is None or view.name != "Piéger" or lapin is None or event.quantity != 3 \
+                or rows != {(roles.get("piégeur"), ids["mira"], None), (roles.get("proie"), None, lapin.id)}:
+            fail(f"EH3: a proposed type gave {error!r}, type {view and view.name}, participants {rows}")
+        types = count(db, EventType)
+        with db.begin_nested():
+            again = _apply_mutation(mutation(db, dict(payload, title="Brakk piège")), db)
+        db.commit()
+        if again or count(db, EventType) != types:
+            fail(f"EH3: the same proposed type twice gave {again!r}, {count(db, EventType) - types} more type(s)")
+        before = (count(db, EventType), count(db, Event), count(db, EventSorte))
+        broken = dict(payload, title="Cassé", new_type=dict(payload["new_type"], name="Braconner",
+                                                            roles=[{"name": "x", "entity_types": ["dragon"]}]))
+        broken["participants"] = [{"role": "proie", "sorte_name": "Renard"}]
+        answer = None
+        try:
+            with db.begin_nested():
+                answer = _apply_mutation(mutation(db, broken), db)
+                if answer:
+                    raise RuntimeError(answer)
+        except RuntimeError:
+            pass
+        db.commit()
+        if not (answer or "").startswith("event_creation:") \
+                or (count(db, EventType), count(db, Event), count(db, EventSorte)) != before:
+            fail(f"EH3: a refused proposed type answered {answer!r} and wrote "
+                 f"{(count(db, EventType), count(db, Event), count(db, EventSorte))} from {before}")
+
+
+# --- EH4 -----------------------------------------------------------------------
+
+def _function(path: pathlib.Path, name: str) -> str:
+    source = path.read_text(encoding="utf-8")
+    for node in ast.walk(ast.parse(source)):
+        if isinstance(node, ast.FunctionDef) and node.name == name:
+            return ast.get_source_segment(source, node) or ""
+    return ""
+
+
+def check_eh4() -> None:
+    body = _function(SRC / "analyzer_transcript.py", "analyze_transcript")
+    if body.count("analysis_vocabulary(db, world_id)") != 1 or "model, host, vocab)" not in body \
+            or "covered_keys, vocab," not in body:
+        fail("EH4: analyze_transcript does not hand one vocabulary to the call and the builder")
+    card = (ROOT / "frontend" / "src" / "creation" / "QueueCard.svelte").read_text(encoding="utf-8")
+    for needle in ("function eventSummary(m)", "nouveau type — validé avec l'événement"):
+        if needle not in card:
+            fail(f"EH4: QueueCard.svelte lacks {needle!r}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    check_eh1()
+    ids = _world(engine)
+    for check in (check_eh2, check_eh3):
+        try:
+            check(engine, ids)
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
+    check_eh4()
+    for msg in FAILURES:
+        print(f"FAIL: {msg}")
+    if FAILURES:
+        return 1
+    print("PASS: event_analyzer -- Play's analyzer reads the world's event types by code and its sortes, proposes "
+          "an event by type and role, fail-closed, and may propose its type, written with the event in one "
+          "savepoint; its prompt is delivered fragment by fragment")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Deliver the prompt on Nia's database after the merge: `python scripts/apply_ticket_0114_analysis_prompt.py`.
4. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
5. Run the checks below, then the full corpus.

## Scope OUT

- The tick's and Journée's typed producers, M-c, U1, Y2 -- TICKET-0119.
- Auto-applying a typed event (D2 of the series, rejected): every proposal goes through the queue.

## Invariants to defend

Creator control (CLAUDE.md « Creator control is structural »): a proposed type is written only on approval, inside `_apply_mutation`'s savepoint -- refused, neither the type nor the event is written (EH3). INV-30's discipline: a participant is never attributed by guess. INV-14: no engine auto-apply. INV-48: the prompt is a new version.

## Decision rights

STOP:
- `prompt_lean.py` fails (an example or a rubric header lost).
- A path would write a proposed type outside the applier's savepoint.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/event_analyzer.py` -> `PASS`.
- `python tooling/verify/checks/analyzer_seam.py` -> `PASS`.
- `python tooling/verify/checks/prompt_lean.py` -> `PASS`.
- `python tooling/verify/checks/event_writes.py` -> `PASS`.
- `python tooling/verify/checks/knowledge_identity.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (156 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EH1** -- `apply_ticket_0114_analysis_prompt.py` `apply_fragments`: `if new in out[field]:\n            continue` -> `pass`
  - **EH2** -- `event_analysis.py` `_participant`: `or not role_accepts(role, entity.type):` -> `or False:`
  - **EH3** -- `event_payloads.py` `_sorte`: `return same.id if same is not None else write_sorte(…)` -> `return write_sorte(…)`; or `_new_type`: drop its `if same is not None: return same.id`
  - **EH4** -- `analyzer_transcript.py` `analyze_transcript`: `covered_keys, vocab,` -> `covered_keys,`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
