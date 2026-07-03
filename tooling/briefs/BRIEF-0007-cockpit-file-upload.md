<!-- slug: cockpit-file-upload -->
# BRIEF — Step "File upload on Soumettre, filename-authority channel" (BRIEF-0007)

## Context
TICKET-0007. The Soumettre surface (BRIEF-0006-a) accepts pasted bodies;
Nia wants to upload the delivered `.md` files directly. Locked at intake:
A1 (upload zone coexists with the textarea, both feeding the same pure
pipeline), B2 (filename is the sole detection authority on the upload
channel; paste keeps body detection; no cross-validation), C1 (ordered
multi-file batches with `bound_ticket` linking), D1 (no recon — the
touched code was specified by BRIEF-0006-a and this ticket exercises the
no-recon-spec rule live for the first time).

## Scope IN

1. **`tooling/pipeline_cockpit/deposit.py` — new pure function
   `parse_filename(name: str) -> ParsedName`.**
   Grammar, applied to the basename with `.md` stripped:
   `(TICKET|RECON|BRIEF)-(0007|[0-9]{4})(-[a-z])?-(slug)` where the
   single-letter suffix group is only legal for `BRIEF`. Returns type,
   number (`None` when the literal placeholder `0007`), optional brief
   suffix, slug. Anything else raises `UnparseableFilename`. No body
   inspection anywhere in this path (B2); no fallback.

2. **Route `POST /api/upload`** (multipart, `files: list[UploadFile]`):
   - Sort the batch: tickets first, then everything else in submitted
     order (C1).
   - Per file: decode UTF-8 → `parse_filename` → number resolution:
     ticket → `compute_next_id()`; non-ticket with a concrete number →
     as-is; non-ticket with placeholder → current `bound_ticket`
     (request-local from a just-processed ticket, else the page-state
     value posted with the form), refuse if none. Then reuse
     `assign_number`'s substitution on the BODY (every `0007` occurrence)
     and write to the type directory under the reconstructed name
     `<TYPE>-<number>[-<suffix>]-<slug>.md`. `TargetExists` refusal
     unchanged.
   - Per-file outcomes: each file succeeds or is refused independently;
     one refusal never blocks the rest of the batch. Response lists, per
     file: created path or refusal reason. A ticket deposit updates the
     page's `bound_ticket` exactly like the paste flow.
   - The route is a thin adapter: all decisions live in the pure
     functions above; no logic duplicated from the paste route.

3. **`index.html` — Soumettre surface:** native
   `<input type="file" multiple accept=".md">` (plus the standard
   drag-over styling the input already gives; no JS library), submitted
   via the existing HTMX pattern; results rendered as the per-file list
   from the route. Textarea untouched (A1).

4. **Verify check extension, `tooling/verify/checks/pipeline_cockpit.py`:**
   the three machine criteria from the ticket — `parse_filename` accept/
   refuse table, batch ordering + `bound_ticket` binding through the pure
   layer in a temp tree, refusal isolation (failed file writes nothing,
   siblings proceed).

## Scope OUT
- No change to the paste path or to body-shape detection (`detect_type`,
  `extract_slug` untouched — they remain the paste channel's authority).
- No filename↔body cross-validation (B3 rejected at intake).
- No producer-contract change: chat keeps embedding `slug:` /
  `<!-- slug: ... -->` in delivered artifacts (the paste channel still
  needs them; on uploads they are simply inert).
- No re-ingestion or renaming of legacy artifacts.
- No new dependencies, no JS upload library, no auth, no git operations.
- No changes under `.claude/` or to any other verify check.

## Invariants to defend
- **Single counter authority**: number assignment still flows through
  `compute_next_id()` only.
- **No silent overwrite**: `TargetExists` refusal applies to uploads
  identically.
- **K1 boundary**: nothing under `tooling/pipeline_cockpit/` imports
  `world_engine` (existing check keeps watching).
- **One logic, two adapters**: any behavior reachable by upload must be
  the same pure functions the paste path calls — divergence between the
  channels beyond detection authority is a defect.

## Done means
- [ ] Live: upload this ticket's own fixture pair (ticket + a dummy recon
      named with `0007`) in one gesture → both land, bound, number shown.
- [ ] Live: upload a brief file carrying a concrete number → written
      as-is; re-uploading it → `TargetExists` refusal shown.
- [ ] Live: a file named `notes.md` is refused with the reason displayed;
      a valid sibling in the same batch still lands.
- [ ] Live regression: pasting a body in the textarea still works.
- [ ] `python -m tooling.verify.run` green, including the extended
      `pipeline_cockpit.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: new section "SOUMETTRE
  FILE UPLOAD — per-channel detection authority (BRIEF-0007, no schema
  change)" recording A1/B2 (per-channel authority, refusal-not-fallback),
  C1, D1. Regenerate the index per close-step.
- No schema change; no changelog entry; CLAUDE.md untouched (the producer
  contract is unchanged).