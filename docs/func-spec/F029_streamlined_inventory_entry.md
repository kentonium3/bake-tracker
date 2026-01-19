# Feature 029: Streamlined Inventory Entry

**Created:** 2025-12-22  
**Status:** DESIGN  
**Priority:** HIGH  
**Complexity:** HIGH

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, schema definitions, service method signatures, and UI mockups. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification
  - Test-driven development requirements

**The requirements and business logic are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Problem Statement

Current inventory entry workflow creates significant friction for the primary use case: adding 20+ items after a shopping trip.

**User Testing Pain Points:**
1. **Too many clicks:** 4-5 dropdown selections + data entry per item = 100+ interactions for shopping trip
2. **Long ingredient list:** 20 categories, hundreds of ingredients → scrolling/searching friction
3. **No memory:** Must manually select "Costco" 20 times in a row for same shopping trip
4. **Product creation friction:** Modal switching breaks flow when product doesn't exist in catalog
5. **Price recall difficulty:** "What did I pay last time?" requires mental effort or external notes
6. **No intelligence:** System doesn't learn from usage patterns (frequently used items buried in long lists)

**Real-World Example:**
> Marianne shops at Costco, buys 20 baking items. Current workflow: Select Category (Baking) → Select Ingredient (scroll through 50 options) → Select Product (dropdown shows "no products" → exit dialog → create product in Products tab → return to inventory) → Select Supplier (Costco for 20th time) → Enter Price (guess or check receipt) → Enter Quantity. Total: 15-20 minutes for data entry. **Target: 5 minutes.**

**Blocking User Testing:**
Without efficient inventory entry, realistic price data cannot be populated quickly enough to validate production/event workflows.

---

## Solution Overview

Transform inventory entry from tedious data entry into intelligent, flow-optimized experience using enhanced ingredient-first workflow with type-ahead, recency ranking, session memory, and inline product creation.

**Core Workflow:**
```
Category [type-ahead] → Ingredient [type-ahead, recent first] 
→ Product [type-ahead, recent ⭐] → Supplier [session default ⭐] 
→ Price [auto-suggested] → Quantity → Add
```

**Key Innovations:**

1. **Type-Ahead Filtering:** Type "bak" → "Baking" auto-completes. Type "ap" → "All-Purpose Flour" appears. Reduces scrolling/searching.

2. **Recency Intelligence:** Frequently/recently used items marked with ⭐ and sorted to top. "I always buy Gold Medal flour" → appears first.

3. **Session Memory:** Last supplier/category remembered during data entry session. Add 20 Costco items → select Costco once.

4. **Inline Product Creation:** Product doesn't exist? Click [+ New Product], fill minimal fields, continue workflow. No modal switching.

5. **Smart Defaults:** Baking ingredients default to "lb", chocolate to "oz". Price pre-fills from last purchase at supplier.

**Design Principle:** Optimize for the common case (adding many items from one shopping trip at one supplier) while maintaining flexibility for edge cases.

---

## Scope

### In Scope

**Type-Ahead Dropdowns:**
- Category dropdown with type-ahead (1-char threshold, contains matching)
- Ingredient dropdown with type-ahead (2-char threshold, category-filtered, recent items first)
- Product dropdown with type-ahead (2-char threshold, ingredient-filtered, recent items marked ⭐)
- Supplier dropdown (standard alphabetical, no type-ahead - only ~10-20 suppliers expected)

**Recency Intelligence:**
- Recency definition: Last 30 days OR 3+ uses in last 90 days (hybrid temporal + frequency)
- Products: ⭐ marker for recent items, sorted to top within ingredient filter
- Ingredients: Recent items sorted to top within category filter
- Recency queries: `get_recent_products()`, `get_recent_ingredients()` service methods
- Cache recency results during session (refresh on successful Add)

**Session-Based Memory:**
- Last-used supplier persists for app lifetime (reset on restart)
- Last-selected category persists for app lifetime (reset on restart)
- Supplier pre-selected with ⭐ visual indicator
- Category pre-selected (no indicator needed)
- Session updates only on successful Add (not on cancel/browse)
- Session state stored in memory (not persisted to database)

**Inline Product Creation:**
- [+ New Product] button next to product dropdown
- [+ Create New Product] option at bottom of product dropdown list
- Both trigger same collapsible accordion form within dialog
- Form expands/collapses without dialog resize
- Pre-filled fields:
  - Ingredient: From current selection (read-only, gray text)
  - Preferred Supplier: From session memory (editable, ⭐ if session default)
  - Package Unit: Smart default based on ingredient category (editable)
- Required fields: Product Name, Package Unit, Package Quantity
- On Create: New product appears in dropdown, auto-selected, dialog continues to supplier/price

**Smart Defaults & Validation:**
- Category→Unit mapping (configurable):
  ```
  Baking → lb (flour, sugar, etc.)
  Chocolate → oz (chips, bars)
  Dairy → lb (butter), fl oz (milk)
  Spices → oz
  Liquids → fl oz
  ```
- Price validation: Warn if >$100 ("⚠️ Price is $100+. Confirm this is correct?")
- Quantity validation: Warn if decimal for count-based units ("Package quantities are usually whole numbers. Continue?")
- Silent failure on suggestion query errors (blank field, log error for debugging)

**Enhanced Price Display:**
- Inline hint: "(last paid: $X.XX on MM/DD)" when supplier selected
- Fallback hint: "(last paid: $X.XX at [Supplier] on MM/DD)" when different supplier
- Price field editable (user can override suggestion)
- Future enhancement: Tooltip on hover showing last 3-5 purchases (deferred to post-MVP)

**UI/UX Improvements:**
- Tab navigation through all fields in logical order
- Enter key behavior: Context-aware (Entry field→advance, Dropdown→select, Button→activate)
- Escape key: Cancel/close dialog, collapse accordion if expanded
- Visual field grouping (subtle borders/spacing)
- Consistent type-ahead behavior across Category/Ingredient/Product
- Zero products edge case: "[+ Create First Product]" button prominently displayed

### Out of Scope

**Deferred to Post-MVP:**
- Purchase history tooltip (hover shows last 3-5 purchases with details)
- Keyboard shortcuts (Ctrl+N for new product, etc.)
- Configuration UI for category→unit mappings (edit config file for now)
- Loading indicators during recency queries (optimize first, add indicators if needed)
- Visual field grouping with explicit separators/borders (subtle spacing sufficient for MVP)

**Future Features (Web Phase / Later):**
- Bulk entry mode (CSV import with preview/validation)
- Voice input for hands-free data entry
- Barcode scanning integration (mobile app)
- Auto-categorization from product name (AI-powered)
- Multi-step wizard alternative to single dialog
- Purchase history charts/visualizations
- Undo/redo functionality
- Real-time collaborative editing (multi-user web)
- Suggested corrections based on usage patterns

---

## Technical Design

### Service Layer

#### New Recency Queries (in product_service.py or new recency_service.py)

```python
"""
Recency intelligence for inventory entry optimization.

Identifies products and ingredients that are "recent" based on usage patterns,
enabling smart sorting and ⭐ markers in UI dropdowns.
"""

from typing import List, Set
from datetime import date, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from src.models import InventoryAddition, Product, Ingredient
from src.database import session_scope


def get_recent_products(
    ingredient_id: int,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None
) -> List[int]:
    """
    Get product IDs that are "recent" for an ingredient.
    
    Recency definition (hybrid):
    - Temporal: Added within last 'days' days
    - Frequency: Added 'min_frequency' or more times in last 'frequency_days' days
    - Product is recent if EITHER condition true
    
    Args:
        ingredient_id: Ingredient to filter products for
        days: Temporal threshold (default 30)
        min_frequency: Frequency threshold (default 3)
        frequency_days: Frequency window (default 90)
        limit: Max results (default 20)
        session: Optional database session
        
    Returns:
        List of product IDs sorted by most recent addition date
        
    Example:
        # Product A: Added yesterday → Recent (temporal)
        # Product B: Added 45 days ago, but 5 times in last 90 days → Recent (frequency)
        # Product C: Added 45 days ago, only 2 times → Not recent
    """
    if session is not None:
        return _get_recent_products_impl(
            ingredient_id, days, min_frequency, frequency_days, limit, session
        )
    
    with session_scope() as session:
        return _get_recent_products_impl(
            ingredient_id, days, min_frequency, frequency_days, limit, session
        )


def _get_recent_products_impl(
    ingredient_id: int,
    days: int,
    min_frequency: int,
    frequency_days: int,
    limit: int,
    session: Session
) -> List[int]:
    """Implementation using provided session."""
    
    today = date.today()
    temporal_cutoff = today - timedelta(days=days)
    frequency_cutoff = today - timedelta(days=frequency_days)
    
    # Temporal: Products added within last N days
    temporal_products = session.query(
        InventoryAddition.product_id,
        func.max(InventoryAddition.addition_date).label('last_addition')
    ).filter(
        and_(
            InventoryAddition.ingredient_id == ingredient_id,
            InventoryAddition.product_id.isnot(None),
            InventoryAddition.addition_date >= temporal_cutoff
        )
    ).group_by(InventoryAddition.product_id).subquery()
    
    # Frequency: Products added min_frequency+ times in last frequency_days
    frequency_products = session.query(
        InventoryAddition.product_id,
        func.max(InventoryAddition.addition_date).label('last_addition')
    ).filter(
        and_(
            InventoryAddition.ingredient_id == ingredient_id,
            InventoryAddition.product_id.isnot(None),
            InventoryAddition.addition_date >= frequency_cutoff
        )
    ).group_by(InventoryAddition.product_id).having(
        func.count(InventoryAddition.id) >= min_frequency
    ).subquery()
    
    # Union: Products that meet EITHER criteria
    # Using Python set union for simplicity (could use SQL UNION for larger datasets)
    temporal_ids = {row.product_id: row.last_addition for row in session.query(temporal_products).all()}
    frequency_ids = {row.product_id: row.last_addition for row in session.query(frequency_products).all()}
    
    # Merge, keeping most recent addition date
    recent_products = {}
    for pid, date in temporal_ids.items():
        recent_products[pid] = date
    for pid, date in frequency_ids.items():
        if pid in recent_products:
            recent_products[pid] = max(recent_products[pid], date)
        else:
            recent_products[pid] = date
    
    # Sort by most recent addition date, limit results
    sorted_products = sorted(recent_products.items(), key=lambda x: x[1], reverse=True)
    return [pid for pid, _ in sorted_products[:limit]]


def get_recent_ingredients(
    category: str,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None
) -> List[int]:
    """
    Get ingredient IDs that are "recent" for a category.
    
    Same recency logic as products, but for ingredients within a category.
    
    Args:
        category: Ingredient category to filter
        days: Temporal threshold (default 30)
        min_frequency: Frequency threshold (default 3)
        frequency_days: Frequency window (default 90)
        limit: Max results (default 20)
        session: Optional database session
        
    Returns:
        List of ingredient IDs sorted by most recent addition date
    """
    if session is not None:
        return _get_recent_ingredients_impl(
            category, days, min_frequency, frequency_days, limit, session
        )
    
    with session_scope() as session:
        return _get_recent_ingredients_impl(
            category, days, min_frequency, frequency_days, limit, session
        )


def _get_recent_ingredients_impl(
    category: str,
    days: int,
    min_frequency: int,
    frequency_days: int,
    limit: int,
    session: Session
) -> List[int]:
    """Implementation using provided session."""
    
    today = date.today()
    temporal_cutoff = today - timedelta(days=days)
    frequency_cutoff = today - timedelta(days=frequency_days)
    
    # Get ingredients in category
    category_ingredients = session.query(Ingredient.id).filter(
        Ingredient.category == category
    ).subquery()
    
    # Temporal: Ingredients added within last N days
    temporal_ingredients = session.query(
        InventoryAddition.ingredient_id,
        func.max(InventoryAddition.addition_date).label('last_addition')
    ).filter(
        and_(
            InventoryAddition.ingredient_id.in_(category_ingredients),
            InventoryAddition.addition_date >= temporal_cutoff
        )
    ).group_by(InventoryAddition.ingredient_id).subquery()
    
    # Frequency: Ingredients added min_frequency+ times in last frequency_days
    frequency_ingredients = session.query(
        InventoryAddition.ingredient_id,
        func.max(InventoryAddition.addition_date).label('last_addition')
    ).filter(
        and_(
            InventoryAddition.ingredient_id.in_(category_ingredients),
            InventoryAddition.addition_date >= frequency_cutoff
        )
    ).group_by(InventoryAddition.ingredient_id).having(
        func.count(InventoryAddition.id) >= min_frequency
    ).subquery()
    
    # Union using Python set merge
    temporal_ids = {row.ingredient_id: row.last_addition for row in session.query(temporal_ingredients).all()}
    frequency_ids = {row.ingredient_id: row.last_addition for row in session.query(frequency_ingredients).all()}
    
    recent_ingredients = {}
    for iid, date in temporal_ids.items():
        recent_ingredients[iid] = date
    for iid, date in frequency_ids.items():
        if iid in recent_ingredients:
            recent_ingredients[iid] = max(recent_ingredients[iid], date)
        else:
            recent_ingredients[iid] = date
    
    # Sort by most recent, limit
    sorted_ingredients = sorted(recent_ingredients.items(), key=lambda x: x[1], reverse=True)
    return [iid for iid, _ in sorted_ingredients[:limit]]


def is_product_recent(
    product_id: int,
    ingredient_id: int,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    session: Optional[Session] = None
) -> bool:
    """
    Check if a single product is recent (for ⭐ marker logic).
    
    More efficient than get_recent_products when checking single product.
    
    Args:
        product_id: Product to check
        ingredient_id: Ingredient context
        days: Temporal threshold
        min_frequency: Frequency threshold
        frequency_days: Frequency window
        session: Optional database session
        
    Returns:
        True if product meets recency criteria
    """
    recent_products = get_recent_products(
        ingredient_id=ingredient_id,
        days=days,
        min_frequency=min_frequency,
        frequency_days=frequency_days,
        session=session
    )
    
    return product_id in recent_products
```

#### Session State Management

```python
"""
Session state management for user preferences during data entry.

Persists for application lifetime, resets on restart.
Not stored in database - in-memory only.
"""


class SessionState:
    """
    Application session state for inventory entry workflow.
    
    Stores user's last selections to reduce repetitive data entry
    during bulk inventory addition (e.g., shopping trip).
    
    Singleton pattern: One instance per application session.
    
    Attributes:
        last_supplier_id: ID of last supplier selected (None if not set)
        last_category: Last category selected (None if not set)
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(SessionState, cls).__new__(cls)
            cls._instance.last_supplier_id = None
            cls._instance.last_category = None
        return cls._instance
    
    def update_supplier(self, supplier_id: int):
        """
        Update last-used supplier.
        
        Call this ONLY on successful inventory addition.
        Do not call on browse/cancel/dialog close.
        
        Args:
            supplier_id: Supplier ID to remember
        """
        self.last_supplier_id = supplier_id
    
    def update_category(self, category: str):
        """
        Update last-selected category.
        
        Call this ONLY on successful inventory addition.
        
        Args:
            category: Category name to remember
        """
        self.last_category = category
    
    def get_last_supplier_id(self) -> Optional[int]:
        """Get last-used supplier ID (None if not set)."""
        return self.last_supplier_id
    
    def get_last_category(self) -> Optional[str]:
        """Get last-selected category (None if not set)."""
        return self.last_category
    
    def reset(self):
        """
        Clear session state.
        
        Call this on application shutdown.
        """
        self.last_supplier_id = None
        self.last_category = None
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"SessionState(supplier_id={self.last_supplier_id}, "
            f"category='{self.last_category}')"
        )


# Global session state instance
session_state = SessionState()
```

#### Category→Unit Default Mapping

```python
"""
Smart defaults for package units based on ingredient category.

Configurable mapping to reduce data entry friction.
Users can override all defaults.
"""

# Category to default package unit mapping
CATEGORY_DEFAULT_UNITS = {
    'Baking': 'lb',          # Flour, sugar, etc.
    'Chocolate': 'oz',       # Chips, bars, cocoa
    'Dairy': 'lb',           # Butter (default to weight, handle milk separately)
    'Spices': 'oz',          # Small quantities
    'Liquids': 'fl oz',      # Extracts, oils
    'Nuts': 'lb',            # Almonds, walnuts
    'Fruits': 'lb',          # Dried fruits
    'Sweeteners': 'lb',      # Honey, syrups (weight for consistency)
    'Leavening': 'oz',       # Baking powder, baking soda
    'Oils': 'fl oz',         # Vegetable oil, olive oil
    'Grains': 'lb',          # Oats, rice flour
    'Misc': 'lb',            # Default fallback
}

def get_default_unit_for_category(category: str) -> str:
    """
    Get default package unit for an ingredient category.
    
    Args:
        category: Ingredient category name
        
    Returns:
        Default unit string (e.g., 'lb', 'oz', 'fl oz')
        Returns 'lb' as fallback if category not found
    """
    return CATEGORY_DEFAULT_UNITS.get(category, 'lb')


def get_default_unit_for_ingredient(ingredient: Ingredient) -> str:
    """
    Get default package unit for a specific ingredient.
    
    Wrapper around get_default_unit_for_category for convenience.
    
    Args:
        ingredient: Ingredient model instance
        
    Returns:
        Default unit string
    """
    return get_default_unit_for_category(ingredient.category)
```

---

## UI Implementation

### Enhanced Add Inventory Dialog

#### Complete Layout Wireframe

```
┌────────────────────────────────────────────────────────────┐
│ Add Inventory Item                                  [× Close] │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ Category:       [⭐ Baking_________________ ▼]             │
│                  ↑ Type "bak" to filter (1 char min)       │
│                  ↑ Pre-selected from session               │
│                                                             │
│ Ingredient:     [All-Purpose Flour_________ ▼]             │
│                  ↑ Type "ap" to filter (2 char min)        │
│                  ↑ Filtered by category (Baking only)      │
│                  ↑ Recent items appear first with ⭐       │
│                                                             │
│ Product:        [⭐ Gold Medal AP 10lb_____ ▼] [+ New]     │
│                  ↑ Type "gold" to filter (2 char min)      │
│                  ↑ Filtered by ingredient (AP Flour only)  │
│                  ↑ Recent items appear first with ⭐       │
│                                                             │
│ ┌─ Create New Product ─────────────────────────────────┐  │
│ │ ▼ Click to collapse                                  │  │
│ │                                                       │  │
│ │ Ingredient:       All-Purpose Flour (read-only)      │  │
│ │                                                       │  │
│ │ Product Name:     [_________________________]        │  │
│ │                                                       │  │
│ │ Package Unit:     [lb ▼]  Package Qty: [____]        │  │
│ │                    ↑ Smart default from category     │  │
│ │                                                       │  │
│ │ Preferred Supplier: [⭐ Costco Waltham MA ▼]         │  │
│ │                      ↑ Pre-filled from session       │  │
│ │                                                       │  │
│ │                       [Cancel]  [Create Product]     │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ Supplier:       [⭐ Costco Waltham MA______ ▼]             │
│                  ↑ Pre-selected from session with ⭐       │
│                  ↑ Alphabetically sorted                   │
│                                                             │
│ Price:          [$8.99]                                    │
│                 (last paid: $8.50 on 11/15) 🛈             │
│                  ↑ Auto-suggested from last purchase       │
│                  ↑ Editable by user                        │
│                  ↑ Hover 🛈 for purchase history (future)  │
│                                                             │
│ Quantity:       [2]                                        │
│                                                             │
│ Notes:          [______________________________]           │
│                                                             │
│                               [Cancel]  [Add Inventory]    │
└────────────────────────────────────────────────────────────┘
```

#### Dialog Behavior Specification

**On Dialog Open:**
1. Load session state: `session_state.get_last_category()`, `session_state.get_last_supplier_id()`
2. If last category exists: Pre-select in Category dropdown
3. If last supplier exists: Pre-select in Supplier dropdown, add ⭐ prefix
4. Load all categories for Category dropdown (alphabetically sorted)
5. Ingredient dropdown disabled until category selected
6. Product dropdown disabled until ingredient selected
7. Inline product creation form collapsed (hidden)

**On Category Selected:**
1. Filter ingredients by selected category
2. Query recent ingredients: `get_recent_ingredients(category)`
3. Build ingredient dropdown:
   - Recent ingredients first (with ⭐ prefix)
   - Separator line: "─────────────"
   - Non-recent ingredients alphabetically
4. Enable ingredient dropdown
5. Clear ingredient selection (if switching categories)
6. Disable product dropdown

**On Ingredient Typed (Type-Ahead):**
1. Wait for 2 characters typed
2. Filter dropdown values to items containing typed text (case-insensitive)
3. Word boundary matches prioritized (e.g., "ap" matches "AP Flour" before "Maple Syrup")
4. Show filtered results in real-time
5. If only one match, auto-select on Enter key

**On Ingredient Selected:**
1. Filter products by selected ingredient
2. Query recent products: `get_recent_products(ingredient_id)`
3. Build product dropdown:
   - Recent products first (with ⭐ prefix)
   - Separator line: "─────────────"
   - Non-recent products alphabetically
   - "[+ Create New Product]" at bottom
4. Enable product dropdown
5. Clear product selection (if switching ingredients)
6. Check product count:
   - If 0 products: Show prominent "[+ Create First Product]" button
   - If products exist: Normal dropdown

**On Product Typed (Type-Ahead):**
1. Wait for 2 characters typed
2. Filter dropdown values (same logic as ingredient)
3. Show filtered results
4. Auto-select on Enter if single match

**On Product Selected:**
1. Product selected from dropdown (not inline creation)
2. Enable supplier dropdown (if not already enabled)
3. If supplier already selected: Trigger price suggestion query

**On [+ New Product] Clicked:**
1. Expand inline product creation form (accordion animation)
2. Pre-fill Ingredient field (read-only, from current selection)
3. Pre-fill Preferred Supplier (from session state, editable)
4. Pre-fill Package Unit (from `get_default_unit_for_category()`, editable)
5. Focus on Product Name field
6. Disable main Product dropdown (force user to complete or cancel inline creation)

**On Create Product (Inline Form):**
1. Validate required fields: Product Name, Package Unit, Package Quantity
2. Call `product_service.create_product()` with:
   - name = entered product name
   - ingredient_id = from current selection
   - package_unit = from dropdown
   - package_unit_quantity = from entry
   - preferred_supplier_id = from dropdown
3. On success:
   - Add new product to Product dropdown (at top, with ⭐)
   - Auto-select new product
   - Collapse inline creation form
   - Re-enable main Product dropdown
   - Continue workflow (enable supplier dropdown)
4. On error:
   - Show error message in inline form
   - Keep form expanded for correction

**On Cancel (Inline Form):**
1. Clear inline form fields
2. Collapse accordion
3. Re-enable main Product dropdown
4. Focus returns to Product dropdown

**On Supplier Selected:**
1. Query price suggestion: `get_last_purchase_price(product_id, supplier_id)`
2. If price found:
   - Pre-fill Price field
   - Query last purchase date from purchase history (limit=1)
   - Display hint: "(last paid: $X.XX on MM/DD)"
3. If no price at this supplier:
   - Query fallback: `get_last_purchase_price_any_supplier(product_id)`
   - If found from different supplier:
     - Pre-fill Price field
     - Display hint: "(last paid: $X.XX at [Supplier] on MM/DD)"
   - If no price history at all:
     - Leave Price blank
     - Display hint: "(no purchase history)"
4. Enable Price field (always editable)

**On Price Changed (Manual Entry):**
1. Remove hint text (user's value is intentional)
2. Validate on blur:
   - If >$100: Show warning dialog ("⚠️ Price is $100+. Confirm this is correct?")
   - If user confirms: Accept value
   - If user cancels: Focus returns to Price field for correction
3. If negative: Show error ("Price cannot be negative")

**On Quantity Changed:**
1. If product has count-based unit (e.g., "count", "bag", "box"):
   - Check if decimal entered (e.g., 1.5)
   - Show warning: "Package quantities are usually whole numbers. Continue?"
   - If user confirms: Accept value
   - If user cancels: Focus returns to Quantity field

**On Add Inventory Clicked:**
1. Validate all required fields populated
2. Call `inventory_service.add_inventory()` with all parameters
3. On success:
   - Update session state: `session_state.update_supplier(supplier_id)`, `session_state.update_category(category)`
   - Clear all fields EXCEPT category and supplier (session memory)
   - Focus returns to Ingredient dropdown (ready for next item)
   - Show brief success indicator (green checkmark, 1 second fade)
4. On error:
   - Show error dialog
   - Keep dialog open with entered data for correction

**On Cancel / Escape / Close:**
1. Do NOT update session state (no changes on cancel)
2. Close dialog
3. Return to inventory tab

**Tab Navigation Order:**
```
Category → Ingredient → Product → [+ New] button 
→ Supplier → Price → Quantity → Notes → [Add] button → [Cancel] button
```

**Enter Key Behavior:**
```
- Entry field (Category, Ingredient, Product typed): Advance to next field
- Dropdown (selecting from list): Select item, advance to next field
- Button ([+ New], [Add], [Cancel]): Activate button
- Price/Quantity field: Advance to next field
```

**Escape Key Behavior:**
```
- Inline form expanded: Collapse form, cancel creation
- Inline form collapsed: Close dialog
```

---

## Implementation Details

### Type-Ahead ComboBox Implementation

```python
class TypeAheadComboBox(ctk.CTkComboBox):
    """
    Enhanced CTkComboBox with type-ahead filtering.
    
    Features:
    - Real-time filtering as user types
    - Minimum character threshold before filtering
    - Contains matching with word boundary priority
    - Preserves full values list for reset
    """
    
    def __init__(
        self,
        master,
        values: List[str],
        min_chars: int = 2,
        **kwargs
    ):
        super().__init__(master, values=values, **kwargs)
        
        self.full_values = values  # Preserve original list
        self.min_chars = min_chars
        self.filtered = False
        
        # Bind to key release for type-ahead
        self._entry.bind('<KeyRelease>', self._on_key_release)
        self._entry.bind('<FocusOut>', self._on_focus_out)
    
    def _on_key_release(self, event):
        """Handle key release for type-ahead filtering."""
        
        # Ignore navigation keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Tab'):
            return
        
        typed = self.get()
        
        # Reset filter if below threshold
        if len(typed) < self.min_chars:
            if self.filtered:
                self.configure(values=self.full_values)
                self.filtered = False
            return
        
        # Filter values
        filtered = self._filter_values(typed)
        
        if filtered:
            self.configure(values=filtered)
            self.filtered = True
        else:
            # No matches - keep current values
            pass
    
    def _filter_values(self, typed: str) -> List[str]:
        """
        Filter values list based on typed text.
        
        Prioritizes word boundary matches over contains matches.
        
        Args:
            typed: Text typed by user
            
        Returns:
            Filtered list of matching values
        """
        typed_lower = typed.lower()
        
        # Word boundary matches (higher priority)
        word_boundary = []
        # Contains matches (lower priority)
        contains = []
        
        for value in self.full_values:
            value_lower = value.lower()
            
            # Check word boundaries (starts with or after space)
            words = value_lower.split()
            is_word_boundary = any(word.startswith(typed_lower) for word in words)
            
            if is_word_boundary:
                word_boundary.append(value)
            elif typed_lower in value_lower:
                contains.append(value)
        
        # Combine: word boundary first, then contains
        return word_boundary + contains
    
    def _on_focus_out(self, event):
        """Reset filter on focus out."""
        if self.filtered:
            self.configure(values=self.full_values)
            self.filtered = False
    
    def reset_values(self, values: List[str]):
        """
        Update the full values list.
        
        Call this when underlying data changes (e.g., category selected).
        
        Args:
            values: New complete list of values
        """
        self.full_values = values
        self.configure(values=values)
        self.filtered = False
```

### Recency-Aware Dropdown Builder

```python
def build_product_dropdown_values(
    ingredient_id: int,
    session: Session
) -> List[str]:
    """
    Build product dropdown values with recency markers and sorting.
    
    Args:
        ingredient_id: Ingredient to filter products for
        session: Database session
        
    Returns:
        List of dropdown values in display order
        
    Example output:
        [
            "⭐ Gold Medal AP Flour 10lb",
            "⭐ King Arthur AP Flour 5lb",
            "─────────────────────────────",
            "Bob's Red Mill AP Flour 2lb",
            "Generic AP Flour 25lb",
            "─────────────────────────────",
            "[+ Create New Product]"
        ]
    """
    # Get all products for ingredient
    products = session.query(Product).filter_by(
        ingredient_id=ingredient_id,
        is_hidden=False
    ).order_by(Product.name).all()
    
    if not products:
        return ["[+ Create New Product]"]
    
    # Get recent product IDs
    recent_ids = get_recent_products(ingredient_id, session=session)
    recent_set = set(recent_ids)
    
    # Separate recent vs non-recent
    recent_products = []
    other_products = []
    
    for product in products:
        display_name = f"{product.name}"
        if product.id in recent_set:
            recent_products.append(f"⭐ {display_name}")
        else:
            other_products.append(display_name)
    
    # Build final list
    values = []
    
    if recent_products:
        values.extend(recent_products)
        if other_products:
            values.append("─────────────────────────────")
    
    values.extend(other_products)
    
    if values:  # Only add separator if products exist
        values.append("─────────────────────────────")
    
    values.append("[+ Create New Product]")
    
    return values


def build_ingredient_dropdown_values(
    category: str,
    session: Session
) -> List[str]:
    """
    Build ingredient dropdown values with recency sorting.
    
    Similar to product dropdown but for ingredients.
    
    Args:
        category: Category to filter ingredients for
        session: Database session
        
    Returns:
        List of dropdown values in display order
    """
    # Get all ingredients in category
    ingredients = session.query(Ingredient).filter_by(
        category=category
    ).order_by(Ingredient.display_name).all()
    
    if not ingredients:
        return []
    
    # Get recent ingredient IDs
    recent_ids = get_recent_ingredients(category, session=session)
    recent_set = set(recent_ids)
    
    # Separate recent vs non-recent
    recent_ingredients = []
    other_ingredients = []
    
    for ingredient in ingredients:
        display_name = ingredient.display_name
        if ingredient.id in recent_set:
            recent_ingredients.append(f"⭐ {display_name}")
        else:
            other_ingredients.append(display_name)
    
    # Build final list
    values = []
    
    if recent_ingredients:
        values.extend(recent_ingredients)
        if other_ingredients:
            values.append("─────────────────────────────")
    
    values.extend(other_ingredients)
    
    return values
```

### Enhanced AddInventoryDialog Class

```python
class AddInventoryDialog(ctk.CTkToplevel):
    """
    Enhanced Add Inventory Item dialog with type-ahead and session memory.
    
    Features (Feature 029):
    - Type-ahead filtering on Category, Ingredient, Product
    - Recency-based sorting with ⭐ markers
    - Session memory for Supplier and Category
    - Inline product creation (collapsible accordion)
    - Smart defaults for package units
    - Price suggestion with hints
    - Validation warnings (>$100, decimal quantities)
    """
    
    def __init__(self, master, service_integrator, **kwargs):
        super().__init__(master, **kwargs)
        
        self.service_integrator = service_integrator
        self.session_state = session_state  # Global session state
        self.session = None  # Database session for queries
        
        # State tracking
        self.inline_create_expanded = False
        self.selected_ingredient = None
        self.selected_product = None
        
        self.title("Add Inventory Item")
        self.geometry("600x700")  # Taller to accommodate inline creation
        
        self._setup_ui()
        self._load_initial_data()
    
    def _setup_ui(self):
        """Configure dialog layout."""
        
        # Category (with type-ahead)
        ctk.CTkLabel(self, text="Category:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.category_combo = TypeAheadComboBox(
            self,
            values=[],  # Loaded in _load_initial_data
            min_chars=1,
            command=self._on_category_selected,
            state="readonly"
        )
        self.category_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Ingredient (with type-ahead, disabled initially)
        ctk.CTkLabel(self, text="Ingredient:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.ingredient_combo = TypeAheadComboBox(
            self,
            values=[],
            min_chars=2,
            command=self._on_ingredient_selected,
            state="disabled"
        )
        self.ingredient_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        # Product (with type-ahead, disabled initially) + New button
        ctk.CTkLabel(self, text="Product:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        product_frame = ctk.CTkFrame(self)
        product_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        product_frame.columnconfigure(0, weight=1)
        
        self.product_combo = TypeAheadComboBox(
            product_frame,
            values=[],
            min_chars=2,
            command=self._on_product_selected,
            state="disabled"
        )
        self.product_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.new_product_btn = ctk.CTkButton(
            product_frame,
            text="+ New",
            width=60,
            command=self._toggle_inline_create,
            state="disabled"
        )
        self.new_product_btn.grid(row=0, column=1)
        
        # Inline product creation (collapsible accordion)
        self.inline_create_frame = ctk.CTkFrame(self, border_width=1)
        # Initially not gridded (hidden)
        
        self._setup_inline_create_form()
        
        # Supplier (standard dropdown, session memory)
        ctk.CTkLabel(self, text="Supplier:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        
        self.supplier_var = ctk.StringVar()
        self.supplier_combo = ctk.CTkComboBox(
            self,
            variable=self.supplier_var,
            command=self._on_supplier_selected,
            state="readonly"
        )
        self.supplier_combo.grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        
        # Price (with hint label)
        ctk.CTkLabel(self, text="Price:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        
        self.price_entry = ctk.CTkEntry(self)
        self.price_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=5)
        self.price_entry.bind('<FocusOut>', self._validate_price)
        
        self.price_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=("", 10),
            text_color="gray"
        )
        self.price_hint_label.grid(row=6, column=1, sticky="w", padx=10)
        
        # Quantity (with validation)
        ctk.CTkLabel(self, text="Quantity:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
        
        self.quantity_entry = ctk.CTkEntry(self)
        self.quantity_entry.grid(row=7, column=1, sticky="ew", padx=10, pady=5)
        self.quantity_entry.bind('<FocusOut>', self._validate_quantity)
        
        # Notes
        ctk.CTkLabel(self, text="Notes:").grid(row=8, column=0, sticky="nw", padx=10, pady=5)
        
        self.notes_entry = ctk.CTkEntry(self)
        self.notes_entry.grid(row=8, column=1, sticky="ew", padx=10, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=9, column=0, columnspan=2, pady=20)
        
        ctk.CTkButton(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Add Inventory", command=self._add_inventory).pack(side="left", padx=5)
        
        # Configure grid weights
        self.columnconfigure(1, weight=1)
    
    def _setup_inline_create_form(self):
        """Setup inline product creation form (inside accordion frame)."""
        
        # Header with collapse indicator
        header_frame = ctk.CTkFrame(self.inline_create_frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        self.inline_header_label = ctk.CTkLabel(
            header_frame,
            text="▼ Click to collapse",
            font=("", 12, "bold")
        )
        self.inline_header_label.pack(side="left")
        
        # Form fields
        form_frame = ctk.CTkFrame(self.inline_create_frame)
        form_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Ingredient (read-only, pre-filled)
        ctk.CTkLabel(form_frame, text="Ingredient:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.inline_ingredient_label = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="gray"
        )
        self.inline_ingredient_label.grid(row=0, column=1, sticky="w", padx=5, pady=3)
        
        # Product Name (required)
        ctk.CTkLabel(form_frame, text="Product Name:*").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.inline_name_entry = ctk.CTkEntry(form_frame)
        self.inline_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        # Package Unit + Quantity
        ctk.CTkLabel(form_frame, text="Package Unit:*").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        
        unit_frame = ctk.CTkFrame(form_frame)
        unit_frame.grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        unit_frame.columnconfigure(0, weight=1)
        unit_frame.columnconfigure(2, weight=1)
        
        self.inline_unit_combo = ctk.CTkComboBox(
            unit_frame,
            values=["lb", "oz", "kg", "g", "fl oz", "ml", "L", "count"],  # Common units
            state="readonly"
        )
        self.inline_unit_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkLabel(unit_frame, text="Qty:").grid(row=0, column=1)
        
        self.inline_qty_entry = ctk.CTkEntry(unit_frame, width=80)
        self.inline_qty_entry.grid(row=0, column=2, sticky="ew", padx=(5, 0))
        
        # Preferred Supplier
        ctk.CTkLabel(form_frame, text="Preferred Supplier:").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self.inline_supplier_combo = ctk.CTkComboBox(
            form_frame,
            values=[],  # Populated same as main supplier dropdown
            state="readonly"
        )
        self.inline_supplier_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        
        # Buttons
        btn_frame = ctk.CTkFrame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ctk.CTkButton(btn_frame, text="Cancel", command=self._cancel_inline_create).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Create Product", command=self._create_product_inline).pack(side="left", padx=5)
        
        form_frame.columnconfigure(1, weight=1)
    
    def _load_initial_data(self):
        """Load initial data and apply session memory."""
        
        with session_scope() as session:
            self.session = session
            
            # Load categories
            categories = session.query(Ingredient.category).distinct().order_by(Ingredient.category).all()
            category_list = [c[0] for c in categories]
            self.category_combo.reset_values(category_list)
            
            # Apply session memory for category
            last_category = self.session_state.get_last_category()
            if last_category and last_category in category_list:
                self.category_combo.set(f"⭐ {last_category}")
                self._on_category_selected(last_category)  # Trigger cascade
            
            # Load suppliers
            suppliers = self.service_integrator.execute_operation(
                operation_type=OperationType.LIST_SUPPLIERS
            )
            suppliers.sort(key=lambda s: (s.name, s.city, s.state))
            
            supplier_names = [s.display_name for s in suppliers]
            self.supplier_combo.configure(values=supplier_names)
            self.inline_supplier_combo.configure(values=supplier_names)
            
            # Store supplier mapping
            self.supplier_map = {s.display_name: s for s in suppliers}
            
            # Apply session memory for supplier
            last_supplier_id = self.session_state.get_last_supplier_id()
            if last_supplier_id:
                # Find supplier display name
                for display_name, supplier in self.supplier_map.items():
                    if supplier.id == last_supplier_id:
                        self.supplier_var.set(f"⭐ {display_name}")
                        self.inline_supplier_combo.set(f"⭐ {display_name}")
                        break
    
    def _on_category_selected(self, selected_value: str):
        """Handle category selection - load ingredients."""
        
        # Remove ⭐ from value if present
        category = selected_value.replace("⭐ ", "").strip()
        
        with session_scope() as session:
            # Build ingredient dropdown with recency
            ingredient_values = build_ingredient_dropdown_values(category, session)
            self.ingredient_combo.reset_values(ingredient_values)
            self.ingredient_combo.configure(state="readonly")
            
            # Clear downstream selections
            self.ingredient_combo.set("")
            self.product_combo.set("")
            self.product_combo.configure(state="disabled")
            self.new_product_btn.configure(state="disabled")
    
    def _on_ingredient_selected(self, selected_value: str):
        """Handle ingredient selection - load products."""
        
        # Remove ⭐ from value if present
        ingredient_name = selected_value.replace("⭐ ", "").strip()
        
        with session_scope() as session:
            # Find ingredient by display_name
            ingredient = session.query(Ingredient).filter_by(
                display_name=ingredient_name
            ).first()
            
            if not ingredient:
                return
            
            self.selected_ingredient = ingredient
            
            # Build product dropdown with recency
            product_values = build_product_dropdown_values(ingredient.id, session)
            self.product_combo.reset_values(product_values)
            self.product_combo.configure(state="readonly")
            self.new_product_btn.configure(state="normal")
            
            # Check if zero products (show create button prominently)
            products = session.query(Product).filter_by(
                ingredient_id=ingredient.id,
                is_hidden=False
            ).count()
            
            if products == 0:
                # Auto-expand inline create? Or just enable button?
                # Per spec: require button click, don't auto-expand
                self.new_product_btn.configure(
                    text="+ Create First Product",
                    fg_color="orange"  # Highlight
                )
    
    def _on_product_selected(self, selected_value: str):
        """Handle product selection."""
        
        # Check if "[+ Create New Product]" selected
        if "[+ Create New Product]" in selected_value:
            self._toggle_inline_create()
            return
        
        # Remove ⭐ from value
        product_name = selected_value.replace("⭐ ", "").strip()
        
        with session_scope() as session:
            # Find product by name and ingredient
            product = session.query(Product).filter_by(
                name=product_name,
                ingredient_id=self.selected_ingredient.id,
                is_hidden=False
            ).first()
            
            if not product:
                return
            
            self.selected_product = product
            
            # If supplier already selected, trigger price suggestion
            if self.supplier_var.get():
                self._update_price_suggestion()
    
    def _toggle_inline_create(self):
        """Toggle inline product creation form (accordion)."""
        
        if self.inline_create_expanded:
            # Collapse
            self.inline_create_frame.grid_forget()
            self.inline_create_expanded = False
            self.inline_header_label.configure(text="▼ Click to expand")
            self.product_combo.configure(state="readonly")
        else:
            # Expand
            self.inline_create_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
            self.inline_create_expanded = True
            self.inline_header_label.configure(text="▼ Click to collapse")
            
            # Pre-fill fields
            if self.selected_ingredient:
                self.inline_ingredient_label.configure(
                    text=self.selected_ingredient.display_name
                )
                
                # Smart default for unit
                default_unit = get_default_unit_for_ingredient(self.selected_ingredient)
                self.inline_unit_combo.set(default_unit)
            
            # Pre-fill preferred supplier from session
            last_supplier = self.supplier_var.get()
            if last_supplier:
                self.inline_supplier_combo.set(last_supplier)
            
            # Focus on name field
            self.inline_name_entry.focus()
            
            # Disable main product dropdown
            self.product_combo.configure(state="disabled")
    
    def _create_product_inline(self):
        """Create product from inline form."""
        
        # Validate
        name = self.inline_name_entry.get().strip()
        if not name:
            show_error(self, "Validation Error", "Product name is required")
            return
        
        unit = self.inline_unit_combo.get()
        if not unit:
            show_error(self, "Validation Error", "Package unit is required")
            return
        
        try:
            qty = Decimal(self.inline_qty_entry.get())
            if qty <= 0:
                raise ValueError()
        except:
            show_error(self, "Validation Error", "Package quantity must be a positive number")
            return
        
        # Get preferred supplier
        supplier_display = self.inline_supplier_combo.get().replace("⭐ ", "").strip()
        preferred_supplier_id = None
        if supplier_display:
            supplier = self.supplier_map.get(supplier_display)
            if supplier:
                preferred_supplier_id = supplier.id
        
        # Create product
        try:
            product = self.service_integrator.execute_operation(
                operation_type=OperationType.CREATE_PRODUCT,
                name=name,
                ingredient_id=self.selected_ingredient.id,
                package_unit=unit,
                package_unit_quantity=qty,
                preferred_supplier_id=preferred_supplier_id
            )
            
            # Success - add to dropdown and select
            with session_scope() as session:
                # Rebuild product dropdown
                product_values = build_product_dropdown_values(
                    self.selected_ingredient.id,
                    session
                )
                self.product_combo.reset_values(product_values)
                
                # Select new product (with ⭐ since just created = recent)
                self.product_combo.set(f"⭐ {name}")
                self.selected_product = product
            
            # Collapse inline create
            self._cancel_inline_create()
            
            # Continue workflow - trigger supplier/price
            if self.supplier_var.get():
                self._update_price_suggestion()
            
        except Exception as e:
            show_error(self, "Product Creation Failed", str(e))
    
    def _cancel_inline_create(self):
        """Cancel inline product creation."""
        
        # Clear form
        self.inline_name_entry.delete(0, 'end')
        self.inline_qty_entry.delete(0, 'end')
        
        # Collapse
        self._toggle_inline_create()
    
    def _on_supplier_selected(self, selected_value: str):
        """Handle supplier selection - update price suggestion."""
        self._update_price_suggestion()
    
    def _update_price_suggestion(self):
        """Update price field with suggestion from purchase history."""
        
        if not self.selected_product:
            return
        
        supplier_display = self.supplier_var.get().replace("⭐ ", "").strip()
        supplier = self.supplier_map.get(supplier_display)
        
        if not supplier:
            return
        
        # Query last price at this supplier
        last_price = self.service_integrator.execute_operation(
            operation_type=OperationType.GET_LAST_PURCHASE_PRICE,
            product_id=self.selected_product.id,
            supplier_id=supplier.id
        )
        
        if last_price:
            # Found price at this supplier
            self.price_entry.delete(0, 'end')
            self.price_entry.insert(0, f"{last_price:.2f}")
            
            # Get date from purchase history
            history = self.service_integrator.execute_operation(
                operation_type=OperationType.GET_PURCHASE_HISTORY,
                product_id=self.selected_product.id,
                supplier_id=supplier.id,
                limit=1
            )
            
            if history:
                date_str = history[0].purchase_date.strftime('%m/%d')
                self.price_hint_label.configure(
                    text=f"(last paid: ${last_price:.2f} on {date_str})"
                )
        else:
            # No price at this supplier - try fallback
            fallback = self.service_integrator.execute_operation(
                operation_type=OperationType.GET_LAST_PURCHASE_PRICE_ANY_SUPPLIER,
                product_id=self.selected_product.id
            )
            
            if fallback:
                # Found price at different supplier
                self.price_entry.delete(0, 'end')
                self.price_entry.insert(0, f"{fallback['price']:.2f}")
                
                date_str = fallback['purchase_date'].strftime('%m/%d')
                supplier_name = f"{fallback['supplier_name']} ({fallback['supplier_city']}, {fallback['supplier_state']})"
                
                self.price_hint_label.configure(
                    text=f"(last paid: ${fallback['price']:.2f} at {supplier_name} on {date_str})"
                )
            else:
                # No purchase history at all
                self.price_entry.delete(0, 'end')
                self.price_hint_label.configure(text="(no purchase history)")
    
    def _validate_price(self, event=None):
        """Validate price on focus out."""
        
        try:
            price = Decimal(self.price_entry.get())
            
            # Warn if >$100
            if price > 100:
                confirm = messagebox.askyesno(
                    "Confirm High Price",
                    "⚠️ Price is $100+. Confirm this is correct?",
                    parent=self
                )
                if not confirm:
                    self.price_entry.focus()
                    return False
            
            # Error if negative
            if price < 0:
                show_error(self, "Validation Error", "Price cannot be negative")
                self.price_entry.focus()
                return False
            
            return True
            
        except (ValueError, InvalidOperation):
            # Invalid format - will be caught on Add
            return False
    
    def _validate_quantity(self, event=None):
        """Validate quantity on focus out."""
        
        if not self.selected_product:
            return True
        
        try:
            qty = Decimal(self.quantity_entry.get())
            
            # Check for decimal with count-based units
            count_units = ['count', 'bag', 'box', 'package', 'bottle', 'can']
            if self.selected_product.package_unit.lower() in count_units:
                if qty != qty.to_integral_value():
                    # Has decimal places
                    confirm = messagebox.askyesno(
                        "Confirm Decimal Quantity",
                        "Package quantities are usually whole numbers. Continue?",
                        parent=self
                    )
                    if not confirm:
                        self.quantity_entry.focus()
                        return False
            
            return True
            
        except (ValueError, InvalidOperation):
            return False
    
    def _add_inventory(self):
        """Add inventory item - validate and call service."""
        
        # Validate all fields populated
        if not self.selected_ingredient:
            show_error(self, "Validation Error", "Please select an ingredient")
            return
        
        if not self.selected_product:
            show_error(self, "Validation Error", "Please select a product")
            return
        
        supplier_display = self.supplier_var.get().replace("⭐ ", "").strip()
        supplier = self.supplier_map.get(supplier_display)
        if not supplier:
            show_error(self, "Validation Error", "Please select a supplier")
            return
        
        try:
            price = Decimal(self.price_entry.get())
        except (ValueError, InvalidOperation):
            show_error(self, "Validation Error", "Invalid price format")
            return
        
        try:
            quantity = int(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError()
        except (ValueError, InvalidOperation):
            show_error(self, "Validation Error", "Quantity must be a positive integer")
            return
        
        notes = self.notes_entry.get().strip() or None
        
        # Validate price and quantity one more time
        if not self._validate_price():
            return
        if not self._validate_quantity():
            return
        
        # Add inventory
        try:
            addition = self.service_integrator.execute_operation(
                operation_type=OperationType.ADD_INVENTORY,
                ingredient_id=self.selected_ingredient.id,
                product_id=self.selected_product.id,
                supplier_id=supplier.id,
                quantity=quantity,
                unit_price=price,
                notes=notes
            )
            
            # Success - update session state
            category = self.category_combo.get().replace("⭐ ", "").strip()
            self.session_state.update_category(category)
            self.session_state.update_supplier(supplier.id)
            
            # Clear fields except category and supplier (session memory)
            self.ingredient_combo.set("")
            self.product_combo.set("")
            self.price_entry.delete(0, 'end')
            self.quantity_entry.delete(0, 'end')
            self.notes_entry.delete(0, 'end')
            self.price_hint_label.configure(text="")
            
            self.selected_ingredient = None
            self.selected_product = None
            
            # Disable downstream dropdowns
            self.ingredient_combo.configure(state="disabled")
            self.product_combo.configure(state="disabled")
            self.new_product_btn.configure(state="disabled")
            
            # Re-enable category/ingredient for next entry
            self.ingredient_combo.configure(state="readonly")
            self.ingredient_combo.focus()
            
            # Brief success indicator (future: green checkmark animation)
            
        except Exception as e:
            show_error(self, "Add Inventory Failed", str(e))
```

---

## Testing Strategy

### Unit Tests

**Recency Queries:**

```python
# tests/services/test_recency_queries.py

class TestRecencyQueries:
    """Test suite for recency intelligence."""
    
    def test_get_recent_products_temporal(self, session, recent_additions):
        """Verify products added within 30 days are recent."""
        
        # Fixture: Product A added yesterday, Product B added 45 days ago
        recent_ids = get_recent_products(
            ingredient_id=recent_additions['ingredient'].id,
            days=30,
            session=session
        )
        
        assert recent_additions['product_a'].id in recent_ids
        assert recent_additions['product_b'].id not in recent_ids
    
    def test_get_recent_products_frequency(self, session, frequent_additions):
        """Verify products used 3+ times in 90 days are recent."""
        
        # Fixture: Product C added 5 times in last 90 days
        recent_ids = get_recent_products(
            ingredient_id=frequent_additions['ingredient'].id,
            min_frequency=3,
            frequency_days=90,
            session=session
        )
        
        assert frequent_additions['product_c'].id in recent_ids
    
    def test_get_recent_products_hybrid(self, session, hybrid_scenario):
        """Verify temporal OR frequency criteria both work."""
        
        # Product D: Added yesterday (recent by temporal)
        # Product E: Added 60 days ago but 4 times (recent by frequency)
        # Product F: Added 60 days ago only once (not recent)
        
        recent_ids = get_recent_products(
            ingredient_id=hybrid_scenario['ingredient'].id,
            days=30,
            min_frequency=3,
            frequency_days=90,
            session=session
        )
        
        assert hybrid_scenario['product_d'].id in recent_ids  # Temporal
        assert hybrid_scenario['product_e'].id in recent_ids  # Frequency
        assert hybrid_scenario['product_f'].id not in recent_ids  # Neither
    
    def test_get_recent_products_sorted_by_date(self, session, multiple_recent):
        """Verify recent products sorted by most recent first."""
        
        recent_ids = get_recent_products(
            ingredient_id=multiple_recent['ingredient'].id,
            session=session
        )
        
        # Should be sorted: most recent → least recent
        assert recent_ids[0] == multiple_recent['newest'].id
        assert recent_ids[-1] == multiple_recent['oldest'].id
    
    def test_get_recent_ingredients_within_category(self, session, baking_ingredients):
        """Verify ingredient recency filtered by category."""
        
        recent_ids = get_recent_ingredients(
            category='Baking',
            session=session
        )
        
        # Only baking ingredients should be in results
        for iid in recent_ids:
            ingredient = session.query(Ingredient).get(iid)
            assert ingredient.category == 'Baking'
```

**Session State:**

```python
# tests/test_session_state.py

class TestSessionState:
    """Test suite for session state management."""
    
    def test_session_state_singleton(self):
        """Verify SessionState is singleton."""
        state1 = SessionState()
        state2 = SessionState()
        
        assert state1 is state2
    
    def test_update_supplier(self, session_state):
        """Verify supplier update."""
        session_state.update_supplier(42)
        assert session_state.get_last_supplier_id() == 42
    
    def test_update_category(self, session_state):
        """Verify category update."""
        session_state.update_category('Baking')
        assert session_state.get_last_category() == 'Baking'
    
    def test_reset_clears_state(self, session_state):
        """Verify reset clears all state."""
        session_state.update_supplier(42)
        session_state.update_category('Baking')
        
        session_state.reset()
        
        assert session_state.get_last_supplier_id() is None
        assert session_state.get_last_category() is None
```

**Smart Defaults:**

```python
# tests/test_smart_defaults.py

class TestSmartDefaults:
    """Test suite for category→unit default mapping."""
    
    def test_baking_defaults_to_lb(self):
        """Verify Baking category defaults to lb."""
        assert get_default_unit_for_category('Baking') == 'lb'
    
    def test_chocolate_defaults_to_oz(self):
        """Verify Chocolate category defaults to oz."""
        assert get_default_unit_for_category('Chocolate') == 'oz'
    
    def test_unknown_category_falls_back(self):
        """Verify unknown category gets fallback default."""
        assert get_default_unit_for_category('UnknownCategory') == 'lb'
    
    def test_get_default_for_ingredient(self, flour_ingredient):
        """Verify ingredient wrapper function."""
        # Flour is in Baking category
        assert get_default_unit_for_ingredient(flour_ingredient) == 'lb'
```

### Integration Tests

**Type-Ahead Workflow:**

```python
# tests/integration/test_type_ahead.py

class TestTypeAheadWorkflow:
    """Integration tests for type-ahead filtering."""
    
    def test_category_type_ahead_filtering(self, dialog):
        """Verify typing in category filters dropdown."""
        
        # Simulate typing "bak"
        dialog.category_combo._entry.insert(0, "bak")
        dialog.category_combo._on_key_release(MagicMock(keysym='k'))
        
        # Should filter to Baking
        values = dialog.category_combo.cget('values')
        assert 'Baking' in values
        assert 'Dairy' not in values
    
    def test_ingredient_filtered_by_category(self, dialog):
        """Verify ingredient dropdown only shows category-filtered items."""
        
        # Select category
        dialog.category_combo.set('Baking')
        dialog._on_category_selected('Baking')
        
        # Ingredient dropdown should only have Baking ingredients
        values = dialog.ingredient_combo.cget('values')
        
        # All values should be Baking ingredients (or separators/stars)
        # Test by loading actual ingredients and verifying
        with session_scope() as session:
            baking_ingredients = session.query(Ingredient).filter_by(
                category='Baking'
            ).all()
            baking_names = {i.display_name for i in baking_ingredients}
            
            for value in values:
                clean_value = value.replace('⭐ ', '').strip()
                if clean_value and '─' not in clean_value:
                    assert clean_value in baking_names
```

**Recency Display:**

```python
# tests/integration/test_recency_display.py

class TestRecencyDisplay:
    """Integration tests for recency markers and sorting."""
    
    def test_recent_products_marked_with_star(self, dialog, recent_product):
        """Verify ⭐ appears next to recent products."""
        
        # Setup: Select ingredient that has recent product
        dialog._on_ingredient_selected(recent_product.ingredient.display_name)
        
        # Check dropdown values
        values = dialog.product_combo.cget('values')
        
        # Recent product should have star
        recent_display = f"⭐ {recent_product.name}"
        assert recent_display in values
    
    def test_recent_products_sorted_first(self, dialog, multiple_products):
        """Verify recent products appear before non-recent."""
        
        # Fixture: Product A is recent, Product B is not
        dialog._on_ingredient_selected(multiple_products['ingredient'].display_name)
        
        values = dialog.product_combo.cget('values')
        
        # Find indices
        recent_idx = None
        other_idx = None
        
        for i, v in enumerate(values):
            if multiple_products['recent'].name in v:
                recent_idx = i
            if multiple_products['other'].name in v:
                other_idx = i
        
        # Recent should come before other
        assert recent_idx < other_idx
```

**Inline Product Creation:**

```python
# tests/integration/test_inline_product_creation.py

class TestInlineProductCreation:
    """Integration tests for inline product creation workflow."""
    
    def test_inline_create_expands_on_button_click(self, dialog):
        """Verify clicking + New expands accordion."""
        
        # Setup: Select ingredient to enable button
        dialog._on_ingredient_selected('All-Purpose Flour')
        
        # Click new button
        dialog.new_product_btn.invoke()
        
        # Verify form expanded
        assert dialog.inline_create_expanded
        assert dialog.inline_create_frame.winfo_viewable()
    
    def test_inline_create_prefills_ingredient(self, dialog):
        """Verify ingredient pre-filled and read-only."""
        
        dialog._on_ingredient_selected('All-Purpose Flour')
        dialog._toggle_inline_create()
        
        # Verify ingredient label shows selection
        assert 'All-Purpose Flour' in dialog.inline_ingredient_label.cget('text')
    
    def test_inline_create_prefills_supplier_from_session(self, dialog, session_state):
        """Verify preferred supplier pre-filled from session."""
        
        # Set session state
        session_state.update_supplier(42)  # Costco
        
        dialog._on_ingredient_selected('All-Purpose Flour')
        dialog._toggle_inline_create()
        
        # Verify supplier combo shows session value
        supplier_value = dialog.inline_supplier_combo.get()
        assert 'Costco' in supplier_value
        assert '⭐' in supplier_value
    
    def test_inline_create_smart_default_unit(self, dialog):
        """Verify package unit defaults based on category."""
        
        # Select Baking ingredient
        dialog.category_combo.set('Baking')
        dialog._on_category_selected('Baking')
        dialog._on_ingredient_selected('All-Purpose Flour')
        dialog._toggle_inline_create()
        
        # Verify unit defaulted to lb (Baking category)
        assert dialog.inline_unit_combo.get() == 'lb'
    
    def test_inline_create_adds_to_dropdown(self, dialog, session):
        """Verify newly created product appears in dropdown."""
        
        dialog._on_ingredient_selected('All-Purpose Flour')
        dialog._toggle_inline_create()
        
        # Fill form
        dialog.inline_name_entry.insert(0, "Test Product 10lb")
        dialog.inline_unit_combo.set('lb')
        dialog.inline_qty_entry.insert(0, '10')
        
        # Create
        dialog._create_product_inline()
        
        # Verify product in dropdown
        values = dialog.product_combo.cget('values')
        assert any('Test Product 10lb' in v for v in values)
        
        # Verify selected
        assert 'Test Product 10lb' in dialog.product_combo.get()
```

**Session Memory:**

```python
# tests/integration/test_session_memory.py

class TestSessionMemory:
    """Integration tests for session-based memory."""
    
    def test_supplier_prefilled_from_session(self, dialog, session_state):
        """Verify last supplier pre-selected with star."""
        
        # Setup session
        session_state.update_supplier(42)  # Costco
        
        # Open dialog
        dialog._load_initial_data()
        
        # Verify supplier pre-selected
        supplier_value = dialog.supplier_var.get()
        assert 'Costco' in supplier_value
        assert '⭐' in supplier_value
    
    def test_category_prefilled_from_session(self, dialog, session_state):
        """Verify last category pre-selected."""
        
        session_state.update_category('Baking')
        
        dialog._load_initial_data()
        
        assert 'Baking' in dialog.category_combo.get()
    
    def test_session_updates_on_successful_add(self, dialog, session_state):
        """Verify session state updates after Add clicked."""
        
        # Setup: Add inventory with Costco + Baking
        # ... populate all fields ...
        dialog._add_inventory()  # Success
        
        # Verify session updated
        assert session_state.get_last_supplier_id() == dialog.supplier_map['Costco'].id
        assert session_state.get_last_category() == 'Baking'
    
    def test_session_not_updated_on_cancel(self, dialog, session_state):
        """Verify session not updated when dialog cancelled."""
        
        initial_supplier = session_state.get_last_supplier_id()
        initial_category = session_state.get_last_category()
        
        # Change selections but cancel
        dialog.category_combo.set('Dairy')
        dialog.supplier_var.set('Wegmans')
        dialog.destroy()  # Cancel
        
        # Verify session unchanged
        assert session_state.get_last_supplier_id() == initial_supplier
        assert session_state.get_last_category() == initial_category
```

**Validation:**

```python
# tests/integration/test_validation.py

class TestValidation:
    """Integration tests for validation warnings."""
    
    def test_price_warning_over_100(self, dialog):
        """Verify warning shown when price >$100."""
        
        dialog.price_entry.insert(0, '150.00')
        
        with patch('tkinter.messagebox.askyesno', return_value=False):
            result = dialog._validate_price()
            
            assert result == False  # Validation failed
    
    def test_decimal_quantity_warning_for_count_units(self, dialog, count_product):
        """Verify warning when entering decimal for count-based unit."""
        
        dialog.selected_product = count_product  # Unit = "bag"
        dialog.quantity_entry.insert(0, '1.5')
        
        with patch('tkinter.messagebox.askyesno', return_value=False):
            result = dialog._validate_quantity()
            
            assert result == False
```

---

## Acceptance Criteria

### Must Have (MVP)

1. ✅ Type-ahead filtering on Category dropdown (1-char threshold, contains match)
2. ✅ Type-ahead filtering on Ingredient dropdown (2-char threshold, category-filtered)
3. ✅ Type-ahead filtering on Product dropdown (2-char threshold, ingredient-filtered)
4. ✅ Recent products marked with ⭐ in dropdown
5. ✅ Recent products sorted to top of dropdown (before separator)
6. ✅ Recent ingredients sorted to top within category
7. ✅ Recency logic: Last 30 days OR 3+ uses in last 90 days
8. ✅ Session memory: Last supplier pre-selected with ⭐
9. ✅ Session memory: Last category pre-selected
10. ✅ Session state persists until app restart
11. ✅ Session updates only on successful Add (not on cancel)
12. ✅ [+ New Product] button functional (triggers inline creation)
13. ✅ Inline product creation: Collapsible accordion form
14. ✅ Inline creation pre-fills: Ingredient (read-only), Supplier (session), Unit (smart default)
15. ✅ Smart unit defaults by category (configurable CATEGORY_DEFAULT_UNITS)
16. ✅ Price validation: Warning when >$100
17. ✅ Quantity validation: Warning for decimal with count units
18. ✅ Zero products case: "[+ Create First Product]" button with orange highlight
19. ✅ Tab navigation works through all fields
20. ✅ Enter/Escape key handling works correctly
21. ✅ Price suggestion shows inline hint with date
22. ✅ Price suggestion fallback shows different supplier in hint
23. ✅ Type-ahead word boundary prioritization ("ap" → "AP Flour" before "Maple")
24. ✅ All existing tests pass with new workflow

### Should Have (Post-MVP)

1. ⬜ Purchase history tooltip on hover (last 3-5 purchases)
2. ⬜ Keyboard shortcut: Ctrl+N for new product
3. ⬜ Visual field grouping with borders/separators
4. ⬜ Loading indicators during recency queries (if performance issues)
5. ⬜ Configuration UI for CATEGORY_DEFAULT_UNITS

### Could Have (Future)

1. ⬜ Bulk entry mode (CSV import)
2. ⬜ Voice input
3. ⬜ Barcode scanning (mobile app)
4. ⬜ Auto-categorization (AI-powered)
5. ⬜ Purchase history visualization
6. ⬜ Undo/redo functionality
7. ⬜ Multi-step wizard alternative

---

## Risks and Mitigation

### Risk: Type-Ahead Performance

**Risk:** Filtering 500+ products on each keystroke could lag.

**Mitigation:**
- Client-side filtering (no DB queries)
- Debounce typing (200ms delay)
- Limit displayed results (top 20)
- Benchmark with realistic data (500 products, 200 ingredients)
- Pre-filter by ingredient (products dropdown only shows ~20-50 items)

### Risk: Session State Loss on Crash

**Risk:** Unexpected app crash loses session state.

**Mitigation:**
- Accept limitation - session is convenience, not critical data
- Document: "Session resets on app restart"
- Future enhancement: Persist to temp file, restore on relaunch

### Risk: Smart Defaults Incorrect

**Risk:** Category→Unit mapping doesn't match all products.

**Mitigation:**
- All defaults editable (user can override)
- Configuration in code constants (easy to update)
- User testing validates defaults
- Document: "Defaults are suggestions"

### Risk: Recency Query Performance

**Risk:** Hybrid temporal/frequency query could be slow.

**Mitigation:**
- Index on InventoryAddition.addition_date
- Cache results during session
- Query only when dropdown opens (lazy)
- Limit to top 20 results
- Benchmark with realistic data

### Risk: UI Complexity

**Risk:** Many features in one dialog could overwhelm users.

**Mitigation:**
- Accordion keeps inline creation hidden until needed
- Progressive disclosure (enable fields as previous selected)
- Type-ahead reduces visible options
- User testing validates comprehension

---

## Open Questions (Minor)

**1. Recency cache invalidation:**
When should recency cache refresh?
- **Current:** On each Add (session lifetime)
- **Alternative:** Every 5 minutes

**Resolution:** Session lifetime sufficient for desktop single-user.

**2. Type-ahead case sensitivity:**
Should "AP" match "All-Purpose Flour"?
- **Resolution:** Case-insensitive always (simpler, expected behavior)

**3. Accordion default state on re-open:**
If user collapses accordion, should it stay collapsed next time?
- **Resolution:** Always collapsed on dialog open (consistent state)

**4. Price hint verbosity:**
Show full supplier name or abbreviate?
- **Current:** Full name with city/state
- **Alternative:** Just supplier name

**Resolution:** Full name for accuracy (users may have Costco Waltham and Costco Burlington)

---

## References

### Existing Features

- **Feature 027:** Product Catalog Management (Product, Supplier entities)
- **Feature 028:** Purchase Tracking & Enhanced Costing (Purchase entity, price queries)
- **Feature 013:** Production & Inventory Tracking (FIFO consumption)

### Architecture Documents

- **Constitution Principle I:** User-Centric Design (optimize for common case)
- **Constitution Principle II:** Data Integrity (session state in-memory only)
- **Constitution Principle III:** Future-Proof Schema (recency queries support web analytics)

### Code References

- `src/models/inventory_addition.py` - InventoryAddition model
- `src/models/product.py` - Product model
- `src/services/inventory_service.py` - Inventory operations
- `src/services/product_service.py` - Product operations
- `src/ui/forms/add_inventory_dialog.py` - Current inventory UI

---

**Version:** 1.0  
**Last Updated:** 2025-12-22  
**Dependencies:** Features 027 (Product Catalog), 028 (Purchase Tracking)  
**Next Steps:** Implementation via Spec Kitty workflow
