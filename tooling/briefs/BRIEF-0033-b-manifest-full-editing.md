# BRIEF — Step "Manifest checkpoint: full editing" (BRIEF-0033-b)

## Context

The Phase-A manifest checkpoint (`regionRenderManifest`, `index.html:5853`)
currently edits ONLY one-liners; names are read-only, the concept is a
frozen heading, and rows cannot be added or removed. The concept is reused
in every Phase-B composite brief (`region_author.py:242, 256, 269`) and the
top-up (`:343`), so editing it is meaningful. Locked decision A1: everything
editable. Phase B already re-normalizes the incoming manifest server-side
(dedup, root/parent resolution, NPC placement — `generate_region_draft`
docstring: the manifest is advisory), so free client-side editing is safe by
construction. Frontend-only step.

## Scope IN

1. `regionRenderManifest` (`index.html:5853`): the concept heading becomes
   a `<textarea>` (rows=3, full width) with
   `oninput="regionManifest.concept = this.value"`.
2. Faction rows: the name `<div>` becomes an `<input>` writing
   `regionManifest.factions[i].name`; keep the one-liner textarea as-is.
   Add a per-row remove button (btn-icon, label `x`, title "Retirer") that
   splices `regionManifest.factions[i]` and re-renders. Add a section-level
   "+ Ajouter une faction" button pushing
   `{ name: '', one_liner: '' }` and re-rendering.
3. Location rows: name becomes an `<input>` writing
   `regionManifest.locations[i].name`. Replace the static "(racine / sous
   X)" hint with two controls: an `is_root` checkbox (label "racine";
   checking it sets `is_root = true` and `parent_name = null`; at most a
   visual hint, no client-side uniqueness enforcement — the server
   re-resolves the root) and a parent `<select>` (options: `--` plus every
   OTHER location's current name; writes `parent_name`; disabled when
   `is_root` is checked). Per-row remove button; "+ Ajouter un lieu" pushes
   `{ name: '', one_liner: '', is_root: false, parent_name: null }`.
4. NPC rows: name becomes an `<input>` writing
   `regionManifest.npcs[i].name`. Replace the static "(lieu · faction)"
   hint with two `<select>`s: `location_name` (options: every location's
   current name — REQUIRED, no empty option once locations exist) and
   `faction_name` (options: `--` = null plus every faction's current
   name). Per-row remove; "+ Ajouter un PNJ" pushes
   `{ name: '', one_liner: '', location_name: <first location's name or
   ''>, faction_name: null }`.
5. Selects are rebuilt from current names on every re-render. A name edit
   does NOT live-sync already-selected `parent_name` / `location_name` /
   `faction_name` strings; render each select with the stored value
   injected as its selected option even if no longer matching a row (the
   server notes/nulls unresolved names in Phase B — this is the existing
   contract, keep it). Re-render the whole section on add/remove only, not
   on each keystroke (oninput mutates state directly, no re-render).
6. `regionBuild()` (`index.html:5916`): before POSTing, filter out
   factions/locations/NPCs whose `name` is empty after trim (mirrors the
   server's drop-nameless posture), and abort with a status message
   "Chaque entree doit avoir un nom" ONLY if a non-empty one-liner exists
   on a nameless row (protects real typed content from silent loss).

## Scope OUT

- No backend change: `/api/regions/manifest` and `/api/regions/generate`
  bodies unchanged; `_normalize_manifest` untouched.
- No client-side validation duplicating server normalization (dedup, root
  uniqueness, parent cycles): server stays the judge.
- No editing of the review screen (BRIEF-0033-c) or graphs (-d, -e).
- No manifest persistence: it remains client-held state, lost on
  "Recommencer" — unchanged contract.
- No NPC-floor UI (MIN_NPCS_PER_FACTION stays a server-side top-up
  concern; removing NPCs below the floor simply yields the existing
  server note).

## Invariants to defend

- Model proposes, code judges: the manifest stays advisory; Phase B
  re-normalization is the sole authority. Nothing in this step trusts
  client edits beyond forwarding them.
- No structure without a reader: no new fields are added to the manifest
  shape — only existing keys become editable.

## Done means

- [ ] Live: edit the concept, rename a faction, add a location under a
      chosen parent, remove an NPC, add an NPC placed in an existing
      location with no faction -> "Generer les fiches" -> the review
      reflects every edit (renamed faction appears; removed NPC absent;
      added entities drafted; concept text visible as the review heading
      and influencing drafts).
- [ ] Live: an added row left nameless with an empty one-liner is silently
      dropped at build; a nameless row WITH a one-liner blocks the build
      with the status message.
- [ ] `/review-step` and `/close-step` run.
- [ ] All verify checks pass (frontend rules advisory, H1).

## Docs to update

- ARCHITECTURE_DECISIONS.md, TICKET-0033 section: A1 recorded — manifest
  checkpoint fully editable; server-side re-normalization remains the
  single judge; nameless-row handling as specified.
