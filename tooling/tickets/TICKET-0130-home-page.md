---
id: TICKET-0130
slug: home-page
title: A home page at / chooses the creator's cockpit or the player's shell; the launcher opens it on request; Claude Code's preview stays on the test database
type: feature
status: live-gate
created: 2026-11-14
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
lot_id: LOT-0130-home-page.md
brief_ids: [A]
current_brief: A
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je n'ai nul part pour ouvrir le coté joueur de mon application. Comment
> me propose tu d'ajouter cela ?

> A2-a, assure toi que je peux ouvrir cela a partir de mon bouton, je ne
> veux pas chercher. H1.

> O1, mais lorsque claude code ouvre, je veux qu'il continue a ouvrir la
> BD de test

"Mon bouton" is `start-prod.cmd` on Nia's desktop (outside the repo, R-12):
it starts the cockpit in prod and opens no browser.

## Clarifications resolved (intake)

- The player shell already exists and is served at `/jouer` (TICKET-0125,
  R-01); what is missing is a door to it. Decision 10 of TICKET-0125 (no
  link to `/jouer` from the cockpit) is superseded by A2-a.
- The server binds `127.0.0.1` only (R-09): neither the home page nor
  `/jouer` is reachable from another device. No authentication is added
  (A1' of the player series: Nia alone on her machine).
- Claude Code's preview is `.claude/launch.json` (port 8001), which does
  not run `scripts/cockpit.py` and today sets no database (R-11).

## Decisions locked (do not re-litigate without Nia)

- A2-a -- `/` serves a third page, `accueil.html`, its own Vite input; `/`
  leaves the creator shell (`_SHELL_ROUTES` and `router.js`). The creator
  shell is reached at `/play`. Rejected: A1, a link in the cockpit header
  (reactivation: none, superseded by A2); A2-b, the home page as a
  surface of the creator shell (the player's door would live in the
  creator bundle); A3, a bookmark outside the app.
- H1 -- the home page holds the tool's name and two links, « Créatrice »
  (`/play`) and « Joueur » (`/jouer`), and nothing else: no script, no
  call. Profile choice stays in `/jouer`. Rejected: H2, the player
  profiles listed on the home page (reactivation: Nia asks for one click
  less).
- B1 -- no link from `/jouer` to the cockpit or to the home page.
- O1 -- `scripts/cockpit.py --ouvrir` opens the default browser on
  `http://127.0.0.1:8000/` once the server accepts connections; without
  the flag nothing opens. `start-prod.cmd` gains `--ouvrir` -- edited by
  Claude (chat) on Nia's machine after the merge, with her yes, never by
  a brief. Rejected: O2, always open (every Claude Code launch would open
  a tab); O3, `start` in the `.cmd` (opens before the server is ready).
- P1 -- Claude Code's preview (`.claude/launch.json`) sets
  `WORLD_ENGINE_ENV=test` itself, so it opens the test database whatever
  the shell it inherits.

## Carried forward / open

- `WORLD_ENGINE_DATABASE_URL` still overrides `WORLD_ENGINE_ENV` (R-10),
  including from a `.env` file read by `load_dotenv`. P1 does not defend
  against an override Nia sets herself; no ticket unless she wants one.
- No link from the creator shell back to the home page. Reactivation: Nia
  asks for one.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `/` serves `accueil.html` with `cache-control`; `/` is not a shell
      route; `/play` still is  -> verify/checks/home_page.py
- [ ] `accueil.html` holds the two links and no script; the build carries
      it  -> verify/checks/home_page.py
- [ ] `--ouvrir` opens once when the port answers, never when it does not,
      and only under the flag  -> verify/checks/home_page.py
- [ ] `.claude/launch.json` sets `WORLD_ENGINE_ENV` to `test` before the
      app is imported  -> verify/checks/home_page.py
- [ ] `legacy_mount.py`, `static_asset_freshness.py`, `player_shell.py`,
      `frontend_build_fresh.py`, `file_map.py`, `claude_md_contract.py`
      stay green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] 1. After Claude adds `--ouvrir` to `start-prod.cmd`: one double-click
      starts the cockpit and opens the browser on the home page.
- [ ] 2. « Créatrice » opens the cockpit on Play; every tab works as before.
- [ ] 3. « Joueur » opens the player shell on its profile choice.
- [ ] 4. Claude Code's preview (port 8001) shows the test database's
      worlds, not prod's.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
