"""Pure functions behind the pipeline cockpit's "Soumettre" surface (I1).

No I/O beyond what's injected: every function here takes its inputs as
plain strings/paths and returns a value or raises — routes in app.py stay
thin wrappers so the verify check can exercise these directly.

Producer contract (P1, documented in CLAUDE.md): every chat-produced
artifact embeds a machine-readable slug (`slug:` front-matter field for
tickets; line-1 `<!-- slug: ... -->` comment for recon specs and briefs).
Type is detected from body shape, never from H1 prose (RECON-0006 finding
20: H1 text is demonstrably inconsistent across the real population).

Upload channel (B2, BRIEF-0007): a second, independent detection
authority for artifacts deposited as files rather than pasted bodies.
`parse_filename` reads type/number/brief-suffix/slug from the filename
alone — body shape is never consulted on this path, and an unparseable
name is refused, never silently routed through `detect_type`. Both
channels converge on the same downstream write logic (`target_path`);
only detection authority differs per channel.
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import NamedTuple

_GLUE_DIR = pathlib.Path(__file__).resolve().parents[1] / "glue"
if str(_GLUE_DIR) not in sys.path:
    sys.path.insert(0, str(_GLUE_DIR))

ID_RE = re.compile(r"(?:TICKET|RECON|BRIEF)-(\d{4})")
BRIEF_SUFFIX_RE = re.compile(r"BRIEF-(?:NNNN|\d{4})-([a-z])")
SLUG_FRONT_MATTER_RE = re.compile(r"^slug:\s*(.+?)\s*$")
SLUG_COMMENT_RE = re.compile(r"^<!--\s*slug:\s*(.+?)\s*-->\s*$")
TICKET_ID_LINE_RE = re.compile(r"^id:\s*TICKET-")

# Upload-channel filename grammar (B2, BRIEF-0007): filename is the sole
# detection authority here, never the body. "0007" is the channel's numeric
# placeholder literal (a 4-digit stand-in for the paste channel's "NNNN",
# chosen because this grammar's number slot is digits-only).
FILENAME_RE = re.compile(r"^(TICKET|RECON|BRIEF)-(0007|[0-9]{4})(?:-([a-z]))?-(.+)$")
UPLOAD_NUMBER_PLACEHOLDER = "0007"


class UnknownArtifactType(Exception):
    """Raised when a pasted body matches none of ticket/recon/brief shape."""


class MissingSlug(Exception):
    """Raised when the expected machine-readable slug is absent."""


class MissingBoundTicket(Exception):
    """Raised when a recon/brief body carries the NNNN placeholder but no
    bound_ticket number was supplied."""


class TargetExists(Exception):
    """Raised when the computed deposit path already exists on disk."""


class UnparseableFilename(Exception):
    """Raised when an uploaded filename matches none of the upload
    channel's TICKET/RECON/BRIEF grammar (B2 — refusal, never a body-shape
    fallback)."""


class ParsedName(NamedTuple):
    type_: str
    number: str | None  # None == the upload channel's placeholder literal
    brief_suffix: str | None
    slug: str


def parse_filename(name: str) -> ParsedName:
    """Upload-channel detection authority (B2): parses a basename (`.md`
    stripped) as `(TICKET|RECON|BRIEF)-(0007|NNNN digits)(-[a-z])?-(slug)`.
    The single-letter suffix segment is only legal for BRIEF — present on
    any other type, the name is refused. A number segment equal to the
    literal placeholder "0007" resolves to `None` (bound at deposit time,
    see resolve_upload_number); any other 4-digit number is concrete,
    used as-is. No body inspection anywhere in this path; no fallback."""
    basename = name[: -len(".md")] if name.endswith(".md") else name
    m = FILENAME_RE.match(basename)
    if m is None:
        raise UnparseableFilename(f"{name!r} does not match the TICKET/RECON/BRIEF upload grammar")

    type_word, number_raw, suffix, slug = m.groups()
    type_ = type_word.lower()
    if suffix and type_ != "brief":
        raise UnparseableFilename(f"{name!r}: the '-{suffix}' suffix segment is only legal for BRIEF")

    number = None if number_raw == UPLOAD_NUMBER_PLACEHOLDER else number_raw
    return ParsedName(type_, number, suffix, slug)


def resolve_upload_number(parsed: ParsedName, bound_ticket: str | None) -> str:
    """Upload-channel number resolution (Scope item 2): a ticket always
    gets a fresh `compute_next_id()`, ignoring whatever was in its
    filename. A non-ticket with a concrete filename number keeps it
    as-is. A non-ticket carrying the placeholder resolves to
    `bound_ticket` — `MissingBoundTicket` if none was supplied."""
    from next_id import compute_next_id

    if parsed.type_ == "ticket":
        return compute_next_id()
    if parsed.number is not None:
        return parsed.number
    if bound_ticket is None:
        raise MissingBoundTicket(
            f"{parsed.type_} filename carries the placeholder but no bound_ticket is available"
        )
    return bound_ticket


def substitute_upload_number(body: str, number: str) -> str:
    """Upload-channel body substitution: replaces every literal '0007'
    occurrence with the resolved number — the same replace-all mechanism
    `assign_number` uses for 'NNNN' on the paste channel, retargeted to
    this channel's placeholder literal (B2)."""
    return body.replace(UPLOAD_NUMBER_PLACEHOLDER, number)


def order_upload_batch(names: list[str]) -> list[int]:
    """C1 — ordered multi-file upload: returns `names`' indices reordered
    so filenames that parse as type "ticket" come first (submitted order
    preserved among them), followed by everything else in its original
    submitted order. An unparseable name sorts with the non-ticket group;
    its refusal is decided later, per file, not by this ordering step."""

    def is_ticket(name: str) -> bool:
        try:
            return parse_filename(name).type_ == "ticket"
        except UnparseableFilename:
            return False

    indices = list(range(len(names)))
    indices.sort(key=lambda i: (0 if is_ticket(names[i]) else 1, i))
    return indices


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


def target_path(
    type_: str,
    number: str,
    slug: str,
    body: str,
    root: pathlib.Path,
    brief_suffix: str | None = None,
) -> pathlib.Path:
    """`tooling/tickets/TICKET-<n>-<slug>.md` / `tooling/recon/RECON-<n>-<slug>.md`
    / `tooling/briefs/BRIEF-<n>[-<suffix>]-<slug>.md`. The brief suffix
    (`-a`, `-b`, ...) is read from the H1's `(BRIEF-....-x)` tag when
    `brief_suffix` is not given (paste channel, body-shape authority);
    when `brief_suffix` is given (upload channel, B2 — filename is the
    detection authority) it is used as-is and the body is never scanned
    for it — the one shared path/TargetExists logic, per-channel
    suffix source ("one logic, two adapters"). Refuses to overwrite an
    existing file (TargetExists)."""
    if type_ == "ticket":
        path = root / "tooling" / "tickets" / f"TICKET-{number}-{slug}.md"
    elif type_ == "recon":
        path = root / "tooling" / "recon" / f"RECON-{number}-{slug}.md"
    elif type_ == "brief":
        if brief_suffix is not None:
            suffix = f"-{brief_suffix}"
        else:
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
