# TD001: Consolidate Duplicate Slug Generation Functions

**Created**: 2026-01-28
**Priority**: Low
**Effort**: Small
**Area**: src/utils/slug_utils.py

---

## Summary

`src/utils/slug_utils.py` contains two nearly identical slug generation functions that should be consolidated into one.

## Current State

```python
# Ingredient-specific (original, ~60 lines)
def create_slug(name: str, session: Optional[Session] = None) -> str:
    # ... slug generation logic ...
    from ..models import Ingredient  # Hardcoded import
    existing = session.query(Ingredient).filter_by(slug=slug).first()

# General-purpose (added later, ~60 lines)
def create_slug_for_model(name: str, model_class: type, session: Optional[Session] = None) -> str:
    # ... identical slug generation logic ...
    existing = session.query(model_class).filter(model_class.slug == slug).first()
```

**Duplication**: The slug generation algorithm (Unicode normalization, ASCII transliteration, underscore handling, etc.) is duplicated in both functions. Only the uniqueness check differs.

## Root Cause

Ingredients were the first entity to need slugs, so `create_slug()` was written specifically for them. When other entities (Supplier, Recipe, etc.) needed slugs, `create_slug_for_model()` was created as a generalized version. The original function was kept for backward compatibility.

## Proposed Solution

Refactor `create_slug()` to delegate to `create_slug_for_model()`:

```python
def create_slug(name: str, session: Optional[Session] = None) -> str:
    """Generate URL-safe slug from ingredient name.

    Legacy function for Ingredient model. New code should use
    create_slug_for_model() directly.
    """
    from ..models import Ingredient
    return create_slug_for_model(name, Ingredient, session)
```

Optionally, deprecate `create_slug()` and update all callers to use `create_slug_for_model()` directly.

## Files to Modify

- `src/utils/slug_utils.py` - Refactor create_slug()
- Search for `create_slug(` imports and update if deprecating

## Acceptance Criteria

- [ ] Single implementation of slug generation algorithm
- [ ] All existing tests pass
- [ ] Backward compatibility maintained (or callers updated)

## Notes

This is a low-risk refactor but should be done carefully to avoid breaking ingredient slug generation. Consider adding a deprecation warning to `create_slug()` to encourage migration to the general-purpose function.
