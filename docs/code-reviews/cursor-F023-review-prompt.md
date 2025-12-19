# Cursor Code Review Prompt - Feature 023: Product Name Differentiation

## Role

You are a senior software engineer performing an independent code review of Feature 023 (product-name-differentiation). This feature adds a `product_name` column to the Product table to distinguish variants with identical packaging (e.g., "Lindt 70% Cacao" vs "Lindt 85% Cacao" both 3.5oz bars).

## Feature Summary

**Core Changes:**
1. New `product_name` column (VARCHAR 200, nullable) on Product model
2. UniqueConstraint updated to include all 5 identifying fields
3. `display_name` property updated to format "Brand ProductName Size Type"
4. Empty string normalization via `@validates` decorator
5. Service layer `create_product()` and `update_product()` handle product_name
6. Import/export includes product_name with backward compatibility
7. UI ProductFormDialog has new optional Product Name field

**Scope:**
- Model layer: Product model column, constraint, property, validator
- Service layer: product_service.py create/update methods
- Service layer: import_export_service.py export/import handling
- UI layer: ProductFormDialog in ingredients_tab.py
- Migration: Export/reset/import cycle (manual, per Constitution VI)

## Files to Review

### Model Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/src/models/product.py` - Product model with new column, constraint, property, validator

### Service Layer (WP02)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/src/services/product_service.py` - `create_product()` and `update_product()` methods

### Import/Export Layer (WP03)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/src/services/import_export_service.py` - Export (~line 1149) and import (~line 2359) handling

### UI Layer (WP04)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/src/ui/ingredients_tab.py` - ProductFormDialog class (~line 1448)
  - `_create_form()` (~line 1499) - new field
  - `_populate_form()` (~line 1648) - load existing value
  - `_save()` (~line 1675) - validation and result dict

### Specification Documents
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/kitty-specs/023-product-name-differentiation/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/kitty-specs/023-product-name-differentiation/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/kitty-specs/023-product-name-differentiation/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/kitty-specs/023-product-name-differentiation/research.md`

### Session Management Reference
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation/docs/design/session_management_remediation_spec.md`

## Review Checklist

### 1. Model Design (WP01)
- [ ] `product_name` column is VARCHAR(200), nullable
- [ ] Column position is after `brand`, before `package_size`
- [ ] UniqueConstraint includes exactly 5 fields in order: `ingredient_id`, `brand`, `product_name`, `package_size`, `package_unit`
- [ ] Constraint named `uq_product_variant`
- [ ] `@validates("product_name")` decorator normalizes empty string to None
- [ ] `display_name` property format: "Brand ProductName Size Type"
- [ ] Docstring updated to include `product_name` in Attributes

### 2. Service Layer - product_service (WP02)
- [ ] `create_product()` docstring documents `product_name` parameter
- [ ] `create_product()` normalizes empty string to None before creating Product
- [ ] `create_product()` passes `product_name` to Product constructor
- [ ] `update_product()` docstring documents `product_name` parameter
- [ ] `update_product()` normalizes empty string to None in product_data
- [ ] Existing callers unaffected (backward compatible via dict.get() returning None)

### 3. Import/Export Layer (WP03)
- [ ] Export: `product_name` included after `brand` (only if not None)
- [ ] Import: `product_name` extracted via `prod_data.get("product_name")` (returns None if missing)
- [ ] Import duplicate check: filter includes `product_name=product_name`
- [ ] Import Product creation: `product_name=product_name` in constructor
- [ ] Backward compatibility: Old exports without product_name import correctly with NULL

### 4. UI Layer - ProductFormDialog (WP04)
- [ ] Product Name field appears after Brand, before Purchase Quantity
- [ ] Label is "Product Name:" (no asterisk - optional field)
- [ ] Placeholder text: "e.g., 70% Cacao, Extra Virgin"
- [ ] `_populate_form()`: handles None with `or ""` for display
- [ ] `_save()`: strips whitespace, validates length <= 200 chars
- [ ] `_save()`: converts empty string to None in result dict
- [ ] `_save()`: result dict has product_name after brand
- [ ] Help text updated to explain Product Name usage

### 5. Functional Requirements Verification
- [ ] FR-001: product_name column exists (VARCHAR 200, nullable)
- [ ] FR-002: UniqueConstraint includes 5 fields
- [ ] FR-004: UI displays Product Name field
- [ ] FR-005: Field is optional (can be left blank)
- [ ] FR-006: Export includes product_name
- [ ] FR-007: Import stores product_name correctly
- [ ] FR-008: Old imports (no product_name) default to NULL
- [ ] FR-009: Empty strings normalized to NULL
- [ ] FR-010: Duplicate products blocked via UniqueConstraint

### 6. Session Management
- [ ] No new `session_scope()` calls that could cause nesting issues
- [ ] Existing service patterns preserved (dict-based product_data approach)

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/023-product-name-differentiation

# Verify model imports correctly
python3 -c "
from src.models.product import Product
print('Product model imports successfully')
print(f'product_name column exists: {hasattr(Product, \"product_name\")}')
"

# Verify service imports correctly
python3 -c "
from src.services import product_service
print('product_service imports successfully')
print(f'create_product exists: {hasattr(product_service, \"create_product\")}')
print(f'update_product exists: {hasattr(product_service, \"update_product\")}')
"

# Verify import/export service imports correctly
python3 -c "
from src.services import import_export_service
print('import_export_service imports successfully')
"

# Verify UI imports correctly
python3 -c "
from src.ui.ingredients_tab import ProductFormDialog
print('ProductFormDialog imports successfully')
"

# Run all tests
python3 -m pytest src/tests -v

# Check for any references to product_name in test files (should exist)
grep -rn "product_name" src/tests/ --include="*.py" | head -20

# Check display_name property implementation
grep -A 20 "def display_name" src/models/product.py

# Check validator implementation
grep -A 10 "@validates" src/models/product.py

# Check UniqueConstraint
grep -A 5 "UniqueConstraint" src/models/product.py
```

## Key Implementation Patterns

### Empty String Normalization Pattern (Model)
```python
@validates("product_name")
def _normalize_product_name(self, key, value):
    """Normalize empty strings to None for consistency with unique constraint."""
    if value == "":
        return None
    return value
```

### Display Name Format Pattern
```python
@property
def display_name(self) -> str:
    parts = []
    if self.brand:
        parts.append(self.brand)
    if self.product_name:
        parts.append(self.product_name)
    if self.package_size:
        parts.append(self.package_size)
    if self.package_type:
        parts.append(self.package_type)
    # ...
    return " ".join(parts)
```

### Service Empty String Normalization Pattern
```python
# In create_product():
product_name = product_data.get("product_name")
if product_name == "":
    product_name = None

# In update_product():
if "product_name" in product_data:
    if product_data["product_name"] == "":
        product_data["product_name"] = None
```

### UI None Handling Pattern
```python
# In _populate_form():
self.product_name_entry.insert(0, self.product.get("product_name", "") or "")

# In _save():
product_name = self.product_name_entry.get().strip()
result = {
    "brand": brand,
    "product_name": product_name if product_name else None,
    # ...
}
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F023-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 023 - Product Name Differentiation

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 023-product-name-differentiation
**Branch:** 023-product-name-differentiation

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- Product model: [PASS/FAIL]
- product_service: [PASS/FAIL]
- import_export_service: [PASS/FAIL]
- ProductFormDialog: [PASS/FAIL]

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]

### Code Pattern Validation
- UniqueConstraint fields: [list fields found]
- display_name format: [describe format]
- @validates decorator: [present/missing]
- Empty string normalization: [service layer - present/missing]

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
| src/models/product.py | [status] | [notes] |
| src/services/product_service.py | [status] | [notes] |
| src/services/import_export_service.py | [status] | [notes] |
| src/ui/ingredients_tab.py | [status] | [notes] |

## Architecture Assessment

### Data Integrity
[Assessment of UniqueConstraint and NULL handling]

### Backward Compatibility
[Assessment of import/export backward compatibility]

### UI Consistency
[Assessment of form field implementation]

### Session Management
[Assessment of service function patterns - no new session_scope issues]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: product_name column | [PASS/FAIL] | [evidence] |
| FR-002: UniqueConstraint 5 fields | [PASS/FAIL] | [evidence] |
| FR-004: UI Product Name field | [PASS/FAIL] | [evidence] |
| FR-005: Optional field | [PASS/FAIL] | [evidence] |
| FR-006: Export includes product_name | [PASS/FAIL] | [evidence] |
| FR-007: Import stores product_name | [PASS/FAIL] | [evidence] |
| FR-008: Old import backward compat | [PASS/FAIL] | [evidence] |
| FR-009: Empty string normalized | [PASS/FAIL] | [evidence] |
| FR-010: Duplicate blocking | [PASS/FAIL] | [evidence] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI (CTkEntry for text fields)
- pytest for testing
- The worktree is isolated from main branch
- Session management pattern: service functions use dict-based approach, not explicit parameters
- Constitution VI requires export/reset/import migration (no ALTER TABLE)
- SQLite unique constraint behavior: NULLs are considered distinct (two products with NULL product_name are allowed)
- This feature addresses FR-001 through FR-010 from the spec
- User clarification confirmed display_name format: "Brand ProductName Size"
