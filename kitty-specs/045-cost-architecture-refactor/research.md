# Research: Cost Architecture Refactor

**Feature**: 045-cost-architecture-refactor
**Date**: 2026-01-09
**Purpose**: Document codebase investigation for cost field removal

---

## Decision Log

### Decision 1: No Migration Script

**Decision**: Use database reset + re-import instead of Alembic migration
**Rationale**: Single-user app with robust import/export. Simpler and safer than migration.
**Alternatives Rejected**: Alembic migration (unnecessary complexity for this use case)

### Decision 2: Standard Schema Validation for Import

**Decision**: Import either succeeds with new schema or fails. No field-specific rejection.
**Rationale**: SQLAlchemy model validation handles schema compliance automatically.
**Alternatives Rejected**: Field-by-field validation with specific error messages (over-engineering)

### Decision 3: Parallel Work Package Assignment

**Decision**: Split model+UI work by entity for parallel execution
**Rationale**: FinishedUnit and FinishedGood files are independent, enabling safe parallelization.
**Alternatives Rejected**: Sequential execution (slower, no benefit)

---

## Codebase Analysis

### Files Containing Cost References

**92 files** contain `unit_cost` or `total_cost` references. However, most refer to:
- `InventoryItem.unit_cost` (different entity, not in scope)
- `Purchase.unit_cost` (different entity, not in scope)
- Recipe calculated costs (dynamic, not stored - not in scope)

**In-scope files** (FinishedUnit/FinishedGood stored costs):

| File | Lines | Type |
|------|-------|------|
| `src/models/finished_unit.py` | 98, 133, 171-196, 198-205, 253-254, 257 | Model |
| `src/models/finished_good.py` | 76, 106, 114-142, 144-151, 173-174, 183-184, 193-195, 312, 315 | Model |
| `src/services/finished_unit_service.py` | 587, 743, 811, 1037 | Service |
| `src/services/finished_good_service.py` | 277, 1131, 1134, 1200, 1218, 1275-1276, 1294-1295, 1339, 1389, 1396, 1405, 1408, 1410, 1479, 1502 | Service |
| `src/ui/forms/finished_unit_detail.py` | 167, 324 | UI |
| `src/ui/forms/finished_good_detail.py` | 143, 426 | UI |
| `src/services/import_export_service.py` | 1138 (version only) | Service |

### Export Analysis

**Finding**: Export functions already exclude cost fields.

```python
# export_finished_units_to_json() - lines 755-800
# Does NOT include unit_cost in output dictionary

# export_all_to_json() - line 1138
# Current version: "4.0"
# Need to change to: "4.1"
```

### Import Analysis

**Finding**: Import functions don't set cost fields.

```python
# import_finished_units_from_json() - lines 1666-1745
# Creates FinishedUnit without unit_cost parameter
# SQLAlchemy default (0.0000) would apply, but column being removed
```

### Sample Data Analysis

**Finding**: Sample data files are already compliant.

Checked files:
- `test_data/sample_data_min.json` - No cost fields in finished_units/finished_goods
- `test_data/sample_data_all.json` - No cost fields in finished_units/finished_goods

Note: `test_data/inventory.json` has `unit_cost` but this is for InventoryItem entity (not in scope).

### UI Analysis

**Finding**: Cost display is only in detail views, not list/catalog views.

- `finished_units_tab.py` - Only comment mentions costs (line 88), no actual column
- `recipes_tab.py` - Shows calculated costs from recipe service (dynamic, not stored)
- `finished_unit_detail.py` - Displays `unit_cost` in detail panel (lines 167, 324)
- `finished_good_detail.py` - Displays `total_cost` in detail panel (lines 143, 426)

---

## Model Field Details

### FinishedUnit.unit_cost

```python
# Location: src/models/finished_unit.py:98
unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

# Constraint to remove: line 133
CheckConstraint("unit_cost >= 0", name="ck_finished_unit_unit_cost_non_negative")

# Methods to remove:
# - calculate_recipe_cost_per_item() - lines 171-196
# - update_unit_cost_from_recipe() - lines 198-205

# to_dict() changes needed:
# - Line 253: result["unit_cost"] = float(self.unit_cost)...
# - Line 257: result["recipe_cost_per_item"] = float(self.calculate_recipe_cost_per_item())
```

### FinishedGood.total_cost

```python
# Location: src/models/finished_good.py:76
total_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

# Constraint to remove: line 106
CheckConstraint("total_cost >= 0", name="ck_finished_good_total_cost_non_negative")

# Methods to remove:
# - calculate_component_cost() - lines 114-142
# - update_total_cost_from_components() - lines 144-151

# Methods to modify (remove cost references):
# - get_component_breakdown() - cost fields in output dict
# - to_dict() - cost fields in output dict
```

---

## Service Layer Impact

### finished_unit_service.py

Heavy cost calculation logic that needs review. Key methods:
- `_calculate_fifo_unit_cost()` - FIFO cost calculation
- `_get_inventory_item_unit_cost()` - Get cost from inventory
- `calculate_unit_cost()` - Public cost calculation method

**Approach**: Remove methods that update stored `unit_cost`. Cost calculation methods may be repurposed in F046+ for dynamic calculation.

### finished_good_service.py

Extensive cost management throughout. Key areas:
- Assembly cost calculation
- Component cost aggregation
- Pricing suggestions based on cost

**Approach**: Remove all references to stored `total_cost` field. Cost calculation logic will be reimplemented in F046+ on production/assembly instances.

---

## Test Impact Assessment

Files likely needing updates:
- `src/tests/test_models.py` - Model field tests
- `src/tests/services/test_import_export_service.py` - Export/import tests
- Any test asserting on `unit_cost` or `total_cost` fields

**Strategy**: Run pytest after each work package to identify failing tests.

---

## Parallelization Safety Analysis

### Independent Work (Safe to Parallelize)

| Work Package | Files | Agent |
|--------------|-------|-------|
| WP1 | `finished_unit.py`, `finished_unit_detail.py` | Claude |
| WP2 | `finished_good.py`, `finished_good_detail.py` | Gemini |

**Why safe**: These files have no imports between them. Each model is self-contained.

### Dependent Work (Must Be Sequential)

| Work Package | Files | Depends On |
|--------------|-------|------------|
| WP3 | `finished_unit_service.py`, `finished_good_service.py` | WP1, WP2 |
| WP4 | `import_export_service.py`, tests | WP3 |

**Why sequential**: Services import models. Tests import services.

---

## Version History Context

Current export version: **4.0** (Feature 040: F037 recipe fields, F039 event output_mode)

New version: **4.1** (Cost field removal from definitions)

Previous version bumps in codebase:
- v1.0 - Original standalone exports
- v3.0 - FinishedUnit/Composition support
- v3.1 - Package compositions
- v3.4 - Enhanced export format
- v4.0 - Recipe fields and event output_mode
