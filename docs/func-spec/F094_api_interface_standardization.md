# F094: API Interface Standardization

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Enhancement

---

## Executive Summary

Current gaps:
- ❌ Inconsistent return types (objects, dicts, tuples, None)
- ❌ Mixed None vs exception patterns for "not found"
- ❌ No filter objects for complex queries
- ❌ Type hints incomplete

This spec standardizes all service interfaces with consistent return types, exception-based error handling, filter objects, and comprehensive type hints.

---

## Problem Statement

**Current State (INCONSISTENT):**
```
Service Return Types
├─ ❌ Some return ORM objects
├─ ❌ Some return dictionaries
├─ ❌ Some return tuples (bool, list)
├─ ❌ Some return None for not found
└─ ❌ No consistent pattern

Query Interfaces
├─ ❌ Many keyword arguments
├─ ❌ No filter objects
├─ ❌ Inconsistent search patterns
└─ ❌ Type hints incomplete
```

**Target State (STANDARDIZED):**
```
Service Return Types
├─ ✅ Always return ORM objects or PaginatedResult
├─ ✅ Never return None (raise exception)
├─ ✅ Never return tuples for validation
├─ ✅ Consistent across all services
└─ ✅ Type-safe with complete hints

Query Interfaces
├─ ✅ Filter objects for complex queries
├─ ✅ Consistent parameter patterns
├─ ✅ Standard search interfaces
└─ ✅ Complete type hints
```

---

## CRITICAL: Study These Files FIRST

1. **Service Return Patterns**
   - Find services returning None
   - Find services returning tuples
   - Find services returning dicts
   - Note inconsistencies

2. **Query Patterns**
   - Find functions with many kwargs
   - Study search implementations
   - Note filter patterns

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.D**: API Consistency & Contracts
  - Method signatures
  - Null/Optional handling
  - Collection operations

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Standardize Exception vs None Pattern

**What it must do:**
- Update all `get_*` functions to raise exception for not found
- Replace `return None` with `raise EntityNotFound`
- Create missing exception types
- Update calling code

**Pattern reference:** Study existing exception-based get functions, apply consistently

**Exception pattern:**
```python
def get_item(slug: str) -> Item:  # Never Optional[Item]
    item = query.first()
    if not item:
        raise ItemNotFoundBySlug(slug)
    return item
```

**Success criteria:**
- [ ] No `get_*` functions return None
- [ ] All raise specific exception for not found
- [ ] Type hints don't use Optional for required entities
- [ ] Calling code updated

---

### FR-2: Eliminate Tuple Return Types

**What it must do:**
- Replace validation functions returning (bool, list)
- Use exceptions for validation errors
- Remove tuple unpacking in calling code
- Standardize validation pattern

**Pattern reference:** Study ValidationError exception, apply consistently

**Success criteria:**
- [ ] No functions return (bool, list) tuples
- [ ] Validation uses exceptions
- [ ] Calling code simplified
- [ ] Pattern documented

---

### FR-3: Create Filter Objects

**What it must do:**
- Create filter dataclasses for complex queries
- Replace many keyword arguments with filter object
- Support optional filter fields
- Enable composable filters

**Pattern reference:** Study dataclass patterns, create filter objects

**Filter pattern:**
```python
@dataclass
class IngredientFilter:
    category: Optional[str] = None
    search_query: Optional[str] = None
    has_density: Optional[bool] = None
```

**Success criteria:**
- [ ] Filter objects exist for complex queries (~15 filters)
- [ ] Functions accept filter parameter
- [ ] Filter composition supported
- [ ] Type-safe filter fields

---

### FR-4: Complete Type Hints

**What it must do:**
- Add type hints to all public service functions
- Include parameter and return type hints
- Use proper generic types (List[T], Optional[T])
- Verify with mypy

**Pattern reference:** Study Python typing module, apply comprehensively

**Success criteria:**
- [ ] All service functions have complete type hints
- [ ] Parameters typed
- [ ] Return types typed
- [ ] Mypy passes without errors

---

### FR-5: Standardize Method Signatures

**What it must do:**
- Establish standard parameter order
- Consistent naming (filter, pagination, session)
- Required vs optional parameters
- Docstring standards

**Pattern reference:** Study best service functions, apply pattern consistently

**Standard order:**
```python
def operation(
    primary_param: Type,
    filter: Optional[FilterClass] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> ReturnType:
```

**Success criteria:**
- [ ] Parameter order consistent
- [ ] Naming standardized
- [ ] Docstrings complete
- [ ] Pattern documented

---

## Out of Scope

- ❌ Pydantic schemas - F107 (separate validation framework)
- ❌ DTO layer - defer
- ❌ Service versioning - YAGNI
- ❌ GraphQL support - out of scope

---

## Success Criteria

**Complete when:**

### Exception Pattern
- [ ] No functions return None for not found
- [ ] All raise specific exceptions
- [ ] Type hints use non-Optional
- [ ] Pattern consistent

### Return Types
- [ ] No tuple returns for validation
- [ ] Consistent ORM object or PaginatedResult
- [ ] No dictionary returns for structured data
- [ ] Type-safe returns

### Filter Objects
- [ ] Filter dataclasses created
- [ ] Complex queries use filters
- [ ] Type-safe filter fields
- [ ] Composable patterns

### Type Hints
- [ ] All functions have complete type hints
- [ ] Generic types used correctly
- [ ] Mypy validation passes
- [ ] IDE autocomplete works

### Quality
- [ ] Follows Code Quality Principle VI.D
- [ ] API predictable and consistent
- [ ] Web-ready interfaces
- [ ] Pattern documented

---

## Architecture Principles

### Exception-Based Error Handling

**Never return None for not found:**
- Raises specific exception (ItemNotFoundBySlug)
- Caller forced to handle error
- Type system enforces (non-Optional)

### Type Safety

**Complete type hints:**
- IDE autocomplete works
- Early error detection
- Self-documenting code

### Filter Objects

**Complex queries use dataclasses:**
- Type-safe fields
- Optional parameters
- Composable filters

---

## Constitutional Compliance

✅ **Principle VI.D: API Consistency & Contracts**
- Implements all method signature requirements
- Implements null/optional handling
- Implements collection operation patterns

✅ **Principle VI.A: Error Handling Standards**
- Exception-based errors
- No silent None returns

---

## Risk Considerations

**Risk: Breaking existing code**
- Many functions being changed
- Mitigation: Phased rollout
- Mitigation: Comprehensive testing

**Risk: Incomplete type hints**
- Complex types challenging
- Mitigation: Use mypy validation
- Mitigation: Gradual improvement

---

## Notes for Implementation

**Pattern Discovery:**
- Study all service functions → identify inconsistencies
- Study type hints → complete missing types
- Study query patterns → create filter objects

**Focus Areas:**
- Consistency is the primary goal
- Type safety enables better tooling
- Filter objects simplify complex queries
- Web API depends on consistent interfaces

---

**END OF SPECIFICATION**
