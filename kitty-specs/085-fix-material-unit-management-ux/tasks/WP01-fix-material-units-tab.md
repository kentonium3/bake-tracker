---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Fix Material Units Tab Query"
phase: "Phase 1 - Bug Fixes"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "74395"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-30T22:39:29Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Fix Material Units Tab Query

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this WP starts fresh from main.

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Fix the Material Units tab to display all MaterialUnits from the database with their associated product names.

**Success Criteria**:
- [ ] Material Units tab shows ALL MaterialUnits in the database (currently shows none)
- [ ] Each unit displays its associated MaterialProduct name for context
- [ ] Tab refreshes correctly when units are created/edited/deleted in Edit Product dialog
- [ ] Query uses correct F084 schema path: `MaterialProduct.material_units`

---

## Context & Constraints

**Background**: Feature 084 changed the MaterialUnit schema - units are now children of MaterialProduct (not Material). The Material Units tab query likely still references the old relationship and returns no results.

**Related Documents**:
- Spec: `kitty-specs/085-fix-material-unit-management-ux/spec.md` (FR-001)
- Plan: `kitty-specs/085-fix-material-unit-management-ux/plan.md` (Issue 1)
- Constitution: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)

**Key Files**:
- `src/ui/materials_tab.py` - Contains the Material Units tab implementation
- `src/models/material_unit.py` - MaterialUnit model
- `src/models/material_product.py` - MaterialProduct model (has `material_units` relationship)
- `src/services/material_unit_service.py` - Service layer for MaterialUnit operations

**Constraints**:
- Must use service layer for data access (Principle V)
- Must handle empty database gracefully
- Must not break existing Edit Product dialog functionality

---

## Subtasks & Detailed Guidance

### Subtask T001 – Investigate Material Units Tab Query

**Purpose**: Locate and understand the broken query that populates the Material Units tab listing.

**Steps**:
1. Open `src/ui/materials_tab.py` and search for "Material Units" tab implementation
2. Find the method that loads/refreshes the Material Units listing (likely `_load_material_units()` or similar)
3. Examine the query being used - it likely references an old `Material.units` relationship
4. Check if there's a separate tab class or if it's integrated into the main Materials tab
5. Document the current query path and why it returns no results

**Files**:
- `src/ui/materials_tab.py` - Primary investigation target

**Expected Finding**: Query uses old `Material.units` relationship (removed in F084) or doesn't exist yet and the tab is a placeholder.

**Notes**:
- The Edit Product dialog's Material Units section works differently (uses `material_unit_service.list_units(product_id)`)
- The tab-level listing needs to show ALL units across ALL products

---

### Subtask T002 – Fix Query to Use F084 Schema

**Purpose**: Update the tab query to correctly traverse `MaterialProduct → MaterialUnit` relationship.

**Steps**:
1. If using direct query, replace with service layer call
2. Create or update the service method to fetch all MaterialUnits with product context
3. Use SQLAlchemy eager loading to include product information:
   ```python
   # In material_unit_service.py (if needed)
   def list_all_units() -> list:
       """List all MaterialUnits with their product information."""
       with session_scope() as session:
           units = session.query(MaterialUnit)\
               .options(joinedload(MaterialUnit.material_product))\
               .order_by(MaterialUnit.name)\
               .all()
           # Return as dicts or detached objects
           return [unit.to_dict(include_relationships=True) for unit in units]
   ```
4. Update the UI method to call the service and populate the listing
5. Verify query returns all expected units

**Files**:
- `src/ui/materials_tab.py` - Update UI loading logic
- `src/services/material_unit_service.py` - Add `list_all_units()` if needed

**Notes**:
- Check if `list_all_units()` already exists in the service
- Session management: return dicts to avoid detached object issues
- Import `joinedload` from `sqlalchemy.orm` if using eager loading

---

### Subtask T003 – Add Product Name Column to Listing

**Purpose**: Display the associated MaterialProduct name alongside each MaterialUnit for user context.

**Steps**:
1. Locate the Treeview or table widget used for the Material Units listing
2. Add a "Product" column to the column definitions:
   ```python
   columns = ("name", "product", "quantity_per_unit")
   tree.heading("product", text="Product")
   tree.column("product", width=150)
   ```
3. Update the data population loop to include product name:
   ```python
   for unit in units:
       tree.insert("", "end", values=(
           unit["name"],
           unit.get("material_product", {}).get("name", "Unknown"),
           f"{unit['quantity_per_unit']:.4f}",
       ))
   ```
4. Ensure column widths are reasonable and text doesn't truncate
5. Test with both units that have products and any edge cases

**Files**:
- `src/ui/materials_tab.py` - Update Treeview columns

**Notes**:
- Column order should be: Name, Product, Quantity per Unit
- Handle case where product might be None (defensive coding)
- Consider adding Material name as well for full hierarchy context

---

## Test Strategy

**Manual Testing Required** (no automated tests for this UI fix):

1. **Database Setup**:
   - Ensure database has MaterialUnits for both "each" and "linear" type products
   - If empty, create units via Edit Product dialog first

2. **Tab Verification**:
   - Navigate to Materials tab
   - Find/click Material Units sub-tab or section
   - Verify ALL units appear in the listing
   - Verify each unit shows its product name

3. **Refresh Testing**:
   - Create a new unit via Edit Product dialog
   - Return to Material Units tab
   - Verify new unit appears in listing
   - Delete a unit and verify it disappears

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tab doesn't exist yet | Check if implementation needed from scratch - flag in review |
| Performance with many units | Use pagination if >100 units (defer to future enhancement) |
| Service returns detached objects | Return dicts from service to avoid SQLAlchemy detachment |

---

## Definition of Done Checklist

- [ ] T001: Query issue identified and documented
- [ ] T002: Query fixed to use F084 schema (MaterialProduct.material_units)
- [ ] T003: Product name column added and displaying correctly
- [ ] Material Units tab shows ALL units in database
- [ ] Product names display correctly for all units
- [ ] Tab refreshes when units are modified

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify ALL MaterialUnits appear (compare with database count)
2. Verify product names are correct (not "Unknown" or blank)
3. Verify no errors in console when loading tab
4. Verify service layer is used (not direct queries in UI)

**Code Review Focus**:
- Session management (no detached objects)
- Error handling for empty database
- Column alignment and display

---

## Activity Log

- 2026-01-30T22:39:29Z – system – lane=planned – Prompt created.
- 2026-01-30T22:46:16Z – claude-opus – shell_pid=73516 – lane=doing – Started implementation via workflow command
- 2026-01-30T22:48:38Z – claude-opus – shell_pid=73516 – lane=for_review – Ready for review: Added eager loading to list_units() to fix Material Units tab showing no units
- 2026-01-30T22:49:43Z – claude-opus – shell_pid=74395 – lane=doing – Started review via workflow command
