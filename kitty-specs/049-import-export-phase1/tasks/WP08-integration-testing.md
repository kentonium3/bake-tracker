---
work_package_id: "WP08"
subtasks:
  - "T067"
  - "T068"
  - "T069"
  - "T070"
  - "T071"
  - "T072"
  - "T073"
  - "T074"
  - "T075"
title: "Integration Testing"
phase: "Phase 4 - Final"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Integration Testing

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create comprehensive integration tests validating all import/export workflows end-to-end.

**Success Criteria**:
- SC-002: Complete system state can be restored from backup (round-trip test passes)
- SC-009: Format auto-detection correctly identifies normalized vs context-rich in 100% of test cases
- Constitution Principle IV: >70% test coverage on new service code

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md`
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Constitution: `.kittify/memory/constitution.md` (Principle IV - TDD)

**Dependencies**: All previous WPs must be complete (WP01-WP07, WP09).

**Test Framework**: pytest

**Test Data Location**: `src/tests/fixtures/` or inline in tests

---

## Subtasks & Detailed Guidance

### Subtask T067 - Create integration test file

**Purpose**: New file for import/export integration tests.

**Steps**:
1. Create `src/tests/integration/test_import_export_roundtrip.py`:
```python
"""
Integration tests for import/export round-trip workflows.

These tests verify complete workflows across multiple services:
- Full backup → restore → verify
- Context-rich export → modify → import
- Transaction imports → verify inventory changes
"""

import json
import pytest
import tempfile
from pathlib import Path
from decimal import Decimal

from src.services.database import session_scope, reset_database
from src.services.coordinated_export_service import export_complete
from src.services.catalog_import_service import import_catalog
from src.services.transaction_import_service import import_purchases, import_adjustments
from src.services.enhanced_import_service import detect_format
from src.services.denormalized_export_service import export_ingredients_view
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.inventory_item import InventoryItem


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_database():
    """Set up database with sample data for testing."""
    # Create test data
    with session_scope() as session:
        # Add ingredients, products, etc.
        pass
    yield
    # Cleanup handled by test isolation
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py` (NEW)

### Subtask T068 - Test: full backup → reset → import → verify

**Purpose**: Validate complete backup/restore workflow.

**Steps**:
1. Create test:
```python
def test_full_backup_roundtrip(sample_database, temp_export_dir):
    """
    Test complete backup → reset → restore workflow.

    SC-002: Complete system state can be restored from backup.
    """
    # 1. Record initial counts
    initial_counts = {}
    with session_scope() as session:
        initial_counts["ingredients"] = session.query(Ingredient).count()
        initial_counts["products"] = session.query(Product).count()
        # ... all 16 entities

    # 2. Export full backup
    manifest = export_complete(str(temp_export_dir))
    assert len(manifest.files) == 16

    # 3. Reset database
    reset_database()

    # 4. Verify database is empty
    with session_scope() as session:
        assert session.query(Ingredient).count() == 0

    # 5. Import backup
    result = import_full_backup(str(temp_export_dir))
    assert result.failed == 0

    # 6. Verify counts match
    with session_scope() as session:
        assert session.query(Ingredient).count() == initial_counts["ingredients"]
        assert session.query(Product).count() == initial_counts["products"]
        # ... all 16 entities
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T069 - Test: context-rich export → modify → import → verify

**Purpose**: Validate AI augmentation workflow.

**Steps**:
1. Create test:
```python
def test_context_rich_roundtrip(sample_database, temp_export_dir):
    """
    Test context-rich export → modify editable → import workflow.

    Verifies editable fields updated, computed fields ignored.
    """
    # 1. Export context-rich ingredients
    export_path = temp_export_dir / "ingredients_view.json"
    export_ingredients_view(str(export_path))

    # 2. Load and modify editable field
    with open(export_path) as f:
        data = json.load(f)

    # Modify an editable field
    original_desc = data["records"][0]["description"]
    data["records"][0]["description"] = "AI-augmented description"

    # Modify a computed field (should be ignored)
    data["records"][0]["inventory_total"] = 99999

    with open(export_path, "w") as f:
        json.dump(data, f)

    # 3. Import modified file
    result = import_context_rich_view(str(export_path))
    assert result.failed == 0

    # 4. Verify editable field updated
    slug = data["records"][0]["slug"]
    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        assert ingredient.description == "AI-augmented description"

        # Verify computed field NOT updated (calculate fresh)
        actual_inventory = calculate_inventory_total(ingredient)
        assert actual_inventory != 99999  # Was ignored
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T070 - Test: purchase import → verify inventory

**Purpose**: Validate purchase transaction import.

**Steps**:
1. Create test:
```python
def test_purchase_import_increases_inventory(sample_database, temp_export_dir):
    """
    Test purchase import creates records and increases inventory.

    SC-006: Purchase import increases inventory quantities correctly.
    """
    # 1. Get initial inventory for test product
    with session_scope() as session:
        product = session.query(Product).first()
        product_slug = product.slug
        initial_qty = sum(
            i.current_quantity for i in
            session.query(InventoryItem).filter_by(product_id=product.id).all()
        )

    # 2. Create purchase JSON
    purchase_data = {
        "schema_version": "4.0",
        "import_type": "purchases",
        "purchases": [
            {
                "product_slug": product_slug,
                "purchased_at": "2026-01-12T10:00:00Z",
                "unit_price": 5.99,
                "quantity_purchased": 10
            }
        ]
    }

    purchase_path = temp_export_dir / "purchases.json"
    with open(purchase_path, "w") as f:
        json.dump(purchase_data, f)

    # 3. Import purchases
    result = import_purchases(str(purchase_path))
    assert result.failed == 0
    assert result.successful == 1

    # 4. Verify inventory increased
    with session_scope() as session:
        product = session.query(Product).filter_by(slug=product_slug).first()
        new_qty = sum(
            i.current_quantity for i in
            session.query(InventoryItem).filter_by(product_id=product.id).all()
        )
        assert new_qty == initial_qty + 10
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T071 - Test: adjustment import → verify inventory

**Purpose**: Validate adjustment transaction import.

**Steps**:
1. Create test:
```python
def test_adjustment_import_decreases_inventory(sample_database, temp_export_dir):
    """
    Test adjustment import decreases inventory correctly.

    SC-007: Inventory adjustment import decreases quantities correctly.
    """
    # 1. Ensure product has inventory
    with session_scope() as session:
        product = session.query(Product).first()
        product_slug = product.slug

        # Add inventory if needed
        inv_item = InventoryItem(product_id=product.id, current_quantity=20)
        session.add(inv_item)
        session.commit()

        initial_qty = 20

    # 2. Create adjustment JSON
    adjustment_data = {
        "schema_version": "4.0",
        "import_type": "adjustments",
        "adjustments": [
            {
                "product_slug": product_slug,
                "adjusted_at": "2026-01-12T10:00:00Z",
                "quantity": -5,
                "reason_code": "spoilage",
                "notes": "Found mold"
            }
        ]
    }

    adj_path = temp_export_dir / "adjustments.json"
    with open(adj_path, "w") as f:
        json.dump(adjustment_data, f)

    # 3. Import adjustments
    result = import_adjustments(str(adj_path))
    assert result.failed == 0

    # 4. Verify inventory decreased
    with session_scope() as session:
        product = session.query(Product).filter_by(slug=product_slug).first()
        new_qty = sum(
            i.current_quantity for i in
            session.query(InventoryItem).filter_by(product_id=product.id).all()
        )
        assert new_qty == initial_qty - 5
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T072 - Test: error handling and rollback

**Purpose**: Verify atomic transactions rollback on failure.

**Steps**:
1. Create test:
```python
def test_import_rollback_on_error(sample_database, temp_export_dir):
    """
    Test that failed imports don't leave partial data.

    All imports should be atomic - rollback on any failure.
    """
    # 1. Create JSON with one valid, one invalid purchase
    purchase_data = {
        "schema_version": "4.0",
        "import_type": "purchases",
        "purchases": [
            {
                "product_slug": "valid_product",
                "unit_price": 5.99,
                "quantity_purchased": 10
            },
            {
                "product_slug": "nonexistent_product_xyz",  # Will fail
                "unit_price": 3.99,
                "quantity_purchased": 5
            }
        ]
    }

    # Note: Depending on implementation, may process partial
    # Test should verify expected rollback behavior
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T073 - Test: format auto-detection accuracy

**Purpose**: Verify 100% detection accuracy.

**Steps**:
1. Create test:
```python
@pytest.mark.parametrize("filename,expected_format", [
    ("context_rich_ingredients.json", "context_rich"),
    ("normalized_backup.json", "normalized"),
    ("purchases.json", "purchases"),
    ("adjustments.json", "adjustments"),
])
def test_format_detection_accuracy(filename, expected_format, temp_export_dir):
    """
    Test format auto-detection accuracy.

    SC-009: Format auto-detection correctly identifies format 100% of time.
    """
    # Create test file with appropriate structure
    if expected_format == "context_rich":
        data = {"_meta": {"editable_fields": ["description"]}, "records": []}
    elif expected_format == "normalized":
        data = {"version": "4.0", "application": "bake-tracker"}
    elif expected_format == "purchases":
        data = {"import_type": "purchases", "purchases": []}
    else:
        data = {"import_type": "adjustments", "adjustments": []}

    file_path = temp_export_dir / filename
    with open(file_path, "w") as f:
        json.dump(data, f)

    detected, _ = detect_format(str(file_path))
    assert detected == expected_format
```

**Files**: `src/tests/integration/test_import_export_roundtrip.py`

### Subtask T074 - Verify >70% coverage on new service code

**Purpose**: Meet constitution TDD requirement.

**Steps**:
1. Run coverage report:
```bash
./run-tests.sh --cov=src/services --cov-report=term-missing
```
2. Verify coverage on:
   - coordinated_export_service.py (WP01 additions)
   - catalog_import_service.py (WP02 additions)
   - denormalized_export_service.py (WP03 additions)
   - transaction_import_service.py (WP04, WP05)
   - enhanced_import_service.py (WP06 additions)
3. Add tests for any uncovered paths

**Files**: Coverage report analysis

### Subtask T075 - Document test fixtures and data requirements

**Purpose**: Ensure tests are reproducible.

**Steps**:
1. Add docstrings to fixtures explaining:
   - What data they create
   - How to reset state
   - Dependencies between fixtures
2. Create sample JSON files in `src/tests/fixtures/import_export/`:
   - `sample_backup/` - Full backup with 16 entities
   - `sample_purchases.json`
   - `sample_adjustments.json`
   - `sample_context_rich.json`

**Files**: `src/tests/fixtures/import_export/` (NEW directory)

---

## Test Strategy

**Run All Integration Tests**:
```bash
./run-tests.sh src/tests/integration/test_import_export_roundtrip.py -v
```

**Run with Coverage**:
```bash
./run-tests.sh --cov=src/services --cov-report=html
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test isolation failures | Reset database in fixtures |
| Flaky tests | Use deterministic data |
| Coverage gaps | Review coverage report, add tests |

---

## Definition of Done Checklist

- [ ] Integration test file created
- [ ] Full backup round-trip test passes
- [ ] Context-rich round-trip test passes
- [ ] Purchase import test passes
- [ ] Adjustment import test passes
- [ ] Error rollback test passes
- [ ] Format detection 100% accurate
- [ ] >70% coverage on new service code
- [ ] Test fixtures documented

## Review Guidance

**Reviewers should verify**:
1. All integration tests pass
2. Coverage meets >70% threshold
3. Tests are not flaky
4. Fixtures properly isolated

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:38:17Z – claude – lane=doing – Starting integration testing - implementing tests for completed WPs while others are delegated
- 2026-01-12T22:20:00Z – claude – shell_pid=13882 – lane=done – Approved: 19 tests pass, 1 skipped (Recipe slug). Format detection 100% accurate. Context-rich roundtrip verified. Purchase/adjustment integration tests pass.
