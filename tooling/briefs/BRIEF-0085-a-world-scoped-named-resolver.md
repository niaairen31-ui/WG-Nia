<!-- slug: world-scoped-named-resolver -->
# BRIEF — Step "World-scoped named resolver"

## Context

TICKET-0085 builds a read-only natural-language consultation surface over the
lore. Its second pipeline step resolves the names in a question to `entity.id`
by lookup, never by model. That lookup already exists inside
`day_concordance.py`, but wired to a `Character` and to play-time casting.
RECON-0085-a (F1, F2) measured that the two named rungs depend on the
concordance context only through `world_id`. This step extracts them, and
nothing else moves.

## Scope IN

1. **New module `src/world_engine/lore_resolve.py`.** Module docstring states,
   verbatim:

   > The resolver never authors and never casts. No model call happens here: a
   > lookup cannot hallucinate an id. Every candidate comes from a real
   > `select(` against canon rows, scoped to the active world at query
   > construction, never post-fetch. Two or more candidates on a name is an
   > ambiguity reported to the creator, never resolved by picking — casting is
   > play semantics and does not exist on this path.

2. **Move `_normalize_surface`, `_LEADING_TOKENS` and `_SURFACE_TOKEN_SPLIT`**
   from `day_concordance.py` into `lore_resolve.py` as `normalize_surface` (now
   public) with its existing docstring carried over unchanged.
   `day_concordance.py` imports it back: `from .lore_resolve import
   normalize_surface`. Do NOT duplicate the function.

3. **Add to `lore_resolve.py` a public `NAMED_RUNGS: tuple[str, ...] =
   ("named_exact", "named_token")`** and a module-level
   `_NAMED_RUNG_LOOKUPS: dict[str, Callable[[str, str, str, Session],
   Optional[list[str]]]]` in bijection with it — the same one-tuple/one-dict
   idiom as `MATCHING_RUNGS`/`_RUNG_LOOKUPS`. `named_alias` is NOT in this
   tuple: RECON F1 measured it as a permanent no-op, and a no-op does not get
   carried into a new module to look complete.

4. **Add `rung_named_exact(surface_form, category, world_id, db)` and
   `rung_named_token(surface_form, category, world_id, db)`** to
   `lore_resolve.py`, bodies moved from `_rung_named_exact` /
   `_rung_named_token` with the `mention.kind != "named"` guard REMOVED (the
   caller owns it) and `mention.surface_form` / `mention.category` /
   `ctx.world_id` replaced by the parameters. The `_CATEGORY_ENTITY_TYPE`
   mapping moves with them. Behavior is otherwise bit-identical — same
   `select(`, same normalization on both sides, same `>= 3` token-length floor,
   same `matches or None` return.

5. **Add the public entry point:**
   `resolve_named(surface_form: str, category: str, world_id: str, db: Session)
   -> NamedResolution`, where `NamedResolution` is a frozen dataclass
   `(verdict: str, entity_id: Optional[str], candidate_ids: tuple[str, ...],
   rung: Optional[str], rungs_tried: tuple[str, ...])` and `verdict` is one of
   `"matched" | "ambiguous" | "unmatched"`. It walks `NAMED_RUNGS` in order,
   stops at the first non-`None` result, returns `matched` on exactly one
   candidate and `ambiguous` on two or more. There is no fourth verdict and no
   casting branch.

6. **Rewire `day_concordance.py`.** `_rung_named_exact` and `_rung_named_token`
   become thin adapters keeping their EXACT current signature
   `(Mention, _ConcordContext, Session) -> Optional[list[str]]`: they keep the
   `mention.kind != "named"` guard, then call the `lore_resolve` function with
   `mention.surface_form`, `mention.category`, `ctx.world_id`, `db`.
   `MATCHING_RUNGS`, `_RUNG_LOOKUPS`, `CAST_PRECEDENCE`, `_CAST_LOOKUPS`,
   `_classify`, `concord` and `emit_germs` are otherwise untouched — RECON F4:
   the existing R6 bijection check must keep passing without being edited.

7. **New G1 check `tooling/verify/checks/lore_resolve.py`**, stdlib `ast` and
   text only, no DB, same FAILURES/fail()/`_parse`/`_rel` idiom as
   `day_concordance.py`'s check:
   - R1 (purity): `lore_resolve.py` contains no `db.add(`, no `.commit(`, no
     `chat(`.
   - R2 (no casting): `lore_resolve.py` contains none of the identifiers
     `_cast_one`, `CAST_PRECEDENCE`, `who_is_at`, `Character`.
   - R3 (bijection): `NAMED_RUNGS` and `_NAMED_RUNG_LOOKUPS` are in bijection.
   - R4 (world scoping at construction): every `select(` in `lore_resolve.py`
     has `world_id` among its `.where(` arguments.
   - R5 (no duplicate normalizer): `_normalize_surface` no longer appears as a
     `def` in `day_concordance.py`.

8. **Register the check** in `tooling/verify/run.py` alongside the existing
   checks, following whatever registration idiom is already there.

## Scope OUT

- **No selectors.** `entity_dossier`, `world_factions`, and every other selector
  belong to BRIEF-0085-b. This step resolves names and returns nothing else.
- **No plan, no plan validation, no whitelist.** BRIEF-0085-b.
- **No model call, no prompt, no `prompt_registry` entry.** BRIEF-0085-c.
- **No prose, no renderer, no template fallback.** BRIEF-0085-d.
- **No route, no frontend.** BRIEF-0085-c and -e.
- **No candidate enrichment.** RECON F5 measured that `AmbiguousMention` carries
  bare ids and that presentation needs names and descriptions. Resolving that is
  BRIEF-0085-c's job; `NamedResolution` stays id-only here. Do not add a name or
  description field "while you're in there".
- **No alias infrastructure.** `named_alias` stays a permanent no-op in
  `day_concordance` and does not appear in `lore_resolve` at all. Do not build
  an alias table, column, or stub.
- **No name-lookup optimization.** RECON F7 measured the linear Python-side
  filter. It is the existing idiom and stays. No index, no `LIKE` pushdown, no
  caching.
- **No `knowledge.subject` FK.** Locked as a decision for the chantier, but it
  belongs to its own ticket with its own non-backfill decision. Nothing in this
  step touches the schema.
- **No change to `concord`'s behavior.** If the extraction changes any
  concordance outcome, that is a defect, not an improvement.

## Invariants to defend

- **Creator control is structural.** This step adds a read path only; it must
  contain no write. R1 of the new check is the guard.
- **Secrets are structurally excluded from every assembled context.** Not
  threatened here — `lore_resolve` reads `entity` name/type/status only, and
  `entity` carries no secret column. It becomes live in BRIEF-0085-b, where
  dossiers reach `knowledge.is_secret` and `discoverable_detail`. Named now so
  the executor does not quietly widen the `select(` to `Entity` columns it does
  not need.
- **All templated model calls resolve through `effective_model`.** Not
  threatened: there is no model call in this step. If one appears, the step is
  wrong.
- **UI-visible data never lives in JSON.** Not threatened.

## Done means

- [ ] `tooling/verify/checks/lore_resolve.py` exits 0
- [ ] `tooling/verify/checks/day_concordance.py` exits 0, unedited
- [ ] `tooling/verify/checks/function_length.py` exits 0
- [ ] `tooling/verify/checks/import_cycle.py` exits 0
- [ ] `tooling/verify/checks/corpus_gate.py` exits 0
- [ ] `grep -n "_normalize_surface" src/world_engine/day_concordance.py` returns
      no `def` line
- [ ] In a live session, a player declaration naming an existing NPC still
      resolves through the day chain with the same `rung` recorded in
      `day_mention_resolution` as before this step
- [ ] In a Python REPL against a live DB, `resolve_named("<an existing NPC
      name>", "person", "<active world id>", db)` returns verdict `matched` with
      that NPC's id
- [ ] Same call with a name absent from the world returns verdict `unmatched`
- [ ] `/review-step` then `/close-step` run clean

## Docs to update

No schema change, so no changelog entry. Add a short
`tooling/standards/ARCHITECTURE_DECISIONS.md` entry recording that the named
rungs are now shared between the day chain and the lore chantier, and that the
casting rungs are deliberately NOT shared because casting is play semantics.
CLAUDE.md gets no new invariant from this step.
