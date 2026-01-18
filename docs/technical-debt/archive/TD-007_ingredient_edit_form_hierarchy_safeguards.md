# TD-007: Ingredient Edit Form Missing Hierarchy Level Safeguards

| Attribute | Value |
|-----------|-------|
| **Status** | Closed (Obsolete) |
| **Priority** | Low |
| **Created** | 2026-01-08 |
| **Closed** | 2026-01-17 |
| **Related Features** | F042 (UI Polish), F033 (Hierarchy Redesign) |
| **Location** | `src/ui/ingredients_tab.py:IngredientFormDialog` |

## Resolution

**Closed as Obsolete** - The form was redesigned as part of F033 with proper hierarchy safeguards.

Analysis on 2026-01-17 found the following safeguards now in place:

| Feature | Implementation |
|---------|---------------|
| **Cascading dropdowns** | L0 selection populates L1; L1 disabled until L0 selected |
| **Auto-computed level** | Level derived from dropdown selections (lines 1293-1321) |
| **Level-aware pre-population** | L0: sets "(None - create root)", L1: shows parent L0, L2: shows L0+L1 ancestors (lines 1431-1460) |
| **Real-time validation** | `_check_parent_change_warnings()` calls `can_change_parent()` on every change, shows red errors for disallowed changes (lines 1323-1350) |
| **Save validation** | Validates L2 has proper L1 parent before saving (lines 1531-1538) |

The implementation uses validation-based safeguards rather than option-hiding, which is more flexible while still preventing invalid states. Invalid parent selections trigger immediate red error messages via `can_change_parent()` service validation.

---

## Original Description

The ingredient edit form does not apply appropriate safeguards based on the hierarchy level of the ingredient being edited. This leads to counter-intuitive UI behavior:

- **L0 (root categories)**: Edit form offers option to select a parent L0 category, but L0 items by definition have no parent
- **L1 (subcategories)**: Edit form offers options that may not be appropriate for the L1 level
- **L2 (leaf ingredients)**: Similar issues with inappropriate options being displayed

## Current Behavior

When editing any ingredient regardless of hierarchy level, the form presents the same set of editable fields, including parent selection dropdowns that may not apply to the item's level.

## Expected Behavior

The edit form should dynamically adjust available fields based on the ingredient's hierarchy level:

### L0 (Root Categories)
- Hide/disable parent selection (L0 items cannot have parents)
- Show only L0-appropriate fields (name, display_name)
- Possibly show read-only count of child L1 items

### L1 (Subcategories)
- Show L0 parent selection only (cannot be re-parented to L1 or L2)
- Hide/disable fields that don't apply to subcategories
- Possibly show read-only count of child L2 items

### L2 (Leaf Ingredients)
- Show L1 parent selection only
- Show all ingredient-specific fields (density, is_packaging, etc.)
- Cannot have children, so no child count

## Impact

- **User confusion**: Users may attempt invalid operations
- **Data integrity risk**: Although service layer should validate, UI should prevent invalid states
- **Polish**: Professional applications adapt forms to context

## Suggested Implementation

1. Add `hierarchy_level` check when opening edit dialog
2. Create level-specific form configurations or dynamically show/hide fields
3. Add validation messages if user attempts invalid operations
4. Consider read-only mode for structural attributes that shouldn't change (like level itself)

## Workaround

Users can manually avoid selecting inappropriate options. Service layer validation should prevent actual data corruption.

## Effort Estimate

4-6 hours

## Reason for Deferral

Implementing foundational workflow features (F043-F047) is higher priority. This is a polish/UX issue that doesn't block core functionality.
