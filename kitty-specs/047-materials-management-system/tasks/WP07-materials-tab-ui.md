---
work_package_id: "WP07"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
title: "Materials Tab UI"
phase: "Phase 2 - UI"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Materials Tab UI

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create CustomTkinter UI for materials management mirroring the Ingredients tab pattern.

**Success Criteria:**
- User can navigate material hierarchy in tree view
- User can create/edit/delete categories, subcategories, materials, products
- User can record purchases and see inventory update
- User can create MaterialUnits
- User can add materials to FinishedGood compositions
- UI patterns match existing Ingredients tab for consistency

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - SC-006: User can complete full workflow without documentation
- `src/ui/ingredients_tab.py` - Pattern to mirror
- `src/ui/` - Existing UI patterns and components

**UI Framework**: CustomTkinter (CTk)
**Pattern**: Mirror Ingredients tab structure exactly for user familiarity

**Dependencies:**
- WP02 (catalog service)
- WP03 (purchase service)
- WP04 (material unit service)

## Subtasks & Detailed Guidance

### Subtask T047 - Create Materials Tab Structure
- **Purpose**: Base tab frame with layout
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Create file with CTk imports
  2. Define `MaterialsTab(CTkFrame)` class
  3. Create two-panel layout (hierarchy tree + detail panel)
  4. Add toolbar with action buttons (Add, Edit, Delete, Refresh)
  5. Initialize with empty state

### Subtask T048 - Implement Hierarchy Tree View
- **Purpose**: Display Category > Subcategory > Material tree
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Add CTkTreeview or equivalent widget
  2. Load categories as root nodes
  3. Load subcategories as children of categories
  4. Load materials as children of subcategories
  5. Show product count indicator next to materials
  6. Handle selection events to update detail panel
  7. Support expand/collapse

### Subtask T049 - Implement Product List Panel
- **Purpose**: Show products for selected material
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Add scrollable list/table for products
  2. Show columns: Name, Brand, Inventory, Unit Cost, Supplier
  3. Update when material selected in tree
  4. Support add/edit/delete product actions
  5. Show inventory with appropriate units (inches, each, etc.)

### Subtask T050 - Implement Purchase Recording Form
- **Purpose**: Dialog for recording new purchases
- **File**: `src/ui/materials_tab.py` (or separate dialog file)
- **Parallel?**: No
- **Steps**:
  1. Create modal dialog for purchase entry
  2. Fields: Product (pre-selected), Supplier (dropdown), Date, Packages, Package Price, Notes
  3. Calculate and show units_added preview
  4. On save: call `material_purchase_service.record_purchase()`
  5. Show success/error message
  6. Refresh product list to show updated inventory

### Subtask T051 - Implement Inventory Adjustment Controls
- **Purpose**: Allow manual inventory corrections
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Add adjustment button to product panel
  2. Create dialog with options:
     - Set to specific count
     - Set to percentage (e.g., "50% remaining")
  3. On save: call `material_purchase_service.adjust_inventory()`
  4. Show confirmation with new inventory value
  5. Refresh product list

### Subtask T052 - Implement MaterialUnit Management UI
- **Purpose**: Create and manage MaterialUnits
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Add "Units" section to material detail panel
  2. List existing MaterialUnits for selected material
  3. Show: Name, Quantity per Unit, Available Inventory, Current Cost
  4. Add/Edit/Delete buttons
  5. Unit creation form: Name, Quantity per Unit, Description
  6. Call `material_unit_service` for operations

### Subtask T053 - Add Material to Composition Dialog Integration
- **Purpose**: Allow adding materials to FinishedGoods
- **File**: Integrate with existing composition UI
- **Parallel?**: No
- **Steps**:
  1. Find existing "Add Component" dialog in FinishedGood UI
  2. Add "Material" tab/section to component type selector
  3. Two options:
     - "Specific Material Unit" - dropdown of MaterialUnits
     - "Generic Material" - dropdown of Materials (placeholder)
  4. Show availability and cost for selection
  5. Create composition via factory methods

### Subtask T054 - Wire Up Service Calls with Error Handling
- **Purpose**: Connect UI to services with proper error handling
- **File**: `src/ui/materials_tab.py`
- **Parallel?**: No
- **Steps**:
  1. Wrap all service calls in try/except
  2. Display user-friendly error messages via CTkMessageBox
  3. Handle ValidationError with specific message
  4. Handle database errors gracefully
  5. Ensure UI state refreshes after operations

## Test Strategy

**Manual testing checklist (UI tests optional):**

1. **Hierarchy Navigation**
   - Create category "Ribbons" -> appears in tree
   - Create subcategory "Satin" under Ribbons -> appears nested
   - Create material "Red Satin" under Satin -> appears with "0 products"
   - Create product -> product count updates

2. **Purchase Flow**
   - Select product with 0 inventory
   - Record purchase: 2 packs, 100 units each, $24 total
   - Verify inventory shows 200 units at $0.12/unit

3. **MaterialUnit Creation**
   - Create "6-inch ribbon" unit for material with inventory
   - Verify available inventory shows correct calculation
   - Verify cost shows weighted average * quantity

4. **Composition Integration**
   - Open FinishedGood composition editor
   - Add MaterialUnit component
   - Verify cost appears in breakdown
   - Add generic Material placeholder
   - Verify "selection pending" indicator

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI responsiveness | Use threading for long service calls if needed |
| Layout inconsistency | Mirror Ingredients tab exactly |
| Error message clarity | Show specific, actionable error messages |
| State synchronization | Refresh relevant panels after any operation |

## Definition of Done Checklist

- [ ] Materials tab integrated into main application
- [ ] Hierarchy tree displays all levels correctly
- [ ] Product list shows inventory and cost
- [ ] Purchase recording updates inventory immediately
- [ ] Inventory adjustment works by count and percentage
- [ ] MaterialUnit management functional
- [ ] Can add materials to FinishedGood compositions
- [ ] Error handling shows user-friendly messages
- [ ] Manual testing checklist passes

## Review Guidance

**Reviewer should verify:**
1. UI pattern matches Ingredients tab closely
2. Error messages are user-friendly (no stack traces)
3. All CRUD operations work correctly
4. Inventory updates visible immediately after purchase
5. MaterialUnit available inventory calculation correct

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T22:16:10Z – claude – lane=doing – Starting materials tab UI implementation
- 2026-01-10T22:27:51Z – claude – lane=for_review – Materials Tab UI complete with composition integration
- 2026-01-11T01:06:55Z – claude – lane=done – Review passed: Materials Tab UI with hierarchy tree, product panel, purchase recording, MaterialUnit management.
