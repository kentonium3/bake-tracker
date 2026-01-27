---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Bundle Decomposition Algorithm"
phase: "Phase 1 - Service Layer"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "28478"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-26T19:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Bundle Decomposition Algorithm

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**No dependencies** – Start directly:

```bash
spec-kitty implement WP01 --agent claude
```

---

## Objectives & Success Criteria

**Objective**: Implement a recursive algorithm to decompose `FinishedGood` bundles into their required atomic recipe IDs.

**Success Criteria**:
- [ ] `get_required_recipes(fg_id, session)` returns `Set[int]` of all recipe IDs required
- [ ] Atomic FG (single FinishedUnit) returns single recipe ID
- [ ] Simple bundle returns all component recipe IDs
- [ ] Nested bundle (bundle containing bundle) recursively decomposes
- [ ] Circular reference detection raises `CircularReferenceError`
- [ ] Depth >10 raises `MaxDepthExceededError`
- [ ] All unit tests pass

---

## Context & Constraints

**Key Discovery**: `FinishedGood` is a bundle container that does NOT have a `recipe_id` field. Recipe linkage is on `FinishedUnit` (atomic items) via `recipe_id`. Bundles contain components via the `Composition` junction model.

**Model Hierarchy**:
```
FinishedGood (bundle)
└── components: List[Composition]
    ├── finished_unit_id → FinishedUnit → recipe_id → Recipe (ATOMIC)
    └── finished_good_id → FinishedGood (nested bundle, RECURSE)
```

**Reference Documents**:
- Spec: `kitty-specs/070-finished-goods-filtering/spec.md` (FR-002, FR-008, FR-009)
- Data Model: `kitty-specs/070-finished-goods-filtering/data-model.md` (Decomposition Algorithm)
- Research: `kitty-specs/070-finished-goods-filtering/research.md` (Recursive Algorithm Patterns)
- Constitution: `.kittify/memory/constitution.md` (Principle IV: TDD, Principle V: Layered Architecture)

**Pattern to Follow**: `src/services/planning/batch_calculation.py:149-234` (`explode_bundle_requirements()`)

**Session Management**: All service methods MUST accept `session` parameter. Do NOT create internal sessions. See CLAUDE.md Session Management section.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create Exception Classes

**Purpose**: Define custom exceptions for error conditions during bundle decomposition.

**Steps**:
1. Add to top of `src/services/event_service.py` (near existing imports/exceptions):

```python
# F070: FG Availability exceptions
class CircularReferenceError(Exception):
    """Raised when a bundle contains a circular reference."""
    def __init__(self, fg_id: int, path: List[int]):
        self.fg_id = fg_id
        self.path = path
        super().__init__(f"Circular reference detected: FG {fg_id} in path {path}")


class MaxDepthExceededError(Exception):
    """Raised when bundle nesting exceeds maximum depth."""
    def __init__(self, depth: int, max_depth: int):
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(f"Maximum nesting depth {max_depth} exceeded at depth {depth}")
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (foundational)
**Notes**: These exceptions will be raised by T002-T004 and caught by callers for error handling.

---

### Subtask T002 – Implement get_required_recipes() Function

**Purpose**: Core recursive function to traverse FinishedGood composition and collect required recipe IDs.

**Steps**:
1. Add the following function to `src/services/event_service.py`:

```python
from typing import Set, Optional
from src.models.finished_good import FinishedGood

MAX_FG_NESTING_DEPTH = 10


def get_required_recipes(
    fg_id: int,
    session: Session,
    *,
    _visited: Optional[Set[int]] = None,
    _depth: int = 0,
) -> Set[int]:
    """
    Recursively decompose a FinishedGood to determine all required recipe IDs.

    Args:
        fg_id: The FinishedGood ID to decompose
        session: Database session (required, caller manages transaction)
        _visited: Internal tracking for circular reference detection
        _depth: Internal tracking for depth limiting

    Returns:
        Set of recipe IDs required to produce this FinishedGood

    Raises:
        CircularReferenceError: If bundle contains circular reference
        MaxDepthExceededError: If nesting exceeds MAX_FG_NESTING_DEPTH
        ValidationError: If fg_id not found
    """
    # Initialize visited set on first call
    if _visited is None:
        _visited = set()

    # Check depth limit
    if _depth > MAX_FG_NESTING_DEPTH:
        raise MaxDepthExceededError(_depth, MAX_FG_NESTING_DEPTH)

    # Check for circular reference
    if fg_id in _visited:
        raise CircularReferenceError(fg_id, list(_visited))

    # Mark as visited
    _visited.add(fg_id)

    # Query the FinishedGood with components eager-loaded
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
    if fg is None:
        raise ValidationError([f"FinishedGood {fg_id} not found"])

    recipes: Set[int] = set()

    # Traverse components
    for comp in fg.components:
        if comp.finished_unit_id is not None:
            # Atomic component: get recipe directly from FinishedUnit
            if comp.finished_unit_component and comp.finished_unit_component.recipe_id:
                recipes.add(comp.finished_unit_component.recipe_id)
        elif comp.finished_good_id is not None:
            # Nested bundle: recurse
            child_recipes = get_required_recipes(
                comp.finished_good_id,
                session,
                _visited=_visited,
                _depth=_depth + 1,
            )
            recipes.update(child_recipes)
        # else: packaging/material component - no recipe needed (skip)

    return recipes
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (depends on T001)
**Notes**:
- Import `FinishedGood` model
- Use `session.query()` not `session.get()` for filter capability
- Components are eager-loaded via `lazy="joined"` on FinishedGood model

---

### Subtask T003 – Add Circular Reference Detection

**Purpose**: Ensure the algorithm detects and reports circular references in bundle structures.

**Steps**:
1. Already implemented in T002 via `_visited` set
2. Verify the logic:
   - Check `if fg_id in _visited` BEFORE adding to visited
   - Raise `CircularReferenceError` with both fg_id and full path
   - Path helps debugging (shows traversal history)

3. Test case to verify (add in T005):
```python
def test_raises_for_circular_reference(self, test_db, circular_bundle):
    """Circular references raise CircularReferenceError."""
    with pytest.raises(CircularReferenceError) as exc_info:
        get_required_recipes(circular_bundle.id, test_db)
    assert circular_bundle.id in exc_info.value.path
```

**Files**: `src/services/event_service.py` (verification), `src/tests/test_fg_availability.py` (test)
**Parallel?**: No
**Notes**: Circular reference can occur if Bundle A contains Bundle B which contains Bundle A.

---

### Subtask T004 – Add Depth Limiting

**Purpose**: Prevent stack overflow from deeply nested bundles (likely data error).

**Steps**:
1. Already implemented in T002 via `_depth` counter
2. Verify the logic:
   - Check `if _depth > MAX_FG_NESTING_DEPTH` BEFORE any processing
   - Constant `MAX_FG_NESTING_DEPTH = 10` at module level
   - Raise `MaxDepthExceededError` with current depth and max

3. Test case to verify (add in T005):
```python
def test_raises_for_deep_nesting(self, test_db, deeply_nested_bundle):
    """Deep nesting (>10 levels) raises MaxDepthExceededError."""
    with pytest.raises(MaxDepthExceededError) as exc_info:
        get_required_recipes(deeply_nested_bundle.id, test_db)
    assert exc_info.value.depth > MAX_FG_NESTING_DEPTH
```

**Files**: `src/services/event_service.py` (verification), `src/tests/test_fg_availability.py` (test)
**Parallel?**: No
**Notes**: 10 levels is consistent with existing codebase patterns.

---

### Subtask T005 – Write Unit Tests for Decomposition

**Purpose**: Comprehensive tests for `get_required_recipes()` covering all scenarios.

**Steps**:
1. Create `src/tests/test_fg_availability.py`:

```python
"""
Tests for FG availability and decomposition service methods (F070).

Tests cover:
- get_required_recipes (WP01)
- check_fg_availability, get_available_finished_goods, remove_invalid_fg_selections (WP02)
"""

import pytest
from src.services import event_service
from src.services.event_service import (
    get_required_recipes,
    CircularReferenceError,
    MaxDepthExceededError,
    MAX_FG_NESTING_DEPTH,
)
from src.services.exceptions import ValidationError


class TestGetRequiredRecipes:
    """Tests for get_required_recipes decomposition algorithm."""

    def test_returns_empty_set_for_fg_with_no_recipe_components(
        self, test_db, fg_no_recipe_components
    ):
        """FG with only packaging components returns empty set."""
        result = get_required_recipes(fg_no_recipe_components.id, test_db)
        assert result == set()

    def test_returns_single_recipe_for_atomic_fg(
        self, test_db, atomic_fg_with_recipe
    ):
        """Atomic FG (single FinishedUnit) returns its recipe ID."""
        result = get_required_recipes(atomic_fg_with_recipe.id, test_db)
        assert len(result) == 1
        # Verify it's the expected recipe
        assert atomic_fg_with_recipe.expected_recipe_id in result

    def test_returns_multiple_recipes_for_simple_bundle(
        self, test_db, simple_bundle
    ):
        """Bundle with multiple FUs returns all recipe IDs."""
        result = get_required_recipes(simple_bundle.id, test_db)
        assert result == simple_bundle.expected_recipe_ids

    def test_returns_all_recipes_for_nested_bundle(
        self, test_db, nested_bundle
    ):
        """Nested bundle (bundle containing bundle) recursively decomposes."""
        result = get_required_recipes(nested_bundle.id, test_db)
        assert result == nested_bundle.expected_recipe_ids

    def test_returns_unique_recipes_no_duplicates(
        self, test_db, bundle_with_duplicate_recipes
    ):
        """Duplicate recipe references are deduplicated."""
        result = get_required_recipes(bundle_with_duplicate_recipes.id, test_db)
        # Result is a set, so duplicates are naturally removed
        assert len(result) == len(bundle_with_duplicate_recipes.expected_unique_recipes)

    def test_raises_for_nonexistent_fg(self, test_db):
        """Raises ValidationError for non-existent FG."""
        with pytest.raises(ValidationError, match="FinishedGood .* not found"):
            get_required_recipes(99999, test_db)

    def test_raises_for_circular_reference(self, test_db, circular_bundle):
        """Circular references raise CircularReferenceError."""
        with pytest.raises(CircularReferenceError):
            get_required_recipes(circular_bundle.id, test_db)

    def test_raises_for_deep_nesting(self, test_db, deeply_nested_bundle):
        """Deep nesting (>10 levels) raises MaxDepthExceededError."""
        with pytest.raises(MaxDepthExceededError) as exc_info:
            get_required_recipes(deeply_nested_bundle.id, test_db)
        assert exc_info.value.max_depth == MAX_FG_NESTING_DEPTH


# ============================================================================
# Fixtures (WP01)
# ============================================================================


@pytest.fixture
def test_recipe(test_db):
    """Create a test recipe."""
    from src.models.recipe import Recipe
    recipe = Recipe(name="Test Recipe", category="Test")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def test_recipes(test_db):
    """Create multiple test recipes."""
    from src.models.recipe import Recipe
    recipes = []
    for i in range(5):
        recipe = Recipe(name=f"Test Recipe {i+1}", category="Test")
        test_db.add(recipe)
        recipes.append(recipe)
    test_db.flush()
    return recipes


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a FinishedUnit linked to a recipe."""
    from src.models.finished_unit import FinishedUnit
    fu = FinishedUnit(
        slug=f"test-fu-{test_recipe.id}",
        display_name="Test Finished Unit",
        recipe_id=test_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def fg_no_recipe_components(test_db):
    """FG with only packaging components (no recipes)."""
    from src.models.finished_good import FinishedGood
    fg = FinishedGood(
        slug="fg-no-recipes",
        display_name="FG No Recipes",
    )
    test_db.add(fg)
    test_db.flush()
    # Note: No compositions added - empty bundle
    return fg


@pytest.fixture
def atomic_fg_with_recipe(test_db, test_finished_unit):
    """FG with single FinishedUnit component."""
    from src.models.finished_good import FinishedGood
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="atomic-fg",
        display_name="Atomic FG",
    )
    test_db.add(fg)
    test_db.flush()

    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=test_finished_unit.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()

    # Store expected recipe for assertion
    fg.expected_recipe_id = test_finished_unit.recipe_id
    return fg


@pytest.fixture
def simple_bundle(test_db, test_recipes):
    """Bundle with multiple FinishedUnit components."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="simple-bundle",
        display_name="Simple Bundle",
    )
    test_db.add(fg)
    test_db.flush()

    expected_recipe_ids = set()
    for i, recipe in enumerate(test_recipes[:3]):
        fu = FinishedUnit(
            slug=f"fu-{recipe.id}",
            display_name=f"FU {recipe.id}",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        expected_recipe_ids.add(recipe.id)

    test_db.flush()
    fg.expected_recipe_ids = expected_recipe_ids
    return fg


@pytest.fixture
def nested_bundle(test_db, test_recipes):
    """Nested bundle (bundle containing another bundle)."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    # Inner bundle with 2 recipes
    inner_fg = FinishedGood(
        slug="inner-bundle",
        display_name="Inner Bundle",
    )
    test_db.add(inner_fg)
    test_db.flush()

    expected_recipe_ids = set()
    for recipe in test_recipes[:2]:
        fu = FinishedUnit(
            slug=f"inner-fu-{recipe.id}",
            display_name=f"Inner FU {recipe.id}",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=inner_fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        expected_recipe_ids.add(recipe.id)

    # Outer bundle containing inner bundle + 1 more recipe
    outer_fg = FinishedGood(
        slug="outer-bundle",
        display_name="Outer Bundle",
    )
    test_db.add(outer_fg)
    test_db.flush()

    # Add inner bundle as component
    comp_inner = Composition(
        assembly_id=outer_fg.id,
        finished_good_id=inner_fg.id,
        component_quantity=1.0,
    )
    test_db.add(comp_inner)

    # Add one more FU directly
    extra_fu = FinishedUnit(
        slug=f"extra-fu-{test_recipes[2].id}",
        display_name="Extra FU",
        recipe_id=test_recipes[2].id,
    )
    test_db.add(extra_fu)
    test_db.flush()

    comp_extra = Composition(
        assembly_id=outer_fg.id,
        finished_unit_id=extra_fu.id,
        component_quantity=1.0,
    )
    test_db.add(comp_extra)
    expected_recipe_ids.add(test_recipes[2].id)

    test_db.flush()
    outer_fg.expected_recipe_ids = expected_recipe_ids
    return outer_fg


@pytest.fixture
def bundle_with_duplicate_recipes(test_db, test_recipe):
    """Bundle where multiple FUs use the same recipe."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="duplicate-recipe-bundle",
        display_name="Duplicate Recipe Bundle",
    )
    test_db.add(fg)
    test_db.flush()

    # Add two FUs with same recipe
    for i in range(2):
        fu = FinishedUnit(
            slug=f"dup-fu-{i}",
            display_name=f"Dup FU {i}",
            recipe_id=test_recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)

    test_db.flush()
    fg.expected_unique_recipes = {test_recipe.id}
    return fg


@pytest.fixture
def circular_bundle(test_db):
    """Bundle with circular reference (A contains B, B contains A)."""
    from src.models.finished_good import FinishedGood
    from src.models.composition import Composition

    # Create two bundles
    fg_a = FinishedGood(slug="circular-a", display_name="Circular A")
    fg_b = FinishedGood(slug="circular-b", display_name="Circular B")
    test_db.add(fg_a)
    test_db.add(fg_b)
    test_db.flush()

    # A contains B
    comp_a = Composition(
        assembly_id=fg_a.id,
        finished_good_id=fg_b.id,
        component_quantity=1.0,
    )
    test_db.add(comp_a)

    # B contains A (creates cycle)
    comp_b = Composition(
        assembly_id=fg_b.id,
        finished_good_id=fg_a.id,
        component_quantity=1.0,
    )
    test_db.add(comp_b)
    test_db.flush()

    return fg_a


@pytest.fixture
def deeply_nested_bundle(test_db, test_recipe):
    """Bundle nested 12 levels deep (exceeds max 10)."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    # Create leaf FU
    leaf_fu = FinishedUnit(
        slug="deep-leaf-fu",
        display_name="Deep Leaf FU",
        recipe_id=test_recipe.id,
    )
    test_db.add(leaf_fu)
    test_db.flush()

    # Create 12 levels of nesting
    prev_fg = None
    for level in range(12):
        fg = FinishedGood(
            slug=f"deep-level-{level}",
            display_name=f"Deep Level {level}",
        )
        test_db.add(fg)
        test_db.flush()

        if prev_fg is None:
            # First level contains the leaf FU
            comp = Composition(
                assembly_id=fg.id,
                finished_unit_id=leaf_fu.id,
                component_quantity=1.0,
            )
        else:
            # Subsequent levels contain previous bundle
            comp = Composition(
                assembly_id=fg.id,
                finished_good_id=prev_fg.id,
                component_quantity=1.0,
            )
        test_db.add(comp)
        prev_fg = fg

    test_db.flush()
    return prev_fg  # Return outermost bundle
```

**Files**: `src/tests/test_fg_availability.py` (NEW)
**Parallel?**: No (write after T001-T004)
**Notes**:
- Tests use existing `test_db` fixture from conftest.py
- Each fixture creates isolated test data
- Fixtures attach expected values for assertion

---

## Test Strategy

**Run tests**:
```bash
./run-tests.sh src/tests/test_fg_availability.py -v -k "TestGetRequiredRecipes"
```

**Expected results**: 8 tests pass

**Fixtures needed**:
- `test_db` - existing from conftest.py
- New fixtures for FG/FU/Composition combinations

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular reference crash | Detect with `_visited` set before recursing |
| Deep nesting stack overflow | Limit to 10 levels with `_depth` counter |
| Session detachment | Accept `session` parameter, don't create internal sessions |
| Model import errors | Import `FinishedGood` from correct module |

---

## Definition of Done Checklist

- [ ] T001: Exception classes created in event_service.py
- [ ] T002: `get_required_recipes()` function implemented
- [ ] T003: Circular reference detection verified
- [ ] T004: Depth limiting verified
- [ ] T005: All 8 unit tests pass
- [ ] Code follows existing patterns (see batch_calculation.py)
- [ ] No session management issues (session passed from caller)

---

## Review Guidance

**Key acceptance checkpoints**:
1. Verify exception classes have descriptive messages with fg_id/path info
2. Verify recursion correctly handles `finished_unit_component` vs `finished_good_component`
3. Verify `_visited` set is mutable across recursive calls (not copied)
4. Verify tests cover all edge cases (empty, atomic, simple, nested, circular, deep)
5. Run full test suite to ensure no regressions

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Initial entry**:
- 2026-01-26T19:45:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-27T01:04:20Z – claude – shell_pid=26262 – lane=doing – Started implementation via workflow command
- 2026-01-27T01:14:56Z – claude – shell_pid=26262 – lane=for_review – Ready for review: Bundle decomposition algorithm with circular reference detection, depth limiting, and 8 passing tests
- 2026-01-27T01:15:49Z – claude – shell_pid=28478 – lane=doing – Started review via workflow command
- 2026-01-27T01:16:21Z – claude – shell_pid=28478 – lane=done – Review passed: All 8 tests pass. Exception classes have descriptive messages. Recursion correctly handles FU vs FG components. Session management follows project patterns. Code matches WP01 requirements exactly.
