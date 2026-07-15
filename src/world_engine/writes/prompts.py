"""`prompt_version`/`prompt_variable` canon-write chokepoints (TICKET-0028,
BRIEF-0028-b — decomposed from `writes.py`; moved for module hygiene, not
policy — neither table is in `canon_write_policy.txt`'s CANON_TABLES).

- `write_prompt_version(...)`   : append a new `prompt_version` row. The
  ONLY function that writes a `prompt_version` row (TICKET-0011, single
  write shape): the PATCH text route, the restore route, and the seed's
  v1-on-virgin-head path all call this so they cannot diverge. C1
  fail-closed placeholder validation: every `{identifier}` placeholder in
  either field must be declared, or nothing is written.
- `write_prompt_variables(...)` : full-replace `prompt_variable` rows for
  one `prompt_template` head (TICKET-0025, BRIEF-0025-c — replaces
  `prompt_template.variables` JSON).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, text
from sqlmodel import Session, select

from ..models import PromptTemplate, PromptVariable, PromptVersion

# Simple-identifier placeholder, e.g. `{player_line}` — deliberately does not
# match JSON-example braces like `{"key": ...}` (TICKET-0011, C1).
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class PromptValidationError(ValueError):
    """C1 fail-closed placeholder validation failed (TICKET-0011).

    `offending` carries the placeholder names not in the head's declared
    `variables` list, for the caller to surface as a 422.
    """

    def __init__(self, offending: list[str]):
        self.offending = offending
        super().__init__(f"undeclared placeholder(s): {', '.join(offending)}")


def write_prompt_version(
    db: Session,
    *,
    template_id: str,
    system_prompt: str,
    user_template: str,
    note: Optional[str] = None,
) -> PromptVersion:
    """Append a new `prompt_version` row for `template_id`. Caller adds nothing
    else — this function itself calls `db.add`.

    C1 fail-closed validation: every `{identifier}` placeholder found in
    EITHER field must be in the head's declared `variables` list
    (`variables` NULL/empty -> any identifier placeholder is rejected). On
    failure raises `PromptValidationError` carrying the offending names;
    nothing is written. JSON-example braces (`{"key": ...}`) don't match the
    identifier pattern and pass freely.

    `version_number` = MAX(existing) + 1 for this head (1 if none exist —
    the migration's own v1 backfill and the seed's virgin-head path both
    reach this branch). Bumps `head.updated_at`.
    """
    head = db.get(PromptTemplate, template_id)
    if head is None:
        raise ValueError(f"write_prompt_version: prompt_template {template_id!r} not found")

    declared = set(db.exec(
        select(PromptVariable.name).where(PromptVariable.prompt_template_id == template_id)
    ).all())
    found = set(_PLACEHOLDER_RE.findall(system_prompt)) | set(_PLACEHOLDER_RE.findall(user_template))
    offending = sorted(found - declared)
    if offending:
        raise PromptValidationError(offending)

    current_max = db.exec(
        select(func.max(PromptVersion.version_number)).where(
            PromptVersion.prompt_template_id == template_id
        )
    ).one()
    next_number = (current_max or 0) + 1

    version = PromptVersion(
        prompt_template_id=template_id,
        version_number=next_number,
        system_prompt=system_prompt,
        user_template=user_template,
        note=note,
    )
    db.add(version)
    head.updated_at = datetime.now(UTC)
    db.add(head)
    return version


def write_prompt_variables(
    db: Session,
    *,
    template_id: str,
    variables: Optional[list[str]],
) -> list[PromptVariable]:
    """Full-replace `prompt_variable` rows for one `prompt_template` head.
    Caller commits.
    """
    clean = sorted({v.strip() for v in (variables or []) if v and v.strip()})
    db.execute(
        text("DELETE FROM prompt_variable WHERE prompt_template_id = :template_id"),
        {"template_id": template_id},
    )
    rows: list[PromptVariable] = []
    for name in clean:
        row = PromptVariable(prompt_template_id=template_id, name=name)
        db.add(row)
        rows.append(row)
    return rows
