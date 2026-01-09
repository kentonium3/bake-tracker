# Research: Purchases Tab with CRUD Operations

**Feature**: 042-purchases-tab-crud-operations
**Date**: 2026-01-08

## Existing Codebase Patterns

### 1. PurchaseService (src/services/purchase_service.py)

**Existing Methods**:
| Method | Purpose |
|--------|---------|
| `record_purchase()` | Creates purchase with auto unit cost calculation |
| `get_purchase()` | Retrieves single purchase by ID |
| `get_purchase_history()` | Multi-filter query (product, ingredient, date range, store) |
| `get_most_recent_purchase()` | Latest purchase for a product |
| `calculate_average_price()` | Average unit cost in time window |
| `detect_price_change()` | Alert level for price changes |
| `get_price_trend()` | Linear regression price analysis |
| `get_last_price_at_supplier()` | Last price at specific supplier (accepts session) |
| `get_last_price_any_supplier()` | Last price from any supplier (accepts session) |
| `delete_purchase()` | Delete by ID |

**Gap Analysis**: Missing methods for:
- Filtered list with date range presets ("Last 30 days", etc.)
- FIFO remaining inventory calculation per purchase
- Edit validation (consumed quantity check)
- Delete validation (any depletions exist check)
- Update with FIFO cost recalculation
- Usage history (depletions with recipe info)

### 2. Dialog Pattern (src/ui/dialogs/adjustment_dialog.py)

**Structure**:
```python
class SomeDialog(ctk.CTkToplevel):
    def __init__(self, parent, data_object, on_apply: Optional[Callable] = None):
        super().__init__(parent)
        self.title("Dialog Title")
        self.on_apply = on_apply

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._extract_info()
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()
        self._center_on_parent(parent)
```

**Key Patterns**:
- Modal via `transient()` + `grab_set()`
- Callback function for results
- Separate methods for extract/create/layout/bind
- Live preview updates during input
- Handles both ORM objects and dicts

### 3. Tab Pattern (src/ui/inventory_tab.py)

**Structure**:
```python
class SomeTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # Grid: fixed header/controls, expandable content
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Controls
        self.grid_rowconfigure(2, weight=1)  # Content (expands)

        self._create_header()
        self._create_controls()
        self._create_item_list()  # ttk.Treeview
```

**Key Patterns**:
- ttk.Treeview for performant lists
- Sortable columns via header click
- Filter dropdowns + search entry
- Lazy loading with `_data_loaded` flag
- Context menu on right-click

### 4. Session Management Pattern

**Correct Pattern**:
```python
def method(..., session: Optional[Session] = None) -> ReturnType:
    def _impl(sess: Session) -> ReturnType:
        # All work uses sess parameter
        ...

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Critical Rules**:
1. Functions callable from other services MUST accept `session=None`
2. Inner `_impl()` function contains actual logic
3. Outer function routes based on session presence
4. Prevents detached object issues in multi-step operations

## Technology Decisions

### Decision 1: Extend PurchaseService

**Decision**: Add new methods to existing `PurchaseService`
**Rationale**:
- Keeps purchase-related logic cohesive
- Follows existing codebase pattern (services are domain-focused)
- Avoids proliferation of small service classes
**Alternatives Rejected**:
- New `PurchaseHistoryService`: Unnecessary separation; methods are tightly related

### Decision 2: ttk.Treeview for List

**Decision**: Use ttk.Treeview (same as InventoryTab)
**Rationale**:
- Handles 500+ rows efficiently
- Built-in column sorting
- Proven pattern in codebase
- Consistent user experience
**Alternatives Rejected**:
- CTkScrollableFrame with row widgets: Poor performance at scale

### Decision 3: Three Separate Dialogs

**Decision**: Separate Add, Edit, and View Details dialogs
**Rationale**:
- Matches existing dialog patterns
- Clearer separation of concerns
- Edit has unique constraints (read-only product, consumed qty validation)
- View Details is read-only with different layout
**Alternatives Rejected**:
- Unified dialog with mode switching: More complex, harder to maintain

### Decision 4: Parallelization Strategy

**Decision**: Claude handles service + Tab + Add; Gemini handles Edit + View Details
**Rationale**:
- Service layer is foundational (must complete first)
- Tab UI and Add dialog are the primary P1 flow
- Edit and View Details are independent P2/P3 features
- Clear file boundaries prevent conflicts
**Alternatives Rejected**:
- All UI to Gemini: Add dialog too tightly coupled to service contract iteration

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| F028 Purchase Tracking | Complete | Purchase, InventoryItem models |
| F042 UI Polish | Complete | Layout patterns, grid expansion |
| PurchaseService | Exists | Needs extension with new methods |
| AdjustmentDialog | Exists | Pattern reference for dialogs |
| InventoryTab | Exists | Pattern reference for tab |

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Session management bugs | Medium | High | Follow documented pattern exactly; test multi-step operations |
| FIFO recalculation errors on edit | Medium | High | Unit tests for edge cases; compare before/after values |
| Filter performance with large datasets | Low | Medium | Use indexed queries; limit result set |
| Dialog/Tab state sync issues | Low | Medium | Callback pattern with full refresh |
