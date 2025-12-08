# Research: Packaging & BOM Foundation

**Feature**: 011-packaging-bom-foundation
**Date**: 2025-12-08
**Status**: Complete

## Research Questions

### RQ1: Package Packaging Association Approach

**Question**: Should Package have its own compositions, or should packaging be associated at the FinishedGood level only?

**Context**: Spec FR-007 requires support for packaging compositions on both FinishedGood assemblies and Package definitions.

**Options Evaluated**:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Extend Composition with `package_id` | Add FK to packages table alongside assembly_id | Unified model, reuses existing code | XOR constraint complexity (4 FKs now), Composition coupled to Package |
| B. PackageComposition table | New junction table mirroring Composition for packages | Clean separation, Package-specific semantics | Code duplication, two places to maintain |
| C. Virtual Assembly | Package creates FinishedGood for its packaging | No schema change to Composition | Semantic mismatch, confusing data model |

**Decision**: **Option A - Extend Composition**

**Rationale**:
- Consistent with how spec FR-004 is worded ("extend the Composition model")
- Composition already handles polymorphic components (XOR constraint)
- Adding `package_id` follows the established pattern
- Service layer can abstract the dual-parent nature
- Avoids code duplication of PackageComposition

**Implementation**:
```python
# Add to Composition model
package_id = Column(
    Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=True, index=True
)

# Update constraints: exactly one parent (assembly_id OR package_id)
CheckConstraint(
    "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
    "(assembly_id IS NULL AND package_id IS NOT NULL)",
    name="ck_composition_exactly_one_parent",
)
```

---

### RQ2: Composition Quantity Type

**Question**: Can `component_quantity` remain Integer, or does it need to support decimals for packaging?

**Current State**:
```python
# src/models/composition.py:73
component_quantity = Column(Integer, nullable=False, default=1)
```

**Requirement**: FR-006 states "Packaging compositions MUST support variable quantities (decimal values, not limited to 1)" and edge cases mention "0.5 yards ribbon".

**Decision**: **Change to Float**

**Rationale**:
- Integer cannot represent "0.5 yards ribbon"
- Float is simple and sufficient for quantity tracking
- SQLite handles Float natively
- Existing Integer values convert seamlessly (1 -> 1.0)

**Implementation**:
```python
# Change from:
component_quantity = Column(Integer, nullable=False, default=1)
# To:
component_quantity = Column(Float, nullable=False, default=1.0)
```

**Migration Impact**: None. SQLite is dynamically typed; existing integer values work with Float column. Auto-create will handle new schema.

---

### RQ3: Deletion Handling with RESTRICT

**Question**: Does `ondelete="RESTRICT"` work correctly with SQLite for FR-018?

**Requirement**: FR-018 states "System MUST prevent deletion of packaging products that are referenced in compositions."

**Research**: SQLite supports RESTRICT but requires `PRAGMA foreign_keys = ON` (enabled by default in SQLAlchemy 2.x with SQLite).

**Verification**:
```python
# src/services/database.py should have:
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

**Decision**: **Use RESTRICT on packaging_product_id FK**

**Implementation**:
```python
packaging_product_id = Column(
    Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True
)
```

**Error Handling**: Service layer should catch IntegrityError and raise user-friendly ValidationError with message like "Cannot delete product X - it is used in Y packaging compositions."

---

### RQ4: Packaging Categories Approach

**Question**: How should packaging-specific categories be handled?

**Options**:
1. Add new categories to existing category system
2. Create separate `packaging_category` field
3. Filter on `is_packaging` flag and reuse category field

**Decision**: **Option 1 - Add to existing category system**

**Rationale**:
- Simplest approach
- Category field already exists on Ingredient
- UI can filter/group by `is_packaging` flag
- Categories for packaging: Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, Other Packaging

**Implementation**: No model changes. Service/UI layer uses `is_packaging=True` to filter, then shows packaging-specific category dropdown.

---

### RQ5: Shopping List Aggregation

**Question**: How should shopping list calculation work for packaging?

**Current State**: Based on event_service.py header comments, the service calculates ingredient needs by traversing:
```
Event -> ERP -> Package -> FinishedGood -> Composition -> FinishedUnit -> Recipe
```

**Required Change**: Add parallel traversal for packaging:
```
Event -> ERP -> Package:
  - Package.compositions (where packaging_product_id is not null)
  - Package.finished_goods -> FinishedGood.compositions (where packaging_product_id is not null)
```

**Decision**: Add `get_packaging_needs()` method to event_service alongside existing ingredient aggregation.

**Implementation Sketch**:
```python
def get_event_packaging_needs(event_id: int) -> Dict[int, PackagingNeed]:
    """
    Aggregate packaging needs for an event.

    Returns dict mapping product_id -> PackagingNeed(product, total_needed, on_hand, to_buy)
    """
    needs = {}

    # Get all packages in event
    for erp in event.recipient_packages:
        package = erp.package
        quantity = erp.quantity

        # Package-level packaging
        for comp in package.compositions:
            if comp.packaging_product_id:
                add_to_needs(needs, comp.packaging_product_id, comp.component_quantity * quantity)

        # FinishedGood-level packaging
        for pfg in package.package_finished_goods:
            fg_qty = pfg.quantity * quantity
            for comp in pfg.finished_good.compositions:
                if comp.packaging_product_id:
                    add_to_needs(needs, comp.packaging_product_id, comp.component_quantity * fg_qty)

    # Subtract on-hand inventory
    for product_id, need in needs.items():
        need.on_hand = get_inventory_quantity(product_id)
        need.to_buy = max(0, need.total_needed - need.on_hand)

    return needs
```

---

## Schema Summary

### Ingredient Model
```python
# Add:
is_packaging = Column(Boolean, nullable=False, default=False)
```

### Composition Model
```python
# Add:
package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=True, index=True)
packaging_product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True)

# Change:
component_quantity = Column(Float, nullable=False, default=1.0)  # was Integer

# Update constraints:
__table_args__ = (
    # ... existing indexes ...

    # Parent constraint: exactly one of assembly_id or package_id
    CheckConstraint(
        "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
        "(assembly_id IS NULL AND package_id IS NOT NULL)",
        name="ck_composition_exactly_one_parent",
    ),

    # Component constraint: exactly one of finished_unit_id, finished_good_id, or packaging_product_id
    CheckConstraint(
        "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR "
        "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR "
        "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)",
        name="ck_composition_exactly_one_component",
    ),

    # ... existing quantity/sort constraints ...
)
```

### Package Model
No schema changes. Packaging compositions accessed via Composition.package_id relationship.

---

## Alternative Approaches Considered

### workflow-refactoring-spec.md Approach
The docs/workflow-refactoring-spec.md suggests:
- Separate PACKAGING_PRODUCT entity
- Separate FG_BOM_LINE and PKG_BOM_LINE tables

**Why Not Chosen**:
- Spec FR-003 explicitly states "Packaging ingredients MUST use the existing Ingredient -> Product -> InventoryItem chain (no separate entities)"
- Creating separate BOM tables duplicates logic already in Composition
- More tables = more maintenance

### schema_v0.5_design.md Suggestions
- Add `is_packaging` to Ingredient (ADOPTED)
- Create fg_bom_lines, pkg_bom_lines tables (NOT ADOPTED - using Composition extension instead)
- Keep Composition for FinishedGood nesting only (NOT ADOPTED - extending for packaging)

**Rationale for Deviation**: The spec takes precedence. FR-004 clearly states to extend Composition. This is simpler and more consistent than introducing new BOM tables.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Complex XOR constraint in Composition | Medium | Low | Well-tested constraint; SQLAlchemy validates at model level |
| Float precision for quantities | Low | Low | Packaging quantities are small; Float precision sufficient |
| Shopping list performance | Low | Low | Single user, small dataset; optimize later if needed |
| Existing data after schema change | Low | Medium | Export before change; reimport after; no data loss |

---

## Next Steps

1. **Phase 1**: Create data-model.md with detailed schema
2. **Phase 1**: Create service contracts in contracts/
3. **Phase 2**: Generate tasks.md via /spec-kitty.tasks
