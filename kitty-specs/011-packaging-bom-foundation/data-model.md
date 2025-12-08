# Data Model: Packaging & BOM Foundation

**Feature**: 011-packaging-bom-foundation
**Date**: 2025-12-08
**Status**: Phase 1 Design

## Entity Relationship Diagram

```
                    Ingredient (is_packaging=True)
                         |
                         | 1:N
                         v
                      Product
                    /         \
                  /             \
              1:N                 1:N
              |                     |
              v                     v
        InventoryItem        Composition (as component)
                                    |
                         -----------+-----------
                        |                       |
                    assembly_id              package_id
                        |                       |
                        v                       v
                  FinishedGood              Package
```

## Model Changes

### 1. Ingredient Model

**File**: `src/models/ingredient.py`

**Changes**: Add `is_packaging` boolean field

```python
class Ingredient(BaseModel):
    __tablename__ = "ingredients"

    # ... existing fields ...

    # NEW: Packaging flag
    is_packaging = Column(Boolean, nullable=False, default=False, index=True)
```

**Indexes**: Add index on `is_packaging` for efficient filtering.

**Packaging Categories** (enforced at service/UI level):
- Bags
- Boxes
- Ribbon
- Labels
- Tissue Paper
- Wrapping
- Other Packaging

---

### 2. Composition Model

**File**: `src/models/composition.py`

**Changes**:
1. Add `package_id` FK for Package parent
2. Add `packaging_product_id` FK for Product component
3. Change `component_quantity` from Integer to Float
4. Add relationship to packaging product
5. Update constraints

```python
class Composition(BaseModel):
    __tablename__ = "compositions"

    # Parent references (exactly one must be non-null)
    assembly_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="CASCADE"),
        nullable=True, index=True  # CHANGED: nullable=True (was False)
    )

    # NEW: Package parent reference
    package_id = Column(
        Integer, ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # Component references (exactly one must be non-null)
    finished_unit_id = Column(
        Integer, ForeignKey("finished_units.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    finished_good_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # NEW: Packaging product component reference
    packaging_product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )

    # CHANGED: Float for decimal quantities (was Integer)
    component_quantity = Column(Float, nullable=False, default=1.0)

    component_notes = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    assembly = relationship(
        "FinishedGood", foreign_keys=[assembly_id],
        back_populates="components", lazy="joined"
    )

    # NEW: Package relationship
    package = relationship(
        "Package", foreign_keys=[package_id],
        back_populates="packaging_compositions", lazy="joined"
    )

    finished_unit_component = relationship(
        "FinishedUnit", foreign_keys=[finished_unit_id], lazy="joined"
    )

    finished_good_component = relationship(
        "FinishedGood", foreign_keys=[finished_good_id], lazy="joined"
    )

    # NEW: Packaging product relationship
    packaging_product = relationship(
        "Product", foreign_keys=[packaging_product_id], lazy="joined"
    )

    __table_args__ = (
        # Indexes
        Index("idx_composition_assembly", "assembly_id"),
        Index("idx_composition_package", "package_id"),
        Index("idx_composition_finished_unit", "finished_unit_id"),
        Index("idx_composition_finished_good", "finished_good_id"),
        Index("idx_composition_packaging_product", "packaging_product_id"),
        Index("idx_composition_sort_order", "assembly_id", "sort_order"),

        # NEW: Parent constraint - exactly one of assembly_id or package_id
        CheckConstraint(
            "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
            "(assembly_id IS NULL AND package_id IS NOT NULL)",
            name="ck_composition_exactly_one_parent",
        ),

        # UPDATED: Component constraint - exactly one of three options
        CheckConstraint(
            "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)",
            name="ck_composition_exactly_one_component",
        ),

        # Positive quantity constraint
        CheckConstraint(
            "component_quantity > 0",
            name="ck_composition_component_quantity_positive"
        ),

        # Non-negative sort order
        CheckConstraint(
            "sort_order >= 0",
            name="ck_composition_sort_order_non_negative"
        ),

        # Prevent self-reference
        CheckConstraint(
            "assembly_id != finished_good_id",
            name="ck_composition_no_self_reference"
        ),

        # Unique constraints
        UniqueConstraint("assembly_id", "finished_unit_id", name="uq_composition_assembly_unit"),
        UniqueConstraint("assembly_id", "finished_good_id", name="uq_composition_assembly_good"),
        UniqueConstraint("assembly_id", "packaging_product_id", name="uq_composition_assembly_packaging"),
        UniqueConstraint("package_id", "packaging_product_id", name="uq_composition_package_packaging"),
    )
```

---

### 3. Package Model

**File**: `src/models/package.py`

**Changes**: Add back-reference to packaging compositions

```python
class Package(BaseModel):
    __tablename__ = "packages"

    # ... existing fields ...

    # Existing relationship
    package_finished_goods = relationship(
        "PackageFinishedGood",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # NEW: Packaging compositions relationship
    packaging_compositions = relationship(
        "Composition",
        foreign_keys="Composition.package_id",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
```

---

## Data Flow

### Creating a Packaging Ingredient

```
User -> UI (Ingredients Tab)
    -> ingredient_service.create_ingredient(
        display_name="Cellophane Cookie Bags",
        category="Bags",
        is_packaging=True
    )
    -> Ingredient record created

User -> UI (Products dialog)
    -> product_service.create_product(
        ingredient_id=<bag_ingredient_id>,
        brand="Amazon Basics",
        package_size="100 count",
        purchase_unit="pack",
        purchase_quantity=100
    )
    -> Product record created
```

### Adding Packaging to FinishedGood

```
User -> UI (FinishedGood dialog, Packaging section)
    -> composition_service.add_packaging_to_assembly(
        assembly_id=<finished_good_id>,
        packaging_product_id=<product_id>,
        quantity=1.0,
        notes="One bag per dozen"
    )
    -> Composition record created with:
        assembly_id = <finished_good_id>
        package_id = NULL
        finished_unit_id = NULL
        finished_good_id = NULL
        packaging_product_id = <product_id>
        component_quantity = 1.0
```

### Adding Packaging to Package

```
User -> UI (Package dialog, Packaging section)
    -> composition_service.add_packaging_to_package(
        package_id=<package_id>,
        packaging_product_id=<product_id>,
        quantity=3.0,
        notes="Three sheets tissue paper"
    )
    -> Composition record created with:
        assembly_id = NULL
        package_id = <package_id>
        finished_unit_id = NULL
        finished_good_id = NULL
        packaging_product_id = <product_id>
        component_quantity = 3.0
```

### Shopping List Calculation

```
event_service.get_event_packaging_needs(event_id)
    -> For each EventRecipientPackage in event:
        -> Get package.packaging_compositions (direct packaging)
        -> For each package_finished_good:
            -> Get finished_good.components where packaging_product_id IS NOT NULL
        -> Aggregate by product_id
    -> Subtract inventory on hand
    -> Return {product_id: PackagingNeed(...)}
```

---

## Validation Rules

### Ingredient Validation
- `is_packaging` must be boolean (defaults to False)
- If `is_packaging=True`, category should be one of packaging categories (warn if not)

### Composition Validation
- Exactly one parent: `assembly_id` XOR `package_id`
- Exactly one component: `finished_unit_id` XOR `finished_good_id` XOR `packaging_product_id`
- `component_quantity` must be > 0
- If `packaging_product_id` is set, referenced Product must be for a packaging Ingredient

### Deletion Rules
- **Product deletion**: RESTRICT if referenced in any Composition.packaging_product_id
- **FinishedGood deletion**: CASCADE to Composition where assembly_id matches
- **Package deletion**: CASCADE to Composition where package_id matches

---

## Import/Export Format

### Ingredient Export (updated)
```json
{
  "ingredients": [
    {
      "display_name": "All-Purpose Flour",
      "category": "Flour",
      "is_packaging": false,
      ...
    },
    {
      "display_name": "Cellophane Cookie Bags",
      "category": "Bags",
      "is_packaging": true,
      ...
    }
  ]
}
```

### Composition Export (updated)
```json
{
  "compositions": [
    {
      "assembly_id": 1,
      "package_id": null,
      "finished_unit_id": 5,
      "finished_good_id": null,
      "packaging_product_id": null,
      "component_quantity": 12.0,
      ...
    },
    {
      "assembly_id": 1,
      "package_id": null,
      "finished_unit_id": null,
      "finished_good_id": null,
      "packaging_product_id": 23,
      "component_quantity": 1.0,
      ...
    }
  ]
}
```

---

## Test Scenarios

### Unit Tests
1. Create packaging ingredient with `is_packaging=True`
2. Create product for packaging ingredient
3. Add inventory for packaging product
4. Create composition with packaging_product_id for FinishedGood
5. Create composition with packaging_product_id for Package
6. Validate XOR constraint rejects invalid combinations
7. Validate RESTRICT prevents deletion of referenced packaging products
8. Validate Float quantities work (0.5, 1.0, 2.5)

### Integration Tests
1. Full flow: Create packaging ingredient -> product -> inventory -> composition
2. Shopping list includes packaging from both FinishedGood and Package levels
3. Shopping list correctly subtracts on-hand inventory
4. Export/import preserves all packaging data
5. Deletion cascade works correctly for Package -> Composition
