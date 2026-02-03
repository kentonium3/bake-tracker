# F094: Core API Standardization

**Version**: 2.0 (Revised - Core Standards Only)
**Priority**: HIGH
**Type**: Code Quality Enhancement
**Estimated Effort**: 3-5 days

---

## Executive Summary

**Status: Core standardization only - defer advanced patterns to web-prep/F004.**

Current gaps:
- ❌ Inconsistent None vs exception patterns (~40 functions)
- ❌ Tuple returns for validation (~15 functions)
- ❌ Type hints incomplete (~60 functions)
- ⏸️ No filter objects (deferred - not urgent for desktop)

This spec standardizes exception handling, eliminates anti-patterns, and completes type hints - all HIGH-value changes with immediate desktop benefits and no dependencies on parked features.

**What this includes:**
- ✅ FR-1: Exception vs None pattern (prevent bugs)
- ✅ FR-2: Eliminate tuple returns (simplify code)
- ✅ FR-3: Complete type hints (better tooling)

**What this does NOT include:**
- ❌ Filter objects (deferred to web-prep/F004 - depends on pagination)
- ❌ Method signature standardization (deferred to web-prep/F004)
- ❌ Comprehensive refactoring (incremental adoption)

**Note:** Advanced interface patterns moved to web-prep/F004 (parked until web migration).

---

## Problem Statement

**Current State (Inconsistent Patterns):**
```
Service Return Types
├─ ❌ Some return None for not found (caller must check)
├─ ❌ Some raise exceptions (caller must handle)
├─ ❌ Some return tuples (bool, list) for validation
├─ ✅ Most return ORM objects (good pattern)
└─ ❌ Type hints incomplete (~60 functions)

Impact
├─ 🐛 "Forgot to check None" bugs
├─ 🐛 Inconsistent error handling
├─ 🔧 Poor IDE autocomplete
└─ 📝 Code harder to understand
```

**Target State (Core Standards):**
```
Service Return Types
├─ ✅ Never return None (always raise exception for not found)
├─ ✅ Never return tuples (use exceptions for validation)
├─ ✅ Complete type hints (all functions)
├─ ✅ Consistent exception-based error handling
└─ ✅ Better IDE support and fewer bugs

Advanced Patterns (Deferred to web-prep/F004)
├─ ⏸️ Filter objects for complex queries
├─ ⏸️ Standardized method signatures
└─ ⏸️ Comprehensive interface patterns
```

---

## Why Core Standards Only (Not Advanced Patterns)

**High-value, zero dependencies:**
- ✅ Exception vs None: Prevents bugs **immediately**
- ✅ Eliminate tuples: Simplifies code **immediately**
- ✅ Complete type hints: Better IDE support **immediately**

**Defer advanced patterns:**
- ⏸️ Filter objects work best with pagination (web-prep/F003 - parked)
- ⏸️ Method signatures depend on pagination + filters
- ⏸️ Can adopt incrementally without big-bang refactor

**YAGNI principle:**
- Core patterns solve real desktop bugs
- Advanced patterns prepare for web (doesn't exist yet)
- Can implement advanced in 2-3 days when needed

---

## CRITICAL: Study These Files FIRST

**Before implementation, planning phase MUST review:**

1. **Functions Returning None (~40 functions)**
   - `src/services/ingredient_service.py` → `get_ingredient()`
   - `src/services/recipe_service.py` → `get_recipe()`
   - Pattern: `return session.query(...).first()` returns None
   - Need: Raise exception instead

2. **Tuple Return Patterns (~15 functions)**
   - `src/utils/validators.py` → validation functions
   - Pattern: `return (bool, List[str])`
   - Need: Raise `ValidationError` instead

3. **Missing Type Hints (~60 functions)**
   - Grep for `def.*\(` without type hints
   - Pattern: Parameters and returns untyped
   - Need: Add complete type hints

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.D.1**: Method Signatures
  - "Type hints for all public methods"
  - "Explicit over implicit"
- **Code Quality Principle VI.D.2**: Null/Optional Handling
  - "Consistent None-checking patterns"
  - Exception vs None (see revised principle)
- **Code Quality Principle VI.A.1**: Exception Hierarchy
  - Domain exceptions for not-found scenarios

From: `docs/design/code_quality_principles_revised.md` (v1.0) and architecture gap analysis

---

## Functional Requirements

### FR-1: Standardize Exception vs None Pattern

**What it must do:**
- Update all `get_*` functions to raise exception for not found (~40 functions)
- Replace `return None` with `raise EntityNotFoundByX(value)`
- Create missing exception types as needed
- Update calling code to handle exceptions

**Current anti-pattern:**
```python
# BAD: Returns None (caller must remember to check)
def get_ingredient(slug: str) -> Optional[Ingredient]:
    """Get ingredient by slug."""
    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        return ingredient  # Returns None if not found

# Calling code (easy to forget None check!)
ingredient = get_ingredient("flour")
print(ingredient.display_name)  # 🐛 AttributeError if None!
```

**Correct pattern:**
```python
# GOOD: Raises exception (caller forced to handle)
def get_ingredient(slug: str) -> Ingredient:  # No Optional!
    """
    Get ingredient by slug.

    Args:
        slug: Ingredient slug

    Returns:
        Ingredient object

    Raises:
        IngredientNotFoundBySlug: If ingredient doesn't exist
    """
    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)  # ✅ Explicit error
        return ingredient

# Calling code (must handle exception)
try:
    ingredient = get_ingredient("flour")
    print(ingredient.display_name)  # ✅ Safe - can't be None
except IngredientNotFoundBySlug as e:
    show_error(f"Ingredient '{e.slug}' not found")
```

**Implementation approach:**
1. Audit all `get_*` functions across service files (~40 functions)
2. Identify which return `Optional[T]` (should raise exception)
3. Create missing exception types (e.g., `RecipeNotFoundById`)
4. Update function to raise exception instead of returning None
5. Update type hint to remove `Optional`
6. Update all calling code to handle exception
7. Update tests to expect exceptions

**Success criteria:**
- [ ] No `get_*` functions return `None` for not found
- [ ] All raise specific exception (`EntityNotFoundByX`)
- [ ] Type hints use non-Optional return types
- [ ] All calling code updated (UI, other services)
- [ ] Tests updated to expect exceptions
- [ ] Pattern documented in CLAUDE.md

**Estimated effort:** 2 days (~40 functions, ~5 min each + calling code updates)

---

### FR-2: Eliminate Tuple Return Types

**What it must do:**
- Replace validation functions returning `(bool, List[str])` (~15 functions)
- Use `ValidationError` exceptions instead
- Remove tuple unpacking in calling code
- Document validation exception pattern

**Current anti-pattern:**
```python
# BAD: Tuple return (awkward, error-prone)
def validate_ingredient_data(data: dict) -> Tuple[bool, List[str]]:
    """Validate ingredient data."""
    errors = []
    if not data.get('display_name'):
        errors.append("Display name required")
    if not data.get('category'):
        errors.append("Category required")
    return len(errors) == 0, errors

# Calling code (tuple unpacking, awkward)
is_valid, errors = validate_ingredient_data(data)
if not is_valid:
    show_errors(errors)
else:
    create_ingredient(data)
```

**Correct pattern:**
```python
# GOOD: Exception-based (clear, type-safe)
def validate_ingredient_data(data: dict) -> None:
    """
    Validate ingredient data.

    Args:
        data: Ingredient data to validate

    Raises:
        ValidationError: If validation fails (includes error list)
    """
    errors = []
    if not data.get('display_name'):
        errors.append("Display name required")
    if not data.get('category'):
        errors.append("Category required")

    if errors:
        raise ValidationError(errors)

# Calling code (simpler, clearer)
try:
    validate_ingredient_data(data)
    create_ingredient(data)  # ✅ Only reached if valid
except ValidationError as e:
    show_errors(e.errors)
```

**Functions to update (~15):**
- `src/utils/validators.py` → Multiple validation functions
- Service-level validation functions
- Any function returning `(bool, List[str])` or similar tuples

**Implementation approach:**
1. Grep for functions returning `Tuple[bool,` pattern
2. Replace with exception-based validation
3. Update calling code to catch `ValidationError`
4. Remove tuple unpacking
5. Update tests

**Success criteria:**
- [ ] No functions return `(bool, List[str])` tuples
- [ ] Validation uses `ValidationError` exception
- [ ] Calling code simplified (no tuple unpacking)
- [ ] Pattern documented with examples
- [ ] Tests updated

**Estimated effort:** 1 day (~15 functions, simpler than FR-1)

---

### FR-3: Complete Type Hints

**What it must do:**
- Add type hints to all public service functions (~60 functions)
- Include both parameter and return type hints
- Use proper generic types (`List[T]`, `Optional[T]`, `Dict[K, V]`)
- Fix type hint errors revealed by mypy

**Current gaps:**
```python
# BAD: No type hints (poor IDE support)
def create_ingredient(ingredient_data, session=None):
    """Create ingredient."""
    # ... implementation

def get_all_recipes(category=None, name_search=None):
    """Get all recipes."""
    # ... implementation
```

**Correct pattern:**
```python
# GOOD: Complete type hints (excellent IDE support)
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

def create_ingredient(
    ingredient_data: Dict[str, Any],
    session: Optional[Session] = None
) -> Ingredient:
    """Create ingredient."""
    # ... implementation

def get_all_recipes(
    category: Optional[str] = None,
    name_search: Optional[str] = None
) -> List[Recipe]:
    """Get all recipes with optional filters."""
    # ... implementation
```

**Implementation approach:**
1. Run mypy on service files to identify missing hints
2. Add parameter type hints to all public functions
3. Add return type hints to all public functions
4. Use proper generic types (List, Dict, Optional)
5. Fix any type errors revealed by mypy
6. Verify IDE autocomplete works correctly

**Common type hint patterns:**
```python
# ORM objects
def get_item(id: int) -> Item: ...

# Lists of objects
def list_items() -> List[Item]: ...

# Optional parameters
def search(query: Optional[str] = None) -> List[Item]: ...

# Session parameter
def operation(..., session: Optional[Session] = None) -> Item: ...

# Dictionary data
def create_item(data: Dict[str, Any]) -> Item: ...

# Complex return (until PaginatedResult adopted)
def check_availability(...) -> Dict[str, Any]: ...
```

**Success criteria:**
- [ ] All service functions have complete type hints
- [ ] Parameters typed (including Optional where appropriate)
- [ ] Return types typed
- [ ] Generic types used correctly (List[T], Dict[K,V], Optional[T])
- [ ] Mypy validation passes on service files
- [ ] IDE autocomplete works (verify in practice)

**Estimated effort:** 2 days (~60 functions, ~5 min each + mypy fixes)

---

## Out of Scope

**Explicitly NOT included in this core standardization:**

- ❌ **Filter objects** — Deferred to web-prep/F004 (parked)
  - Best adopted with pagination (web-prep/F003 - parked)
  - Can create incrementally as needed
  - Not urgent for desktop (small datasets, many kwargs work fine)

- ❌ **Method signature standardization** — Deferred to web-prep/F004 (parked)
  - Depends on filter objects + pagination
  - Large refactoring effort (40+ functions)
  - Can document pattern without rollout

- ❌ **Pydantic schemas** — Separate future feature
  - Full validation framework (larger scope)
  - Web API concern (doesn't exist yet)
  - Can adopt when building FastAPI

- ❌ **DTO layer** — Not needed yet
  - Services return ORM objects (works for desktop)
  - Web API may want DTOs (future concern)

- ❌ **Service versioning** — YAGNI

- ❌ **GraphQL support** — Out of scope

---

## Success Criteria

**Complete when:**

### FR-1: Exception Pattern Standardized
- [ ] All ~40 `get_*` functions raise exceptions for not found
- [ ] No functions return `None` for not found
- [ ] Type hints use non-Optional return types
- [ ] All calling code updated (UI, services, tests)
- [ ] Pattern documented in CLAUDE.md

### FR-2: Tuple Returns Eliminated
- [ ] No functions return `(bool, List[str])` tuples
- [ ] Validation uses `ValidationError` exceptions
- [ ] Calling code simplified (no tuple unpacking)
- [ ] Pattern documented with examples
- [ ] Tests updated to expect exceptions

### FR-3: Type Hints Complete
- [ ] All ~60 service functions have complete type hints
- [ ] Parameters typed (including `Optional` where appropriate)
- [ ] Return types typed
- [ ] Generic types used correctly (`List[T]`, `Dict[K,V]`, `Optional[T]`)
- [ ] Mypy validation passes on service files
- [ ] IDE autocomplete verified working

### Quality Checks
- [ ] Follows Code Quality Principle VI.D (API Consistency)
- [ ] Follows Code Quality Principle VI.A (Error Handling)
- [ ] No regressions in desktop functionality
- [ ] Patterns documented for future work

---

## Architecture Principles

### Exception-Based Error Handling (FR-1)

**Never return None for not found:**
- Raises specific exception (`ItemNotFoundBySlug`)
- Caller forced to handle error explicitly
- Type system enforces (non-Optional return type)
- IDE can't compile call without exception handling

**Benefits:**
- ✅ Prevents "forgot to check None" bugs
- ✅ Forces explicit error handling at call site
- ✅ Type-safe (can't get AttributeError from None)
- ✅ Self-documenting (exception in signature)

### Eliminate Anti-Patterns (FR-2)

**Never return tuples for validation:**
- Tuple returns (`(bool, List[str])`) are awkward
- Exceptions are clearer and more Pythonic
- Simpler calling code (no unpacking)
- Better type safety

**Benefits:**
- ✅ Simpler calling code
- ✅ Consistent with exception-based pattern
- ✅ Better type safety
- ✅ More readable

### Complete Type Safety (FR-3)

**Type hints for all public functions:**
- IDE autocomplete works perfectly
- Early error detection (before runtime)
- Self-documenting code
- Enables refactoring with confidence

**Benefits:**
- ✅ Better developer experience (IDE support)
- ✅ Catches bugs at development time
- ✅ Code is self-documenting
- ✅ Refactoring is safer

---

## Constitutional Compliance

✅ **Principle VI.D.1: Method Signatures**
- "Type hints for all public methods" — FR-3 implements
- "Explicit over implicit" — FR-1 & FR-2 implement

✅ **Principle VI.D.2: Null/Optional Handling**
- "Consistent None-checking patterns" — FR-1 implements
- Exception vs None standardized

✅ **Principle VI.A.1: Exception Hierarchy**
- Domain exceptions for not-found scenarios — FR-1 implements
- Validation exceptions — FR-2 implements

---

## Risk Considerations

### Risk: Breaking Existing Code

**Problem:** ~40 functions changing return behavior (None → exception)

**Mitigation:**
- Phased rollout (service by service)
- Update all calling code in same commit
- Comprehensive testing before merge
- UI error handling already uses try/except (compatible)

### Risk: Incomplete Type Hints

**Problem:** Complex generic types may be challenging

**Mitigation:**
- Use mypy validation to catch errors
- Start with simple types, improve iteratively
- Document tricky patterns for future reference
- IDE helps generate correct types

### Risk: UI Error Handling Changes

**Problem:** UI may not handle new exceptions

**Mitigation:**
- Desktop UI already uses try/except with ServiceError
- New exceptions inherit from ServiceError (compatible)
- Centralized error handler (F089) makes UI updates easy
- Test UI thoroughly after changes

---

## Implementation Plan

### Phase 1: Exception Pattern (Day 1-2)
1. Audit all `get_*` functions (~40 functions)
2. Create missing exception types (e.g., `RecipeNotFoundById`)
3. Update functions to raise instead of return None
4. Update type hints to remove Optional
5. Update calling code (UI + services)
6. Update tests to expect exceptions

### Phase 2: Eliminate Tuples (Day 3)
1. Find all functions returning `(bool, List[str])` (~15 functions)
2. Replace with exception-based validation
3. Update calling code (remove tuple unpacking)
4. Update tests

### Phase 3: Complete Type Hints (Day 4-5)
1. Run mypy to identify missing hints (~60 functions)
2. Add parameter type hints
3. Add return type hints
4. Fix mypy errors
5. Verify IDE autocomplete works

### Phase 4: Documentation & Testing (Day 5)
1. Update CLAUDE.md with patterns
2. Document migration examples
3. Comprehensive testing
4. Code review

**Total: 3-5 days**

---

## Notes for Implementation

### Pattern Discovery (Planning Phase)

**Study these patterns:**
1. Exception-based get functions (already exist in some services)
2. ValidationError usage (already exists)
3. Type hint examples from well-typed functions

**Key files to review:**
- `src/services/exceptions.py` — Exception types
- `src/services/ingredient_service.py` — Example functions
- Well-typed functions — Copy type hint patterns

### Common Patterns to Apply

**Exception pattern:**
```python
def get_item(slug: str) -> Item:  # No Optional!
    item = session.query(Item).filter_by(slug=slug).first()
    if not item:
        raise ItemNotFoundBySlug(slug)
    return item
```

**Validation pattern:**
```python
def validate_data(data: Dict[str, Any]) -> None:
    errors = []
    # ... validation logic
    if errors:
        raise ValidationError(errors)
```

**Type hints pattern:**
```python
def function(
    param: ParamType,
    optional: Optional[Type] = None,
    session: Optional[Session] = None
) -> ReturnType:
```

### Focus Areas

1. **Consistency over perfection** — Some functions may be tricky, document and move on
2. **Update all call sites** — Incomplete updates cause bugs
3. **Test thoroughly** — Desktop UI must work after changes
4. **Document patterns** — Help future developers follow patterns

---

**END OF SPECIFICATION**
