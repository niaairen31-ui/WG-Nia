"""Pure functions behind the pipeline cockpit's "Soumettre" surface (I1).

No I/O beyond what's injected: every function here takes its inputs as
plain strings/paths and returns a value or raises — routes in app.py stay
thin wrappers so the verify check can exercise these directly.

Producer contract (P1, documented in CLAUDE.md): every chat-produced
artifact embeds a machine-readable slug (`slug:` front-matter field for
tickets; line-1 `<!-- slug: ... -->` comment for recon specs and briefs).
Type is detected from body shape, never from H1 prose (RECON-0006 finding
20: H1 text is demonstrably inconsistent across the real population).
"""
from __future__ import annotations

import pathlib
import re
import sys

_GLUE_DIR = pathlib.Path(__file__).resolve().parents[1] / "glue"
if str(_GLUE_DIR) not in sys.path:
    sys.path.insert(0, str(_GLUE_DIR))

ID_RE = re.compile(r"(?:TICKET|RECON|BRIEF)-(\d{4})")
BRIEF_SUFFIX_RE = re.compile(r"BRIEF-(?:NNNN|\d{4})-([a-z])")
SLUG_FRONT_MATTER_RE = re.compile(r"^slug:\s*(.+?)\s*$")
SLUG_COMMENT_RE = re.compile(r"^<!--\s*slug:\s*(.+?)\s*-->\s*$")
TICKET_ID_LINE_RE = re.compile(r"^id:\s*TICKET-")


class UnknownArtifactType(Exception):
    """Raised when a pasted body matches none of ticket/recon/brief shape."""


class MissingSlug(Exception):
    """Raised when the expected machine-readable slug is absent."""


class MissingBoundTicket(Exception):
    """Raised when a recon/brief body carries the NNNN placeholder but no
    bound_ticket number was supplied."""


class TargetExists(Exception):
    """Raised when the computed deposit path already exists on disk."""


def _front_matter_lines(body: str) -> list[str] | None:
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return None


def detect_type(body: str) -> str:
    """"ticket" if a YAML front-matter block contains a line matching
    `^id:\\s*TICKET-`; "recon" if the first H1 starts with "# RECON";
    "brief" if the first H1 starts with "# BRIEF"; else raises
    UnknownArtifactType."""
    front_matter = _front_matter_lines(body)
    if front_matter is not None:
        for line in front_matter:
            if TICKET_ID_LINE_RE.match(line.strip()):
                return "ticket"

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            if stripped.startswith("# RECON"):
                return "recon"
            if stripped.startswith("# BRIEF"):
                return "brief"
            break

    raise UnknownArtifactType("body matches neither ticket, recon, nor brief shape")


def extract_slug(body: str, type_: str) -> str:
    """Tickets: front-matter `slug:` field. Recon/briefs: first-line HTML
    comment `<!-- slug: ... -->`. Missing -> raises MissingSlug. No
    guessing, no slugification fallback."""
    if type_ == "ticket":
        front_matter = _front_matter_lines(body)
        if front_matter is not None:
            for line in front_matter:
                m = SLUG_FRONT_MATTER_RE.match(line.strip())
                if m:
                    return m.group(1)
        raise MissingSlug("ticket body has no front-matter 'slug:' field")

    lines = body.splitlines()
    if lines:
        m = SLUG_COMMENT_RE.match(lines[0].strip())
        if m:
            return m.group(1)
    raise MissingSlug(f"{type_} body's first line has no '<!-- slug: ... -->' comment")


def assign_number(
    body: str,
    type_: str,
    root: pathlib.Path,
    bound_ticket: str | None,
) -> tuple[str, str]:
    """Tickets -> number = compute_next_id(). Recon/briefs containing the
    NNNN placeholder -> number = bound_ticket (MissingBoundTicket if
    None). Recon/briefs already carrying a concrete 4-digit number in
    their body -> that number, as-is. Substitutes the number for every
    NNNN occurrence in the body. Returns (numbered_body, number)."""
    from next_id import compute_next_id

    if type_ == "ticket":
        number = compute_next_id()
    elif "NNNN" in body:
        if bound_ticket is None:
            raise MissingBoundTicket(
                f"{type_} body carries the NNNN placeholder but no bound_ticket was supplied"
            )
        number = bound_ticket
    else:
        m = ID_RE.search(body)
        if m is None:
            raise MissingBoundTicket(f"{type_} body has no NNNN placeholder and no existing number")
        number = m.group(1)

    numbered_body = body.replace("NNNN", number)
    return numbered_body, number


def target_path(type_: str, number: str, slug: str, body: str, root: pathlib.Path) -> pathlib.Path:
    """`tooling/tickets/TICKET-<n>-<slug>.md` / `tooling/recon/RECON-<n>-<slug>.md`
    / `tooling/briefs/BRIEF-<n>[-<suffix>]-<slug>.md`. The brief suffix
    (`-a`, `-b`, ...) is read from the H1's `(BRIEF-....-x)` tag when
    present; absent tag -> no suffix. Refuses to overwrite an existing
    file (TargetExists)."""
    if type_ == "ticket":
        path = root / "tooling" / "tickets" / f"TICKET-{number}-{slug}.md"
    elif type_ == "recon":
        path = root / "tooling" / "recon" / f"RECON-{number}-{slug}.md"
    elif type_ == "brief":
        suffix = ""
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                m = BRIEF_SUFFIX_RE.search(stripped)
                if m:
                    suffix = f"-{m.group(1)}"
                break
        path = root / "tooling" / "briefs" / f"BRIEF-{number}{suffix}-{slug}.md"
    else:
        raise UnknownArtifactType(f"unknown artifact type '{type_}'")

    if path.exists():
        raise TargetExists(f"{path} already exists")
    return path
