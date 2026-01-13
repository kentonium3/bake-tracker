---
work_package_id: "WP08"
subtasks:
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
title: "Menu Cleanup and Multi-Entity Support"
phase: "Phase 3 - Cleanup"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Menu Cleanup and Multi-Entity Support

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Remove redundant menu items and ensure multi-entity import works with dependency ordering.

**Success Criteria**:
- File menu shows only "Import Data" (no separate Import Catalog or Import Context-Rich)
- Multi-entity files display all detected entities with counts
- Multi-entity import processes entities in dependency order
- Entity checkboxes hidden for Catalog purpose (auto-detection only)
- No regressions in any import workflow

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US1, US7)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`

**Dependencies**:
- WP07 (unified import dialog) must be complete

**Existing Code**:
- Main window/menu setup (find location)
- `src/ui/import_export_dialog.py` - ImportViewDialog class (may be orphaned)
- `src/services/catalog_import_service.py` - entity ordering

## Subtasks & Detailed Guidance

### Subtask T052 - Remove Import Catalog menu item
- **Purpose**: Consolidate to single import entry point
- **Steps**:
  1. Find menu setup (likely `src/ui/main_window.py` or similar)
  2. Search for "Import Catalog" text
  3. Remove menu item definition
  4. Remove associated command binding
  5. Verify no orphaned handler code
- **Files**: `src/ui/main_window.py` (or equivalent)
- **Parallel?**: No (foundational cleanup)
- **Notes**: May be implemented as separate menu item or submenu

### Subtask T053 - Remove Import Context-Rich menu item
- **Purpose**: Consolidate to single import entry point
- **Steps**:
  1. Search for "Import Context-Rich" or "Import View" text
  2. Remove menu item definition
  3. Remove associated command binding
  4. This may reference ImportViewDialog class
- **Files**: `src/ui/main_window.py` (or equivalent)
- **Parallel?**: Yes (parallel to T052)
- **Notes**: May be labeled differently; search for "Context" or "View"

### Subtask T054 - Remove orphaned handler code
- **Purpose**: Clean up unused code
- **Steps**:
  1. Check if ImportViewDialog class is still needed
  2. If only used by removed menu item, consider removing entire class
  3. Remove any handler methods that were only called from removed menu items
  4. Keep code if other callers exist
  5. Document any intentional preservation
- **Files**: `src/ui/import_export_dialog.py`, `src/ui/main_window.py`
- **Parallel?**: No (after T052, T053)
- **Notes**: ImportViewDialog at line 1148 may be obsolete

### Subtask T055 - Update detection display for multi-entity files
- **Purpose**: Show all detected entities clearly
- **Steps**:
  1. In `_detect_format()`, handle multi-entity case
  2. Build display string: "Multiple entities: Suppliers (6), Ingredients (45), Products (12)"
  3. Update detection_label with this formatted string
  4. Use orange color for "select purpose below" indicator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes (independent of menu cleanup)
- **Notes**: Multi-entity files need user to select purpose

### Subtask T056 - Ensure multi-entity dependency order
- **Purpose**: Import entities in FK-safe order
- **Steps**:
  1. Verify `catalog_import_service` processes in order:
     - suppliers (no FKs)
     - ingredients (no FKs)
     - products (FK to ingredient, supplier)
     - materials (no FKs)
     - material_products (FK to material, product)
     - recipes (FK to ingredients)
  2. If order not enforced, add explicit ordering
  3. Test with file containing suppliers + products
- **Files**: `src/services/catalog_import_service.py`
- **Parallel?**: Yes (independent of menu cleanup)
- **Notes**: Order prevents FK constraint violations

### Subtask T057 - Hide entity checkboxes for Catalog purpose
- **Purpose**: Rely on auto-detection per FR-009
- **Steps**:
  1. In ImportDialog, when Catalog selected, hide any entity selection checkboxes
  2. All detected entities should import automatically
  3. Only show mode selection (Update Existing / Add New Only)
  4. Spec FR-009: "System MUST NOT display entity checkboxes for Catalog purpose"
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after T055)
- **Notes**: Current UI may already do this; verify

### Subtask T058 - Regression verification
- **Purpose**: Ensure no existing workflows broken
- **Steps**:
  1. Test Backup purpose: restore full backup
  2. Test Catalog purpose: import ingredients.json
  3. Test Purchases purpose: import purchase transactions
  4. Test Adjustments purpose: import inventory adjustments
  5. Test Context-Rich purpose: import aug_ingredients.json
  6. Verify File menu structure correct
  7. Document any issues found
- **Files**: None (testing only)
- **Parallel?**: No (final verification)
- **Notes**: This is manual testing; document results

## Expected File Menu Structure

**Before**:
```
File
├── Import Data...
├── Import Catalog...    ← REMOVE
├── Import Context-Rich...    ← REMOVE
├── Export Data...
├── Preferences...    ← Added by WP03
├── ─────────────
└── Exit
```

**After**:
```
File
├── Import Data...
├── Export Data...
├── Preferences...
├── ─────────────
└── Exit
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing workflows | Thorough regression testing (T058) |
| Orphaned code causes issues | Careful code review before deletion |
| Multi-entity order wrong | Explicit ordering in service layer |

## Definition of Done Checklist

- [ ] "Import Catalog" menu item removed
- [ ] "Import Context-Rich" menu item removed
- [ ] Orphaned code cleaned up or documented
- [ ] Multi-entity detection shows all entities with counts
- [ ] Multi-entity import processes in dependency order
- [ ] Entity checkboxes hidden for Catalog purpose
- [ ] All 5 import purposes verified working
- [ ] File menu structure matches expected

## Review Guidance

**Key checkpoints**:
1. Open File menu, verify only "Import Data" (not Catalog/Context-Rich)
2. Import multi-entity file, verify all entities listed with counts
3. Import file with suppliers + products, verify no FK errors
4. Test each of 5 purposes to verify no regression
5. Check for any console errors or warnings

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T19:24:24Z – claude – lane=doing – Starting implementation of Menu Cleanup and Multi-Entity Support
- 2026-01-13T19:28:29Z – claude – lane=for_review – Implemented menu cleanup and multi-entity display improvements
- 2026-01-13T20:57:16Z – claude – lane=done – Code review APPROVED by claude - Import Catalog/Context-Rich menu items removed, multi-entity display, dependency ordering verified
