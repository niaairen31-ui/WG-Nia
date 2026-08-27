# BRIEF — Step "Proximity on-stop + « Parler » affordance (targeted join)"

Ticket: TICKET-0032 · Brief: BRIEF-0032-c · v1.00
Execution order: LAST — requires BRIEF-0032-a (endpoint contract:
`scene/join.target_gathering_id`) and BRIEF-0032-b (canvas state:
confirmed position, movement ticker, NPC list) both merged.

## Context

The canvas (0032-b) moves and draws; nothing gates dialogue on distance yet.
`POST /api/spatial/proximity` returns `{in_range:[{npc_id, name, distance}],
threshold}` against the same recomputed positions `presence` draws
(`routes/spatial.py:142-165`, threshold 2.0 m). Decision D1: ask on stop, not
while moving. Decisions G2-b/I1: "Parler" performs a deterministic
gathering-anchored join; cross-gathering clicks compose leave-then-join from
existing endpoints.

## Scope IN

All in the BRIEF-0032-b section of `src/world_engine/cockpit/index.html`.

1. **On-stop proximity (D1)**: fire `POST /api/spatial/proximity
   {location_id, position: confirmed}` (a) once after activation/spawn, and
   (b) 200 ms after movement ends (all movement keys up AND the final
   confirmed response received), debounced — a new keydown within the window
   cancels it. Never while moving. One in-flight request max. Clear the
   affordance list on every movement start.

2. **Affordance rendering**: a `<div id="spatial-actions">` under the canvas.
   For each `in_range` entry (already server-sorted by distance):
   `<button>Parler à {name}</button>` plus `({distance} m)`. Empty list ->
   verbatim: `Personne à portée de voix.` Also highlight in-range NPC circles
   (ring stroke) on the canvas — matching by `npc_id` from proximity against
   `id` from presence (known field-name divergence; map explicitly, comment
   it).

3. **Gathering resolution for a click**: from the scene response already held
   (`gatherings[].members[]`), map the clicked `npc_id` -> its `gathering_id`.
   If the NPC is in no open gathering (stale roster), re-fetch `/api/scene`
   once and retry the mapping; still absent -> status message
   `Ce personnage n'est plus disponible.` and refresh presence.

4. **Click flow — ungrouped player (G2-b)**:
   `POST /api/scene/join {target_gathering_id}` (no `player_text`). On
   `{conversation_id}` -> reuse the existing post-join transition verbatim
   (`loadConversations()` + `selectConv(id)`, as in `sceneJoin`,
   `index.html:1645-1650`).

5. **Click flow — grouped player (I1)**: read `scene.player_gathering`.
   - Target NPC in the SAME gathering: if `active_conversation_id` ->
     `selectConv(it)`; else reuse `_sceneResumeOrStart()`'s existing call.
   - Target NPC in ANOTHER gathering: `POST /api/scene/leave`, then the
     targeted join of §4. Sequential, awaited; if leave fails, stop and show
     the error (no join attempt).
   No confirmation dialog in either case (the affordance label is the
   intent).

6. **Post-join canvas state**: after entering a conversation the cockpit
   switches to the transcript view; on returning to the spatial tab the
   normal activation flow (0032-b §2/§8) re-fetches scene + presence — no
   special-casing here beyond verifying it happens.

## Scope OUT

- NO gating of `/say` or `conversations/start` server-side — the proximity
  gate stays advisory (G-A, `routes/spatial.py:149-151`); a distant NPC
  reachable through the old scene text view is ACCEPTED behavior this ticket.
- NO continuous proximity polling, no proximity during movement (D2
  rejected), no client-side distance pre-filter (D3 rejected).
- NO server-side migrate endpoint; I1 stays a client-side composition.
- NO earshot / overhearing mechanics (Tier 4, separate stream).
- NO change to the existing free-text join UI or the C2 picker.
- NO NPC position re-derivation after join/leave beyond the existing
  activation re-fetch (gathering rosters changing mid-view is next-chantier
  territory).

## Invariants to defend

- **Single spatial-distance authority**: the client never computes distance;
  in-range comes solely from the proximity endpoint (`placement.py:35-39` is
  the only site).
- **Advisory gate (G-A)**: do not "harden" the gate server-side in passing.
- **State-transition purity**: join/leave through existing endpoints only;
  no new write paths.

## Done means

- [ ] Live: stop within 2.0 m of an NPC -> button `Parler à {nom}` appears
      ~200 ms later with distance; their circle is highlighted; moving clears
      it; no proximity requests while keys are held (network tab).
- [ ] Live: stop out of range -> `Personne à portée de voix.`
- [ ] Live (ungrouped): click Parler -> conversation opens, anchored to the
      NPC's gathering; leave it, reload the scene text view -> « Reprendre la
      conversation » sees it.
- [ ] Live (grouped, same gathering): click Parler -> resumes/continues the
      existing conversation, no leave.
- [ ] Live (grouped, other gathering): click Parler -> current conversation
      closes (analyze_window ran — check log), player joins target, new
      conversation opens.
- [ ] Live: no Ollama call logged for any targeted-join click.
- [ ] `tooling/verify` suite green.
- [ ] /review-step and /close-step run.

## Docs to update

None new (the G2-b amendment entry ships with BRIEF-0032-a).
