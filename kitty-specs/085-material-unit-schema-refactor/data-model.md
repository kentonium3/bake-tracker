# Data Model: MaterialUnit Schema Refactor

**Feature**: 085-material-unit-schema-refactor
**Date**: 2026-01-30

## Entity Changes

### MaterialUnit (MODIFIED)

**Current Schema**:
```
MaterialUnit
├── id (PK)
├── uuid
├── material_id (FK → materials.id, CASCADE) ← REMOVE
├── name (String 200, NOT NULL)
├── slug (String 200, NOT NULL, UNIQUE)
├── quantity_per_unit (Float, NOT NULL, >0)
└── description (Text, nullable)
```

**New Schema**:
```
MaterialUnit
├── id (PK)
├── uuid
├── material_product_id (FK → material_products.id, CASCADE) ← ADD
├── name (String 200, NOT NULL)
├── slug (String 200, NOT NULL) ← UNIQUE per product, not global
├── quantity_per_unit (Float, NOT NULL, >0)
└── description (Text, nullable)
```

**Changes**:
| Field | Change | Details |
|-------|--------|---------|
| `material_id` | REMOVE | Drop FK to materials table |
| `material_product_id` | ADD | New FK to material_products table, NOT NULL, CASCADE delete |
| `slug` | MODIFY | Unique constraint scoped to material_product_id (not global) |

**Relationship Changes**:
- REMOVE: `material` → Material (back_populates="units")
- ADD: `material_product` → MaterialProduct (back_populates="material_units", lazy="joined")

---

### MaterialProduct (MODIFIED)

**Current Schema**:
```
MaterialProduct
├── id (PK)
├── uuid
├── material_id (FK → materials.id)
├── name, slug, brand, etc.
├── package_count (Integer, nullable)
├── package_length_m (Float, nullable)
├── package_sq_m (Float, nullable)
└── [relationships: material, supplier, purchases, inventory_items]
```

**New Schema** (additions only):
```
MaterialProduct
├── ... (existing fields unchanged)
└── material_units (relationship) ← ADD
```

**Relationship Added**:
```python
material_units = relationship(
    "MaterialUnit",
    back_populates="material_product",
    cascade="all, delete-orphan",
    lazy="select",
)
```

---

### Material (MODIFIED)

**Current Schema**:
```
Material
├── id (PK)
├── uuid
├── subcategory_id (FK)
├── name, slug, base_unit_type, description
├── products (relationship → MaterialProduct)
└── units (relationship → MaterialUnit) ← REMOVE
```

**New Schema**:
```
Material
├── id (PK)
├── uuid
├── subcategory_id (FK)
├── name, slug, base_unit_type, description
└── products (relationship → MaterialProduct)
    └── [MaterialProduct now owns MaterialUnits]
```

**Relationship Removed**:
- `units` → MaterialUnit (back_populates="material")

---

### Composition (MODIFIED)

**Current Schema**:
```
Composition
├── id (PK)
├── assembly_id (FK → assemblies.id)
├── finished_unit_id (FK, nullable)
├── finished_good_id (FK, nullable)
├── packaging_product_id (FK, nullable)
├── material_unit_id (FK, nullable)
├── material_id (FK, nullable) ← REMOVE
├── quantity, notes, sort_order
└── XOR constraint: exactly one of 5 FKs NOT NULL
```

**New Schema**:
```
Composition
├── id (PK)
├── assembly_id (FK → assemblies.id)
├── finished_unit_id (FK, nullable)
├── finished_good_id (FK, nullable)
├── packaging_product_id (FK, nullable)
├── material_unit_id (FK, nullable)
├── quantity, notes, sort_order
└── XOR constraint: exactly one of 4 FKs NOT NULL
```

**Changes**:
| Field | Change | Details |
|-------|--------|---------|
| `material_id` | REMOVE | Drop FK to materials table |
| `material_component` | REMOVE | Drop relationship |
| XOR constraint | MODIFY | 5-way → 4-way (remove material_id condition) |

**Methods to Update**:
- `component_type` property: Remove "material" case
- `component_id` property: Remove `or self.material_id`
- `component_name` property: Remove material_component branch
- `get_component_cost()`: Remove material_component branch
- `_estimate_material_cost()`: Remove entirely
- `validate_polymorphic_constraint()`: Update to 4-way validation
- `create_material_placeholder_composition()`: REMOVE factory method

---

## Entity Relationships Diagram

```
┌─────────────────────┐
│     Material        │
├─────────────────────┤
│ id                  │
│ name                │
│ slug                │
│ base_unit_type      │
└─────────┬───────────┘
          │ 1:N
          ▼
┌─────────────────────┐
│  MaterialProduct    │
├─────────────────────┤
│ id                  │
│ material_id (FK)    │──────► Material
│ name                │
│ slug                │
│ package_count       │
│ package_length_m    │
│ package_sq_m        │
└─────────┬───────────┘
          │ 1:N (NEW)
          ▼
┌─────────────────────┐
│   MaterialUnit      │
├─────────────────────┤
│ id                  │
│ material_product_id │──────► MaterialProduct (NEW)
│ name                │
│ slug                │
│ quantity_per_unit   │
└─────────┬───────────┘
          │ 0:N
          ▼
┌─────────────────────┐
│    Composition      │
├─────────────────────┤
│ id                  │
│ assembly_id         │
│ material_unit_id    │──────► MaterialUnit
│ [3 other FK types]  │
│ XOR: exactly 1 set  │
└─────────────────────┘
```

---

## Migration Transformation

### MaterialUnit Migration

**Input** (old schema):
```json
{
  "material_slug": "red-satin-ribbon",
  "name": "6-inch Red Ribbon",
  "slug": "6-inch-red-ribbon",
  "quantity_per_unit": 0.1524
}
```

**Transformation Logic**:
1. Lookup Material by `material_slug`
2. Get all MaterialProducts for that Material
3. For each MaterialProduct:
   - Create new MaterialUnit with `material_product_slug` = product.slug
   - Preserve name, quantity_per_unit, description
   - Generate unique slug if collision within product

**Output** (new schema - duplicated per product):
```json
[
  {
    "material_product_slug": "michaels-red-satin-25m",
    "name": "6-inch Red Ribbon",
    "slug": "6-inch-red-ribbon",
    "quantity_per_unit": 0.1524
  },
  {
    "material_product_slug": "joann-red-satin-50m",
    "name": "6-inch Red Ribbon",
    "slug": "6-inch-red-ribbon",
    "quantity_per_unit": 0.1524
  }
]
```

### Composition Migration

**Records with `material_id`**: SKIP with log entry

```
SKIPPED: Composition id=42, assembly='Holiday Box A', material='Red Satin Ribbon'
  Reason: Generic material_id references cannot be auto-migrated
  Action: User must edit export file to specify material_unit_slug instead
```

---

## Validation Rules

### MaterialUnit Validation

| Rule | Implementation |
|------|----------------|
| `material_product_id` NOT NULL | FK constraint |
| `name` NOT NULL, non-empty | Service validation |
| `name` unique per product | UniqueConstraint(material_product_id, name) |
| `slug` unique per product | UniqueConstraint(material_product_id, slug) |
| `quantity_per_unit` > 0 | CheckConstraint |

### Auto-Generation Rules

| Condition | Action |
|-----------|--------|
| `package_count IS NOT NULL` AND `package_length_m IS NULL` AND `package_sq_m IS NULL` | Auto-create "1 {product.name}" MaterialUnit |
| Any other combination | No auto-generation |

### Composition Validation

| Rule | Implementation |
|------|----------------|
| Exactly one component FK set | 4-way XOR CheckConstraint |
| No `material_id` field | Field removed from model |
