# F046 Research: Finished Goods, Bundles & Assembly Tracking

**Date**: 2026-01-10
**Status**: Complete

## Executive Summary

Codebase exploration reveals **significantly more infrastructure exists than the design doc implied**. The core issue is that F045 removed stored costs from definition models but left code paths referencing the removed `total_cost` fields. The fix is primarily about adding dynamic cost calculation methods and fixing broken references.

## Key Decisions

### D1: Implementation Approach
**Decision**: Derive implementation from requirements + existing codebase patterns; design doc is reference only
**Rationale**: Design doc specifies ALTER TABLE migrations, but project uses reset/import migration model
**Alternatives considered**: Follow design doc exactly (rejected due to migration model conflict)

### D2: Migration Strategy
**Decision**: Reset/import migration model - update models directly, no ALTER scripts
**Rationale**: Single-user desktop app with established pattern
**Alternatives considered**: SQLAlchemy migrations (rejected - not used in this project)

### D3: Pattern Reference
**Decision**: Follow ProductionRun/ProductionConsumption pattern, but simpler (no yield loss, no lot tracking)
**Rationale**: User confirmed assemblies are simpler than production
**Alternatives considered**: Full parity with ProductionRun (rejected as over-engineering)

### D4: Component Types
**Decision**: F046 scope = FinishedUnits only; packaging materials deferred to F04X
**Rationale**: Clarification session confirmed packaging modeled incorrectly as Ingredients
**Alternatives considered**: Include packaging in F046 (rejected - needs proper PackagingMaterial model)

## Existing Infrastructure Analysis

### Models That ALREADY Exist

| Model | Status | Notes |
|-------|--------|-------|
| AssemblyRun | Complete | Has `total_component_cost`, `per_unit_cost`, `event_id` |
| AssemblyFinishedUnitConsumption | Complete | Has `quantity_consumed`, `unit_cost_at_consumption`, `total_cost` |
| AssemblyPackagingConsumption | Complete | For packaging (out of F046 scope) |
| FinishedGood | Partial | Missing `calculate_current_cost()` method |
| FinishedUnit | Partial | Missing `calculate_current_cost()` method |
| Composition | Partial | `get_component_cost()` references non-existent attributes |
| Package | Broken | `get_cost_breakdown()` references removed `total_cost` |
| PackageFinishedGood | Broken | `get_line_cost()` references removed `total_cost` |

### Services That ALREADY Exist

| Service | Status | Notes |
|---------|--------|-------|
| assembly_service.py | Partial | Has `record_assembly()` but uses hardcoded `0.0000` for costs |
| finished_good_service.py | Complete | Full CRUD, component management, hierarchy ops |
| composition_service.py | Complete | Component operations |

### UI That ALREADY Exists

| File | Status | Notes |
|------|--------|-------|
| finished_goods_tab.py | Exists | Need to verify no cost display |
| tabs/assembly_tab.py | Exists | Need to verify state |
| forms/record_assembly_dialog.py | Exists | Need to verify cost snapshot display |
| forms/finished_good_form.py | Exists | CRUD form |
| forms/finished_good_detail.py | Exists | Detail view |

## Critical Issues Identified

### Issue 1: Missing Dynamic Cost Calculation Methods

**Location**: `src/models/finished_good.py`, `src/models/finished_unit.py`

**Problem**: F045 removed `total_cost` and `unit_cost` stored fields but no replacement dynamic calculation methods were added.

**Required Fix**: Add `calculate_current_cost()` methods to both models:
- FinishedUnit: Calculate average cost from ProductionRun history (FIFO weighted average)
- FinishedGood: Sum of component costs via `Composition.finished_unit.calculate_current_cost()`

### Issue 2: Broken Package Cost Calculation

**Location**: `src/models/package.py` lines 130-131, 216-217

**Problem**: `get_cost_breakdown()` and `get_line_cost()` reference `fg.total_cost` which was removed in F045

**Current broken code**:
```python
unit_cost = fg.total_cost or Decimal("0.00")  # AttributeError!
```

**Required Fix**: Use dynamic calculation:
```python
unit_cost = fg.calculate_current_cost()
```

### Issue 3: Hardcoded Zero Costs in Assembly Service

**Location**: `src/services/assembly_service.py` lines 341-356, 370-376

**Problem**: F045 comment says costs tracked on instances but implementation uses `Decimal("0.0000")` hardcoded

**Current code**:
```python
# Feature 045: Costs now tracked on instances, not definitions
# FinishedUnit no longer has unit_cost field
unit_cost = Decimal("0.0000")  # Wrong!
cost = Decimal("0.0000")
```

**Required Fix**: Call `calculate_current_cost()` on the FinishedUnit

### Issue 4: Composition.get_component_cost() Broken

**Location**: `src/models/composition.py` lines 212-220

**Problem**: References non-existent `unit_cost` and `total_cost` attributes

**Current broken code**:
```python
if self.finished_unit_component:
    return float(self.finished_unit_component.unit_cost or 0.0)  # AttributeError!
elif self.finished_good_component:
    return float(self.finished_good_component.total_cost or 0.0)  # AttributeError!
```

**Required Fix**: Use `calculate_current_cost()` methods

## Cost Calculation Chain

The correct cost calculation chain for F046:

```
InventoryItem (FIFO cost per unit of ingredient)
    ↓ consumed by
ProductionRun.total_ingredient_cost / actual_yield = per_unit_cost
    ↓ snapshot captured
ProductionConsumption tracks ingredient costs
    ↓ averages to
FinishedUnit.calculate_current_cost() = weighted average from recent ProductionRuns
    ↓ summed by
FinishedGood.calculate_current_cost() = sum(component.calculate_current_cost() * qty)
    ↓ used by
Package.calculate_cost() for event planning (PLAN mode)
    ↓ captured by
AssemblyRun.total_component_cost (snapshot at assembly time in MAKE mode)
```

## Scope Refinement

### Must Do (F046 Core)
1. Add `FinishedUnit.calculate_current_cost()` method
2. Add `FinishedGood.calculate_current_cost()` method
3. Fix `Package.get_cost_breakdown()` to use dynamic calculation
4. Fix `PackageFinishedGood.get_line_cost()` to use dynamic calculation
5. Fix `Composition.get_component_cost()` to use dynamic calculation
6. Fix `assembly_service.record_assembly()` to capture actual costs
7. Verify UI tabs show correct data (no costs in catalog, costs in Make mode)

### Already Done (No Work Needed)
- AssemblyRun model with cost fields
- AssemblyFinishedUnitConsumption model
- finished_good_service.py CRUD operations
- assembly_service.py structure (just needs cost fix)
- UI files exist (may need minor adjustments)

### Out of Scope (Deferred)
- Packaging materials as components (F04X)
- Assembly yield loss tracking
- Lot tracking for finished units

## Test Strategy

1. **Unit Tests**: Test `calculate_current_cost()` methods in isolation
2. **Integration Tests**: Test cost chain from ProductionRun through to AssemblyRun
3. **UI Validation**: Manual verification that:
   - Finished Goods tab shows NO cost columns
   - Assembly recording dialog shows cost snapshot
   - Assembly history shows captured costs
   - Event planning calculates package costs without errors
