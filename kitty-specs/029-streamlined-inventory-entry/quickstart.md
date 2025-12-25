# Quickstart: Feature 029 Development

**Feature**: Streamlined Inventory Entry
**Branch**: `029-streamlined-inventory-entry`

## Prerequisites

- Python 3.10+
- Virtual environment activated
- Dependencies installed (`pip install -r requirements.txt`)

## Getting Started

### 1. Activate the Feature Worktree

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/029-streamlined-inventory-entry
source venv/bin/activate
```

### 2. Verify Test Baseline

```bash
pytest src/tests -v --tb=short
```

All existing tests should pass before starting implementation.

### 3. Key Files to Create

| File | Purpose |
|------|---------|
| `src/ui/session_state.py` | SessionState singleton |
| `src/ui/widgets/type_ahead_combobox.py` | TypeAheadComboBox widget |
| `src/ui/widgets/dropdown_builders.py` | Recency-aware dropdown builders |
| `src/utils/category_defaults.py` | Category-to-unit mapping |

### 4. Key Files to Modify

| File | Changes |
|------|---------|
| `src/services/inventory_item_service.py` | Add recency query methods |
| `src/ui/dialogs/add_inventory_dialog.py` | Major refactor for new workflow |

### 5. Running the Application

```bash
python src/main.py
```

Navigate to Inventory tab and click "Add Inventory" to test the enhanced dialog.

## Development Order

Recommended implementation sequence:

1. **SessionState** - Foundation for session memory
2. **Category Defaults** - Simple utility, no dependencies
3. **Recency Queries** - Service layer, testable in isolation
4. **TypeAheadComboBox** - Widget, testable with mock data
5. **Dropdown Builders** - Uses recency queries
6. **AddInventoryDialog Refactor** - Integrates all components

## Testing Strategy

### Unit Tests

```bash
# Session state tests
pytest src/tests/ui/test_session_state.py -v

# Category defaults tests
pytest src/tests/utils/test_category_defaults.py -v

# Recency query tests
pytest src/tests/services/test_inventory_item_service.py -v -k recency
```

### Integration Tests

```bash
# Full dialog workflow tests
pytest src/tests/integration/test_add_inventory_dialog.py -v
```

## Key Patterns to Follow

### Session Management

Always pass session when calling other services:

```python
def get_recent_products(ingredient_id, ..., session=None):
    if session is not None:
        return _get_recent_products_impl(..., session)
    with session_scope() as session:
        return _get_recent_products_impl(..., session)
```

### Widget Creation

Extend CTkFrame for composite widgets:

```python
class TypeAheadComboBox(ctk.CTkFrame):
    def __init__(self, master, values, min_chars=2, **kwargs):
        super().__init__(master, **kwargs)
        # Wrap CTkComboBox inside frame
```

## Reference Documents

- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md`
- Design: `docs/design/F029_streamlined_inventory_entry.md`
- Research: `kitty-specs/029-streamlined-inventory-entry/research.md`
- Data Model: `kitty-specs/029-streamlined-inventory-entry/data-model.md`
