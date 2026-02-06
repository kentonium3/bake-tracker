# F096: Recipe Category Management System

**Version**: 1.1
**Priority**: MEDIUM
**Type**: Full Stack Feature

**Revision History:**
- v1.1 (2026-02-05): Corrected menu placement - Catalog menu, not Tools → Catalog
- v1.0 (2026-02-05): Initial specification

---

## Executive Summary

Current gaps:
- ❌ Recipe categories hardcoded as list in `finished_unit_form.py:155`
- ❌ Users cannot customize recipe taxonomy
- ❌ No admin UI for category management
- ❌ Categories: `["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]`

This spec implements a database-driven recipe category system following the proven MaterialCategory pattern, with admin UI in Catalog menu for user customization.

---

## Problem Statement

**Current State (HARDCODED):**
```
Recipe Categories
├─ ❌ Hardcoded list in finished_unit_form.py:155
├─ ❌ Cannot add "Tarts", "Pastries", etc. without code change
├─ ❌ No admin UI for management
└─ ❌ Recipe.category stored as string, validated against hardcoded list

Catalog Menu Structure
├─ ✅ Ingredient Hierarchy (admin UI)
├─ ✅ Material Hierarchy (admin UI)
└─ ❌ Recipe Categories missing (should be here)
```

**Target State (DATABASE-DRIVEN):**
```
Recipe Categories
├─ ✅ recipe_categories table with CRUD operations
├─ ✅ Users can customize taxonomy via admin UI
├─ ✅ Admin UI in Catalog → "Recipe Categories..."
└─ ✅ Recipe.category validates against database

Catalog Menu Structure
├─ ✅ Ingredient Hierarchy
├─ ✅ Material Hierarchy
└─ ✅ Recipe Categories (new)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Cursor Inspection Report**
   - Find `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` - full analysis
   - Find `docs/inspections/hardcoded_maps_categories_summary.md` - executive summary
   - Study Section 2: Hardcoded Categories by Entity
   - Note MaterialCategory as exemplar pattern to follow

2. **MaterialCategory Pattern (EXEMPLAR)**
   - Find `src/models/material_category.py` - model with 3-level hierarchy
   - Find `src/services/material_category_service.py` - CRUD operations
   - Find `src/ui/materials/material_categories_dialog.py` - admin UI
   - Study complete pattern: model → service → UI

3. **Current Recipe Category Usage**
   - Find `src/ui/finished_goods/finished_unit_form.py:155` - hardcoded list
   - Find `src/models/recipe.py` - Recipe.category field (string)
   - Find `src/services/recipe_service.py` - how categories are used/validated
   - Note migration strategy: keep string field, validate on save

4. **Catalog Menu Structure**
   - Find `src/ui/main_window.py` - menu bar implementation
   - Study Catalog menu with Ingredient Hierarchy and Material Hierarchy
   - Note pattern for adding menu items
   - Recipe Categories will be third item in Catalog menu

---

## Requirements Reference

This specification implements:
- **Code Quality Principle I.A**: User Data Sovereignty
  - Users control their own category taxonomies
- **Code Quality Principle VI.D**: API Consistency & Contracts
  - Database-driven categories (consistent with MaterialCategory)
- **Code Quality Principle VI.G**: Code Organization Patterns
  - Pattern consistency across entity types

From: `docs/design/code_quality_principles_revised.md` (v1.0)

Also addresses findings from:
- `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` - Section 2: Recipe Categories

---

## Functional Requirements

### FR-1: Create RecipeCategory Model

**What it must do:**
- Create `recipe_categories` table in database
- Include fields: id, name, slug, sort_order, description
- Support CRUD operations via service layer
- Follow MaterialCategory table structure (simplified, no hierarchy)

**Pattern reference:** Study `src/models/material_category.py` - copy structure, simplify (no parent/hierarchy)

**Table schema:**
```sql
CREATE TABLE recipe_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Model fields:**
- `name` - Display name (e.g., "Cakes", "Pastries")
- `slug` - URL-safe identifier (e.g., "cakes", "pastries")
- `sort_order` - Display order in dropdowns (default 0)
- `description` - Optional notes about category usage
- Standard timestamps (created_at, updated_at)

**Success criteria:**
- [ ] RecipeCategory model exists in src/models/
- [ ] Table created via migration
- [ ] All fields defined with proper types and constraints
- [ ] Follows BaseModel pattern for timestamps
- [ ] Unique constraints on name and slug

---

### FR-2: Create Recipe Category Service

**What it must do:**
- Create `recipe_category_service.py` with CRUD operations
- Implement list_categories(), create_category(), update_category(), delete_category()
- Include validation (prevent delete if categories in use)
- Follow MaterialCategoryService pattern exactly

**Pattern reference:** Study `src/services/material_category_service.py` - copy CRUD patterns

**Service functions needed:**
```python
def list_categories(
    session: Optional[Session] = None
) -> List[RecipeCategory]:
    """List all recipe categories ordered by sort_order."""

def create_category(
    name: str,
    slug: str,
    sort_order: int = 0,
    description: Optional[str] = None,
    session: Optional[Session] = None
) -> RecipeCategory:
    """Create new recipe category."""

def update_category(
    category_id: int,
    name: Optional[str] = None,
    sort_order: Optional[int] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None
) -> RecipeCategory:
    """Update recipe category."""

def delete_category(
    category_id: int,
    session: Optional[Session] = None
) -> None:
    """Delete category if not in use."""

def get_category_by_name(
    name: str,
    session: Optional[Session] = None
) -> Optional[RecipeCategory]:
    """Get category by name."""

def is_category_in_use(
    category_id: int,
    session: Optional[Session] = None
) -> bool:
    """Check if category used by any recipes."""
```

**Validation requirements:**
- Prevent delete if category used by recipes
- Ensure unique names and slugs
- Auto-generate slug from name if not provided
- Validate sort_order is non-negative

**Success criteria:**
- [ ] recipe_category_service.py exists with all CRUD functions
- [ ] All functions follow session parameter pattern
- [ ] Delete validation prevents orphaning recipes
- [ ] Slug auto-generation works
- [ ] Service follows MaterialCategoryService pattern

---

### FR-3: Create Recipe Category Admin UI

**What it must do:**
- Create admin dialog for recipe category management
- Add to Catalog menu → "Recipe Categories..."
- Support create, edit, delete, reorder operations
- Follow MaterialCategoriesDialog UI pattern

**Pattern reference:** Study `src/ui/materials/material_categories_dialog.py` - copy UI structure exactly

**Menu placement:**
```
Catalog Menu
├─ Ingredient Hierarchy
├─ Material Hierarchy
└─ Recipe Categories (NEW)
```

**UI requirements:**
- Dialog accessible from Catalog → "Recipe Categories..." menu item
- List view showing all categories with sort order
- Add/Edit/Delete buttons
- Drag-to-reorder categories (updates sort_order)
- Delete confirmation with "in use" check
- Form fields: Name, Description, Sort Order
- Save/Cancel buttons

**UI components to create:**
- `src/ui/catalog/recipe_categories_dialog.py` - main dialog
- Integration with Catalog menu in main_window.py

**Success criteria:**
- [ ] Recipe Categories dialog exists and is functional
- [ ] Accessible via Catalog → "Recipe Categories..." menu item
- [ ] All CRUD operations work
- [ ] Drag-to-reorder updates sort_order
- [ ] Delete prevented if category in use
- [ ] UI follows MaterialCategoriesDialog pattern
- [ ] Consistent with Ingredient/Material Hierarchy placement

---

### FR-4: Update Finished Unit Form

**What it must do:**
- Replace hardcoded category list with database query
- Populate dropdown from recipe_category_service.list_categories()
- Validate selected category against database on save
- Allow typing custom category (not in database) with warning

**Pattern reference:** Study how material dropdowns populate from database

**Current code (finished_unit_form.py:155):**
```python
# BEFORE - Hardcoded
categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
self.category_combo = ctk.CTkComboBox(values=categories)
```

**Target code:**
```python
# AFTER - Database-driven
categories = [cat.name for cat in recipe_category_service.list_categories()]
self.category_combo = ctk.CTkComboBox(values=categories)
```

**Validation on save:**
- Check if entered category exists in database
- If not, show warning: "Category 'X' not in database. Add it via Catalog → Recipe Categories first?"
- Option to auto-add category or cancel save

**Success criteria:**
- [ ] Hardcoded list removed from finished_unit_form.py
- [ ] Category dropdown populated from database
- [ ] Validation checks against database categories
- [ ] Warning shown for unlisted categories
- [ ] Warning directs user to Catalog → Recipe Categories
- [ ] Option to add new category from save dialog

---

### FR-5: Seed Database with Existing Categories

**What it must do:**
- Query existing Recipe.category values from database
- Create RecipeCategory records for each distinct value
- Set reasonable sort_order based on frequency or alphabetically
- Migration script or one-time data load

**Pattern reference:** Study how seed data is handled in existing migrations

**Migration strategy:**
```python
# Get distinct categories from existing recipes
distinct_categories = session.query(Recipe.category).distinct().all()

# Create RecipeCategory records
for i, (category_name,) in enumerate(distinct_categories):
    if category_name:  # Skip NULL
        create_category(
            name=category_name,
            slug=slugify(category_name),
            sort_order=i * 10,  # Leave gaps for reordering
            session=session
        )
```

**Initial categories to seed:**
- Cakes
- Cookies
- Candies
- Brownies
- Bars
- Breads
- Other
- Any other categories found in existing Recipe data

**Success criteria:**
- [ ] Migration script creates RecipeCategory records
- [ ] All existing recipe categories preserved
- [ ] Sort order assigned logically
- [ ] No data loss during migration
- [ ] Recipes still display correct categories after migration

---

### FR-6: Add Import/Export Support

**What it must do:**
- Add recipe_categories to full backup export
- Add recipe_categories to catalog export
- Support importing recipe categories from JSON
- Follow existing import/export patterns

**Pattern reference:** Study how material_categories are exported/imported

**Export format (recipe_categories.json):**
```json
[
  {
    "name": "Cakes",
    "slug": "cakes",
    "sort_order": 0,
    "description": "Layer cakes, sheet cakes, bundt cakes"
  },
  {
    "name": "Cookies",
    "slug": "cookies",
    "sort_order": 10,
    "description": "Drop cookies, cutouts, bars"
  }
]
```

**Import behavior:**
- Merge with existing categories (don't replace)
- Skip duplicates (by slug)
- Update sort_order if specified
- Validate data before import

**Success criteria:**
- [ ] recipe_categories.json included in full backup
- [ ] recipe_categories.json in catalog export
- [ ] Import creates/updates categories correctly
- [ ] Duplicate handling works
- [ ] Export/import cycle preserves all data

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Category hierarchies (MaterialCategory has 3 levels, recipes only need 1)
- ❌ Category-specific attributes or metadata
- ❌ Category icons or colors
- ❌ Finished Good categories - reuse Recipe categories (same taxonomy)
- ❌ Auto-categorization or AI suggestions
- ❌ Category usage statistics/analytics
- ❌ Bulk category operations (mass delete, mass edit)

---

## Success Criteria

**Complete when:**

### Database Layer
- [ ] RecipeCategory model exists with all fields
- [ ] Table created via migration
- [ ] Unique constraints enforced
- [ ] Timestamps working

### Service Layer
- [ ] recipe_category_service.py with complete CRUD
- [ ] Delete validation prevents orphaning
- [ ] Slug auto-generation works
- [ ] All functions follow session parameter pattern
- [ ] Pattern matches MaterialCategoryService

### UI Layer
- [ ] Recipe Categories dialog accessible via Catalog menu
- [ ] Menu item between Material Hierarchy and bottom of menu
- [ ] All CRUD operations functional
- [ ] Drag-to-reorder working
- [ ] Delete confirmation with in-use check
- [ ] Follows MaterialCategoriesDialog pattern

### Integration
- [ ] finished_unit_form.py uses database categories
- [ ] Validation checks database on save
- [ ] Warning directs to Catalog → Recipe Categories
- [ ] Migration seeds existing categories
- [ ] No data loss

### Import/Export
- [ ] Categories included in full backup
- [ ] Categories in catalog export
- [ ] Import/export cycle works
- [ ] Duplicate handling correct

### Quality
- [ ] Follows Code Quality Principle I.A (User Data Sovereignty)
- [ ] Follows Code Quality Principle VI.D (API Consistency)
- [ ] Pattern consistency with MaterialCategory
- [ ] Menu structure consistent with Ingredient/Material Hierarchies
- [ ] All tests pass

---

## Architecture Principles

### Catalog Menu Organization

**Category/taxonomy management in Catalog menu:**
- Ingredient Hierarchy (existing)
- Material Hierarchy (existing)
- Recipe Categories (new)

**NOT in Tools menu:**
- Tools menu for utilities/operations (Suppliers, Health Check)
- Catalog menu for data/taxonomy management
- Clear separation of concerns

### Follow MaterialCategory Exemplar

**MaterialCategory is the proven pattern:**
- 3-tier architecture: Model → Service → UI
- CRUD operations in service layer
- Admin UI in Catalog menu (not Tools)
- Import/export support
- Delete validation

**Recipe categories simplify (no hierarchy):**
- Flat list of categories (no parent/child)
- Simpler UI (no tree view needed)
- Same CRUD operations
- Same Catalog menu location

### Keep Recipe.category as String

**Don't use foreign key, validate instead:**
- Recipe.category remains TEXT field
- Validation checks against database on save
- Allows flexibility for custom/temporary categories
- No complex migration needed
- Backward compatible

**Rationale:**
- Users might type custom categories during data entry
- Strict FK would block saves unnecessarily
- Validation + warning provides better UX
- Can tighten to FK later if needed

---

## Constitutional Compliance

✅ **Principle I.A: User Data Sovereignty**
- Users control their category taxonomy
- Can add/edit/delete categories as needed
- Not locked into developer's choices

✅ **Principle VI.D: API Consistency & Contracts**
- Database-driven categories (like MaterialCategory)
- Consistent CRUD patterns
- Predictable service interfaces

✅ **Principle VI.G: Code Organization Patterns**
- Pattern matching MaterialCategory exemplar
- Related code grouped together
- Consistent architecture across entity types
- Menu organization follows taxonomy vs operations pattern

✅ **Principle V: Layered Architecture Discipline**
- Model → Service → UI separation
- Business logic in service layer
- UI calls services, not database directly

---

## Risk Considerations

**Risk: Breaking existing recipe data**
- Migration must preserve all category values
- Mitigation: Keep Recipe.category as string (no FK)
- Mitigation: Seed database from existing data
- Mitigation: Test migration with production data copy

**Risk: Users delete categories in use**
- Could orphan recipes
- Mitigation: Delete validation checks usage
- Mitigation: Warning message shows affected recipes
- Mitigation: Require confirmation before delete

**Risk: Import/export conflicts**
- Duplicate category names on import
- Mitigation: Merge by slug (not replace)
- Mitigation: Skip duplicates with warning
- Mitigation: Document import behavior

**Risk: Menu placement confusion**
- User might look in Tools menu
- Mitigation: Consistent with Ingredient/Material placement
- Mitigation: "Recipe Categories" clearly describes function
- Mitigation: Only one logical place (Catalog menu)

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` → Section 3: MaterialCategory pattern
- Study `src/models/material_category.py` → copy model structure
- Study `src/services/material_category_service.py` → copy service patterns
- Study `src/ui/materials/material_categories_dialog.py` → copy UI structure
- Study Catalog menu in main_window.py → understand menu structure

**Key Patterns to Copy:**
- MaterialCategory model → simplify to RecipeCategory (no hierarchy)
- MaterialCategoryService CRUD → replicate for recipes
- MaterialCategoriesDialog UI → adapt for recipe categories
- Catalog menu placement → add alongside hierarchies
- Import/export patterns → apply to recipe categories

**Focus Areas:**
- MaterialCategory is the gold standard - follow it exactly
- Keep Recipe.category as string field (validate, don't FK)
- Catalog menu is established pattern for taxonomy management
- Migration must be safe (test with real data first)
- Import/export ensures data portability
- Menu placement consistency critical for UX

**Implementation Note:**
This feature provides immediate user value (Marianne can customize categories) while establishing architectural consistency. The MaterialCategory pattern is proven and well-documented - following it exactly minimizes risk and ensures quality. Menu placement in Catalog (not Tools) maintains logical separation between taxonomy management and operational utilities.

**Cursor Inspection Context:**
Per `docs/inspections/hardcoded_maps_categories_summary.md`:
- MaterialCategory is exemplar with 3-level hierarchy and admin UI
- Recipe categories only need flat list (simpler)
- Pattern already proven and working well
- 4-6 hours estimated effort (reasonable for full stack feature)

---

**END OF SPECIFICATION**
