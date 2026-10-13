<!-- slug: dashboard-registry -->
# BRIEF 0115-D — "The dashboard is a registry in code -- dashboard_metrics.py, dashboard_deferrals.py, dashboard_export.py, GET /api/dashboard[/export] (no schema change)"

Lot: LOT-0115-creator-dashboard.md (authoritative on conflict)
Depends on: BRIEF-0115-C (C-03), BRIEF-0115-B (C-02)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after the previous brief of this lot).

- `src/world_engine/cockpit/app.py` -> `from .routes import event_types as _routes_event_types` and `app.include_router(_routes_event_types.router)`, the last router
- `src/world_engine/conditions.py` -> `def and_path_leaves(node: Optional[ConditionTree]) -> tuple[RequirementSpec, ...]:`
- `src/world_engine/models/pipeline.py` -> `ConditionDraft` with `outcome`, `saved_as_proposed`, `world_ref`, `created_at`; `SkillResolution` with `verdict` in `('base','matched','unmatched')`
- `src/world_engine/proposal_producers.py` -> `def producer_label(` (BRIEF-0115-C)
- Each of the 20 anchors of `DEFERRALS` (in the diff) is found once in its file -- `dashboard_registry.py` DB1 checks it; a miss is a STOP, never an edit of the anchor.
- No `dashboard_*.py`, no `cockpit/routes/dashboard.py`, no `tooling/verify/checks/dashboard_registry.py`.

## Facts carried

### R-05 — the JSON boundary [M]
Opened: `tooling/verify/checks/json_ui_boundary.py` (:46-47 the payload, « First structured UI consumer must relationalize »; :119 `ConditionDraft.payload`, « the rate reads the relational `outcome` and `saved_as_proposed` »); `writes/condition_drafts.py:49` (`PAYLOAD_KEYS`); `condition_interpreter.py:118` (the « coût », « forme inexistante » kinds live only in the notes' text).
Consequence (M1): the metrics read relational columns only; IA2, A2 and the missing label are `metric: export`.

### R-06 — the relational sources [M]
Opened: `models/pipeline.py:455` (`ConditionDraft`), `models/config.py:166` (`ConditionNode`), `models/ephemeral.py:170` (`Rencontre`), `SkillResolution`; `cockpit/routes/day.py:303` (the day's NPC, Q1).

### R-08 — the deferral candidates [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md` and the tickets 0111-0119; Nia kept 20 (the lot's table); each anchor matched once on `main`.

## Contracts

### C-04 — the dashboard's routes
Produced by: BRIEF-0115-D   Consumed by: E
`GET /api/dashboard?world=all|<id>&since=YYYY-MM-DD&until=YYYY-MM-DD` -> `{worlds, scope, metrics: [{key, title, question, watches, dated, note, rows: [{group, label, value, of}]}], deferrals: [{code, ticket, deferred, condition, source, metric, status, follow_up}]}`; `GET /api/dashboard/export` (same query) -> an attachment, JSON `{format: "wg-nia-dashboard-export/1", exported_at, scope, proposals, interpreter, metrics, deferrals}`. 422 on a bad date, `since` after `until`, an unknown world. Days on the cockpit's own clock, both included.

## Context

H1, E2, F2, M1 of the dashboard: the metrics and the deferral registry are code; the tab (E) only shows them. The export carries what the tab may not read (the JSON columns) for an analysis in Claude Code.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `dashboard_metrics.py` (new): `Scope`, `METRICS` (ten), `compute_metrics`, `world_names`;
   - `dashboard_deferrals.py` (new): `DEFERRALS` (Nia's 20), `EXPORT`, `deferral_dicts`;
   - `dashboard_export.py` (new): `build_export`;
   - `cockpit/routes/dashboard.py` (new, C-04), registered in `cockpit/app.py`;
   - creates check `dashboard_registry.py` (DB1-DB5); appends the decision entry above the footer.
   The files it touches, exactly:
   - src/world_engine/cockpit/app.py
   - src/world_engine/cockpit/routes/dashboard.py
   - src/world_engine/dashboard_deferrals.py
   - src/world_engine/dashboard_export.py
   - src/world_engine/dashboard_metrics.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/dashboard_registry.py

````diff
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index 4c79b49..d1eea71 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -60,6 +60,7 @@ from .routes import creator as _routes_creator
 from .routes import day as _routes_day
 from .routes import debts as _routes_debts
 from .routes import event_types as _routes_event_types
+from .routes import dashboard as _routes_dashboard
 from .routes import link_agent as _routes_link_agent
 from .routes import lore as _routes_lore
 from .routes import lore_mentions as _routes_lore_mentions
@@ -148,6 +149,7 @@ app.include_router(_routes_conditions.router)
 app.include_router(_routes_debts.router)
 app.include_router(_routes_attributes.router)
 app.include_router(_routes_event_types.router)
+app.include_router(_routes_dashboard.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/dashboard.py b/src/world_engine/cockpit/routes/dashboard.py
new file mode 100644
index 0000000..f9d8232
--- /dev/null
+++ b/src/world_engine/cockpit/routes/dashboard.py
@@ -0,0 +1,83 @@
+"""The « Suivi » tab's routes -- the creator's dashboard and its export (TICKET-0115, BRIEF-0115-D; decisions H1, E2, I1, J1 and M1 of the conditions series' dashboard). Reads only:
+
+    GET /api/dashboard          `{worlds, scope, metrics, deferrals}`:
+                                every metric of `dashboard_metrics.METRICS`
+                                and the deferral registry
+    GET /api/dashboard/export   the same scope as one JSON file to save
+                                (`dashboard_export.build_export`)
+
+Query: `world` -- `all` (default) or one world's id (J1); `since`, `until`
+-- real-world dates `YYYY-MM-DD` on the cockpit's own clock, both days
+included, either may be left out (the timestamps are stored in UTC). A date that does not parse, `since` after `until`, or an unknown world
+answers 422.
+"""
+
+from __future__ import annotations
+
+import json
+from datetime import UTC, date, datetime, time, timedelta
+from typing import Optional
+
+from fastapi import APIRouter, Depends, HTTPException, Query
+from fastapi.responses import Response
+from sqlmodel import Session
+
+from ...dashboard_deferrals import deferral_dicts
+from ...dashboard_export import build_export
+from ...dashboard_metrics import Scope, compute_metrics, world_names
+from ...db import get_session
+
+router = APIRouter()
+ALL_WORLDS = "all"
+
+
+def _day(raw: Optional[str], name: str) -> Optional[date]:
+    if raw in (None, ""):
+        return None
+    try:
+        return date.fromisoformat(raw)
+    except ValueError as exc:
+        raise HTTPException(status_code=422, detail=f"{name} : date invalide {raw!r} (AAAA-MM-JJ)") from exc
+
+
+def _utc(day: date) -> datetime:
+    """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
+    naive UTC the timestamps are stored in."""
+    return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)
+
+
+def scope_of(db: Session, world: str, since: Optional[str], until: Optional[str]) -> Scope:
+    """The scope a query names (see the module docstring)."""
+    first, last = _day(since, "since"), _day(until, "until")
+    if first is not None and last is not None and first > last:
+        raise HTTPException(status_code=422, detail="« du » est après « au ».")
+    names = world_names(db)
+    if world != ALL_WORLDS and world not in names:
+        raise HTTPException(status_code=422, detail=f"monde inconnu {world!r}")
+    return Scope(
+        world_ids=None if world == ALL_WORLDS else (world,),
+        since=_utc(first) if first is not None else None,
+        until=_utc(last + timedelta(days=1)) if last is not None else None,
+    )
+
+
+@router.get("/api/dashboard")
+def dashboard(world: str = Query(ALL_WORLDS), since: Optional[str] = Query(None),
+              until: Optional[str] = Query(None), db: Session = Depends(get_session)) -> dict:
+    scope = scope_of(db, world, since, until)
+    return {
+        "worlds": [{"id": w, "name": n} for w, n in sorted(world_names(db).items(), key=lambda p: p[1])],
+        "scope": {"world": world, "since": since or None, "until": until or None},
+        "metrics": compute_metrics(db, scope),
+        "deferrals": deferral_dicts(),
+    }
+
+
+@router.get("/api/dashboard/export")
+def dashboard_export(world: str = Query(ALL_WORLDS), since: Optional[str] = Query(None),
+                     until: Optional[str] = Query(None), db: Session = Depends(get_session)) -> Response:
+    scope = scope_of(db, world, since, until)
+    body = json.dumps(build_export(db, scope), ensure_ascii=False, indent=2, default=str)
+    name = f"suivi-{world if world == ALL_WORLDS else 'monde'}-{since or 'debut'}-{until or 'fin'}.json"
+    return Response(content=body, media_type="application/json",
+                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
diff --git a/src/world_engine/dashboard_deferrals.py b/src/world_engine/dashboard_deferrals.py
new file mode 100644
index 0000000..8fe0d80
--- /dev/null
+++ b/src/world_engine/dashboard_deferrals.py
@@ -0,0 +1,161 @@
+"""The deferrals the creator watches: each rejected or deferred choice whose reactivation condition she approved, where it is declared, and the dashboard metric that watches it, if any (TICKET-0115, BRIEF-0115-D; decisions F2, K2 and L of the conditions series' dashboard).
+
+`DEFERRALS` is written by hand, entry by entry, from the choices Nia named
+(L): a deferral enters this list only when a ticket's lot names it, never
+by a scan of the decision registry. Each entry carries:
+
+- `code`, `ticket`: the decision code and the ticket that locked it;
+- `deferred_fr`, `condition_fr`: what waits, and when it comes back, in
+  French for the « Suivi » tab;
+- `source`, `anchor`: the file that declares it and a verbatim passage of
+  it -- `dashboard_registry.py` (the check) finds the anchor there once, so
+  a reworded or moved declaration is a red gate, never a stale line;
+- `metric`: the key of the `dashboard_metrics.METRICS` entry that watches
+  the condition, `EXPORT` when only the export can measure it (M1: the tab
+  reads no JSON column), or None when no data can;
+- `status`: `open`, or `reached` -- the condition is met and the decision
+  is Nia's -- with `follow_up`, the ticket reserved for it, if any.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+EXPORT = "export"
+DEFERRAL_STATUSES: tuple[str, ...] = ("open", "reached")
+
+
+@dataclass(frozen=True)
+class Deferral:
+    code: str
+    ticket: str
+    deferred_fr: str
+    condition_fr: str
+    source: str
+    anchor: str
+    metric: Optional[str] = None
+    status: str = "open"
+    follow_up: Optional[str] = None
+
+
+_T0111 = "tooling/tickets/TICKET-0111-condition-language.md"
+_T0112 = "tooling/tickets/TICKET-0112-condition-interpreter.md"
+_T0113 = "tooling/tickets/TICKET-0113-world-state.md"
+_T0114 = "tooling/tickets/TICKET-0114-event-journal.md"
+_T0119 = "tooling/tickets/TICKET-0119-event-producers.md"
+_DECISIONS = "tooling/standards/ARCHITECTURE_DECISIONS.md"
+_JSON_BOUNDARY = "tooling/verify/checks/json_ui_boundary.py"
+
+DEFERRALS: tuple[Deferral, ...] = (
+    Deferral("D2", "TICKET-0111",
+             "Appliquer d'office les événements proposés par le MJ.",
+             "Le taux d'acceptation tel quel des événements proposés est assez haut.",
+             _T0111, "D2 (auto-applied; reactivation: an acceptance rate measured high enough under D1)",
+             metric="event_reviews"),
+    Deferral("M2", "TICKET-0111",
+             "Une étape s'accomplit seule quand sa condition d'accomplissement est vraie.",
+             "Le tableau de bord montre que Nia confirme ce que la condition dit déjà.",
+             _T0111, "M2 (completing on its own; reactivation: a dashboard metric showing Nia confirms what "
+                     "the condition already says)",
+             metric="step_verdicts"),
+    Deferral("A1", "TICKET-0119",
+             "Le tick propose de nouveaux types d'événements.",
+             "Nia retype souvent les événements proposés par le tick.",
+             _T0119, "Reactivation: the dashboard (0115) shows the creator retyping the tick's domain-typed "
+                     "events often.",
+             metric="tick_retyped"),
+    Deferral("Q2", "TICKET-0111",
+             "Des champs explicites pour le PNJ de journée et les faits à approfondir.",
+             "Une étape dont le PNJ de journée n'est la cible d'aucune relation atteinte par « toutes ».",
+             _T0111, "Q2 (explicit step fields; reactivation: a step whose day's NPC is not the target of a "
+                     "relation)",
+             metric="steps_without_day_npc"),
+    Deferral("absence", "TICKET-0114",
+             "Une forme dédiée « sans être repéré ».",
+             "Le tableau de bord montre le besoin : beaucoup de « non » sur un événement.",
+             _T0114, "a dedicated form only if the dashboard shows the need.",
+             metric="absence_leaves"),
+    Deferral("A2", "TICKET-0111",
+             "Des conditions écrites en SQL généré.",
+             "Une condition réelle que l'arbre ne peut pas exprimer, même avec une nouvelle primitive.",
+             _T0111, "A2 (generated SQL; reactivation: a real condition the tree cannot express even with a "
+                     "new primitive)",
+             metric=EXPORT),
+    Deferral("F2", "TICKET-0111",
+             "Une table « acte » à côté du journal d'événements.",
+             "Un ralentissement mesuré de la chronique par le volume des traces.",
+             _T0111, "F2 (a second table « acte »; reactivation: a measured slowdown of the chronicle by the "
+                     "volume of traces)"),
+    Deferral("IA2", "TICKET-0112",
+             "L'interprète traduit aussi les coûts et les récompenses.",
+             "Le journal de l'interprète montre Nia tapant des coûts dans l'interprète.",
+             _T0112, "IA2 (terms too: a second judge; reactivation: the journal shows the creator typing costs "
+                     "into the interpreter)",
+             metric=EXPORT),
+    Deferral("ID1b", "TICKET-0112",
+             "Les offres de quête dans l'index des noms.",
+             "Une offre de quête devient une entité.",
+             _T0112, "ID1b (offers and skills in `name_index`; reactivation: a quest offer becomes an entity)"),
+    Deferral("libellé", "TICKET-0113",
+             "Ajouter depuis l'interprète un libellé qui manque à un état existant.",
+             "Des propositions refusées parce que l'état existant n'a pas le libellé.",
+             _T0113, "Reactivation: `condition_draft` rows whose `errors` name « n'est pas un libellé de ».",
+             metric=EXPORT),
+    Deferral("effets/sorte", "TICKET-0119",
+             "Un effet qui vise une sorte (« les loups de Brume sont enragés »).",
+             "Un type dont l'effet vise un rôle qui accepte une sorte, et Nia qui le demande.",
+             _T0119, "Reactivation: a type whose effect targets a role that accepts a sorte, and the creator "
+                     "asking for it."),
+    Deferral("WH3", "TICKET-0113",
+             "Un état visible lisible par un joueur sur les autres.",
+             "Le journal d'événements sait qui a été témoin d'un changement.",
+             _T0113, "WH2, WH3 (reactivation: TICKET-0114's journal knows who witnessed a change).",
+             status="reached", follow_up="TICKET-0122"),
+    Deferral("payload", "TICKET-0025",
+             "Rendre relationnel le payload d'une proposition.",
+             "Une interface le lit champ par champ : la carte de revue l'édite depuis TICKET-0119.",
+             _JSON_BOUNDARY, "First structured UI consumer must relationalize.",
+             status="reached"),
+    Deferral("A1'b", "TICKET-0104",
+             "Limiter `rencontre` aux paires de personnages.",
+             "Une mesure de prod ne montre aucune paire `rencontre` hors deux personnages.",
+             _DECISIONS, "Reactivates if a production measurement shows no `rencontre` pair involving anything "
+                         "but two characters.",
+             metric="rencontre_pairs"),
+    Deferral("P2", "TICKET-0101",
+             "Faire passer toute écriture de lieu par `write_character_location`.",
+             "Un septième site d'écriture apparaît (le contrôle (c) de `zone_placement.py` échoue).",
+             _DECISIONS, "Reactivates when a seventh write site appears (`zone_placement.py` (c) fails on it)."),
+    Deferral("C3b", "TICKET-0084",
+             "Alias, recherche approchée ou normalisation pour le lexique d'actions.",
+             "Le nombre de formes non reconnues distinctes dépasse le seuil que Nia fixe.",
+             _DECISIONS, "**C3b reactivation condition, made measurable.**",
+             metric="lexicon_gaps"),
+    Deferral("A2 (îlots)", "TICKET-0088",
+             "Un deuxième registre d'îlots de Création.",
+             "Le premier brief qui doit retirer une entrée de `CREATION_ISLANDS`.",
+             _DECISIONS, "reactivate at the first brief that must remove an entry from `CREATION_ISLANDS`."),
+    Deferral("A3 (îlots)", "TICKET-0088",
+             "Retirer les règles 2 et 7 de `creation_island.py`.",
+             "`legacy.html` est absent et `LEGACY_MOUNTS` est vide.",
+             _DECISIONS, "reactivate when `legacy.html` is absent **and** `frontend/src/legacy/registry.js`'s "
+                         "`LEGACY_MOUNTS` is empty."),
+    Deferral("D-0088-rule6-alias", "TICKET-0088",
+             "Chercher un alias nu de `mount(` / `hydrate(` importé de `'svelte'`.",
+             "Un second import de `mount` / `hydrate` depuis `'svelte'` hors des trois fichiers permis.",
+             _DECISIONS, "**D-0088-rule6-alias**: a bare `mount(`/ `hydrate(` alias imported from `'svelte'` "
+                         "is not itself scanned for;"),
+    Deferral("D-0088-rule11-unrouted", "TICKET-0088",
+             "Vérifier une `primaryAction` sans champ `createPanel`.",
+             "Un site `primaryAction: {` sans `createPanel` dans `tabs.js`.",
+             _DECISIONS, "**D-0088-rule11-unrouted**: a non-routed `primaryAction` object with no "
+                         "`createPanel` field at all passes rule 11 unchecked;"),
+)
+
+
+def deferral_dicts() -> list[dict]:
+    """The registry as the « Suivi » tab and the export read it."""
+    return [{"code": d.code, "ticket": d.ticket, "deferred": d.deferred_fr, "condition": d.condition_fr,
+             "source": d.source, "metric": d.metric, "status": d.status, "follow_up": d.follow_up}
+            for d in DEFERRALS]
diff --git a/src/world_engine/dashboard_export.py b/src/world_engine/dashboard_export.py
new file mode 100644
index 0000000..7663764
--- /dev/null
+++ b/src/world_engine/dashboard_export.py
@@ -0,0 +1,112 @@
+"""The dashboard's export: everything a deeper analysis needs, between two real-world dates, as one JSON document for a Claude Code session (TICKET-0115, BRIEF-0115-D; decisions E2, I1, J1 and M1 of the conditions series' dashboard).
+
+`build_export(db, scope) -> dict` -- reads only:
+
+- `proposals`: every `proposed_mutation` proposed in the scope (its
+  `proposed_at`), each with its world's name, producer and label, type,
+  status, dates, rationale, creator notes, `payload` (as approved, or as
+  proposed while unreviewed), `original_payload` (as the producer wrote it,
+  when the creator edited it), and its review rounds with their changes;
+- `interpreter`: every `condition_draft` created in the scope, whole --
+  instruction, outcome, payload (notes, errors, proposed vocabulary) and
+  model calls;
+- `metrics`: `dashboard_metrics.compute_metrics` on the same scope;
+  `deferrals`: `dashboard_deferrals.deferral_dicts`.
+
+M1: the JSON columns the « Suivi » tab never reads are here, for the
+analysis -- IA2, A2 and the missing label (`dashboard_deferrals.EXPORT`)
+are measured from them. The export holds the world's secrets and the
+creator's notes: the tab says so beside its button.
+"""
+
+from __future__ import annotations
+
+from collections import defaultdict
+from datetime import UTC, datetime
+from typing import Any, Optional
+
+from sqlmodel import Session, select
+
+from .dashboard_deferrals import deferral_dicts
+from .dashboard_metrics import Scope, compute_metrics, world_names
+from .models import ConditionDraft, MutationReview, MutationReviewChange, ProposedMutation
+from .proposal_producers import producer_kind, producer_label
+
+EXPORT_FORMAT = "wg-nia-dashboard-export/1"
+
+
+def _iso(at: Optional[datetime]) -> Optional[str]:
+    return at.isoformat() if at is not None else None
+
+
+def _scoped(query, column, world_column, scope: Scope):
+    if scope.world_ids is not None:
+        query = query.where(world_column.in_(scope.world_ids))
+    if scope.since is not None:
+        query = query.where(column >= scope.since)
+    if scope.until is not None:
+        query = query.where(column < scope.until)
+    return query
+
+
+def _reviews(db: Session, mutation_ids: list[str]) -> dict[str, list[dict]]:
+    if not mutation_ids:
+        return {}
+    reviews = db.exec(select(MutationReview).where(MutationReview.mutation_id.in_(mutation_ids))
+                      .order_by(MutationReview.mutation_id, MutationReview.round)).all()
+    changes: dict[str, list[dict]] = defaultdict(list)
+    if reviews:
+        for c in db.exec(select(MutationReviewChange).where(
+                MutationReviewChange.review_id.in_([r.id for r in reviews]))
+                .order_by(MutationReviewChange.path)).all():
+            changes[c.review_id].append({"path": c.path, "field": c.field, "kind": c.kind,
+                                         "before": c.before_value, "after": c.after_value})
+    out: dict[str, list[dict]] = defaultdict(list)
+    for r in reviews:
+        out[r.mutation_id].append({"round": r.round, "action": r.action, "via": r.via,
+                                   "status_after": r.status_after, "edited": r.edited,
+                                   "step_verdict": r.step_verdict, "reviewed_at": _iso(r.reviewed_at),
+                                   "changes": changes.get(r.id, [])})
+    return out
+
+
+def _proposals(db: Session, scope: Scope, names: dict[str, str]) -> list[dict]:
+    rows = db.exec(_scoped(select(ProposedMutation), ProposedMutation.proposed_at, ProposedMutation.world_id,
+                           scope).order_by(ProposedMutation.proposed_at)).all()
+    reviews = _reviews(db, [m.id for m in rows])
+    return [{
+        "id": m.id, "world_id": m.world_id, "world": names.get(m.world_id), "source_type": m.source_type,
+        "producer": m.proposed_by, "producer_label": producer_label(m.proposed_by),
+        "producer_kind": producer_kind(m.proposed_by), "mutation_type": m.mutation_type,
+        "target_table": m.target_table, "target_id": m.target_id, "status": m.status,
+        "proposed_at": _iso(m.proposed_at), "reviewed_at": _iso(m.reviewed_at), "applied_at": _iso(m.applied_at),
+        "rationale": m.rationale, "creator_notes": m.creator_notes,
+        "payload": m.payload, "original_payload": m.original_payload, "reviews": reviews.get(m.id, []),
+    } for m in rows]
+
+
+def _interpreter(db: Session, scope: Scope) -> list[dict]:
+    rows = db.exec(_scoped(select(ConditionDraft), ConditionDraft.created_at, ConditionDraft.world_ref, scope)
+                   .order_by(ConditionDraft.created_at)).all()
+    return [{
+        "id": d.id, "attempt_id": d.attempt_id, "world_id": d.world_ref, "world": d.world_name, "role": d.role,
+        "instruction": d.instruction, "outcome": d.outcome, "retried": d.retried, "offer_id": d.offer_ref,
+        "saved_as_proposed": d.saved_as_proposed, "created_at": _iso(d.created_at),
+        "decided_at": _iso(d.decided_at), "payload": d.payload, "model_calls": d.model_calls,
+    } for d in rows]
+
+
+def build_export(db: Session, scope: Scope) -> dict[str, Any]:
+    """The export of `scope` (see the module docstring)."""
+    names = world_names(db)
+    return {
+        "format": EXPORT_FORMAT,
+        "exported_at": datetime.now(UTC).isoformat(),
+        "scope": {"worlds": [{"id": w, "name": names.get(w)} for w in scope.world_ids]
+                  if scope.world_ids is not None else "all",
+                  "since": _iso(scope.since), "until_excluded": _iso(scope.until)},
+        "proposals": _proposals(db, scope, names),
+        "interpreter": _interpreter(db, scope),
+        "metrics": compute_metrics(db, scope),
+        "deferrals": deferral_dicts(),
+    }
diff --git a/src/world_engine/dashboard_metrics.py b/src/world_engine/dashboard_metrics.py
new file mode 100644
index 0000000..f8afd0f
--- /dev/null
+++ b/src/world_engine/dashboard_metrics.py
@@ -0,0 +1,295 @@
+"""The creator's dashboard: a registry of metrics in code, each a question in French, its computation over relational columns, and the decision codes it watches (TICKET-0115, BRIEF-0115-D; decisions H1, D1, E2 and M1 of the conditions series' dashboard).
+
+H1: a metric is code -- never SQL written in the interface. E2: no
+threshold; the numbers are shown and Nia judges. M1: a metric reads
+relational columns only, never a JSON column (`ProposedMutation.payload`,
+`ConditionDraft.payload`: INV-20) -- what lives in JSON is measured from
+the export (`dashboard_export.py`).
+
+`Scope(world_ids, since, until)`: the worlds (None: every world) and the
+real-world dates, `until` excluded (the route passes the day after the last
+day asked). A metric of reviews reads `mutation_review.reviewed_at`, of the
+interpreter `condition_draft.created_at`, of the lexicon
+`skill_resolution.created_at`; a metric of the world as it stands
+(conditions, encounters, the queue) ignores the dates.
+
+`compute_metrics(db, scope) -> list[dict]`: each `METRICS` entry as
+`{key, title, question, watches, dated, rows: [{group, label, value, of}],
+note}` -- `value` out of `of` when `of` is set.
+"""
+
+from __future__ import annotations
+
+from collections import Counter, defaultdict
+from dataclasses import dataclass
+from datetime import datetime
+from typing import Callable, Optional
+
+from sqlmodel import Session, select
+
+from .conditions import and_path_leaves, read_condition
+from .models import (
+    Agenda, AgendaStep, Character, ConditionDraft, ConditionNode, MutationReview, MutationReviewChange,
+    ProposedMutation, Quest, Rencontre, SkillResolution, World,
+)
+from .proposal_producers import producer_label
+
+
+@dataclass(frozen=True)
+class Scope:
+    world_ids: Optional[tuple[str, ...]] = None
+    since: Optional[datetime] = None
+    until: Optional[datetime] = None
+
+
+@dataclass(frozen=True)
+class Row:
+    group: str
+    label: str
+    value: int
+    of: Optional[int] = None
+
+
+@dataclass(frozen=True)
+class Metric:
+    key: str
+    title: str
+    question: str
+    watches: tuple[str, ...]
+    dated: bool
+    compute: Callable[[Session, Scope], tuple[list[Row], str]]
+
+
+def _in_worlds(column, scope: Scope):
+    return True if scope.world_ids is None else column.in_(scope.world_ids)
+
+
+def _dated(column, scope: Scope):
+    conditions = []
+    if scope.since is not None:
+        conditions.append(column >= scope.since)
+    if scope.until is not None:
+        conditions.append(column < scope.until)
+    return conditions
+
+
+def _rounds(db: Session, scope: Scope, mutation_type: str) -> dict[str, list[MutationReview]]:
+    """The review rounds of `mutation_type` proposals whose LAST round falls
+    in the scope, by proposal, in round order."""
+    rows = db.exec(select(MutationReview)
+                   .join(ProposedMutation, ProposedMutation.id == MutationReview.mutation_id)
+                   .where(ProposedMutation.mutation_type == mutation_type,
+                          _in_worlds(MutationReview.world_id, scope))
+                   .order_by(MutationReview.mutation_id, MutationReview.round)).all()
+    by_mutation: dict[str, list[MutationReview]] = defaultdict(list)
+    for review in rows:
+        by_mutation[review.mutation_id].append(review)
+    return {m: r for m, r in by_mutation.items() if all(_holds(r[-1].reviewed_at, b) for b in _bounds(scope))}
+
+
+def _bounds(scope: Scope) -> list[tuple[str, datetime]]:
+    return [(op, at) for op, at in ((">=", scope.since), ("<", scope.until)) if at is not None]
+
+
+def _holds(at: datetime, bound: tuple[str, datetime]) -> bool:
+    op, limit = bound
+    at, limit = at.replace(tzinfo=None), limit.replace(tzinfo=None)
+    return at >= limit if op == ">=" else at < limit
+
+
+def _producers(db: Session, ids) -> dict[str, Optional[str]]:
+    if not ids:
+        return {}
+    return dict(db.exec(select(ProposedMutation.id, ProposedMutation.proposed_by)
+                        .where(ProposedMutation.id.in_(list(ids)))).all())
+
+
+# --- the metrics -------------------------------------------------------------------
+
+def _event_reviews(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rounds = _rounds(db, scope, "event_creation")
+    producers = _producers(db, rounds)
+    outcome: dict[str, Counter] = defaultdict(Counter)
+    for mutation_id, reviews in rounds.items():
+        last = reviews[-1]
+        if last.action == "reject":
+            kind = "rejeté"
+        elif last.status_after == "approved":
+            kind = "en attente (« Needs attention »)"
+        elif any(r.edited for r in reviews):
+            kind = "accepté corrigé"
+        else:
+            kind = "accepté tel quel"
+        outcome[producer_label(producers.get(mutation_id))][kind] += 1
+    rows = [Row(group, kind, n, sum(counts.values()))
+            for group, counts in sorted(outcome.items())
+            for kind, n in sorted(counts.items())]
+    return rows, "Chaque événement proposé, selon sa dernière revue dans la période."
+
+
+def _tick_retyped(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rounds = _rounds(db, scope, "event_creation")
+    producers = _producers(db, rounds)
+    tick = {m: r for m, r in rounds.items() if producers.get(m) == "local_ai_tick" and r[-1].action == "approve"}
+    retyped = 0
+    for reviews in tick.values():
+        ids = [r.id for r in reviews]
+        fields = db.exec(select(MutationReviewChange.field)
+                         .where(MutationReviewChange.review_id.in_(ids))).all()
+        if any(f in ("type_id", "type") or f.startswith("new_type") for f in fields):
+            retyped += 1
+    return [Row("Tick du monde", "retypés par Nia", retyped, len(tick))], \
+        "Événements du tick acceptés dont Nia a changé le type."
+
+
+_AGREE = {("approve", "met"), ("reject", "unmet")}
+_JUDGED = ("met", "unmet")
+
+
+def _step_verdicts(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rounds = _rounds(db, scope, "agenda_step_change")
+    counts: Counter = Counter()
+    for reviews in rounds.values():
+        first = reviews[0]
+        verdict = first.step_verdict
+        if verdict in _JUDGED:
+            counts["Nia confirme la condition" if (reviews[-1].action, verdict) in _AGREE
+                   else "Nia contredit la condition"] += 1
+        elif verdict == "unknown":
+            counts["condition invérifiable"] += 1
+        else:
+            counts["pas de condition à juger"] += 1
+    total = sum(counts.values())
+    return [Row("Étapes", label, n, total) for label, n in sorted(counts.items())], \
+        "Le verdict de la condition au moment de la revue, comparé à la décision finale de Nia."
+
+
+OUTCOMES_FR: dict[str, str] = {
+    "proposed": "proposée, sans suite", "needs_choice": "un nom à choisir, sans suite",
+    "refused": "refusée par le code", "unavailable": "modèle indisponible", "parse_error": "réponse illisible",
+    "inserted": "insérée, offre non enregistrée", "discarded": "écartée par Nia", "saved": "enregistrée",
+}
+
+
+def _interpreter(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rows = db.exec(select(ConditionDraft.outcome, ConditionDraft.saved_as_proposed)
+                   .where(_in_worlds(ConditionDraft.world_ref, scope),
+                          *_dated(ConditionDraft.created_at, scope))).all()
+    total = len(rows)
+    outcomes = Counter(o for o, _s in rows)
+    saved = [s for o, s in rows if o == "saved"]
+    out = [Row("Propositions", OUTCOMES_FR.get(outcome, outcome), n, total)
+           for outcome, n in sorted(outcomes.items())]
+    if saved:
+        out.append(Row("Enregistrées", "telles que proposées", sum(1 for s in saved if s), len(saved)))
+    return out, "Chaque proposition de l'interprète de conditions, selon son issue."
+
+
+def _steps_without_day_npc(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    steps = db.exec(select(AgendaStep, Agenda.world_id)
+                    .join(Agenda, Agenda.id == AgendaStep.agenda_id)
+                    .join(Quest, Quest.agenda_id == Agenda.id)
+                    .where(AgendaStep.status == "active", Agenda.status == "active",
+                           _in_worlds(Agenda.world_id, scope))).all()
+    with_prerequisite = without_npc = 0
+    for step, _world in steps:
+        try:
+            tree = read_condition(db, role="prerequisite", agenda_step_id=step.id)
+        except ValueError:
+            continue
+        if tree is None:
+            continue
+        with_prerequisite += 1
+        if not any(leaf.type == "relation_gte" for leaf in and_path_leaves(tree)):
+            without_npc += 1
+    return [Row("Étapes de quête actives", "sans PNJ de journée", without_npc, with_prerequisite)], \
+        "Étapes actives avec un prérequis, dont aucune relation atteinte par « toutes » ne nomme le PNJ."
+
+
+def _absence_leaves(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    leaves = db.exec(select(ConditionNode.parent_id).where(
+        ConditionNode.op == "leaf", ConditionNode.form == "event",
+        _in_worlds(ConditionNode.world_id, scope))).all()
+    parents = {p for p in leaves if p}
+    nots = set(db.exec(select(ConditionNode.id).where(ConditionNode.id.in_(list(parents)),
+                                                       ConditionNode.op == "not")).all()) if parents else set()
+    under_not = sum(1 for p in leaves if p in nots)
+    return [Row("Feuilles « événement »", "sous un « non »", under_not, len(leaves))], \
+        "« Sans être repéré » s'écrit « non » sur une feuille événement."
+
+
+def _edited_fields(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rows = db.exec(select(ProposedMutation.mutation_type, MutationReviewChange.field)
+                   .join(MutationReview, MutationReview.id == MutationReviewChange.review_id)
+                   .join(ProposedMutation, ProposedMutation.id == MutationReview.mutation_id)
+                   .where(_in_worlds(MutationReviewChange.world_id, scope),
+                          *_dated(MutationReview.reviewed_at, scope))).all()
+    counts = Counter(rows)
+    return [Row(mutation_type, field, n) for (mutation_type, field), n in counts.most_common(15)], \
+        "Ce que Nia corrige le plus souvent avant d'accepter (15 premiers)."
+
+
+def _rencontre_pairs(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    characters = set(db.exec(select(Character.id).where(_in_worlds(Character.world_id, scope))).all())
+    pairs = db.exec(select(Rencontre.entity_lo_id, Rencontre.entity_hi_id)
+                    .where(_in_worlds(Rencontre.world_id, scope))).all()
+    other = sum(1 for lo, hi in pairs if lo not in characters or hi not in characters)
+    return [Row("Rencontres", "hors deux personnages", other, len(pairs))], \
+        "A1'b revient si aucune rencontre ne lie autre chose que deux personnages."
+
+
+def _lexicon_gaps(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    forms = db.exec(select(SkillResolution.surface_form).where(
+        SkillResolution.verdict == "unmatched", _in_worlds(SkillResolution.world_id, scope),
+        *_dated(SkillResolution.created_at, scope))).all()
+    distinct = {f.strip().casefold() for f in forms}
+    return [Row("Lexique d'actions", "formes non reconnues distinctes", len(distinct), len(forms))], \
+        "Le seuil de C3b est le tien : la liste des formes est dans « Compétences »."
+
+
+def _needs_attention(db: Session, scope: Scope) -> tuple[list[Row], str]:
+    rows = db.exec(select(ProposedMutation.proposed_by).where(
+        ProposedMutation.status == "approved", _in_worlds(ProposedMutation.world_id, scope))).all()
+    counts = Counter(producer_label(p) for p in rows)
+    return [Row("En attente", label, n) for label, n in sorted(counts.items())], \
+        "Approuvées sans pouvoir s'appliquer (ou en attente de réalisation) : la file « Needs attention »."
+
+
+METRICS: tuple[Metric, ...] = (
+    Metric("event_reviews", "Événements proposés",
+           "Combien d'événements proposés acceptes-tu tels quels ?", ("D1", "D2"), True, _event_reviews),
+    Metric("tick_retyped", "Types du tick",
+           "Retypes-tu souvent les événements du tick ?", ("A1 (0119)",), True, _tick_retyped),
+    Metric("step_verdicts", "Objectifs d'étape",
+           "Confirmes-tu ce que la condition d'accomplissement dit déjà ?", ("M1", "M2"), True, _step_verdicts),
+    Metric("interpreter", "Interprète de conditions",
+           "Que deviennent les propositions de l'interprète ?", ("IH1",), True, _interpreter),
+    Metric("steps_without_day_npc", "PNJ de journée",
+           "Des étapes actives n'ont-elles pas de PNJ de journée ?", ("Q1", "Q2"), False, _steps_without_day_npc),
+    Metric("absence_leaves", "Absence",
+           "Écris-tu souvent « non » sur une feuille événement ?", ("absence",), False, _absence_leaves),
+    Metric("edited_fields", "Corrections",
+           "Que corriges-tu dans les propositions ?", ("A3", "H1a"), True, _edited_fields),
+    Metric("rencontre_pairs", "Rencontres",
+           "Des rencontres lient-elles autre chose que deux personnages ?", ("A1'b",), False, _rencontre_pairs),
+    Metric("lexicon_gaps", "Lexique d'actions",
+           "Combien de gestes le lexique ne reconnaît-il pas ?", ("C3b",), True, _lexicon_gaps),
+    Metric("needs_attention", "File « Needs attention »",
+           "Combien de propositions approuvées attendent encore ?", (), False, _needs_attention),
+)
+
+
+def compute_metrics(db: Session, scope: Scope) -> list[dict]:
+    """Every metric of `METRICS` for `scope` (see the module docstring)."""
+    out = []
+    for metric in METRICS:
+        rows, note = metric.compute(db, scope)
+        out.append({"key": metric.key, "title": metric.title, "question": metric.question,
+                    "watches": list(metric.watches), "dated": metric.dated, "note": note,
+                    "rows": [{"group": r.group, "label": r.label, "value": r.value, "of": r.of} for r in rows]})
+    return out
+
+
+def world_names(db: Session) -> dict[str, str]:
+    """Every world's name by id."""
+    return dict(db.exec(select(World.id, World.name)).all())
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 2dedc33..836cc9f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19747,6 +19747,42 @@ stamped `local_ai` by Journée's objective event before this brief stay as
 they are (history): the export carries `mutation_type` and `rationale`,
 which tell them apart.
 
+## THE DASHBOARD IS A REGISTRY IN CODE (TICKET-0115) -- `dashboard_metrics.py`, `dashboard_deferrals.py`, `dashboard_export.py`, `GET /api/dashboard[/export]` (BRIEF-0115-d, no schema change)
+
+**H1, E2.** Each metric is a question in French, a computation in code and
+the decision codes it watches -- never SQL typed in the interface. No
+threshold: the numbers are shown, Nia judges (E2). The scope is every world
+or one (J1) and two real-world days on the cockpit's own clock, both
+included; a metric of the world as it stands (conditions, encounters, the
+queue) ignores the dates and says so (`dated`).
+
+**M1 -- the tab reads no JSON.** `ProposedMutation.payload` and
+`ConditionDraft.payload` stay audit material (INV-20): the metrics read
+`mutation_review`, `mutation_review_change`, `condition_draft.outcome` and
+`saved_as_proposed`, `condition_node`, `rencontre`, `skill_resolution`.
+What only the JSON holds -- costs typed into the interpreter (IA2), « cette
+forme n'existe pas » (A2), a missing label -- is measured from the export,
+whose entries say `metric: export`. Reactivation of M2 (the rejected
+alternative: signals made relational now): an analysis of the export shows
+one of those measures deserves a screen.
+
+**F2, K2, L -- the deferral registry.** `DEFERRALS` lists the deferrals Nia
+named, each with its condition in French, the file that declares it and a
+verbatim anchor (`dashboard_registry.py` finds it there once: a reworded
+declaration is red), the metric that watches it, and its status. Two are
+`reached` on entry: WH3 (0114's journal knows the witnesses; TICKET-0122 is
+reserved for it) and the payload's relationalization (the review card has
+edited it field by field since 0119; no ticket yet). A future deferral
+enters by the lot of the ticket that locks it, never by a scan.
+
+**I1 -- the export.** One JSON document for the scope: proposals with their
+payloads, original payloads and review rounds; the interpreter's drafts
+whole; the metrics; the registry -- for a Claude Code session. It holds the
+world's secrets: the tab says so beside the button.
+
+**Rejected.** H2 (metrics typed in the interface), E1 (thresholds with a
+minimum sample: Nia's prod held 3 typed events), I2 (a CSV per table).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/dashboard_registry.py b/tooling/verify/checks/dashboard_registry.py
new file mode 100644
index 0000000..a8c5c00
--- /dev/null
+++ b/tooling/verify/checks/dashboard_registry.py
@@ -0,0 +1,329 @@
+"""G1 check for TICKET-0115 -- the dashboard is a registry in code: its metrics read relational columns only, its deferrals point at the passage that declares them, and its export carries what the tab does not show.
+
+BRIEF-0115-D's rules (H1, E2, F2, I1, J1, K2, L and M1 of the conditions
+series' dashboard).
+
+DB1 -- the deferral registry (static). `DEFERRALS` is not empty; each
+   entry's `source` exists and holds its `anchor` exactly once (whitespace
+   folded); its `status` is one of `DEFERRAL_STATUSES`, `follow_up` only
+   when `reached`; its `metric` is None, `EXPORT` or a `METRICS` key; no
+   `(code, ticket)` twice; every text is non-empty.
+DB2 -- the metrics (static). `METRICS` keys are unique, each with a title, a
+   question and a compute function. M1: `dashboard_metrics.py` reads no
+   JSON column -- no attribute `payload`, `original_payload` or
+   `model_calls`, no `text(` -- and neither does the route module.
+DB3 -- the numbers (fixture, two worlds). In world A: three window events
+   reviewed -- one accepted as proposed, one edited, one rejected; two tick
+   events accepted, both edited, one with a changed `type_id` (retyped)
+   and one with a changed title only (not retyped); three step changes -- one
+   approved while its completion was `met`, one approved while `unmet`, one
+   with no condition; one interpreter draft `saved` as proposed and one
+   `discarded`; one `event` leaf under a `not` of two. World B holds one
+   more window event. `dashboard(world=A)` gives exactly the rows of
+   `EXPECTED`; `world=all` counts B's event too; `until` today includes
+   today; `since` the day after today leaves every dated metric empty and
+   the undated ones unchanged.
+DB4 -- the scope. A date that does not parse, `since` after `until` and an
+   unknown world each answer 422.
+DB5 -- the export. `dashboard_export(world=A)` answers an attachment whose
+   JSON has `format`, A's proposals only -- the edited one with its
+   `original_payload`, its round and its change `title` --, both
+   interpreter drafts with their payload, the metrics and the deferrals.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import json
+import os
+import pathlib
+import re
+import sys
+import tempfile
+from datetime import date, timedelta
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+METRICS_PY = ROOT / "src" / "world_engine" / "dashboard_metrics.py"
+ROUTES_PY = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "dashboard.py"
+
+FAILURES: list[str] = []
+FORBIDDEN_ATTRS = ("payload", "original_payload", "model_calls")
+
+# (metric, group, label) -> (value, of), for world A.
+EXPECTED: dict[tuple[str, str, str], tuple[int, int | None]] = {
+    ("event_reviews", "Play — analyse de fenêtre", "accepté tel quel"): (1, 3),
+    ("event_reviews", "Play — analyse de fenêtre", "accepté corrigé"): (1, 3),
+    ("event_reviews", "Play — analyse de fenêtre", "rejeté"): (1, 3),
+    ("event_reviews", "Tick du monde", "accepté corrigé"): (2, 2),
+    ("tick_retyped", "Tick du monde", "retypés par Nia"): (1, 2),
+    ("step_verdicts", "Étapes", "Nia confirme la condition"): (1, 3),
+    ("step_verdicts", "Étapes", "Nia contredit la condition"): (1, 3),
+    ("step_verdicts", "Étapes", "pas de condition à juger"): (1, 3),
+    ("interpreter", "Propositions", "enregistrée"): (1, 2),
+    ("interpreter", "Propositions", "écartée par Nia"): (1, 2),
+    ("interpreter", "Enregistrées", "telles que proposées"): (1, 1),
+    ("absence_leaves", "Feuilles « événement »", "sous un « non »"): (1, 2),
+    ("edited_fields", "event_creation", "title"): (2, None),
+    ("edited_fields", "event_creation", "type_id"): (1, None),
+}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+
+
+def _fold(text: str) -> str:
+    return re.sub(r"\s+", " ", text)
+
+
+# --- DB1, DB2 --------------------------------------------------------------------
+
+def check_db1() -> None:
+    from world_engine.dashboard_deferrals import DEFERRAL_STATUSES, DEFERRALS, EXPORT
+    from world_engine.dashboard_metrics import METRICS
+
+    keys = {m.key for m in METRICS}
+    if not DEFERRALS:
+        fail("DB1: the deferral registry is empty")
+    seen = set()
+    for d in DEFERRALS:
+        where = f"DB1: {d.code} ({d.ticket})"
+        if (d.code, d.ticket) in seen:
+            fail(f"{where} is listed twice")
+        seen.add((d.code, d.ticket))
+        if not all(s.strip() for s in (d.code, d.ticket, d.deferred_fr, d.condition_fr, d.anchor)):
+            fail(f"{where} has an empty text")
+        source = ROOT / d.source
+        if not source.exists():
+            fail(f"{where}: {d.source} not found")
+        elif _fold(source.read_text(encoding="utf-8")).count(_fold(d.anchor)) != 1:
+            fail(f"{where}: its anchor is not found exactly once in {d.source}")
+        if d.status not in DEFERRAL_STATUSES or (d.follow_up is not None and d.status != "reached"):
+            fail(f"{where}: status {d.status!r}, follow-up {d.follow_up!r}")
+        if d.metric not in (None, EXPORT) and d.metric not in keys:
+            fail(f"{where}: unknown metric {d.metric!r}")
+
+
+def _attrs_and_text(path: pathlib.Path) -> tuple[set[str], bool]:
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
+    raw = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "text"
+              for n in ast.walk(tree))
+    return attrs, raw
+
+
+def check_db2() -> None:
+    from world_engine.dashboard_metrics import METRICS
+
+    if not METRICS:
+        fail("DB2: no metric")
+    if len({m.key for m in METRICS}) != len(METRICS):
+        fail("DB2: a metric key is listed twice")
+    for m in METRICS:
+        if not (m.title.strip() and m.question.strip() and callable(m.compute)):
+            fail(f"DB2: {m.key} lacks a title, a question or a computation")
+    for path in (METRICS_PY, ROUTES_PY):
+        if not path.exists():
+            fail(f"DB2: {path} not found")
+            continue
+        attrs, raw = _attrs_and_text(path)
+        if raw or set(FORBIDDEN_ATTRS) & attrs:
+            fail(f"DB2: {path.name} reads {sorted(set(FORBIDDEN_ATTRS) & attrs)} or raw SQL (M1)")
+
+
+# --- fixture ---------------------------------------------------------------------
+
+def _review(db, mut, action: str, before: dict, status: str, verdict=None) -> None:
+    from world_engine.writes.mutation_reviews import ReviewCall, record_review
+
+    mut.status = status
+    db.add(mut)
+    record_review(db, mut, ReviewCall(action, "unit", before, verdict))
+
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.conditions import node_from_dict
+    from world_engine.models import (
+        Agenda, AgendaStep, Character, ConditionDraft, Entity, ProposedMutation, World,
+    )
+    from world_engine.writes.conditions import write_condition
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type
+
+    with Session(engine) as db:
+        ids = {}
+        for key in ("a", "b"):
+            world = World(name=f"Monde {key.upper()}", is_active=key == "a")
+            db.add(world)
+            db.flush()
+            ids[key] = world.id
+        brakk = Entity(world_id=ids["a"], type="character", name="Brakk")
+        db.add(brakk)
+        db.flush()
+        db.add(Character(id=brakk.id, world_id=ids["a"], character_type="player"))
+        chasse = write_event_type(db, world_id=ids["a"], spec=EventTypeSpec(
+            name="Chasse", roles=(RoleSpec("Chasseur", ("character",)),)))
+
+        def proposal(world: str, producer: str, kind: str = "event_creation", payload=None):
+            row = ProposedMutation(world_id=ids[world], source_type="conversation", mutation_type=kind,
+                                   payload=payload or {"title": "t", "type_id": "x"}, proposed_by=producer)
+            db.add(row)
+            db.flush()
+            return row
+
+        plain = proposal("a", "local_ai_window")
+        _review(db, plain, "approve", dict(plain.payload), "applied")
+        edited = proposal("a", "local_ai_window")
+        ids["edited"] = edited.id
+        before = dict(edited.payload)
+        edited.payload = {"title": "Chasse au loup", "type_id": "x"}
+        _review(db, edited, "approve", before, "applied")
+        rejected = proposal("a", "local_ai_window")
+        _review(db, rejected, "reject", dict(rejected.payload), "rejected")
+        tick_titled = proposal("a", "local_ai_tick")
+        before = dict(tick_titled.payload)
+        tick_titled.payload = {"title": "Loups", "type_id": "x"}
+        _review(db, tick_titled, "approve", before, "applied")
+        tick_typed = proposal("a", "local_ai_tick")
+        before = dict(tick_typed.payload)
+        tick_typed.payload = {"title": "t", "type_id": "y"}
+        _review(db, tick_typed, "approve", before, "applied")
+        other = proposal("b", "local_ai_window")
+        _review(db, other, "approve", dict(other.payload), "applied")
+
+        for verdict in ("met", "unmet", "none"):
+            step = proposal("a", "local_ai", "agenda_step_change", {"step_id": "s", "action": "complete"})
+            _review(db, step, "approve", dict(step.payload), "applied", verdict)
+
+        for outcome, saved in (("saved", True), ("discarded", None)):
+            db.add(ConditionDraft(attempt_id="at", world_ref=ids["a"], world_name="Monde A", role="completion",
+                                  instruction="trois loups", outcome=outcome,
+                                  offer_ref="offer" if saved else None, saved_as_proposed=saved,
+                                  payload={"notes": ["« apporte 3 peaux » : c'est un coût"]}))
+
+        agenda = Agenda(world_id=ids["a"], owner_entity_id=brakk.id, title="t", status="active")
+        db.add(agenda)
+        db.flush()
+        leaf = {"op": "leaf", "type": "event", "subject_role": "doer", "target_key": chasse.id, "threshold": 1}
+        for order, tree in ((1, {"op": "not", "children": [leaf]}), (2, leaf)):
+            step = AgendaStep(agenda_id=agenda.id, step_order=order, objective="o",
+                              status="active" if order == 1 else "pending")
+            db.add(step)
+            db.flush()
+            write_condition(db, world_id=ids["a"], role="completion", tree=node_from_dict(tree),
+                            agenda_step_id=step.id)
+        db.commit()
+    return ids
+
+
+def _rows(answer: dict) -> dict[tuple[str, str, str], tuple[int, int | None]]:
+    return {(m["key"], r["group"], r["label"]): (r["value"], r["of"])
+            for m in answer["metrics"] for r in m["rows"]}
+
+
+# --- DB3, DB4, DB5 ---------------------------------------------------------------
+
+def check_db3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import dashboard as routes
+
+    with Session(engine) as db:
+        a = _rows(routes.dashboard(world=ids["a"], since=None, until=None, db=db))
+        every = _rows(routes.dashboard(world="all", since=None, until=None, db=db))
+        tomorrow = (date.today() + timedelta(days=1)).isoformat()
+        later = routes.dashboard(world=ids["a"], since=tomorrow, until=None, db=db)
+        today = _rows(routes.dashboard(world=ids["a"], since=None, until=date.today().isoformat(), db=db))
+    keys = {k[0] for k in EXPECTED}
+    got = {k: v for k, v in a.items() if k[0] in keys}
+    if got != EXPECTED:
+        fail(f"DB3: world A's rows are {sorted(got.items())}")
+    window = ("event_reviews", "Play — analyse de fenêtre", "accepté tel quel")
+    if today.get(window) != (1, 3):
+        fail(f"DB3: `until` today counts {today.get(window)}: the last day is not included")
+    if every.get(window) != (2, 4):
+        fail(f"DB3: every world counts {every.get(window)} window events accepted as proposed")
+    for metric in later["metrics"]:
+        undated = [r for r in _rows({"metrics": [metric]}).items()]
+        if metric["dated"] and metric["rows"] and any(r["value"] for r in metric["rows"]):
+            fail(f"DB3: {metric['key']} counts {metric['rows']} after tomorrow")
+        if not metric["dated"] and dict(undated) != {k: v for k, v in a.items() if k[0] == metric["key"]}:
+            fail(f"DB3: the undated {metric['key']} moved with the dates")
+
+
+def check_db4(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import dashboard as routes
+
+    cases = ((ids["a"], "2026-13-01", None), (ids["a"], "2026-10-12", "2026-10-01"), ("no-such-world", None, None))
+    with Session(engine) as db:
+        for world, since, until in cases:
+            try:
+                routes.dashboard(world=world, since=since, until=until, db=db)
+                fail(f"DB4: {world}/{since}/{until} was accepted")
+            except HTTPException as exc:
+                if exc.status_code != 422:
+                    fail(f"DB4: {world}/{since}/{until} answered {exc.status_code}")
+
+
+def check_db5(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import dashboard as routes
+
+    with Session(engine) as db:
+        answer = routes.dashboard_export(world=ids["a"], since=None, until=None, db=db)
+    if "attachment" not in answer.headers.get("content-disposition", ""):
+        fail(f"DB5: the export is not an attachment: {answer.headers}")
+    data = json.loads(answer.body)
+    proposals = data.get("proposals", [])
+    if data.get("format") != "wg-nia-dashboard-export/1" or len(proposals) != 8 \
+            or any(p["world_id"] != ids["a"] for p in proposals):
+        fail(f"DB5: {len(proposals)} proposals, format {data.get('format')}")
+    edited = next((p for p in proposals if p["id"] == ids["edited"]), None)
+    if edited is None or edited["original_payload"] != {"title": "t", "type_id": "x"} \
+            or [c["path"] for r in edited["reviews"] for c in r["changes"]] != ["title"]:
+        fail(f"DB5: the edited proposal exports as {edited}")
+    drafts = data.get("interpreter", [])
+    if len(drafts) != 2 or not all(d["payload"].get("notes") for d in drafts):
+        fail(f"DB5: the interpreter exports {drafts}")
+    if not data.get("metrics") or not data.get("deferrals"):
+        fail("DB5: the export lacks its metrics or its deferrals")
+
+
+def main() -> None:
+    _fresh_db()
+    from sqlmodel import SQLModel
+
+    from world_engine import models  # noqa: F401 -- registers every table
+    from world_engine.db import engine
+
+    SQLModel.metadata.create_all(engine)
+    check_db1()
+    check_db2()
+    ids = _fixture(engine)
+    check_db3(engine, ids)
+    check_db4(engine, ids)
+    check_db5(engine, ids)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print("PASS: dashboard_registry -- the metrics read relational columns, each deferral points at its "
+          "declaration, the numbers and the export hold on a fixture")
+
+
+if __name__ == "__main__":
+    main()
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Any threshold (E2), any SQL typed in the interface (H2).
- Reading a JSON column in a metric (M1); a screen for the export's signals (M2).
- The tab (BRIEF-0115-E).

## Invariants to defend

INV-20 / M1: no metric, and not the route module, reads `payload`, `original_payload` or `model_calls` (DB2) -- only the export does, and the export is a file, not a surface. INV-01 (secrets): the export holds the world's secrets and the creator's notes; it is a creator-only download, and the tab (E) warns. The routes write nothing.

## Decision rights

STOP:
- A deferral anchor not found once in its file (DB1): the declaration moved -- STOP, never reword the anchor to fit.
- A metric that can only be computed from a JSON column.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- `lore_usage.py` timing out at 16-17 s inside the corpus: it does the same on `main` (pre-existing, R-09 of the lot).
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/dashboard_registry.py` -> `PASS`.
- `python tooling/verify/checks/origin_guard.py` -> `PASS`.
- `python tooling/verify/checks/module_budget.py` -> `PASS`.
- `python tooling/verify/checks/undefined_names.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (166 on the prototype; `lore_usage.py` may time out as on `main` -- REPORT-ONLY).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **DB1** -- `dashboard_deferrals.py`, P2's anchor: `"Reactivates when a seventh write site appears` -> `"Reactivates when an eighth write site appears`
  - **DB1** -- `dashboard_deferrals.py`, WH3: `             status="reached", follow_up="TICKET-0122"),` -> `             follow_up="TICKET-0122"),`
  - **DB2** -- `dashboard_metrics.py` `_interpreter`: `    rows = db.exec(select(ConditionDraft.outcome, ConditionDraft.saved_as_proposed)` -> `    _x = ConditionDraft.payload` added above it
  - **DB3** -- `dashboard_metrics.py` `_AGREE`: `_AGREE = {("approve", "met"), ("reject", "unmet")}` -> `_AGREE = {("approve", "met"), ("approve", "unmet")}`
  - **DB3** -- `dashboard_metrics.py` `_tick_retyped`: `        if any(f in ("type_id", "type") or f.startswith("new_type") for f in fields):` -> `        if fields:`
  - **DB3** -- `dashboard_metrics.py` `_in_worlds`: `    return True if scope.world_ids is None else column.in_(scope.world_ids)` -> `    return True`
  - **DB3** -- `routes/dashboard.py` `scope_of`: `        until=_utc(last + timedelta(days=1)) if last is not None else None,` -> `        until=_utc(last) if last is not None else None,`
- Live gate (Nia): `GET http://127.0.0.1:8000/api/dashboard` answers the metrics and the 20 deferrals; `/api/dashboard/export?since=2026-10-01` downloads a JSON file.
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
