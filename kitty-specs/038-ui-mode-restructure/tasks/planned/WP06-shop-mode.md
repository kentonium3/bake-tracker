---
work_package_id: "WP06"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "SHOP Mode"
phase: "Phase 2 - Mode Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-05"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - SHOP Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement SHOP mode with Shopping Lists, Purchases (new tabs), and Inventory migration.

**Success Criteria**:
- SHOP mode dashboard shows shopping lists by store and inventory alerts (FR-009)
- Shopping Lists tab organizes items by store (FR-023)
- Purchases tab allows recording purchases (FR-022)
- Inventory (My Pantry) tab accessible and functional

**User Story**: US7 - SHOP Mode for Inventory (Priority P3)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes), WP02 (Main Window Navigation)

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - User Story 7, FR-009, FR-022, FR-023
- `kitty-specs/038-ui-mode-restructure/data-model.md` - ShopMode definition

**Existing Tab**:
- `src/ui/inventory_tab.py` (103KB) - Large, complex tab

**Services Available**:
- `event_service.get_shopping_list(event_id, include_packaging)` - Shopping list data
- `purchase_service.record_purchase()`, `get_purchase_history()`, `get_most_recent_purchase()`
- `inventory_item_service` - Inventory operations

## Subtasks & Detailed Guidance

### Subtask T031 - Create ShopDashboard

**Purpose**: Show shopping lists by store and inventory alerts (FR-009).

**Steps**:
1. Create `src/ui/dashboards/shop_dashboard.py`
2. Extend BaseDashboard
3. Display shopping lists summary (items by store)
4. Show low inventory alerts

**Files**: `src/ui/dashboards/shop_dashboard.py`

**Implementation**:
```python
class ShopDashboard(BaseDashboard):
    def __init__(self, master):
        super().__init__(master)
        self._create_shopping_summary()
        self._create_alerts()

    def _create_shopping_summary(self):
        self.add_stat("Shopping Lists", "0")
        self.add_stat("Items Needed", "0")
        self.stores_frame = ctk.CTkFrame(self.stats_frame)
        self.stores_frame.pack(fill="x", pady=5)

    def _create_alerts(self):
        self.alerts_frame = ctk.CTkFrame(self.stats_frame)
        ctk.CTkLabel(self.alerts_frame, text="Low Inventory Alerts").pack()
        self.alerts_frame.pack(fill="x", pady=5)

    def refresh(self):
        from services.event_service import get_upcoming_events, get_shopping_list
        from services.inventory_item_service import get_low_inventory_items
        # Aggregate shopping needs, show alerts
```

**Parallel?**: No - needed for T032.

### Subtask T032 - Create ShopMode

**Purpose**: Container for SHOP mode with dashboard and tabs.

**Steps**:
1. Create `src/ui/modes/shop_mode.py`
2. Extend BaseMode
3. Set up dashboard and CTkTabview with 3 tabs

**Files**: `src/ui/modes/shop_mode.py`

**Implementation**:
```python
class ShopMode(BaseMode):
    def __init__(self, master):
        super().__init__(master, name="SHOP")
        self.dashboard = ShopDashboard(self)
        self.dashboard.pack(fill="x", padx=10, pady=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabview.add("Shopping Lists")
        self.tabview.add("Purchases")
        self.tabview.add("Inventory")

        self._setup_tabs()
```

**Parallel?**: No - needed before tab setup.

### Subtask T033 - Create shopping_lists_tab.py (NEW) [P]

**Purpose**: Display shopping lists organized by store (FR-023).

**Steps**:
1. Create `src/ui/tabs/shopping_lists_tab.py`
2. Display event selector for shopping list
3. Show items grouped by store/supplier
4. Allow marking items as purchased

**Files**: `src/ui/tabs/shopping_lists_tab.py`

**Implementation**:
```python
class ShoppingListsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_controls()
        self._create_list_view()

    def _create_controls(self):
        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", pady=5)

        self.event_combo = ctk.CTkComboBox(controls, command=self._on_event_selected)
        self.event_combo.pack(side="left", padx=5)

        self.generate_btn = ctk.CTkButton(controls, text="Generate List", command=self._generate_list)
        self.generate_btn.pack(side="left", padx=5)

        self.print_btn = ctk.CTkButton(controls, text="Print", command=self._print_list)
        self.print_btn.pack(side="left", padx=5)

    def _create_list_view(self):
        # Scrollable frame with store sections
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)

    def _on_event_selected(self, event_name: str):
        self._load_shopping_list()

    def _load_shopping_list(self):
        from services.event_service import get_shopping_list
        # Group by store, display
```

**Service Integration**:
- `event_service.get_shopping_list(event_id, include_packaging=True)`
- Returns items organized by product with store info

**Display Format**:
```
Store: Costco
  [ ] All-Purpose Flour - 5 lbs
  [ ] Sugar - 10 lbs

Store: Walmart
  [ ] Vanilla Extract - 4 oz
  [ ] Butter - 2 lbs
```

**Parallel?**: Yes - after T031/T032.

### Subtask T034 - Create purchases_tab.py (NEW) [P]

**Purpose**: Allow recording and viewing purchases.

**Steps**:
1. Create `src/ui/tabs/purchases_tab.py`
2. Display purchase history list
3. Provide form to record new purchases
4. Support edit/delete operations

**Files**: `src/ui/tabs/purchases_tab.py`

**Implementation**:
```python
class PurchasesTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_action_bar()
        self._create_purchase_list()

    def _create_action_bar(self):
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", pady=5)

        self.add_btn = ctk.CTkButton(bar, text="Record Purchase", command=self._add_purchase)
        self.add_btn.pack(side="left", padx=5)

        self.edit_btn = ctk.CTkButton(bar, text="Edit", command=self._edit_purchase)
        self.edit_btn.pack(side="left", padx=5)

        self.delete_btn = ctk.CTkButton(bar, text="Delete", command=self._delete_purchase)
        self.delete_btn.pack(side="left", padx=5)

    def _create_purchase_list(self):
        columns = ("date", "product", "quantity", "price", "supplier")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill="both", expand=True)

    def _add_purchase(self):
        # Open purchase dialog
        pass

    def refresh(self):
        from services.purchase_service import get_purchase_history
        purchases = get_purchase_history()
        # Populate tree
```

**Service Integration**:
- `purchase_service.record_purchase(...)` - Create purchase
- `purchase_service.get_purchase_history(...)` - List purchases
- `purchase_service.get_most_recent_purchase(product_id)` - Price suggestions

**Parallel?**: Yes - after T031/T032.

### Subtask T035 - Integrate inventory_tab.py [P]

**Purpose**: Add Inventory (My Pantry) tab to SHOP mode.

**Steps**:
1. Review existing `inventory_tab.py` structure (103KB - large file)
2. Instantiate InventoryTab in ShopMode
3. Add to "Inventory" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/shop_mode.py` (modify)
- `src/ui/inventory_tab.py` (may need minor adjustments)

**Verification**: Test all inventory operations - this is a complex tab:
- Add inventory items
- View FIFO consumption
- Filter by ingredient, supplier
- Low stock indicators

**Notes**: This is the largest existing tab (103KB). Take extra care to preserve all functionality.

**Parallel?**: Yes - after T031/T032.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large inventory_tab.py (103KB) integration | Minimal changes; thorough testing |
| Shopping list performance with many items | Use pagination or lazy loading |
| Store grouping logic complexity | Use service layer for grouping |

## Definition of Done Checklist

- [ ] ShopDashboard shows shopping summary and alerts
- [ ] ShopMode contains all 3 tabs
- [ ] Shopping Lists tab: Event selector works
- [ ] Shopping Lists tab: Items grouped by store
- [ ] Shopping Lists tab: Generate list works
- [ ] Purchases tab: Add, Edit, Delete work
- [ ] Purchases tab: Purchase history displays
- [ ] Inventory tab: All existing functionality preserved
- [ ] Tab switching within mode works

## Review Guidance

- Test shopping list generation for events
- Verify purchase recording affects inventory
- Check all inventory tab functionality (FIFO, filtering)

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
