---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "IngredientService Implementation"
phase: "Phase 2 - Service Implementation"
lane: "done"
assignee: "Claude Code"
agent: "Claude Code"
shell_pid: "4504"
history:
  - timestamp: "2025-11-09T03:08:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: "4504"
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-09T07:58:47Z"
    lane: "done"
    agent: "Claude Code"
    shell_pid: "4504"
    action: "Work package completed - all tasks implemented and integration tests passing"
---

# Work Package Prompt: WP02 – IngredientService Implementation

## Objectives & Success Criteria

Implement complete IngredientService with 7 functions for managing the ingredient catalog using TDD approach (tests first, then implementation).

**Success Criteria**:
- All 7 service functions pass unit tests with >70% coverage
- CRUD operations work end-to-end (create, read, update, delete)
- Slug generation auto-increments on conflicts
- Dependency checking prevents orphaned data
- All functions use session_scope() for transaction management

## Context & Constraints

**Supporting Specs**:
- `kitty-specs/002-service-layer-for/contracts/ingredient_service.md` - Complete API contract
- `kitty-specs/002-service-layer-for/data-model.md` - Ingredient entity definition
- `kitty-specs/002-service-layer-for/research.md` - Slug generation decision

**Dependencies**: WP01 must be complete (exceptions, session_scope, slug_utils, validators)

**TDD Approach**: Write pytest tests BEFORE implementation for each function.

## Subtasks & Detailed Guidance

### Function 1: create_ingredient()

**T006 - Write tests** (`src/tests/test_ingredient_service.py`):
```python
def test_create_ingredient_success():
    """Test successful ingredient creation with auto-generated slug."""
    data = {
        "name": "All-Purpose Flour",
        "category": "Flour",
        "recipe_unit": "cup",
        "density_g_per_ml": 0.507
    }
    ingredient = create_ingredient(data)
    assert ingredient.slug == "all_purpose_flour"
    assert ingredient.name == "All-Purpose Flour"

def test_create_ingredient_slug_conflict():
    """Test auto-increment when slug exists."""
    # Create first ingredient
    # Create second with same name
    # Assert second slug is "all_purpose_flour_1"

def test_create_ingredient_validation_error():
    """Test ValidationError for missing required fields."""
    with pytest.raises(ValidationError):
        create_ingredient({"name": "Flour"})  # Missing category, recipe_unit
```

**T007 - Implement** (`src/services/ingredient_service.py`):
```python
from typing import Dict, Any
from src.models import Ingredient
from src.services.database import session_scope
from src.services.exceptions import ValidationError, DatabaseError, SlugAlreadyExists
from src.utils.validators import validate_ingredient_data
from src.utils.slug_utils import create_slug

def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    """Create a new ingredient with auto-generated slug."""
    validate_ingredient_data(ingredient_data)

    with session_scope() as session:
        slug = create_slug(ingredient_data['name'], session)
        ingredient = Ingredient(
            slug=slug,
            name=ingredient_data['name'],
            category=ingredient_data['category'],
            recipe_unit=ingredient_data['recipe_unit'],
            density_g_per_ml=ingredient_data.get('density_g_per_ml'),
            foodon_id=ingredient_data.get('foodon_id'),
            fdc_id=ingredient_data.get('fdc_id'),
            gtin=ingredient_data.get('gtin'),
            allergens=ingredient_data.get('allergens')
        )
        session.add(ingredient)
        session.flush()  # Get ID before commit
        return ingredient
```

**Parallel**: T006 can start immediately after WP01.

---

### Function 2: get_ingredient()

**T008 - Write tests**:
- Test successful retrieval by slug
- Test `IngredientNotFoundBySlug` for non-existent slug

**T009 - Implement**:
```python
def get_ingredient(slug: str) -> Ingredient:
    """Retrieve ingredient by slug."""
    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)
        return ingredient
```

---

### Function 3: search_ingredients()

**T010 - Write tests**:
- Test partial name search (case-insensitive)
- Test category filter
- Test combined query + category filter
- Test limit enforcement

**T011 - Implement**:
```python
from typing import Optional, List

def search_ingredients(
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Ingredient]:
    """Search ingredients by partial name and/or category."""
    with session_scope() as session:
        q = session.query(Ingredient)

        if query:
            q = q.filter(Ingredient.name.ilike(f'%{query}%'))
        if category:
            q = q.filter(Ingredient.category == category)

        return q.order_by(Ingredient.name).limit(limit).all()
```

---

### Function 4: update_ingredient()

**T012 - Write tests**:
- Test successful partial update
- Test `IngredientNotFoundBySlug` for invalid slug
- Test `ValidationError` for slug change attempt
- Test validation of updated fields

**T013 - Implement**:
```python
def update_ingredient(slug: str, ingredient_data: Dict[str, Any]) -> Ingredient:
    """Update ingredient attributes (slug cannot be changed)."""
    if 'slug' in ingredient_data:
        raise ValidationError("Slug cannot be changed after creation")

    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        for key, value in ingredient_data.items():
            if hasattr(ingredient, key):
                setattr(ingredient, key, value)

        return ingredient
```

---

### Function 5: delete_ingredient()

**T014 - Write tests**:
- Test successful deletion (no dependencies)
- Test `IngredientNotFoundBySlug` for invalid slug
- Test `IngredientInUse` when dependencies exist
- Test deletion with mocked dependencies

**T015 - Implement**:
```python
def delete_ingredient(slug: str) -> bool:
    """Delete ingredient if not referenced by other entities."""
    deps = check_ingredient_dependencies(slug)

    if any(deps.values()):
        details = ', '.join(f"{count} {entity}" for entity, count in deps.items() if count > 0)
        raise IngredientInUse(f"Cannot delete {slug}: used in {details}")

    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        session.delete(ingredient)
        return True
```

---

### Function 6: check_ingredient_dependencies()

**T016 - Write tests**:
- Test zero dependencies
- Test counts for recipes, variants, pantry_items, unit_conversions
- Test `IngredientNotFoundBySlug` for invalid slug

**T017 - Implement**:
```python
def check_ingredient_dependencies(slug: str) -> Dict[str, int]:
    """Check if ingredient is referenced by other entities."""
    from src.models import Variant, PantryItem, UnitConversion  # Avoid circular imports

    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        # Use COUNT queries for performance
        variants_count = session.query(Variant).filter_by(ingredient_slug=slug).count()
        # recipes_count = session.query(Recipe).join(RecipeIngredient).filter_by(ingredient_slug=slug).count()
        # pantry_count = session.query(PantryItem).join(Variant).filter_by(ingredient_slug=slug).count()
        # conversions_count = session.query(UnitConversion).filter_by(ingredient_slug=slug).count()

        return {
            "recipes": 0,  # TODO: Implement when Recipe model exists
            "variants": variants_count,
            "pantry_items": 0,  # TODO: Implement
            "unit_conversions": 0  # TODO: Implement
        }
```

---

### Function 7: list_ingredients()

**T018 - Write tests**:
- Test listing all ingredients
- Test category filter
- Test sorting (name, category, created_at)
- Test pagination (limit, offset)

**T019 - Implement**:
```python
def list_ingredients(
    category: Optional[str] = None,
    sort_by: str = "name",
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Ingredient]:
    """List all ingredients with optional filtering and pagination."""
    with session_scope() as session:
        q = session.query(Ingredient)

        if category:
            q = q.filter(Ingredient.category == category)

        # Sorting
        if sort_by == "name":
            q = q.order_by(Ingredient.name)
        elif sort_by == "category":
            q = q.order_by(Ingredient.category, Ingredient.name)
        # Add more sort options as needed

        q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        return q.all()
```

## Test Strategy

**Test file**: `src/tests/test_ingredient_service.py`

**Fixtures** (create in `conftest.py`):
```python
@pytest.fixture
def db_session():
    """Provide test database session."""
    # Setup test DB
    yield session
    # Teardown

@pytest.fixture
def sample_ingredient_data():
    return {
        "name": "All-Purpose Flour",
        "category": "Flour",
        "recipe_unit": "cup",
        "density_g_per_ml": 0.507
    }
```

**Run tests**: `pytest src/tests/test_ingredient_service.py -v --cov=src/services/ingredient_service`

**Coverage target**: >70% (per spec.md SC-002)

## Definition of Done Checklist

- [x] All 14 subtasks completed (7 test tasks + 7 implementation tasks)
- [x] `src/services/ingredient_service.py` created with 7 functions
- [x] All functions have type hints and docstrings matching contract
- [x] All tests pass (`pytest src/tests/test_ingredient_service.py`)
- [x] Test coverage >70%
- [x] No circular import issues
- [x] All functions use session_scope() correctly
- [x] Dependency checking works (even if some counts are TODO)

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.

