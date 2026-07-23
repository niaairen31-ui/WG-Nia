---
id: TICKET-0048
title: canon.py stratum sub-split -- extract faction domain to canon_faction.py
type: refactor            # NOTE: TEMPLATE.md's type enum lists only feature|bug; refactor per Nia's call (2026-07-23). Template may need a type-vocab update.
status: live-gate         # intake|recon|brief|exec|verify|live-gate|done|paused|escalated
created: 2026-07-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # no db_write, no migration, no destructive_data -- move-only, schema byte-identical
blast_radius: small
brief_ids: [BRIEF-0048-a]
schema_version_touched:   # none -- no schema change, no version bump
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Resume-blocking decision surfaced during BRIEF-0044-b execution (Claude Code
stopped pre-commit per /brief-exec's D1 rule): the brief instructs adding
`EntityType` + `EntityTypeHistory` to `src/world_engine/models/canon.py`,
which pushes the file from 985 -> 1064 lines, crossing `module_budget.py`'s
1000-line cap for the first time (PASS -> FAIL). Two non-brief paths existed:
(1) split `canon.py`, or (2) add a `module_budget.json` baseline entry.

Nia's call: split, not baseline. This ticket carries that split as a
standalone preparatory refactor that lands on `main` BEFORE 0044-b resumes;
0044-b then places its two classes into the slimmed `canon.py` with room to
spare, unchanged from its brief.

## Clarifications resolved (intake)

Split-vs-baseline: **split** (doctrine C2, refactor over exemption).
`module_budget.py`'s own docstring frames the baseline as a transition
artifact retired at TICKET-0028's close (entries "may only shrink or
disappear; this check never rewrites the baseline"); creating a fresh entry
for new growth is exactly what the mechanism forbids. The failing check IS
the tripwire forcing the split.

Decisions locked (2026-07-23):
- **A1** -- extract the faction domain (`Faction`, `FactionRole`,
  `FactionMembership`) into a new `models/canon_faction.py`. Largest clean
  single-domain block (`canon.py:395-515`, ~121 lines); post-split canon.py
  ~864, then +79 for 0044-b's EntityType = ~943 (durable ~57-line headroom).
- **B1** -- `canon_faction.py` imports `_uuid`/`_created_ts`
  `from .canon import ...`. No `models/_base.py` extraction (B2 deferred;
  trigger = a second domain extraction actually needs the shared helpers).
- **C1** -- `EntityType`/`EntityTypeHistory` stay in the slimmed `canon.py`;
  0044-b resumes there unchanged. No registry/catalog stratum (C2 deferred).
- **D** -- module name `models/canon_faction.py`.
- **type = refactor.**

RECON facts (live `main`, canon.py at 985) anchoring blast_radius = small:
- All 93 external import sites resolve through the package
  (`from .models import X`); **zero** direct `models.canon` imports. Moving
  a class = only `models/__init__.py`'s internal import block changes; the
  93 sites are untouched (the TICKET-0028 re-export pattern).
- Structural gates already walk the package, not the file:
  `single_canon_write.py` and `world_tick.py` walk `MODELS_DIR`;
  `canon_write_policy.txt` keys on **table names**, not module paths. A new
  canon sub-module is covered automatically.
- Only `npc_goal_read.py` path-couples `models/canon.py` in its
  `ALLOWED_MODULES` -- and it concerns the `npc_goal` cluster, NOT faction.
  The faction domain has **zero** verify-check path-coupling: no check edit
  required. `prompt_version.py` deliberately excludes canon.py (fail-closed
  preserved; the new module is out of its allow-list too, correctly).

Ordering: this ticket merges to `main` before BRIEF-0044-b resumes. During
0048, 0044-b's uncommitted working tree is stashed to keep `main` clean.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `canon.py` <= 1000 physical lines (target ~864)  -> verify/checks/module_budget.py (PASS)
- [ ] faction tables (`faction`, `faction_role`, `faction_membership`) attributed from `models/canon_faction.py`, no unattributable write site  -> verify/checks/single_canon_write.py (PASS)
- [ ] CLAUDE.md File structure lists `models/canon_faction.py` (pointer-fresh)  -> verify/checks/claude_md_contract.py (PASS)
- [ ] entire verify suite green  -> tooling/verify/run.py
- [ ] existing test suite passes with ZERO test-file edits (move-only correctness signal)
- [ ] `from world_engine.models import Faction, FactionRole, FactionMembership` resolves; `models/__init__.py` `__all__` byte-unchanged

### Live  ->  human gate (Nia)
- [ ] virgin-DB `init_db.py` registers every table; `world-engine-schema.md` diff empty (no schema change, no version bump)
- [ ] `models/canon_faction.py` defines exactly the three faction classes with their section-header comments; `canon.py` no longer defines them; no duplicated definition anywhere
- [ ] 0048 merged to `main` before BRIEF-0044-b resumes; 0044-b then adds EntityType/EntityTypeHistory to the slimmed `canon.py` with the cap green
