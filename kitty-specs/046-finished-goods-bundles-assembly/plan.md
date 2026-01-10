# Implementation Plan: F046 Finished Goods, Bundles & Assembly Tracking

**Feature Branch**: `046-finished-goods-bundles-assembly`
**Created**: 2026-01-10
**Status**: Ready for Implementation

## Technical Context

| Aspect | Decision |
|--------|----------|
| **Implementation approach** | Derive from requirements + existing codebase patterns; design doc is reference only |
| **Schema changes** | Reset/import migration model (update models, no ALTER scripts) |
| **Pattern reference** | ProductionRun/ProductionConsumption, but simpler (no yield loss, no lot tracking) |
| **UI approach** | Match design mockups where practical, following existing tab patterns |
| **Components scope** | FinishedUnits only (packaging materials deferred to F04X) |
| **Cost display** | None in CATALOG; dynamic calculation for PLAN/MAKE modes |

## Constitution Check

- [x] **Principle I (User-Centric Design)**: Implements user-requested functionality ("Finished Goods button goes nowhere")
- [x] **Principle III (Data Integrity)**: Cost snapshots immutable, no stored costs on definitions
- [x] **Principle V (Layered Architecture)**: Model/Service/UI separation maintained

## Research Findings Summary

**Key Discovery**: Significantly more infrastructure exists than design doc implied:
- AssemblyRun model already has cost fields
- AssemblyFinishedUnitConsumption already exists
- assembly_service.py has structure (just needs cost calculation fix)
- UI files exist and may need only minor adjustments

**Critical Issues to Fix**:
1. Missing `calculate_current_cost()` methods on FinishedUnit and FinishedGood
2. Broken `Package.get_cost_breakdown()` referencing removed `total_cost`
3. Broken `Composition.get_component_cost()` referencing removed attributes
4. Hardcoded zero costs in `assembly_service.record_assembly()`

See `research/research.md` for complete analysis.

## Implementation Phases

### Phase 1: Model Layer Fixes (3-4 hours)

**Goal**: Add dynamic cost calculation methods and fix broken references

#### Work Package 1.1: FinishedUnit.calculate_current_cost()

**File**: `src/models/finished_unit.py`

**Task**: Add method to calculate weighted average cost from ProductionRun history

**Implementation Notes**:
- Query `self.production_runs` relationship
- Calculate weighted average of `per_unit_cost` by `actual_yield`
- Return `Decimal("0.0000")` if no production history
- Add unit tests for various scenarios (no runs, single run, multiple runs)

#### Work Package 1.2: FinishedGood.calculate_current_cost()

**File**: `src/models/finished_good.py`

**Task**: Add method to sum component costs dynamically

**Implementation Notes**:
- Iterate `self.components` (Composition relationships)
- For FinishedUnit components: call `calculate_current_cost() * quantity`
- For FinishedGood components (nested): call `calculate_current_cost() * quantity`
- Ignore `packaging_product_id` (out of F046 scope)
- Add unit tests

#### Work Package 1.3: Fix Package Model

**File**: `src/models/package.py`

**Tasks**:
1. Fix `calculate_cost()` - currently returns hardcoded `Decimal("0.00")`
2. Fix `get_cost_breakdown()` - references non-existent `fg.total_cost`

**Implementation Notes**:
- Use `fg.calculate_current_cost()` instead of `fg.total_cost`
- Also fix `PackageFinishedGood.get_line_cost()`
- Add/update unit tests

#### Work Package 1.4: Fix Composition Model

**File**: `src/models/composition.py`

**Task**: Fix `get_component_cost()` and `get_total_cost()` methods

**Implementation Notes**:
- Use `calculate_current_cost()` instead of non-existent attributes
- Update tests

### Phase 2: Service Layer Fixes (2-3 hours)

**Goal**: Fix assembly recording to capture actual costs

#### Work Package 2.1: Fix assembly_service.record_assembly()

**File**: `src/services/assembly_service.py`

**Task**: Replace hardcoded `Decimal("0.0000")` with actual cost calculation

**Implementation Notes**:
- Lines 341-356: Calculate `unit_cost` from `fu.calculate_current_cost()`
- Lines 370-376: Calculate nested FG cost similarly
- Update `total_component_cost` calculation
- Ensure `AssemblyFinishedUnitConsumption` records capture actual costs
- Add/update integration tests

#### Work Package 2.2: Verify finished_good_service.py

**File**: `src/services/finished_good_service.py`

**Task**: Verify CRUD operations work correctly with new cost methods

**Implementation Notes**:
- Check `_recalculate_assembly_cost()` method
- Verify no lingering references to removed cost fields
- Run existing tests, fix any failures

### Phase 3: UI Verification and Fixes (2-3 hours)

**Goal**: Verify UI displays costs correctly in appropriate contexts

#### Work Package 3.1: Verify Finished Goods Tab (CATALOG Mode)

**File**: `src/ui/finished_goods_tab.py`

**Task**: Verify NO cost columns displayed in catalog view

**Implementation Notes**:
- Check grid column configuration
- Ensure `get_component_breakdown()` used (not cost methods)
- Add informational footer if not present: "No costs shown - definitions don't have prices"

#### Work Package 3.2: Verify Assembly Tab (MAKE Mode)

**File**: `src/ui/tabs/assembly_tab.py`

**Task**: Verify assembly history shows cost snapshots

**Implementation Notes**:
- Check that `per_unit_cost` and `total_component_cost` from AssemblyRun are displayed
- Verify column headers: Date, Finished Good, Qty, Cost/Unit, Total

#### Work Package 3.3: Verify Record Assembly Dialog

**File**: `src/ui/forms/record_assembly_dialog.py`

**Task**: Verify cost snapshot preview during assembly recording

**Implementation Notes**:
- Should show "Cost Snapshot (captured at assembly)" section
- Should calculate and display current component costs
- Should show inventory availability check

#### Work Package 3.4: Verify Event Planning (PLAN Mode)

**Files**: `src/ui/planning/`, `src/ui/tabs/event_status_tab.py`

**Task**: Verify Package.calculate_cost() works without errors

**Implementation Notes**:
- Navigate to event planning
- Assign a package to a recipient
- Verify cost calculates and displays (no crashes)

### Phase 4: Testing and Validation (2-3 hours)

**Goal**: Comprehensive testing of cost calculation chain

#### Work Package 4.1: Unit Tests for Cost Methods

**Files**: `src/tests/models/test_finished_unit.py`, `src/tests/models/test_finished_good.py`

**Tasks**:
1. Test `FinishedUnit.calculate_current_cost()` with various production run scenarios
2. Test `FinishedGood.calculate_current_cost()` with component hierarchies
3. Test `Package.calculate_cost()` with fixed methods

#### Work Package 4.2: Integration Tests

**File**: `src/tests/services/test_assembly_service.py`

**Tasks**:
1. Test full assembly recording with cost capture
2. Test cost chain: ProductionRun → FinishedUnit → FinishedGood → AssemblyRun
3. Test that historical costs remain immutable

#### Work Package 4.3: Manual UI Validation

**Checklist**:
- [ ] Finished Goods tab: NO cost columns visible
- [ ] Add Finished Good dialog: NO cost calculation shown
- [ ] Assembly tab: Shows cost history with per_unit_cost
- [ ] Record Assembly dialog: Shows cost snapshot preview
- [ ] Event planning: Package cost calculation works

## Acceptance Criteria Mapping

| Acceptance Criteria | Implementation |
|---------------------|----------------|
| SC-001: Create finished good in <2 min | Existing UI works |
| SC-002: Record assembly in <1 min | Existing dialog + cost fix |
| SC-003: Package cost calculation (zero crashes) | WP 1.3 Package fixes |
| SC-004: Historical costs accurate | WP 2.1 cost snapshots |
| SC-005: 100% inventory validation | Existing `check_can_assemble()` |
| SC-006: No cost columns in catalog | WP 3.1 verification |
| SC-007: Assembly history shows snapshots | WP 3.2 verification |

## Effort Estimate

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: Model Layer Fixes | 3-4 |
| Phase 2: Service Layer Fixes | 2-3 |
| Phase 3: UI Verification | 2-3 |
| Phase 4: Testing | 2-3 |
| **Total** | **9-13 hours** |

Note: Estimate reduced from design doc (21-25 hours) because much infrastructure already exists.

## Dependencies

- F044 (Finished Units): Complete
- F045 (Cost Architecture Refactor): Complete

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Hidden references to removed fields | Grep for `total_cost`, `unit_cost` before starting |
| Cost calculation performance | Use eager loading, cache if needed |
| Test coverage gaps | Run full test suite after each phase |

## Files to Modify

### Model Layer
- `src/models/finished_unit.py` - Add `calculate_current_cost()`
- `src/models/finished_good.py` - Add `calculate_current_cost()`
- `src/models/package.py` - Fix `calculate_cost()`, `get_cost_breakdown()`
- `src/models/composition.py` - Fix `get_component_cost()`, `get_total_cost()`

### Service Layer
- `src/services/assembly_service.py` - Fix cost calculation in `record_assembly()`

### UI Layer (Verification)
- `src/ui/finished_goods_tab.py` - Verify no costs
- `src/ui/tabs/assembly_tab.py` - Verify cost display
- `src/ui/forms/record_assembly_dialog.py` - Verify cost preview

### Tests
- `src/tests/models/test_finished_unit.py` - Add cost method tests
- `src/tests/models/test_finished_good.py` - Add cost method tests
- `src/tests/models/test_package.py` - Update for fixed methods
- `src/tests/services/test_assembly_service.py` - Update cost capture tests
