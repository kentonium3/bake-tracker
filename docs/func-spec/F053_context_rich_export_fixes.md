# F053: Context-Rich Export Fixes

**Version**: 1.0
**Priority**: HIGH
**Type**: UI Enhancement

---

## Executive Summary

Context-rich export functionality has several issues discovered during first use: incorrect file prefix ("view" instead of "aug"), missing entity types (Products, Material Products), no "All" option for bulk export, radio buttons instead of checkboxes, and inconsistent button text. These issues make the feature harder to use and less intuitive.

Current gaps:
- ❌ Files exported with "view_" prefix (should be "aug_" for augmentation)
- ❌ Products and Material Products missing from entity selection
- ❌ No "All" option to select/export all entity types at once
- ❌ Radio buttons force single selection (should be checkboxes for multiple)
- ❌ Button text says "View" (should say "File" to match other buttons)

This spec fixes the prefix, adds missing entities, enables multi-select with "All" option, and standardizes button text.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Context-Rich Export
├─ ✅ Export functionality works
├─ ✅ Ingredients export
├─ ✅ Recipes export
├─ ✅ Finished Units export
├─ ✅ Finished Goods export
├─ ✅ Materials export
├─ ❌ Products NOT available
├─ ❌ Material Products NOT available
├─ ❌ Files prefixed "view_" (wrong prefix)
├─ ❌ Radio buttons (single select only)
├─ ❌ No "All" option
└─ ❌ Button says "Export Context-Rich View" (inconsistent)
```

**Target State (COMPLETE):**
```
Context-Rich Export
├─ ✅ Export functionality works
├─ ✅ All 7 entity types available:
│   ├─ Ingredients
│   ├─ Products
│   ├─ Recipes
│   ├─ Finished Units
│   ├─ Finished Goods
│   ├─ Materials
│   └─ Material Products
├─ ✅ Files prefixed "aug_" (augmentation)
├─ ✅ Checkboxes (multi-select)
├─ ✅ "All" option (select/export all)
└─ ✅ Button says "Export Context-Rich File" (consistent)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Context-Rich Export Implementation**
   - Find export dialog (likely `src/ui/file_menu/export_dialog.py`)
   - Study how entity types are defined
   - Note radio button widget creation
   - Understand export service call for context-rich export

2. **Export Service Context-Rich Methods**
   - File: `src/services/export_service.py`
   - Find context-rich export methods
   - Study file prefix logic ("view_" currently)
   - Note how entity types are handled
   - Understand export format

3. **Other Export Dialogs**
   - Study catalog export (likely same file)
   - Study backup export (likely same file)
   - Note button text patterns
   - Understand checkbox vs radio button usage

4. **Entity Type Constants**
   - Find where entity types are defined
   - Note which entities support context-rich export
   - Understand entity type enumeration

---

## Requirements Reference

This specification addresses user feedback:
- **Issue**: "Files exported with 'view' prefix but should use 'aug' prefix"
- **Issue**: "Products and Material Products missing from export options"
- **Issue**: "Need 'All' option to export everything at once"
- **Issue**: "Radio buttons limit to single entity - should be checkboxes"
- **Issue**: "Button text says 'View' but should say 'File'"

From: User testing session (2026-01-15)

---

## Functional Requirements

### FR-1: Fix File Prefix

**What it must do:**
- Change context-rich export file prefix from "view_" to "aug_"
- Apply to all context-rich exports
- Examples:
  - OLD: `view_ingredients.json`
  - NEW: `aug_ingredients.json`

**Rationale:**
- "aug" = augmentation (AI-assisted data enhancement)
- Distinguishes from other export types
- Matches intended workflow (augment data with AI)

**Pattern reference:** Existing prefix logic in export service

**Success criteria:**
- [ ] All context-rich exports use "aug_" prefix
- [ ] No files created with "view_" prefix
- [ ] Prefix change applies consistently

---

### FR-2: Add Missing Entity Types

**What it must do:**
- Add Products to entity selection
- Add Material Products to entity selection
- Total entity types: 7 (was 5, now 7)

**Complete list:**
1. Ingredients
2. Products (NEW)
3. Recipes
4. Finished Units
5. Finished Goods
6. Materials
7. Material Products (NEW)

**Pattern reference:** Existing entity type handling for Ingredients, Materials, etc.

**Success criteria:**
- [ ] Products appears in entity selection
- [ ] Material Products appears in entity selection
- [ ] Both entities export correctly
- [ ] Export format matches other entities

---

### FR-3: Change Radio Buttons to Checkboxes

**What it must do:**
- Replace radio buttons with checkboxes
- Enable multi-select (user can select 1+ entities)
- Allow any combination of entities
- Update export logic to handle multiple selections

**Why checkboxes:**
- Users often want multiple entities
- Radio buttons force single selection
- Checkboxes standard for multi-select

**Pattern reference:** Checkbox widgets in other dialogs

**Success criteria:**
- [ ] Checkboxes replace radio buttons
- [ ] User can select multiple entities
- [ ] Export processes all selected entities
- [ ] Validation prevents empty selection (at least one required)

---

### FR-4: Add "All" Option

**What it must do:**
- Add "All" checkbox at top of entity list
- When checked: selects all 7 entities
- When unchecked: deselects all entities
- Behavior:
  - Checking "All" → checks all entity checkboxes
  - Unchecking "All" → unchecks all entity checkboxes
  - Manually checking all entities → checks "All"
  - Manually unchecking any entity → unchecks "All"

**UI layout:**
```
☐ All
---
☐ Ingredients
☐ Products
☐ Recipes
☐ Finished Units
☐ Finished Goods
☐ Materials
☐ Material Products
```

**Pattern reference:** Standard "select all" checkbox pattern

**Success criteria:**
- [ ] "All" checkbox appears at top
- [ ] Checking "All" selects all entities
- [ ] Unchecking "All" deselects all entities
- [ ] Selecting all manually checks "All"
- [ ] Deselecting any unchecks "All"
- [ ] Export with "All" checked exports all 7 entities

---

### FR-5: Fix Button Text

**What it must do:**
- Change button text from "Export Context-Rich View" to "Export Context-Rich File"
- Match button text pattern from other export types

**Why "File" not "View":**
- "File" is accurate (exporting to file)
- "View" suggests UI display (incorrect)
- Consistency with "Export Catalog File", "Export Backup File"

**Pattern reference:** Other export buttons in same dialog

**Success criteria:**
- [ ] Button text reads "Export Context-Rich File"
- [ ] Button functionality unchanged
- [ ] Text matches other export button patterns

---

## Out of Scope

**Explicitly NOT included in F053:**
- ❌ Adding new entity types beyond Products/Material Products
- ❌ Changing export format or file structure
- ❌ Import functionality (separate feature)
- ❌ Export location selection (uses existing logic)
- ❌ Progress indicator enhancements (uses existing)

---

## Success Criteria

**Complete when:**

### File Prefix
- [ ] All context-rich exports use "aug_" prefix
- [ ] No "view_" prefix used anywhere
- [ ] File naming consistent: `aug_<entity>.json`

### Entity Types
- [ ] Products available for export
- [ ] Material Products available for export
- [ ] All 7 entities export correctly
- [ ] Export format matches existing entities

### Multi-Select UI
- [ ] Checkboxes replace radio buttons
- [ ] User can select 1+ entities
- [ ] "All" checkbox at top
- [ ] "All" behavior works correctly (select/deselect all)
- [ ] Manual selection syncs with "All" checkbox
- [ ] Validation prevents empty selection

### Button Text
- [ ] Button reads "Export Context-Rich File"
- [ ] Text consistent with other buttons

### Quality
- [ ] No errors when exporting multiple entities
- [ ] Files created in correct location
- [ ] Export service handles multi-select correctly
- [ ] UI intuitive and clear

---

## Architecture Principles

### Prefix Naming Convention

**"aug_" for augmentation exports:**
- Distinguishes context-rich exports
- Indicates purpose (AI augmentation)
- Consistent naming pattern

**Rationale**: Clear naming helps users understand file purpose

### Multi-Select Pattern

**Checkboxes for multiple selection:**
- Standard UI pattern
- Users familiar with behavior
- "All" checkbox common convention

**Rationale**: Use standard patterns for predictability

### Entity Completeness

**All relevant entities should be exportable:**
- Products (food items with brands)
- Material Products (material items with brands)
- Complete catalog coverage

**Rationale**: Users need full catalog export capability

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- No data changes (UI/naming only)
- Export functionality preserved

✅ **Principle II: Future-Proof Architecture**
- Entity list easily extensible
- Multi-select supports future needs

✅ **Principle III: Layered Architecture**
- UI changes in dialog layer
- Export service handles entity logic
- Clear separation maintained

✅ **Principle V: User-Centric Design**
- Multi-select improves usability
- "All" option speeds workflow
- Clear button text reduces confusion

✅ **Principle VI: Pragmatic Aspiration**
- Simple fixes to improve UX
- Standard patterns (checkboxes, "All")
- No over-engineering

---

## Risk Considerations

**Risk: Multi-select changes export logic**
- Current logic may assume single entity
- Mitigation: Planning phase identifies export service changes needed
- Verify export service can handle multiple entities (likely already does for backup export)

**Risk: "All" checkbox behavior confusing**
- Users may not understand sync behavior
- Mitigation: Standard pattern, widely understood
- Test with real user to verify intuitive

**Risk: Adding Products/Material Products breaks something**
- Entity types may have special handling
- Mitigation: Planning phase studies existing entity export logic
- Copy pattern exactly for new entities

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study backup export → uses checkboxes, handles multiple entities
- Study catalog export → may have "All" checkbox pattern
- Study entity type handling → understand how Products/Material Products differ
- Find prefix logic in export service → simple string replacement

**Key Implementation Areas:**

**UI Changes (Export Dialog):**
- Replace radio button group with checkbox group
- Add "All" checkbox at top with separator
- Update button text
- Wire "All" checkbox to select/deselect all
- Wire individual checkboxes to update "All" state

**Export Service Changes:**
- Change prefix "view_" → "aug_"
- Add Products to entity type handling (copy Ingredients pattern)
- Add Material Products to entity type handling (copy Materials pattern)
- Verify multi-select works (may already work)

**Focus Areas:**
- Prefix change is trivial (one string replacement)
- Entity addition follows existing patterns
- Multi-select UI needs "All" checkbox logic
- Button text is simple label change

---

**END OF SPECIFICATION**
