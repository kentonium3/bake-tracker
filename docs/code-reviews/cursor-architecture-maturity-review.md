# Code Review Report: Architecture & Service Maturity

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-20
**Reference:** `docs/design/architecture.md` (2026-01-19)
**Scope Focus:** Planning/Production (least mature), service boundaries, session/transaction patterns, primitive/unit/cost handling, import/export fidelity, observability/testing.

## Executive Summary
Planning and production surfaces are only partially aligned with the architecture intent. Core inventory/production services (batch production, FIFO) are relatively mature, but newer orchestration layers (planning facade, progress/shopping/feasibility) and some production/assembly flows leak sessions across service boundaries, mix transactional and non-transactional calls, and lack cost/inventory fidelity for nested assemblies. Several primitives (units, decimals, slugs) are inconsistently enforced. To unlock the next feature wave, standardize session/transaction handoff, harden definition-vs-instantiation invariants, and close gaps in assembly/package/material cost tracking and planning freshness.

## Review Scope

**Primary Areas Read:**
- Planning: `src/services/planning/{planning_service, batch_calculation, feasibility, progress, shopping_list}.py`
- Production/Assembly: `src/services/{batch_production_service, production_service, assembly_service}.py`

**Comparators (maturity reference):**
- FIFO/consumption patterns in `batch_production_service`
- Material/ingredient FIFO services (recent reviews)
- Architecture intent from `docs/design/architecture.md`

## Findings

### Critical Issues

**Session boundary violations break atomicity**
- **Locations:** `planning/progress.py` (`event_service.get_*` without shared session); `production_service.record_production` calls `inventory_item_service.consume_fifo` without passing the open session; `assembly_service.record_assembly` mixes external services but is careful—contrast shows inconsistency.
- **Problem:** Mixed session ownership inside a single logical operation risks stale reads and cross-transaction divergence (e.g., production records saved but FIFO consumption in a different session could fail/rollback separately).
- **Impact:** Potential partial writes and data drift under failure; harder to reason about transactions when moving to multi-user or API.
- **Recommendation:** Enforce “caller owns session” across service calls; every downstream call accepts `session` and does not open its own. Add lint/checklist; refactor production/planning facades to pass sessions through.

**Planning snapshots omit ingredient aggregation and cost baselines**
- **Location:** `planning/planning_service.calculate_plan` (calculation_results["aggregated_ingredients"] is TODO; shopping list uses live inventory only).
- **Problem:** Snapshots lack ingredient-level requirements/cost baselines; staleness and downstream views cannot reconstruct what was planned vs current state.
- **Impact:** Planning dashboards and audits cannot reconcile production/assembly progress to planned needs; future AI/API inputs lack a stable contract.
- **Recommendation:** Populate aggregated ingredients from recipe aggregation (post-F056 yield model); store costs/units in snapshot; extend staleness to include ingredient changes.

**Assembly cost and ledger gaps for nested finished goods**
- **Location:** `assembly_service.record_assembly` (nested FinishedGood consumption decrements inventory but records no ledger entry; cost uses `calculate_current_cost` but no per-component trace).
- **Problem:** No consumption ledger for nested finished goods; costs are inferred, not snapped; auditability and export fidelity suffer.
- **Impact:** Cannot audit component usage for bundles; back-compat exports miss nested consumption; cost variance impossible to trace.
- **Recommendation:** Create consumption records for nested finished goods analogous to finished-unit consumptions; ensure costs snap at consumption time.

### Major Concerns

**Planning progress uses detached data sources**
- **Location:** `planning/progress.py` derives progress from `event_service` helpers that open their own sessions; availability/feasibility not integrated.
- **Problem:** Progress can be stale vs current transaction; no linkage to the plan snapshot; available_to_assemble hard-coded to 0.
- **Recommendation:** Rework progress to operate off the snapshot + live deltas in one session; compute availability_to_assemble via feasibility service; add transactional consistency.

**Staleness checks miss key mutations**
- **Location:** `planning/planning_service._check_staleness_impl`
- **Problem:** Tracks `Composition.created_at` but not updates/deletes; ignores FinishedUnit yield changes, packaging assignments, or material requirements.
- **Impact:** Plans may be marked fresh while BOM/yield changed, leading to under/over-production.
- **Recommendation:** Add updated_at on Composition (or hash of contents), include FinishedUnit and material/package requirement timestamps; invalidate on schema-affecting changes.

**Shopping completion mutates snapshot outside caller transaction**
- **Location:** `planning/shopping_list.py` (`mark_shopping_complete` commits inside helper)
- **Problem:** Commits a new transaction regardless of caller, making it impossible to coordinate with upstream plan updates.
- **Impact:** Partial updates and double-commit patterns under multi-step UI/API flows.
- **Recommendation:** Accept session and avoid internal commits; follow session ownership rule.

**Production service lags feature parity**
- **Location:** `production_service.record_production`
- **Problems:** Uses `inventory_item_service` without session (atomicity risk); no recipe snapshot link; no loss/cost variance tracking like `batch_production_service`.
- **Impact:** Two competing production paths with different invariants; older one is weaker and unsafe for cost/audit.
- **Recommendation:** Deprecate or align to `batch_production_service` (snapshot + loss + unified session).

**Assembly feasibility lacks material/packaging cost awareness**
- **Location:** `planning/feasibility.py` and `assembly_service.check_can_assemble`
- **Problem:** Feasibility only checks availability; no cost snapshot or packaging/material assignment validation besides inventory.
- **Impact:** Plan may be “feasible” but produces wrong cost signals; generic packaging/material assignment gaps persist.
- **Recommendation:** Extend feasibility to include material assignments and cost estimation; surface blockers distinctly (inventory vs assignment).

### Minor Issues

- `progress.py` averages percentages, capping at 100 per target, but mixes detached session reads—consider computing directly from production/assembly runs.
- `shopping_list.py` and `progress.py` rely on `event_service` functions that themselves open sessions; violates layering intent.
- Missing observability: no structured logging around plan calc/feasibility/progress to trace decisions.
- Decimal/string handling varies (some costs returned as Decimal, others as str); normalize DTO contracts.

### Positive Observations

- Batch production path (`batch_production_service`) follows good patterns: explicit session threading, dry-run vs commit, snapshots, loss tracking, FIFO ledger.
- Planning facade cleanly enumerates phases and provides staleness guardrails; good DTO discipline for batch results and feasibility results.
- Feasibility/assembly/production expose domain-specific exceptions, aiding UI/API clarity.

## Spec/Intent Compliance (architecture.md)
- **Layering:** Many services respect UI→service→model separation, but planning/progress/shopping still call helpers that self-manage sessions, violating “caller owns session”.
- **Definition vs Instantiation:** Production/assembly respect instantiation costs; planning snapshots do not yet capture the planned ingredient/cost view (missing instantiation intent).
- **FIFO & snapshots:** Batch production and assembly packaging/material consumption align; production_service path and nested-finished-good assembly ledger are misaligned.
- **Import/Export fidelity:** Assembly and production exports exist, but planning outputs are not exported; nested FG consumption and shopping/plan state are absent from coordinated export.

## Recommendations Priority

**Must Fix (foundational)**
1. Enforce session ownership across services; audit and refactor calls to avoid internal session_scope when a session is provided (planning/progress/shopping, production_service).
2. Populate planning snapshots with aggregated ingredient requirements and unit/cost baselines; include FinishedUnit yield and composition change detection in staleness.
3. Add ledger + cost snapshot for nested FinishedGood consumption in `assembly_service`; align DTO/export accordingly.
4. Deprecate or align `production_service.record_production` to the batch production pattern (snapshot + loss + unified session).
5. Remove internal commits in planning/shopping helpers; caller controls transaction.

**Should Fix (near-term hardening)**
1. Compute progress/available_to_assemble within a single session and tie to plan snapshot; integrate feasibility for availability.
2. Normalize DTO types (Decimals as strings or Decimals consistently) and unit handling across planning/production/assembly.
3. Add observability: structured logs for plan calc, feasibility, progress, and assembly/production decisions.
4. Extend feasibility to surface material/packaging assignment blockers distinctly from inventory blockers.

**Consider for Future**
1. Export/import planning snapshots (requirements, shopping status) for backup/API parity.
2. Composition versioning or hashing to simplify staleness detection.
3. Unified cost model helpers (per-unit, snapshot, loss) shared by production and assembly.

## Priority Gaps to Fix in Mature Areas (pre-req for new specs)
- **Material catalog/UI alignment:** Update materials UI to use metric base units; fix FIFO consumption to respect base unit type (linear/square/each); include `MaterialInventoryItem` lots and correct purchase fields in coordinated export/import.
- **Material costing and listing:** Use `cost_per_unit` in material catalog listings; ensure area/each conversions are covered by unit converter and tests.
- **Assembly ledger completeness:** Add consumption ledger entries (and cost snapshot) for nested FinishedGoods; keep packaging/material consumption already ledgered.
- **Session hygiene in shared services:** Remove internal commits/session_scope from shopping/progress/feasibility/planning helpers; caller owns session for atomicity.
- **Production path parity:** Align or deprecate `production_service.record_production` in favor of the snapshot/loss-aware `batch_production_service`.

## Overall Assessment
Needs targeted hardening. Core FIFO and batch production are solid, but planning/assembly orchestration and older production paths have boundary and fidelity gaps. Addressing session ownership, snapshot completeness, and nested-assembly ledgering will bring the services in line with the architecture intent and reduce risk for upcoming features. Would not treat planning/production orchestration as “mature” until must-fix items are resolved and tests cover the new invariants.***
