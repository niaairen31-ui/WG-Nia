<!-- slug: coded-refs-prompt-call -->
# BRIEF 0112-A — "One coded list, one templated JSON call -- `CodedRefs` names any target by code, `prompt_call.call_json` serves the authoring tools"

Lot: LOT-0112-condition-interpreter.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main` at `c317053`).

- `src/world_engine/fact_refs.py:78` -> `class CodedFacts:`
- `src/world_engine/fact_refs.py:96` -> `def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedFacts:`
- `src/world_engine/lore_write_draft.py:28` -> `from . import llm_parse, model_exchange, prompt_load`
- `src/world_engine/lore_write_draft.py:79` -> `def _world_facts(db: Session, world_id: str) -> list[str]:`
- `src/world_engine/lore_write_draft.py:115` -> `def _call(db: Session, usage: str, values: dict[str, str], exchanges: Exchanges) -> dict:`
- `src/world_engine/prompt_registry.py:285` -> `"lore_statement_to_proposal": PromptSpec(`
- `CLAUDE.md:473` -> `│   ├── prompt_store.py, prompt_load.py  # prompt_version accessor; Lore-shell prompt loader`
- No `src/world_engine/prompt_call.py` and no `tooling/verify/checks/condition_interpreter.py` exist.

## Facts carried

### R-01 — the coded fact list [M]
Opened: `src/world_engine/fact_refs.py:32` (`CODE_PREFIX = "f"`),
`:78-93` (`CodedFacts`: `codes`, `lines`, `resolve` tolerating case,
spaces and brackets, `code_of`), `:96-110` (`code_facts`: ids in order,
first occurrence wins, a missing fact skipped, line `f<n> — <text>`).
Importers (enumeration (c) 1): `lore_write_draft.py:31`, `tick_context.py:40`,
`tick_normalize.py:27`, `tick.py:26`, `day_plan.py:38`,
`analyzer_transcript.py:65`; `tooling/verify/checks/knowledge_identity.py:50`
names it in its docstring (its code imports `code_facts` only, `:485`).
Consequence: A renames the class to `CodedRefs` in `fact_refs.py` and its
six importers, adds `code_refs(prefix, pairs)`, and `code_facts` returns
`code_refs("f", ...)` -- same codes, same lines (NA1). No new module.

### R-02 — the Lore draft's model call, and who stubs it [M]
Opened: `src/world_engine/lore_write_draft.py:28` (`from . import llm_parse,
model_exchange, prompt_load`), `:35` (`from .ollama_client import chat`),
`:115-131` (`_call`: `prompt_load.load`, `{name}` replacement,
`model_exchange.begin`, `chat(..., model=spec.model, format="json")`, raw
output kept before `llm_parse.extract_object`).
`tooling/verify/checks/lore_write.py:510` (`original = lwd.chat`, then the
stub assigned to `lwd.chat`), `tooling/verify/checks/lore_usage.py:453-456`
(`_swap(module, stub)`: `module.chat = stub`, applied to `lwd`).
`src/world_engine/prompt_registry.py:278-291` (both Lore writing usages'
call site `src/world_engine/lore_write_draft.py:_call`);
`tooling/verify/checks/prompt_registry.py` rule 2 (docstring `:6-7`, each
`path:function` resolves to a file with that `def`).
Consequence: the shared call takes the client as a parameter and each
caller passes the `chat` it imported, looked up at call time -- the stubs
keep reaching the call; `_call` stays in `lore_write_draft.py` (the
registry's call site) as one `return` of `prompt_call.call_json(...)`.

### R-03 — the prompt loader is fenced to the prompt tables [M]
Opened: `src/world_engine/prompt_load.py:35-43` (`RenderSpec`: plain
strings, `version_id`, `version_number`), `:50-72` (`load`: active head,
current version, `effective_model(template, _author_model())`);
`tooling/verify/checks/lore_isolation.py:671-700` (R15: every `select(` in
`prompt_load.py` names only `PromptTemplate`/`PromptVersion`).
Consequence: the JSON call lives in its own module, `prompt_call.py`, not in
`prompt_load.py`; it calls `prompt_load.load` and adds no `select(`.

### R-04 — one model exchange, and its failure [M]
Opened: `src/world_engine/model_exchange.py:25-37` (`ModelExchange`,
`to_record`), `:40-55` (`begin`: appends when the caller keeps a list),
`:58-64` (`fail`: records the error on the last exchange without one).
Consequence: the interpreter and its route keep exchanges the same way;
`fail` is the route's on `OllamaError` / `LlmParseError` (D).

### R-05 — the Lore draft's context [M]
Opened: `src/world_engine/lore_write_draft.py:43` (`MAX_CODED_FACTS = 200`),
`:68-76` (`named_entity_ids`: the tokenizer's entity tokens, in order),
`:79-85` (`_world_facts`: facts with no participant, relation, event or
law), `:88-102` (`draft_context`: named entities' facts, then world facts,
creator-only excluded via `creator_only_fact_ids`, capped).
`src/world_engine/facet_reads.py:44-55` (`_creator_only_select`: a stored
`unaware`, `is_secret` row of one of the fact's own participants), `:58-63`.
Consequence: C reuses `named_entity_ids`, `MAX_CODED_FACTS` and the world
facts (made public as `world_fact_ids` in A) but builds its own list, with
the current tree's facts first and creator-only facts kept (IE1).

### R-21 — CLAUDE.md budgets, measured in characters [M]
Opened: `tooling/verify/checks/claude_md_contract.py:69-71`
(`TOTAL_CHAR_BUDGET = 38_000` on `len(text)`, `MAX_LINE_LENGTH = 100`,
`FILE_STRUCTURE_LINE_BUDGET = 80`); `CLAUDE.md` on `main`: 37 180
characters (37 839 bytes -- the handover's figure), File structure at 80
lines; `:461` (`day_plan.py, condition*.py`), `:473` (`prompt_store.py,
prompt_load.py`). No rule requires every module to be listed (the check's
implementation reads the section's length, its archaeology patterns and
pointer freshness only).
Consequence: A folds `prompt_call.py` into line 473, C extends line 461's
comment; no line added.

## Contracts

### C-01 — `fact_refs.CodedRefs`, `code_refs`, `code_facts`
Produced by: BRIEF-0112-A   Consumed by: BRIEF-0112-C (and the six renamed importers)
Signature: `CodedRefs(codes: dict[str, str], lines: tuple[str, ...])`;
`CodedRefs.resolve(code: object) -> Optional[str]`;
`CodedRefs.code_of(target_id: str) -> Optional[str]`;
`code_refs(prefix: str, pairs: Iterable[tuple[str, str]]) -> CodedRefs`;
`code_facts(db, fact_ids: Iterable[str]) -> CodedRefs`.
Return shape: codes `<prefix><n>`, n from 1, positional; line
`<prefix><n> — <label>`.
Error and empty cases: an empty id is skipped; a repeated id keeps its
first code; `resolve` returns None for a non-string, a code the list did
not show, a code of another prefix; tolerates case, spaces, brackets.
`code_facts` skips an id with no `fact` row. No exception.

### C-02 — `prompt_call.call_json`
Produced by: BRIEF-0112-A   Consumed by: `lore_write_draft._call`, BRIEF-0112-C
Signature: `call_json(db, usage: str, values: dict[str, str], exchanges:
Optional[list[ModelExchange]], chat: Callable[..., str]) -> dict`.
Return shape: the parsed JSON object (`llm_parse.extract_object`).
Error and empty cases: `LlmParseError` on a missing prompt head or an
unparsable reply; whatever `chat` raises (`OllamaError`) propagates. When
`exchanges` is a list, one `ModelExchange` is appended before the call and
its `raw_output` set before parsing.

## Context

TICKET-0111 gave conditions a tree; TICKET-0112 writes them from French. Before the interpreter exists, two pieces it shares with the Lore writing panel are made general, at constant behaviour: the coded list a model picks targets from (ID1a: facts today, quest offers and skills next), and the one templated JSON call to the model, which today lives privately in `lore_write_draft._call`. Nothing new is reachable by the creator after this brief.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `fact_refs.py`: `CodedFacts` becomes `CodedRefs` (same fields and methods), `code_refs(prefix, pairs)` codes any `(id, label)` pairs, `code_facts` returns `code_refs("f", ...)` (C-01); the module docstring says so;
   - renames `CodedFacts` to `CodedRefs` in its six importers (R-01) and in `knowledge_identity.py`'s docstring -- annotations and imports only;
   - creates `src/world_engine/prompt_call.py` with `call_json` (C-02): `lore_write_draft._call`'s former body, verbatim, the client a parameter;
   - `lore_write_draft.py`: `_call` becomes one `return prompt_call.call_json(db, usage, values, exchanges, chat)`; `llm_parse` and `prompt_load` leave its imports; `_world_facts` becomes the public `world_fact_ids`;
   - `CLAUDE.md` line 473 names `prompt_call.py` (no line added);
   - creates `tooling/verify/checks/condition_interpreter.py` with NA1 and NA2;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - src/world_engine/analyzer_transcript.py
   - src/world_engine/day_plan.py
   - src/world_engine/fact_refs.py
   - src/world_engine/lore_write_draft.py
   - src/world_engine/prompt_call.py
   - src/world_engine/tick.py
   - src/world_engine/tick_context.py
   - src/world_engine/tick_normalize.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/knowledge_identity.py

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 74e3cc5..32b54f2 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -470,7 +470,7 @@ WG-Nia/
 │   ├── lore_*.py, unbound_facts.py, fact_refs.py  # Lore read/write; unbound facts; fact codes
 │   ├── writes/               # canon-write helpers by domain; schema.py is the DDL authority
 │   ├── prompt_registry.py   # prompt wiring registry; effective_model resolver
-│   ├── prompt_store.py, prompt_load.py  # prompt_version accessor; Lore-shell prompt loader
+│   ├── prompt_store.py, prompt_load.py, prompt_call.py  # version accessor; loader; JSON call
 │   ├── entity_author.py     # AI authoring assistant (entities, PC, skills, agendas, events)
 │   ├── region_author.py     # region generation orchestrator (proposes names, no canon)
 │   ├── spatial_author.py    # Creation-side door materialization from live connects_to
diff --git a/src/world_engine/analyzer_transcript.py b/src/world_engine/analyzer_transcript.py
index c176c48..1394417 100644
--- a/src/world_engine/analyzer_transcript.py
+++ b/src/world_engine/analyzer_transcript.py
@@ -62,7 +62,7 @@ from . import llm_parse, ollama_client
 from .models import Character, Entity, Fact, Knowledge, ProposedMutation, PromptTemplate
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
-from .fact_refs import CodedFacts, code_facts, find_held, knowledge_key
+from .fact_refs import CodedRefs, code_facts, find_held, knowledge_key
 from .prose_render import fact_text, knowledge_text
 from .writes import knowledge_level_rank
 
@@ -663,7 +663,7 @@ def analyze_transcript(
     )
 
 
-def _overhearing_fact_codes(attribution: AttributionContext, db: Session) -> CodedFacts:
+def _overhearing_fact_codes(attribution: AttributionContext, db: Session) -> CodedRefs:
     """c. The closed, coded fact list (L1, TICKET-0097): the facts the
     possible speakers hold on a non-secret row -- the NPC's first, then the
     counterparty's, each in `Knowledge.id` order. Only these can source a
@@ -682,7 +682,7 @@ def _overhearing_fact_codes(attribution: AttributionContext, db: Session) -> Cod
 
 def _overhearing_classify(
     db: Session, world_id: str, speaker_line: str, listener_line: str,
-    facts: CodedFacts, model: str, host: str,
+    facts: CodedRefs, model: str, host: str,
 ) -> list | None:
     """d. Model call."""
     template = load_analysis_prompt(
@@ -705,7 +705,7 @@ def _overhearing_classify(
     return llm_parse.extract_array_or_none(raw)
 
 
-def _overhearing_parse_classifications(items: list, facts: CodedFacts) -> list[tuple[str, str]]:
+def _overhearing_parse_classifications(items: list, facts: CodedRefs) -> list[tuple[str, str]]:
     """e. Normalization — a code the list showed, resolved to its fact id;
     anything else is dropped. No fuzzy matching."""
     classified: list[tuple[str, str]] = []
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 3b8dfef..bcf3eb8 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -35,7 +35,7 @@ from .conditions import (
     map_leaves,
     read_condition,
 )
-from .fact_refs import CodedFacts, code_facts
+from .fact_refs import CodedRefs, code_facts
 from .models import (
     BASE_SKILL_DOMAINS,
     SCHEDULE_PHASES,
@@ -300,7 +300,7 @@ def _validate_step(raw: object) -> PlanStep:
     return PlanStep(objective=objective.strip(), cost=cost, domain=domain, prerequisite=all_of(requirements))
 
 
-def learnable_facts(character: Character, db: Session) -> CodedFacts:
+def learnable_facts(character: Character, db: Session) -> CodedRefs:
     """D1'a (TICKET-0097): the coded list of facts a `knowledge` gate may
     name — anchorable (B3) and not already held (A1b), ordered by their
     rendered text, at most `MAX_LEARNABLE_FACTS_SHOWN` (the rest is counted
@@ -316,7 +316,7 @@ def learnable_facts(character: Character, db: Session) -> CodedFacts:
     return code_facts(db, [fact.id for fact in ordered[:MAX_LEARNABLE_FACTS_SHOWN]])
 
 
-def learnable_facts_summary(character_name: str, learnable: CodedFacts) -> str:
+def learnable_facts_summary(character_name: str, learnable: CodedRefs) -> str:
     """The French text `emit_plan` appends for `learnable` (BRIEF-0078-a's
     appended-text shape, never a template placeholder). Positive form only —
     the gameplay model is abliterated. "" when the list is empty."""
@@ -329,7 +329,7 @@ def learnable_facts_summary(character_name: str, learnable: CodedFacts) -> str:
     )
 
 
-def _resolve_knowledge_codes(steps: list[PlanStep], learnable: CodedFacts) -> list[PlanStep]:
+def _resolve_knowledge_codes(steps: list[PlanStep], learnable: CodedRefs) -> list[PlanStep]:
     """Each `knowledge` requirement's code becomes its fact id; a code the
     list did not show is kept as emitted, for `anchor_requirements` to drop
     and report."""
diff --git a/src/world_engine/fact_refs.py b/src/world_engine/fact_refs.py
index fcd04fb..db3ba4d 100644
--- a/src/world_engine/fact_refs.py
+++ b/src/world_engine/fact_refs.py
@@ -6,10 +6,13 @@ consequences live here, and only here:
 
 - **Codes (D1'a, L1, Z2).** A model never emits a fact id and never copies a
   free-text key. It is shown a coded list (`f1 — <the fact's text>`), emits
-  a code, and `CodedFacts.resolve` turns it back into a fact id -- or None
+  a code, and `CodedRefs.resolve` turns it back into a fact id -- or None
   for any code the list did not show. Codes are positional: the same fact
   ids in the same order give the same codes, so a list rebuilt from the same
-  rows resolves the codes a prompt carried.
+  rows resolves the codes a prompt carried. Since TICKET-0112 (BRIEF-0112-A,
+  ID1a) the list is general: `code_refs` codes any `(id, label)` pairs under
+  one prefix (the condition interpreter's quest offers `q`, skills `s`),
+  and `code_facts` is its fact list.
 - **Identity key (M1).** `knowledge_key(payload)` is the dedup identity of a
   `new_knowledge` payload or a `resource_change` knowledge leg:
   `("fact", fact_id)` when the payload names an existing fact,
@@ -75,25 +78,39 @@ def find_held(db: Session, entity_id: Optional[str], payload: dict) -> Optional[
 
 
 @dataclass(frozen=True)
-class CodedFacts:
-    """A coded fact list: `lines[i]` shows the fact coded `f{i+1}`."""
+class CodedRefs:
+    """A coded list: `lines[i]` shows the target coded `<prefix>{i+1}`."""
 
     codes: dict[str, str]
     lines: tuple[str, ...]
 
     def resolve(self, code: object) -> Optional[str]:
-        """The fact id behind `code`, or None when the list did not show it.
+        """The id behind `code`, or None when the list did not show it.
         Surrounding whitespace and brackets are tolerated (`[f3]`, ` F3 `)."""
         if not isinstance(code, str):
             return None
         return self.codes.get(code.strip().strip("[]").strip().lower())
 
-    def code_of(self, fact_id: str) -> Optional[str]:
-        """The code the list gives `fact_id`, or None."""
-        return next((code for code, fid in self.codes.items() if fid == fact_id), None)
+    def code_of(self, target_id: str) -> Optional[str]:
+        """The code the list gives `target_id`, or None."""
+        return next((code for code, tid in self.codes.items() if tid == target_id), None)
 
 
-def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedFacts:
+def code_refs(prefix: str, pairs: Iterable[tuple[str, str]]) -> CodedRefs:
+    """Code `(id, label)` pairs in order under `prefix`, first occurrence of
+    an id wins. Each line is `<prefix><n> — <label>`."""
+    codes: dict[str, str] = {}
+    lines: list[str] = []
+    for target_id, label in pairs:
+        if not target_id or target_id in codes.values():
+            continue
+        code = f"{prefix}{len(codes) + 1}"
+        codes[code] = target_id
+        lines.append(f"{code} — {label}")
+    return CodedRefs(codes=codes, lines=tuple(lines))
+
+
+def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedRefs:
     """Code `fact_ids` in order, first occurrence wins; an id with no `fact`
     row is skipped. Each line is `f<n> — <the fact's rendered text>`."""
     ordered: list[str] = []
@@ -101,10 +118,4 @@ def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedFacts:
         if fact_id and fact_id not in ordered:
             ordered.append(fact_id)
     facts = [fact for fact in (db.get(Fact, fid) for fid in ordered) if fact is not None]
-    codes: dict[str, str] = {}
-    lines: list[str] = []
-    for index, (fact, text) in enumerate(zip(facts, fact_texts(db, facts)), start=1):
-        code = f"{CODE_PREFIX}{index}"
-        codes[code] = fact.id
-        lines.append(f"{code} — {text}")
-    return CodedFacts(codes=codes, lines=tuple(lines))
+    return code_refs(CODE_PREFIX, ((fact.id, text) for fact, text in zip(facts, fact_texts(db, facts))))
diff --git a/src/world_engine/lore_write_draft.py b/src/world_engine/lore_write_draft.py
index 540e598..4c542a3 100644
--- a/src/world_engine/lore_write_draft.py
+++ b/src/world_engine/lore_write_draft.py
@@ -25,10 +25,10 @@ from typing import Any, Optional
 
 from sqlmodel import Session, select
 
-from . import llm_parse, model_exchange, prompt_load
+from . import model_exchange, prompt_call
 from .facet_reads import creator_only_fact_ids
 from .facets import FACETS
-from .fact_refs import CodedFacts, code_facts
+from .fact_refs import CodedRefs, code_facts
 from .lore_resolve import near_candidates, resolve_named
 from .models import Entity, Fact, FactParticipant
 from .name_index import CREATOR
@@ -62,7 +62,7 @@ class DraftContext:
     """What the model may see: the named entities and the coded facts."""
 
     entity_lines: tuple[str, ...]
-    coded: CodedFacts
+    coded: CodedRefs
 
 
 def named_entity_ids(db: Session, world_id: str, statement: str) -> list[str]:
@@ -76,7 +76,7 @@ def named_entity_ids(db: Session, world_id: str, statement: str) -> list[str]:
     return ordered
 
 
-def _world_facts(db: Session, world_id: str) -> list[str]:
+def world_fact_ids(db: Session, world_id: str) -> list[str]:
     """Free facts of the world with no participant (world-level lore)."""
     bound = select(FactParticipant.fact_id)
     return list(db.exec(select(Fact.id).where(
@@ -96,7 +96,7 @@ def draft_context(db: Session, world_id: str, statement: str) -> DraftContext:
         entity_lines.append(f"- {entity.name} ({entity.type})")
         fact_ids += db.exec(select(FactParticipant.fact_id).where(
             FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
-    fact_ids += _world_facts(db, world_id)
+    fact_ids += world_fact_ids(db, world_id)
     hidden = creator_only_fact_ids(db, fact_ids)
     kept = [fid for fid in dict.fromkeys(fact_ids) if fid not in hidden][:MAX_CODED_FACTS]
     return DraftContext(entity_lines=tuple(entity_lines), coded=code_facts(db, kept))
@@ -115,20 +115,10 @@ Exchanges = Optional[list[model_exchange.ModelExchange]]
 def _call(db: Session, usage: str, values: dict[str, str], exchanges: Exchanges) -> dict:
     """One model call. When `exchanges` is a list (TICKET-0103, BRIEF-0103-B,
     C-03), the call is appended to it as a `ModelExchange`, its raw reply
-    kept before parsing, so a reply that does not parse is still recorded."""
-    spec = prompt_load.load(db, usage)
-    user_message = spec.user_template
-    for key, value in values.items():
-        user_message = user_message.replace("{" + key + "}", value)
-    exchange = model_exchange.begin(exchanges, usage, spec, spec.system_prompt, user_message)
-    raw = chat(
-        [{"role": "system", "content": spec.system_prompt},
-         {"role": "user", "content": user_message}],
-        model=spec.model, format="json",
-    )
-    if exchange is not None:
-        exchange.raw_output = raw
-    return llm_parse.extract_object(raw)
+    kept before parsing, so a reply that does not parse is still recorded.
+    The call itself is `prompt_call.call_json` (TICKET-0112, BRIEF-0112-A),
+    handed this module's `chat`."""
+    return prompt_call.call_json(db, usage, values, exchanges, chat)
 
 
 def _values(context: DraftContext, statement: str, answers: str = "") -> dict[str, str]:
@@ -207,7 +197,7 @@ def _knowers(raw: Any, known: set[str]) -> list[dict]:
     return out
 
 
-def _fact(raw: Any, coded: CodedFacts, known: set[str], notes: list[str]) -> Optional[dict]:
+def _fact(raw: Any, coded: CodedRefs, known: set[str], notes: list[str]) -> Optional[dict]:
     if not isinstance(raw, dict):
         return None
     action = raw.get("action")
diff --git a/src/world_engine/prompt_call.py b/src/world_engine/prompt_call.py
new file mode 100644
index 0000000..b2591d5
--- /dev/null
+++ b/src/world_engine/prompt_call.py
@@ -0,0 +1,44 @@
+"""One templated JSON call to the model, shared by the creator's authoring
+tools (TICKET-0112, BRIEF-0112-A -- extracted verbatim from
+`lore_write_draft._call`, which now delegates here).
+
+`call_json` loads a usage's prompt through `prompt_load.load`, fills the
+user template's `{name}` variables, records the exchange when the caller
+keeps a list (`model_exchange.begin`; the raw reply is kept before parsing,
+so a reply that does not parse is still recorded), calls the model and
+parses one JSON object (`llm_parse.extract_object`).
+
+The model client is a parameter: each caller passes the `chat` it imported,
+so a check that replaces `<caller module>.chat` still reaches the call
+(`lore_write.py` D1, `lore_usage.py` U6, `condition_interpreter.py`). This
+module imports no client, writes nothing and commits nothing.
+`OllamaError` and `LlmParseError` propagate.
+"""
+
+from __future__ import annotations
+
+from typing import Callable, Optional
+
+from sqlmodel import Session
+
+from . import llm_parse, model_exchange, prompt_load
+
+
+def call_json(
+    db: Session, usage: str, values: dict[str, str],
+    exchanges: Optional[list[model_exchange.ModelExchange]], chat: Callable[..., str],
+) -> dict:
+    """One model call for `usage`, its template filled with `values`."""
+    spec = prompt_load.load(db, usage)
+    user_message = spec.user_template
+    for key, value in values.items():
+        user_message = user_message.replace("{" + key + "}", value)
+    exchange = model_exchange.begin(exchanges, usage, spec, spec.system_prompt, user_message)
+    raw = chat(
+        [{"role": "system", "content": spec.system_prompt},
+         {"role": "user", "content": user_message}],
+        model=spec.model, format="json",
+    )
+    if exchange is not None:
+        exchange.raw_output = raw
+    return llm_parse.extract_object(raw)
diff --git a/src/world_engine/tick.py b/src/world_engine/tick.py
index a770e5c..930a159 100644
--- a/src/world_engine/tick.py
+++ b/src/world_engine/tick.py
@@ -23,7 +23,7 @@ from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
 from .analyzer import load_analysis_prompt
-from .fact_refs import CodedFacts, knowledge_key
+from .fact_refs import CodedRefs, knowledge_key
 from .prose_render import fact_texts
 from .models import Agenda, Character, Entity, Fact, FactionMembership, Knowledge, ProposedMutation
 from .prompt_registry import effective_model
@@ -175,7 +175,7 @@ def _tick_npc_dedup_note(mutation_type: str, payload: dict, state: dict[str, Any
 
 
 def _tick_normalize_npc_items(
-    items: list, *, npc_id: str, world_id: str, roster: dict[str, str], fact_codes: CodedFacts,
+    items: list, *, npc_id: str, world_id: str, roster: dict[str, str], fact_codes: CodedRefs,
     secret_fact_ids: set[str], secret_texts: set[str],
     destinations: dict[str, str], from_location_id: str | None, from_name: str | None,
     agendas_index: dict[str, str], effects_roster: dict[str, str], db: Session,
diff --git a/src/world_engine/tick_context.py b/src/world_engine/tick_context.py
index 45cacd7..445f5c1 100644
--- a/src/world_engine/tick_context.py
+++ b/src/world_engine/tick_context.py
@@ -37,7 +37,7 @@ from .knowledge_resolve import (
     resolve_public_levels,
 )
 from .facet_reads import facts_of, joined, known_fact_texts
-from .fact_refs import CodedFacts, code_facts
+from .fact_refs import CodedRefs, code_facts
 from .prose_render import knowledge_texts
 from .ledger import get_balance
 from .models import (
@@ -273,7 +273,7 @@ def tick_knowledge_rows(npc_id: str, session: Session) -> list[Knowledge]:
     return knowledge + resolve_default_rows(session, npc_id, {k.fact_id for k in knowledge})
 
 
-def tick_fact_codes(npc_id: str, session: Session) -> CodedFacts:
+def tick_fact_codes(npc_id: str, session: Session) -> CodedRefs:
     """The briefing's fact codes (Z2): one per `tick_knowledge_rows` row."""
     return code_facts(session, [k.fact_id for k in tick_knowledge_rows(npc_id, session)])
 
diff --git a/src/world_engine/tick_normalize.py b/src/world_engine/tick_normalize.py
index fc79ca4..d95e106 100644
--- a/src/world_engine/tick_normalize.py
+++ b/src/world_engine/tick_normalize.py
@@ -24,7 +24,7 @@ from typing import Any
 from sqlmodel import Session, select
 
 from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP
-from .fact_refs import CodedFacts
+from .fact_refs import CodedRefs
 from .models import Agenda, AgendaStep, Character, Entity, Faction, Relation
 from .tick_context import _perceived_target
 
@@ -702,7 +702,7 @@ def _tick_normalize_npc_move(
 
 
 def _tick_normalize_new_knowledge(
-    payload_in: dict, *, npc_id: str, roster: dict[str, str], fact_codes: CodedFacts,
+    payload_in: dict, *, npc_id: str, roster: dict[str, str], fact_codes: CodedRefs,
     secret_fact_ids: set[str], secret_texts: set[str],
 ) -> tuple[dict, str] | None:
     """`source_fact` is the briefing code of what the NPC passes on (Z2,
@@ -750,7 +750,7 @@ def _normalize_tick_item(
     npc_id: str,
     world_id: str,
     roster: dict[str, str],
-    fact_codes: CodedFacts,
+    fact_codes: CodedRefs,
     secret_fact_ids: set[str], secret_texts: set[str],
     destinations: dict[str, str],
     from_location_id: str | None,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 6fa0e00..4930046 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18521,6 +18521,31 @@ the character may not have seen it; reactivation: the event journal of
 TICKET-0114 says who witnessed what -- « tue le loup géant » is tracked
 from then).
 
+## ONE CODED LIST, ONE TEMPLATED JSON CALL (TICKET-0112) -- `CodedRefs` NAMES ANY TARGET BY CODE, `prompt_call.call_json` SERVES THE AUTHORING TOOLS (BRIEF-0112-a, no schema change)
+
+**ID1a.** A model that must name a target from a closed set is shown a
+coded list and answers a code; code turns the code back into an id or
+refuses it. `fact_refs.CodedFacts` becomes `fact_refs.CodedRefs`, built by
+`code_refs(prefix, pairs)` for any `(id, label)` pairs; `code_facts` is its
+fact list (`f`), unchanged in behaviour. The condition interpreter adds
+quest offers (`q`) and skills (`s`). Entities stay named by name and
+resolved by `name_index` (creator regime).
+
+**Rejected.** ID1b (offers and skills in `name_index`): a name surface is
+an entity's, carrying an `entity_id` the tokenizer turns into an identity
+token and the day concordance matches a player's words against -- both
+would meet offers and skills. ID1c (a `quest_index` and a `skill_index`): a
+second structure for a job that is not name resolution -- the sets are
+small and shown whole. Reactivation of ID1b for offers: a quest offer
+becomes an entity.
+
+**One templated JSON call.** `lore_write_draft._call`'s body moves
+verbatim to `prompt_call.call_json(db, usage, values, exchanges, chat)`:
+load the prompt, fill its variables, record the exchange, call, parse one
+object. The client is a parameter, so a check that replaces a caller's
+`chat` still reaches the call. `lore_write_draft._world_facts` becomes the
+public `world_fact_ids`, for the interpreter's context.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
new file mode 100644
index 0000000..c4c50c4
--- /dev/null
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -0,0 +1,242 @@
+"""G1 check for TICKET-0112 -- the condition interpreter.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`conditions.py` precedent). Each brief adds its rules here in the same
+commit.
+
+NA1 -- one coded list (BRIEF-0112-A, ID1a; import, fixture). `fact_refs`
+   declares `CodedRefs` and `code_refs`; no module under `src/` declares or
+   names `CodedFacts`. `code_refs("q", ...)` codes pairs in order under its
+   prefix, keeps the first of a repeated id, skips an empty id; `resolve`
+   tolerates case, spaces and brackets and returns None for a code the list
+   did not show, a code of another prefix and a non-string; `code_of` is its
+   inverse. `code_facts` returns a `CodedRefs` whose lines read
+   `f<n> — <the fact's text>`, skipping a missing fact.
+NA2 -- one templated JSON call (BRIEF-0112-A; static, AST, and a stub).
+   `prompt_call.call_json` is declared in `prompt_call.py`, which imports
+   neither `ollama_client` nor anything under `cockpit`, and calls none of
+   `add`, `commit`, `delete`, `execute`, `flush`. `lore_write_draft._call`
+   is one `return` of `prompt_call.call_json(..., chat)` with this module's
+   `chat`; `lore_write_draft.py` calls `chat` nowhere else. With
+   `lore_write_draft.chat` stubbed, `draft_proposal` still reaches the stub
+   and records one exchange whose raw output is the stub's reply.
+   `lore_write_draft.world_fact_ids` is public and `_world_facts` gone.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import json
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+
+FAILURES: list[str] = []
+
+_WRITE_CALLS = {"add", "commit", "delete", "execute", "flush"}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+def _parse(path: pathlib.Path) -> ast.Module:
+    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
+
+
+def _callee(node: ast.Call) -> str:
+    func = node.func
+    if isinstance(func, ast.Name):
+        return func.id
+    if isinstance(func, ast.Attribute):
+        return func.attr
+    return ""
+
+
+def _imported(tree: ast.Module) -> set[str]:
+    names: set[str] = set()
+    for node in ast.walk(tree):
+        if isinstance(node, ast.ImportFrom):
+            names.add(node.module or "")
+            names.update(alias.name for alias in node.names)
+        elif isinstance(node, ast.Import):
+            names.update(alias.name for alias in node.names)
+    return names
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
+        return reply if isinstance(reply, str) else json.dumps(reply)
+
+
+# --- NA1 -----------------------------------------------------------------------
+
+def _na1_static() -> None:
+    declared = {node.name for node in _parse(SRC / "fact_refs.py").body
+                if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
+    for name in ("CodedRefs", "code_refs", "code_facts"):
+        if name not in declared:
+            fail(f"NA1: fact_refs.py does not declare {name}")
+    scanned = 0
+    for path in sorted(SRC.rglob("*.py")):
+        if "__pycache__" in path.parts:
+            continue
+        scanned += 1
+        if "CodedFacts" in path.read_text(encoding="utf-8"):
+            fail(f"NA1: {path.relative_to(ROOT).as_posix()} still names CodedFacts")
+    if scanned == 0:
+        fail("NA1: scanned zero modules under src/")
+
+
+def _na1_lists() -> None:
+    from world_engine.fact_refs import CodedRefs, code_refs
+
+    coded = code_refs("q", [("o-1", "La fourrure"), ("", "vide"), ("o-2", "Le pont"), ("o-1", "doublon")])
+    if not isinstance(coded, CodedRefs) or coded.lines != ("q1 — La fourrure", "q2 — Le pont"):
+        fail(f"NA1: code_refs lines read {getattr(coded, 'lines', coded)!r}")
+    cases = {"q1": "o-1", " Q2 ": "o-2", "[q2]": "o-2", "q3": None, "f1": None, None: None, 2: None}
+    for code, expected in cases.items():
+        if coded.resolve(code) != expected:
+            fail(f"NA1: resolve({code!r}) gave {coded.resolve(code)!r}, expected {expected!r}")
+    if coded.code_of("o-2") != "q2" or coded.code_of("o-9") is not None:
+        fail("NA1: code_of is not resolve's inverse")
+
+
+def _na1_facts(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.fact_refs import CodedRefs, code_facts
+    from world_engine.models import World
+    from world_engine.writes.facts import create_fact
+
+    with Session(engine) as session:
+        world = World(name="Interprète NA1", is_active=False)
+        session.add(world)
+        session.flush()
+        one = create_fact(session, world_id=world.id, content="Le pont est fragile", created_by="check",
+                          facet="information")
+        two = create_fact(session, world_id=world.id, content="La rivière monte", created_by="check",
+                          facet="information")
+        session.commit()
+        coded = code_facts(session, [two.id, "no-such-fact", one.id, two.id])
+        if not isinstance(coded, CodedRefs) or coded.lines != ("f1 — La rivière monte", "f2 — Le pont est fragile") \
+                or coded.resolve("f2") != one.id:
+            fail(f"NA1: code_facts reads {coded!r}")
+
+
+def check_na1(engine) -> None:
+    _na1_static()
+    _na1_lists()
+    _na1_facts(engine)
+
+
+# --- NA2 -----------------------------------------------------------------------
+
+def _na2_static() -> None:
+    call_file = SRC / "prompt_call.py"
+    if not call_file.exists():
+        fail("NA2: prompt_call.py is missing")
+        return
+    tree = _parse(call_file)
+    if not any(isinstance(n, ast.FunctionDef) and n.name == "call_json" for n in tree.body):
+        fail("NA2: prompt_call.py does not declare call_json")
+    bad = {m for m in _imported(tree) if "ollama_client" in m or "cockpit" in m}
+    if bad:
+        fail(f"NA2: prompt_call.py imports {sorted(bad)}")
+    writes = {_callee(n) for n in ast.walk(tree) if isinstance(n, ast.Call)} & _WRITE_CALLS
+    if writes:
+        fail(f"NA2: prompt_call.py calls {sorted(writes)}")
+    draft = _parse(SRC / "lore_write_draft.py")
+    call = next((n for n in draft.body if isinstance(n, ast.FunctionDef) and n.name == "_call"), None)
+    body = [n for n in call.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))] if call else []
+    ok = (len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call)
+          and _callee(body[0].value) == "call_json"
+          and isinstance(body[0].value.args[-1], ast.Name) and body[0].value.args[-1].id == "chat")
+    if not ok:
+        fail("NA2: lore_write_draft._call is not one return of prompt_call.call_json(..., chat)")
+    chats = [n for n in ast.walk(draft) if isinstance(n, ast.Call) and _callee(n) == "chat"]
+    if chats:
+        fail(f"NA2: lore_write_draft.py still calls chat( at line(s) {[n.lineno for n in chats]}")
+    names = {n.name for n in draft.body if isinstance(n, ast.FunctionDef)}
+    if "world_fact_ids" not in names or "_world_facts" in names:
+        fail("NA2: lore_write_draft.world_fact_ids is not the public name of the world facts")
+
+
+def _seed_lore_prompts(session) -> None:
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+    from world_engine.models import PromptTemplate
+
+    for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
+        if session.get(PromptTemplate, head["id"]) is None:
+            seed_pilot.upsert_prompt_template(session, **dict(head))
+    session.commit()
+
+
+def _na2_stub(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine import lore_write_draft as lwd
+    from world_engine.models import World
+
+    with Session(engine) as session:
+        _seed_lore_prompts(session)
+        world = World(name="Interprète NA2", is_active=False)
+        session.add(world)
+        session.commit()
+        reply = json.dumps({"entities": [], "facts": []})
+        stub, original = _Stub([reply]), lwd.chat
+        lwd.chat = stub
+        try:
+            exchanges: list = []
+            lwd.draft_proposal(session, world.id, "La rivière monte.", exchanges=exchanges)
+        finally:
+            lwd.chat = original
+        if len(stub.messages) != 1 or len(exchanges) != 1 or exchanges[0].raw_output != reply \
+                or exchanges[0].usage != lwd.PROPOSAL_USAGE:
+            fail(f"NA2: the stubbed draft reached chat {len(stub.messages)} time(s), {len(exchanges)} exchange(s)")
+
+
+def check_na2(engine) -> None:
+    _na2_static()
+    _na2_stub(engine)
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_na1(engine)
+    check_na2(engine)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; "
+          "one templated JSON call serves the creator's authoring tools")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 8d7c995..8400fd9 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -47,7 +47,7 @@ K4 -- the mutation pipeline keys knowledge by fact (C-01, C-02):
    g. window normalization drops a model-emitted `knowledge_change` (N1)
       and strips `subject` / `fact_id` from a model `new_knowledge`.
 K5 -- models name facts by code (C-03, C-04, C-05):
-   a. `code_facts` / `CodedFacts` on the `_CODE_CASES` table;
+   a. `code_facts` / `CodedRefs` on the `_CODE_CASES` table;
    b. overhearing (L1): the classifier's list shows the speaker's
       non-secret fact and never the text of its secret one; the code the
       model answers resolves to that fact -- an unaware bystander gets a
````

2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit as one commit: `BRIEF-0112-A: one coded list, one templated JSON call`.

## Scope OUT

- Any change to what a model sees or emits anywhere: the codes and lines `code_facts` produces are byte for byte the same.
- Moving `lore_plan.py` / `lore_render.py`'s own model calls onto `call_json` (the consultation pipeline is untouched; REPORT if tempting).
- Offers or skills in `name_index` (ID1b, rejected) or a `quest_index` / `skill_index` (ID1c, rejected).
- A `CodedFacts` alias kept for compatibility: the name goes (NA1).
- The interpreter, its journal, its routes, its editor (BRIEF-0112-B to E).

## Invariants to defend

**A model never emits an id** (CLAUDE.md, the code-list invariant): `code_refs` keeps `resolve` returning None for any code the list did not show (NA1). **The consultation pipeline stays pure** -- `prompt_call.py` is neither a pipeline nor a panel file, holds no `select(` and imports no client (`lore_isolation.py` R15, R17; NA2). **Behaviour is constant** -- `lore_write.py`, `lore_usage.py`, `knowledge_identity.py`, `day_plan.py` stay green with their stubs on `lore_write_draft.chat`. No player surface is touched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `lore_write.py` or `lore_usage.py` turns red: a stub no longer reaches the call.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- An importer of `CodedFacts` outside the six of R-01 appears (a file landed since): rename it the same way, in this commit, and report it.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- `prompt_registry.py` still names `lore_write_draft.py:_call` -- correct, it is the call site.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/condition_interpreter.py` -> `PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; one templated JSON call serves the creator's authoring tools`
- `lore_write.py`, `lore_usage.py`, `lore_isolation.py`, `knowledge_identity.py`, `day_plan.py`, `prompt_registry.py`, `name_index.py`, `claude_md_contract.py`, `module_budget.py`, `function_length.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`condition_interpreter.py` exits 1 with the rule named):
  - in `src/world_engine/fact_refs.py`, `        if not target_id or target_id in codes.values():` -> `        if not target_id:` -> `NA1`
  - in `src/world_engine/prompt_call.py`, `        exchange.raw_output = raw` -> `        exchange.raw_output = None` -> `NA2`
  - in `src/world_engine/lore_write_draft.py`, `    return prompt_call.call_json(db, usage, values, exchanges, chat)` -> `    return prompt_call.call_json(db, usage, values, exchanges, prompt_call.prompt_load and chat)` -> `NA2`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 145/145.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry « ONE CODED LIST, ONE TEMPLATED JSON CALL (TICKET-0112) -- `CodedRefs` NAMES ANY TARGET BY CODE, `prompt_call.call_json` SERVES THE AUTHORING TOOLS (BRIEF-0112-a, no schema change) » -- in the diff. `CLAUDE.md` line 473 -- in the diff. No schema change.
