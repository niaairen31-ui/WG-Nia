"""G1 check: the cockpit stylesheet partition (TICKET-0063, BRIEF-0063-a).

Creation's entire visual layer -- buttons, cards, badges, the `:root`
design tokens -- used to live in one ~1050-line <style> block inside
cockpit/index.html, shared by Play/Observation/Creation alike. Once
Creation mounts outside the legacy iframe (BRIEF-0059-l), nothing in that
inline block reaches it. R1 partitions the sheet three ways -- shared.css
(both surviving documents), creation.css (Creation-only, linked by both
while the iframe mount persists) and cockpit/index.html's own remaining
inline <style> (Play + legacy-document-only chrome) -- and makes cascade
order moot rather than reasoned about: if no selector appears in more than
one destination, load order cannot decide a conflict.

Six rules, each named in its own failure message:

  rule1 (scan is real)         -- vacuous-proof: both sheets exist and are
                                   non-empty, the inline <style> block
                                   parses and is non-empty.
  rule2 (no duplicate selectors) -- every top-level selector across the
                                   three sources is unique; a duplicate
                                   means load order would decide a
                                   conflict, exactly what this partition
                                   exists to make impossible.
  rule3 (tokens moved, not copied) -- no `:root { ... }` block survives in
                                   cockpit/index.html; the design tokens
                                   exist exactly once, in shared.css.
  rule4 (both documents link shared) -- frontend/index.html and
                                   cockpit/index.html each carry the exact
                                   shared.css <link>.
  rule5 (creation link tracks the mount) -- cockpit/index.html links
                                   creation.css IFF LEGACY_MOUNTS declares
                                   `creation`; both directions FAIL. This
                                   is what makes BRIEF-0059-l's single
                                   deleted <link> structurally required,
                                   not remembered.
  rule6 (built copies are fresh) -- static/shared.css and static/creation.css
                                   exist and byte-match their
                                   frontend/public/ sources. No line-ending
                                   normalisation: a byte comparison that
                                   normalises is fail-open, and
                                   .gitattributes already governs EOLs
                                   here.

No DB, stdlib only, same FAILURES/_report_and_exit/ROOT idiom as
legacy_call.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_PUBLIC = ROOT / "frontend" / "public"
SHARED_SRC = FRONTEND_PUBLIC / "shared.css"
CREATION_SRC = FRONTEND_PUBLIC / "creation.css"
FRONTEND_INDEX = ROOT / "frontend" / "index.html"
COCKPIT_INDEX = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
STATIC_DIR = ROOT / "src" / "world_engine" / "cockpit" / "static"
SHARED_STATIC = STATIC_DIR / "shared.css"
CREATION_STATIC = STATIC_DIR / "creation.css"
REGISTRY_FILE = ROOT / "frontend" / "src" / "legacy" / "registry.js"

SHARED_LINK = '<link rel="stylesheet" href="/static/shared.css">'
CREATION_LINK = '<link rel="stylesheet" href="/static/creation.css">'
STYLE_BLOCK_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
MOUNTS_CREATION_RE = re.compile(r"^\s*creation:\s*Object\.freeze\(", re.MULTILINE)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: stylesheet_partition — {counts['selectors']} top-level selector(s) "
        f"across shared.css/creation.css/inline, zero duplicates"
    )
    sys.exit(0)


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _split_top_level(prelude: str, sep: str) -> list[str]:
    """Split on sep at paren/bracket depth 0 only."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _top_level_selectors(css_text: str) -> list[str]:
    """Top-level selectors/at-rule preludes of a stylesheet. Does not
    descend into an at-rule's body (e.g. @keyframes spin { to {...} } is
    one atomic entry, 'to' is never extracted as its own selector) --
    only the selectors this partition actually governs are meaningful
    duplication candidates."""
    text = _strip_comments(css_text)
    selectors: list[str] = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        start = i
        while i < n and text[i] != "{":
            i += 1
        if i >= n:
            break
        prelude = text[start:i].strip()
        depth = 0
        j = i
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1
        if not prelude:
            continue
        if prelude.startswith("@"):
            selectors.append(" ".join(prelude.split()))
        else:
            for sel in _split_top_level(prelude, ","):
                sel = " ".join(sel.split())
                if sel:
                    selectors.append(sel)
    return selectors


def _extract_inline_style(html_text: str, source_label: str) -> str | None:
    m = STYLE_BLOCK_RE.search(html_text)
    if not m:
        fail(f"rule1: vacuous scan -- no <style>...</style> block found in {source_label}")
        return None
    body = m.group(1)
    if not body.strip():
        fail(f"rule1: vacuous scan -- <style> block in {source_label} is empty")
        return None
    return body


def _check_rule1_and_collect() -> dict[str, list[str]] | None:
    """rule1 + selector collection for rule2/rule3. Returns
    {source_name: [selectors]} or None if any input is vacuous."""
    sources: dict[str, list[str]] = {}

    if not SHARED_SRC.is_file():
        fail(f"rule1: vacuous scan -- {SHARED_SRC} does not exist")
    else:
        text = SHARED_SRC.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"rule1: vacuous scan -- {SHARED_SRC} is empty")
        else:
            sources["shared.css"] = _top_level_selectors(text)

    if not CREATION_SRC.is_file():
        fail(f"rule1: vacuous scan -- {CREATION_SRC} does not exist")
    else:
        text = CREATION_SRC.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"rule1: vacuous scan -- {CREATION_SRC} is empty")
        else:
            sources["creation.css"] = _top_level_selectors(text)

    if not COCKPIT_INDEX.is_file():
        fail(f"rule1: vacuous scan -- {COCKPIT_INDEX} does not exist")
    else:
        html_text = COCKPIT_INDEX.read_text(encoding="utf-8")
        inline_body = _extract_inline_style(html_text, str(COCKPIT_INDEX))
        if inline_body is not None:
            sources["cockpit/index.html (inline)"] = _top_level_selectors(inline_body)

    if len(sources) != 3:
        return None
    return sources


def _check_rule2(sources: dict[str, list[str]]) -> int:
    """No selector appears in more than one source. Returns total selector count."""
    owner: dict[str, str] = {}
    total = 0
    for source_name, selectors in sources.items():
        for sel in selectors:
            total += 1
            if sel in owner and owner[sel] != source_name:
                fail(
                    f"rule2: selector {sel!r} appears in both {owner[sel]} and "
                    f"{source_name} -- exactly one destination is allowed"
                )
            else:
                owner[sel] = source_name
    return total


def _check_rule3(sources: dict[str, list[str]]) -> None:
    inline = sources.get("cockpit/index.html (inline)")
    if inline is None:
        return
    if ":root" in inline:
        fail(
            "rule3: cockpit/index.html's inline <style> still declares a :root block -- "
            "design tokens must exist exactly once, in shared.css"
        )


def _check_rule4() -> None:
    for path, label in ((FRONTEND_INDEX, "frontend/index.html"), (COCKPIT_INDEX, "cockpit/index.html")):
        if not path.is_file():
            fail(f"rule4: {path} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        if SHARED_LINK not in text:
            fail(f"rule4: {label} is missing the exact shared.css <link> ({SHARED_LINK!r})")


def _check_rule5() -> None:
    if not REGISTRY_FILE.is_file():
        fail(f"rule5: {REGISTRY_FILE} does not exist")
        return
    registry_text = REGISTRY_FILE.read_text(encoding="utf-8")
    mount_declared = bool(MOUNTS_CREATION_RE.search(registry_text))

    if not COCKPIT_INDEX.is_file():
        fail(f"rule5: {COCKPIT_INDEX} does not exist")
        return
    cockpit_text = COCKPIT_INDEX.read_text(encoding="utf-8")
    link_present = CREATION_LINK in cockpit_text

    if link_present and not mount_declared:
        fail(
            "rule5: cockpit/index.html links creation.css but LEGACY_MOUNTS no longer "
            "declares 'creation' -- the link outlived the mount it was tied to"
        )
    elif mount_declared and not link_present:
        fail(
            "rule5: LEGACY_MOUNTS still declares 'creation' but cockpit/index.html is "
            "missing the creation.css <link> -- Creation would lose its styling while "
            "still rendering inside the legacy iframe"
        )


def _check_rule6() -> None:
    for src, built, label in (
        (SHARED_SRC, SHARED_STATIC, "shared.css"),
        (CREATION_SRC, CREATION_STATIC, "creation.css"),
    ):
        if not src.is_file():
            continue  # already FAILed by rule1
        if not built.is_file():
            fail(f"rule6: {built} does not exist -- run \"npm run build\" in frontend/")
            continue
        if src.read_bytes() != built.read_bytes():
            fail(
                f"rule6: {built} does not byte-match {src} -- run \"npm run build\" in "
                "frontend/ and commit the output"
            )


def main() -> None:
    sources = _check_rule1_and_collect()
    if sources is None:
        _report_and_exit()
        return

    total = _check_rule2(sources)
    _check_rule3(sources)
    _check_rule4()
    _check_rule5()
    _check_rule6()

    _report_and_exit({"selectors": total})


if __name__ == "__main__":
    main()
