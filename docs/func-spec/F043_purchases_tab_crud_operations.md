# Purchases Tab Implementation - Feature Specification

**Feature ID**: F043
**Feature Name**: Purchases Tab Implementation
**Priority**: P1 - FOUNDATIONAL (blocks end-to-end workflow testing)
**Status**: Design Specification
**Created**: 2026-01-08
**Dependencies**: F028 (Purchase Tracking ✅), F042 (UI Polish ✅)
**Constitutional References**: Principle I (User-Centric Design), Principle V (Layered Architecture)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, UI mockups, and implementation patterns. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification

**The requirements and user workflow are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

**Problem**: PURCHASE mode currently has three sub-tabs planned (Inventory, Purchases, Shopping Lists), but **Purchases tab is not implemented**. Users cannot:
- View purchase history
- Add new purchases (primary data entry point)
- Track spending by supplier/product/date
- Edit/delete past purchases

**Current Workaround**: Users add purchases via Inventory tab's "Add to Pantry" dialog, but this obscures the **Purchase → Inventory** architectural flow (purchases DRIVE inventory, not vice versa).

**Solution**: Implement Purchases tab as the **primary data entry point** for new purchases, with purchase history browsing, editing, and deletion capabilities.

**Impact**:
- Establishes proper workflow: Purchase → Inventory (not Inventory → Purchase)
- Enables AI-assisted purchase workflows (BT Mobile uploads to Purchase table)
- Provides audit trail for spending analysis
- Unblocks end-to-end Plan → Purchase → Make → Deliver testing

**Scope**:
- Purchases tab UI with list view and filters
- Add Purchase dialog (single-item, product-first)
- Edit Purchase dialog (date/price/quantity only)
- Delete Purchase with validation (block if consumed)
- Purchase history queries with FIFO tracking ("remaining inventory")

---

## 1. Problem Statement

### 1.1 Missing Primary Entry Point

**Current State**:
```
User workflow (WRONG):
  1. Go to PURCHASE mode → Inventory tab
  2. Click "Add to Pantry"
  3. Dialog creates: Purchase + InventoryItem

Problems:
  - Inventory tab is NOT the conceptual entry point for purchases
  - "Add to Pantry" obscures the Purchase → Inventory relationship
  - No way to VIEW purchase history
  - No way to EDIT past purchases
  - No way to DELETE mistaken purchases
```

**Desired State**:
```
User workflow (CORRECT):
  1. Go to PURCHASE mode → Purchases tab
  2. Click "Add Purchase"
  3. Dialog creates: Purchase + InventoryItem (same backend)
  4. User can browse purchase history
  5. User can edit/delete recent purchases

Architecture alignment:
  Purchase (transaction) → InventoryItem (current state)
  NOT: InventoryItem → Purchase (backwards!)
```

### 1.2 Real-World Use Cases

**Use Case 1: Costco Shopping Trip**
```
User: Just got back from Costco, need to record purchases
Flow:
  1. Open Purchases tab
  2. Add Purchase: King Arthur AP Flour 25lb, $15.99, 1/8/2026
  3. Add Purchase: Nestle Chocolate Chips 12oz, $4.99, 1/8/2026
  4. Add Purchase: Organic Valley Butter 1lb, $6.49, 1/8/2026
Result: 3 purchases recorded, inventory automatically updated
```

**Use Case 2: Price Tracking**
```
User: How much did I pay for flour last time?
Flow:
  1. Open Purchases tab
  2. Search: "flour"
  3. See purchase history: $15.99 (1/8/2026), $14.99 (12/15/2025), $16.49 (11/20/2025)
Result: User knows current price is reasonable
```

**Use Case 3: Fix Typo**
```
User: Oops, I entered $1.99 instead of $19.99
Flow:
  1. Open Purchases tab
  2. Find purchase (filter by date: today)
  3. Click "Edit"
  4. Change price: $1.99 → $19.99
  5. Save (recalculates FIFO costs)
Result: Accurate cost tracking restored
```

**Use Case 4: Delete Duplicate**
```
User: I accidentally entered this purchase twice
Flow:
  1. Open Purchases tab
  2. Find duplicate purchase (same product, same date, same price)
  3. Click "Delete"
  4. System checks: Has this purchase been consumed?
     - If YES: Block delete ("Cannot delete - 5 cups already used")
     - If NO: Delete purchase + linked inventory
Result: Duplicate removed, data integrity maintained
```

### 1.3 AI-Assisted Workflow Integration

**BT Mobile Purchase Upload** (current):
```
User: Takes photo of receipt with Gemini mobile app
Flow:
  1. Gemini OCR extracts: Product, Price, Date, Supplier
  2. Gemini generates JSON: {"purchases": [{...}]}
  3. User uploads JSON via Import system
  4. Purchase table populated → Inventory auto-updated
```

**Future Voice/Chat** (planned):
```
User: "I just bought flour at Costco for $15.99"
Flow:
  1. Voice assistant creates Purchase record via API
  2. API auto-creates InventoryItem
  3. User sees purchase in Purchases tab immediately
```

**Architectural Requirement**: Purchases tab must be the **canonical view** of purchase data, regardless of entry method (manual UI, BT Mobile JSON, future API).

---

## 2. Proposed Solution

### 2.1 Purchases Tab UI

**Location**: PURCHASE Mode → Purchases tab (between Inventory and Shopping Lists)

**Layout**:
```
┌─ PURCHASE Mode ──────────────────────────────────────────┐
│ 🛒 PURCHASE • 47 items in inventory • $1,234.56 spent    │
│ [Inventory] [Purchases] [Shopping Lists]                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ [+ Add Purchase]  Date Range: [Last 30 days ▼]          │
│                   Supplier: [All ▼]  Search: [____]      │
│                                                           │
│ ╔═══════════════════════════════════════════════════╗    │
│ ║ Date       Product               Supplier  Qty ... ║   │
│ ║ ────────   ──────────────────    ────────  ─── ... ║   │
│ ║ 1/8/2026   King Arthur AP 25lb   Costco    1   ... ║   │
│ ║ 1/8/2026   Nestle Choc Chips     Costco    2   ... ║   │
│ ║ 1/5/2026   Organic Valley Butter Wegmans   3   ... ║   │
│ ║ ...                                                ║   │
│ ║ (20-30 rows visible)                               ║   │
│ ╚═══════════════════════════════════════════════════╝    │
│                                                           │
│ Loaded 47 purchases                                      │
└──────────────────────────────────────────────────────────┘
```

**Filters (Single Row)**:
- **Date Range dropdown**: Last 30 days | Last 90 days | Last year | All time
- **Supplier dropdown**: All | Costco | Wegmans | Amazon | ...
- **Search bar**: Filter by product name (type-ahead)

**List Columns**:
1. **Date** - Purchase date (sortable)
2. **Product** - Product name with package size
3. **Supplier** - Supplier name
4. **Qty** - Quantity purchased (e.g., "1 package")
5. **Unit Price** - Price per package (e.g., "$15.99")
6. **Total** - Total cost (qty × unit price)
7. **Remaining** - Current inventory from this purchase (FIFO tracking)

**Actions** (context menu or buttons):
- **Add Purchase** - Opens Add Purchase dialog
- **View Details** - Shows purchase info + inventory tracking
- **Edit** - Opens Edit Purchase dialog (if not fully consumed)
- **Delete** - Deletes purchase (if not consumed)

### 2.2 Add Purchase Dialog

**Triggered by**: [+ Add Purchase] button

**Dialog Layout**:
```
┌─ Add Purchase ────────────────────────────────────────┐
│                                                        │
│  Product: [King Arthur AP Flour 25lb ▼]               │
│           ↑ Type-ahead dropdown with recent items     │
│                                                        │
│  Purchase Date: [01/08/2026]  ← Date picker           │
│                                                        │
│  Quantity: [1] packages                                │
│            ↑ Integer input                            │
│                                                        │
│  Unit Price: [$15.99]  ← Auto-fills from last purchase│
│              ↑ Decimal input (2 decimal places)       │
│                                                        │
│  Supplier: [Costco ▼]  ← Defaults to preferred_supplier│
│            ↑ Dropdown with all suppliers              │
│                                                        │
│  Notes: (optional)                                     │
│  ┌────────────────────────────────────────────────┐   │
│  │ On sale - 20% off regular price                │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  Preview:                                              │
│  • Total Cost: $15.99 (1 × $15.99)                    │
│  • Inventory: +1 package added to pantry              │
│                                                        │
│  [Cancel]  [Add Purchase]                              │
└────────────────────────────────────────────────────────┘
```

**Field Behavior**:

1. **Product dropdown**:
   - Type-ahead with fuzzy matching
   - Shows: "King Arthur All-Purpose Flour 25lb"
   - Recent purchases at top (session intelligence)
   - Supports inline product creation (future)

2. **Purchase Date**:
   - Defaults to today
   - Date picker for easy selection
   - Validates: Cannot be future date

3. **Quantity**:
   - Integer input (1, 2, 3, ...)
   - Defaults to 1
   - Validates: Must be > 0

4. **Unit Price**:
   - Decimal input (2 decimal places)
   - Auto-fills from most recent purchase of this product
   - User can override
   - Validates: Must be ≥ 0

5. **Supplier**:
   - Dropdown with all suppliers
   - Defaults to product's `preferred_supplier` (if set)
   - User can override
   - Required field

6. **Notes**:
   - Optional text field
   - For context: "On sale", "Bulk buy", "Trial size", etc.

**Validation**:
- ✅ Product selected
- ✅ Purchase date valid (not future)
- ✅ Quantity > 0
- ✅ Unit price ≥ 0
- ✅ Supplier selected

**On Save**:
```python
# Create Purchase record
purchase = Purchase(
    product_id=selected_product.id,
    supplier_id=selected_supplier.id,
    purchase_date=date(2026, 1, 8),
    quantity_purchased=1,
    unit_price=Decimal("15.99"),
    notes="On sale - 20% off"
)
session.add(purchase)

# Create InventoryItem (automatic via service)
inventory_item = InventoryItem(
    purchase_id=purchase.id,
    ingredient_id=selected_product.ingredient_id,
    current_quantity=selected_product.package_unit_quantity,  # From product
    unit=selected_product.package_unit,
    unit_cost=Decimal("15.99") / selected_product.package_unit_quantity
)
session.add(inventory_item)

session.commit()

# Result: Purchase recorded, inventory updated
```

### 2.3 Edit Purchase Dialog

**Triggered by**: Right-click → "Edit" or double-click purchase row

**Dialog Layout** (same as Add, but pre-filled):
```
┌─ Edit Purchase ───────────────────────────────────────┐
│                                                        │
│  Purchase: King Arthur AP Flour 25lb (1/8/2026)       │
│                                                        │
│  Product: [King Arthur AP Flour 25lb]  ← READ-ONLY    │
│           ⚠️ Cannot change product after creation     │
│                                                        │
│  Purchase Date: [01/08/2026]  ← Editable              │
│                                                        │
│  Quantity: [1] packages  ← Editable                    │
│                                                        │
│  Unit Price: [$15.99]  ← Editable                      │
│                                                        │
│  Supplier: [Costco ▼]  ← Editable                      │
│                                                        │
│  Notes: (optional)                                     │
│  ┌────────────────────────────────────────────────┐   │
│  │ On sale - 20% off regular price                │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  Preview (if changes made):                            │
│  • New Total: $19.99 (1 × $19.99)                     │
│  • FIFO costs will be recalculated                    │
│                                                        │
│  [Cancel]  [Save Changes]                              │
└────────────────────────────────────────────────────────┘
```

**Editable Fields**:
- ✅ Purchase date (can fix typos)
- ✅ Quantity (can fix typos)
- ✅ Unit price (can fix typos)
- ✅ Supplier (can correct)
- ✅ Notes (can add/edit)

**Read-Only Fields**:
- ❌ Product (cannot change - would break FIFO chain)

**Validation**:
- If inventory has been consumed (FIFO depletions exist):
  - Allow edit IF new quantity ≥ consumed quantity
  - Block edit IF new quantity < consumed quantity
  - Example: Purchased 10 cups, used 5 cups, can edit quantity to 7+ (not 3)

**On Save**:
```python
# Update Purchase record
purchase.purchase_date = new_date
purchase.quantity_purchased = new_quantity
purchase.unit_price = new_unit_price
purchase.supplier_id = new_supplier_id
purchase.notes = new_notes

# Recalculate InventoryItem (if quantity/price changed)
inventory_item.current_quantity = (
    new_quantity * package_unit_quantity - consumed_quantity
)
inventory_item.unit_cost = new_unit_price / package_unit_quantity

session.commit()

# Result: Purchase corrected, FIFO costs recalculated
```

### 2.4 Delete Purchase

**Triggered by**: Right-click → "Delete" or Delete key

**Validation**:
```python
def can_delete_purchase(purchase_id: int, session) -> tuple[bool, str]:
    """
    Check if purchase can be deleted.
    
    Returns:
        (can_delete, reason)
    """
    purchase = session.query(Purchase).get(purchase_id)
    
    # Check if any inventory has been consumed
    inventory_items = purchase.inventory_items
    for item in inventory_items:
        depletions = session.query(InventoryDepletion).filter(
            InventoryDepletion.inventory_item_id == item.id
        ).all()
        
        if depletions:
            consumed_qty = sum(abs(d.quantity_depleted) for d in depletions)
            return False, f"Cannot delete - {consumed_qty} {item.unit} already used in production"
    
    return True, ""
```

**Confirmation Dialog** (if deletable):
```
┌─ Confirm Delete ──────────────────────────────────────┐
│                                                        │
│  ⚠️ Delete Purchase?                                   │
│                                                        │
│  King Arthur AP Flour 25lb                             │
│  Purchased: 1/8/2026                                   │
│  Price: $15.99                                         │
│  Supplier: Costco                                      │
│                                                        │
│  This will also remove 10 cups from inventory.         │
│                                                        │
│  This action cannot be undone.                         │
│                                                        │
│  [Cancel]  [Delete Purchase]                           │
└────────────────────────────────────────────────────────┘
```

**Error Dialog** (if NOT deletable):
```
┌─ Cannot Delete Purchase ──────────────────────────────┐
│                                                        │
│  ❌ Cannot Delete Purchase                             │
│                                                        │
│  King Arthur AP Flour 25lb                             │
│  Purchased: 1/8/2026                                   │
│                                                        │
│  Reason: 5 cups already used in production:            │
│  • Sugar Cookies (12/20/2025): 3 cups                 │
│  • Brownies (12/25/2025): 2 cups                      │
│                                                        │
│  You can edit this purchase instead, or manually       │
│  adjust inventory if needed.                           │
│                                                        │
│  [OK]                                                  │
└────────────────────────────────────────────────────────┘
```

**On Delete** (if allowed):
```python
# Delete Purchase + cascade to InventoryItem
purchase = session.query(Purchase).get(purchase_id)
inventory_items = purchase.inventory_items

# Delete linked inventory items
for item in inventory_items:
    session.delete(item)

# Delete purchase
session.delete(purchase)
session.commit()

# Result: Purchase and inventory removed
```

### 2.5 View Purchase Details

**Triggered by**: Right-click → "View Details" or dedicated button

**Dialog Layout**:
```
┌─ Purchase Details ────────────────────────────────────┐
│                                                        │
│  King Arthur All-Purpose Flour 25lb                    │
│                                                        │
│  Purchase Information:                                 │
│  • Date: January 8, 2026                              │
│  • Supplier: Costco (Waltham, MA)                     │
│  • Quantity: 1 package (10 cups)                      │
│  • Unit Price: $15.99 per package ($1.599/cup)        │
│  • Total Cost: $15.99                                 │
│  • Notes: On sale - 20% off                           │
│                                                        │
│  Inventory Tracking:                                   │
│  • Original: 10 cups                                  │
│  • Used: 5 cups (50%)                                 │
│  • Remaining: 5 cups (50%)                            │
│                                                        │
│  Usage History:                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ Date       Recipe          Qty      Cost       │   │
│  │ ─────────  ──────────────  ───────  ─────────  │   │
│  │ 1/10/2026  Sugar Cookies   3 cups   $4.80     │   │
│  │ 1/12/2026  Brownies        2 cups   $3.20     │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  [Edit Purchase]  [Close]                              │
└────────────────────────────────────────────────────────┘
```

**Key Information**:
- Purchase details (date, supplier, price, notes)
- Inventory tracking (original → used → remaining)
- Usage history (depletions with recipes, dates, costs)
- Quick action: [Edit Purchase] button

---

## 3. Data Model (No Changes)

**Existing Models** (already implemented in F028):

### Purchase Model
```python
class Purchase(BaseModel):
    __tablename__ = "purchases"
    
    product_id = Column(Integer, ForeignKey("products.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    purchase_date = Column(Date)
    unit_price = Column(Numeric(10, 4))
    quantity_purchased = Column(Integer)
    notes = Column(Text, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")
    inventory_items = relationship("InventoryItem", back_populates="purchase")
```

### InventoryItem Model
```python
class InventoryItem(BaseModel):
    __tablename__ = "inventory_items"
    
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    current_quantity = Column(Numeric(10, 2))
    unit = Column(String(50))
    unit_cost = Column(Numeric(10, 4))
    
    # Relationships
    purchase = relationship("Purchase", back_populates="inventory_items")
    ingredient = relationship("Ingredient")
```

**No schema changes needed** - F043 is purely UI + service layer.

---

## 4. Service Layer

### 4.1 Purchase Service (Existing - F028)

**Already Implemented**:
```python
class PurchaseService:
    def create_purchase(self, product_id, supplier_id, purchase_date, 
                       quantity, unit_price, notes, session):
        """Create purchase + auto-create inventory item."""
        
    def get_purchases(self, filters, session):
        """Query purchases with filters."""
        
    def get_purchase_by_id(self, purchase_id, session):
        """Get single purchase with details."""
        
    def update_purchase(self, purchase_id, updates, session):
        """Update purchase (if not fully consumed)."""
        
    def delete_purchase(self, purchase_id, session):
        """Delete purchase (if not consumed)."""
```

### 4.2 New Service Methods (F043)

**Extension to PurchaseService**:

```python
def get_purchase_history(
    self,
    date_range: str = "last_30_days",
    supplier_id: Optional[int] = None,
    search_query: Optional[str] = None,
    session: Session
) -> List[Dict]:
    """
    Get purchase history with filters.
    
    Args:
        date_range: "last_30_days", "last_90_days", "last_year", "all_time"
        supplier_id: Filter by supplier (None = all)
        search_query: Filter by product name (fuzzy match)
        session: DB session
        
    Returns:
        List of purchase dicts with computed fields:
        - id, product_name, supplier_name, purchase_date
        - quantity_purchased, unit_price, total_cost
        - remaining_inventory (from FIFO tracking)
    """
    # Calculate date cutoff
    if date_range == "last_30_days":
        cutoff = date.today() - timedelta(days=30)
    elif date_range == "last_90_days":
        cutoff = date.today() - timedelta(days=90)
    elif date_range == "last_year":
        cutoff = date.today() - timedelta(days=365)
    else:  # all_time
        cutoff = None
    
    # Build query
    query = session.query(Purchase).join(Product).join(Supplier)
    
    if cutoff:
        query = query.filter(Purchase.purchase_date >= cutoff)
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    if search_query:
        query = query.filter(Product.display_name.ilike(f"%{search_query}%"))
    
    query = query.order_by(Purchase.purchase_date.desc())
    
    purchases = query.all()
    
    # Compute remaining inventory for each purchase
    results = []
    for purchase in purchases:
        remaining_qty = self._calculate_remaining_inventory(purchase, session)
        results.append({
            "id": purchase.id,
            "product_name": purchase.product.display_name,
            "supplier_name": purchase.supplier.name,
            "purchase_date": purchase.purchase_date,
            "quantity_purchased": purchase.quantity_purchased,
            "unit_price": purchase.unit_price,
            "total_cost": purchase.total_cost,
            "remaining_inventory": remaining_qty,
            "notes": purchase.notes,
        })
    
    return results

def _calculate_remaining_inventory(
    self,
    purchase: Purchase,
    session: Session
) -> Decimal:
    """
    Calculate remaining inventory from this purchase (FIFO tracking).
    
    Returns:
        Total remaining quantity across all inventory items
    """
    inventory_items = purchase.inventory_items
    total_remaining = Decimal("0")
    
    for item in inventory_items:
        total_remaining += item.current_quantity
    
    return total_remaining

def can_edit_purchase(
    self,
    purchase_id: int,
    new_quantity: int,
    session: Session
) -> tuple[bool, str]:
    """
    Check if purchase can be edited.
    
    Args:
        purchase_id: Purchase to edit
        new_quantity: Proposed new quantity
        session: DB session
        
    Returns:
        (can_edit, reason)
    """
    purchase = session.query(Purchase).get(purchase_id)
    
    # Calculate consumed quantity
    consumed = Decimal("0")
    for item in purchase.inventory_items:
        depletions = session.query(InventoryDepletion).filter(
            InventoryDepletion.inventory_item_id == item.id
        ).all()
        consumed += sum(abs(d.quantity_depleted) for d in depletions)
    
    # Check if new quantity ≥ consumed
    package_qty = purchase.product.package_unit_quantity
    new_total_qty = new_quantity * package_qty
    
    if new_total_qty < consumed:
        return False, f"Cannot reduce quantity below {consumed} (already consumed)"
    
    return True, ""

def can_delete_purchase(
    self,
    purchase_id: int,
    session: Session
) -> tuple[bool, str]:
    """
    Check if purchase can be deleted.
    
    Returns:
        (can_delete, reason)
    """
    purchase = session.query(Purchase).get(purchase_id)
    
    # Check if any inventory consumed
    for item in purchase.inventory_items:
        depletions = session.query(InventoryDepletion).filter(
            InventoryDepletion.inventory_item_id == item.id
        ).all()
        
        if depletions:
            consumed_qty = sum(abs(d.quantity_depleted) for d in depletions)
            return False, f"Cannot delete - {consumed_qty} {item.unit} already used"
    
    return True, ""
```

---

## 5. UI Implementation

### 5.1 Purchases Tab Structure

**File**: `src/ui/tabs/purchases_tab.py` (NEW)

**Pattern**: Follow `inventory_tab.py` structure (F029)

```python
class PurchasesTab(ctk.CTkFrame):
    """Purchases tab for purchase history and entry."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # State
        self.purchases = []
        self.filtered_purchases = []
        self._data_loaded = False
        
        # Create UI
        self._create_header()
        self._create_controls()
        self._create_purchase_list()
        
        # Configure expansion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Purchase list expands
    
    def _create_header(self):
        """Title + subtitle."""
        
    def _create_controls(self):
        """[Add Purchase] button + filters (date/supplier/search)."""
        
    def _create_purchase_list(self):
        """Treeview with purchase rows."""
        
    def load_purchases(self):
        """Query purchases with current filters."""
        
    def _on_add_purchase(self):
        """Open Add Purchase dialog."""
        
    def _on_edit_purchase(self):
        """Open Edit Purchase dialog."""
        
    def _on_delete_purchase(self):
        """Delete selected purchase (with validation)."""
        
    def _on_view_details(self):
        """Open Purchase Details dialog."""
```

### 5.2 Add Purchase Dialog

**File**: `src/ui/dialogs/add_purchase_dialog.py` (NEW)

**Pattern**: Similar to `add_inventory_dialog.py` (F029)

```python
class AddPurchaseDialog(ctk.CTkToplevel):
    """Dialog for adding new purchase."""
    
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        
        self.on_save_callback = on_save_callback
        
        # Create fields
        self.product_dropdown = TypeAheadComboBox(...)
        self.purchase_date_entry = ctk.CTkEntry(...)
        self.quantity_entry = ctk.CTkEntry(...)
        self.unit_price_entry = ctk.CTkEntry(...)
        self.supplier_dropdown = ctk.CTkComboBox(...)
        self.notes_text = ctk.CTkTextbox(...)
        
        # Bind events
        self.product_dropdown.bind("<<ComboboxSelected>>", self._on_product_selected)
        
    def _on_product_selected(self, event):
        """Auto-fill price from last purchase."""
        
    def _validate(self):
        """Validate all fields."""
        
    def _save(self):
        """Create purchase via service."""
```

### 5.3 Integration with Purchase Dashboard

**File**: `src/ui/dashboards/purchase_dashboard.py`

**Change**: Add Purchases tab to dashboard

```python
class PurchaseDashboard(BaseDashboard):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Create tab view
        self.tabview = ctk.CTkTabview(self.content_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # Add tabs
        self.inventory_tab = self.tabview.add("Inventory")
        self.purchases_tab = self.tabview.add("Purchases")  # NEW
        self.shopping_lists_tab = self.tabview.add("Shopping Lists")
        
        # Create tab content
        from src.ui.inventory_tab import InventoryTab
        from src.ui.tabs.purchases_tab import PurchasesTab  # NEW
        
        self.inventory = InventoryTab(self.inventory_tab)
        self.purchases = PurchasesTab(self.purchases_tab)  # NEW
```

---

## 6. Functional Requirements

### 6.1 Purchase List View

**REQ-F043-001:** Purchases tab SHALL display all purchases in descending date order
**REQ-F043-002:** List SHALL show: date, product, supplier, qty, unit price, total, remaining
**REQ-F043-003:** List SHALL expand to fill 70-80% of vertical space (20+ rows)
**REQ-F043-004:** Columns SHALL be sortable by clicking header

### 6.2 Filters

**REQ-F043-005:** Date range filter SHALL support: last 30 days, 90 days, 1 year, all time
**REQ-F043-006:** Supplier filter SHALL show all suppliers + "All" option
**REQ-F043-007:** Search bar SHALL filter by product name (fuzzy match)
**REQ-F043-008:** Filters SHALL update list view immediately

### 6.3 Add Purchase

**REQ-F043-009:** [Add Purchase] button SHALL open Add Purchase dialog
**REQ-F043-010:** Dialog SHALL require: product, date, quantity, unit price, supplier
**REQ-F043-011:** Dialog SHALL auto-fill unit price from most recent purchase
**REQ-F043-012:** Dialog SHALL default supplier to product's preferred_supplier
**REQ-F043-013:** Dialog SHALL validate: date not future, quantity > 0, price ≥ 0
**REQ-F043-014:** On save, SHALL create Purchase + InventoryItem records
**REQ-F043-015:** On save, SHALL refresh purchase list

### 6.4 Edit Purchase

**REQ-F043-016:** Edit Purchase dialog SHALL allow editing: date, quantity, price, supplier, notes
**REQ-F043-017:** Edit Purchase dialog SHALL block editing product (read-only)
**REQ-F043-018:** Edit SHALL validate new quantity ≥ consumed quantity
**REQ-F043-019:** Edit SHALL recalculate FIFO costs if price/quantity changed
**REQ-F043-020:** Edit SHALL show preview of changes before saving

### 6.5 Delete Purchase

**REQ-F043-021:** Delete SHALL validate purchase not consumed (block if depletions exist)
**REQ-F043-022:** Delete SHALL show confirmation dialog if allowed
**REQ-F043-023:** Delete SHALL show error with usage details if blocked
**REQ-F043-024:** Delete SHALL cascade to InventoryItem records
**REQ-F043-025:** Delete SHALL refresh purchase list

### 6.6 View Details

**REQ-F043-026:** View Details SHALL show purchase info + inventory tracking
**REQ-F043-027:** View Details SHALL show usage history (depletions with recipes)
**REQ-F043-028:** View Details SHALL calculate remaining inventory (FIFO)
**REQ-F043-029:** View Details SHALL provide [Edit Purchase] quick action

---

## 7. Non-Functional Requirements

### 7.1 Usability

**REQ-F043-NFR-001:** Purchase list SHALL load in <500ms for 100 purchases
**REQ-F043-NFR-002:** Filters SHALL update list in <200ms
**REQ-F043-NFR-003:** Add Purchase SHALL pre-fill intelligently (recent products, last price)
**REQ-F043-NFR-004:** Error messages SHALL be specific and actionable

### 7.2 Data Integrity

**REQ-F043-NFR-005:** Edit/Delete SHALL preserve FIFO integrity
**REQ-F043-NFR-006:** Purchase creation SHALL be atomic (Purchase + InventoryItem together)
**REQ-F043-NFR-007:** Validation SHALL prevent data corruption (negative inventory, etc.)

### 7.3 Consistency

**REQ-F043-NFR-008:** Add Purchase dialog SHALL match "Add to Pantry" backend behavior
**REQ-F043-NFR-009:** Purchase list layout SHALL match Inventory tab layout (filters, columns)
**REQ-F043-NFR-010:** Keyboard shortcuts SHALL work (Delete key, Ctrl+N for new)

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Purchase Service**:
```python
def test_get_purchase_history_filters():
    """Test purchase history with date/supplier filters."""
    
def test_calculate_remaining_inventory():
    """Test FIFO remaining calculation."""
    
def test_can_edit_purchase_validation():
    """Test edit validation (consumed quantity check)."""
    
def test_can_delete_purchase_validation():
    """Test delete validation (blocks if consumed)."""
```

### 8.2 Integration Tests

**Purchase Workflow**:
```python
def test_add_purchase_creates_inventory():
    """Test Purchase + InventoryItem creation."""
    
def test_edit_purchase_recalculates_costs():
    """Test FIFO cost recalculation on edit."""
    
def test_delete_purchase_removes_inventory():
    """Test cascade delete."""
    
def test_delete_purchase_blocks_if_consumed():
    """Test deletion blocked when inventory used."""
```

### 8.3 User Acceptance Tests

**UAT-001: Add Purchase**
```
Given: User opens Purchases tab
When: User clicks [Add Purchase]
And: Selects product "King Arthur AP Flour 25lb"
And: Enters quantity 1, price $15.99, supplier Costco
And: Clicks [Add Purchase]
Then: Purchase appears in list
And: Inventory tab shows +10 cups flour
```

**UAT-002: Edit Purchase**
```
Given: User has purchase with typo ($1.99 should be $19.99)
When: User opens Purchases tab
And: Selects purchase
And: Clicks [Edit]
And: Changes price to $19.99
And: Clicks [Save]
Then: Purchase updated in list
And: Total cost recalculated
And: FIFO costs updated
```

**UAT-003: Delete Consumed Purchase (Blocked)**
```
Given: User has purchase partially consumed (5 cups used)
When: User selects purchase
And: Clicks [Delete]
Then: Error dialog shows "Cannot delete - 5 cups already used"
And: Purchase NOT deleted
```

**UAT-004: Delete Unused Purchase (Allowed)**
```
Given: User has purchase not consumed (0 cups used)
When: User selects purchase
And: Clicks [Delete]
And: Confirms deletion
Then: Purchase removed from list
And: Inventory item removed
```

---

## 9. Implementation Phases

### Phase 1: Purchases Tab UI (High Priority)
**Effort:** 4-5 hours

**Scope:**
- Create `purchases_tab.py`
- Purchase list view with columns
- Filters (date range, supplier, search)
- Grid expansion (20+ rows visible)
- Integration with purchase_dashboard.py

**Deliverables:**
- ✓ Purchases tab visible in PURCHASE mode
- ✓ Purchase list displays existing purchases
- ✓ Filters functional

### Phase 2: Add Purchase Dialog (High Priority)
**Effort:** 3-4 hours

**Scope:**
- Create `add_purchase_dialog.py`
- Product dropdown with type-ahead
- Auto-fill price from last purchase
- Validation (date, quantity, price)
- Create Purchase + InventoryItem

**Deliverables:**
- ✓ [Add Purchase] button opens dialog
- ✓ Dialog creates purchase + inventory
- ✓ List refreshes after save

### Phase 3: Edit Purchase Dialog (Medium Priority)
**Effort:** 2-3 hours

**Scope:**
- Create `edit_purchase_dialog.py`
- Pre-fill fields from existing purchase
- Block editing product
- Validate consumed quantity
- Recalculate FIFO costs

**Deliverables:**
- ✓ Edit dialog functional
- ✓ FIFO costs recalculated correctly
- ✓ Validation prevents invalid edits

### Phase 4: Delete Purchase (Medium Priority)
**Effort:** 2-3 hours

**Scope:**
- Delete validation (check depletions)
- Confirmation dialog
- Error dialog with usage details
- Cascade delete to inventory

**Deliverables:**
- ✓ Delete blocks if consumed
- ✓ Delete succeeds if unused
- ✓ Error messages specific

### Phase 5: View Details Dialog (Low Priority)
**Effort:** 2-3 hours

**Scope:**
- Create `purchase_details_dialog.py`
- Show purchase info + inventory tracking
- Show usage history (depletions)
- Quick [Edit Purchase] action

**Deliverables:**
- ✓ View Details functional
- ✓ Usage history accurate
- ✓ FIFO tracking correct

### Total Effort Estimate
**12-16 hours** (1.5-2 working days)

---

## 10. Success Criteria

**Must Have:**
- [ ] Purchases tab visible in PURCHASE mode (between Inventory and Shopping Lists)
- [ ] Purchase list shows 20+ rows with all columns
- [ ] Filters work: date range, supplier, search
- [ ] [Add Purchase] creates Purchase + InventoryItem
- [ ] Edit Purchase allows fixing typos (date/price/qty)
- [ ] Delete Purchase blocks if consumed, succeeds if unused
- [ ] "Remaining" column shows FIFO-tracked inventory

**Should Have:**
- [ ] Add Purchase auto-fills price from last purchase
- [ ] Add Purchase defaults supplier to preferred_supplier
- [ ] Edit Purchase shows preview of changes
- [ ] Delete Purchase shows specific error with usage details
- [ ] View Details shows usage history

**Nice to Have:**
- [ ] Keyboard shortcuts (Ctrl+N for new, Delete for delete)
- [ ] Context menu on right-click
- [ ] Double-click to view details
- [ ] Column sorting by clicking header

---

## 11. Architecture Alignment

### 11.1 Purchase → Inventory Flow

**Correct**:
```
Purchase (transaction) → InventoryItem (current state)
- Purchases drive inventory
- Inventory is a derived view
- AI uploads target Purchase table
```

**Purchases Tab** establishes this as the primary workflow.

### 11.2 Dual Entry Points

**Purchases tab**: Primary (new purchases, normal workflow)
**Inventory tab**: Secondary (corrections, manual adjustments)

Both create same backend records (Purchase + InventoryItem), but **Purchases tab is conceptually primary**.

### 11.3 AI Integration Ready

**BT Mobile** (current): Uploads JSON → Purchase table → Inventory auto-updates
**Voice/Chat** (future): API creates Purchase → Inventory auto-updates

**Purchases tab** is the canonical UI view regardless of entry method.

---

## 12. Future Enhancements (Out of Scope)

**Multi-Item Purchase** (F043.5):
- Add multiple products in single dialog (shopping trip mode)
- Batch create purchases with shared date/supplier

**Quick Re-Order** (F044):
- [Re-Order] button on purchase row
- Pre-fills Add Purchase dialog with same product/supplier

**Price Alerts** (F0XX):
- Show price trends in list ("↑ 15% vs last purchase")
- Alert when price significantly higher than average

**Budget Tracking** (F0XX):
- Monthly spending by supplier
- Category spending analysis
- Export to CSV for budget software

---

## 13. Relationship to Other Features

**F028 (Purchase Tracking ✅)**: Provides Purchase model and service layer
**F029 (Streamlined Inventory Entry ✅)**: Provides "Add to Pantry" (dual entry point)
**F042 (UI Polish ✅)**: Establishes header/filter/grid layout patterns
**F046 (Shopping Lists)**: Will reference purchase history for recommendations
**F047 (Assembly Workflows)**: Will consume inventory created by purchases

---

## 14. Constitutional Compliance

**Principle I (User-Centric Design):**
- ✓ Purchases tab matches real-world workflow (buy ingredients → track spending)
- ✓ Filters match user mental model (date, supplier, search)
- ✓ Validation prevents user errors (delete consumed purchases)

**Principle V (Layered Architecture):**
- ✓ Service methods in PurchaseService (not UI)
- ✓ UI calls service, doesn't do business logic
- ✓ Existing models reused (no schema changes)

**Principle VII (Pragmatic Aspiration):**
- ✓ Desktop-native UI patterns (CustomTkinter)
- ✓ Web-ready: Purchase service methods are API-ready
- ✓ AI-ready: Purchase table is canonical for all entry methods

---

## 15. Related Documents

- **Requirements:** `docs/requirements/req_inventory.md` Section 3.1 (Purchase Management)
- **Dependencies:** `docs/func-spec/F028_purchase_tracking_enhanced_costing.md` (Purchase model)
- **Dependencies:** `docs/func-spec/F029_streamlined_inventory_entry.md` (Add to Pantry dialog)
- **Dependencies:** `docs/func-spec/F042_ui_polish_layout_fixes.md` (UI layout patterns)
- **Feature Roadmap:** `docs/feature_roadmap.md` (F043-F047 sequence)
- **Constitution:** `.kittify/memory/constitution.md` (User-centric design)

---

**END OF SPECIFICATION**
