---
work_package_id: "WP03"
subtasks:
  - "T007"
  - "T008"
  - "T009"
title: "Service Layer - Import/Export Updates"
phase: "Phase 2 - Service Changes"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Service Layer - Import/Export Updates

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Objective**: Add product_name to JSON export and import with backward compatibility for old export files.

**Success Criteria**:
- [ ] Export includes `product_name` field for each product
- [ ] Import reads `product_name` and stores it correctly
- [ ] Import of old JSON (without product_name) defaults to NULL
- [ ] Duplicate detection includes product_name in lookup

## Context & Constraints

**Spec Reference**: `kitty-specs/023-product-name-differentiation/spec.md` - FR-006, FR-007, FR-008
**Research Reference**: `kitty-specs/023-product-name-differentiation/research.md` - Section 3

**Key Files**:
- `src/services/import_export_service.py`
- Export logic: lines ~1137-1178
- Import logic: lines ~2345-2386

**Key Constraints**:
- Backward compatibility is mandatory (FR-008)
- Follow existing optional field patterns (see `brand`, `notes`, `upc_code`)
- Import lookup must be precise to avoid false duplicates

**Dependencies**: WP01 must be complete (Product model must have product_name column)

## Subtasks & Detailed Guidance

### Subtask T007 - Add product_name to Export

**Purpose**: Include product_name in JSON export for data portability.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Locate the product export section (around line 1137-1178)
3. Find where optional product fields are added (after `brand`):

```python
# Current pattern (around line 1147-1148):
if product.brand:
    product_data["brand"] = product.brand
```

4. Add product_name export following the same pattern:

```python
if product.brand:
    product_data["brand"] = product.brand
if product.product_name:
    product_data["product_name"] = product.product_name  # NEW
if product.package_size:
    product_data["package_size"] = product.package_size
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes [P] - can be done independently from T008-T009

**Notes**:
- Only export if not None (matches existing pattern)
- Position after brand, before package_size for logical grouping
- This creates v3.5 format (per data-model.md)

### Subtask T008 - Update Import Duplicate Check

**Purpose**: Include product_name in product lookup to correctly identify duplicates.

**Steps**:
1. Locate the product import section (around line 2345-2386)
2. Find the duplicate check query (around line 2357):

```python
# Current code:
if skip_duplicates:
    existing = session.query(Product).filter_by(
        ingredient_id=ingredient.id,
        brand=brand,
    ).first()
```

3. Extend the filter to include product_name:

```python
if skip_duplicates:
    product_name = prod_data.get("product_name")  # May be None
    existing = session.query(Product).filter_by(
        ingredient_id=ingredient.id,
        brand=brand,
        product_name=product_name,  # NEW - None matches NULL in DB
    ).first()
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - should be done with T009

**Notes**:
- SQLite filter_by with None correctly matches NULL values
- This prevents false duplicate detection when products differ only by product_name
- Keep brand lookup as well (it's still needed)

### Subtask T009 - Handle Backward Compatibility

**Purpose**: Ensure old export files without product_name import correctly.

**Steps**:
1. In the same import section, locate where Product is created (around line 2372):

```python
# Current code:
product = Product(
    ingredient_id=ingredient.id,
    brand=brand,
    package_size=prod_data.get("package_size"),
    # ...
)
```

2. Add product_name with default None:

```python
product = Product(
    ingredient_id=ingredient.id,
    brand=brand,
    product_name=prod_data.get("product_name"),  # NEW - defaults to None if missing
    package_size=prod_data.get("package_size"),
    # ...
)
```

3. Verify no explicit check is needed - `.get()` returns None if key missing

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - combined with T008

**Notes**:
- Python dict.get() returns None for missing keys - exactly what we want
- No transformation of old exports needed
- Model validator will normalize "" to None if somehow present

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Old exports fail to import | Low | Using .get() with None default |
| Duplicate detection misses matches | Medium | Filter includes product_name |
| Export format breaks consumers | Low | Only adding optional field |

## Definition of Done Checklist

- [ ] T007: Export includes product_name for products that have it
- [ ] T008: Import duplicate check includes product_name
- [ ] T009: Missing product_name defaults to None on import
- [ ] Round-trip test: export -> import preserves product_name
- [ ] Old format test: import without product_name succeeds

## Review Guidance

**Reviewers should verify**:
1. Export position is after brand (matching model field order)
2. Duplicate check filter includes all identifying fields
3. Product creation uses .get() for product_name (backward compat)
4. No required field errors for missing product_name

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
