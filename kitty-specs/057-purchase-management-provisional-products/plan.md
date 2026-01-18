# Implementation Plan: Purchase Management with Provisional Products

**Branch**: `057-purchase-management-provisional-products` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/057-purchase-management-provisional-products/spec.md`

## Summary

Enable purchase recording regardless of product catalog state by introducing provisional product creation. When a user searches for a product during purchase entry and it doesn't exist, the form expands inline to allow creating a provisional product with prepopulated fields. Provisional products are flagged with `is_provisional=True` and appear in a review queue in the Products tab.

**Key Technical Approach:**
- Add `is_provisional: bool = False` field to Product model
- Extend product_service with `create_provisional_product()` method
- Enhance Add Purchase dialog with inline provisional product creation
- Add "Needs Review" filter and badge to Products tab
- Integrate with existing import services for JSON purchase import

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single desktop application
**Performance Goals**: Purchase recording < 2 minutes including provisional product creation
**Constraints**: Schema changes via reset/re-import (per constitution VI)
**Scale/Scope**: Single user, ~500 products, ~1000 purchases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|------|--------|----------|
| Does this design block web deployment? | ✅ PASS | Service layer is UI-independent; all business logic in services |
| Is the service layer UI-independent? | ✅ PASS | `product_service`, `purchase_service`, `inventory_item_service` have no UI imports |
| Does this support AI-assisted JSON import? | ✅ PASS | Core feature - provisional products auto-created during import |
| What's the web migration cost? | LOW | Services become API endpoints with minimal refactoring |
| Test-Driven Development (IV)? | ✅ PASS | Plan includes unit tests for all service methods |
| Layered Architecture (V)? | ✅ PASS | UI → Services → Models flow maintained |

**Phase-Specific Checks (Desktop Phase):**
- ✅ Service layer UI-independent
- ✅ Supports AI-assisted JSON import
- ✅ Web migration cost documented (LOW)

## Project Structure

### Documentation (this feature)

```
kitty-specs/057-purchase-management-provisional-products/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Codebase research findings
├── data-model.md        # Product model changes
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality validation
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── product.py              # Add is_provisional field
├── services/
│   ├── product_service.py      # Add create_provisional_product()
│   ├── product_catalog_service.py  # Add get_provisional_products(), mark_reviewed()
│   ├── purchase_service.py     # Enhance to support provisional products
│   └── import_export_service.py    # Enhance for provisional product creation
├── ui/
│   ├── dialogs/
│   │   └── add_purchase_dialog.py  # Inline provisional product creation
│   └── tabs/
│       └── inventory_tab.py        # Products filter + badge (or products_tab.py)
└── tests/
    ├── services/
    │   ├── test_product_service.py     # Provisional product tests
    │   ├── test_purchase_service.py    # Integration tests
    │   └── test_import_export_service.py   # Import with provisional tests
    └── ui/
        └── test_add_purchase_dialog.py # UI behavior tests
```

**Structure Decision**: Single desktop application structure per existing codebase patterns. All new code integrates into existing `src/` hierarchy.

## Key Design Decisions

### 1. Provisional Product Field: `is_provisional`

**Decision**: Add `is_provisional: bool = False` to Product model

**Rationale**:
- Clearer semantics than `needs_review` - a provisional product is one created quickly during purchase entry
- Default `False` means existing products are unaffected
- Simple boolean enables filtering with `Product.is_provisional == True`

**Implementation**:
```python
# src/models/product.py
class Product(BaseModel):
    # ... existing fields ...
    is_provisional = Column(Boolean, default=False, nullable=False, index=True)
```

### 2. Inline Provisional Product Creation

**Decision**: Expand Add Purchase dialog inline when product not found

**Rationale**:
- No modal nesting or wizard complexity
- User stays in purchase context
- Fields prepopulated from search context reduces data entry

**UI Flow**:
1. User searches for product → not found
2. Form expands to show: "Create Provisional Product"
   - Brand (prepopulated from search if parseable)
   - Ingredient selector (cascading dropdown)
   - Package unit, quantity (required)
   - Other fields optional
3. User completes fields → provisional product created
4. Purchase form continues with new product selected

### 3. Review Queue Implementation

**Decision**: Filter + badge in existing Products tab

**Rationale**:
- No new tab required
- Badge draws attention to pending reviews
- Filter isolates provisional products for batch completion

**UI Components**:
- Badge: Show count next to Products tab label when provisional products exist
- Filter: Dropdown option "Needs Review" alongside existing filters
- Highlighting: Missing fields shown with visual indicator (border color, icon)

### 4. Import Service Integration

**Decision**: Extend existing import services to create provisional products for unknown items

**Rationale**:
- Reuses proven import infrastructure
- Consistent with BT Mobile JSON import workflow (constitution VII)
- No duplicate import logic

**Flow**:
1. Import service processes JSON purchase records
2. For each purchase, lookup product by UPC/slug
3. If not found, call `product_service.create_provisional_product()`
4. Continue with purchase recording
5. Return results including provisional products created

## Service Interface Changes

### product_service.py

**New Methods**:
```python
def create_provisional_product(
    ingredient_id: int,
    brand: str,
    package_unit: str,
    package_unit_quantity: float,
    product_name: Optional[str] = None,
    upc_code: Optional[str] = None,
    session: Optional[Session] = None
) -> Product:
    """Create a provisional product for immediate use during purchase entry.

    Sets is_provisional=True for later review/completion.
    Auto-generates display_name from available data.
    """
```

### product_catalog_service.py

**New Methods**:
```python
def get_provisional_products(
    session: Optional[Session] = None
) -> List[Dict]:
    """Return all products where is_provisional=True."""

def get_provisional_count(
    session: Optional[Session] = None
) -> int:
    """Return count of provisional products for badge display."""

def mark_product_reviewed(
    product_id: int,
    session: Optional[Session] = None
) -> Dict:
    """Clear is_provisional flag after user completes product details."""
```

### purchase_service.py

**Enhanced Methods**:
```python
def record_purchase(
    product_id: int,  # Can now be provisional product
    # ... existing params ...
) -> Purchase:
    """Record purchase - works with both regular and provisional products."""
```

No changes to method signature - provisional products are valid products.

## Testing Strategy

### Unit Tests (services/)

| Test File | Coverage Target | Key Scenarios |
|-----------|-----------------|---------------|
| test_product_service.py | >80% | create_provisional_product(), validation, slug generation |
| test_product_catalog_service.py | >80% | get_provisional_products(), mark_product_reviewed() |
| test_purchase_service.py | >80% | record_purchase with provisional product |
| test_import_export_service.py | >70% | Import with unknown products → provisional creation |

### Integration Tests

| Test Scenario | Components | Validation |
|--------------|------------|------------|
| Full provisional workflow | product_service + purchase_service + inventory_service | Purchase recorded, inventory created |
| Import with unknowns | import_service + product_service | Provisional products created, purchases linked |
| Review and complete | product_catalog_service | is_provisional cleared |

### UI Tests (manual or automated)

| Test Scenario | Expected Behavior |
|--------------|-------------------|
| Search product not found | Form expands with provisional fields |
| Create provisional product | Product created, purchase continues |
| Products tab badge | Shows count when provisional products exist |
| Needs Review filter | Shows only provisional products |
| Mark as reviewed | Product removed from review queue |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Schema change disrupts existing data | Use reset/re-import per constitution VI; test with production data backup |
| Provisional products accumulate | Badge draws attention; products remain usable |
| UI complexity in Add Purchase dialog | Keep inline expansion minimal; hide advanced fields initially |
| Import service changes affect existing imports | Add comprehensive tests; maintain backward compatibility |

## Dependencies

| Dependency | Status | Action Required |
|------------|--------|-----------------|
| Product model | Exists | Add is_provisional field |
| product_service | Exists | Add create_provisional_product() |
| product_catalog_service | Exists | Add get_provisional_products(), mark_product_reviewed() |
| purchase_service | Exists | Verify works with provisional products |
| inventory_item_service | Exists | No changes needed |
| supplier_service | Exists | No changes needed |
| Add Purchase dialog | Exists | Enhance with inline expansion |
| Products tab | Exists | Add filter and badge |
| Import service | Exists | Enhance for provisional product creation |

## Complexity Tracking

*No constitution violations requiring justification.*

This feature adds complexity through:
- New Product model field (minimal - single boolean)
- New service methods (moderate - follows existing patterns)
- UI enhancements (moderate - inline expansion vs modal)

All complexity serves the core user value: unblocking purchase workflow.
