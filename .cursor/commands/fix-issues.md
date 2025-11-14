---
description: Repair code issues, bugs, and quality problems
---

# Fix Code Issues

You are repairing code issues in the Seasonal Baking Tracker (`bake-tracker`) project.

## User Input

```text
$ARGUMENTS
```

The user may specify:
- Specific files to fix
- Types of issues (linting, type errors, bugs, security)
- Test failures to resolve
- Error messages or stack traces

## Fix Categories

### 1. Linting Issues
Run and fix issues from:
```bash
dev lint
```
This runs: flake8, black, and mypy

**Common fixes:**
- Line length violations (max 100)
- Import ordering
- Unused imports or variables
- Spacing and formatting

### 2. Type Errors
Fix mypy type checking errors:
- Add missing type hints
- Fix incorrect type annotations
- Handle Optional types properly
- Use proper generic types (List[str], Dict[str, int], etc.)

### 3. Runtime Errors
Fix bugs and exceptions:
- Handle edge cases
- Fix logic errors
- Add proper error handling
- Resolve null/None reference errors

### 4. Test Failures
Fix failing tests:
- Analyze test output
- Identify root cause
- Fix implementation or update tests if specs changed
- Verify fix with `dev test`

### 5. Security Issues
Address security vulnerabilities:
- Input validation
- SQL injection prevention (use SQLAlchemy properly)
- File path sanitization
- XSS prevention in UI

## Fix Process

### Step 1: Diagnose
1. **Run diagnostics**:
   ```bash
   dev lint    # Check code quality
   dev test    # Run test suite
   ```
2. **Analyze output**: Understand the error messages
3. **Identify root cause**: Don't just fix symptoms

### Step 2: Plan the Fix
1. **Determine scope**: What files need changes?
2. **Check dependencies**: Will this affect other code?
3. **Consider tests**: Do tests need updating?

### Step 3: Implement Fix
1. **Make minimal changes**: Fix the issue without unnecessary refactoring
2. **Follow standards**: Maintain PEP 8, type hints, docstrings
3. **Preserve functionality**: Don't break existing features

### Step 4: Verify
1. **Run linters**: `dev lint` should pass
2. **Run tests**: `dev test` should pass
3. **Manual testing**: If UI changes, test the interface
4. **Check related code**: Ensure no side effects

## Common Issue Patterns

### Pattern 1: Type Hint Missing
```python
# BEFORE (mypy error)
def calculate_total(items):
    return sum(items)

# AFTER (fixed)
def calculate_total(items: List[float]) -> float:
    """Calculate total of numeric items.

    Args:
        items: List of numeric values to sum

    Returns:
        Sum of all items
    """
    return sum(items)
```

### Pattern 2: Missing Error Handling
```python
# BEFORE (can crash)
def load_recipe(recipe_id):
    recipe = session.query(Recipe).get(recipe_id)
    return recipe.name

# AFTER (safe)
def load_recipe(recipe_id: int) -> Optional[str]:
    """Load recipe name by ID.

    Args:
        recipe_id: Recipe database ID

    Returns:
        Recipe name if found, None otherwise
    """
    recipe = session.query(Recipe).get(recipe_id)
    return recipe.name if recipe else None
```

### Pattern 3: Line Length Violation
```python
# BEFORE (too long)
def create_shopping_list(recipes, existing_inventory, planned_quantities, include_optional_items=False):

# AFTER (fixed)
def create_shopping_list(
    recipes: List[Recipe],
    existing_inventory: Dict[str, float],
    planned_quantities: Dict[int, int],
    include_optional_items: bool = False
) -> ShoppingList:
```

## Output Format

After fixing issues, provide:

```markdown
# Fix Report

## Issues Fixed
1. **[File:Line]**: [Brief description]
   - **Problem**: [What was wrong]
   - **Solution**: [What was changed]
   - **Impact**: [What this affects]

## Verification Results
- [ ] Linting: PASSED
- [ ] Type checking: PASSED
- [ ] Tests: PASSED
- [ ] Manual testing: [PASSED/NOT APPLICABLE]

## Files Modified
- [List of files changed with brief description of changes]

## Notes
[Any important information about the fixes]
```

## Important Reminders
- **Test after every fix**: Run `dev lint` and `dev test`
- **Maintain existing behavior**: Don't introduce breaking changes
- **Document complex fixes**: Add comments explaining non-obvious solutions
- **Update tests if needed**: If implementation changes, update tests accordingly
- **Commit atomically**: Each logical fix should be its own commit
