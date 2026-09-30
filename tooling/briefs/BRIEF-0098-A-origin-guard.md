<!-- slug: origin-guard -->
# BRIEF 0098-A — "Origin guard on every write method"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: nothing in this lot (first by decision I1, not by dependency)
Commit header for decisions: `(BRIEF-0098-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `tooling/tickets/TICKET-0097-knowledge-identity.md` → front matter `status: live-gate`, `current_brief: G`
- `src/world_engine/cockpit/app.py:32` → `- No authentication needed for this solo local tool.`
- `src/world_engine/cockpit/app.py:118` → `app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)`, and `git grep -n middleware -- src/world_engine` prints nothing
- `client = TestClient(app)` at `tooling/verify/checks/spatial_door_travel.py:164`, `scene_join_target.py:190`, `name_resolution.py:446`, `choice_review.py:561`, `prompt_model_write.py:171`
- `tooling/verify/checks/origin_guard.py` and `tooling/verify/checks/lore_write.py` → do not exist

## Facts carried

### R-01 — the cockpit's exposure [M]
Opened: `src/world_engine/cockpit/app.py:28-34` (Security docstring),
`:118` (`app = FastAPI(...)`); `scripts/cockpit.py:31-32` (`HOST =
"127.0.0.1"`, `PORT = 8000`); `.claude/launch.json:7-8` (port 8001).
Finding: loopback binding, no authentication, no middleware of any kind
(enumeration E2, gate (c)). The cockpit runs on 8000 and 8001.
Consequence: I1 is a new module with nothing to reuse; its rule is
hostname-only, never port.

### R-02 — checks that post through `TestClient` [M]
Opened: the five files of enumeration E1 (gate (c)).
Finding: `client = TestClient(app)` at `spatial_door_travel.py:164`,
`scene_join_target.py:190`, `name_resolution.py:446`, `choice_review.py:561`,
`prompt_model_write.py:171`; each file then posts (counts in E1). Starlette's
default base URL sends `Host: testserver`.
Consequence: A passes `base_url="http://127.0.0.1"` in those five lines;
the guard learns no exception. `origin_guard.py` O4 keeps it that way.

## Contracts

### C-01 — origin guard
Produced by: A   Consumed by: E (E1d), `origin_guard.py`
- `cockpit/origin_guard.py`: `LOCAL_HOSTNAMES = {"127.0.0.1", "localhost",
  "::1"}`; `WRITE_METHODS = {"POST","PUT","PATCH","DELETE"}`;
  `REFUSED_MESSAGE` (French, fixed); `host_name(host) -> str | None`;
  `verdict(method, host, origin) -> str | None` (None = proceed);
  `origin_guard(request, call_next)` (HTTP middleware, 403
  `{"detail": REFUSED_MESSAGE}`).
- Registered once: `app.middleware("http")(origin_guard)` right after
  `app = FastAPI(...)`.

## Context

TICKET-0097 passed its live gate. This brief closes it, then closes every write route of the cockpit to non-local origins before the lot adds a route that turns prose into canon (I1). It also creates `lore_write.py` with its census only, so every Machine arrow of TICKET-0098 resolves from the first brief on.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. **Commit 1 (on its own):** in `tooling/tickets/TICKET-0097-knowledge-identity.md` set `status: done` and empty `current_brief:`. Message: `chore(tickets): close TICKET-0097 — live gate passed (Nia, 2026-09-29)`.
2. **Commit 2:** apply the embedded diff. It: creates `src/world_engine/cockpit/origin_guard.py` (C-01); registers it in `cockpit/app.py` (`from .origin_guard import origin_guard` after the `crud` import; `app.middleware("http")(origin_guard)` right after `app = FastAPI(...)`) and updates the Security docstring; passes `base_url="http://127.0.0.1"` in the five checks of R-02; creates `tooling/verify/checks/origin_guard.py` (O1-O4) and `tooling/verify/checks/lore_write.py` (L0, empty census); appends the decision entry.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit 2 message: `feat(cockpit): origin guard on every write method (BRIEF-0098-a)`.

````diff
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index 4fd9756..43e67ef 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -29,7 +29,9 @@ no logic change) — see BRIEF-0027-d for the full census.
 Security
 --------
 - uvicorn is bound to 127.0.0.1 only (enforced in scripts/cockpit.py).
-- No authentication needed for this solo local tool.
+- No authentication needed for this solo local tool; every write method
+  passes `origin_guard` first (TICKET-0098, BRIEF-0098-A, I1): a non-local
+  Host or Origin is refused with a 403 before any route runs.
 - No CORS opened to any origin.
 - No external calls except the local Ollama endpoint via the existing client.
 """
@@ -51,6 +53,7 @@ from ..db import engine
 from ..models import LinkBatch, LinkBatchRow, NpcBatch, NpcBatchRow, SchemaMeta
 from ..schema_version import EXPECTED_STATIC_SCHEMA_VERSION
 from . import crud as _crud
+from .origin_guard import origin_guard
 from .routes import creator as _routes_creator
 from .routes import day as _routes_day
 from .routes import link_agent as _routes_link_agent
@@ -116,6 +119,7 @@ class _FreshnessAwareStaticFiles(StaticFiles):
 
 
 app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)
+app.middleware("http")(origin_guard)
 app.include_router(_crud.router)
 app.include_router(_routes_creator.router)
 app.include_router(_routes_day.router)
diff --git a/src/world_engine/cockpit/origin_guard.py b/src/world_engine/cockpit/origin_guard.py
new file mode 100644
index 0000000..104e62e
--- /dev/null
+++ b/src/world_engine/cockpit/origin_guard.py
@@ -0,0 +1,65 @@
+"""Origin guard for every write route (TICKET-0098, BRIEF-0098-A, decision I1).
+
+The cockpit is bound to loopback with no authentication. Loopback binding
+does not stop a web page open in the creator's own browser from sending a
+request to `127.0.0.1`: a cross-site form post, or a DNS-rebinding page
+whose name resolves to loopback. Both carry a non-local `Origin` (the
+first) or a non-local `Host` (the second). This guard refuses any write
+method whose `Host` hostname is not local, or whose `Origin`, when sent,
+is not a local http(s) origin. Reads pass untouched; a local script that
+sends no `Origin` passes as long as its `Host` is local.
+
+The rule is hostname-only, never port: the cockpit runs on 8000 and, from
+`.claude/launch.json`, on 8001. `verdict` is pure; the middleware is the
+only caller in `src/`.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+from urllib.parse import urlsplit
+
+from fastapi import Request
+from fastapi.responses import JSONResponse
+
+LOCAL_HOSTNAMES: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
+WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
+REFUSED_MESSAGE = (
+    "Écriture refusée : la requête ne vient pas du cockpit local "
+    "(origine ou hôte non local)."
+)
+
+
+def host_name(host: Optional[str]) -> Optional[str]:
+    """The hostname of a `Host` header value (`name`, `name:port`,
+    `[v6]:port`), lowercased; None when absent or empty."""
+    if not host:
+        return None
+    parsed = urlsplit(f"//{host.strip()}")
+    return parsed.hostname
+
+
+def verdict(method: str, host: Optional[str], origin: Optional[str]) -> Optional[str]:
+    """None when the request may proceed, else the refusal message.
+
+    A read method always proceeds. A write method proceeds only when the
+    `Host` hostname is local and the `Origin` is absent or a local
+    http(s) origin. `Origin: null` (sandboxed or opaque) is refused."""
+    if method.upper() not in WRITE_METHODS:
+        return None
+    if host_name(host) not in LOCAL_HOSTNAMES:
+        return REFUSED_MESSAGE
+    if origin is None:
+        return None
+    parsed = urlsplit(origin.strip())
+    if parsed.scheme not in ("http", "https") or parsed.hostname not in LOCAL_HOSTNAMES:
+        return REFUSED_MESSAGE
+    return None
+
+
+async def origin_guard(request: Request, call_next):
+    """HTTP middleware: a 403 with `REFUSED_MESSAGE` on a refused write."""
+    refusal = verdict(request.method, request.headers.get("host"), request.headers.get("origin"))
+    if refusal is not None:
+        return JSONResponse(status_code=403, content={"detail": refusal})
+    return await call_next(request)
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 2e4e66b..01635d2 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17222,6 +17222,23 @@ already fail on `main` (no `fact_id`, since 0082) and are left as they are;
 `apply_ticket_0087_subject_participants.py` imports the deleted
 `subject_resolve` -- a one-shot that ran in 0087, kept as history.
 
+## WRITES FROM A NON-LOCAL ORIGIN ARE REFUSED (TICKET-0098) -- ONE GUARD FOR EVERY ROUTE (BRIEF-0098-a, no schema change)
+
+**I1.** The cockpit is bound to loopback with no authentication, which does
+not stop a page open in the creator's browser from posting to `127.0.0.1`
+(a cross-site form, or a DNS-rebinding name). TICKET-0098 adds a route that
+turns free prose into canon, so the gap now reaches the world itself.
+`cockpit/origin_guard.py` refuses every POST/PUT/PATCH/DELETE whose `Host`
+hostname is not local, or whose `Origin`, when present, is not a local
+http(s) origin; reads pass. The rule is hostname-only (the cockpit runs on
+8000 and 8001). Five checks that post through `TestClient` now declare
+`base_url="http://127.0.0.1"`: no exception is taught to the guard.
+
+**Rejected.** I2 (a per-boot session token on every write): reactivates if
+the cockpit ever listens beyond loopback, or another local tool must call
+the API. I3 (nothing now, authentication later): the writing route would
+ship open.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/choice_review.py b/tooling/verify/checks/choice_review.py
index e19a2a9..a49b7d2 100644
--- a/tooling/verify/checks/choice_review.py
+++ b/tooling/verify/checks/choice_review.py
@@ -558,7 +558,7 @@ def check_route(engine, ids: dict) -> int:
 
     with Session(engine) as db:
         choices_before, rewrites_before = _count(db, DayMentionChoice), _count(db, DayRewrite)
-    client = TestClient(app)
+    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
     listed = _check_t1_t4(client, engine, ids)
     _check_t5_t9(client, engine, ids)
     resp = client.get("/api/lore/choices")
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
new file mode 100644
index 0000000..e439675
--- /dev/null
+++ b/tooling/verify/checks/lore_write.py
@@ -0,0 +1,56 @@
+"""G1 check for TICKET-0098 -- the lore writing path.
+
+The lot adds its modules brief by brief; this check grows with it. Each
+brief adds its files to `_LORE_WRITE_FILES` and its rules below in the same
+commit (the `knowledge_identity.py` K3 census precedent, TICKET-0097).
+
+L0 -- census. The files of the lore writing path that exist under
+   `src/world_engine` (the glob `_CENSUS_GLOBS`) equal `_LORE_WRITE_FILES`
+   exactly: a new module is red until a brief names it, a named module that
+   is missing is red.
+
+Fresh temp-file SQLite database for any fixture rule
+(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
+Nia's DB.
+"""
+from __future__ import annotations
+
+import pathlib
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+
+FAILURES: list[str] = []
+
+_CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
+_LORE_WRITE_FILES: frozenset[str] = frozenset()
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def check_l0() -> None:
+    found = {
+        path.relative_to(SRC).as_posix()
+        for pattern in _CENSUS_GLOBS for path in SRC.glob(pattern)
+    }
+    for extra in sorted(found - _LORE_WRITE_FILES):
+        fail(f"L0: {extra} exists but no brief named it in _LORE_WRITE_FILES")
+    for missing in sorted(_LORE_WRITE_FILES - found):
+        fail(f"L0: {missing} is named in _LORE_WRITE_FILES but does not exist")
+
+
+def main() -> int:
+    check_l0()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/name_resolution.py b/tooling/verify/checks/name_resolution.py
index e68e183..6ea7360 100644
--- a/tooling/verify/checks/name_resolution.py
+++ b/tooling/verify/checks/name_resolution.py
@@ -443,7 +443,7 @@ def check_g11(engine) -> None:
     from world_engine.models import UnresolvedMention
 
     maelis_id, (bound_id, refused_id) = _g11_fixture(engine)
-    client = TestClient(app)
+    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
     _g11_panel_reads_and_post(client, maelis_id)
     with Session(engine) as session:
         before = len(_appellation_facts(session, maelis_id))
diff --git a/tooling/verify/checks/origin_guard.py b/tooling/verify/checks/origin_guard.py
new file mode 100644
index 0000000..62a386f
--- /dev/null
+++ b/tooling/verify/checks/origin_guard.py
@@ -0,0 +1,166 @@
+"""G1 check for TICKET-0098 (BRIEF-0098-A, decision I1) -- the origin guard.
+
+O1 -- verdict table. `cockpit/origin_guard.py::verdict` returns the refusal
+   message or None for every row of `_CASES` (method x Host x Origin).
+O2 -- wiring. `cockpit/app.py` registers `origin_guard` with
+   `app.middleware("http")` exactly once, and nothing else in
+   `src/world_engine` calls `verdict` or `origin_guard` (one gate, one site).
+O3 -- live. Through `TestClient(app)`: a POST from a non-local Host answers
+   403 with `REFUSED_MESSAGE`; the same POST from a non-local Origin answers
+   403; a GET from a non-local Host is not a 403; a POST from the local host
+   with no Origin reaches the route (not a 403).
+O4 -- every `TestClient(app` construction in `tooling/verify/checks/` that
+   is followed in the same file by a write call (`.post(`, `.put(`,
+   `.patch(`, `.delete(` on a client) passes `base_url="http://127.0.0.1"`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that locates zero items is a
+FAILURE.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import re
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+CHECKS = ROOT / "tooling" / "verify" / "checks"
+GUARD = SRC / "cockpit" / "origin_guard.py"
+APP = SRC / "cockpit" / "app.py"
+
+FAILURES: list[str] = []
+
+_REFUSED = "refused"
+# (method, host, origin, expected) -- expected is None (proceeds) or _REFUSED.
+_CASES = (
+    ("GET", "evil.example", None, None),
+    ("GET", "127.0.0.1:8000", "https://evil.example", None),
+    ("POST", "127.0.0.1:8000", None, None),
+    ("POST", "localhost:8001", None, None),
+    ("POST", "[::1]:8000", None, None),
+    ("POST", "127.0.0.1:8000", "http://127.0.0.1:8000", None),
+    ("POST", "127.0.0.1:8000", "http://localhost:5173", None),
+    ("PUT", "127.0.0.1", "http://127.0.0.1", None),
+    ("POST", "evil.example", None, _REFUSED),
+    ("POST", "evil.example:8000", "http://evil.example:8000", _REFUSED),
+    ("POST", None, None, _REFUSED),
+    ("POST", "testserver", None, _REFUSED),
+    ("POST", "127.0.0.1:8000", "https://evil.example", _REFUSED),
+    ("POST", "127.0.0.1:8000", "null", _REFUSED),
+    ("POST", "127.0.0.1:8000", "file://127.0.0.1", _REFUSED),
+    ("PATCH", "127.0.0.1.evil.example", None, _REFUSED),
+    ("DELETE", "localhost.evil.example:8000", None, _REFUSED),
+    ("delete", "evil.example", None, _REFUSED),
+)
+_WRITE_CALL = re.compile(r"\bclient\.(post|put|patch|delete)\(")
+_LOCAL_BASE = 'base_url="http://127.0.0.1"'
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def check_o1(guard_mod) -> None:
+    for method, host, origin, expected in _CASES:
+        got = guard_mod.verdict(method, host, origin)
+        want = guard_mod.REFUSED_MESSAGE if expected == _REFUSED else None
+        if got != want:
+            fail(f"O1: verdict({method!r}, {host!r}, {origin!r}) = {got!r}, expected {want!r}")
+
+
+def _is_middleware_registration(node: ast.AST) -> bool:
+    return (
+        isinstance(node, ast.Call)
+        and isinstance(node.func, ast.Call)
+        and isinstance(node.func.func, ast.Attribute)
+        and node.func.func.attr == "middleware"
+        and isinstance(node.func.func.value, ast.Name) and node.func.func.value.id == "app"
+        and [a.value for a in node.func.args if isinstance(a, ast.Constant)] == ["http"]
+        and len(node.args) == 1 and isinstance(node.args[0], ast.Name)
+        and node.args[0].id == "origin_guard"
+    )
+
+
+def check_o2() -> None:
+    tree = ast.parse(APP.read_text(encoding="utf-8"))
+    regs = [n for n in ast.walk(tree) if _is_middleware_registration(n)]
+    if len(regs) != 1:
+        fail(f"O2: cockpit/app.py registers origin_guard {len(regs)} time(s), expected 1")
+    scanned = 0
+    for path in SRC.rglob("*.py"):
+        if path in (GUARD, APP):
+            continue
+        scanned += 1
+        text = path.read_text(encoding="utf-8")
+        if re.search(r"\b(verdict|origin_guard)\(", text) and "origin_guard" in text:
+            fail(f"O2: {path.relative_to(ROOT).as_posix()} calls the origin guard")
+    if scanned == 0:
+        fail("O2: scanned zero modules under src/world_engine")
+
+
+def check_o3(guard_mod) -> None:
+    from fastapi.testclient import TestClient
+    from world_engine.cockpit.app import app
+
+    far = TestClient(app, base_url="http://evil.example")
+    resp = far.post("/api/lore/ask", json={"question": "x"})
+    if resp.status_code != 403 or resp.json().get("detail") != guard_mod.REFUSED_MESSAGE:
+        fail(f"O3: non-local Host POST answered {resp.status_code} {resp.text[:120]!r}")
+    near = TestClient(app, base_url="http://127.0.0.1")
+    resp = near.post("/api/lore/ask", json={"question": "x"},
+                     headers={"origin": "https://evil.example"})
+    if resp.status_code != 403:
+        fail(f"O3: non-local Origin POST answered {resp.status_code}, expected 403")
+    resp = far.get("/api/worlds")
+    if resp.status_code == 403:
+        fail("O3: a GET from a non-local Host was refused")
+    resp = near.post("/api/lore/resolve", json={})
+    if resp.status_code == 403:
+        fail("O3: a local POST with no Origin was refused")
+
+
+def check_o4() -> None:
+    constructions = 0
+    for path in sorted(CHECKS.glob("*.py")):
+        if path.name == pathlib.Path(__file__).name:
+            continue
+        text = path.read_text(encoding="utf-8")
+        if not _WRITE_CALL.search(text):
+            continue
+        for line in text.splitlines():
+            if re.search(r"=\s*TestClient\(app\b", line):
+                constructions += 1
+                if _LOCAL_BASE not in line:
+                    fail(f"O4: {path.name}: a writing TestClient lacks {_LOCAL_BASE}: {line.strip()}")
+    if constructions == 0:
+        fail("O4: found zero writing TestClient constructions")
+
+
+def main() -> int:
+    tmp = tempfile.mkdtemp(prefix="origin_guard_")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{tmp}/x.db"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    from world_engine.cockpit import origin_guard as guard_mod
+    from world_engine.db import create_db_and_tables
+
+    create_db_and_tables()
+    check_o1(guard_mod)
+    check_o2()
+    check_o3(guard_mod)
+    check_o4()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: origin_guard -- writes from a non-local Host or Origin are refused; reads and "
+          "local writes pass; one registration; every writing test client is local")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/prompt_model_write.py b/tooling/verify/checks/prompt_model_write.py
index 783759d..5f71ee4 100644
--- a/tooling/verify/checks/prompt_model_write.py
+++ b/tooling/verify/checks/prompt_model_write.py
@@ -168,7 +168,7 @@ def check_write_path_and_list_route() -> None:
         session.refresh(row)
         last_updated_at = row.updated_at
 
-    client = TestClient(app)
+    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
 
     # unknown id -> 404
     resp = client.patch("/api/prompts/does-not-exist/model", json={"model": None})
diff --git a/tooling/verify/checks/scene_join_target.py b/tooling/verify/checks/scene_join_target.py
index 8e1b9e4..885e285 100644
--- a/tooling/verify/checks/scene_join_target.py
+++ b/tooling/verify/checks/scene_join_target.py
@@ -187,7 +187,7 @@ def check_targeted_and_free_text_join() -> None:
     from world_engine.models import Conversation, GatheringMember
     from world_engine.cockpit.play import ResponseMode
 
-    client = TestClient(app)
+    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
 
     # ── 4. Both / neither -> 422 ────────────────────────────────────────
     resp = client.post("/api/scene/join", json={"player_id": fixture["player_id"]})
diff --git a/tooling/verify/checks/spatial_door_travel.py b/tooling/verify/checks/spatial_door_travel.py
index 6379167..6d5f287 100644
--- a/tooling/verify/checks/spatial_door_travel.py
+++ b/tooling/verify/checks/spatial_door_travel.py
@@ -161,7 +161,7 @@ def check_travel_endpoint() -> None:
     from world_engine.cockpit.app import app
     from world_engine.models import Conversation, Entity, GatheringMember, Relation
 
-    client = TestClient(app)
+    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
 
     def _rows():
         return _count_rows(engine, Conversation), _count_rows(engine, GatheringMember)
````

## Scope OUT

- A session token (I2) or any authentication (I3).
- Any exception in the guard for `testserver` or any other test host: the five checks declare a local base URL instead.
- CORS headers of any kind.
- Every later brief of the lot: BRIEF-0098-B, BRIEF-0098-C, BRIEF-0098-D, BRIEF-0098-E, BRIEF-0098-F.

## Invariants to defend

None of CLAUDE.md's invariants is threatened directly; the guard adds a barrier in front of both canon-write paths without touching them. The risk is behavioural: a guard too strict would stop the cockpit's own pages from saving. O3 proves a local POST with no Origin reaches its route; the live gate checks the cockpit's own writes.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `origin_guard.py` O3 shows a local write refused.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `pipeline_state.py` is red on `main` because TICKET-0098 is deposited with arrows to `origin_guard.py` and `lore_write.py`, which this brief creates: expected before commit 2, green after it.
- A sixth check posts through a default `TestClient(app)` (a check added to `main` since the RECON): give it the same `base_url="http://127.0.0.1"` in this commit and report it (O4 names it).

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- Any other place in `tooling/` or `scripts/` that calls the cockpit over HTTP.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` of commit 2 lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/origin_guard.py` → `PASS: origin_guard -- …`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/lore_write.py` → `PASS: lore_write -- census of 0 module(s) holds`.
- Mutation test: comment out `app.middleware("http")(origin_guard)`; `origin_guard.py` fails O2 and O3; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 128 check(s) discovered, 128 executed, 128 passed`.
- `/review-step` then `/close-step` ran on commit 2.

## Docs to update

This brief carries its docs: `cockpit/app.py`'s Security docstring and the decision entry `WRITES FROM A NON-LOCAL ORIGIN ARE REFUSED (TICKET-0098) … (BRIEF-0098-a, no schema change)`. No schema change, no CLAUDE.md change.
