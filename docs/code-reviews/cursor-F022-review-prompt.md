# Cursor Code Review Prompt - Feature 022: Unit Reference Table

## Role

You are a senior software engineer performing an independent code review of Feature 022 (unit-reference-table). This feature introduces a database-backed Unit reference table to replace hardcoded unit constants, and replaces free-form unit entry with dropdown selection in UI forms.

## Feature Summary

**Core Changes:**
1. New `Unit` SQLAlchemy model with 27 units across 4 categories (weight, volume, count, package)
2. New `unit_service.py` with query functions for dropdown population
3. Three UI forms updated to use dynamic dropdowns from the database instead of hardcoded constants

**Scope:**
- Model layer: New Unit model in `src/models/unit.py`
- Service layer: New `src/services/unit_service.py` + database seeding
- UI layer: Product form, Ingredient form, Recipe form dropdowns
- Test layer: New test files for Unit model and service
- Total: 812 tests pass

## Files to Review

### Model Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/models/unit.py` - New Unit model
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/models/__init__.py` - Unit export added

### Database Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/services/database.py` - `seed_units()` function added

### Service Layer (WP02)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/services/unit_service.py` - New service with query functions

### UI Layer (WP03, WP04, WP05)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/ui/ingredients_tab.py` - Product form package_unit dropdown (WP03)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/ui/forms/ingredient_form.py` - Density unit dropdowns (WP04)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/ui/forms/recipe_form.py` - Recipe ingredient unit dropdown (WP05)

### Test Layer
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/tests/test_unit_model.py` - 11 tests for Unit model
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/tests/test_unit_seeding.py` - 10 tests for seeding
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/tests/test_unit_service.py` - 28 tests for service

### Specification Documents
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/kitty-specs/022-unit-reference-table/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/kitty-specs/022-unit-reference-table/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/kitty-specs/022-unit-reference-table/data-model.md`

### Existing Constants (Reference - should still exist for backward compat)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table/src/utils/constants.py` - Original hardcoded units

## Review Checklist

### 1. Model Design (WP01)
- [ ] Unit model follows BaseModel pattern (id, uuid, created_at, updated_at)
- [ ] Fields: code (unique), display_name, symbol, category, un_cefact_code, sort_order
- [ ] Category values limited to: weight, volume, count, package
- [ ] Unit exported from `src/models/__init__.py`

### 2. Seeding (WP01)
- [ ] `seed_units()` function exists in database.py
- [ ] Called from `init_database()` after table creation
- [ ] Idempotent (checks if empty before inserting)
- [ ] Seeds exactly 27 units with correct category distribution:
  - Weight: 4 (oz, lb, g, kg)
  - Volume: 9 (tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal)
  - Count: 4 (each, count, piece, dozen)
  - Package: 10 (bag, box, bar, bottle, can, jar, packet, container, package, case)

### 3. Service Layer (WP02)
- [ ] `get_all_units()` returns all 27 units
- [ ] `get_units_by_category(category)` filters correctly
- [ ] `get_units_for_dropdown(categories)` returns list with category headers ("-- Weight --", etc.)
- [ ] All functions accept optional `session` parameter (session management pattern)
- [ ] Units ordered by sort_order within categories

### 4. UI Dropdowns (WP03, WP04, WP05)
- [ ] Product form: CTkComboBox with all 27 units + 4 headers (31 total items)
- [ ] Ingredient form density_volume_unit: Volume units only (9 units)
- [ ] Ingredient form density_weight_unit: Weight units only (4 units)
- [ ] Recipe ingredient form: Weight + Volume + Count units (17 units + 3 headers)
- [ ] All dropdowns use `state="readonly"` to prevent free-form entry
- [ ] Header selection prevented (callback reverts to last valid selection)
- [ ] Save validation rejects category headers

### 5. Test Coverage
- [ ] Unit model tests cover: creation, uniqueness, BaseModel inheritance
- [ ] Seeding tests cover: initial seed, idempotency, category counts
- [ ] Service tests cover: all query functions, session parameter handling

### 6. Session Management
- [ ] Service functions accept `session=None` parameter
- [ ] Session passed through when called from within transactions
- [ ] No nested `session_scope()` issues

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/022-unit-reference-table

# Verify unit counts
python3 -c "
from src.services.unit_service import get_all_units, get_units_by_category, get_units_for_dropdown
print(f'Total units: {len(get_all_units())}')
print(f'Weight: {len(get_units_by_category(\"weight\"))}')
print(f'Volume: {len(get_units_by_category(\"volume\"))}')
print(f'Count: {len(get_units_by_category(\"count\"))}')
print(f'Package: {len(get_units_by_category(\"package\"))}')
dropdown = get_units_for_dropdown(['weight', 'volume', 'count', 'package'])
print(f'Full dropdown: {len(dropdown)} items (27 units + 4 headers)')
"

# Run all tests
python3 -m pytest src/tests -v

# Run unit-specific tests
python3 -m pytest src/tests/test_unit_model.py src/tests/test_unit_seeding.py src/tests/test_unit_service.py -v

# Check for any remaining hardcoded unit references in UI that should use unit_service
grep -rn "CTkOptionMenu" src/ui/ --include="*.py"
grep -rn "WEIGHT_UNITS\|VOLUME_UNITS\|COUNT_UNITS\|PACKAGE_UNITS" src/ui/ --include="*.py"
```

## Key Implementation Patterns

### Header Selection Prevention Pattern
```python
def _on_unit_selected(self, selected_value: str):
    """Handle unit selection, preventing category headers."""
    if selected_value.startswith("--"):
        self.combo.set(self._last_valid_unit)
    else:
        self._last_valid_unit = selected_value
```

### Session Management Pattern
```python
def get_units_by_category(category: str, session: Optional[Session] = None) -> List[Unit]:
    def _impl(sess: Session) -> List[Unit]:
        return sess.query(Unit).filter(Unit.category == category).order_by(Unit.sort_order).all()

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F022-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 022 - Unit Reference Table

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 022-unit-reference-table
**Branch:** 022-unit-reference-table

## Summary

[Brief overview of findings]

## Verification Results

### Unit Count Validation
- Total units: [count] (expected 27)
- Weight: [count] (expected 4)
- Volume: [count] (expected 9)
- Count: [count] (expected 4)
- Package: [count] (expected 10)

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]
- Unit-specific tests: [PASS/FAIL]

### grep Validation
- CTkOptionMenu remaining: [count] (should be 0 for unit fields)
- Hardcoded unit constants in UI: [acceptable/needs work]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/unit.py | [status] | [notes] |
| src/services/unit_service.py | [status] | [notes] |
| src/services/database.py | [status] | [notes] |
| src/ui/ingredients_tab.py | [status] | [notes] |
| src/ui/forms/ingredient_form.py | [status] | [notes] |
| src/ui/forms/recipe_form.py | [status] | [notes] |
| src/tests/test_unit_model.py | [status] | [notes] |
| src/tests/test_unit_seeding.py | [status] | [notes] |
| src/tests/test_unit_service.py | [status] | [notes] |

## Architecture Assessment

### Session Management
[Assessment of session parameter handling across service functions]

### UI Consistency
[Assessment of dropdown implementation consistency across forms]

### Test Coverage
[Assessment of test coverage adequacy]

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI (CTkComboBox for dropdowns)
- pytest for testing (812 tests pass, 12 skipped as expected)
- The worktree is isolated from main branch
- Session management pattern: functions accept optional `session=None` parameter
- The original constants in `src/utils/constants.py` are preserved for backward compatibility
- This feature addresses User Stories from the spec:
  - US1: Select Unit from Dropdown When Adding Product
  - US2: Select Density Units When Defining Ingredient
  - US3: Select Unit When Adding Recipe Ingredient
  - US4: Reference Table Seeded on First Launch
