# Quickstart: Manual Inventory Adjustments (F041)

## Overview

This feature adds manual inventory depletion capability for tracking spoilage, gifts, corrections, and ad hoc usage outside the production workflow.

## Parallel Development Setup

This feature uses parallel development with two agents:

| Agent | Scope | Files |
|-------|-------|-------|
| **Claude** (Service) | Model, enum, service logic, tests | `src/models/`, `src/services/`, `src/tests/` |
| **Gemini** (UI) | Adjustment dialog, inventory tab enhancement | `src/ui/` |

### Integration Contract

The UI layer calls the service layer via this contract:

```python
from src.services.inventory_item_service import manual_adjustment
from src.models.enums import DepletionReason
from decimal import Decimal

# Record a depletion
depletion = manual_adjustment(
    inventory_item_id=123,
    quantity_to_deplete=Decimal("5.0"),
    reason=DepletionReason.SPOILAGE,
    notes="Weevils discovered"
)

# Access results
print(f"Depleted: {depletion.quantity_depleted}")
print(f"Cost impact: ${depletion.cost}")
print(f"New quantity: {item.quantity}")  # Item is updated
```

## Development Steps

### Claude (Service Layer)

1. **Create DepletionReason enum** in `src/models/enums.py`
2. **Create InventoryDepletion model** in `src/models/inventory_depletion.py`
3. **Add manual_adjustment()** to `src/services/inventory_item_service.py`
4. **Add get_depletion_history()** to `src/services/inventory_item_service.py`
5. **Write unit tests** in `src/tests/test_inventory_adjustment.py`

### Gemini (UI Layer)

1. **Create adjustment dialog** - `src/ui/dialogs/adjustment_dialog.py`
2. **Add [Adjust] button** to inventory tab item rows
3. **Implement live preview** - Calculate new quantity as user types
4. **Handle validation errors** - Display service layer exceptions
5. **Update depletion history view** - Show manual adjustments with reason/notes

## Key Files

```
src/
  models/
    enums.py                    # Add DepletionReason enum
    inventory_depletion.py      # NEW: InventoryDepletion model
    __init__.py                 # Export new model
  services/
    inventory_item_service.py   # Add manual_adjustment(), get_depletion_history()
  ui/
    dialogs/
      adjustment_dialog.py      # NEW: Manual adjustment dialog
    inventory_tab.py            # Add [Adjust] button, wire dialog
  tests/
    test_inventory_adjustment.py # NEW: Unit tests for service
```

## Testing

```bash
# Run all tests
pytest src/tests -v

# Run only adjustment tests
pytest src/tests/test_inventory_adjustment.py -v

# Run with coverage
pytest src/tests -v --cov=src/services/inventory_item_service
```

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| quantity_to_deplete > 0 | Service raises ValidationError |
| quantity_to_deplete <= current quantity | Service raises ValidationError |
| notes required when reason=OTHER | Service raises ValidationError |
| Inventory never goes negative | Service validates before update |

## DepletionReason Values

| Value | UI Label | Use Case |
|-------|----------|----------|
| SPOILAGE | Spoilage/Waste | Ingredient went bad |
| GIFT | Gift/Donation | Gave to friend/family |
| CORRECTION | Physical Count Correction | Inventory count mismatch |
| AD_HOC_USAGE | Ad Hoc Usage | Testing, personal use |
| OTHER | Other (specify in notes) | Requires notes field |
