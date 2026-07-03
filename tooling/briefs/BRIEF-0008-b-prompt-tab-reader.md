<!-- slug: prompt-tab-reader -->
# BRIEF-0008-b — Prompts tab (read-only): API, master list, raw + assembled previews

Ticket: TICKET-0008. Depends on: BRIEF-0008-a executed and merged.
**Re-anchoring note:** all `file:line` anchors below cite the RECON-0008
*result* against the pre-(-a) tree; -a adds `prompt_registry.py`, the verify
check, and touches `model=` lines in `entity_author.py` / `region_author.py`
/ `analyzer.py` / `gathering.py` / `cockpit/app.py`. Re-anchor against the
post-(-a) tree before editing; the cited functions and structures are the
stable reference, not the line numbers.

## Context

The reader that justifies -a's structure: a read-only cockpit tab showing,
one prompt at a time, what is actually sent to the local models — effective
template per usage, effective model (`template.model ??` registry default),
static call sites, and previews. Locked decisions implemented here: D1
(lazy master list + one detail at a time), C3 (raw preview default,
assembled dry-run preview only for `dry_run_capable` usages), R1 (effective
row computed per the usage's real resolution semantics via the registry's
`world_scoped` flag), E1 (standard shell, `primaryAction: null`),
`destination` **omitted** from the tab entirely (no reader in code —
displaying it would show a routing promise the code does not keep).

## Scope IN

1. **`GET /api/prompts`** (in `cockpit/crud.py`, read-only): returns usages
   grouped, each with:
   - registry facts: `surface`, `world_scoped`, `dry_run_capable`,
     `default_model` (live value), `call_sites`
   - DB rows for the usage: `id`, `name`, `world_id`, `version`,
     `is_active`, `model` (the override column, NULL today)
   - `effective_id`: computed by replicating the real loader semantics
     per R1 — `world_scoped=True`: active rows, world-specific for the
     active world preferred, else global (the `app.py:1307-1311` chain);
     `world_scoped=False`: first active row in the same order the
     authoring loaders' `.first()` returns (replicate, don't idealize; the
     latent nondeterminism with 2+ active rows is an accepted observation,
     not fixed here)
   - `effective_model`: `row.model ?? registry default` for the effective
     row
   No `system_prompt`/`user_template` bodies in the list payload (lazy —
   the person's requirement: only the selected prompt is ever rendered).

2. **`GET /api/prompts/{id}`** (read-only): full detail for one row —
   `system_prompt`, `user_template`, `variables`, `notes`, `version`,
   `is_active`, `world_id`, `model`, `effective_model`, registry facts for
   its usage, and flags `is_effective` / `shadowed_by` (id of the row that
   wins resolution, when this one loses).

3. **Assembled preview endpoints** (C3, both read-only, **zero model
   calls, zero writes** — no `conversation` row, no `injected_context`
   snapshot, no `change_history`):
   - `GET /api/prompts/preview/npc_dialogue?npc_id=&pc_id=` — location
     defaults to the NPC's `current_location_id`. Builds the exact system
     prompt the real conversation-start path would build from the
     effective template + `assemble_npc_context(npc_id, pc_id,
     location_id, db)`.
   - `GET /api/prompts/preview/player_narration?pc_id=` — location
     defaults to the PC's `current_location_id`; effective template +
     `assemble_mj_context(...)`.
   **Fidelity rule:** the preview must reuse the same construction the
   live path uses. If the live construction is inline today, extract it
   into a pure behavior-preserving helper called by BOTH the live path and
   the preview (extraction limited to prompt-string assembly; no logic
   change, no reordering). Never duplicate the construction — a duplicated
   preview drifts.

4. **Cockpit tab** (`cockpit/index.html`): new `prompts` entry in
   `CREATION_TABS` (registry at index.html:3009), standard shell,
   `primaryAction: null` (read-only precedent: `artefacts` :3091, `queue`
   :3107). UI:
   - Master list grouped by usage, sub-grouped Play / Création
     (`surface`), one line per row: name, version, `is_active`,
     world/global badge, **effectif** badge on the winning row, effective
     model badge
   - Selecting a row lazy-loads the detail panel (`GET
     /api/prompts/{id}`): metadata, call sites list, raw preview =
     `system_prompt` + `user_template` with `{tokens}` highlighted
     (regex-scan the template text for `{...}` tokens; also list the
     declared `variables` JSON, flagging tokens present in text but absent
     from `variables` and vice versa — declared/actual drift made visible,
     display-only)
   - For `dry_run_capable` usages only: entity selector(s) (NPC +
     interlocutor PC for `npc_dialogue`; PC for `player_narration`) + a
     "Preview assemblée" action rendering the real assembled prompt
   - `destination` appears nowhere in the tab
   - No client-side persistence of selection state (consistent with the
     cockpit's no-draft-persistence doctrine)

5. **Verify check extension** — `tooling/verify/checks/page_contract.py`:
   append `"prompts"` to `TAB_KEYS` (array at :11-14 pre-(-a)); the new
   entry must satisfy the existing contract shape with
   `primaryAction: null`.

## Scope OUT (named)

- Any write path: no editing of `model`, templates, `is_active`, nothing —
  the tab is read-only end to end
- `destination` display or cleanup (fate deferred to the write-path
  chantier)
- Assembled previews for any usage beyond the two `dry_run_capable` ones
  (a new preview requires its assembler to exist first; adding one is a
  future registry-flag flip + selector, not an architecture change)
- Promotion of Python-built context blocks to first-class objects (they
  are visible *through* the assembled previews only)
- B2 invocation journal; category defaults; loader consolidation;
  `.first()` determinism fix (all carried over from -a)

## Invariants to defend

- **Read-only end to end.** No `_apply_mutation`, no `change_history`, no
  canon write, no conversation/session row, no snapshot — including from
  the preview endpoints. The preview is a dry-run in the strictest sense.
- **Structural secret exclusion traverses the preview intact.** The
  assembled previews call the real `assemble_npc_context` /
  `assemble_mj_context` (context.py:134 / :373 pre-(-a)) — never a
  reimplementation. Therefore `knowledge.is_secret` rows, other entities'
  knowledge, `character.secrets`, `internal_name`, `is_public=FALSE`
  entities, and secret/rumor events are excluded by the same query
  construction as live play. The preview adds NO new query beside the
  assembler's own.
- **Displayed truth = executed truth.** Effective row per `world_scoped`
  (real loader semantics), effective model via the same
  `effective_model()` the call sites use, call sites from the verified
  registry. Nothing shown is computed by a rule the code doesn't run.
- **Active-world scoping at the chokepoint:** `GET /api/prompts` scopes
  its world-specific logic on `_world_id(db)` exactly like the other crud
  endpoints. (Global `world_id=NULL` templates are legitimately visible —
  they are config, not another world's canon.)
- **Creator surface, not player surface:** the tab may show template text
  wholesale (creator's own management surface, same reasoning as the Lieux
  browse showing non-public entities) — but assembled previews still show
  only what the assemblers emit, because fidelity, not secrecy, demands it.

## Done-means checklist

- [ ] `python tooling/verify/run.py` passes (page_contract extended,
      prompt_registry from -a still green)
- [ ] Live (Nia): onglet Prompts — liste groupée Play/Création, badge
      « effectif » correct pour le monde actif, un seul détail chargé à la
      fois (vérifiable au réseau : aucun body de template dans la liste)
- [ ] Live: modèle effectif conforme — `llama3.1:8b` sur un usage
      authoring, modèle de jeu sur un usage play
- [ ] Live: preview brute d'un usage arbitraire — tokens surlignés, drift
      variables déclarées/réelles visible si présent
- [ ] Live (critique): preview assemblée `npc_dialogue` sur un NPC réel
      porteur d'un secret (`knowledge.is_secret`) et d'un `cover_role` —
      le prompt rendu ne contient ni le secret, ni `character.secrets`,
      ni `internal_name`; le rôle affiché est le `cover_role`
- [ ] Live: preview assemblée `player_narration` — contexte MJ rendu,
      mêmes exclusions, le savoir propre du PJ (y compris ses propres
      rows `is_secret`) présent (frontière MJ, pas frontière NPC)
- [ ] Live: call sites affichés exacts par sondage sur 2 usages
- [ ] Aucune écriture DB constatée après une session complète dans
      l'onglet (previews incluses)

## Docs to update

- `ARCHITECTURE_DECISIONS.md` (append-only): the tab as the registry's
  reader; C3 hybrid preview doctrine ("a new prompt costs one registry
  line, not a preview path"); the fidelity rule (previews reuse live
  construction, never duplicate); `destination` omission rationale.
- `CLAUDE.md`: one line if the prompt-construction extraction (Scope IN 3)
  creates a shared helper — name it as the single construction path.
