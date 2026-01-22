# Service Primitives & Best-Practice Readiness Review

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-20
**Reference:** `docs/design/architecture.md` (layering, definitions vs instantiations, session ownership, FIFO, export fidelity)
**Scope:** Service layer primitives for a future multi-user/web context. Deep reads: planning (`planning_service`, `batch_calculation`, `feasibility`, `progress`, `shopping_list`), production (`batch_production_service`, `production_service`), assembly (`assembly_service`), shared infra (`database.py`, `exceptions.py`), and recent material/finished-unit work from prior reviews (F056-F058). Findings focus on adherence and gaps that must be fixed before building on these services.

## Executive Summary
Core primitives (session_scope, domain exceptions, FIFO consumption, definition/instantiation separation, slug/UUID usage, import/export framing) are present and now significantly hardened after F060/F061. Planning snapshots aggregate ingredients and detect composition/finished-unit updates; nested finished-good consumption is ledgered; the legacy production path is removed; a finished-goods inventory service provides session-aware adjust/validate/query with audit. Remaining blockers are concentrated in event service session ownership (still self-managing sessions), detached progress/cost flows, DTO/logging consistency, and material metric/FIFO gaps that were out of F060/F061 scope.

## Adherence Highlights
- **Layered design:** Services avoid UI imports; models carry schema only. Planning, production, and assembly expose service-level DTOs and domain exceptions (good for API surface).
- **Session primitive (`session_scope`):** Centralized in `database.py`; many services accept an optional `session` and thread it through (e.g., `batch_production_service`, `assembly_service` for packaging/material consumption).
- **Definition vs instantiation:** Production/assembly use snapshots and FIFO to cost instances; catalog entities remain costless definitions (recipes, finished units, products, material products).
- **FIFO & cost snapshotting:** Ingredient FIFO is mature; batch production records consumptions and losses; assembly captures packaging/material consumption ledgers; nested FG consumption now ledgered.
- **Finished goods inventory primitives:** New `finished_goods_inventory_service` is session-aware (query/validate/adjust) with audit records.
- **Planning hardening:** `planning_service` now aggregates plan ingredients/cost baselines; staleness checks composition created/updated and finished-unit yield changes; planning/shopping/progress/feasibility accept and forward caller sessions.
- **Domain exceptions:** `exceptions.py` plus service-specific errors give API-friendly failure modes (`ValidationError`, `NotFound`, insufficiency errors).
- **Import/export framing:** Coordinated export/import exists for catalog and history; slugs/UUIDs are used for portability.

## Gaps (must address before relying on “mature” services)
- **Event service session ownership:** `event_service` still self-manages sessions and lacks optional `session` on most helpers (CRUD, needs, packaging, progress), forcing detached reads/writes and preventing atomic orchestration.
- **Detached progress/cost aggregation:** `production_service.get_production_progress`, `event_service.get_events_with_progress`, and some cost analytics still open their own sessions even when upstream would provide one; progress remains partially detached from caller transactions.
- **Material catalog alignment (unchanged, out of F060/F061 scope):** Materials UI still uses imperial units; coordinated export/import omits `MaterialInventoryItem` lots and uses stale purchase fields; materials FIFO callers remain linear-centric; material listing may use the wrong cost field.
- **DTO/typing consistency:** Costs/quantities mix Decimal and str across services; units sometimes implicit. Standardize DTOs for API readiness.
- **Observability:** Minimal structured logging around plan calc, feasibility, production/assembly/inventory adjustments for multi-user debugging.

## Must-Fix Checklist (mature surface hardening)
1. **Event service session ownership:** Add optional `session` to event_service helpers and use caller sessions when provided; avoid internal `session_scope` when a session is passed.
2. **Progress/cost aggregation transactions:** Allow production/assembly progress and cost analytics to run inside caller transactions (accept session, no detached session_scope when provided); align `event_service.get_events_with_progress` to reuse shared sessions if supplied.
3. **Material primitives (still open):**
   - UI/options to metric base units; fix unit-aware FIFO (linear/square/each).
   - Use `cost_per_unit` in material listings; fix unit converter coverage/tests for area/each.
   - Export/import `MaterialInventoryItem` lots and correct purchase fields in coordinated flows.
4. **DTO normalization & logging:** Standardize numeric/Decimal/string conventions and add structured logs for plan calc, feasibility, production/assembly/inventory execution.

## Ready Primitives You Can Build On (after above fixes)
- Ingredient/product catalog + FIFO (food) with batch production ledger and loss tracking.
- Recipes/FinishedUnits as unified yield source; batch production uses snapshots and FIFO correctly.
- Assembly service with packaging/material and nested finished-good consumption ledger, integrated with finished-goods inventory service.
- Finished goods inventory service (session-aware adjust/validate/query with audit trail).
- Domain exceptions and slug/UUID patterns for import/export portability.

## Overall Assessment
The service layer is materially closer to multi-user/web readiness after F060/F061: planning snapshots are complete, nested assembly ledgering is in place, finished-goods inventory primitives exist, and the legacy production path is removed. Remaining blockers are concentrated in event service session ownership (and dependent progress/cost flows), lingering material catalog gaps, and DTO/logging consistency. Address the must-fix checklist above before treating the services as stable foundations for new features or API exposure.***
