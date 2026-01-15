# Data Model: Ingredient & Material Hierarchy Admin

**Feature**: 052-ingredient-material-hierarchy-admin
**Date**: 2026-01-14

## Existing Models (No Changes Required)

This feature uses existing models without schema modifications.

### Ingredient Hierarchy (Self-Referential)

```
Ingredient
├── id: Integer (PK)
├── display_name: String(200) - unique
├── slug: String(200) - unique
├── parent_ingredient_id: Integer (FK → ingredients.id, nullable)
├── hierarchy_level: Integer (0=root, 1=mid, 2=leaf)
├── category: String(100) - deprecated, for rollback
├── ... (other fields)
└── Relationships:
    ├── parent: Ingredient (via backref)
    ├── children: List[Ingredient] (dynamic query)
    ├── products: List[Product]
    └── recipe_ingredients: List[RecipeIngredient]
```

**Hierarchy Structure**:
```
L0 (root)     → L1 (mid)           → L2 (leaf)
"Flours"      → "Wheat Flours"     → "All-Purpose Flour"
              → "Specialty Flours" → "Almond Flour"
"Chocolate"   → "Dark Chocolate"   → "Semi-Sweet Chips"
              → "Milk Chocolate"   → "Milk Chocolate Chips"
```

### Material Hierarchy (Explicit Models)

```
MaterialCategory
├── id: Integer (PK)
├── name: String(100)
├── slug: String(100) - unique
├── description: Text (nullable)
├── sort_order: Integer
└── Relationships:
    └── subcategories: List[MaterialSubcategory]

MaterialSubcategory
├── id: Integer (PK)
├── category_id: Integer (FK → material_categories.id)
├── name: String(100)
├── slug: String(100) - unique
├── description: Text (nullable)
├── sort_order: Integer
└── Relationships:
    ├── category: MaterialCategory
    └── materials: List[Material]

Material
├── id: Integer (PK)
├── subcategory_id: Integer (FK → material_subcategories.id)
├── name: String(200)
├── slug: String(200) - unique
├── description: Text (nullable)
├── base_unit_type: String(20) - 'each', 'linear_inches', 'square_inches'
├── notes: Text (nullable)
└── Relationships:
    ├── subcategory: MaterialSubcategory
    ├── products: List[MaterialProduct]
    └── units: List[MaterialUnit]
```

**Hierarchy Structure**:
```
Category      → Subcategory     → Material
"Ribbons"     → "Satin"         → "Red Satin 1-inch"
              → "Grosgrain"     → "White Grosgrain 5/8"
"Boxes"       → "Window Boxes"  → "10x10 Window Box"
              → "Gift Boxes"    → "6x6 Gift Box"
```

## Service Layer Interfaces

### IngredientHierarchyService

```python
class IngredientHierarchyService:
    """Service for ingredient hierarchy operations."""

    def get_leaf_ingredients(self, session=None) -> List[Ingredient]:
        """Get all L2 (leaf) ingredients with parent data eager-loaded."""

    def get_ingredient_with_ancestors(self, ingredient_id: int, session=None) -> dict:
        """Get ingredient with L0 and L1 ancestor names."""
        # Returns: {"l0_name": str, "l1_name": str, "l2_name": str, "ingredient": Ingredient}

    def get_hierarchy_tree(self, session=None) -> List[dict]:
        """Get full tree structure for admin UI."""
        # Returns nested structure: [{name, level, children: [...], ingredient: Ingredient}]

    def add_leaf_ingredient(self, parent_id: int, name: str, session=None) -> Ingredient:
        """Create new L2 ingredient under L1 parent."""

    def rename_ingredient(self, ingredient_id: int, new_name: str, session=None) -> Ingredient:
        """Rename ingredient (any level)."""

    def reparent_ingredient(self, ingredient_id: int, new_parent_id: int, session=None) -> Ingredient:
        """Move ingredient to new parent (validates no cycle)."""

    def get_usage_counts(self, ingredient_id: int, session=None) -> dict:
        """Get product and recipe counts for an ingredient."""
        # Returns: {"product_count": int, "recipe_count": int}
```

### MaterialHierarchyService

```python
class MaterialHierarchyService:
    """Service for material hierarchy operations."""

    def get_materials_with_parents(self, session=None) -> List[dict]:
        """Get all materials with category/subcategory names."""
        # Returns: [{"category_name": str, "subcategory_name": str, "material_name": str, "material": Material}]

    def get_hierarchy_tree(self, session=None) -> List[dict]:
        """Get full tree structure for admin UI."""

    def add_material(self, subcategory_id: int, name: str, base_unit_type: str, session=None) -> Material:
        """Create new material under subcategory."""

    def rename_item(self, item_type: str, item_id: int, new_name: str, session=None):
        """Rename category, subcategory, or material."""

    def reparent_material(self, material_id: int, new_subcategory_id: int, session=None) -> Material:
        """Move material to new subcategory."""

    def reparent_subcategory(self, subcategory_id: int, new_category_id: int, session=None):
        """Move subcategory to new category."""

    def get_usage_counts(self, material_id: int, session=None) -> dict:
        """Get product count for a material."""
        # Returns: {"product_count": int}
```

### HierarchyAdminService (Shared)

```python
class HierarchyAdminService:
    """Shared utilities for hierarchy admin operations."""

    def validate_unique_sibling_name(self, siblings: List, new_name: str, exclude_id: int = None) -> bool:
        """Check if name is unique among siblings."""

    def generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""

    def validate_no_cycle(self, item_descendants: List, proposed_parent) -> bool:
        """Ensure reparenting won't create cycle."""
```

## UI Data Requirements

### Ingredients Tab Display

| Column | Source | Notes |
|--------|--------|-------|
| L0 | `ingredient.parent.parent.display_name` | Root category |
| L1 | `ingredient.parent.display_name` | Sub-category |
| Ingredient | `ingredient.display_name` | Leaf name |
| (existing columns) | ... | Products, inventory, etc. |

### Materials Tab Display

| Column | Source | Notes |
|--------|--------|-------|
| Category | `material.subcategory.category.name` | Top level |
| Subcategory | `material.subcategory.name` | Mid level |
| Material | `material.name` | Leaf name |
| (existing columns) | ... | Products, inventory, etc. |

### Hierarchy Admin Tree

Both Ingredient and Material admin UIs display a tree with:
- Expandable/collapsible nodes
- Icons by level (folder for L0/L1/category/subcategory, leaf for L2/material)
- Selection triggers detail panel showing:
  - Item name (editable)
  - Parent path
  - Usage counts (products, recipes)
  - Action buttons: Add Child, Rename, Reparent, Delete (if no children/usage)

## Validation Rules

| Rule | Scope | Implementation |
|------|-------|----------------|
| Unique name among siblings | All levels | Check siblings before save |
| Non-empty name | All | Trim whitespace, reject empty |
| Valid hierarchy level | Ingredients | 0, 1, or 2 only (CHECK constraint exists) |
| No cycles | Reparent | Check descendants before move |
| L2 only for products/recipes | Ingredients | `hierarchy_level == 2` check |
| Valid base_unit_type | Materials | 'each', 'linear_inches', 'square_inches' |
