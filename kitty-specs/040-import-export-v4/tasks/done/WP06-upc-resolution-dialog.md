---
work_package_id: "WP06"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "UPC Resolution Dialog"
phase: "Phase 2 - BT Mobile Workflows"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "11228"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - UPC Resolution Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create CustomTkinter dialog for resolving unknown UPCs during purchase import
- Support three resolution options: Map to existing, Create new, Skip
- Persist UPC mapping to Product for future imports
- Clean integration with WP05 import workflow

**Success Criteria**:
- Dialog displays unmatched UPC with scan details
- "Map to existing" updates Product.upc_code
- "Create new product" creates Product with UPC, then Purchase
- "Skip" logs the skip and continues to next UPC

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 3 acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Purchase import JSON schema
- `kitty-specs/040-import-export-v4/research.md` - Key decisions D3, D4

**Key Constraints**:
- Dialog receives unmatched_purchases list from WP05 ImportResult
- Must match existing CustomTkinter dialog patterns in codebase
- Product requires ingredient_id FK, so "Create new" needs ingredient selection
- Non-modal option preferred (user can process in background)

**New File**: `src/ui/dialogs/upc_resolution_dialog.py`

**Dependencies**: WP05 must provide unmatched_purchases in ImportResult

## Subtasks & Detailed Guidance

### Subtask T025 - Create dialog structure

**Purpose**: Establish dialog layout and lifecycle.

**Steps**:
1. Create new file `src/ui/dialogs/upc_resolution_dialog.py`
2. Use CTkToplevel as base class (matches other dialogs)
3. Dialog receives: parent window, unmatched_purchases list
4. Layout:
   - Header: "Resolve Unknown UPCs ({count} remaining)"
   - Current UPC info panel: UPC, price, timestamp
   - Three action buttons: Map to Existing, Create New, Skip
   - Progress indicator: "1 of N"
   - Close button (exits without processing remaining)

**Code Pattern**:
```python
import customtkinter as ctk
from typing import List, Dict, Callable

class UPCResolutionDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        unmatched_purchases: List[Dict],
        on_complete: Callable[[int, int, int], None] = None
    ):
        super().__init__(parent)
        self.title("Resolve Unknown UPCs")
        self.geometry("500x400")

        self._purchases = unmatched_purchases
        self._current_index = 0
        self._mapped_count = 0
        self._created_count = 0
        self._skipped_count = 0
        self._on_complete = on_complete

        self._setup_ui()
        self._show_current_purchase()

    def _setup_ui(self):
        # Header
        self._header_label = ctk.CTkLabel(self, text="")
        self._header_label.pack(pady=10)

        # UPC info frame
        self._info_frame = ctk.CTkFrame(self)
        self._info_frame.pack(fill="x", padx=20, pady=10)

        # UPC details
        self._upc_label = ctk.CTkLabel(self._info_frame, text="")
        self._upc_label.pack()

        # ... add price, timestamp labels

        # Action buttons
        self._button_frame = ctk.CTkFrame(self)
        self._button_frame.pack(fill="x", padx=20, pady=10)

        self._map_btn = ctk.CTkButton(
            self._button_frame,
            text="Map to Existing Product",
            command=self._on_map_existing
        )
        self._map_btn.pack(side="left", padx=5)

        # ... add create, skip buttons
```

**Files**: `src/ui/dialogs/upc_resolution_dialog.py`
**Parallel?**: No - foundation for other subtasks

### Subtask T026 - Implement "Map to existing product" option

**Purpose**: Allow user to link UPC to an existing product.

**Steps**:
1. On button click, show product search/selection UI:
   - CTkEntry for search (filter by name)
   - CTkOptionMenu or Listbox showing matching products
2. On product selection:
   - Update `product.upc_code = current_upc`
   - Create Purchase and InventoryItem (same logic as WP05)
   - Increment mapped_count
   - Advance to next UPC

**Code Pattern**:
```python
def _on_map_existing(self):
    """Show product selection dialog."""
    selection_dialog = ProductSelectionDialog(self, self._on_product_selected)
    selection_dialog.grab_set()

def _on_product_selected(self, product_id: int):
    """Handle product selection for UPC mapping."""
    with session_scope() as session:
        product = session.query(Product).get(product_id)
        if product:
            # Update UPC for future matching
            product.upc_code = self._current_purchase["upc"]

            # Create purchase (reuse WP05 logic)
            self._create_purchase_for_product(product.id, session)

            session.commit()

    self._mapped_count += 1
    self._advance_to_next()
```

**Files**: `src/ui/dialogs/upc_resolution_dialog.py`
**Parallel?**: Yes - independent of T027, T028

**Notes**:
- Consider creating a simple ProductSelectionDialog or inline search
- Reuse existing product listing patterns from codebase

### Subtask T027 - Implement "Create new product" option

**Purpose**: Allow user to create a new product with the scanned UPC.

**Steps**:
1. On button click, show product creation form:
   - Ingredient selection (required - FK)
   - Brand name (optional)
   - Product name
   - Package size/unit (optional)
2. On form submit:
   - Create Product with upc_code = current_upc
   - Create Purchase and InventoryItem
   - Increment created_count
   - Advance to next UPC

**Code Pattern**:
```python
def _on_create_new(self):
    """Show product creation form."""
    # Use existing AddProductDialog or create simplified version
    from src.ui.dialogs.add_product_dialog import AddProductDialog

    dialog = AddProductDialog(
        self,
        prefill_upc=self._current_purchase["upc"],
        on_save=self._on_product_created
    )
    dialog.grab_set()

def _on_product_created(self, product_id: int):
    """Handle new product creation."""
    with session_scope() as session:
        self._create_purchase_for_product(product_id, session)
        session.commit()

    self._created_count += 1
    self._advance_to_next()
```

**Files**: `src/ui/dialogs/upc_resolution_dialog.py`
**Parallel?**: Yes - independent of T026, T028

**Notes**:
- Check if AddProductDialog exists and can accept prefill_upc
- May need to create simplified inline form if full dialog is too complex

### Subtask T028 - Implement "Skip" option

**Purpose**: Allow user to skip UPC without creating records.

**Steps**:
1. On button click:
   - Log the skip with UPC details
   - Increment skipped_count
   - Advance to next UPC
2. If last UPC, call on_complete callback with counts

**Code Pattern**:
```python
import logging
logger = logging.getLogger(__name__)

def _on_skip(self):
    """Skip current UPC without processing."""
    logger.info(
        f"Skipped UPC resolution: {self._current_purchase['upc']} "
        f"(price: {self._current_purchase.get('unit_price')})"
    )
    self._skipped_count += 1
    self._advance_to_next()

def _advance_to_next(self):
    """Move to next unmatched purchase or complete."""
    self._current_index += 1
    if self._current_index >= len(self._purchases):
        self._complete()
    else:
        self._show_current_purchase()

def _complete(self):
    """Finish resolution process."""
    if self._on_complete:
        self._on_complete(
            self._mapped_count,
            self._created_count,
            self._skipped_count
        )
    self.destroy()
```

**Files**: `src/ui/dialogs/upc_resolution_dialog.py`
**Parallel?**: Yes - independent of T026, T027

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/ui/dialogs/test_upc_resolution_dialog.py -v
```

**Test Cases** (may require mocking CTk):
- `test_dialog_shows_correct_upc_info`: Dialog displays UPC details
- `test_map_existing_updates_product`: Product.upc_code updated after mapping
- `test_create_new_creates_product`: New product created with UPC
- `test_skip_increments_counter`: Skip count incremented, next UPC shown
- `test_complete_callback_called`: Callback receives correct counts

**Notes**:
- UI tests may be integration-level rather than unit tests
- Focus on service-layer logic in unit tests, mock UI

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dialog complexity | Keep minimal, three simple paths |
| Product search performance | Use indexed name search, limit results |
| Form validation | Required fields only, simple validation |

## Definition of Done Checklist

- [x] T025: Dialog structure created
- [x] T026: Map to existing works, updates UPC
- [x] T027: Create new works, creates product + purchase
- [x] T028: Skip works, logs and advances
- [x] All three paths complete successfully
- [x] Completion callback provides accurate counts

## Review Guidance

- Test with real unmatched UPCs from sample import
- Verify Product.upc_code persists after mapping
- Check that mapped UPCs match automatically on next import
- Confirm dialog closes cleanly after processing all UPCs

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:38:12Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:41:59Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-07T05:44:09Z – claude-reviewer – shell_pid= – lane=done – Approved: Tests pass, supplier handling fixed
