# BRIEF — Step "Link-agent frontend on the NPC graph panel" (BRIEF-0036-d)

Ticket: TICKET-0036. Anchored on RECON-0036. Requires 0036-a/b/c landed.

## Context

The whole backend flow (staging, pair pass, coherence, patches, commit)
is live and curl-testable. This step gives it its creator UI, attached
to the existing NPC relation graph panel (#creation-npc-relgraph,
index.html:1267 area) -- no new creation tab.

## Pre-exec verification (report, then proceed or stop)

- #creation-npc-relgraph panel and its head bar still exist with the
  Global/Lier controls (index.html:1267-1281 area at RECON time).
- page_contract check: confirm the panel is inside the existing NPC tab
  registration; this brief must not touch CREATION_TABS.
- All 0036-a/b/c endpoints respond on a live cockpit.
If any anchor fails: STOP, report, no code.

## Scope IN

All frontend work in cockpit/index.html, vanilla JS + fetch, same style
as the existing relgraph functions (relGraph* namespace; new functions
prefixed linkAgent*).

1. Launcher: a "Agent liens" button in the relgraph head bar. Opens an
   inline panel (same visual family as the graph panel, below the head):
   - Location multi-select: checkbox list of the world's locations
     rendered as an indented hierarchy (parent_location_id); checking a
     parent auto-checks its descendants (S1 visual mirror; the SERVER
     expansion from 0036-a remains the authority -- the UI sends only
     the checked root ids the user actually clicked).
   - "Prévisualiser" -> POST /api/link-batches/preview -> displays
     "{N} PNJ, {P} paires, {P} appels au modèle" + roster names.
   - "Lancer" (enabled only after a preview) -> POST /api/link-batches
     then starts the run loop. 409 (already an open batch) -> offer to
     open the existing batch instead.

2. Run loop: sequential fetch of POST run-next until {done:true};
   progress line "paire {pairs_done}/{pairs_total}" updated per
   response; a "Pause" button stops the loop client-side (batch stays
   open; "Reprendre" restarts the loop -- resume semantics are server
   truth from 0036-b). A 502 (parse error) shows the failing pair and a
   "Réessayer" button; the loop does not silently continue past it.

3. Review surface, rendered from GET /api/link-batches/{id}:
   - Grouped by pair. Relation rows: type, direction, intensity,
     visible_to_b, notes -- editable inline (same clamps client-side,
     server re-validates via PATCH). Knowledge rows: holder name, level,
     content, source, is_incorrect/is_secret/share_threshold badges --
     editable likewise. no_links rows render as "Aucun lien proposé"
     (distinct, non-error styling).
   - Per-row "Rejeter" (PATCH row_status='rejected', struck-through,
     reversible while open).
   - NEW endpoint required: PATCH /api/link-batches/{id}/rows/{row_id}
     accepting {payload} and/or {row_status} -- add it to
     routes/link_agent.py with the same payload validation as 0036-b
     clamps (this is the one backend addition of this brief; it edits
     STAGING only, strata check must stay green).

4. Coherence block: "Passe de cohérence" button -> POST coherence ->
   render findings list: problem, rationale, target (pair or canon row,
   named), source badge (code/model), and -- ONLY for
   validation='valid' unapplied findings -- an "Appliquer" button ->
   POST apply -> re-render (staged target rows refresh; canon patches
   show a "canon modifié" badge). validation='rejected' findings render
   greyed with their reason. coherence_status='partial' renders a
   visible warning banner "Graphe canon tronqué -- passe partielle".

5. Commit: "Committer le lot" button (disabled until coherence_status
   is 'ran' or 'partial', mirroring the server 409) -> POST commit ->
   shows per-row result incl. skipped F1-conflicts -> triggers
   relGraph reload so the new edges appear immediately in the global
   graph.

6. Reopen path: on cockpit load, if GET /api/link-batches returns an
   open batch, the "Agent liens" button carries a dot badge; clicking
   it opens directly on the review surface of that batch with
   "Reprendre" available if pairs remain.

## Scope OUT

- No new creation tab, no CREATION_TABS change, no cytoscape work on the
  graph itself beyond the existing relGraph reload call.
- No websocket/SSE progress; the sequential fetch loop is the contract.
- No client-side persistence (no browser storage of any kind); server
  state is the only state.
- No bulk-apply of findings; no editing of canon rows from the review
  table (canon changes happen only through valid finding patches).
- No styling pass beyond the existing panel's visual family.
- No mobile layout work.

## Invariants to defend

- json_ui_boundary check: the new endpoints/UI exchange stays within the
  allow-listed boundary conventions; extend the named allow-list if the
  check requires it, never bypass it.
- Model proposes, code judges, creator decides: every button that
  mutates (apply, commit, reject) maps 1:1 to a server-validated
  endpoint; the UI never computes a decision.
- index.html is already 10k+ lines: keep additions in one contiguous,
  commented block per concern (styles / markup / JS), matching existing
  panel conventions, to keep future extraction possible.

## Done means

- [ ] Full happy path in a live session: select a parent location (its
      children auto-check), preview shows correct counts, launch, watch
      progress, pause, resume, review rows, edit one, reject one, run
      coherence, apply one valid patch, commit; new edges visible in the
      global graph without reload.
- [ ] Parse-error pair: loop halts on the failing pair with Réessayer;
      retry after template fix completes the batch.
- [ ] Rejected finding renders greyed with reason and no button.
- [ ] Close the cockpit mid-run; reopen: badge present, batch resumes.
- [ ] Commit disabled before coherence; enabled after; skipped
      F1-conflict (seed one during review) reported in the result.
- [ ] page_contract, json_ui_boundary, link_agent_strata, full verify
      suite green; /review-step and /close-step run.

## Docs to update

- ARCHITECTURE_DECISIONS.md: close the 0036 record -- UI contract
  (valid-findings-only buttons, server-truth resume, commit gate).
- CLAUDE.md: nothing expected; report if the contract check disagrees.
- This brief closes TICKET-0036; ticket status -> done after live gate.
