# BRIEF — Step "Prompt lean rewrite: resolved facts over conditional instructions, pilot purge"

Ticket: TICKET-0012 · Brief: BRIEF-0012-a · Executes strictly after TICKET-0011 (closed).

## Context

Live prompts carry instructions the code could resolve (the 5-tier affinity
table), blocks irrelevant to most NPCs (pricing rules for non-sellers), a
factually wrong universal paragraph (allegiance denial contradicting TES
AFFILIATIONS), pilot-world names inside `world_id=NULL` templates, forced
magic vocabulary injected by the assemblers into every world, and a developer
sync note sent to the model. All decisions are locked (A1, B1, C1, D3, E1,
F1, G1, H2 — see TICKET-0012). TICKET-0011's versioning machinery is live:
seed never touches text on existing heads (S2), so rewrites reach the live DB
as new `prompt_version` rows through `write_prompt_version` and reach virgin
DBs as seed v1 — both paths, same text.

All anchors below are against `main` post-TICKET-0011 (verified 2026-07-06).

## Scope IN

### 1. `src/world_engine/context.py` — affinity tier resolver (A1 + H2)

Add, near `NEUTRAL_INTENSITY` (`context.py:57`), the tier resolution — code
is the single authority for tier boundaries:

```python
# Affinity tiers (TICKET-0012, A1/H2): resolved in code, never by the model.
# The prompt-side 5-tier table was removed from NPC_DIALOGUE_SYSTEM_PROMPT;
# these boundaries and texts are the sole authority.
_AFFINITY_TIERS = (
    # (upper_bound_exclusive, adjective, directive)
    (30, "hostile",
     "Ton attitude envers cette personne : hostile ou méprisante. "
     "Interaction minimale, ton sec ; tu peux refuser d'échanger ou la renvoyer."),
    (50, "méfiante",
     "Ton attitude envers cette personne : méfiante. Laconique ; tu ne donnes "
     "que ce qui est manifestement public ; tu peux marchander "
     "(« qu'est-ce que j'y gagne ? ») plutôt que de partager de bon cœur."),
    (60, "neutre",
     "Ton attitude envers cette personne : discrétion ordinaire. Poli ; tu "
     "parles de choses banales ; tu deviens évasif si l'on insiste sur un "
     "sujet sensible ; tu ne vas pas de toi-même au-delà des banalités."),
    (76, "chaleureuse",
     "Ton attitude envers cette personne : chaleureuse. Tu partages si l'on "
     "te le demande, tout en gardant une réserve sur les sujets délicats."),
    (101, "confiante",
     "Ton attitude envers cette personne : confiante. Tu offres spontanément "
     "des choses que tu tairais à un inconnu, sans qu'on ait à te pousser."),
)


def _affinity_tier(intensity: int) -> tuple[str, str]:
    """(adjective, directive) for an intensity 1-100. Code-side authority."""
    for upper, adjective, directive in _AFFINITY_TIERS:
        if intensity < upper:
            return adjective, directive
    return _AFFINITY_TIERS[-1][1], _AFFINITY_TIERS[-1][2]
```

Boundaries formalized from the removed table: `<30` hostile, `30-49`
méfiante, `50-59` neutre, `60-75` chaleureuse, `>75` confiante.

### 2. `context.py` — perception rendering (A1 + H2, no raw numbers)

`_render_perception` (`context.py:88-92`) currently renders
`"intensité {n}/100"`. Replace with the H2 adjective — the numeric intensity
never appears in any fiche:

```python
def _render_perception(name: str, rel: Relation) -> str:
    adjective, _ = _affinity_tier(rel.intensity)
    return (
        f"- {name} : {rel.notes} "
        f"(perception : {rel.type}, disposition : {adjective})"
    )
```

In `assemble_npc_context`, section 4 (`context.py:260-268`): after the
interlocutor's perception line (or the "un visage de plus" sentence for the
no-relation case), append ONE directive line resolved from the already
computed `intensity` (`context.py:234` — covers the neutral-50 default the
prompt used to explain):

```python
_, directive = _affinity_tier(intensity)
perception_lines.append("  " + directive)
```

The directive is emitted for the interlocutor only — other perceived people
get the adjective via `_render_perception`, never a directive (H2).

### 3. `context.py` — pricing rules relocated (B1)

In the `pricing_section` construction (`context.py:336-341`), after the
tariff lines and inside the same `price_list` branch, append this text
verbatim (the injection condition replaces the old "si tu vends" framing):

```
RÈGLES DE TARIFICATION :
- Tes prix affichés ci-dessus sont FERMES et identiques pour tout le monde :
tu les énonces tels quels, sans marchander.
- Pour une chose qui n'est PAS dans tes tarifs (objet rare, service
inhabituel, faveur), tu proposes toi-même un prix, en te servant de tes
tarifs comme ÉCHELLE de référence : reste dans le même ordre de grandeur, ne
lance pas un nombre absurde. Tu peux laisser ta relation avec la personne
l'influencer — plus bas pour quelqu'un que tu apprécies, plus haut pour
quelqu'un dont tu te méfies. Annonce UN seul prix (pas de marchandage en
va-et-vient pour l'instant).
- Tu ne vends que ce que tu possèdes ou peux raisonnablement fournir ; tu
n'inventes pas un stock que tu n'as pas.
- Les montants sont dans la monnaie du lieu.
```

This text must exist in exactly ONE place in the codebase (this branch).

### 4. `context.py` — magic ambience removed structurally (D3)

- Delete the `atmo` block in `assemble_npc_context` (`context.py:204-213`):
  the `"L'atmosphère y est magiquement « … »"` line and the
  `magic_phenomena` read feeding it. The `values` subculture line
  (`context.py:215-217`) STAYS — independent, non-magical.
- `_SAFE_SUBCULTURE_KEYS` (`context.py:61`) becomes `("values",)`. This
  structurally removes `magic_phenomena` / `nexus_link` from
  `assemble_mj_context` (`context.py:432-438`) and from the
  `pt-mj-establishment` ambiance join (`cockpit/app.py:1792`,
  `1825-1830`) — no instruction-level guard, the data is simply absent.
- Do NOT rename or drop any column; `location.magic_status` and subculture
  keys remain stored — they just no longer reach any prompt.

### 5. `scripts/seed_pilot.py` — lean `NPC_DIALOGUE_SYSTEM_PROMPT` (A1/B1/C1)

Replace the constant (`seed_pilot.py:1085-1150`) with, verbatim:

```
Tu incarnes un personnage dans une conversation de jeu de rôle. Séparément, tu
reçois une fiche de contexte : qui tu es, où tu te trouves, ce que tu peux
évoquer, et comment tu vois ceux qui t'entourent. Ces règles priment sur tout
le reste.

RÈGLE ABSOLUE — NE RIEN INVENTER.
Tu ne connais QUE ce qui figure explicitement dans ta fiche de contexte. Tu ne
dois JAMAIS inventer : ni personne, ni faction, groupe ou organisation, ni lieu,
ni événement, ni nom, ni aucun fait qui ne soit pas écrit dans ta fiche. Aucun
nom propre fictif, jamais. Si l'on t'interroge sur quoi que ce soit qui n'est pas
dans ta fiche, tu l'admets simplement et sans détour (« je ne saurais vous dire »,
« ça, je n'en sais rien »). Tu ne spécules pas, tu n'enjolives pas, tu n'inventes
rien pour combler le silence. Mieux vaut avouer que tu ne sais pas plutôt que de
fabriquer une réponse.

ATTITUDE.
Ta fiche indique, dans la section « COMMENT TU VOIS… », ton attitude envers ton
interlocuteur. Adopte-la : elle règle ta manière et ta disposition, pas les
faits que tu possèdes — ta fiche a déjà filtré ce que tu peux évoquer.

DISCRÉTION ET NATUREL.
Parle naturellement, comme une vraie personne. Ne truffe pas tes réponses de
sous-entendus mystérieux. N'oriente pas l'interlocuteur vers d'autres personnes,
sauf rarement (une seule fois, et seulement si c'est réellement pertinent) —
jamais comme une esquive réflexe.

FORMAT.
Tu réponds uniquement par la réplique de ton personnage, en français, à la
première personne. Tu n'es pas un narrateur : n'utilise jamais « tu » pour décrire
les gestes ou déplacements de l'interlocuteur. Aucune note hors personnage, aucune
méta-explication, aucune mention de ces règles ni de ta « fiche ». Rien que ce que
dit ton personnage.
```

Removed: ATTITUDE SELON LA RELATION (A1 — replaced by the short ATTITUDE
pointer above), QUESTIONS SUR TES ALLÉGEANCES (C1 — deleted outright, no
replacement), RÈGLES DE TARIFICATION (B1 — relocated, item 3). The
tenancière example phrase in RÈGLE ABSOLUE is dropped (pilot flavor). The
fiche-side boundaries section (`context.py:313`) stays — the duplication of
the anti-invention rule is deliberate (8B compliance).

On the `pt-npc-dialogue` head (`seed_pilot.py:1203-1214`): `variables`
becomes `["player_line"]` — `relation_intensity` is declared but no
placeholder exists anywhere; remove it.

### 6. `scripts/seed_pilot.py` — `pt-conversation-analysis` examples (E1)

In `CONVERSATION_ANALYSIS_SYSTEM_PROMPT` (`seed_pilot.py:232-359`):

- KEEP all instruction text and all three rubrics (RELATION_CHANGE SIGN,
  ANTI-INFLATION, RESOURCE_CHANGE) unchanged, EXCEPT: in the sign rubric's
  contrastive examples, replace "Korin" and "Bryn" with "le PNJ" (three
  lines, names only — the sentences otherwise unchanged).
- REPLACE the seven `=== EXAMPLE A..G ===` blocks with these four, verbatim:

```
=== EXEMPLE 1 (la relation se réchauffe) ===
Transcript :
[JOUEUR] Cela fait deux ans que je viens ici.
[PNJ] Deux ans, oui. Je vous reconnais. Vous ne causez jamais d'ennuis. J'apprécie.
Output:
[{"mutation_type":"relation_change","target_table":"relation","target_id":"rel-a-player","payload":{"entity_a_id":"npc-a","entity_b_id":"char-player","relation_type":"passive_attention","intensity_delta":6},"rationale":"Le PNJ a explicitement reconnu le joueur et l'a évalué positivement — la confiance se réchauffe."}]

=== EXEMPLE 2 (le joueur apprend un fait) ===
Transcript :
[JOUEUR] On dit que des voyageurs disparaissent sur la route ?
[PNJ] On le dit, oui. Les patrouilles ont doublé depuis un mois. Personne ne sait pourquoi.
Output:
[{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","subject":"disparitions_route","level":"rumor","content":"Le PNJ confirme des rumeurs de disparitions et un doublement des patrouilles depuis un mois.","source":"conversation avec le PNJ"},"rationale":"Le PNJ a directement confirmé la rumeur — le joueur dispose maintenant d'une corroboration externe."}]

=== EXEMPLE 3 (fenêtre multi-tours, échange banal → rien à enregistrer) ===
Transcript :
[JOUEUR] Bonsoir.
[PNJ] Bonsoir.
[JOUEUR] Une chambre pour la nuit, c'est possible ?
[PNJ] Bien sûr. Deuxième porte à gauche.
[JOUEUR] Merci, c'est aimable.
[PNJ] C'est mon métier, mais je vous en prie.
Output:
[]

=== EXEMPLE 4 (le joueur achète une information à prix convenu) ===
Transcript :
[JOUEUR] Je te donne 15 pièces pour ce que tu sais sur le Conseil.
[PNJ] Quinze, d'accord. Le Conseil cache l'un de ses propres membres.
[JOUEUR] Tiens.
[PNJ] Plaisir de faire affaire.
Output:
[{"mutation_type":"resource_change","target_table":"ledger","target_id":null,"payload":{"entity_id":"char-player","amount":-15,"counterparty_id":"npc-b","reason":"achat d'une information sur le Conseil","knowledge":{"entity_id":"char-player","subject":"conseil_secret","level":"rumor","content":"Le Conseil cache l'un de ses propres membres.","source":"acheté au PNJ","is_secret":false}},"rationale":"Le joueur a payé 15 pièces, le PNJ a énoncé le prix et l'information, l'échange s'est conclu dans la scène."}]
```

The `=== EXAMPLE E ===` inn-room content is absorbed by EXEMPLE 3;
A/C collapse into EXEMPLE 1; F/G into EXEMPLE 4. The English instruction
body of this prompt is NOT translated (see Scope OUT).

### 7. `scripts/seed_pilot.py` — `pt-mj-narration` example neutralized (E1)

In `MJ_NARRATION_SYSTEM_PROMPT` (`seed_pilot.py:403-`): every occurrence of
"Maelis" becomes "Mira", "Reike" becomes "un client au fond de la salle"
(adjusting the example's closing clause to "Elle jette un regard vers un
client, au fond de la salle."), and "Le Dernier Verre est mon domaine"
becomes "Cette taverne est mon domaine". The RÈGLE 2 correct/interdit
mini-examples (`:~397`) switch "Maelis" → "Mira". Example mechanics
(verbatim speech preservation, first→third person conversion) unchanged.

### 8. `scripts/seed_pilot.py` — `pt-mj-interpretation` example neutralized (E1)

At `seed_pilot.py:~555` ("les deux près du feu », « Maelis et Korin », …"):
replace "« Maelis et Korin »" with "« la patronne et le garde »". Nothing
else in this template changes.

### 9. `scripts/seed_pilot.py` — sync note out of the model text (F1)

In `REGION_MANIFEST_SYSTEM_PROMPT` (`seed_pilot.py:973-974`): delete the
parenthesis line "(Ces deux valeurs — 4 et 4 — doivent rester synchronisées
avec MIN_NPCS_PER_FACTION / MIN_FACTIONLESS dans region_author.py,
BRIEF-40.)". Add directly above the constant's assignment, as a Python
comment:

```python
# The two "au moins 4" minimums inside this prompt MUST stay in sync with
# MIN_NPCS_PER_FACTION / MIN_FACTIONLESS in region_author.py (BRIEF-40).
```

The density floor itself (both "au moins 4" rules) stays in the prompt.

### 10. `scripts/apply_ticket_0012_prompt_rewrite.py` — live-DB delivery (G1/S2)

New one-shot, idempotent script (sibling of the migration scripts). For each
touched head — `pt-npc-dialogue`, `pt-conversation-analysis`,
`pt-mj-narration`, `pt-mj-interpretation`, `pt-region-manifest` — it:

1. imports the rewritten constants from `scripts/seed_pilot.py` (single
   source of text — the script embeds NO prompt text of its own);
2. reads the head's current text via `prompt_store.current_prompt`;
3. if `(system_prompt, user_template)` already equals the seed constants →
   prints "unchanged", writes nothing;
4. otherwise calls `writes.write_prompt_version(note="TICKET-0012 lean
   rewrite")` — the single write shape; C1 validation applies as everywhere;
5. prints a summary (head id, old→new version number or "unchanged").

Run order on the live DB: `python scripts/seed_pilot.py` first (converges
head fields — the narrowed `variables` — without touching text, per S2),
then this script (text as new versions).

### 11. `tooling/verify/checks/prompt_lean.py` — new deterministic check

Static assertions (imports the seed module's constants and reads
`context.py` source; no DB):

- `NPC_DIALOGUE_SYSTEM_PROMPT` contains none of: `"ATTITUDE SELON LA
  RELATION"`, `"RÈGLES DE TARIFICATION"`, `"QUESTIONS SUR TES ALLÉGEANCES"`.
- No seed prompt constant (`*_SYSTEM_PROMPT`, `*_USER_TEMPLATE` module-level
  names) contains, case-insensitively: `maelis`, `reike`, `senna`, `korin`,
  `bryn`, `dernier verre`, `verkhaal`.
- `context.py` source contains no `"magiquement"`; `_SAFE_SUBCULTURE_KEYS ==
  ("values",)`; `"_affinity_tier"` is defined and referenced inside
  `assemble_npc_context`.
- `"RÈGLES DE TARIFICATION"` appears exactly once in `context.py` and zero
  times in `seed_pilot.py`.
- `CONVERSATION_ANALYSIS_SYSTEM_PROMPT` contains exactly 4 `"=== EXEMPLE"`
  markers, zero `"=== EXAMPLE"` markers, and all three rubric headers
  (`"SIGN RUBRIC"`, `"ANTI-INFLATION RUBRIC"`, `"RESOURCE_CHANGE RUBRIC"`).
- `REGION_MANIFEST_SYSTEM_PROMPT` contains neither `"synchronis"` nor
  `"BRIEF-"`, and contains `"au moins 4"` twice.

Wire it into the harness the same way the existing checks are registered
(`tooling/verify/run.py`).

## Scope OUT

- **Creator editability of tier texts** — `_AFFINITY_TIERS` are code
  constants; no template, no cockpit surface for them. Named deferral
  (TICKET-0012, drafting decision 1).
- **Tier adjectives in the MJ context** — H2 applies to the NPC fiche only;
  `assemble_mj_context` perception data is untouched beyond D3.
- **Translating the English instruction body of `pt-conversation-analysis`**
  — only transcripts and example content go French (E1 as locked); the
  working English rubric/instruction prose is not rewritten in this step.
- **Any schema change** — no DDL, no migration, no changelog version bump.
  `location.magic_status`, subculture keys, and `prompt_template.variables`
  columns all keep their shape; only row values / injected text change.
- **`pt-mj-establishment` template text** — its `{subculture}` input is
  narrowed by the `_SAFE_SUBCULTURE_KEYS` change; the template itself is
  not edited.
- **Deleting or renaming pilot world DATA** (Verkhaal entities, Maelis &
  co. as seed rows) — the purge targets universal `world_id=NULL` prompt
  texts only.
- **Renaming `resource_change` or any `mutation_type`** — closed vocabulary
  parsed by `analyzer.py` / `_apply_mutation`.
- **Further example reduction or prompt-length optimization** beyond the
  locked items — no freelance trimming of other templates
  (`pt-mj-arbiter`, `pt-mj-initiative`, generation templates…).
- **Prompt cockpit UI changes** — 0011-b shipped; nothing UI here.
- **B2 (model/variables versioning)** — untouched, still deferred from 0011.

## Invariants to defend

- **Two sanctioned canon-write paths / single prompt write shape** — the
  delivery script must write ONLY through `writes.write_prompt_version`
  (`writes.py:522`); never a direct `PromptVersion` insert.
  `tooling/verify/checks/` scans must stay green.
- **History is sacred** — no existing `prompt_version` row is edited or
  deleted; rewrites are appended versions. The seed's S2 guarantee
  (`seed_pilot.py:126-158`) must survive untouched.
- **Secrets excluded structurally** — the `_SAFE_SUBCULTURE_KEYS` narrowing
  and the atmo-block deletion REDUCE what assemblers read; verify no change
  widens any assembler query (`assemble_npc_context` /
  `assemble_mj_context` secret exclusions unchanged).
- **G1 (0011) accessor discipline** — the delivery script reads current
  text via `prompt_store.current_prompt` only.
- **Minimal first** — the tier resolver ships with its two concrete readers
  (directive line + `_render_perception`); no config table, no per-world
  tier overrides.

## Done means

- [ ] `python tooling/verify/run.py` green, including the new
      `prompt_lean.py` check.
- [ ] `grep -i magiquement src/world_engine/context.py` returns nothing.
- [ ] Cockpit prompt preview (`/api/prompts/preview/npc_dialogue`) for a
      NON-seller NPC contains no "RÈGLES DE TARIFICATION"; for a seller NPC
      (with `price_list`), tariffs and rules appear together.
- [ ] The same preview shows, for the interlocutor, one "Ton attitude
      envers cette personne : …" directive and NO "intensité …/100"
      anywhere; other perceived people carry "disposition : <adjectif>".
- [ ] `python scripts/seed_pilot.py` then
      `python scripts/apply_ticket_0012_prompt_rewrite.py` on the live DB:
      summary shows one new version per touched head; a second run of the
      apply script prints "unchanged" for all five heads.
- [ ] Cockpit prompt history for `pt-npc-dialogue` shows the new version as
      current with the full prior text intact as the previous version.
- [ ] Live test, low-intensity (<30) vs high-intensity (>75) NPC: clearly
      distinct dispositions in dialogue (live gate, Nia).
- [ ] Live test, several MJ narrations/establishments in a location with
      `magic_phenomena` set: no magic ambience volunteered (live gate, Nia).
- [ ] Live test, NPC with a public affiliation asked "pour qui
      travailles-tu ?": answer consistent with TES AFFILIATIONS, no
      reflexive denial (live gate, Nia).
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append a "PROMPT LEAN REWRITE — resolved
  facts over conditional instructions (TICKET-0012, BRIEF-0012-a)" section
  recording A1/B1/C1/D3/E1/F1/H2, the tier-boundary formalization, the
  `_SAFE_SUBCULTURE_KEYS` narrowing, and the named deferral (tier-text
  editability).
- `CLAUDE.md`: one line under the prompt conventions: affinity tiers are
  resolved in code (`context.py::_affinity_tier`); prompt templates never
  carry the tier table. (Respect the line budget — one line.)
- No schema changelog entry — no DDL in this step.

---

**Drafting decisions embedded (flag for creator review before deposit):**

1. **D3 extended to all three injection points** — the locked decision named
   "the assembler"; RECON showed `_SAFE_SUBCULTURE_KEYS` also feeds
   `assemble_mj_context` and `pt-mj-establishment`'s ambiance. Narrowing the
   allow-list to `("values",)` is the structural version of your intent
   ("le modèle parle toujours de magie dans l'ambiance") — reverse by
   keeping the tuple unchanged if you want NPC-fiche-only removal.
2. **Exact tier boundaries** `<30 / 30-49 / 50-59 / 60-75 / >75` formalized
   from the old table's fuzzy wording ("de 30 à 50", "autour de 50").
3. **Directive and adjective wording** derived nearly verbatim from the
   deleted table; adjectives feminine-agreeing with "personne/disposition".
4. **English instruction body of conversation-analysis kept** — only
   examples/transcripts localized; full translation named in Scope OUT.
5. **`pt-npc-dialogue.variables` narrowed to `["player_line"]`** — the
   declared-but-unused `relation_intensity` is removed.
6. **Delivery = idempotent script importing seed constants** — single
   source of text, single write shape, seed-then-script run order.
7. **Anti-invention duplication kept deliberately** (system prompt + fiche
   boundaries) — repetition aids 8B compliance; not part of locked scope.
