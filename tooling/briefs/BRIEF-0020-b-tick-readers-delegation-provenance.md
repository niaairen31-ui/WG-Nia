# BRIEF — Step "tick readers, agenda_delegation, D1 provenance, F1 (BRIEF-0020-b-tick-readers-delegation-provenance)"

## Context

BRIEF-0020-a shipped the structure (goal_agenda_link, character
owners, cascade); nothing reads it yet — "no structure without a
reader" is settled HERE. The per-NPC tick call gains its own intrigue
(section + advancement + creation, a DELIBERATE, logged extension of
the 0017 per-NPC contract); the faction scope gains
`agenda_delegation`; dialogue goals gain D1-gated provenance; the
faction prompt gains the F1 posture anchor. Grounding: RECON on live
main (tick.py:302 frozenset; tick.py:192-221 T1 affiliation block;
context.py:131-158 choke-point; app.py:1354-1395 goal_change branch;
O1 note app.py:1380-1384). No migration — db_write only.

## Scope IN

1. **Per-NPC briefing — section `TON INTRIGUE` (tick.py, per-NPC
   assembler, after TES OBJECTIFS).** Query the single ACTIVE agenda
   with `owner_entity_id == npc_id` (at most one — 0020-a invariant).
   If present, render title + active step objective +
   `visibility_trace` + the most recent step outcomes, mirroring the
   AGENDA EN COURS composition (tick.py:462-520) but singular. If
   absent, omit the section entirely (no placeholder).

2. **Per-NPC goal provenance (tick briefing).** For each goal line in
   TES OBJECTIFS: if the goal has at least one ACTIVE link
   (`detached_at IS NULL`) to an ACTIVE agenda, append
   ` (sert : « <title> »)` — one suffix per linked agenda, comma-
   joined if several. FULL interiority: secret-faction agendas
   included — same T1 tier as the affiliation block directly above it
   (tick.py:192-221), which already prints secret rows. No gating in
   the TICK path.

3. **Per-NPC contract extension (tick.py).**
   - `_TICK_MUTATION_TYPES` (tick.py:302) gains `"agenda_step_change"`
     and `"agenda_creation"`. Update the frozenset's doc/comments AND
     the `_normalize_scope_event` docstring claim that these types are
     "FACTION SCOPE ONLY" — now: "faction scope, and the per-NPC path
     restricted to owner==npc (TICKET-0020, BRIEF-0020-b)".
   - Per-NPC calls now build their own `agendas_index`: name.casefold()
     -> id over ACTIVE agendas with `owner_entity_id == npc_id` ONLY
     (zero or one entry). The faction/scope indexes are untouched.
   - `_normalize_tick_item` gains two branches, mirroring the scope
     shapes (tick.py:615+):
     `agenda_step_change`: agenda referenced BY TITLE against the
     per-NPC agendas_index, payload `{action: complete|fail, outcome}`;
     step id stays code-derived at apply (unchanged branch). Unknown
     title or empty index -> drop with printed note.
     `agenda_creation`: title + 2-5 non-empty steps; `owner_entity_id`
     is FORCED to `npc_id` (H1/O1 forcing precedent, analyzer.py:398) —
     never read from the payload. CANON-EXISTENCE dedup (0014
     tick-guard doctrine): drop at normalize if the NPC already owns
     an ACTIVE agenda; at most ONE agenda_creation per per-NPC call
     (mirror the scope-level `agenda_creation_emitted` flag,
     tick.py:1263).
   - Approval-time duplicate guard (app.py:995-1011 block): for a
     character-owner `agenda_creation`, duplicate iff the owner
     already holds ANY active agenda (not just same-title) -> Needs
     attention. Faction-owner guard unchanged.

4. **`agenda_delegation` — new mutation type, FACTION SCOPE ONLY.**
   - `_normalize_scope_event`: accepted only when
     `scope_type == "faction"` (explicit gate, same as the two 0018
     types). Payload in: `{npc: <name>, goal: <text>, horizon?:
     short|long, agenda: <title>}`. Normalization: `npc` resolved
     against the scope roster EXCLUDING the faction's own id
     (tick.py:589-591 note — the faction id is appended to the
     faction roster); `agenda` resolved against the faction
     agendas_index; `horizon` lowercased, anything outside
     `{"short","long"}` (missing included) CLAMPED to `"short"` with
     a parse note. Empty goal text, unresolved npc, or unresolved
     agenda -> drop with note. Payload out: `{npc_id, goal, horizon,
     agenda_id}`.
   - Apply branch (`_apply_mutation`, app.py — place after the
     agenda_creation branch): re-validate at apply (stale-proof,
     canon-existence): the agenda is still ACTIVE; the NPC holds an
     ACTIVE FactionMembership (`left_at IS NULL`, secret OR public —
     a faction may task a secret member) in the agenda's owner
     faction; else return a one-line "Needs attention" reason.
     Duplicate guard: reuse the create_short duplicate rule
     (app.py:953-960) — an ACTIVE goal with the same normalized text
     on that NPC -> Needs attention. Then, atomically in the existing
     SAVEPOINT: `write_npc_goal(horizon=payload["horizon"],
     changed_by=f"mutation:{mut.id}")` +
     `write_goal_agenda_link(created_by=f"mutation:{mut.id}",
     mutation_id=mut.id)`. Same-domain parent-child aggregate — the
     0018 agenda_creation precedent, not a one-branch-one-table
     exception.
   - O1 relaxation is SCOPED: only this branch ever reads a horizon
     from a payload. `goal_change`/`create_short` stays hard-coded
     short — do not touch it.

5. **`goal_change` own-agenda reference (per-NPC path only).**
   - `_normalize_tick_item`, `create_short` shape: optional payload
     key `agenda` (title), resolved against the per-NPC (owner-only)
     agendas_index -> normalized payload gains `agenda_id`; unknown
     title -> the key is DROPPED with a note, the goal_change itself
     survives. The analyzer/conversation path is untouched — it never
     resolves nor forwards this key.
   - Apply branch (app.py:1380-1394): after `write_npc_goal`, if
     `payload.get("agenda_id")`, call `write_goal_agenda_link(...,
     created_by=f"mutation:{mut.id}")`; a ValueError from the link
     helper (e.g. agenda closed since proposal) returns Needs
     attention WITHOUT creating the goal (order: validate link
     preconditions before writing the goal, or rely on the SAVEPOINT
     rollback — executor picks the mechanically simpler, both are
     acceptable; state which in the commit message). `complete`/
     `abandon` ignore the key.

6. **D1 dialogue provenance (`src/world_engine/context.py`).**
   - New accessor `read_public_membership_faction_ids(entity_id,
     session) -> set[str]`, placed directly beside
     `read_public_memberships` (context.py:131): SAME structural
     WHERE triplet (`entity_id` match, `left_at IS NULL`,
     `is_secret == False`), returning faction ids. Docstring declares
     it the SECOND sanctioned reader of `faction_membership` for
     prompts, existing solely as the D1 provenance gate — no caller
     can opt into secret rows (no parameter exists).
   - Goal lines (context.py:226-242): for each injected goal with at
     least one ACTIVE link to an ACTIVE agenda, append
     ` (sert : « <title> »)` IFF the agenda's `owner_entity_id ==
     npc_id` (own intrigue) OR `owner_entity_id` is in
     `read_public_membership_faction_ids(npc_id, session)`. Links
     failing the gate render NOTHING — the goal appears bare, exactly
     as today. The gate is query/membership-mechanical; no model
     instruction anywhere.

7. **Prompt versions + delivery** (append-version branch, 0015/0016
   script shape; heads exist):
   - `pt-world-tick` (per-NPC): directives for TON INTRIGUE — the NPC
     may propose `agenda_step_change` (complete|fail + outcome) on
     ITS OWN intrigue when the briefing supports it, may propose AT
     MOST one `agenda_creation` (2-5 steps) ONLY if it has none, and
     may attach `"agenda": "<titre>"` to a `create_short` goal_change
     when the new goal serves its intrigue. French wording; executor
     drafts within these semantics; JSON shape examples mirror the
     scope-template style.
   - `pt-world-tick-events` (scope): document `agenda_delegation`
     (faction scope: npc + goal + horizon optionnel + agenda) with one
     French example, PLUS the F1 anchor, verbatim:
     "Toute nouvelle intrigue (agenda_creation) doit découler
     directement des Buts ou de l'Aversion de la faction tels
     qu'affichés dans ce briefing — jamais d'intrigue sans motivation
     posturale."
   - One script `apply_ticket_0020_prompt_updates.py`: appends one new
     version to EACH head, usage unchanged, re-run no-op.

8. **Docs**: `ARCHITECTURE_DECISIONS.md` two entries: (i) the per-NPC
   contract extension (frozenset grown, owner-restricted index,
   forced owner) as a logged evolution of 0017 — the exact wording of
   the old "FACTION SCOPE ONLY" claim it supersedes, quoted; (ii) the
   scoped O1 relaxation (horizon readable from agenda_delegation
   payloads only, clamp rule). CLAUDE.md: one line under the tick
   contract notes if it currently states the four-type per-NPC
   frozenset (check and update the count).

## Scope OUT

- Cockpit: no UI, no CRUD endpoint, no review-queue rendering polish
  (BRIEF-0020-c).
- No dialogue-context TON INTRIGUE section; no faction posture or
  visibility_trace in dialogue (F2, separate deferred brief).
- Analyzer/conversation path: no link resolution, no delegation, no
  agenda types — tick only.
- No delegation from the per-NPC scope; no cross-faction delegation.
- No changes to cascade, link helpers, or owner rules (0020-a is
  closed structure).
- No seed data changes.

## Invariants to defend

- **Structural MJ exclusion / secrets**: the D1 gate must be
  query-mechanical via the new accessor — never an instruction, never
  a parameterized opt-in. The tick's full-provenance rendering is the
  EXISTING T1 exception's tier, not a new one.
- **Model proposes, code judges**: step identity stays code-derived;
  owner_entity_id forced; horizon clamped; membership re-validated at
  apply.
- **0014 tick-guard doctrine**: all dedup/dup guards are
  canon-existence checks (owner has an active agenda; active goal with
  same text) — never proposal-id equality.
- **Single canon-write paths**: delegation and link attachment go
  through writes.py helpers inside the existing SAVEPOINT pattern.

## Done means

- [ ] `apply_ticket_0020_prompt_updates.py` appends one version to
      each of the two heads; re-run no-ops; cockpit prompt preview
      shows the new texts (fidelity: exactly as sent).
- [ ] Per-NPC tick for an NPC owning an intrigue: briefing contains
      TON INTRIGUE + goal provenance suffixes (secret-faction links
      INCLUDED); an `agenda_step_change` complete on its own intrigue
      round-trips the queue and advances the step.
- [ ] Per-NPC tick for an NPC with NO intrigue: an `agenda_creation`
      proposal applies (agenda born active, owner forced to the NPC);
      on the NEXT tick a further creation is dropped at normalize
      (log note) and a stale queued one hits Needs attention.
- [ ] Faction tick: `agenda_delegation` proposed on a member;
      approval creates goal (payload horizon respected; a bogus
      horizon clamps to short with a parse note) + active link;
      non-member npc name in a hand-forged payload -> Needs attention.
- [ ] Dialogue, secret member with a linked goal: goal line bare;
      same setup public member: `(sert : « ... »)` present; NPC's own
      intrigue link: present regardless of memberships.
- [ ] Location-scoped tick: `agenda_delegation` impossible (drop
      note), regression: agenda types still absent.
- [ ] `verify/checks/world_tick.py` extended per the ticket's
      machine-checkable criteria; `npc_goal_read.py` covers the D1
      gate; full suite green: `tooling/verify/run.py`.
- [ ] /review-step and /close-step run.

## Docs to update

Covered in Scope IN item 8 (ARCHITECTURE_DECISIONS x2, CLAUDE.md tick
contract count if stated). Schema doc untouched — no schema change in
this brief.
