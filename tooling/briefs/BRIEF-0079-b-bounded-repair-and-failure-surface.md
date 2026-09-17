# BRIEF — Step "Bounded repair pass and failure surface"

## Context

TICKET-0079, second and last step; BRIEF-0079-a must be merged first. After -a,
the extractor no longer fuses across sentences, but a capitalised common noun
(`Dirigeants`, `Serviteurs`) still reports as an unauthorised name -- correctly,
under the precedent at `day_resolve.py:141-146`: the judge stays strict and the
fix belongs to the model. Today a failing verdict has no way out
(`detect_late_delta` cannot fire, per `day_narration.py:18-25`), so
`cockpit/routes/day.py:766` returns a bare 422 and the day is stuck.

This step does three things: re-anchors the naming rule in the narration prompt
so the model stops capitalising non-listed words (`B2b-2`, `R2`), adds one
bounded repair pass fed the exact offending words the judge already computed
(`C1a`, `P1`), and makes the 422 body structured (`D2`).

## Scope IN

1. **`src/world_engine/day_narration_guard.py` -- carry the offending words.**
   Add a field to `JudgeVerdict` (`:89-92`):

   ```
   offending_words: tuple[str, ...] = ()
   ```

   Defaulted, so every existing construction stays valid. The containment
   branch (`:178-182`) populates it with `tuple(sorted(unauthorised))`, the same
   list it already renders into `reason`. Every other `return JudgeVerdict(...)`
   in the module leaves it empty. The route must never parse `reason`.

2. **`scripts/seed_pilot.py` -- rewrite the naming rule
   (`B2b-2` + `R2`).** In `DAY_NARRATION_SYSTEM_PROMPT` (`:1855-1882`), replace
   the two bullets currently at `:1871-1877` with exactly these two, verbatim
   (line continuations to match the surrounding style):

   ```
   - Nomme les personnes et les lieux listes sous « Personnes nommables » et \
   « Lieux nommables », plus le personnage joueur lui-meme. La majuscule \
   initiale est reservee a ces noms et au premier mot de chaque phrase ; tout \
   autre mot s'ecrit en minuscules, y compris les groupes, les metiers, les \
   titres et les fonctions.
   - Pour toute personne ou tout lieu liste sous « Personnes et lieux sans nom \
   resolu », designe-le uniquement par sa fonction donnee.
   ```

   (Accents as in the surrounding file; the ASCII above is the shape, not the
   encoding.) Three properties this wording is chosen for, none of which may be
   "improved":
   - **No examples.** The removed `« le marchand », « la femme aux registres »,
     « le marche »` were a vocabulary reservoir tinting later narration. Do not
     reintroduce an example of any kind, in either bullet.
   - **Positive form only.** `N'invente aucun autre nom propre` and
     `jamais par un nom propre invente` are both removed; the typographic clause
     carries the same prohibition positively. `day_narration.py:7-8` records why
     negative form is worthless against the abliterated model.
   - **Forward-compatible with factions.** The rule is anchored on the nameable
     LIST, not on a word class, so when faction entities later join the fact
     sheet (deferred as `E2'`) a capitalised faction name becomes correct with
     no prompt change.

   Leave `_render_fact_sheet`'s code-built role-hint line
   (`day_narration.py:93-98`) as it is -- it says `en minuscules`, which the new
   rule agrees with.

3. **`scripts/seed_pilot.py` -- seed the repair prompt.** Add
   `DAY_NARRATION_REPAIR_SYSTEM_PROMPT` and `DAY_NARRATION_REPAIR_USER_TEMPLATE`
   next to the `day_rewrite` pair (`:1898-1924`), and one
   `upsert_prompt_template` row alongside `pt-day-rewrite` (`:2092+`) with
   `id="pt-day-narration-repair"`, `usage="day_narration_repair"`,
   `world_id=None`, `variables=["fact_sheet", "offending_words", "prior_prose"]`,
   `destination="local"`, and no `model=` (forbidden by
   `prompt_model_write.py`). System prompt, verbatim:

   ```
   Tu corriges une narration deja ecrite pour un jeu de role. Certains mots y \
   portent une majuscule alors qu'ils ne designent aucune personne ni aucun \
   lieu nommable. Ton travail : reecrire la narration en mettant ces mots en \
   minuscules.

   REGLES :
   - Ecris en minuscules chacun des mots listes sous « Mots a corriger », \
   partout ou il apparait.
   - Conserve le marqueur [REUSSITE]/[PARTIEL]/[ECHEC]/[BLOQUE] de chaque \
   etape, a l'identique.
   - Conserve les noms deja corrects, le deroule des faits et l'ordre des \
   etapes.
   - Ecris un francais correct.

   Reponds UNIQUEMENT avec le texte corrige de la narration, en francais, sans \
   preambule ni commentaire.
   ```

   User template, verbatim:

   ```
   {fact_sheet}

   Mots a corriger : {offending_words}

   Narration a corriger :
   {prior_prose}
   ```

4. **`src/world_engine/prompt_registry.py` -- register the usage.** Add a
   `day_narration_repair` entry mirroring `day_rewrite` (`:295-301`):
   `surface="play"`, `world_scoped=True`, `dry_run_capable=True`,
   `call_sites=("src/world_engine/day_narration.py:repair",)`,
   `default_model=_game_model`. `prompt_registry.py`'s bijection check requires
   seed and registry to agree; item 3 and this item ship together.

5. **`src/world_engine/day_narration.py` -- the repair call.** Add a
   module-level constant next to `MAX_REWRITE_ATTEMPTS` (`:46`):

   ```
   MAX_REPAIR_ATTEMPTS = 1
   ```

   with a comment stating that one repair fires per resolution and a judge
   failure after it is a stop, never a loop. Add:

   ```
   def repair(fact_sheet: FactSheet, prior_prose: str, offending_words: tuple[str, ...], db: Session) -> str:
   ```

   built on `rewrite`'s shape (`:128-154`): load via
   `_load_day_prose_template("day_narration_repair", fact_sheet.world_id, db)`,
   raise `LlmParseError` on a missing template with the same message shape,
   `current_prompt`, substitute `{fact_sheet}` with `_render_fact_sheet`,
   `{offending_words}` with `", ".join(offending_words)`, `{prior_prose}` with
   the prose, append `"\n/no_think"`, call `ollama_client.chat` with
   `effective_model(template, ollama_client.DEFAULT_MODEL)`, log at INFO with
   the offending words, return `raw.strip()`.

6. **`src/world_engine/cockpit/routes/day.py` -- wire one guarded attempt.** In
   `_narrate_and_judge` (`:707-740`), after the existing late-delta branch and
   its re-judge, add a final block: if the verdict has not passed AND
   `verdict.offending_words` is non-empty, call `repair` ONCE, re-judge, and
   return. `LlmParseError` is handled exactly as the two existing calls handle
   it (`db.rollback()`, then `HTTPException(502, ...)` with a
   `day narration repair failed: ...` detail). Exactly one `repair` call site
   in the function; no loop, no counter beyond the constant.

7. **`src/world_engine/cockpit/routes/day.py` -- structured 422 (`D2`).**
   Replace the `detail` string at `:766` with a dict:

   ```
   {
       "message": f"day narration rejected by judge: {verdict.reason}",
       "reason": verdict.reason,
       "offending_words": list(verdict.offending_words),
       "prose": prose,
   }
   ```

   The `history` append that precedes it (`:763-765`) is unchanged and still
   happens before the raise.

8. **Enumerate the consumers of that 422, then REPORT ONLY.** Find every caller
   of `POST /api/day/{batch_id}/resolve` in `src/` and `frontend/src/` and every
   place that renders the error `detail` from it. If any consumer renders
   `detail` as a string, do NOT fix it here -- list it in the execution notes
   with `file:line`. The Play surface is sealed behind TICKET-0069; touching it
   is out of scope even if it is the broken consumer.

9. **New rules in `tooling/verify/checks/day_narration.py`.** Continue the
   numbering from R18. Each fail-closed and vacuity-guarded (zero items located
   is a FAILURE):
   - **R19 (bounded repair).** `MAX_REPAIR_ATTEMPTS` is a module-level literal
     `1` in `day_narration.py`; `_narrate_and_judge` (falling back to
     `resolve_day`) contains exactly one call named `repair`, and at least one
     `ast.If` exists in the enclosing function. Mirror `check_bounded_rewrite`
     (`:248-313`) -- R6 counts `rewrite`/`day_rewrite` by name and would not
     see a call named `repair`, which is precisely why R19 is required.
   - **R20 (registry wiring).** `day_narration_repair` is a `PROMPT_REGISTRY`
     key and its `call_sites` names `repair` in `day_narration.py`. Extend the
     existing `check_registry_wiring` (`:394`).
   - **R21 (no reason parsing).** `JudgeVerdict` declares an `offending_words`
     field, and no `.split(`, `.replace(`, `re.` or subscript appears applied to
     `verdict.reason` anywhere in `cockpit/routes/day.py`.
   - **R22 (prompt hygiene).** `DAY_NARRATION_SYSTEM_PROMPT`'s source text in
     `scripts/seed_pilot.py` contains none of `le marchand`,
     `la femme aux registres`, `le marche`, `N'invente aucun autre nom propre`,
     or `jamais par un nom propre invente`.
   Add each to `main()` and extend the summary `PASS:` line.

## Scope OUT

- **The extractor.** `extract_names`, `_sentences`, `_strip_stopword_edges` and
  `day_name_extraction.py` are BRIEF-0079-a's. Do not touch them, and do not
  "also" widen what the extractor discards because the repair pass now exists.
- **`B1` / `B3`.** No determiner exemption, no deterministic de-capitalisation
  of the prose by code. Rejected in TICKET-0079 with a named reactivation
  condition (rejection after repair on more than 2 of 10 resolved days).
- **A second repair attempt, or a repair-of-the-repair.** One call, then the
  422. Do not add a retry counter, a loop, or a fallback to `rewrite`.
- **Repairing anything other than capitalisation.** The repair pass fires only
  when `offending_words` is non-empty. A band-marker failure
  (`_missing_band_markers`) and both anti-vacuity failures go straight to the
  422 as today.
- **`freeze_facts` and factions (`E1`).** `day_resolve.py:409-411`, `:413`.
  Deferred as `E2'`; reactivation condition recorded in TICKET-0079. Do not
  add a `factions` tuple, a `Groupes nommables` fact-sheet line, or faction
  names to `authorised_names`.
- **The Play surface.** `cockpit/` HTMX templates and the legacy page are sealed
  (TICKET-0069, paused). Item 8 is report-only.
- **Prompt text beyond items 2 and 3.** `day_rewrite`, `day_feasibility`,
  `day_plan`, `day_extract_*`, `day_reconcile` are untouched.
- **`_render_fact_sheet`.** Unchanged.

## Invariants to defend

- **R6 must stay green and must not be stretched.** R6 proves the REWRITE is
  bounded by counting calls named `rewrite`/`day_rewrite`. Adding a second model
  call named `repair` is invisible to it. Do not relax R6 to cover both -- add
  R19 as its own rule, so each pass carries its own bound.
- **Fail-closed narration (Scope IN item 4 of BRIEF-0075-d).** A judge failure
  after repair still stores nothing final and still raises. Do not let the
  repair pass become a way to store a rejected narration.
- **History is sacred.** `write_pass_play_resolution` appends; the rejected
  attempt and the repaired attempt each get their own `history` entry, and the
  rejected one is never overwritten. `pipeline.py:86-107` is unchanged.
- **Positive form only.** `day_narration.py:7-8`. Every prompt line added by
  items 2 and 3 must be an instruction to do something, not to avoid something.
- **No `model=` in seeded rows.** `prompt_model_write.py` (`:73-110`).
- **Module budgets.** `cockpit/routes/day.py` is 868 lines against a 1000-line
  cap -- items 6 and 7 add roughly 15. `_narrate_and_judge` is ~34 lines against
  an 80-line function cap. Put the repair logic in `day_narration.py` (180
  lines, ample headroom), never a helper in the route file.
- **Prompt/registry bijection.** `prompt_registry.py`'s check fails if items 3
  and 4 ship apart.

## Done means

- [ ] `python tooling/verify/checks/day_narration.py` exits 0, printing a
      summary line that names R19-R22.
- [ ] `python tooling/verify/checks/prompt_registry.py` exits 0.
- [ ] `python tooling/verify/checks/prompt_model_write.py` and
      `prompt_lean.py` exit 0.
- [ ] `python tooling/verify/checks/day_name_extraction.py` still exits 0.
- [ ] `python tooling/verify/run.py --ticket TICKET-0079` reports `green: true`.
- [ ] Live: reseed prompts, then resolve "Je veux apprendre les preferences de
      Lorian". A recit is returned and the day reaches `resolved`.
- [ ] Live: the resulting `pass_play.history` shows either one entry (no repair
      needed) or two (rejected, then repaired), the first intact.
- [ ] Live: the returned prose keeps the initial capital on `Lorian` and on the
      player character's name, and on the first word of every sentence.
- [ ] Live: force a rejection the repair cannot fix (temporarily remove
      `day_narration_repair`'s seeded row) and confirm the 422 body carries
      `offending_words` and `prose`. Restore the row afterwards.
- [ ] Execution notes list the 422 consumers found in item 8, with `file:line`,
      and state that none were modified.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `day_narration.py`'s module docstring -- add the repair pass alongside the
  rewrite pass, stating its trigger (`verdict.offending_words` non-empty), its
  bound, and that it is the only recovery path that can actually fire today.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- one appended entry covering:
  the naming rule re-anchored on the nameable list rather than a word class and
  why that survives the arrival of factions; the no-examples-in-system-prompts
  rule and its reason; the bounded repair pass and why it carries its own R19
  rather than extending R6; and the `E2'` deferral with its verifiable
  reactivation condition (a resolved day whose `declared_action` contains,
  case-insensitively, the `name` of an `entity` row with `type = 'faction'` in
  the active world).
- No schema change. `world-engine-schema.md` untouched, no version consumed --
  `prompt_template` rows are data, not schema.
