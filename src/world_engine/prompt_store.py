"""`prompt_version` read accessor (G1) — TICKET-0011.

The ONLY read path for `prompt_version`. Every prompt-text consumer (loaders,
assemblers, previews, reader API) fetches the head (`PromptTemplate`, via its
existing loader) and then calls `current_prompt(db, template)` once, next to
that load, to get the text — mirroring the `effective_model` pattern.

Pure reads only: this module never writes. The sole write path is
`writes.write_prompt_version`.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import PromptTemplate, PromptVersion


def current_prompt(db: Session, template: PromptTemplate) -> PromptVersion:
    """Return the highest-`version_number` row for `template`.

    Raises RuntimeError on a versionless head — structurally impossible
    post-migration (migration post-check + S2 + append-only): a head with
    zero versions must fail loud, never fall back to blank text.
    """
    version = db.exec(
        select(PromptVersion)
        .where(PromptVersion.prompt_template_id == template.id)
        .order_by(PromptVersion.version_number.desc())
    ).first()
    if version is None:
        raise RuntimeError(
            f"prompt_template {template.id!r} ({template.usage!r}) has no "
            "prompt_version rows — run the vX.YY migration."
        )
    return version


def get_version(db: Session, template_id: str, version_number: int) -> PromptVersion | None:
    """Return one specific version row, or None if it doesn't exist."""
    return db.exec(
        select(PromptVersion).where(
            PromptVersion.prompt_template_id == template_id,
            PromptVersion.version_number == version_number,
        )
    ).first()


def list_versions(db: Session, template_id: str) -> list[PromptVersion]:
    """Every version row for `template_id`, newest first."""
    return list(
        db.exec(
            select(PromptVersion)
            .where(PromptVersion.prompt_template_id == template_id)
            .order_by(PromptVersion.version_number.desc())
        ).all()
    )


__all__ = ["current_prompt", "get_version", "list_versions"]
