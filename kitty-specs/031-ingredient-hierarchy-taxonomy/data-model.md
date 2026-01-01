# Data Model: Ingredient Hierarchy Taxonomy

**Feature**: 031-ingredient-hierarchy-taxonomy
**Date**: 2025-12-30
**Status**: Complete

---

## Entity Changes

### Modified Entity: Ingredient

**Current State**: Flat structure with `category` string field.

**New State**: Self-referential hierarchy with parent relationship.

#### New Fields

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `parent_ingredient_id` | Integer | Yes | NULL | FK → ingredients.id | Reference to parent ingredient |
| `hierarchy_level` | Integer | No | 2 | CHECK (0, 1, 2) | Hierarchy depth: 0=root, 1=mid, 2=leaf |

#### Deprecated Fields

| Field | Status | Notes |
|-------|--------|-------|
| `category` | Deprecated | Retained for rollback safety; not displayed in UI |

#### New Relationships

| Relationship | Type | Target | Description |
|--------------|------|--------|-------------|
| `children` | One-to-Many | Ingredient | Direct child ingredients |
| `parent` | Many-to-One | Ingredient | Parent ingredient (via backref) |

#### Updated Model Definition

```python
class Ingredient(BaseModel):
    __tablename__ = 'ingredients'

    # Existing fields
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    category = Column(String(100))  # DEPRECATED - retained for rollback
    description = Column(Text)
    notes = Column(Text)
    is_packaging = Column(Boolean, default=False)

    # Density fields (existing)
    density_volume_value = Column(Float)
    density_volume_unit = Column(String(20))
    density_weight_value = Column(Float)
    density_weight_unit = Column(String(20))

    # NEW: Hierarchy fields
    parent_ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=True)
    hierarchy_level = Column(Integer, nullable=False, default=2)

    # NEW: Hierarchy relationships
    children = relationship(
        "Ingredient",
        backref=backref('parent', remote_side=[id]),
        lazy='dynamic'
    )

    # Existing relationships (unchanged)
    products = relationship("Product", back_populates="ingredient")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
```

---

## Hierarchy Level Semantics

| Level | Name | Purpose | Examples | Constraints |
|-------|------|---------|----------|-------------|
| 0 | Root | Broad domain categories | Chocolate, Flour, Sugar, Dairy | Cannot have products; cannot be used in recipes |
| 1 | Mid-tier | Functional/type groupings | Dark Chocolate, All-Purpose Flour | Cannot have products; cannot be used in recipes |
| 2 | Leaf | Specific ingredients | Semi-Sweet Chocolate Chips, King Arthur AP Flour | CAN have products; CAN be used in recipes |

---

## Validation Rules

### VR-001: Hierarchy Level Matches Parent Depth

**Rule**: `hierarchy_level = parent.hierarchy_level + 1` (or 0 if no parent)

**Enforcement**: Service layer validation on create/update

```python
def validate_hierarchy_level(ingredient_data, parent=None):
    if parent is None:
        if ingredient_data['hierarchy_level'] != 0:
            raise ValidationError("Root ingredients must have hierarchy_level=0")
    else:
        expected_level = parent.hierarchy_level + 1
        if ingredient_data['hierarchy_level'] != expected_level:
            raise ValidationError(f"Expected hierarchy_level={expected_level}")
        if expected_level > 2:
            raise ValidationError("Maximum hierarchy depth is 3 levels (0, 1, 2)")
```

---

### VR-002: Circular Reference Prevention

**Rule**: An ingredient cannot be moved to be under itself or any of its descendants.

**Enforcement**: Service layer validation on move/update parent

```python
def would_create_cycle(ingredient_id, new_parent_id, session):
    """Return True if setting new_parent_id would create a cycle."""
    if new_parent_id is None:
        return False
    if ingredient_id == new_parent_id:
        return True

    # Walk up from new_parent to root; if we hit ingredient_id, it's a cycle
    current_id = new_parent_id
    while current_id is not None:
        if current_id == ingredient_id:
            return True
        parent = session.query(Ingredient).get(current_id)
        current_id = parent.parent_ingredient_id if parent else None
    return False
```

---

### VR-003: Leaf-Only Products

**Rule**: Only ingredients with `hierarchy_level=2` can have associated Products.

**Enforcement**: Product creation/update validation

```python
def validate_product_ingredient(ingredient, session=None):
    if ingredient.hierarchy_level != 2:
        raise ValidationError(
            f"Products can only be assigned to leaf ingredients (level 2). "
            f"'{ingredient.display_name}' is level {ingredient.hierarchy_level}."
        )
```

---

### VR-004: Leaf-Only Recipe Usage

**Rule**: Only ingredients with `hierarchy_level=2` can be used in Recipes.

**Enforcement**: RecipeIngredient creation validation

```python
def validate_recipe_ingredient(ingredient, session=None):
    if ingredient.hierarchy_level != 2:
        leaf_suggestions = get_leaf_descendants(ingredient.id, session)[:3]
        raise ValidationError(
            f"Recipes require specific ingredients (level 2). "
            f"'{ingredient.display_name}' is a category. "
            f"Try: {', '.join(s.display_name for s in leaf_suggestions)}"
        )
```

---

### VR-005: Delete Protection

**Rule**: Cannot delete ingredients with children, products, or recipe usage.

**Enforcement**: Delete validation

```python
def can_delete_ingredient(ingredient_id, session):
    ingredient = session.query(Ingredient).get(ingredient_id)

    # Check for children
    if ingredient.children.count() > 0:
        raise ValidationError("Cannot delete: ingredient has child ingredients")

    # Check for products
    if session.query(Product).filter_by(ingredient_id=ingredient_id).count() > 0:
        raise ValidationError("Cannot delete: ingredient has associated products")

    # Check for recipe usage
    if session.query(RecipeIngredient).filter_by(ingredient_id=ingredient_id).count() > 0:
        raise ValidationError("Cannot delete: ingredient is used in recipes")

    return True
```

---

## Database Schema Changes

### New Columns

```sql
ALTER TABLE ingredients ADD COLUMN parent_ingredient_id INTEGER REFERENCES ingredients(id);
ALTER TABLE ingredients ADD COLUMN hierarchy_level INTEGER NOT NULL DEFAULT 2;
```

### New Indexes

```sql
CREATE INDEX idx_ingredient_parent ON ingredients(parent_ingredient_id);
CREATE INDEX idx_ingredient_hierarchy_level ON ingredients(hierarchy_level);
```

### Constraints

```sql
-- Level constraint (enforced via application, CHECK for defense-in-depth)
ALTER TABLE ingredients ADD CONSTRAINT chk_hierarchy_level
    CHECK (hierarchy_level IN (0, 1, 2));
```

---

## Migration Data Transformation

### Input Format (AI-generated suggestions)

```json
{
  "suggested_hierarchy": {
    "roots": [
      {"display_name": "Chocolate", "slug": "chocolate"}
    ],
    "mappings": {
      "semi_sweet_chocolate_chips": {
        "parent_slug": "dark_chocolate",
        "grandparent_slug": "chocolate",
        "hierarchy_level": 2,
        "confidence": 0.95
      }
    }
  }
}
```

### Output Format (Import-ready)

```json
{
  "version": "3.5",
  "ingredients": [
    {
      "display_name": "Chocolate",
      "slug": "chocolate",
      "hierarchy_level": 0,
      "parent_ingredient_id": null
    },
    {
      "display_name": "Dark Chocolate",
      "slug": "dark_chocolate",
      "hierarchy_level": 1,
      "parent_ingredient_id": null  // Resolved during import by slug
    },
    {
      "display_name": "Semi-Sweet Chocolate Chips",
      "slug": "semi_sweet_chocolate_chips",
      "hierarchy_level": 2,
      "parent_ingredient_slug": "dark_chocolate"  // FK resolved by slug
    }
  ]
}
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       INGREDIENT                             │
├─────────────────────────────────────────────────────────────┤
│ id                    INTEGER PK                            │
│ uuid                  STRING(36) UNIQUE                     │
│ display_name          STRING(200) UNIQUE                    │
│ slug                  STRING(100) UNIQUE                    │
│ parent_ingredient_id  INTEGER FK → ingredients.id (SELF)    │
│ hierarchy_level       INTEGER CHECK(0,1,2)                  │
│ category              STRING(100) [DEPRECATED]              │
│ description           TEXT                                   │
│ notes                 TEXT                                   │
│ is_packaging          BOOLEAN                                │
│ density_*             FLOAT/STRING (4 fields)               │
│ date_added            TIMESTAMP                              │
│ last_modified         TIMESTAMP                              │
├─────────────────────────────────────────────────────────────┤
│ RELATIONSHIPS:                                               │
│   children  → Ingredient[] (self-referential, one-to-many)  │
│   parent    → Ingredient   (self-referential, many-to-one)  │
│   products  → Product[]    (one-to-many, ONLY if level=2)   │
│   recipe_ingredients → RecipeIngredient[] (ONLY if level=2) │
└─────────────────────────────────────────────────────────────┘
          │
          │ parent_ingredient_id (self-referential)
          ▼
┌─────────────────────────────────────────────────────────────┐
│                       INGREDIENT                             │
│                    (same table - tree structure)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Sample Hierarchy Data

```
Chocolate (L0, id=1)
├── Dark Chocolate (L1, id=2, parent=1)
│   ├── Semi-Sweet Chocolate Chips (L2, id=3, parent=2) ← Products here
│   ├── Bittersweet Chocolate Chips (L2, id=4, parent=2)
│   └── Dark Chocolate Bar 70% (L2, id=5, parent=2)
├── Milk Chocolate (L1, id=6, parent=1)
│   ├── Milk Chocolate Chips (L2, id=7, parent=6)
│   └── Milk Chocolate Bar (L2, id=8, parent=6)
└── White Chocolate (L1, id=9, parent=1)
    └── White Chocolate Chips (L2, id=10, parent=9)

Flour (L0, id=11)
├── Wheat Flour (L1, id=12, parent=11)
│   ├── All-Purpose Flour (L2, id=13, parent=12)
│   ├── Bread Flour (L2, id=14, parent=12)
│   └── Cake Flour (L2, id=15, parent=12)
└── Alternative Flour (L1, id=16, parent=11)
    ├── Almond Flour (L2, id=17, parent=16)
    └── Coconut Flour (L2, id=18, parent=16)
```
