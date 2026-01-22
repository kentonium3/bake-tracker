# Service Primitives & Best-Practice Readiness Review

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-20
**Reference:** `docs/design/architecture.md` (layering, definitions vs instantiations, session ownership, FIFO, export fidelity)
**Scope:** Service layer primitives for a future multi-user/web context. Deep reads: planning (`planning_service`, `batch_calculation`, `feasibility`, `progress`, `shopping_list`), production (`batch_production_service`, `production_service`), assembly (`assembly_service`), shared infra (`database.py`, `exceptions.py`), and recent material/finished-unit work from prior reviews (F056-F058). Findings focus on adherence and gaps that must be fixed before building on these services.

## Executive Summary
Core primitives (session_scope, domain exceptions, FIFO consumption, definition/instantiation separation, slug/UUID usage, import/export framing) are present and mostly consistent. However, several services violate session ownership, omit cost/consumption ledgers for nested assemblies, and leave material catalog primitives partially aligned with recent metric/FIFO requirements. Before treating the service layer as “ready” for multi-user/web, resolve the session/transaction hygiene gaps, complete cost and inventory fidelity for materials and nested finished goods, and standardize DTO typing and logging.

## Adherence Highlights
- **Layered design:** Services avoid UI imports; models carry schema only. Planning, production, and assembly expose service-level DTOs and domain exceptions (good for API surface).
- **Session primitive (`session_scope`):** Centralized in `database.py`; many services accept an optional `session` and thread it through (e.g., `batch_production_service`, `assembly_service` for packaging/material consumption).
- **Definition vs instantiation:** Production/assembly use snapshots and FIFO to cost instances; catalog entities remain costless definitions (recipes, finished units, products, material products).
- **FIFO & cost snapshotting:** Ingredient FIFO is mature; batch production records consumptions and losses; assembly captures packaging/material consumption ledgers.
- **Domain exceptions:** `exceptions.py` plus service-specific errors give API-friendly failure modes (`ValidationError`, `NotFound`, insufficiency errors).
- **Import/export framing:** Coordinated export/import exists for catalog and history; slugs/UUIDs are used for portability.

## Gaps (must address before relying on “mature” services)
- **Session ownership violations:** Planning progress/shopping/feasibility and `production_service.record_production` open their own sessions while performing multi-step operations, risking partial writes and stale reads. Caller-owned session must be enforced end-to-end.
- **Nested assembly ledger gap:** `assembly_service.record_assembly` decrements nested FinishedGood inventory without recording a consumption ledger entry or cost snapshot. This breaks auditability and export completeness.
- **Material catalog alignment:** Materials UI/options still imperial; `material_inventory` exports are missing lots in coordinated export/import; FIFO consumption for materials assumes linear cm in some callers; material listing uses the wrong cost field. These primitives must be fixed to make material services dependable.
- **Planning snapshot completeness:** `planning_service` leaves aggregated ingredients/cost baselines empty and staleness ignores composition/yield changes. Plans are not yet a dependable contract for downstream workflows or API exposure.
- **DTO/typing consistency:** Costs sometimes returned as `Decimal`, sometimes as string; units sometimes implicit. Standardize DTOs for API readiness.
- **Observability:** Minimal structured logging around plan calc, feasibility, production/assembly decisions; harder to debug in multi-user/web contexts.

## Must-Fix Checklist (mature surface hardening)
1. **Session hygiene:** Remove internal `session_scope`/commits from planning/shopping/feasibility/progress and `production_service`; require caller to pass session and thread it to all downstream calls (including FIFO consumption).
2. **Nested FG ledger:** Add consumption ledger + cost snapshot for nested FinishedGoods in `assembly_service`; include in exports.
3. **Material primitives:**
   - UI/options to metric base units; fix unit-aware FIFO (linear/square/each).
   - Use `cost_per_unit` in material listings; fix unit converter coverage/tests for area/each.
   - Export/import `MaterialInventoryItem` lots and correct purchase fields in coordinated flows.
4. **Planning snapshots:** Populate aggregated ingredients/cost baselines; extend staleness to recipe/FinishedUnit/composition/material/package changes.
5. **DTO normalization & logging:** Standardize numeric/Decimal/string conventions and add structured logs for plan calc, feasibility, and production/assembly execution.

## Ready Primitives You Can Build On (after above fixes)
- Ingredient/product catalog + FIFO (food) with batch production ledger and loss tracking.
- Recipes/FinishedUnits as unified yield source; batch production uses snapshots and FIFO correctly.
- Assembly service for packaging/material consumption (once nested FG ledger is added).
- Domain exceptions and slug/UUID patterns for import/export portability.

## Overall Assessment
The service layer has the right primitives in place but needs hygiene and fidelity fixes to be safe for multi-user/web evolution. Address the must-fix checklist above before treating the catalog and core services as stable foundations for new features or API exposure.***
