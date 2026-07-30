"""G1 check: frontend build-freshness gate (TICKET-0055, BRIEF-0055-c).

E1 commits the frontend build output instead of building at launch (a stale
or absent build must never render a blank page). This check pays the other
half of that debt: a *stale* build. No DB, stdlib only (hashlib, json), same
FAILURES/_report_and_exit/ROOT idiom as import_cycle.py. Four assertions,
each a vacuous-proof guard (a missing/empty input is a FAILURE, never a
trivially-satisfied comparison):

  1. Sources exist — frontend/src/ is a directory, the source set is
     non-empty, and the four named root files exist.
  2. Output exists — src/world_engine/cockpit/static/ is a directory
     containing at least one *.js file and an index.html.
  3. Manifest exists and is well-formed — .build-manifest.json parses as
     JSON and carries a source_hash matching ^[0-9a-f]{64}$.
  4. Manifest is fresh — the recomputed source hash equals the manifest's
     source_hash.

Assertion 4 also carries a diagnostic-only 4-bis (BRIEF-0055-c amendment,
TICKET-0055): on a mismatch, the source hash is recomputed a SECOND time
with CRLF normalized to LF before hashing, purely to produce a more useful
failure message when the mismatch is a `.gitattributes` refresh issue
(`frontend/**` is `text eol=lf`, `static/**` is `-text`, TICKET-0055). This
normalized value is NEVER the primary comparison and never turns a FAIL
into a PASS — it only changes which message is printed before exiting 1.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_SRC = FRONTEND_DIR / "src"
ROOT_FILES = ("package.json", "package-lock.json", "vite.config.js", "index.html")
STATIC_DIR = ROOT / "src" / "world_engine" / "cockpit" / "static"
MANIFEST_FILE = STATIC_DIR / ".build-manifest.json"
SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(source_count: int = 0, output_count: int = 0) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: frontend_build_fresh — {source_count} source file(s), "
        f"{output_count} output asset(s), manifest hash matches"
    )
    sys.exit(0)


def _source_set() -> list[Path] | None:
    """Every file under frontend/src/ at any depth, plus the four named
    root files. Returns None (with FAILURES populated) on any miss —
    assertion 1."""
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return None

    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files — empty source set is a failure, never a vacuous pass")
        return None

    for name in ROOT_FILES:
        p = FRONTEND_DIR / name
        if not p.is_file():
            fail(f"{p} does not exist")
            return None
        files.append(p)

    return files


def _canonical_source_hash(files: list[Path], *, normalize_eol: bool = False) -> str:
    """SOURCE SET -> PER-FILE -> CANONICAL STRING -> SOURCE HASH, per the
    canonical algorithm specified verbatim in BRIEF-0055-c item 1. The
    primary comparison (assertion 4) always calls this with
    normalize_eol=False — line endings are hashed as they exist on disk.
    normalize_eol=True is the 4-bis diagnostic path only."""
    rel_files = sorted(p.relative_to(ROOT).as_posix() for p in files)
    canonical = ""
    for rel in rel_files:
        raw = (ROOT / rel).read_bytes()
        if normalize_eol:
            raw = raw.replace(b"\r\n", b"\n")
        file_hash = hashlib.sha256(raw).hexdigest()
        canonical += f"{rel}\n{file_hash}\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_output() -> int | None:
    """Assertion 2. Returns the output *.js asset count, or None (with
    FAILURES populated) on any miss."""
    if not STATIC_DIR.is_dir():
        fail(f"{STATIC_DIR} is not a directory")
        return None
    js_files = list(STATIC_DIR.glob("**/*.js"))
    if not js_files:
        fail(f"{STATIC_DIR} contains no .js file")
        return None
    if not (STATIC_DIR / "index.html").is_file():
        fail(f"{STATIC_DIR / 'index.html'} does not exist")
        return None
    return len(js_files)


def _check_manifest() -> str | None:
    """Assertion 3. Returns the manifest's source_hash, or None (with
    FAILURES populated) on any miss."""
    if not MANIFEST_FILE.is_file():
        fail(f"{MANIFEST_FILE} does not exist")
        return None
    try:
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{MANIFEST_FILE} does not parse as JSON: {exc}")
        return None
    source_hash = manifest.get("source_hash")
    if not isinstance(source_hash, str) or not SOURCE_HASH_RE.match(source_hash):
        fail(f"{MANIFEST_FILE}: source_hash {source_hash!r} does not match ^[0-9a-f]{{64}}$")
        return None
    return source_hash


def main() -> None:
    files = _source_set()
    output_count = _check_output()
    manifest_hash = _check_manifest()

    if FAILURES:
        _report_and_exit()
        return

    recomputed_hash = _canonical_source_hash(files)
    if recomputed_hash != manifest_hash:
        normalized_hash = _canonical_source_hash(files, normalize_eol=True)
        if normalized_hash == manifest_hash:
            fail(
                "source bytes differ only by line endings -- the .gitattributes rule "
                "for frontend/** is missing or the working tree was not refreshed "
                "after adding it; see ARCHITECTURE_DECISIONS.md"
            )
        else:
            fail(
                f"manifest source_hash {manifest_hash[:12]}... does not match recomputed "
                f"{recomputed_hash[:12]}... — run \"npm run build\" in frontend/ and commit the output"
            )
        _report_and_exit()
        return

    _report_and_exit(source_count=len(files), output_count=output_count)


if __name__ == "__main__":
    main()
