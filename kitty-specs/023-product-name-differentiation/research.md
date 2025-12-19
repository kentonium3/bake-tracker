# Research: Product Name Differentiation

**Feature**: 023-product-name-differentiation
**Date**: 2025-12-19
**Status**: Complete

## Executive Summary

This feature adds a `product_name` field to the Product model to differentiate variants with identical packaging (e.g., "Lindt 70% Cacao" vs "Lindt 85% Cacao" both 3.5oz bars). The implementation is straightforward, following existing patterns in the codebase.

## Research Findings

### 1. Current Product Model Structure

**Decision**: Add `product_name` as VARCHAR(200), nullable, positioned after `brand` field

**Rationale**:
- Matches existing field length convention (brand is VARCHAR(200))
- Nullable allows backward compatibility with existing products
- Position after brand maintains logical field grouping

**Alternatives Considered**:
- Repurposing `notes` field for variant names - rejected: notes serves different purpose
- Adding variant as suffix to brand - rejected: conflates two distinct concepts

**Evidence**: `src/models/product.py:53` shows brand as `String(200), nullable=True`

### 2. Unique Constraint Strategy

**Decision**: Update constraint to `(ingredient_id, brand, product_name, package_size, package_unit)`

**Rationale**:
- Prevents true duplicates while allowing NULL product_name
- SQLite treats NULLs as distinct in unique constraints (acceptable per spec assumptions)
- Maintains data integrity without breaking existing records

**Alternatives Considered**:
- No unique constraint - rejected: allows unintentional duplicates
- COALESCE-based constraint - rejected: adds complexity, SQLite NULL behavior is acceptable

**Evidence**: No current unique constraint exists on Product model. Other models use `UniqueConstraint` pattern (see `src/models/recipe.py:375`).

### 3. Import/Export Handling

**Decision**: Add `product_name` as optional export field, extend lookup to include it

**Rationale**:
- Optional field maintains backward compatibility with old exports
- Import lookup needs three-part key: (ingredient_id, brand, product_name)
- Existing pattern in `src/services/import_export_service.py:2357-2363`

**Alternatives Considered**:
- Breaking change requiring product_name - rejected: violates backward compatibility

**Evidence**: Current import uses `(ingredient_id, brand)` lookup at line 2357-2360.

### 4. Display Name Format

**Decision**: "Brand ProductName Size" format (e.g., "Lindt 70% Cacao 3.5 oz")

**Rationale**:
- User clarification confirmed this format
- Maintains readability with product_name between brand and size
- Consistent with existing display pattern

**Alternatives Considered**:
- "Brand Size (ProductName)" - rejected by user
- "ProductName by Brand Size" - rejected by user

**Evidence**: User clarification session 2025-12-19 in spec.md.

### 5. UI Form Placement

**Decision**: Add "Product Name" field after "Brand" field, mark as optional

**Rationale**:
- Logical flow: Brand identifies manufacturer, Product Name identifies variant
- Matches form structure in `src/ui/ingredients_tab.py:1519-1525`
- Optional field reduces user burden for simple products

**Alternatives Considered**:
- Placing before brand - rejected: brand is primary identifier
- Making required - rejected: many products don't need variant distinction

**Evidence**: `ProductFormDialog` class at `src/ui/ingredients_tab.py:1448` shows current form structure.

### 6. Migration Approach

**Decision**: Export/reset/import cycle per Constitution VI

**Rationale**:
- Single-user desktop app with existing migration infrastructure
- Simpler and more reliable than Alembic migrations
- User confirmed existing migrations follow this pattern

**Alternatives Considered**:
- Alembic migration scripts - rejected: Constitution VI specifies export/reset/import for desktop phase

**Evidence**: Constitution section VI "Schema Change Strategy (Desktop Phase)".

## Files to Modify

| File | Changes Required |
|------|-----------------|
| `src/models/product.py` | Add `product_name` column, update `display_name` property, add unique constraint |
| `src/services/import_export_service.py` | Add `product_name` to export (lines ~1148), update import lookup (lines ~2357) |
| `src/ui/ingredients_tab.py` | Add Product Name field to `ProductFormDialog._create_form()` |
| `src/services/product_service.py` | Update create/update methods to accept product_name |

## Open Questions

None - all questions resolved during clarification phase.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing products fail unique constraint | Low | Low | NULL product_name is distinct from other NULLs in SQLite |
| Import of old data fails | Low | Medium | Import handles missing product_name by defaulting to NULL |
| User confusion about product_name usage | Low | Low | Help text explains when to use the field |
