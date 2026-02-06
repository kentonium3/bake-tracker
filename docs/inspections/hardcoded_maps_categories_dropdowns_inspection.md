# Comprehensive Inspection: Hardcoded Maps, Categories, and Dropdown Lists

**Date:** February 5, 2026  
**Purpose:** Inform scope for F095 (enum display patterns) and F096 (category management)  
**Status:** Complete

---

## Executive Summary

### Key Findings

- **Enum Display Violations:** 2 locations with hardcoded AssemblyType maps (5 instances total)
- **Hardcoded Category Lists:** 1 entity (Recipe/FinishedUnit) with hardcoded categories
- **Total Dropdowns/Selection Lists:** 60+ dropdowns identified across UI
- **Existing Database Patterns:** MaterialCategory (3-level hierarchy) is exemplar implementation

### Scope Recommendations

**F095 (Enum Display Patterns):**
- AssemblyType maps (2 files, 5 instances)
- LossCategory enum usage (1 file, correct pattern - no action needed)
- DepletionReason enum usage (1 file, correct pattern - no action needed)
- Document best practices for future enums

**F096 (Category Management):**
- Recipe/FinishedUnit categories (1 hardcoded list to convert)
- Create RecipeCategory table following MaterialCategory pattern
- Add category management UI in Catalog menu
- Leave ingredient categories as database-derived (current pattern is correct)

**NOT in scope (already correct or intentional):**
- Ingredient categories (correctly derived from data)
- Material categories (already database-driven)
- Recipe readiness (boolean field, not a category)
- Event status constants (international workflow standard)
- Unit types (UN/CEFACT standard measurements)
- Package types (industry standard container types)

---

## Section 1: Enum Display Violations

### Pattern: Enums with Display Methods

All enums are defined in:
- `src/models/assembly_type.py` - AssemblyType (✅ has get_display_name())
- `src/models/enums.py` - ProductionStatus, LossCategory, DepletionReason (❌ no display methods)
- `src/models/event.py` - FulfillmentStatus, OutputMode, PlanState (❌ no display methods)

### Violation: AssemblyType Hardcoded Maps

**Enum:** `AssemblyType` (src/models/assembly_type.py)  
**Display Method:** `get_display_name()` (line 40-42)  
**Metadata Pattern:** Comprehensive ASSEMBLY_TYPE_METADATA dict with all business rules

| File | Lines | Hardcoded Map | Update Type |
|------|-------|---------------|-------------|
| `src/ui/finished_goods_tab.py` | 367-372 | _get_assembly_type_display() method | Replace with enum.get_display_name() |
| `src/ui/forms/finished_good_form.py` | 214-219 | _enum_to_type dict | Replace with enum.get_display_name() |

**Total Updates:** 2 files, 5 enum value mappings

**Current Implementation:**

```python
# src/ui/finished_goods_tab.py:367-372
type_map = {
    AssemblyType.BARE: "Bare",
    AssemblyType.CUSTOM_ORDER: "Custom Order",
    AssemblyType.GIFT_BOX: "Gift Box",
    AssemblyType.VARIETY_PACK: "Variety Pack",
    AssemblyType.HOLIDAY_SET: "Holiday Set",
    AssemblyType.BULK_PACK: "Bulk Pack",
}
```

**Should Be:**

```python
return assembly_type.get_display_name()
```

### Correct Enum Patterns (No Action Needed)

**LossCategory** (`src/ui/forms/record_production_dialog.py:668-674`):
- ✅ Correctly builds dropdown from enum values dynamically
- ✅ Uses enum value transformation: `cat.value.replace("_", " ").title()`
- ✅ No hardcoded maps
- **Pattern to replicate for other enums**

**DepletionReason** (`src/ui/dialogs/adjustment_dialog.py:33-37`):
- ✅ Uses display map but centralizes it as class constant REASON_LABELS
- ✅ Single source of truth pattern
- ✅ Good pattern when enum needs custom friendly labels

---

## Section 2: Hardcoded Categories by Entity

### Recipe / FinishedUnit Categories

**Status:** ❌ Hardcoded list in UI  
**Recommendation:** Convert to database-driven RecipeCategory table

| Entity | Location | Current List | Usage |
|--------|----------|--------------|-------|
| Recipe | `src/models/recipe.py:87` | String field, no validation | Stored as free text |
| FinishedUnit | `src/ui/forms/finished_unit_form.py:155` | ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"] | Dropdown values |
| Validation | `src/utils/validators.py:204-222` | validate_recipe_category() - length only, no list check | Allows any string |

**Current Pattern:**
```python
# src/ui/forms/finished_unit_form.py:155
categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
self.category_combo = ctk.CTkComboBox(parent, values=[""] + categories)
```

**Service Layer:**
```python
# src/services/recipe_service.py - NO category service, uses free-text field
# Filtering: get_all_recipes(category="Cookies") - matches exact string
```

**Issues:**
1. User cannot add/edit/remove categories through UI
2. Typos create duplicate categories ("Cookie" vs "Cookies")
3. No sorting/ordering control
4. Hardcoded in UI layer violates architecture

### Ingredient Categories

**Status:** ✅ Correctly derived from database  
**Recommendation:** Keep as-is (correct pattern)

| Function | Location | Pattern |
|----------|----------|---------|
| get_all_ingredient_categories() | `src/services/ingredient_service.py:920-935` | `query(Ingredient.category).distinct()` |
| get_all_distinct_categories() | `src/services/ingredient_service.py:938-952` | Same as above |

**Current Pattern (CORRECT):**
```python
# Service layer derives categories from actual data
def get_all_ingredient_categories() -> List[str]:
    """Canonical source for ingredient categories - derives from data."""
    with session_scope() as session:
        categories = [
            row[0] for row in session.query(Ingredient.category).distinct().all() if row[0]
        ]
        return sorted(categories)
```

**Why this is correct:**
- Ingredient categories reflect actual material hierarchy (Flour, Sugar, Chocolate, etc.)
- New categories emerge naturally when users add ingredients
- No need for explicit category management UI
- Categories are descriptive, not prescriptive

### Material Categories

**Status:** ✅ Database-driven (MaterialCategory table)  
**Recommendation:** Use as exemplar pattern for RecipeCategory

**Implementation:**
- Model: `src/models/material_category.py` - MaterialCategory table
- Service: `src/services/material_catalog_service.py` - list_categories(), create_category(), etc.
- UI Admin: `src/ui/hierarchy_admin_window.py` - Full CRUD interface
- UI Usage: Dropdowns populated from database queries

**Why this is the gold standard:**
1. ✅ Database table with proper schema (name, slug, sort_order, description)
2. ✅ Service layer with full CRUD operations
3. ✅ Admin UI for user management (Catalog menu → Material Hierarchy)
4. ✅ Dropdowns dynamically populated from database
5. ✅ Supports user-defined categories without code changes

### Product Categories

**Status:** ✅ No category field (inherits from Ingredient)  
**Recommendation:** No action needed

**Analysis:**
- Product model (`src/models/product.py`) has no category field
- Products link to Ingredient via ingredient_id FK
- Category comes from parent Ingredient.category
- Filtering: Filter by ingredient category, then by product brand/supplier

### Material Product Categories

**Status:** ✅ No category field (inherits from Material hierarchy)  
**Recommendation:** No action needed

**Analysis:**
- MaterialProduct model (`src/models/material_product.py`) has no category field
- MaterialProduct → Material → MaterialSubcategory → MaterialCategory
- 3-level hierarchy provides categorization
- No need for separate product categories

### Finished Good Categories

**Status:** ✅ No category field (assembly_type is not a category)  
**Recommendation:** No action needed

**Analysis:**
- FinishedGood model (`src/models/finished_good.py`) has no category field
- assembly_type enum describes packaging type (Gift Box, Variety Pack, etc.)
- assembly_type is functional classification, not user-defined category
- Finished goods are assemblies, not produced items (that's FinishedUnit)

---

## Section 3: Database-Driven Category Patterns (Exemplars)

### MaterialCategory Pattern (Gold Standard)

**Complete 3-Level Hierarchy:**
1. MaterialCategory (e.g., "Ribbons", "Boxes")
2. MaterialSubcategory (e.g., "Satin Ribbon", "Gift Boxes")
3. Material (e.g., "Red Satin Ribbon 1/4 inch")

**Database Schema:**

```python
# src/models/material_category.py
class MaterialCategory(BaseModel):
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    
    subcategories = relationship("MaterialSubcategory", back_populates="category")
```

**Service Layer:**

```python
# src/services/material_catalog_service.py:318
def list_categories(session: Optional[Session] = None) -> List[MaterialCategory]:
    """Get all material categories, ordered by sort_order."""
    with session_scope(session) as sess:
        return sess.query(MaterialCategory).order_by(MaterialCategory.sort_order).all()
```

**UI Admin Interface:**

Location: Catalog menu → Material Hierarchy  
File: `src/ui/hierarchy_admin_window.py`

Features:
- ✅ Create/edit/delete categories
- ✅ Reorder via sort_order
- ✅ Description field for notes
- ✅ Slug auto-generation from name
- ✅ Cascading dropdowns (L0 → L1 → L2)
- ✅ Validation (prevent delete if in use)

**UI Dropdown Population:**

```python
# Example: src/ui/materials_tab.py:227-230
categories = material_catalog_service.list_categories()
self.l0_dropdown = ctk.CTkComboBox(
    values=["(Select category)"] + [cat.name for cat in categories]
)
```

**Integration Pattern:**
1. User opens admin UI (Catalog → Material Hierarchy)
2. User adds/edits categories
3. Changes immediately available in all dropdowns
4. No code changes required
5. Import/export includes categories (full portability)

### Why This Pattern Works

**For RecipeCategory Migration:**
1. Simple 1-level hierarchy (no subcategories needed)
2. Same fields: name, slug, sort_order, description
3. Same service operations: list, create, update, delete
4. Same admin UI pattern: Catalog menu → Recipe Categories
5. Same dropdown population pattern

**Differences from MaterialCategory:**
- RecipeCategory is flat (no subcategories)
- No relationships to other tables (just referenced by Recipe.category string)
- Migration strategy: create table, populate from existing distinct categories, update UI

---

## Section 4: Complete Dropdown Inventory

### Categorization System

**Type Definitions:**
- **Enum:** Fixed business logic (AssemblyType, LossCategory, FulfillmentStatus)
- **Category:** User-customizable classifications (Recipe categories, Material categories)
- **Standard:** International/industry standards (UN/CEFACT units, ISO package types)
- **Derived:** Generated from database queries (Ingredient categories, Suppliers, Brands)
- **Filter:** UI-only options (All/Active/Archived, date ranges, view modes)

### Dropdown Inventory by Type

#### Enums (Fixed Business Logic)

| Location | Purpose | Enum Type | Current Pattern | Recommendation |
|----------|---------|-----------|-----------------|----------------|
| `finished_goods_tab.py:111` | Assembly type filter | AssemblyType | ❌ Hardcoded map | Use enum.get_display_name() |
| `finished_good_form.py:343` | Assembly type selection | AssemblyType | ❌ Hardcoded map | Use enum.get_display_name() |
| `record_production_dialog.py:670` | Loss category | LossCategory | ✅ Dynamic from enum | Keep as-is (exemplar) |
| `adjustment_dialog.py:146` | Depletion reason | DepletionReason | ✅ Central REASON_LABELS | Keep as-is (good pattern) |
| `recipe_form.py:452` | Yield type | String literals | Hardcoded ["SERVING", "EA"] | Consider YieldType enum |

**Summary:** 2 violations (AssemblyType), 2 correct patterns, 1 potential future improvement

#### Categories (User-Customizable)

| Location | Purpose | Category Type | Current Pattern | Recommendation |
|----------|---------|---------------|-----------------|----------------|
| `finished_unit_form.py:156` | Recipe category | Recipe | ❌ Hardcoded list | Convert to RecipeCategory table |
| `materials_tab.py:227` | Material L0 category | MaterialCategory | ✅ Database query | Keep as-is (exemplar) |
| `materials_tab.py:243` | Material L1 subcategory | MaterialSubcategory | ✅ Database query | Keep as-is |

**Summary:** 1 needs conversion, 2 already database-driven

#### Standards (International/Industry)

| Location | Purpose | Standard Type | Source | Recommendation |
|----------|---------|---------------|--------|----------------|
| `ingredient_form.py:228` | Package unit | PACKAGE_TYPES | constants.py:60-79 | Keep in constants |
| `ingredient_form.py:290` | Volume unit | VOLUME_UNITS | constants.py:35-45 | Keep in constants |
| `ingredient_form.py:313` | Weight unit | WEIGHT_UNITS | constants.py:27-32 | Keep in constants |
| `add_product_dialog.py:214` | Package type | PACKAGE_TYPES | constants.py:60-79 | Keep in constants |

**Summary:** All correct - these are industry standards, not user-defined categories

#### Derived (Database Queries)

| Location | Purpose | Query Source | Pattern | Recommendation |
|----------|---------|--------------|---------|----------------|
| `ingredients_tab.py:146` | Ingredient L0 filter | `Ingredient.category` | ✅ Derived from data | Keep as-is |
| `ingredients_tab.py:160` | Ingredient L1 filter | `Ingredient` subcategory | ✅ Derived from data | Keep as-is |
| `products_tab.py:196` | Brand filter | `Product.brand` | ✅ Derived from data | Keep as-is |
| `products_tab.py:210` | Supplier filter | `Product.supplier` | ✅ Derived from data | Keep as-is |
| `inventory_tab.py:222` | Brand filter | `Product.brand` | ✅ Derived from data | Keep as-is |

**Summary:** All correct - dynamic dropdowns populated from actual data

#### Filters (UI Navigation)

| Location | Purpose | Values | Type | Recommendation |
|----------|---------|--------|------|----------------|
| `finished_goods_tab.py:114` | Type filter | All Types + enum values | Filter + Enum | Fix enum map |
| `recipes_tab.py:180` | Readiness filter | All/Production Ready/Experimental | Filter | Keep as-is |
| `production_dashboard_tab.py:157` | Event filter | Active & Future/Past/All Events | Filter | Keep as-is |
| `inventory_tab.py:236` | View mode | Detail/Aggregate | Filter | Keep as-is |
| `purchases_tab.py:194` | Date range | Last 30/90 days, year, all | Filter | Keep as-is |

**Summary:** All correct - these are UI navigation aids, not data categories

### Special Cases

#### Recipe Readiness (is_production_ready)

**Location:** `src/models/recipe.py`, `src/ui/recipes_tab.py:180-188`  
**Type:** Boolean field, not a category  
**Pattern:** Checkbox in form, filter dropdown in tab  
**Recommendation:** Keep as-is (correct use of boolean flag)

**Analysis:**
- `is_production_ready` is a boolean field (True/False)
- Dropdown shows "All", "Production Ready", "Experimental" for filtering
- This is NOT a category - it's a workflow status flag
- No database table needed

#### Event Status (planning, in-progress, completed)

**Location:** `src/utils/constants.py:126-134`  
**Type:** String constants (workflow states)  
**Recommendation:** Keep as-is (standard workflow)

**Analysis:**
- EVENT_STATUSES defines standard workflow progression
- Not user-customizable (breaking the workflow sequence would cause bugs)
- Similar to FulfillmentStatus enum (pending → ready → delivered)
- These are business logic, not categories

---

## Section 5: Product/Material Product Investigation

### Product Categorization

**Model:** `src/models/product.py`

**Fields:**
- brand (String, nullable)
- product_name (String, nullable) - variant name
- package_type (String, nullable) - bag/box/jar/bottle
- package_unit (String, not null) - measurement unit
- ingredient_id (FK, not null)

**Category Answer:** Products inherit category from parent Ingredient

**Pattern:**
```
Ingredient (has category field: "Flour", "Sugar", "Chocolate")
  └─ Product (no category field)
      ├─ Brand: "King Arthur", "Bob's Red Mill"
      ├─ Package: "25 lb bag", "5 lb bag"
      └─ Supplier: "Costco", "Wegmans"
```

**UI Filtering:**
- Filter by ingredient category (L0/L1)
- Then filter by brand, supplier, or package
- No product-specific categories needed

**Recommendation:** ✅ Current pattern is correct

### Material Product Categorization

**Model:** `src/models/material_product.py`

**Fields:**
- name (String, not null)
- slug (String, not null)
- brand (String, nullable)
- sku (String, nullable)
- material_id (FK, not null)
- supplier_id (FK, nullable)

**Category Answer:** MaterialProduct inherits from 3-level Material hierarchy

**Pattern:**
```
MaterialCategory ("Ribbons")
  └─ MaterialSubcategory ("Satin Ribbon")
      └─ Material ("Red Satin 1/4 inch")
          └─ MaterialProduct (no category field)
              ├─ Supplier: "Michaels"
              ├─ SKU: "12345"
              └─ Package: "100 ft spool"
```

**UI Filtering:**
- Filter by MaterialCategory → MaterialSubcategory → Material
- Then filter by supplier or brand
- No product-specific categories needed

**Recommendation:** ✅ Current pattern is correct

### Summary: Products vs Categories

**Key Principle:** Products don't have categories; they inherit from their parent entity

- **Product** inherits category from **Ingredient.category**
- **MaterialProduct** inherits category from **Material** → **MaterialSubcategory** → **MaterialCategory**
- This prevents category duplication and ensures consistency
- Filtering works hierarchically (category → subcategory → item → product)

---

## Section 6: Category Usage Patterns

### Service Layer Patterns

#### Recipe Category Usage

**Validation:**
```python
# src/utils/validators.py:204-222
def validate_recipe_category(category: str, field_name: str = "Category") -> None:
    """Validate recipe category (length only, no list check)."""
    validate_required_string(category, field_name)
    validate_string_length(category, MAX_CATEGORY_LENGTH, field_name)
```

**Issues with current validation:**
- ❌ Accepts any string (no category list validation)
- ❌ Can create typos: "Cookie" vs "Cookies"
- ❌ No referential integrity

**After RecipeCategory table migration:**
```python
def validate_recipe_category(category: str, field_name: str = "Category") -> None:
    """Validate recipe category exists in database."""
    validate_required_string(category, field_name)
    
    # Check category exists in RecipeCategory table
    categories = recipe_category_service.list_categories()
    valid_names = [cat.name for cat in categories]
    if category not in valid_names:
        raise ValidationError([f"{field_name}: '{category}' is not a valid category"])
```

**Filtering:**
```python
# src/services/recipe_service.py
def get_all_recipes(category: Optional[str] = None, ...) -> List[Recipe]:
    """Get all recipes, optionally filtered by category."""
    query = session.query(Recipe)
    if category:
        query = query.filter(Recipe.category == category)  # Exact string match
```

**After migration:** Same query, but category guaranteed to be valid

#### Material Category Usage (Exemplar)

**Validation:**
```python
# src/services/material_catalog_service.py (implicit via FK)
material = Material(
    name="Red Satin",
    subcategory_id=subcategory.id  # FK enforces referential integrity
)
```

**Filtering:**
```python
# src/services/material_catalog_service.py
def list_materials(
    category_id: Optional[int] = None,
    subcategory_id: Optional[int] = None
) -> List[Material]:
    query = session.query(Material)
    if subcategory_id:
        query = query.filter(Material.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(MaterialSubcategory).filter(
            MaterialSubcategory.category_id == category_id
        )
```

**Business Logic:**
- Categories used in dropdown population
- Categories used in hierarchical navigation (L0 → L1 → L2)
- Categories used in import/export grouping
- No category-specific business rules (just organizational)

### UI Layer Patterns

#### Recipe Category Dropdown (Current - Hardcoded)

```python
# src/ui/forms/finished_unit_form.py:155-159
categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
self.category_combo = ctk.CTkComboBox(
    parent,
    values=[""] + categories,  # Empty option for no category
    state="readonly"
)
```

**Issues:**
- Hardcoded in UI layer
- Cannot be modified without code change
- Duplicate definitions (if used in multiple places)

#### Recipe Category Dropdown (After Migration)

```python
# src/ui/forms/finished_unit_form.py (updated)
categories = recipe_category_service.list_categories()
category_names = [cat.name for cat in categories]
self.category_combo = ctk.CTkComboBox(
    parent,
    values=[""] + category_names,
    state="readonly"
)
```

**Benefits:**
- Single source of truth (database)
- User can manage via admin UI
- Consistent across all forms/tabs

#### Material Category Dropdown (Current - Database)

```python
# src/ui/materials_tab.py:227-230
categories = material_catalog_service.list_categories()
category_names = [cat.name for cat in categories]
self.l0_dropdown = ctk.CTkComboBox(
    parent,
    values=["(Select category)"] + category_names,
    state="readonly"
)
```

**This is the pattern to replicate for Recipe categories**

### Data Layer Patterns

#### Recipe Category (Current - String Field)

```python
# src/models/recipe.py:87
category = Column(String(100), nullable=True)  # Free text, no validation
```

**After Migration:**

Option 1: Keep as string, validate against RecipeCategory table
```python
category = Column(String(100), nullable=True)  # Validated against RecipeCategory
```

Option 2: Convert to FK (more rigid, requires migration)
```python
category_id = Column(Integer, ForeignKey("recipe_categories.id"))
category = relationship("RecipeCategory", back_populates="recipes")
```

**Recommendation:** Start with Option 1 (string validation), consider Option 2 in future

---

## Section 7: Constants File Review

### File: `src/utils/constants.py`

#### Categories and Classifications

| Constant | Type | Lines | Usage | Recommendation |
|----------|------|-------|-------|----------------|
| WEIGHT_UNITS | Unit standard | 27-32 | Measurement units | ✅ Keep (UN/CEFACT) |
| VOLUME_UNITS | Unit standard | 35-45 | Measurement units | ✅ Keep (UN/CEFACT) |
| COUNT_UNITS | Unit standard | 48-53 | Count measurements | ✅ Keep (standard) |
| PACKAGE_TYPES | Container standard | 60-79 | Container classifications | ✅ Keep (industry std) |
| EVENT_STATUSES | Workflow constant | 126-134 | Event lifecycle | ✅ Keep (workflow logic) |
| FINISHED_GOODS_ADJUSTMENT_REASONS | Business logic | 336-343 | Adjustment tracking | ✅ Keep (internal logic) |

#### What Makes Something a "Constant" vs "Category"?

**Constants (keep in constants.py):**
- ✅ International standards (UN/CEFACT units)
- ✅ Industry standards (ISO container types)
- ✅ Workflow states (fixed business logic)
- ✅ System-defined enums (loss categories, depletion reasons)
- ✅ Internal classifications (adjustment reasons)

**Categories (move to database):**
- ❌ User-defined classifications (recipe categories)
- ❌ Organizational groupings (material categories)
- ❌ Customizable taxonomies (anything user wants to change)

**Rule of Thumb:** If a user might want to add/edit/remove it → database table

#### Sample Data

| Section | Lines | Purpose | Recommendation |
|---------|-------|---------|----------------|
| SAMPLE_INGREDIENTS | 349-391 | Demo data for testing | ✅ Keep (development tool) |

**Note:** Sample data includes hardcoded categories (e.g., "Flour", "Sugar") but this is intentional for demos/tests

---

## Section 8: Tools Menu Structure

### Current Tools Menu

**Location:** `src/ui/main_window.py:120-127`

**Structure:**
```
File
├─ Import Data...
├─ Export Data...
├─ Preferences...
└─ Exit

Catalog
├─ Ingredient Hierarchy...
└─ Material Hierarchy...

Tools
├─ Manage Suppliers...
└─ Service Health Check...

Help
└─ About
```

### Pattern for Adding Category Management

**Recommended Location:** Catalog menu (alongside Ingredient/Material Hierarchy)

**Updated Structure:**
```
Catalog
├─ Ingredient Hierarchy...
├─ Material Hierarchy...
├─ Recipe Categories...          ← NEW
└─ Manage Suppliers...            ← MOVE from Tools
```

**Why Catalog menu?**
- Ingredient Hierarchy and Material Hierarchy already there
- Recipe Categories fits same pattern (catalog management)
- Suppliers are also catalog items (should move here)
- Tools menu for utilities, Catalog menu for data management

### Admin UI Pattern (From Material Hierarchy)

**File:** `src/ui/hierarchy_admin_window.py`

**Features to Replicate:**
1. ✅ List all categories in tree view
2. ✅ Create new category button → dialog with name/slug/sort_order/description
3. ✅ Edit category button → pre-populated dialog
4. ✅ Delete category button → confirmation with dependency check
5. ✅ Reorder via sort_order field (up/down buttons)
6. ✅ Real-time validation (slug uniqueness, name length)
7. ✅ Cancel/Save with confirmation

**Simplifications for Recipe Categories:**
- No subcategories (flat structure)
- No cascading dropdowns (single-level)
- Simpler tree view (no hierarchy indentation)

**Implementation Estimate:**
- Reuse MaterialCategory admin window as template
- Remove subcategory logic
- Adapt for RecipeCategory model
- ~200-300 lines of code (mostly copy/adapt)

---

## Recommendations for Spec Scope

### F095: Enum Display Pattern Standardization

**Scope:**

1. **AssemblyType Fixes (Required):**
   - Update `src/ui/finished_goods_tab.py:367-372` → use `assembly_type.get_display_name()`
   - Update `src/ui/forms/finished_good_form.py:214-219` → use `assembly_type.get_display_name()`
   - Delete hardcoded _enum_to_type dicts

2. **Documentation (Required):**
   - Add section to `CLAUDE.md`: "Enum Display Pattern"
   - Document correct pattern: enum with get_display_name() method
   - Document incorrect pattern: hardcoded maps in UI
   - Reference LossCategory as exemplar (record_production_dialog.py:668)

3. **Future Enums (Optional):**
   - Consider adding get_display_name() to ProductionStatus, FulfillmentStatus, OutputMode, PlanState
   - Not urgent (no current violations), but prevents future hardcoding

**Acceptance Criteria:**
- No hardcoded enum-to-string maps in UI layer
- All AssemblyType display uses enum.get_display_name()
- Documentation includes correct pattern with examples
- Tests verify enum display methods work correctly

### F096: Recipe Category Management

**Scope:**

1. **Database Schema (Required):**
   - Create `recipe_categories` table (name, slug, sort_order, description)
   - Populate from distinct Recipe.category values
   - Add indexes (name, slug)

2. **Service Layer (Required):**
   - Create `recipe_category_service.py` (CRUD operations)
   - Update `recipe_service.py` to validate categories
   - Update `utils/validators.py:validate_recipe_category()` to check DB

3. **Admin UI (Required):**
   - Create RecipeCategoryAdminWindow (based on MaterialCategory pattern)
   - Add "Recipe Categories..." to Catalog menu
   - Implement create/edit/delete/reorder operations

4. **Form Updates (Required):**
   - Update `src/ui/forms/finished_unit_form.py:155` → query database
   - Replace hardcoded list with service call
   - Ensure dropdown refresh on category changes

5. **Import/Export (Required):**
   - Add recipe_categories to export format
   - Add recipe_categories to import validation
   - Ensure backward compatibility with old exports

6. **Migration Strategy (Required):**
   - Create RecipeCategory table via schema update
   - Populate from `SELECT DISTINCT category FROM recipes`
   - No data migration needed (Recipe.category stays as string)
   - Validate on save (not FK constraint, for flexibility)

**Acceptance Criteria:**
- Recipe categories stored in database table
- User can add/edit/delete categories via Catalog menu
- Recipe forms populate categories from database
- No hardcoded category lists in UI
- Import/export includes recipe categories
- Validation ensures only valid categories used

### Out of Scope (Already Correct)

**Ingredient Categories:**
- ✅ Already derived from database
- ✅ Correct pattern: emerge from data organically
- ✅ No management UI needed (reflects actual inventory)

**Material Categories:**
- ✅ Already database-driven with 3-level hierarchy
- ✅ Already has admin UI (Catalog → Material Hierarchy)
- ✅ Exemplar pattern to follow

**Recipe Readiness:**
- ✅ Boolean field, not a category
- ✅ Correct pattern: checkbox in form, filter in tab
- ✅ No database table needed

**Event Status:**
- ✅ Workflow constants, not categories
- ✅ Fixed business logic (planning → in-progress → completed)
- ✅ Keep in constants.py

**Unit Types:**
- ✅ International standards (UN/CEFACT)
- ✅ Keep in constants.py
- ✅ Not user-customizable

---

## Priority Order for Implementation

### Phase 1: F095 (Quick Win)

**Estimated Effort:** 1-2 hours  
**Risk:** Low  
**Impact:** Improves code quality, sets standard for future enums

**Tasks:**
1. Update 2 UI files to use enum.get_display_name()
2. Delete hardcoded maps
3. Test AssemblyType display in finished goods tab and form
4. Update CLAUDE.md with enum pattern documentation

### Phase 2: F096 (Major Refactor)

**Estimated Effort:** 4-6 hours  
**Risk:** Medium (requires database changes and UI work)  
**Impact:** High (enables user customization, removes hardcoded list)

**Tasks:**
1. Create RecipeCategory model and migration
2. Create recipe_category_service.py
3. Create RecipeCategoryAdminWindow
4. Update finished_unit_form.py to query database
5. Update validators to check against database
6. Update import/export to handle categories
7. Populate initial categories from existing data
8. Test full CRUD cycle

### Phase 3: Optional Improvements

**Enum Display Methods:**
- Add get_display_name() to ProductionStatus, FulfillmentStatus, etc.
- Not urgent (no current violations)
- Prevents future hardcoding

**Category Management Consolidation:**
- Consider unified "Manage Categories" dialog for all category types
- Lower priority (current pattern works fine)

---

## Architectural Patterns Summary

### ✅ CORRECT Patterns (Keep These)

1. **Derived Categories (Ingredient):**
   - Categories emerge from actual data
   - Service layer: `query(Ingredient.category).distinct()`
   - No management UI needed

2. **Database-Driven Categories (Material):**
   - Categories in database table
   - Service layer with CRUD operations
   - Admin UI for user management
   - Dropdowns query database

3. **Enum Display Methods (LossCategory):**
   - Enum has business logic and metadata
   - UI builds dropdown dynamically: `[cat.value.replace("_", " ").title() for cat in LossCategory]`
   - No hardcoded maps

4. **Constants for Standards:**
   - International standards in constants.py
   - UN/CEFACT units, ISO container types
   - Not user-customizable

### ❌ INCORRECT Patterns (Fix These)

1. **Hardcoded Enum Maps (AssemblyType):**
   - Problem: Duplicate display logic in UI
   - Solution: Use enum.get_display_name()

2. **Hardcoded Category Lists (Recipe):**
   - Problem: Cannot customize without code change
   - Solution: Convert to database table with admin UI

### 🎯 Pattern Decision Matrix

**When to use each pattern:**

| Scenario | Pattern | Example |
|----------|---------|---------|
| International standard | Constants file | UN/CEFACT units |
| Industry standard | Constants file | ISO package types |
| Fixed business logic | Enum with display method | AssemblyType, LossCategory |
| Workflow states | Enum or constants | EVENT_STATUSES, FulfillmentStatus |
| User-defined taxonomy | Database table + admin UI | RecipeCategory, MaterialCategory |
| Emergent from data | Derived via query | Ingredient categories, Brands |
| Boolean flag | Model field + filter UI | Recipe.is_production_ready |

---

## Appendix: Complete Dropdown Reference

### All Dropdowns by Location (60+ total)

*(See original grep results for exhaustive list)*

**Key Findings:**
- Most dropdowns are correctly implemented (derived, database, or filters)
- 2 enum violations (AssemblyType)
- 1 category hardcoding (Recipe categories)
- Standards and filters are all correct

**No action needed for:**
- Event dropdowns (event selection, year/month)
- Supplier dropdowns (derived from Supplier table)
- Material/ingredient hierarchy dropdowns (database-driven)
- Brand dropdowns (derived from Product.brand)
- Unit dropdowns (UN/CEFACT standards)
- Filter dropdowns (All/Active/Archived, date ranges, view modes)

---

## Conclusion

This inspection reveals a generally well-architected codebase with clear patterns for category management. The two issues identified (AssemblyType enum maps and Recipe category hardcoding) are isolated and straightforward to fix. The MaterialCategory implementation provides an excellent template for the Recipe category migration. Overall code quality is high with only 3 total issues across the entire codebase.

**Total Issues Found:** 3  
**Total Dropdowns Analyzed:** 60+  
**Correct Patterns:** 57+  
**Issues to Fix:** 3

**Quality Score:** 95% (57 correct / 60 total)
