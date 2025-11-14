---
description: Quick fixes for common linting and formatting issues
---

# Quick Fix

Automatically fix common code quality issues in the Seasonal Baking Tracker project.

## User Input

```text
$ARGUMENTS
```

If files are specified, fix those. Otherwise, fix issues in currently open files or recent changes.

## Quick Fix Actions

### 1. Auto-Format with Black
```bash
dev format
```
This automatically fixes:
- Line length issues
- Indentation
- Spacing around operators
- Import formatting

### 2. Auto-Fix Common Flake8 Issues
- Remove unused imports
- Remove trailing whitespace
- Add missing blank lines
- Fix import order

### 3. Add Missing Type Hints
For functions without type hints, infer and add appropriate types:
```python
# BEFORE
def calculate_cost(price, quantity):
    return price * quantity

# AFTER
def calculate_cost(price: float, quantity: int) -> float:
    return price * quantity
```

### 4. Add Missing Docstrings
For public functions/classes without docstrings:
```python
# BEFORE
def convert_units(value, from_unit, to_unit):
    # ... implementation

# AFTER
def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value from one unit to another.

    Args:
        value: Numeric value to convert
        from_unit: Source unit (e.g., 'cups', 'grams')
        to_unit: Target unit

    Returns:
        Converted value in target unit
    """
    # ... implementation
```

## Fix Priority (from fastest to slowest)

1. **Formatting** (seconds): Run `dev format`
2. **Import cleanup** (seconds): Remove unused, sort imports
3. **Type hints** (minutes): Add where obviously missing
4. **Docstrings** (minutes): Add for public API
5. **Logic fixes** (varies): Requires understanding

## Execution

### Step 1: Run Auto-Formatters
```bash
dev format
```

### Step 2: Check Results
```bash
dev lint
```

### Step 3: Manual Fixes
For remaining issues that can't be auto-fixed:
- Add type hints manually
- Write docstrings
- Fix logic errors
- Resolve mypy errors

### Step 4: Verify
```bash
dev lint
dev test
```

## Output

Report what was fixed:

```markdown
# Quick Fix Results

## Auto-Fixed Issues
- Formatting: [X files formatted with Black]
- Imports: [Y unused imports removed]
- Spacing: [Z spacing issues fixed]

## Manual Fixes Applied
1. [File:Function] - Added type hints
2. [File:Class] - Added docstring
...

## Remaining Issues
[List any issues that need manual attention]

## Verification
- Linting: [PASS/FAIL]
- Tests: [PASS/FAIL]

## Files Modified
- [List of files]
```

## When to Use

Use `quick-fix` for:
- Pre-commit cleanup
- Fixing CI/CD lint failures
- Cleaning up after rapid prototyping
- Standardizing code formatting

Use `fix-issues` for:
- Complex bugs
- Test failures
- Logic errors
- Security issues

## Notes
- Always run `dev test` after fixes to ensure nothing broke
- Review auto-generated docstrings for accuracy
- Type hint inference may need manual adjustment
