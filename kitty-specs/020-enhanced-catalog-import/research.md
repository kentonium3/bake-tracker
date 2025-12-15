# Research: Enhanced Catalog Import

**Feature**: 020-enhanced-catalog-import
**Date**: 2025-12-14
**Status**: Complete

## Research Summary

This document captures the research findings and architectural decisions for the Enhanced Catalog Import feature.

---

## Decision 1: Service Architecture Pattern

**Decision**: Module-level functions in `src/services/catalog_import_service.py`

**Rationale**: Matches existing `import_export_service.py` pattern. The codebase uses module-level functions for service logic, not class-based services.

**Alternatives Considered**:
- Class-based `CatalogImportService` (as proposed in original spec) - rejected for consistency with existing patterns
- Adding to existing `import_export_service.py` - rejected to maintain separation of concerns

---

## Decision 2: File Organization

**Decision**: Separate files for CLI and service logic
- `src/utils/import_catalog.py` - CLI entry point
- `src/services/catalog_import_service.py` - Business logic

**Rationale**: Matches existing pattern where `import_export_cli.py` exists separately from `import_export_service.py`. Maintains layered architecture (UI -> Services -> Models).

**Alternatives Considered**:
- Single file with both CLI and logic - rejected for separation of concerns
- Service in utils directory - rejected as services belong in services layer

---

## Decision 3: Validation Architecture

**Decision**: Inline validation within `catalog_import_service.py`

**Rationale**: Validation is catalog-import-specific. Simpler than creating separate validator module. FK validation logic can be extracted later if needed for unified import.

**Alternatives Considered**:
- Separate `src/utils/import_validators.py` - rejected as over-engineering for current scope
- Separate `src/services/validation_service.py` - rejected; validation is import-specific

---

## Decision 4: Result Reporting Pattern

**Decision**: Create `CatalogImportResult` class similar to existing `ImportResult`

**Rationale**: Existing `ImportResult` class provides proven pattern with:
- Per-entity tracking (`entity_counts` dict)
- Error/warning collection with structured format
- `get_summary()` method for user-friendly output
- `add_success()`, `add_skip()`, `add_error()` methods

**Implementation Notes**:
- Can potentially reuse `ImportResult` directly if interface matches
- Entity types: "ingredients", "products", "recipes"
- Track: added, skipped, failed counts per entity

---

## Decision 5: Import Mode Implementation

**Decision**: Enum-based mode selection with explicit behavior per entity

**Modes**:
| Mode | Ingredients | Products | Recipes |
|------|-------------|----------|---------|
| ADD_ONLY | Create new, skip existing | Create new, skip existing | Create new, skip existing |
| AUGMENT | Update null fields | Update null fields | NOT SUPPORTED (error) |

**Key Behaviors**:
- Unique keys: `slug` (Ingredient), `(ingredient_slug, brand)` (Product), `slug` (Recipe)
- AUGMENT on non-existent record: creates new record (additive)
- Recipe AUGMENT attempt: returns error, no processing

---

## Decision 6: Session Management

**Decision**: All service functions accept optional `session=None` parameter

**Rationale**: Per CLAUDE.md guidance, nested `session_scope()` calls cause SQLAlchemy objects to become detached. Functions must accept optional session for transactional composition.

**Pattern**:
```python
def import_ingredients(data: list[dict], mode: str = "add",
                       dry_run: bool = False, session=None) -> CatalogImportResult:
    if session is not None:
        return _import_ingredients_impl(data, mode, dry_run, session)
    with session_scope() as session:
        return _import_ingredients_impl(data, mode, dry_run, session)
```

---

## Decision 7: Dry-Run Implementation

**Decision**: Perform all validation and simulate operations, but skip `session.commit()`

**Implementation**:
1. Run full validation pass (FK checks, unique key checks)
2. Build result object with would-be outcomes
3. If dry_run=True: rollback session, return preview result
4. If dry_run=False: commit session, return actual result

**Notes**:
- Dry-run and actual run should produce identical result counts
- Use `session.rollback()` or `session.expire_all()` to discard dry-run changes

---

## Decision 8: Partial Success Behavior

**Decision**: Commit valid records, report failures with actionable messages

**Implementation**:
- Process records in order
- For each record: validate, then create/update if valid
- Invalid records: add to errors list, continue processing
- At end: commit all valid changes, return result with success/failure breakdown

**Error Message Format**:
```
{entity_type} '{identifier}' failed: {specific_error}. {suggested_fix}
```

Example:
```
Recipe 'vanilla-cake' failed: Missing ingredient 'organic_vanilla'.
Import the ingredient first or remove from recipe.
```

---

## Decision 9: Format Detection

**Decision**: Detect format by presence of `catalog_version` vs `version` field

**Logic**:
```python
if "catalog_version" in data:
    # Catalog import format v1.0
    return process_catalog_import(data)
elif "version" in data and data["version"].startswith("3."):
    # Unified import format v3.x - route to existing import_export_service
    raise CatalogImportError("This appears to be a unified import file. Use 'Import Data...' instead.")
else:
    raise CatalogImportError("Unrecognized file format. Expected 'catalog_version' field.")
```

---

## Existing Code Patterns

### ImportResult Class (from `import_export_service.py`)

```python
class ImportResult:
    def __init__(self):
        self.total_records = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.errors = []
        self.warnings = []
        self.entity_counts: Dict[str, Dict[str, int]] = {}

    def add_success(self, entity_type: str = None)
    def add_skip(self, record_type: str, record_name: str, reason: str)
    def add_error(self, record_type: str, record_name: str, error: str)
    def add_warning(self, record_type: str, record_name: str, message: str)
    def merge(self, other: "ImportResult")
    def get_summary(self) -> str
```

### Entity Unique Keys

| Entity | Unique Key | Field(s) |
|--------|------------|----------|
| Ingredient | `slug` | `slug` column |
| Product | Composite | `ingredient_id` + `brand` (need to lookup by slug) |
| Recipe | `name` | `name` column (note: spec says slug but model uses name) |

**Note**: Recipe model does not have a `slug` column. The spec refers to slug-based lookup, but the actual unique constraint is on `name`. Need to clarify: use `name` as unique key, or generate slug from name.

---

## Protected vs Augmentable Fields

### Ingredient

**Protected** (never modified):
- `slug`
- `display_name`

**Augmentable** (updated only if currently null):
- `density_volume_value`
- `density_volume_unit`
- `density_weight_value`
- `density_weight_unit`
- `foodon_id`
- `fdc_ids`
- `foodex2_code`
- `langual_terms`
- `allergens`
- `description`

### Product

**Protected**:
- `ingredient_id` (via ingredient_slug lookup)
- `brand`

**Augmentable**:
- `upc_code`
- `package_size`
- `package_type`
- `purchase_unit` (only if null)
- `purchase_quantity` (only if null)
- `preferred` (only if null/False - user decision during discovery)

### Recipe

**Protected**: ALL fields (AUGMENT not supported)

---

## Catalog File Format (v1.0)

```json
{
  "catalog_version": "1.0",
  "generated_at": "2025-12-14T10:30:00Z",
  "ingredients": [
    {
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category": "Flour",
      "description": null,
      "density_volume_value": 1.0,
      "density_volume_unit": "cup",
      "density_weight_value": 4.25,
      "density_weight_unit": "oz",
      "allergens": ["gluten"]
    }
  ],
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "5 lb",
      "purchase_unit": "bag",
      "purchase_quantity": 1.0,
      "upc_code": "071012000000"
    }
  ],
  "recipes": [
    {
      "name": "Chocolate Chip Cookies",
      "category": "Cookies",
      "yield_quantity": 48,
      "yield_unit": "cookies",
      "ingredients": [
        {"ingredient_slug": "all_purpose_flour", "quantity": 2.25, "unit": "cup"}
      ],
      "components": []
    }
  ]
}
```

---

## Dependencies Verified

1. **Existing import_export_service.py**: Provides `ImportResult` class and patterns
2. **Existing import_export_dialog.py**: Provides UI patterns for modal dialogs
3. **Session management**: CLAUDE.md documents `session=None` pattern
4. **Menu structure**: File menu exists with Import Data.../Export Data... items

---

## Open Items Resolved

| Item | Resolution |
|------|------------|
| `is_preferred` handling | Augmentable if null (per user decision) |
| Recipe slug collisions | Reject with detailed error (per user decision) |
| Partial success | Commit valid, report failures (per user decision) |
| Export separation | Unified only (per user decision) |
| Recipe unique key | Use `name` field (matches existing model) |
