---
work_package_id: "WP04"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "Integration Tests"
phase: "Phase C - Validation"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "3311"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T10:45:22Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Integration Tests

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Objective**: Write integration tests to prevent regression of cascading filter behavior and recipe L2-only enforcement.

**Success Criteria**:
- SC-001: Tests cover L0->L1 cascading in products tab
- SC-002: Tests cover L1->L2 cascading in products tab
- SC-003: Tests cover Clear button functionality
- SC-004: Tests cover inventory tab cascading (mirror products)
- SC-005: Tests cover recipe L2-only enforcement
- SC-006: All tests pass in CI
- SC-007: No regressions in existing test suite

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/034-cascading-filters-recipe/spec.md` - All user stories
- Plan: `kitty-specs/034-cascading-filters-recipe/plan.md` - WP4 details
- Completed WPs: WP01, WP02, WP03 (verify implementations)

**Key Findings**:
- UI testing may require mocking CustomTkinter components
- Consider pytest fixtures for database setup
- Focus on behavioral tests, not implementation details

**Architecture Constraints**:
- Test file location: `src/tests/ui/test_cascading_filters.py` (new file)
- Use pytest conventions
- Mock UI components if direct testing is complex

**Dependencies**:
- Depends on WP01, WP02, WP03 completion
- Tests validate the implementations from those WPs

## Subtasks & Detailed Guidance

### Subtask T023 - Create test file

**Purpose**: Set up the test file structure.

**Steps**:
1. Create directory if needed: `src/tests/ui/`
2. Create file: `src/tests/ui/test_cascading_filters.py`
3. Add imports and basic structure:
   ```python
   """
   Integration tests for cascading hierarchy filters.

   Tests the L0 -> L1 -> L2 cascading behavior in Products and Inventory tabs,
   and L2-only enforcement in recipe ingredient selection.
   """

   import pytest
   from unittest.mock import Mock, patch, MagicMock

   # Import services for test data setup
   from src.services import ingredient_hierarchy_service
   from src.services.database import session_scope


   class TestProductsTabCascading:
       """Tests for Products tab cascading filters."""
       pass


   class TestInventoryTabCascading:
       """Tests for Inventory tab cascading filters."""
       pass


   class TestRecipeIngredientSelection:
       """Tests for recipe L2-only ingredient selection."""
       pass
   ```
4. Add pytest fixtures for test data

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - foundation for other tests

### Subtask T024 - Test L0 selection updates L1

**Purpose**: Test that selecting L0 populates L1 with correct children.

**Steps**:
1. Add test in `TestProductsTabCascading`:
   ```python
   def test_l0_selection_updates_l1_options(self, mock_products_tab):
       """When L0 is selected, L1 should show only children of that L0."""
       # Arrange
       l0_ingredient = {"id": 1, "display_name": "Baking", "hierarchy_level": 0}
       l1_children = [
           {"id": 10, "display_name": "Flour", "hierarchy_level": 1},
           {"id": 11, "display_name": "Sugar", "hierarchy_level": 1},
       ]

       with patch.object(ingredient_hierarchy_service, 'get_children', return_value=l1_children):
           # Act
           mock_products_tab._on_l0_filter_change("Baking")

           # Assert
           assert mock_products_tab.l1_filter_dropdown.configure.called
           call_args = mock_products_tab.l1_filter_dropdown.configure.call_args
           assert "Flour" in call_args[1]["values"]
           assert "Sugar" in call_args[1]["values"]
   ```
2. Consider testing edge case: L0 with no children

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - depends on T023

### Subtask T025 - Test L1 selection updates L2

**Purpose**: Test that selecting L1 populates L2 with correct leaves.

**Steps**:
1. Add test:
   ```python
   def test_l1_selection_updates_l2_options(self, mock_products_tab):
       """When L1 is selected, L2 should show only leaves under that L1."""
       l2_leaves = [
           {"id": 100, "display_name": "All-Purpose Flour", "hierarchy_level": 2},
           {"id": 101, "display_name": "Bread Flour", "hierarchy_level": 2},
       ]

       with patch.object(ingredient_hierarchy_service, 'get_children', return_value=l2_leaves):
           mock_products_tab._on_l1_filter_change("Flour")

           assert mock_products_tab.l2_filter_dropdown.configure.called
           call_args = mock_products_tab.l2_filter_dropdown.configure.call_args
           assert "All-Purpose Flour" in call_args[1]["values"]
   ```
2. Test edge case: L1 with no L2 children

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - follows T024

### Subtask T026 - Test Clear button

**Purpose**: Test that Clear button resets all filters.

**Steps**:
1. Add test:
   ```python
   def test_clear_filters_resets_all_dropdowns(self, mock_products_tab):
       """Clear button should reset all hierarchy filters to default."""
       # Arrange - set some filter values
       mock_products_tab.l0_filter_var.set("Baking")
       mock_products_tab.l1_filter_var.set("Flour")

       # Act
       mock_products_tab._clear_filters()

       # Assert
       assert mock_products_tab.l0_filter_var.get() == "All Categories"
       assert mock_products_tab.l1_filter_var.get() == "All"
       assert mock_products_tab.l2_filter_var.get() == "All"
       assert mock_products_tab.l1_filter_dropdown.configure.called
   ```

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - follows T025

### Subtask T027 - Test inventory tab cascading

**Purpose**: Mirror products tab tests for inventory tab.

**Steps**:
1. Add parallel tests in `TestInventoryTabCascading`:
   ```python
   def test_l0_selection_updates_l1_options(self, mock_inventory_tab):
       """Same as products tab - L0 selection should update L1."""
       # Similar implementation to T024
       pass

   def test_l1_selection_updates_l2_options(self, mock_inventory_tab):
       """Same as products tab - L1 selection should update L2."""
       pass

   def test_clear_filters_resets_hierarchy_dropdowns(self, mock_inventory_tab):
       """Clear should reset hierarchy filters."""
       pass
   ```
2. Ensure tests use inventory tab's method names (may differ slightly)

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - follows T026

### Subtask T028 - Test recipe L2-only enforcement

**Purpose**: Test that recipe ingredient selection enforces leaf-only.

**Steps**:
1. Add tests in `TestRecipeIngredientSelection`:
   ```python
   def test_tree_widget_has_leaf_only_enabled(self):
       """Verify tree widget is configured with leaf_only=True."""
       # This may require inspecting the widget configuration
       pass

   def test_non_leaf_selection_blocked(self, mock_recipe_dialog):
       """Selecting L0 or L1 should not enable selection."""
       l0_ingredient = {"id": 1, "display_name": "Baking", "is_leaf": False}

       mock_recipe_dialog._on_tree_select(l0_ingredient)

       assert mock_recipe_dialog._selected_ingredient is None

   def test_leaf_selection_allowed(self, mock_recipe_dialog):
       """Selecting L2 should enable selection."""
       l2_ingredient = {"id": 100, "display_name": "Flour", "is_leaf": True}

       mock_recipe_dialog._on_tree_select(l2_ingredient)

       assert mock_recipe_dialog._selected_ingredient == l2_ingredient
   ```

**Files**: `src/tests/ui/test_cascading_filters.py`
**Parallel?**: No - follows T027

### Subtask T029 - Run full test suite

**Purpose**: Verify no regressions and all new tests pass.

**Steps**:
1. Run new tests only:
   ```bash
   pytest src/tests/ui/test_cascading_filters.py -v
   ```
2. Run full test suite:
   ```bash
   pytest src/tests -v
   ```
3. Verify all tests pass
4. Fix any failures before completing WP

**Files**: N/A - test execution
**Parallel?**: No - final validation

## Test Strategy

**Test Approach**:
- Mock CustomTkinter components where direct testing is complex
- Use pytest fixtures for common setup
- Focus on behavioral validation, not implementation details
- Ensure tests are deterministic (no timing dependencies)

**Fixtures Needed**:
```python
@pytest.fixture
def mock_products_tab():
    """Create a mock products tab with filter components."""
    tab = Mock()
    tab.l0_filter_var = Mock()
    tab.l1_filter_var = Mock()
    tab.l2_filter_var = Mock()
    tab.l0_filter_dropdown = Mock()
    tab.l1_filter_dropdown = Mock()
    tab.l2_filter_dropdown = Mock()
    tab._l0_map = {}
    tab._l1_map = {}
    tab._l2_map = {}
    return tab
```

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UI mocking complexity | Medium | Focus on service integration, mock UI components |
| Tests too coupled to implementation | Medium | Test behaviors, not internals |
| Flaky tests | Low | Use deterministic test data, avoid timing |

## Definition of Done Checklist

- [ ] All subtasks T023-T029 completed
- [ ] Test file created with proper structure
- [ ] Tests cover L0->L1 cascading
- [ ] Tests cover L1->L2 cascading
- [ ] Tests cover Clear button
- [ ] Tests cover inventory tab (parallel to products)
- [ ] Tests cover recipe L2-only enforcement
- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewers should verify**:
1. Tests cover all acceptance scenarios from spec
2. Tests are maintainable and not overly coupled to implementation
3. Fixtures are reusable and well-structured
4. Edge cases are covered (empty results, no children, etc.)
5. Tests run reliably in CI

## Activity Log

- 2026-01-02T10:45:22Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T16:15:00Z - claude - lane=planned - DEFERRED: WP04 is P3 priority and optional. Core functionality (WP01-03) is complete with all 1443 existing tests passing. Integration tests for cascading behavior deferred to future iteration. Cursor review APPROVED WITH CHANGES (addressed).
- 2026-01-02T16:36:13Z – claude – shell_pid=1504 – lane=doing – Implementing integration tests
- 2026-01-02T16:41:27Z – claude – shell_pid=2426 – lane=for_review – 14 integration tests written and passing. Full suite: 1457 passed, 14 skipped.
- 2026-01-02T16:50:45Z – claude-reviewer – shell_pid=3311 – lane=done – Review approved: 14 integration tests added, all passing. Full suite: 1457 passed, 14 skipped.
