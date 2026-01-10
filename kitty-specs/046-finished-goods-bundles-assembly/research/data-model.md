# F046 Data Model Design

**Date**: 2026-01-10
**Status**: Complete

## Overview

F046 primarily involves adding methods to existing models rather than creating new tables. The database schema changes are minimal because AssemblyRun and consumption models already exist with the required fields.

## Schema Status

### No Schema Changes Required

The following models already have all required fields:

| Model | Table | Fields Present |
|-------|-------|----------------|
| AssemblyRun | assembly_runs | `total_component_cost`, `per_unit_cost`, `event_id`, `packaging_bypassed` |
| AssemblyFinishedUnitConsumption | assembly_finished_unit_consumptions | `quantity_consumed`, `unit_cost_at_consumption`, `total_cost` |

## Model Method Additions

### FinishedUnit.calculate_current_cost()

**Purpose**: Calculate the current average cost per finished unit based on production history

**Algorithm**:
1. Query recent ProductionRuns for this FinishedUnit
2. Calculate weighted average of `per_unit_cost` based on `actual_yield`
3. Return as Decimal with 4 decimal places

**Implementation**:
```python
def calculate_current_cost(self) -> Decimal:
    """
    Calculate current average cost per unit from production history.

    Uses weighted average of per_unit_cost from recent ProductionRuns,
    weighted by actual_yield.

    Returns:
        Decimal: Average cost per unit, or Decimal("0.0000") if no production history
    """
    if not self.production_runs:
        return Decimal("0.0000")

    total_cost = Decimal("0.0000")
    total_yield = 0

    for run in self.production_runs:
        if run.actual_yield > 0 and run.per_unit_cost:
            total_cost += run.per_unit_cost * run.actual_yield
            total_yield += run.actual_yield

    if total_yield == 0:
        return Decimal("0.0000")

    return (total_cost / Decimal(str(total_yield))).quantize(Decimal("0.0001"))
```

### FinishedGood.calculate_current_cost()

**Purpose**: Calculate the current total cost to assemble one FinishedGood

**Algorithm**:
1. Iterate through components (via Composition relationships)
2. For each FinishedUnit component: get `calculate_current_cost() * quantity`
3. For each FinishedGood component (nested): get `calculate_current_cost() * quantity`
4. Sum all component costs

**Implementation**:
```python
def calculate_current_cost(self) -> Decimal:
    """
    Calculate current cost from component costs (dynamic, not stored).

    For internal use during assembly recording and event planning.
    NOT displayed in catalog UI.

    Returns:
        Decimal: Total cost for one assembly
    """
    if not self.components:
        return Decimal("0.0000")

    total = Decimal("0.0000")

    for composition in self.components:
        if composition.finished_unit_component:
            unit_cost = composition.finished_unit_component.calculate_current_cost()
            total += unit_cost * Decimal(str(composition.component_quantity))
        elif composition.finished_good_component:
            unit_cost = composition.finished_good_component.calculate_current_cost()
            total += unit_cost * Decimal(str(composition.component_quantity))
        # packaging_product_id ignored in F046 scope

    return total.quantize(Decimal("0.0001"))
```

## Model Method Fixes

### Package.get_cost_breakdown()

**Current (Broken)**:
```python
unit_cost = fg.total_cost or Decimal("0.00")  # AttributeError
```

**Fixed**:
```python
unit_cost = fg.calculate_current_cost()
```

### Package.calculate_cost()

**Current**: Returns hardcoded `Decimal("0.00")`

**Fixed**: Sum of FinishedGood costs
```python
def calculate_cost(self) -> Decimal:
    if not self.package_finished_goods:
        return Decimal("0.00")

    total = Decimal("0.00")
    for pfg in self.package_finished_goods:
        if pfg.finished_good:
            total += pfg.finished_good.calculate_current_cost() * Decimal(str(pfg.quantity))

    return total.quantize(Decimal("0.01"))
```

### PackageFinishedGood.get_line_cost()

**Current (Broken)**:
```python
unit_cost = self.finished_good.total_cost or Decimal("0.00")  # AttributeError
```

**Fixed**:
```python
unit_cost = self.finished_good.calculate_current_cost() if self.finished_good else Decimal("0.00")
```

### Composition.get_component_cost()

**Current (Broken)**:
```python
return float(self.finished_unit_component.unit_cost or 0.0)  # AttributeError
return float(self.finished_good_component.total_cost or 0.0)  # AttributeError
```

**Fixed**:
```python
def get_component_cost(self) -> float:
    if self.finished_unit_component:
        return float(self.finished_unit_component.calculate_current_cost())
    elif self.finished_good_component:
        return float(self.finished_good_component.calculate_current_cost())
    elif self.packaging_product:
        return float(self.packaging_product.purchase_price or 0.0)
    return 0.0
```

## Service Layer Fixes

### assembly_service.record_assembly()

**Current (Wrong)**:
```python
# Feature 045: Costs now tracked on instances, not definitions
unit_cost = Decimal("0.0000")  # Hardcoded!
cost = Decimal("0.0000")
```

**Fixed**:
```python
# Calculate actual cost from FinishedUnit at assembly time
unit_cost = fu.calculate_current_cost()
cost = unit_cost * Decimal(str(needed))
```

## Entity Relationship Diagram (Existing)

```
ProductionRun (cost snapshot)
    │
    ├── ProductionConsumption (ingredient costs)
    │
    └──▶ FinishedUnit (definition)
              │
              │ calculate_current_cost() → weighted avg from ProductionRuns
              │
              └──▶ Composition ◀── FinishedGood (definition)
                                        │
                                        │ calculate_current_cost() → sum of components
                                        │
                                        └──▶ PackageFinishedGood ◀── Package
                                                                        │
                                                                        │ calculate_cost() → sum of FinishedGoods
                                                                        │
                                                                        └──▶ EventRecipientPackage

AssemblyRun (cost snapshot)
    │
    ├── AssemblyFinishedUnitConsumption (component costs at assembly time)
    │
    └──▶ FinishedGood (what was assembled)
```

## Validation Rules

### FinishedUnit.calculate_current_cost()
- Returns `Decimal("0.0000")` if no production runs
- Uses only runs where `actual_yield > 0`
- Weighted by actual_yield to reflect proportional contribution

### FinishedGood.calculate_current_cost()
- Returns `Decimal("0.0000")` if no components
- Ignores `packaging_product_id` components (out of F046 scope)
- Recursively handles nested FinishedGood components

### AssemblyRun Cost Capture
- `total_component_cost` = sum of all component costs at assembly time
- `per_unit_cost` = `total_component_cost / quantity_assembled`
- Values are immutable snapshots (historical accuracy)
