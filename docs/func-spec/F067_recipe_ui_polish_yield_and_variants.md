# F067: Recipe UI Polish - Yield Information and Variant Grouping

**Version**: 1.0  
**Priority**: MEDIUM (P1 - UX Polish)  
**Type**: UI Refinement  
**Status**: Draft  
**Created**: 2025-01-25

---

## Executive Summary

Current Recipe UI has usability gaps across three areas:

**Edit Recipe Dialog:**
- ❌ Yield Information section has excessive whitespace
- ❌ Unclear terminology ("Yield Types" vs "Finished Units")
- ❌ Missing column labels make fields ambiguous
- ❌ "Production Ready" defaults to unchecked (should default checked)

**Recipe Catalog Grid:**
- ❌ No visual relationship between base recipes and variants in catalog grid

**Finished Units Grid:**
- ❌ No visual relationship between base finished units and variant finished units

**Create Variant Dialog:**
- ❌ Poor label positioning ("Variant Name:" beside field instead of above)
- ❌ Help text in wrong position (after field instead of before)
- ❌ Wrong section title ("Variant Yields" instead of "Finished Unit Name(s)")
- ❌ Unnecessary "Base:" labels clutter the interface
- ❌ Input fields not left-justified

This spec polishes the Recipe UI to improve clarity and usability across all recipe management dialogs.

---

## Problem Statement

**Current State (FROM SCREENSHOT):**
```
Edit Recipe Dialog - Yield Information Section
┌─────────────────────────────────────────────┐
│ Yield Information                            │
│                                              │  ← Excessive whitespace
│                                              │
│ Yield Types* - Each row defines a finished  │  ← Confusing term
│ product from this recipe (Description,       │
│ Unit, Qty/batch):                            │
│                                              │
│ [Standard Almond Biscotti] [slices] [30] [X]│  ← No column labels
│                                              │
│ [+ Add Yield Type]                           │
└─────────────────────────────────────────────┘

Recipe Catalog Grid
┌─────────────────────────────────────────────┐
│ Chocolate Chip Cookies                       │
│ Gluten-Free Chocolate Chip (variant)         │  ← No visual grouping
│ Almond Biscotti                              │
│ Whole Wheat Almond Biscotti (variant)        │  ← No indentation
└─────────────────────────────────────────────┘

Production Ready Checkbox
☐ Production Ready  ← Defaults unchecked (wrong)
```

**Target State (IMPROVED):**
```
Edit Recipe Dialog - Yield Information Section
┌─────────────────────────────────────────────┐
│ Yield Information                            │
│ Each row defines a Finished Unit and        │  ← No extra whitespace
│ quantity per batch for this recipe.          │  ← Clear terminology
│                                              │
│ Finished Unit Name      Unit     Qty/Batch  │  ← Column labels
│ [Standard Almond Bisc] [slices]  [30]   [X] │
│                                              │
│ [+ Add Yield Type]                           │
└─────────────────────────────────────────────┘

Recipe Catalog Grid
┌─────────────────────────────────────────────┐
│ Chocolate Chip Cookies                       │
│   ↳ Gluten-Free Chocolate Chip               │  ← Indented variant
│ Almond Biscotti                              │
│   ↳ Whole Wheat Almond Biscotti              │  ← Visual hierarchy
└─────────────────────────────────────────────┘

Production Ready Checkbox
☑ Production Ready  ← Defaults checked (correct)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe Form Dialog (Current UI)**
   - Find `/src/ui/dialogs/recipe_form_dialog.py`
   - Study Yield Information section layout
   - Note current help text and spacing
   - Understand how yield rows are created

2. **Recipe Catalog Tab (Grid Display)**
   - Find `/src/ui/tabs/recipe_tab.py` (or equivalent)
   - Study how recipe grid is populated
   - Note current recipe listing logic
   - Understand filtering/sorting

3. **Finished Units Tab (Grid Display)**
   - Find `/src/ui/tabs/finished_units_tab.py` (or equivalent)
   - Study how finished units grid is populated
   - Note current listing logic
   - Understand relationship to recipes

4. **Recipe Model (Base/Variant Relationship)**
   - Find `/src/models/recipe.py`
   - Study base_recipe_id field
   - Note how variants link to base recipes
   - Understand variant detection

5. **Recipe Service (Catalog Queries)**
   - Find `/src/services/recipe_service.py`
   - Study list_all_recipes() or equivalent
   - Note current sorting/grouping logic
   - Understand query patterns

6. **Variant Creation Dialog (Current UI)**
   - Find `/src/ui/dialogs/variant_creation_dialog.py`
   - Study current layout structure
   - Note label and field positioning
   - Understand finished unit name customization flow

7. **CustomTkinter Layout Patterns**
   - Study existing CTk layouts for reference
   - Note label placement patterns
   - Understand grid/pack management
   - Review spacing conventions

---

## Functional Requirements

### FR-1: Remove Excessive Whitespace in Yield Information Section

**What it must do:**
- Remove vertical whitespace between "Yield Information" title and help text
- Reduce padding/spacing to match other sections (Basic Information, Recipe Ingredients)
- Maintain visual hierarchy without excessive gaps

**Current layout issue:**
```python
# BEFORE (excessive spacing):
yield_section = CTkFrame(...)
CTkLabel(yield_section, text="Yield Information")  # Title
# ← 20-30px gap here (too much)
CTkLabel(yield_section, text="Yield Types* - ...")  # Help text
```

**Target layout:**
```python
# AFTER (tight spacing):
yield_section = CTkFrame(...)
title = CTkLabel(yield_section, text="Yield Information", font=("", 14, "bold"))
title.pack(pady=(0, 5))  # Small gap after title only

help_text = CTkLabel(yield_section, text="Each row defines...", font=("", 11))
help_text.pack(pady=(0, 10))  # Normal gap before content
```

**Success criteria:**
- [ ] Whitespace between title and help text ≤ 5px
- [ ] Visual consistency with other sections
- [ ] Help text immediately follows title

---

### FR-2: Update Yield Information Help Text

**What it must do:**
- Change help text from "Yield Types* - Each row defines a finished product from this recipe (Description, Unit, Qty/batch):"
- To: "Each row defines a Finished Unit and quantity per batch for this recipe."
- Remove asterisk (not needed)
- Use proper terminology: "Finished Unit" instead of "finished product"
- Simpler, clearer phrasing

**Current:**
```python
help_text = "Yield Types* - Each row defines a finished product from this recipe (Description, Unit, Qty/batch):"
```

**Target:**
```python
help_text = "Each row defines a Finished Unit and quantity per batch for this recipe."
```

**Success criteria:**
- [ ] Help text uses "Finished Unit" terminology
- [ ] No asterisk in help text
- [ ] Simpler, clearer phrasing
- [ ] No parenthetical field list (replaced by column labels)

---

### FR-3: Add Column Labels to Yield Fields

**What it must do:**
- Add column header labels above yield input fields
- Label 1 (Description field): "Finished Unit Name"
- Label 2 (Unit field): "Unit"
- Label 3 (Qty/Batch field): "Qty/Batch"
- Labels should be clear, not too bold, above each column
- Align labels with their respective input fields

**Current (no labels):**
```
[Standard Almond Biscotti] [slices] [30] [X]
```

**Target (with labels):**
```
Finished Unit Name      Unit     Qty/Batch
[Standard Almond Bisc] [slices]  [30]   [X]
```

**Layout approach:**
```python
# Header row with labels
header_frame = CTkFrame(yield_section)
header_frame.pack(fill="x", pady=(10, 5))

CTkLabel(header_frame, text="Finished Unit Name", font=("", 11)).pack(side="left", padx=(0, 10))
CTkLabel(header_frame, text="Unit", font=("", 11)).pack(side="left", padx=(0, 10))
CTkLabel(header_frame, text="Qty/Batch", font=("", 11)).pack(side="left")

# Then yield rows as before
```

**Success criteria:**
- [ ] "Finished Unit Name" label over description field
- [ ] "Unit" label over unit dropdown
- [ ] "Qty/Batch" label over quantity field
- [ ] Labels aligned with input fields
- [ ] Clear visual hierarchy (labels slightly smaller/lighter than title)

---

### FR-4: Default "Production Ready" to Checked

**What it must do:**
- Change default value of "Production Ready" checkbox to checked (True)
- Apply to all new recipes created
- Apply when editing existing recipes (if currently unchecked, leave as-is; but new recipes default checked)
- Most recipes are production-ready, so checked should be the default

**Current:**
```python
# BEFORE
self.production_ready_var = CTkBooleanVar(value=False)  # ❌ Wrong default
```

**Target:**
```python
# AFTER
self.production_ready_var = CTkBooleanVar(value=True)  # ✅ Correct default
```

**When creating new recipe:**
```python
def create_new_recipe():
    # Recipe starts as production-ready by default
    new_recipe = Recipe(
        name="New Recipe",
        production_ready=True,  # Default checked
        ...
    )
```

**Success criteria:**
- [ ] New recipes default to production_ready=True
- [ ] Checkbox appears checked by default
- [ ] Existing recipe values preserved when editing
- [ ] UI shows checked state on new recipe dialog

---

### FR-5: Group Variant Recipes Under Base Recipes in Catalog Grid

**What it must do:**
- Recipe catalog grid should visually group variants under their base recipes
- Base recipes appear at top level
- Variant recipes indented under base recipe
- Clear visual indicator (indent + arrow or icon)
- Maintain alphabetical/category sorting for base recipes
- Variants sorted alphabetically under their base

**Current (flat list):**
```
Chocolate Chip Cookies
Gluten-Free Chocolate Chip
Almond Biscotti
Whole Wheat Almond Biscotti
```

**Target (hierarchical):**
```
Almond Biscotti
  ↳ Whole Wheat Almond Biscotti
Chocolate Chip Cookies
  ↳ Gluten-Free Chocolate Chip
```

**Implementation approach:**
```python
def populate_recipe_grid():
    # Get all recipes
    all_recipes = recipe_service.list_all_recipes()
    
    # Separate base recipes and variants
    base_recipes = [r for r in all_recipes if not r.base_recipe_id]
    variants = [r for r in all_recipes if r.base_recipe_id]
    
    # Build variant lookup
    variants_by_base = {}
    for variant in variants:
        if variant.base_recipe_id not in variants_by_base:
            variants_by_base[variant.base_recipe_id] = []
        variants_by_base[variant.base_recipe_id].append(variant)
    
    # Sort base recipes
    base_recipes.sort(key=lambda r: r.name)
    
    # Display with hierarchy
    for base_recipe in base_recipes:
        add_recipe_row(base_recipe, indent=0)
        
        # Add variants indented
        if base_recipe.id in variants_by_base:
            for variant in sorted(variants_by_base[base_recipe.id], key=lambda r: r.name):
                add_recipe_row(variant, indent=1, show_arrow=True)

def add_recipe_row(recipe, indent=0, show_arrow=False):
    row_frame = CTkFrame(...)
    
    # Add indent spacing
    if indent > 0:
        CTkLabel(row_frame, text="  ").pack(side="left")
    
    # Add arrow for variants
    if show_arrow:
        CTkLabel(row_frame, text="↳ ", fg_color="gray").pack(side="left")
    
    # Recipe name
    CTkLabel(row_frame, text=recipe.name).pack(side="left")
    ...
```

**Success criteria:**
- [ ] Base recipes appear at top level
- [ ] Variant recipes indented under base
- [ ] Visual indicator (↳ or similar) for variants
- [ ] Base recipes sorted alphabetically
- [ ] Variants sorted alphabetically under base
- [ ] Clear visual hierarchy

---

### FR-6: Update Recipe Listing Query (if needed)

**What it must do:**
- Recipe service list_all_recipes() should support hierarchical display
- May need to add variant_count or include_variants flag
- Ensure efficient query (not N+1 for variants)
- Return data structure that supports grouping

**Current:**
```python
def list_all_recipes():
    return session.query(Recipe).order_by(Recipe.name).all()
```

**Potential enhancement (if needed):**
```python
def list_all_recipes_grouped():
    """Return recipes grouped by base/variant relationship."""
    recipes = session.query(Recipe).order_by(Recipe.name).all()
    
    base_recipes = [r for r in recipes if not r.base_recipe_id]
    
    # Build hierarchy
    result = []
    for base in base_recipes:
        result.append({
            "recipe": base,
            "is_variant": False,
            "variants": [r for r in recipes if r.base_recipe_id == base.id]
        })
    
    return result
```

**Success criteria:**
- [ ] Query supports hierarchical display
- [ ] No N+1 query issues
- [ ] Efficient data structure for UI
- [ ] Backward compatible with existing callers

---

### FR-7: Polish Create Variant Dialog Layout

**What it must do:**
- Reorganize Create Variant dialog for better clarity and layout consistency
- Fix label naming and positioning
- Improve vertical spacing
- Left-justify input fields

**Current layout issues (FROM SCREENSHOT):**
```
Create Variant of Almond Biscotti
┌─────────────────────────────────────────────┐
│ Variant Name: [_____________________]       │  ← Label right of field
│                                              │
│ This name distinguishes the variant...       │  ← Help text after field
│                                              │
│ Base Recipe Yields (Reference):              │
│ Standard Almond Biscotti: 30 slices...       │
│                                              │
│ Variant inherits yield structure...          │
│ You can customize display names below.       │
│                                              │
│ Variant Yields:                              │  ← Wrong section name
│                                              │
│ Base: Standard Almond Biscotti               │  ← Unnecessary label
│       [Standard Almond Biscotti_____]        │  ← Field not left-justified
└─────────────────────────────────────────────┘
```

**Target layout (IMPROVED):**
```
Create Variant of Almond Biscotti
┌─────────────────────────────────────────────┐
│ Recipe Variant Name                          │  ← Label above field, left-justified
│ This name distinguishes the variant...       │  ← Help text below label
│ [_____________________________]              │  ← Field below help text
│                                              │
│ Base Recipe Yields (Reference):              │
│ Standard Almond Biscotti: 30 slices...       │
│                                              │
│ Variant inherits yield structure...          │
│ You can customize display names below.       │
│                                              │
│ Finished Unit Name(s):                       │  ← Correct section name
│ [Standard Almond Biscotti_____]              │  ← Left-justified, no "Base:" label
└─────────────────────────────────────────────┘
```

**Sub-requirement 7.1: Recipe Variant Name Layout**
- Change label from "Variant Name:" to "Recipe Variant Name"
- Left-justify label (no colon)
- Place help text below label
- Place input field below help text
- Keep vertical spacing compact (5-10px between elements)

```python
# BEFORE (label and field on same line):
name_frame = CTkFrame(...)
CTkLabel(name_frame, text="Variant Name:").pack(side="left")
CTkEntry(name_frame, ...).pack(side="left")

# AFTER (vertical layout):
name_frame = CTkFrame(...)
CTkLabel(name_frame, text="Recipe Variant Name", anchor="w").pack(fill="x", pady=(0, 5))
CTkLabel(name_frame, text="This name distinguishes...", font=(11), anchor="w").pack(fill="x", pady=(0, 5))
CTkEntry(name_frame, ...).pack(fill="x")
```

**Sub-requirement 7.2: Finished Unit Name(s) Section**
- Change section title from "Variant Yields:" to "Finished Unit Name(s):"
- Remove "Base: Standard Almond Biscotti" label to left of input field
- Left-justify input field(s)
- If multiple finished units, show each input field left-justified

```python
# BEFORE (with "Base:" label):
yields_section = CTkFrame(...)
CTkLabel(yields_section, text="Variant Yields:").pack(...)

for fu in base_finished_units:
    row = CTkFrame(...)
    CTkLabel(row, text=f"Base: {fu.display_name}").pack(side="left")  # ❌ Remove
    CTkEntry(row, ...).pack(side="left")  # ❌ Not left-justified

# AFTER (left-justified, no "Base:" label):
yields_section = CTkFrame(...)
CTkLabel(yields_section, text="Finished Unit Name(s):", anchor="w").pack(fill="x", pady=(10, 5))

for fu in base_finished_units:
    entry = CTkEntry(yields_section, ...)  # ✅ No "Base:" label
    entry.pack(fill="x", pady=(0, 5))  # ✅ Left-justified
```

**Success criteria:**
- [ ] Label reads "Recipe Variant Name" (not "Variant Name:")
- [ ] Label is left-justified above field
- [ ] Help text appears between label and input field
- [ ] Input field appears below help text
- [ ] Vertical spacing compact (5-10px)
- [ ] Section title reads "Finished Unit Name(s):" (not "Variant Yields:")
- [ ] No "Base: ..." label before input fields
- [ ] Input fields are left-justified
- [ ] Multiple finished units each get left-justified input field

---

### FR-8: Group Related Finished Units in Finished Units Grid

**What it must do:**
- Finished Units grid should visually group variant finished units under their base finished units
- Mirror the approach used in FR-5 (Recipe Catalog Grid grouping)
- Base finished units appear at top level
- Variant finished units indented under base finished unit
- Clear visual indicator (indent + arrow or icon)
- Maintain alphabetical/category sorting for base finished units
- Variants sorted alphabetically under their base

**Current (flat list):**
```
Finished Units Grid
┌─────────────────────────────────────────────┐
│ Chocolate Chip Cookie                        │
│ Gluten-Free Chocolate Chip Cookie            │  ← No visual link
│ Standard Almond Biscotti                     │
│ Whole Wheat Almond Biscotti                  │  ← No visual link
└─────────────────────────────────────────────┘
```

**Target (hierarchical):**
```
Finished Units Grid
┌─────────────────────────────────────────────┐
│ Chocolate Chip Cookie                        │
│   ↳ Gluten-Free Chocolate Chip Cookie        │  ← Indented variant
│ Standard Almond Biscotti                     │
│   ↳ Whole Wheat Almond Biscotti              │  ← Visual hierarchy
└─────────────────────────────────────────────┘
```

**Relationship detection:**
- Finished units are related via their parent recipe relationship
- Base recipe → Base finished unit
- Variant recipe → Variant finished unit
- Group finished units when their recipes have base/variant relationship

**Implementation approach (mirrors FR-5):**
```python
def populate_finished_units_grid():
    # Get all finished units with recipe info
    all_finished_units = finished_unit_service.list_all_finished_units()
    
    # Separate base and variant finished units
    # Base: finished unit's recipe has no base_recipe_id
    # Variant: finished unit's recipe has base_recipe_id
    base_units = [fu for fu in all_finished_units if not fu.recipe.base_recipe_id]
    variant_units = [fu for fu in all_finished_units if fu.recipe.base_recipe_id]
    
    # Build variant lookup by base recipe ID
    variants_by_base_recipe = {}
    for variant_fu in variant_units:
        base_recipe_id = variant_fu.recipe.base_recipe_id
        if base_recipe_id not in variants_by_base_recipe:
            variants_by_base_recipe[base_recipe_id] = []
        variants_by_base_recipe[base_recipe_id].append(variant_fu)
    
    # Sort base finished units
    base_units.sort(key=lambda fu: fu.display_name)
    
    # Display with hierarchy
    for base_fu in base_units:
        add_finished_unit_row(base_fu, indent=0)
        
        # Add variant finished units indented
        base_recipe_id = base_fu.recipe_id
        if base_recipe_id in variants_by_base_recipe:
            for variant_fu in sorted(variants_by_base_recipe[base_recipe_id], 
                                    key=lambda fu: fu.display_name):
                add_finished_unit_row(variant_fu, indent=1, show_arrow=True)

def add_finished_unit_row(finished_unit, indent=0, show_arrow=False):
    row_frame = CTkFrame(...)
    
    # Add indent spacing
    if indent > 0:
        CTkLabel(row_frame, text="  ").pack(side="left")
    
    # Add arrow for variants
    if show_arrow:
        CTkLabel(row_frame, text="↳ ", fg_color="gray").pack(side="left")
    
    # Finished unit name
    CTkLabel(row_frame, text=finished_unit.display_name).pack(side="left")
    ...
```

**Success criteria:**
- [ ] Base finished units appear at top level
- [ ] Variant finished units indented under base
- [ ] Visual indicator (↳ or similar) for variants
- [ ] Base finished units sorted alphabetically
- [ ] Variants sorted alphabetically under base
- [ ] Clear visual hierarchy
- [ ] Relationship determined via recipe base_recipe_id
- [ ] Multiple variants per base handled correctly

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Changing yield inheritance logic (F063/F066)
- ❌ Service primitive implementation (F066)
- ❌ Variant creation dialog changes (F066)
- ❌ Yield editing restrictions for variants (F066)
- ❌ Adding new functionality to recipes
- ❌ Recipe deletion or archival features

---

## Success Criteria

**Complete when:**

### Yield Information Section
- [ ] Whitespace reduced between title and help text
- [ ] Help text reads: "Each row defines a Finished Unit and quantity per batch for this recipe."
- [ ] Column labels present: "Finished Unit Name", "Unit", "Qty/Batch"
- [ ] Labels aligned above input fields
- [ ] Visual consistency with other sections

### Production Ready Default
- [ ] New recipes default to production_ready=True
- [ ] Checkbox appears checked by default
- [ ] Existing recipe values preserved

### Recipe Catalog Grid
- [ ] Base recipes at top level
- [ ] Variant recipes indented under base
- [ ] Visual indicator (↳) for variants
- [ ] Alphabetical sorting maintained
- [ ] Clear visual hierarchy

### Create Variant Dialog
- [ ] Label reads "Recipe Variant Name" (left-justified)
- [ ] Help text between label and input field
- [ ] Input field below help text
- [ ] Compact vertical spacing (5-10px)
- [ ] Section title reads "Finished Unit Name(s):"
- [ ] No "Base: ..." labels before input fields
- [ ] Input fields left-justified
- [ ] Works correctly with multiple finished units

### Finished Units Grid
- [ ] Base finished units appear at top level
- [ ] Variant finished units indented under base
- [ ] Visual indicator (↳) for variants
- [ ] Alphabetical sorting maintained
- [ ] Clear visual hierarchy
- [ ] Relationship determined via recipe.base_recipe_id
- [ ] Multiple variants per base handled correctly

### Quality
- [ ] UI tested with various recipe combinations
- [ ] Layout responsive to window sizing
- [ ] No visual regressions in other sections
- [ ] Consistent spacing throughout dialog

---

## Architecture Principles

### UI Clarity

**Clear labeling:**
- Column labels eliminate ambiguity
- Consistent terminology ("Finished Unit")
- Visual hierarchy guides user understanding

**Visual grouping:**
- Variants clearly associated with base recipes
- Indentation creates clear parent/child relationship
- Alphabetical sorting within groups

### Minimal Changes

**Conservative approach:**
- Polish existing UI, don't redesign
- Maintain current functionality
- Small, focused improvements

**Backward compatibility:**
- Existing recipes unaffected
- Recipe service API unchanged (or minimally extended)
- No database schema changes

---

## Risk Considerations

**Risk: Layout changes affect existing dialogs**
- Spacing changes might break other sections
- Mitigation: Test entire dialog after changes
- Use relative spacing (not absolute pixels)

**Risk: Variant grouping confuses users initially**
- Users accustomed to flat list
- Mitigation: Clear visual indicator (↳)
- Alphabetical sorting maintained

**Risk: Column labels make section taller**
- May require scrolling on smaller screens
- Mitigation: Test on minimum resolution
- Use compact label fonts

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study RecipeFormDialog current layout structure
- Review CustomTkinter spacing conventions
- Check Recipe catalog grid implementation
- Note existing label/frame patterns

**Key Patterns to Copy:**
- Other section labels (Basic Information, Recipe Ingredients)
- Existing help text styling
- Current grid row display logic
- Recipe service query patterns

**Focus Areas:**
- Precise spacing (5px, 10px) for consistency
- Column label alignment with fields
- Indent calculation for variants
- Efficient variant lookup (no N+1 queries)

**Testing Strategy:**
- Test with base recipes only
- Test with variants (1 level deep)
- Test with multiple variants per base
- Test sorting and filtering
- Verify responsive layout

---

**END OF SPECIFICATION**
