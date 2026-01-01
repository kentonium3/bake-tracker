---
work_package_id: "WP06"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
title: "UI Integration"
phase: "Phase 3 - UI"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "4513"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – UI Integration

## Objectives & Success Criteria

**Goal**: Integrate tree widget into existing UI components.

**Success Criteria**:
- Users can navigate ingredients via tree in Ingredients tab
- Recipe ingredient dialog uses tree for selection (leaf-only)
- Ingredient detail panel shows hierarchy breadcrumb
- Search and filter controls connected to tree widget
- Create/edit forms include hierarchy fields
- All UI flows work correctly with hierarchical data

## Context & Constraints

**References**:
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md` - UI Layer Design
- Spec: `kitty-specs/031-ingredient-hierarchy-taxonomy/spec.md` - User Stories US-001, US-002
- Quickstart: `kitty-specs/031-ingredient-hierarchy-taxonomy/quickstart.md`

**Constraints**:
- Must maintain backwards compatibility (flat view still works until migration)
- UI should not contain business logic (validation in services)
- Follow existing UI patterns and style
- Depends on WP04 (services) and WP05 (widget) being complete

## Subtasks & Detailed Guidance

### Subtask T032 – Integrate tree widget into ingredients_tab.py
- **Purpose**: Replace or augment flat ingredient list with tree view.
- **Steps**:
  1. Open `src/ui/ingredients_tab.py`
  2. Import IngredientTreeWidget from widgets
  3. Add tree widget alongside or replacing existing list
  4. Wire up selection callback to show ingredient details
  5. Consider split view: tree on left, details on right
  6. Handle refresh after ingredient create/update/delete
- **Files**: `src/ui/ingredients_tab.py`
- **Parallel?**: No (main integration point)
- **Notes**: May need layout adjustments; consider user testing

### Subtask T033 – Update recipe_ingredient_dialog.py to use tree selector
- **Purpose**: Use tree widget for ingredient selection in recipes.
- **Steps**:
  1. Open `src/ui/forms/recipe_ingredient_dialog.py`
  2. Replace dropdown/list with IngredientTreeWidget
  3. Configure with `leaf_only=True` for recipe context
  4. Wire up selection to populate ingredient field
  5. Show breadcrumb for selected ingredient
  6. Handle validation errors from service (non-leaf selected)
- **Files**: `src/ui/forms/recipe_ingredient_dialog.py`
- **Parallel?**: Yes (different dialog from T032)
- **Notes**: Dialog may need resize for tree widget

### Subtask T034 – Add ingredient detail panel showing hierarchy
- **Purpose**: Display breadcrumb path in ingredient details.
- **Steps**:
  1. Update ingredient detail view (in ingredients_tab or detail dialog)
  2. Add section showing hierarchy path:
     - Label: "Category Path:"
     - Value: "Chocolate → Dark Chocolate → Semi-Sweet Chips"
  3. Call `get_ancestors()` to build path
  4. Handle root ingredients (no ancestors)
- **Files**: `src/ui/ingredients_tab.py` or related detail component
- **Parallel?**: Yes (can be done with T033)
- **Notes**: Breadcrumb provides context for where ingredient lives

### Subtask T035 – Wire search and filter controls to tree widget
- **Purpose**: Connect existing search UI to tree widget.
- **Steps**:
  1. If ingredients_tab has existing search entry:
     - Connect to tree widget's search functionality
     - Or replace with tree widget's built-in search
  2. Ensure search results auto-expand in tree
  3. Consider filter by hierarchy level (show only leaves, etc.)
  4. Update any existing filter dropdowns
- **Files**: `src/ui/ingredients_tab.py`
- **Parallel?**: No (depends on T032)
- **Notes**: Avoid duplicate search boxes; integrate cleanly

### Subtask T036 – Update ingredient create/edit forms for hierarchy fields
- **Purpose**: Allow setting parent when creating/editing ingredients.
- **Steps**:
  1. Find ingredient create/edit form (in ingredients_tab or dialog)
  2. Add parent selection field:
     - Use IngredientTreeWidget with leaf_only=False
     - Or dropdown of level 0 and 1 ingredients
  3. Auto-calculate hierarchy_level from parent
  4. Validate: new ingredient level must not exceed 2
  5. Show current parent in edit mode
- **Files**: `src/ui/forms/ingredient_dialog.py` or similar
- **Parallel?**: Yes (different form from T033)
- **Notes**: Most new ingredients will be leaves (level 2)

## Test Strategy

- **Manual Testing**:
  - Navigate tree in ingredients tab
  - Select ingredient for recipe (verify leaf-only)
  - Create new ingredient with parent
  - Edit ingredient to change parent
  - Search and verify tree behavior

- **User Acceptance**:
  - Test with actual ingredient data
  - Verify intuitive navigation
  - Check responsiveness with 500+ ingredients

- **Commands**:
  ```bash
  # Run application for manual testing
  python src/main.py
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout issues with tree widget | Test early; adjust frame sizes as needed |
| User confusion with new navigation | Clear visual hierarchy; breadcrumbs help |
| Performance with full ingredient list | Lazy loading in tree widget handles this |

## Definition of Done Checklist

- [ ] T032: Ingredients tab displays tree view
- [ ] T033: Recipe dialog uses tree with leaf-only mode
- [ ] T034: Detail panel shows breadcrumb path
- [ ] T035: Search connected to tree widget
- [ ] T036: Create/edit forms include parent selection
- [ ] All UI flows work correctly
- [ ] No regressions in existing functionality

## Review Guidance

- Verify tree widget configured correctly (leaf_only where appropriate)
- Verify breadcrumb displays correctly at all levels
- Test with empty tree (no hierarchy data yet)
- Verify forms validate hierarchy constraints
- Check CustomTkinter theme compatibility

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T15:34:06Z – claude – shell_pid=37805 – lane=doing – Starting UI integration
- 2025-12-31T15:58:59Z – claude – shell_pid=37805 – lane=for_review – Moved to for_review
- 2025-12-31T19:44:09Z – claude-reviewer – shell_pid=4513 – lane=done – Code review passed: Tree view toggle in ingredients tab, recipe dialog with leaf-only, parent selection in create/edit forms, breadcrumb enabled
