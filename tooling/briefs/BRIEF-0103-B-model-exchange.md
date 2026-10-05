<!-- slug: model-exchange -->
# BRIEF 0103-B — "Capture every Lore model call: prompt version and raw reply"

Lot: LOT-0103-lore-usage-journal.md (authoritative on conflict)
Depends on: BRIEF-0103-A (`MODEL_CALL_KEYS`, `write_usage_event`, `lore_usage.py`)
Commit header for decisions: `(BRIEF-0103-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0103`, on the tree BRIEF-0103-A left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/prompt_load.py:35` → `class RenderSpec:`; `:38` → `    model: str` (third and last field); `:61` → `    version = current_prompt(db, template)`; `:62` → `    return RenderSpec(`.
- `src/world_engine/lore_plan.py:14` → `from . import llm_parse, lore_prompt`; `:79` → `def draft_plan(question: str, world_id: str, db: Session) -> LorePlan:`; `:93` → `    raw = chat(`; `:101` → `    parsed = llm_parse.extract_object(raw)`.
- `src/world_engine/lore_render.py:13` → `from typing import Callable`; `:15` → `from .lore_prompt import RenderSpec`; `:249` → `def _call_model(result: LoreResult, question: str, spec: RenderSpec) -> str:`; `:265` → `def render(`; `:282` → `    except OllamaError:`.
- `src/world_engine/lore_write_draft.py:28` → `from . import llm_parse, prompt_load`; `:112` → `def _call(db: Session, usage: str, values: dict[str, str]) -> dict:`; `:135` → `def draft_questions(db: Session, world_id: str, statement: str) -> list[str]:`; `:238` → `def draft_proposal(db: Session, world_id: str, statement: str, answers: str = "") -> dict:`.
- `tooling/verify/checks/lore_write.py:489-490` and `:550-551` → the checks swap `lwd.chat` for a stub (the `chat` call in `lore_write_draft.py` must stay a module-level name).
- `grep -rn "RenderSpec(" src tooling/verify scripts` → one hit, `src/world_engine/prompt_load.py:62`.
- `tooling/verify/checks/lore_usage.py` exists and passes (U0-U4).

## Facts carried

### R-04 — the prompt version is read, then dropped [M]
Opened: `src/world_engine/prompt_load.py:35-38` (`RenderSpec`: three
strings), `:61-66`; `src/world_engine/prompt_store.py:19`
(`current_prompt` returns the `PromptVersion` row); `models/pipeline.py`
`PromptVersion` (`id`, `version_number`).
Finding: `load` has the version row in hand and returns only its text and
the model. One constructor of `RenderSpec` exists (enumeration E2).
Consequence: `RenderSpec` gains `version_id` and `version_number`, required
(B); no other constructor to adapt.

### R-05 — the Lore shell's model calls [M]
Opened: enumeration E1; `src/world_engine/lore_plan.py:79-111`,
`lore_render.py:249-284`, `lore_write_draft.py:112-122, 135-140, 238-266`.
Finding: three `chat(` sites serve four usages: `lore_question_to_plan`
(`draft_plan`), `lore_rows_to_prose` (`_call_model`, `answered` verdict
only), `lore_statement_questions` and `lore_statement_to_proposal` (one
`_call`). The raw reply goes straight to `llm_parse.extract_object`; a parse
failure loses it.
Consequence: each site records its exchange before parsing (B). Callers of
these four functions: enumeration E9 (two routes, one check).

### R-06 — the renderer is Session-free; the panel and the pipeline do not import each other [M]
Opened: `tooling/verify/checks/lore_isolation.py:44-46` (R10, implementation
`check_render_isolation` 537-566: no `Session` name, no `select(`, no
`db.add(`/`.commit(`), `:59-66` and `:91-104` (R17, `PANEL_FILES`,
`PIPELINE_FILES`, implementation 706-746).
Finding: `lore_render.py` may import plain modules; R17 forbids imports
between the panel modules and `lore_selectors, lore_query, lore_plan,
lore_render, lore_prompt`, both ways.
Consequence: the capture lives in a neutral module (`model_exchange.py`,
the `prompt_load.py` precedent), holding plain strings only; U5 forbids it
any `world_engine` import.

## Contracts

### C-02 — the journal's two key families (the model-call half)
Produced by: BRIEF-0103-A   Consumed by: this brief (U5)
`MODEL_CALL_KEYS = {usage, prompt_version_id, prompt_version_number, model,
system_prompt, user_message, raw_output, error}`.

### C-03 — `model_exchange` and the capturing call sites
Produced by: BRIEF-0103-B   Consumed by: BRIEF-0103-C
`ModelExchange` dataclass, fields exactly `MODEL_CALL_KEYS` (U5);
`to_record() -> dict`. `begin(exchanges, usage, spec, system_prompt,
user_message) -> Optional[ModelExchange]` appends and returns a new
exchange (None when `exchanges` is None); `fail(exchanges, exc)` sets
`"<Type>: <message>"` on the last exchange without an error.
`RenderSpec(system_prompt, user_template, model, version_id: str,
version_number: int)`.
Call-site family (written before any member, re-read after the fourth):
- `lore_plan.draft_plan(question, world_id, db, exchanges=None)`, usage
  `PLAN_USAGE = "lore_question_to_plan"`
- `lore_render.render(result, question, spec, candidates, exchanges=None)`,
  usage `PROSE_USAGE = "lore_rows_to_prose"`, `answered` only; an
  `OllamaError` is recorded by `fail` before the template fallback
- `lore_write_draft.draft_questions(db, world_id, statement,
  exchanges=None)`, usage `QUESTIONS_USAGE`
- `lore_write_draft.draft_proposal(db, world_id, statement, answers="",
  exchanges=None)`, usage `PROPOSAL_USAGE`
Each assigns `raw_output` as soon as `chat` returns, before parsing.
Without a list each behaves exactly as before.

## Context

The journal must keep each model exchange as it happened (B1), including replies that fail to parse (C1). The four Lore model calls learn to report themselves to a list their caller hands in; nobody hands one in yet — the routes do in C. Without a list, every call behaves exactly as before.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`)
are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `model_exchange.py` (C-03: `ModelExchange`, `begin`, `fail`; no `world_engine` import); adds `version_id` and `version_number` to `prompt_load.RenderSpec`, filled from the `PromptVersion` row `load` already reads; gives `lore_plan.draft_plan`, `lore_render.render` (through `_call_model`) and `lore_write_draft.draft_questions` / `draft_proposal` (through `_call`) an optional `exchanges` list, with `PLAN_USAGE` and `PROSE_USAGE` named constants; `render` records an `OllamaError` with `model_exchange.fail` before falling back to the template; extends `lore_usage.py` with U5-U6; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): capture each Lore model exchange with its prompt version and raw reply (BRIEF-0103-b)`.

````diff
diff --git a/src/world_engine/lore_plan.py b/src/world_engine/lore_plan.py
index 4cda0cb..3a3b867 100644
--- a/src/world_engine/lore_plan.py
+++ b/src/world_engine/lore_plan.py
@@ -9,9 +9,11 @@ is not in `SELECTORS` is a rejected plan, not an improvised query.
 
 from __future__ import annotations
 
+from typing import Optional
+
 from sqlmodel import Session
 
-from . import llm_parse, lore_prompt
+from . import llm_parse, lore_prompt, model_exchange
 from .lore_query import LorePlan, PlanCall, PlanMention
 from .ollama_client import chat
 
@@ -76,20 +78,31 @@ def _coerce_call(raw: object) -> PlanCall:
     return PlanCall(selector=selector, args=tuple(args))
 
 
-def draft_plan(question: str, world_id: str, db: Session) -> LorePlan:
+PLAN_USAGE = "lore_question_to_plan"
+
+
+def draft_plan(
+    question: str, world_id: str, db: Session,
+    exchanges: Optional[list[model_exchange.ModelExchange]] = None,
+) -> LorePlan:
     """Builds the prompt, calls the model through the resolved
     `lore_prompt.RenderSpec`, parses the reply with `llm_parse.extract_object`,
     and maps the JSON into a `LorePlan`. `LlmParseError` propagates -- a
     malformed reply, a missing template, or an out-of-vocabulary mention
     category is a failed draft, never silently coerced into an empty plan.
     `validate_plan` (lore_query.py) still runs afterward against the selector
-    whitelist; this function only guards the shape it itself constructs."""
-    spec = lore_prompt.load(db, "lore_question_to_plan")
+    whitelist; this function only guards the shape it itself constructs.
+
+    `exchanges` (TICKET-0103, BRIEF-0103-B, C-03): when a list is given, the
+    model call is appended to it as a `ModelExchange`, its raw reply kept
+    before parsing."""
+    spec = lore_prompt.load(db, PLAN_USAGE)
     user_message = (
         spec.user_template
         .replace("{selectors}", _render_selectors())
         .replace("{question}", question)
     )
+    exchange = model_exchange.begin(exchanges, PLAN_USAGE, spec, spec.system_prompt, user_message)
     raw = chat(
         [
             {"role": "system", "content": spec.system_prompt},
@@ -98,6 +111,8 @@ def draft_plan(question: str, world_id: str, db: Session) -> LorePlan:
         model=spec.model,
         format="json",
     )
+    if exchange is not None:
+        exchange.raw_output = raw
     parsed = llm_parse.extract_object(raw)
 
     raw_mentions = parsed.get("mentions")
diff --git a/src/world_engine/lore_render.py b/src/world_engine/lore_render.py
index 92fe5e4..a18a7b8 100644
--- a/src/world_engine/lore_render.py
+++ b/src/world_engine/lore_render.py
@@ -10,8 +10,9 @@ an absence will fill it.
 from __future__ import annotations
 
 from dataclasses import dataclass
-from typing import Callable
+from typing import Callable, Optional
 
+from . import model_exchange
 from .lore_prompt import RenderSpec
 from .lore_query import LoreResult
 from .ollama_client import OllamaError, chat
@@ -246,12 +247,19 @@ def _render_deterministic(result: LoreResult, candidates: dict[str, list[dict]])
     return RenderedAnswer(prose=prose, renderer="deterministic", trace=result.trace)
 
 
-def _call_model(result: LoreResult, question: str, spec: RenderSpec) -> str:
+PROSE_USAGE = "lore_rows_to_prose"
+
+
+def _call_model(
+    result: LoreResult, question: str, spec: RenderSpec,
+    exchanges: Optional[list[model_exchange.ModelExchange]],
+) -> str:
     user_message = (
         spec.user_template
         .replace("{question}", question)
         .replace("{rows}", _serialize_rows_by_section(result.rows))
     )
+    exchange = model_exchange.begin(exchanges, PROSE_USAGE, spec, spec.system_prompt, user_message)
     raw = chat(
         [
             {"role": "system", "content": spec.system_prompt},
@@ -259,11 +267,14 @@ def _call_model(result: LoreResult, question: str, spec: RenderSpec) -> str:
         ],
         model=spec.model,
     )
+    if exchange is not None:
+        exchange.raw_output = raw
     return raw.strip()
 
 
 def render(
-    result: LoreResult, question: str, spec: RenderSpec, candidates: dict[str, list[dict]]
+    result: LoreResult, question: str, spec: RenderSpec, candidates: dict[str, list[dict]],
+    exchanges: Optional[list[model_exchange.ModelExchange]] = None,
 ) -> RenderedAnswer:
     """No `Session` parameter -- the structural guarantee, not a convention
     (R10). `candidates` is `{}` on every verdict other than
@@ -274,11 +285,16 @@ def render(
     call is possible (R11) -- an empty retrieval can never be filled in by
     the model. One `chat` attempt on the `answered` path; `OllamaError` falls
     through to `render_template` (R12); `LlmParseError` is never caught here
-    -- the renderer returns prose, not JSON."""
+    -- the renderer returns prose, not JSON.
+
+    `exchanges` (TICKET-0103, BRIEF-0103-B, C-03): when a list is given, the
+    model call is appended to it, and an `OllamaError` is recorded on it
+    before the template fallback."""
     if result.verdict != "answered":
         return _render_deterministic(result, candidates)
     try:
-        prose = _call_model(result, question, spec)
-    except OllamaError:
+        prose = _call_model(result, question, spec, exchanges)
+    except OllamaError as exc:
+        model_exchange.fail(exchanges, exc)
         return render_template(result)
     return RenderedAnswer(prose=prose, renderer="model", trace=result.trace)
diff --git a/src/world_engine/lore_write_draft.py b/src/world_engine/lore_write_draft.py
index 060ea1c..e6f207e 100644
--- a/src/world_engine/lore_write_draft.py
+++ b/src/world_engine/lore_write_draft.py
@@ -25,7 +25,7 @@ from typing import Any, Optional
 
 from sqlmodel import Session, select
 
-from . import llm_parse, prompt_load
+from . import llm_parse, model_exchange, prompt_load
 from .facet_reads import creator_only_fact_ids
 from .facets import FACETS
 from .fact_refs import CodedFacts, code_facts
@@ -109,16 +109,25 @@ def _facet_lines() -> str:
     )
 
 
-def _call(db: Session, usage: str, values: dict[str, str]) -> dict:
+Exchanges = Optional[list[model_exchange.ModelExchange]]
+
+
+def _call(db: Session, usage: str, values: dict[str, str], exchanges: Exchanges) -> dict:
+    """One model call. When `exchanges` is a list (TICKET-0103, BRIEF-0103-B,
+    C-03), the call is appended to it as a `ModelExchange`, its raw reply
+    kept before parsing, so a reply that does not parse is still recorded."""
     spec = prompt_load.load(db, usage)
     user_message = spec.user_template
     for key, value in values.items():
         user_message = user_message.replace("{" + key + "}", value)
+    exchange = model_exchange.begin(exchanges, usage, spec, spec.system_prompt, user_message)
     raw = chat(
         [{"role": "system", "content": spec.system_prompt},
          {"role": "user", "content": user_message}],
         model=spec.model, format="json",
     )
+    if exchange is not None:
+        exchange.raw_output = raw
     return llm_parse.extract_object(raw)
 
 
@@ -132,10 +141,14 @@ def _values(context: DraftContext, statement: str, answers: str = "") -> dict[st
     }
 
 
-def draft_questions(db: Session, world_id: str, statement: str) -> list[str]:
+def draft_questions(
+    db: Session, world_id: str, statement: str, exchanges: Exchanges = None,
+) -> list[str]:
     """At most `MAX_QUESTIONS` non-empty questions, in the model's order.
-    `OllamaError` and `LlmParseError` propagate."""
-    parsed = _call(db, QUESTIONS_USAGE, _values(draft_context(db, world_id, statement), statement))
+    `OllamaError` and `LlmParseError` propagate. `exchanges`: see `_call`
+    (TICKET-0103, C-03)."""
+    parsed = _call(db, QUESTIONS_USAGE, _values(draft_context(db, world_id, statement), statement),
+                   exchanges)
     questions = [q.strip() for q in _as_list(parsed.get("questions"))
                  if isinstance(q, str) and q.strip()]
     return questions[:MAX_QUESTIONS]
@@ -235,14 +248,16 @@ def _pairs(raw: Any, keys: tuple[str, str], known: set[str]) -> list[dict]:
     return out
 
 
-def draft_proposal(db: Session, world_id: str, statement: str, answers: str = "") -> dict:
+def draft_proposal(
+    db: Session, world_id: str, statement: str, answers: str = "", exchanges: Exchanges = None,
+) -> dict:
     """The draft the writing panel edits (C-05), with the facet vocabulary the
     panel offers (names and French labels, from `FACETS`). Every entity carries a
     `status` (`matched` / `ambiguous` / `new`); every fact code is resolved to
     an id or dropped with a note. `OllamaError` and `LlmParseError`
-    propagate."""
+    propagate. `exchanges`: see `_call` (TICKET-0103, C-03)."""
     context = draft_context(db, world_id, statement)
-    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers))
+    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers), exchanges)
     notes: list[str] = []
     entities = [e for e in (_entity(db, world_id, raw, notes)
                             for raw in _as_list(parsed.get("entities"))) if e is not None]
diff --git a/src/world_engine/model_exchange.py b/src/world_engine/model_exchange.py
new file mode 100644
index 0000000..c163f5e
--- /dev/null
+++ b/src/world_engine/model_exchange.py
@@ -0,0 +1,64 @@
+"""One model exchange, captured as it happened (TICKET-0103, BRIEF-0103-B,
+decisions B1 + C1, C-03).
+
+A neutral module, like `prompt_load.py`: the consultation pipeline
+(`lore_plan.py`, `lore_render.py`) and the writing panel
+(`lore_write_draft.py`) both import it, and it imports neither -- nor any
+`Session`, model, writer or client. It holds plain strings only, so the
+Session-free renderer can fill one (`lore_isolation.py` R10).
+
+A call site that talks to the model appends one `ModelExchange` per `chat`
+call to the list its caller handed in: `begin` before the call records the
+prompt version, the model and the rendered messages; the raw reply is
+assigned as soon as `chat` returns, before any parsing, so a reply that
+fails to parse is still kept; `fail` records the error of whoever caught it.
+`to_record` is the journal's model-call shape (`writes/lore_usage.py`
+`MODEL_CALL_KEYS`, kept equal by `lore_usage.py` U5).
+"""
+
+from __future__ import annotations
+
+from dataclasses import asdict, dataclass
+from typing import Optional
+
+
+@dataclass
+class ModelExchange:
+    usage: str
+    prompt_version_id: Optional[str] = None
+    prompt_version_number: Optional[int] = None
+    model: Optional[str] = None
+    system_prompt: Optional[str] = None
+    user_message: Optional[str] = None
+    raw_output: Optional[str] = None
+    error: Optional[str] = None
+
+    def to_record(self) -> dict:
+        return asdict(self)
+
+
+def begin(
+    exchanges: Optional[list[ModelExchange]], usage: str, spec, system_prompt: str, user_message: str,
+) -> Optional[ModelExchange]:
+    """Append and return a new exchange carrying `spec`'s prompt version and
+    model and the rendered messages; `None` when the caller keeps no list.
+    `spec` is a `prompt_load.RenderSpec` (duck-typed: this module imports
+    nothing)."""
+    if exchanges is None:
+        return None
+    exchange = ModelExchange(
+        usage=usage, prompt_version_id=spec.version_id,
+        prompt_version_number=spec.version_number, model=spec.model,
+        system_prompt=system_prompt, user_message=user_message,
+    )
+    exchanges.append(exchange)
+    return exchange
+
+
+def fail(exchanges: Optional[list[ModelExchange]], exc: BaseException) -> None:
+    """Record `exc` on the last exchange of `exchanges` that has no error
+    yet -- the one the exception interrupted. No-op on an empty list."""
+    for exchange in reversed(exchanges or []):
+        if exchange.error is None:
+            exchange.error = f"{type(exc).__name__}: {exc}"
+            return
diff --git a/src/world_engine/prompt_load.py b/src/world_engine/prompt_load.py
index e7ad465..192f7bb 100644
--- a/src/world_engine/prompt_load.py
+++ b/src/world_engine/prompt_load.py
@@ -36,6 +36,10 @@ class RenderSpec:
     system_prompt: str
     user_template: str
     model: str
+    # The `prompt_version` the text came from (TICKET-0103, BRIEF-0103-B, B1):
+    # plain values, so a usage journal can name the version without a row.
+    version_id: str
+    version_number: int
 
 
 def _author_model() -> str:
@@ -63,4 +67,6 @@ def load(db: Session, usage: str) -> RenderSpec:
         system_prompt=version.system_prompt,
         user_template=version.user_template,
         model=effective_model(template, _author_model()),
+        version_id=version.id,
+        version_number=version.version_number,
     )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 00a7837..8b7710f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17633,6 +17633,20 @@ the analysis material. I2, a `world_id` column exempted by name in W1:
 reactivates when a second table must outlive its world AND be read by the
 application itself.
 
+
+## EVERY LORE MODEL CALL CAN BE CAPTURED (TICKET-0103) -- PROMPT VERSION AND RAW REPLY (BRIEF-0103-b, no schema change)
+
+**B1, C1.** `model_exchange.py` is a neutral module (the `prompt_load.py`
+precedent): `lore_plan.draft_plan`, `lore_render.render` and
+`lore_write_draft.draft_questions` / `draft_proposal` take an optional list
+and append one `ModelExchange` per `chat` call -- usage, prompt version id
+and number, model, rendered system prompt and user message, raw reply,
+error. The raw reply is kept before parsing, so a reply that fails to parse
+is still recorded; the renderer records an `OllamaError` before its template
+fallback. `prompt_load.RenderSpec` gains `version_id` and `version_number`,
+plain values, so the Session-free renderer names the version without a row.
+Without a list every call behaves as before.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_usage.py b/tooling/verify/checks/lore_usage.py
index 3a11a1f..34890d7 100644
--- a/tooling/verify/checks/lore_usage.py
+++ b/tooling/verify/checks/lore_usage.py
@@ -30,6 +30,23 @@ U3 -- writer (C-01, C-02). `_good()` is inserted once; every row of
 U4 -- the journal outlives its world (F2). A world tagged by a journal row
    is deleted by `delete_world_cascade`; the journal row is still there,
    with its `world_ref` and `world_name` unchanged.
+U5 -- the capture shape (BRIEF-0103-B, C-03). The fields of
+   `model_exchange.ModelExchange` equal `writes/lore_usage.MODEL_CALL_KEYS`;
+   `model_exchange.py` imports nothing from `world_engine`; `prompt_load.load`
+   returns the `id` and `version_number` of the head's current
+   `prompt_version`.
+U6 -- capture (C-03), `chat` stubbed in each module, on seeded prompt heads:
+   a. `lore_plan.draft_plan` given a list appends one exchange: usage
+      `PLAN_USAGE`, the head's current version id and number, the rendered
+      user message, the raw reply; an unparsable reply raises `LlmParseError`
+      and the exchange still holds that raw reply;
+   b. `lore_render.render` appends one exchange on `answered` (usage
+      `PROSE_USAGE`) and none on any other verdict; an `OllamaError` falls
+      back to the template and leaves the exchange with no raw reply and the
+      error recorded;
+   c. `lore_write_draft.draft_questions` and `draft_proposal` each append one
+      exchange, usage `QUESTIONS_USAGE` and `PROPOSAL_USAGE`;
+   d. every exchange's `to_record()` is accepted by `write_usage_event`.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -305,6 +322,182 @@ def check_u4() -> None:
             fail("U4: the journal row did not outlive its world")
 
 
+def check_u5() -> None:
+    import ast
+    import dataclasses
+
+    from sqlmodel import Session
+
+    from world_engine import model_exchange, prompt_load
+    from world_engine.db import engine
+    from world_engine.models import PromptTemplate
+    from world_engine.prompt_store import current_prompt
+    from world_engine.writes.lore_usage import MODEL_CALL_KEYS
+
+    fields = {f.name for f in dataclasses.fields(model_exchange.ModelExchange)}
+    if not fields or fields != MODEL_CALL_KEYS:
+        fail(f"U5: ModelExchange fields {sorted(fields)} != MODEL_CALL_KEYS {sorted(MODEL_CALL_KEYS)}")
+    tree = ast.parse((SRC / "model_exchange.py").read_text(encoding="utf-8"))
+    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
+               and (n.level > 0 or (n.module or "").startswith("world_engine"))]
+    if imports:
+        fail(f"U5: model_exchange.py imports from world_engine at line(s) {[n.lineno for n in imports]}")
+    with Session(engine) as db:
+        _seed_prompts(db)
+        spec = prompt_load.load(db, "lore_question_to_plan")
+        template = db.get(PromptTemplate, "pt-lore-question-to-plan")
+        version = current_prompt(db, template)
+        if (spec.version_id, spec.version_number) != (version.id, version.version_number):
+            fail("U5: RenderSpec does not carry the head's current prompt_version")
+
+
+def _seed_prompts(db) -> None:
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+
+    from world_engine.models import PromptTemplate
+
+    heads = [
+        dict(id="pt-lore-question-to-plan", world_id=None, name="plan", usage="lore_question_to_plan",
+             system_prompt=seed_pilot.LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT,
+             user_template=seed_pilot.LORE_QUESTION_TO_PLAN_USER_TEMPLATE,
+             variables=["selectors", "question"], destination="local"),
+        dict(id="pt-lore-rows-to-prose", world_id=None, name="prose", usage="lore_rows_to_prose",
+             system_prompt=seed_pilot.LORE_ROWS_TO_PROSE_SYSTEM_PROMPT,
+             user_template=seed_pilot.LORE_ROWS_TO_PROSE_USER_TEMPLATE,
+             variables=["question", "rows"], destination="local"),
+        *seed_pilot.LORE_WRITE_PROMPT_HEADS,
+    ]
+    for head in heads:
+        if db.get(PromptTemplate, head["id"]) is None:
+            seed_pilot.upsert_prompt_template(db, **dict(head))
+    db.commit()
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
+        return reply if isinstance(reply, str) else __import__("json").dumps(reply)
+
+
+def _swap(module, stub):
+    original = module.chat
+    module.chat = stub
+    return original
+
+
+def _check_exchange(label: str, exchange, usage: str, spec, raw) -> None:
+    if (exchange.usage, exchange.prompt_version_id, exchange.prompt_version_number,
+            exchange.model, exchange.raw_output) != (usage, spec.version_id, spec.version_number,
+                                                     spec.model, raw):
+        fail(f"{label}: exchange {exchange.to_record()!r}"[:300])
+
+
+def check_u6() -> None:
+    from sqlmodel import Session
+
+    from world_engine import lore_plan, lore_render, lore_write_draft as lwd, prompt_load
+    from world_engine.db import engine
+    from world_engine.llm_parse import LlmParseError
+    from world_engine.lore_query import LoreResult
+    from world_engine.models import World
+    from world_engine.ollama_client import OllamaError
+    from world_engine.writes.lore_usage import write_usage_event
+
+    collected = []
+    with Session(engine) as db:
+        _seed_prompts(db)
+        world = World(name="Capture 0103")
+        db.add(world)
+        db.commit()
+        plan_spec = prompt_load.load(db, lore_plan.PLAN_USAGE)
+        prose_spec = prompt_load.load(db, lore_render.PROSE_USAGE)
+        reply = '{"mentions": [], "calls": [{"selector": "world_factions", "args": ["$world"]}]}'
+        original = _swap(lore_plan, _Stub([reply, "pas du json"]))
+        try:
+            exchanges = []
+            lore_plan.draft_plan("Quelles factions ?", world.id, db, exchanges)
+            if len(exchanges) != 1:
+                fail(f"U6a: draft_plan appended {len(exchanges)} exchange(s)")
+            else:
+                _check_exchange("U6a", exchanges[0], lore_plan.PLAN_USAGE, plan_spec, reply)
+                if "Quelles factions ?" not in (exchanges[0].user_message or ""):
+                    fail("U6a: the rendered user message was not kept")
+            collected += exchanges
+            exchanges = []
+            try:
+                lore_plan.draft_plan("Encore ?", world.id, db, exchanges)
+                fail("U6a: an unparsable plan did not raise")
+            except LlmParseError:
+                pass
+            if len(exchanges) != 1 or exchanges[0].raw_output != "pas du json":
+                fail("U6a: the unparsable reply was not kept")
+        finally:
+            lore_plan.chat = original
+        answered = LoreResult(verdict="answered", rows=({"section": "factions", "name": "Guilde",
+                                                         "faction_type": "guilde"},),
+                              trace=[], ambiguous_mentions=(), unmatched_surface_forms=(),
+                              rejection_reason=None)
+        silent = LoreResult(verdict="silent_canon", rows=(), trace=[], ambiguous_mentions=(),
+                            unmatched_surface_forms=(), rejection_reason=None)
+        original = _swap(lore_render, _Stub(["Une guilde.", OllamaError("down")]))
+        try:
+            exchanges = []
+            lore_render.render(answered, "Quelles factions ?", prose_spec, {}, exchanges)
+            if len(exchanges) != 1:
+                fail(f"U6b: render appended {len(exchanges)} exchange(s) on answered")
+            else:
+                _check_exchange("U6b", exchanges[0], lore_render.PROSE_USAGE, prose_spec, "Une guilde.")
+            collected += exchanges
+            exchanges = []
+            lore_render.render(silent, "Quoi ?", prose_spec, {}, exchanges)
+            if exchanges:
+                fail("U6b: render appended an exchange on a non-answered verdict")
+            rendered = lore_render.render(answered, "Quelles factions ?", prose_spec, {}, exchanges)
+            if (rendered.renderer != "template" or len(exchanges) != 1
+                    or exchanges[0].raw_output is not None
+                    or not (exchanges[0].error or "").startswith("OllamaError")):
+                fail(f"U6b: Ollama down left {[e.to_record() for e in exchanges]}"[:300])
+            collected += exchanges
+        finally:
+            lore_render.chat = original
+        original = _swap(lwd, _Stub([{"questions": ["Qui ?"]},
+                                     {"entities": [], "facts": [], "memberships": [], "controls": []}]))
+        try:
+            for label, usage, call in (
+                ("U6c questions", lwd.QUESTIONS_USAGE,
+                 lambda ex: lwd.draft_questions(db, world.id, "Un texte.", ex)),
+                ("U6c proposal", lwd.PROPOSAL_USAGE,
+                 lambda ex: lwd.draft_proposal(db, world.id, "Un texte.", "", ex)),
+            ):
+                exchanges = []
+                call(exchanges)
+                spec = prompt_load.load(db, usage)
+                if len(exchanges) != 1:
+                    fail(f"{label}: {len(exchanges)} exchange(s)")
+                else:
+                    _check_exchange(label, exchanges[0], usage, spec, exchanges[0].raw_output or "-")
+                    if not exchanges[0].raw_output:
+                        fail(f"{label}: no raw reply kept")
+                collected += exchanges
+        finally:
+            lwd.chat = original
+        if len(collected) < 5:
+            fail(f"U6d: only {len(collected)} exchange(s) collected")
+        try:
+            write_usage_event(db, **_good(attempt_id="att-u6",
+                                          model_calls=[e.to_record() for e in collected]))
+            db.rollback()
+        except ValueError as exc:
+            fail(f"U6d: the writer refused captured exchanges: {exc}")
+
+
 def main() -> int:
     tmp = tempfile.mkdtemp(prefix="lore_usage_")
     db_path = f"{tmp}/u.db"
@@ -316,13 +509,16 @@ def main() -> int:
     check_u2(db_path)
     check_u3()
     check_u4()
+    check_u5()
+    check_u6()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: lore_usage -- the journal is named by its model and its writer only; "
           "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
-          "writer refuses every malformed record; a journal row outlives its world")
+          "writer refuses every malformed record; a journal row outlives its world; every "
+          "Lore model call can be captured with its prompt version and raw reply")
     return 0
 
 
````

## Scope OUT

- Any route change, any journal write (C). No caller passes a list in this brief except `lore_usage.py`.
- Moving the `chat` calls out of their modules or wrapping `chat` in a helper: `lore_write.py` D1/E1 stub `lwd.chat`, and `lore_isolation.py` R11/R12 walk `render`'s own `chat`/`OllamaError` structure.
- Adding `model_exchange.py` to `lore_isolation.py`'s `PANEL_FILES` or `PIPELINE_FILES`: it is neither; U5 holds it neutral.
- Capturing model calls outside the Lore shell (the day chain, the tick, authoring).
- Changing any prompt text or any parsing behaviour.
- Every later brief of the lot: BRIEF-0103-C, D, E.

## Invariants to defend

**The lore renderer receives rows, never a `Session`:** `model_exchange` holds plain strings and `RenderSpec` stays plain values, so R10 holds. **Only the `answered` verdict reaches a model:** the capture sits inside `_call_model`, which R11 already proves unreachable from the empty branches. **Secrets are structurally excluded:** the capture records the messages already built — it adds nothing to what the model sees.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `lore_isolation.py` fails (R10, R11, R12 or R17), or `lore_write.py` D1/E1 fails: behaviour without a list must be unchanged.
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `python tooling/verify/checks/lore_usage.py` → `PASS: lore_usage -- … a journal row outlives its world; every Lore model call can be captured with its prompt version and raw reply`.
- `lore_isolation.py`, `lore_write.py`, `prompt_registry.py`, `function_length.py`, `module_budget.py` → `PASS`.
- Mutation test: in `lore_plan.py`, replace `        exchange.raw_output = raw` by `        pass`; U6a fails (twice); revert.
- Mutation test: in `lore_render.py`, replace `        model_exchange.fail(exchanges, exc)` by `        pass`; U6b fails; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `EVERY LORE MODEL CALL CAN BE CAPTURED (TICKET-0103) -- PROMPT VERSION AND RAW REPLY (BRIEF-0103-b, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
