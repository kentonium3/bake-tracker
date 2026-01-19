# Bug Fix: F032 Ingredient Hierarchy UI Conceptual Errors

**Bug ID:** BUG_F032_HIERARCHY_CONCEPTUAL_ERRORS  
**Created:** 2025-12-30  
**Priority:** CRITICAL  
**Status:** READY FOR IMPLEMENTATION  
**Related Feature:** F032 (Ingredient Hierarchy UI Completion)

---

## Problem Statement

The F032 implementation has **fundamental conceptual errors** in how it represents and edits the ingredient hierarchy:

### Critical Issue 1: Wrong Mental Model in Edit Form

**Current (WRONG):**
- Ingredient name shown as dialog title (not editable)
- Dropdown to "set ingredient level" with options: "Root category (L0)", "Subcategory (L1)", "Leaf Ingredient"
- This treats hierarchy level as a **property you assign** rather than a **consequence of position in tree**

**Correct Mental Model:**
- An ingredient's level is **determined by its position in the hierarchy**, not assigned directly
- If an ingredient has NO parent → it's L0 (root)
- If an ingredient has a parent that's L0 → it's L1 (subcategory)
- If an ingredient has a parent that's L1 → it's L2 (leaf)
- **You never "set the level" - you set the parent, and level is computed**

### Critical Issue 2: Ingredients Tab Shows Wrong Data

**Current (WRONG):**
- Some fields showing dashes instead of L0/L1 category names
- Unclear what data is being displayed

**Expected:**
- Grid should show **ONLY L2 (leaf) ingredients** by default
- Each row shows: Ingredient Name | L1 Parent | L0 Grandparent | Products | Actions
- Filter option to show L0 or L1 ingredients if needed for management

### Critical Issue 3: Product Edit Form Hangs

**Symptom:**
- Clicking edit button on product causes hang/freeze
- Likely due to cascading dropdown logic errors or infinite loops

---

## Correct Design Specification

### Part 1: Ingredients Tab Grid

**Display Logic:**

```
Default View: LEAF INGREDIENTS ONLY (L2)

| Ingredient Name              | Subcategory (L1)  | Root (L0)  | Products | Actions |
|------------------------------|-------------------|------------|----------|---------|
| Semi-Sweet Chocolate Chips   | Dark Chocolate    | Chocolate  | 3        | [Edit]  |
| All-Purpose Flour            | All-Purpose       | Flour      | 5        | [Edit]  |
| Granulated Sugar             | White Sugar       | Sugar      | 2        | [Edit]  |
```

**Filter Options:**

```
Show: [Leaf Ingredients (L2) ▼]
  - Leaf Ingredients Only (L2) ← DEFAULT
  - Subcategories (L1)
  - Root Categories (L0)
  - All Levels
```

**When showing L1 (Subcategories):**
```
| Ingredient Name    | Parent (L0) | Level | Children | Actions |
|--------------------|-------------|-------|----------|---------|
| Dark Chocolate     | Chocolate   | L1    | 5        | [Edit]  |
| All-Purpose        | Flour       | L1    | 3        | [Edit]  |
```

**When showing L0 (Root Categories):**
```
| Ingredient Name | Level | Children | Actions |
|-----------------|-------|----------|---------|
| Chocolate       | L0    | 12       | [Edit]  |
| Flour           | L0    | 8        | [Edit]  |
```

---

### Part 2: Ingredient Edit Form - Correct Design

**Form Title:** "Edit Ingredient" (or "Create Ingredient")

**Layout:**

```
┌─ Edit Ingredient ──────────────────────────────────────┐
│                                                         │
│  Ingredient Name: [Semi-Sweet Chocolate Chips_______]  │
│                   (Editable text field)                │
│                                                         │
│  Hierarchy Position:                                   │
│                                                         │
│    Parent Category:                                    │
│    ┌─────────────────────────────────────────────┐    │
│    │ ○ No Parent (Root Category - L0)            │    │
│    │                                              │    │
│    │ ● Has Parent:                                │    │
│    │   Root (L0):      [Chocolate ▼]             │    │
│    │   Subcategory:    [Dark Chocolate ▼]        │    │
│    │                   (filtered by L0 selection) │    │
│    └─────────────────────────────────────────────┘    │
│                                                         │
│  Computed Level: L2 (Leaf Ingredient)                  │
│  Can have products: Yes ✓                              │
│                                                         │
│  Recipe Unit: [oz ▼]                                   │
│  Density: [Enabled ☑]                                  │
│  ...                                                   │
│                                                         │
│  [Cancel]  [Save]                                      │
└─────────────────────────────────────────────────────────┘
```

**Logic:**

1. **Radio Buttons:**
   - "No Parent (Root Category)" → Creates L0 ingredient, both dropdowns disabled
   - "Has Parent" → Enables dropdowns

2. **Root (L0) Dropdown:**
   - Populates with all L0 ingredients
   - When changed, L1 dropdown updates to show children of selected L0
   - If L0 has no children yet, L1 dropdown shows "(No subcategories - will create L1 ingredient)"

3. **Subcategory Dropdown:**
   - Shows children of selected L0
   - Option: "+ Create New Subcategory" → Opens inline subcategory creation
   - If selected L1 has no children, creates L2 (leaf)
   - If selected L1 has children, creates L2 (leaf)

4. **Computed Level Display:**
   - No parent selected → "L0 (Root Category)"
   - L0 parent selected, no L1 → "L1 (Subcategory)"
   - L0 + L1 selected → "L2 (Leaf Ingredient)"
   - Read-only, informational only

5. **Can Have Products Display:**
   - L0: "No - Root categories cannot have products"
   - L1: "No - Subcategories cannot have products"
   - L2: "Yes ✓ - Leaf ingredients can have products"

---

### Part 3: Create Workflow Examples

**Example 1: Create L0 (Root Category)**

User wants to create "Spices" root category:

```
1. Name: "Spices"
2. Select "No Parent (Root Category)"
3. Computed Level shows: "L0 (Root Category)"
4. Can have products: "No"
5. Save → Creates L0 ingredient
```

**Example 2: Create L1 (Subcategory)**

User wants to create "Cinnamon" under "Spices":

```
1. Name: "Cinnamon"
2. Select "Has Parent"
3. Root (L0): [Spices ▼]
4. Subcategory: (empty - no L1 children exist yet)
5. Computed Level shows: "L1 (Subcategory)"
6. Can have products: "No"
7. Save → Creates L1 ingredient with parent = Spices
```

**Example 3: Create L2 (Leaf Ingredient)**

User wants to create "Ground Cinnamon" under "Spices → Cinnamon":

```
1. Name: "Ground Cinnamon"
2. Select "Has Parent"
3. Root (L0): [Spices ▼]
4. Subcategory: [Cinnamon ▼] (now visible since L1 exists)
5. Computed Level shows: "L2 (Leaf Ingredient)"
6. Can have products: "Yes ✓"
7. Save → Creates L2 ingredient with parent = Cinnamon
```

**Example 4: Create L2 When L1 Doesn't Exist Yet**

User wants to create "Semi-Sweet Chips" but "Dark Chocolate" L1 doesn't exist:

```
Option A: Inline creation
1. Name: "Semi-Sweet Chips"
2. Root (L0): [Chocolate ▼]
3. Subcategory: [+ Create New Subcategory...]
4. Dialog opens: "Create Subcategory"
   Name: "Dark Chocolate"
   [Create]
5. Returns to main form with "Dark Chocolate" selected
6. Save → Creates both L1 (Dark Chocolate) and L2 (Semi-Sweet Chips)

Option B: Error message (simpler for Phase 2)
"Cannot create leaf ingredient without subcategory.
Please create 'Dark Chocolate' subcategory first."
```

---

### Part 4: Edit Workflow and Protections

**Editing Existing Ingredient:**

When editing an ingredient that already exists:

**Safe Edits (Always Allowed):**
- Change name (updates `display_name`)
- Change recipe_unit, density, notes

**Hierarchy Changes (Require Validation):**

**Rule 1: Cannot change hierarchy if ingredient has children**
```
Example: Editing "Chocolate" (L0) which has L1 children
Attempted change: Move under "Baking Supplies"
Result: ERROR - "Cannot change parent: this ingredient has 5 children"
Solution: Must move/delete children first
```

**Rule 2: Cannot change L2 to L0/L1 if ingredient has products**
```
Example: Editing "Semi-Sweet Chips" (L2) which has 3 products
Attempted change: Remove parent (make it L0)
Result: ERROR - "Cannot change to non-leaf: this ingredient has 3 products"
Solution: Must remove/reassign products first
```

**Rule 3: Can change L0 to L1 or L2 if no children**
```
Example: Editing "Vanilla" (L0) which has no children
Attempted change: Move under "Spices → Sweet Spices"
Result: OK - Updates parent_ingredient_id, hierarchy_level computed
```

**Rule 4: Can change parent within same level**
```
Example: Moving L2 ingredient from one L1 to another
Current: "Semi-Sweet Chips" under "Chocolate → Dark Chocolate"
Change: Move to "Chocolate → Baking Chocolate"
Result: OK - Updates parent_ingredient_id, level stays L2
```

---

### Part 5: Service Layer Methods Needed

```python
# ingredient_hierarchy_service.py

def compute_hierarchy_level(parent_ingredient_id: Optional[int]) -> int:
    """
    Compute hierarchy level based on parent.
    
    Args:
        parent_ingredient_id: ID of parent ingredient, or None
    
    Returns:
        0 if no parent (root)
        1 if parent is L0
        2 if parent is L1
    
    Raises:
        ValueError if parent is already L2 (can't have children)
    """
    
def can_change_parent(
    ingredient_id: int, 
    new_parent_id: Optional[int]
) -> Tuple[bool, str]:
    """
    Validate if ingredient can be moved to new parent.
    
    Returns:
        (True, "") if allowed
        (False, "error message") if not allowed
    
    Checks:
    - Has children? → Cannot change parent
    - Has products and new level != L2? → Cannot change
    - New parent is L2? → Cannot (L2 can't have children)
    - Would create cycle? → Cannot
    """

def get_available_l0_ingredients() -> List[Ingredient]:
    """Get all L0 ingredients for dropdown."""
    
def get_available_l1_ingredients(parent_l0_id: int) -> List[Ingredient]:
    """Get L1 children of specified L0 ingredient."""

def update_ingredient_hierarchy(
    ingredient_id: int,
    new_parent_id: Optional[int]
) -> None:
    """
    Update ingredient's parent and recompute level.
    Validates before updating.
    """
```

---

### Part 6: Product Edit Form Issue

**Known Issue:** Edit button hangs/freezes

**Likely Causes:**

1. **Infinite loop in cascading dropdowns:**
   - L0 change triggers L1 update
   - L1 update triggers L0 change
   - Loop continues forever

2. **Blocking database query in UI thread:**
   - `get_children()` query blocks main thread
   - UI freezes waiting for response

3. **Event handler recursion:**
   - Change event fires during programmatic update
   - Triggers another programmatic update
   - Recursion continues

**Debugging Steps:**

1. Add print statements to dropdown change handlers
2. Check for recursive calls
3. Use flag to prevent event handler re-entry:
   ```python
   self._updating = False
   
   def on_l0_change(self, event):
       if self._updating:
           return
       self._updating = True
       # ... update L1 dropdown
       self._updating = False
   ```

**Recommendation:** Assign to Gemini/Cursor for debugging as you mentioned.

---

## Implementation Plan

### Phase 1: Fix Ingredient Edit Form (CRITICAL)

1. Remove "ingredient level" dropdown entirely
2. Add "No Parent" / "Has Parent" radio buttons
3. Add cascading L0 / L1 dropdowns (only enabled if "Has Parent" selected)
4. Add computed level display (read-only)
5. Add "can have products" indicator (read-only)
6. Implement `compute_hierarchy_level()` logic
7. Implement `can_change_parent()` validation

**Estimate:** 6-8 hours

---

### Phase 2: Fix Ingredients Tab Grid (HIGH)

1. Filter to show only L2 ingredients by default
2. Add hierarchy columns: Ingredient | Subcategory (L1) | Root (L0)
3. Use `get_ancestors()` to populate L0/L1 columns
4. Add "Show" dropdown with level filter options
5. Adjust grid columns based on selected filter

**Estimate:** 4-6 hours

---

### Phase 3: Fix Product Edit Form Hang (BLOCKER)

1. Debug cascading dropdown logic
2. Add re-entry guards to event handlers
3. Test edit workflow thoroughly
4. Consider handing to Gemini/Cursor if issue persists

**Estimate:** 4-8 hours (or external debugger)

---

### Phase 4: Comprehensive Testing

**Test Cases:**

1. **Create L0 Ingredient:**
   - Name: "Spices"
   - No parent selected
   - Saves as L0
   - Cannot add products

2. **Create L1 Ingredient:**
   - Name: "Cinnamon"
   - Parent: "Spices" (L0)
   - Saves as L1
   - Cannot add products

3. **Create L2 Ingredient:**
   - Name: "Ground Cinnamon"
   - L0: "Spices"
   - L1: "Cinnamon"
   - Saves as L2
   - Can add products

4. **Edit L2 - Move Between L1 Parents:**
   - Edit "Semi-Sweet Chips" (currently under "Dark Chocolate")
   - Change L1 to "Baking Chocolate"
   - Saves successfully, still L2

5. **Edit L0 - Try to Add Parent (Should Fail if Has Children):**
   - Edit "Chocolate" (has children)
   - Try to add parent
   - Error: "Cannot change parent: this ingredient has 5 children"

6. **Edit L2 - Try to Remove Parent (Should Fail if Has Products):**
   - Edit "Semi-Sweet Chips" (has products)
   - Try to select "No Parent"
   - Error: "Cannot change to non-leaf: this ingredient has 3 products"

7. **Ingredients Tab - Default View:**
   - Opens showing only L2 ingredients
   - Columns: Name | L1 | L0 | Products
   - No dashes, all fields populated

8. **Ingredients Tab - Filter to L0:**
   - Change filter to "Root Categories (L0)"
   - Grid shows: Name | Level | Children
   - Shows only L0 ingredients

**Estimate:** 4-6 hours

---

## Total Estimated Effort

- Phase 1 (Edit Form): 6-8 hours
- Phase 2 (Grid): 4-6 hours
- Phase 3 (Product Edit Hang): 4-8 hours (or external)
- Phase 4 (Testing): 4-6 hours

**Total:** 18-28 hours (2-4 working days)

---

## Success Criteria

### Must Have
- [ ] Ingredient edit form uses radio buttons + cascading dropdowns (NOT level dropdown)
- [ ] Level is computed from parent, not directly set
- [ ] Ingredients tab shows only L2 by default with L0/L1 ancestry columns
- [ ] No dashes in grid (all hierarchy fields populated)
- [ ] Product edit form doesn't hang
- [ ] Can create L0, L1, and L2 ingredients successfully
- [ ] Hierarchy change validation prevents illegal moves

### Should Have
- [ ] Inline subcategory creation in edit form
- [ ] Clear error messages for validation failures
- [ ] Filter option to view L0 or L1 ingredients

### Nice to Have
- [ ] Batch move operations
- [ ] Orphan detection (ingredients with deleted parents)

---

## Related Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/docs/func-spec/F031_ingredient_hierarchy.md` - Original backend spec
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/bugs/BUG_F031_incomplete_hierarchy_ui.md` - Original UI spec (now superseded)

---

## Critical Note

The original F032 implementation fundamentally misunderstood the hierarchy model. **Hierarchy level is not a property you assign** - it's a **computed value based on position in the tree**. This is the core conceptual error that must be fixed.

The mental model should be:
- **What you edit:** Parent relationship (which L0? which L1?)
- **What gets computed:** Hierarchy level (L0/L1/L2)
- **What gets validated:** Whether the change is allowed (based on children/products)
