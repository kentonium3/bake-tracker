# Feature Specification: Shelf Life & Freshness Tracking

**Feature ID:** F041  
**Status:** Draft  
**Created:** 2025-01-04  
**Last Updated:** 2025-01-04  
**Author:** Kent Gale  
**Spec-Kitty Phase:** Specification

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

## Executive Summary

Add shelf life tracking and freshness indicators to inventory management without requiring manual expiration date entry. Users can set shelf life values at the Ingredient or Product level (in user-friendly time units: days, weeks, months, years), with optional per-Purchase overrides. The system computes expiration dates and displays visual freshness indicators in the Inventory tab.

**Key Benefits:**
- Addresses user testing feedback on expiration tracking
- No manual date entry burden (uses purchase date + shelf life)
- Flexible 3-tier inheritance system (Purchase > Product > Ingredient)
- Prepared for web migration (system-provided shelf life defaults)
- Minimal UI surface area (single column in Inventory list)

---

## Problem Statement

### User Need

During user testing, the issue of tracking item expiration emerged as important for inventory management. Users want to know when items are approaching end-of-life or have expired, especially for:
- Fresh ingredients (short shelf life: days to weeks)
- Ground spices (medium shelf life: months)
- Extracts and dried goods (long shelf life: years)

### Current State Limitations

**Manual Expiration Date Entry is Impractical:**
- Products have varied expiration date formats and placements
- Entering dates for every purchase is unrealistic time burden
- AI-assisted date reading from packaging is fragile and unreliable
- No existing mechanism to track or alert on expiration

### Proposed Solution

Instead of capturing actual printed expiration dates, use a **computed expiration proxy**:
1. Associate shelf life (duration) with Ingredients
2. Allow Product-level overrides (e.g., organic vs. conventional)
3. Allow Purchase-level overrides (e.g., clearance items, special cases)
4. Compute expiration: `purchase_date + shelf_life_days`
5. Display freshness indicators in Inventory tab

This approach:
- Eliminates manual date entry
- Provides actionable expiration awareness
- Supports future system-provided defaults (web migration)
- Allows user customization at multiple levels

---

## Design Principles

### Architectural Alignment

**Catalog vs Transactional Data:**
- Shelf life = catalog data (Ingredients, Products)
- Expiration dates = transactional data (computed from Purchases)
- Safe to expand ingredient shelf life via AI without touching user data

**Inheritance Hierarchy:**
- Default at Ingredient level (broadest applicability)
- Override at Product level (brand/variant specificity)
- Override at Purchase level (individual item exceptions)
- Priority: Purchase > Product > Ingredient

**Web Migration Preparedness:**
- Desktop Phase: User-managed shelf life values
- Web Phase: System-provided defaults (like ingredient hierarchy)
- User overrides always preserved

**Graceful Degradation:**
- Unset shelf life = no indicator (not "unknown")
- Feature is opt-in via shelf life data entry
- No breaking changes to existing workflows

---

## Data Model

### Schema Changes

#### Ingredient Table
```python
class Ingredient(Base):
    __tablename__ = 'ingredient'
    
    # ... existing fields ...
    
    shelf_life_days = Column(
        Integer, 
        nullable=True,
        comment="Default shelf life in days from purchase"
    )
```

#### Product Table
```python
class Product(Base):
    __tablename__ = 'product'
    
    # ... existing fields ...
    
    shelf_life_days = Column(
        Integer, 
        nullable=True,
        comment="Product-specific shelf life override (days)"
    )
```

#### Purchase Table
```python
class Purchase(Base):
    __tablename__ = 'purchase'
    
    # ... existing fields ...
    
    shelf_life_days = Column(
        Integer,
        nullable=True,
        comment="User override for this specific purchase (days)"
    )
```

### Computed Properties

#### Purchase Model Extensions
```python
class Purchase(Base):
    # ... existing definition ...
    
    @property
    def effective_shelf_life_days(self) -> Optional[int]:
        """
        Compute effective shelf life with 3-tier inheritance.
        Priority: Purchase override > Product > Ingredient
        Returns None if unset at all levels.
        """
        if self.shelf_life_days is not None:
            return self.shelf_life_days
        if self.product and self.product.shelf_life_days is not None:
            return self.product.shelf_life_days
        if (self.product and self.product.ingredient 
            and self.product.ingredient.shelf_life_days is not None):
            return self.product.ingredient.shelf_life_days
        return None
    
    @property
    def shelf_life_source(self) -> str:
        """Return where the effective shelf life comes from."""
        if self.shelf_life_days is not None:
            return "purchase_override"
        if self.product and self.product.shelf_life_days is not None:
            return "product"
        if (self.product and self.product.ingredient 
            and self.product.ingredient.shelf_life_days is not None):
            return "ingredient"
        return "unset"
    
    @property
    def computed_expiration_date(self) -> Optional[date]:
        """
        Compute expiration date based on purchase date + effective shelf life.
        Returns None if purchase_date or shelf_life is unset.
        """
        if not self.purchase_date:
            return None
        
        shelf_life = self.effective_shelf_life_days
        if shelf_life is None:
            return None
        
        return self.purchase_date + timedelta(days=shelf_life)
    
    @property
    def days_until_expiration(self) -> Optional[int]:
        """
        Days until expiration (negative if expired).
        Returns None if expiration cannot be computed.
        """
        exp_date = self.computed_expiration_date
        if exp_date is None:
            return None
        return (exp_date - date.today()).days
    
    @property
    def freshness_status(self) -> Optional[str]:
        """
        Freshness status: FRESH, EXPIRING_SOON, EXPIRED, or None.
        Returns None instead of "UNKNOWN" for unset values.
        
        Thresholds:
        - EXPIRED: days < 0
        - EXPIRING_SOON: 0 <= days <= 7
        - FRESH: days > 7
        """
        days = self.days_until_expiration
        if days is None:
            return None
        elif days < 0:
            return "EXPIRED"
        elif days <= 7:
            return "EXPIRING_SOON"
        else:
            return "FRESH"
```

### Migration Script

```sql
-- Add shelf_life_days columns to all three tables
ALTER TABLE ingredient ADD COLUMN shelf_life_days INTEGER;
ALTER TABLE product ADD COLUMN shelf_life_days INTEGER;
ALTER TABLE purchase ADD COLUMN shelf_life_days INTEGER;

-- No default values - all start as NULL (unset)
```

---

## Service Layer

### InventoryService Extensions

```python
class InventoryService:
    def get_inventory_with_freshness(self, session) -> List[Dict]:
        """
        Retrieve inventory items with computed freshness indicators.
        
        Returns enriched inventory data including:
        - Standard inventory fields
        - computed_expiration_date
        - days_until_expiration
        - freshness_status
        - shelf_life_source
        """
        inventory_items = session.query(InventoryItem).options(
            joinedload(InventoryItem.purchase)
                .joinedload(Purchase.product)
                .joinedload(Product.ingredient)
        ).all()
        
        return [
            {
                'inventory_item': item,
                'purchase': item.purchase,
                'product': item.purchase.product,
                'ingredient': item.purchase.product.ingredient,
                'expiration_date': item.purchase.computed_expiration_date,
                'days_until_expiration': item.purchase.days_until_expiration,
                'freshness_status': item.purchase.freshness_status,
                'shelf_life_source': item.purchase.shelf_life_source
            }
            for item in inventory_items
        ]
```

**Performance Note:** Uses eager loading (joinedload) to prevent N+1 query issues when accessing related ingredient/product shelf life values.

---

## User Interface

### Reusable Component: ShelfLifeInput

**Purpose:** Provide consistent shelf life entry across Ingredient, Product, and Purchase forms.

**User Experience:**
- Accepts input in user-friendly units: days, weeks, months, years
- Stores internally as integer days (for calculation consistency)
- Displays current value in most appropriate unit (e.g., 14 days → 2 weeks)
- Shows inherited value source when applicable ("from ingredient: 90 days")

**Implementation:**

```python
class ShelfLifeInput:
    """
    Reusable shelf life input widget.
    Displays/accepts user-friendly units (days/weeks/months/years).
    Stores as integer days in database.
    """
    
    UNIT_MULTIPLIERS = {
        "days": 1,
        "weeks": 7,
        "months": 30,
        "years": 365
    }
    
    @classmethod
    def days_to_display(cls, days: Optional[int]) -> tuple[Optional[int], str]:
        """
        Convert stored days to user-friendly display value and unit.
        Uses largest whole unit possible.
        
        Examples:
        - 14 days → (2, "weeks")
        - 90 days → (3, "months")
        - 365 days → (1, "years")
        - 10 days → (10, "days")
        """
        if days is None:
            return None, "days"
        
        # Try units from largest to smallest
        if days >= 365 and days % 365 == 0:
            return days // 365, "years"
        elif days >= 30 and days % 30 == 0:
            return days // 30, "months"
        elif days >= 7 and days % 7 == 0:
            return days // 7, "weeks"
        else:
            return days, "days"
    
    @classmethod
    def display_to_days(cls, value: int, unit: str) -> int:
        """Convert user input (value + unit) to days for storage."""
        return value * cls.UNIT_MULTIPLIERS[unit]
    
    def __init__(self, parent, label: str, current_days: Optional[int] = None, 
                 source_hint: Optional[str] = None):
        """
        Initialize shelf life input widget.
        
        Args:
            parent: Parent CTk widget
            label: Label text (e.g., "Shelf Life:")
            current_days: Current value in days (None if unset)
            source_hint: Optional hint about where value comes from 
                        (e.g., "from ingredient: 90 days")
        """
        self.frame = ctk.CTkFrame(parent)
        self.source_hint = source_hint
        
        # Label
        label_widget = ctk.CTkLabel(self.frame, text=label)
        label_widget.grid(row=0, column=0, padx=5, sticky="w")
        
        # Value entry
        value, unit = self.days_to_display(current_days)
        self.value_entry = ctk.CTkEntry(self.frame, width=60, placeholder_text="0")
        if value is not None:
            self.value_entry.insert(0, str(value))
        self.value_entry.grid(row=0, column=1, padx=5)
        
        # Unit dropdown
        self.unit_dropdown = ctk.CTkOptionMenu(
            self.frame,
            values=["days", "weeks", "months", "years"],
            width=80
        )
        self.unit_dropdown.set(unit)
        self.unit_dropdown.grid(row=0, column=2, padx=5)
        
        # Source hint (if provided)
        if source_hint:
            hint_label = ctk.CTkLabel(
                self.frame, 
                text=f"({source_hint})",
                text_color="gray",
                font=("Arial", 10)
            )
            hint_label.grid(row=0, column=3, padx=5)
    
    def get_days(self) -> Optional[int]:
        """
        Get current value as days (None if blank).
        Returns None for empty input or invalid values.
        """
        value_text = self.value_entry.get().strip()
        if not value_text:
            return None
        
        try:
            value = int(value_text)
            unit = self.unit_dropdown.get()
            return self.display_to_days(value, unit)
        except ValueError:
            return None
    
    def grid(self, **kwargs):
        """Allow frame to be positioned using grid."""
        self.frame.grid(**kwargs)
```

### Form Integration

#### Ingredient Edit Form

```python
class IngredientEditForm:
    def __init__(self, parent, ingredient: Optional[Ingredient] = None):
        # ... existing fields ...
        
        # Shelf life input (no source hint - this is the source)
        self.shelf_life_input = ShelfLifeInput(
            parent=self.form_frame,
            label="Shelf Life:",
            current_days=ingredient.shelf_life_days if ingredient else None
        )
        self.shelf_life_input.grid(row=5, column=0, columnspan=2, pady=5, sticky="w")
    
    def save(self):
        # ... existing save logic ...
        ingredient.shelf_life_days = self.shelf_life_input.get_days()
        # ... continue save ...
```

**User Experience:**
- Enter "2" + "weeks" → Stores as 14 days
- Next edit shows "2 weeks" (not "14 days")

#### Product Edit Form

```python
class ProductEditForm:
    def __init__(self, parent, product: Optional[Product] = None):
        # ... existing fields ...
        
        # Show inherited value from ingredient if applicable
        inherited_days = None
        source_hint = None
        if product and product.ingredient and product.ingredient.shelf_life_days:
            inherited_days = product.ingredient.shelf_life_days
            value, unit = ShelfLifeInput.days_to_display(inherited_days)
            source_hint = f"from ingredient: {value} {unit}"
        
        # Shelf life input with override capability
        self.shelf_life_input = ShelfLifeInput(
            parent=self.form_frame,
            label="Shelf Life Override:",
            current_days=product.shelf_life_days if product else None,
            source_hint=source_hint
        )
        self.shelf_life_input.grid(row=7, column=0, columnspan=2, pady=5, sticky="w")
    
    def save(self):
        # ... existing save logic ...
        product.shelf_life_days = self.shelf_life_input.get_days()
        # ... continue save ...
```

**User Experience:**
- Sees "(from ingredient: 3 months)" when ingredient has 90 days
- Can leave blank to use ingredient default
- Can override with different value (e.g., "6 months" for organic variant)

#### Purchase Edit Form

```python
class PurchaseEditForm:
    def __init__(self, parent, purchase: Optional[Purchase] = None):
        # ... existing fields ...
        
        # Show inherited value from product/ingredient if applicable
        inherited_days = None
        source_hint = None
        
        if purchase and purchase.product:
            if purchase.product.shelf_life_days:
                inherited_days = purchase.product.shelf_life_days
                value, unit = ShelfLifeInput.days_to_display(inherited_days)
                source_hint = f"from product: {value} {unit}"
            elif purchase.product.ingredient and purchase.product.ingredient.shelf_life_days:
                inherited_days = purchase.product.ingredient.shelf_life_days
                value, unit = ShelfLifeInput.days_to_display(inherited_days)
                source_hint = f"from ingredient: {value} {unit}"
        
        # Shelf life input with override capability
        self.shelf_life_input = ShelfLifeInput(
            parent=self.form_frame,
            label="Shelf Life Override:",
            current_days=purchase.shelf_life_days if purchase else None,
            source_hint=source_hint
        )
        self.shelf_life_input.grid(row=6, column=0, columnspan=2, pady=5, sticky="w")
    
    def save(self):
        # ... existing save logic ...
        purchase.shelf_life_days = self.shelf_life_input.get_days()
        # ... continue save ...
```

**User Experience:**
- Sees "(from ingredient: 1 year)" or "(from product: 6 months)"
- Can leave blank to use inherited default
- Can override for special cases (e.g., clearance item, damaged packaging)

### Inventory Tab Changes

#### Freshness Indicator Column

**Visual Design:**
- Icon-based indicators in new "Freshness" column
- 🟢 FRESH (>7 days until expiration)
- 🟡 EXPIRING_SOON (0-7 days until expiration)
- 🔴 EXPIRED (<0 days until expiration)
- (blank) No shelf life data set

**Tooltip Content:**
- "Expires in 23 days (Jan 27, 2026) (from ingredient)"
- "Expires in 5 days (Jan 9, 2026) (from product)"
- "Expired 2 days ago (Jan 2, 2026) (custom)"

**Implementation:**

```python
class InventoryTab:
    def populate_inventory_list(self):
        """Populate inventory list with freshness indicators."""
        # Clear existing list
        # ... existing clear logic ...
        
        # Get inventory with freshness data
        inventory_data = self.inventory_service.get_inventory_with_freshness(
            self.session
        )
        
        # Populate list
        for idx, row_data in enumerate(inventory_data):
            # ... existing columns ...
            
            # Freshness indicator column
            status = row_data['freshness_status']
            if status is not None:
                # Show indicator with tooltip
                freshness_icon = self._get_freshness_icon(status)
                freshness_label = ctk.CTkLabel(
                    row_frame, 
                    text=freshness_icon,
                    font=("Arial", 14)
                )
                freshness_label.grid(row=idx, column=5, padx=5)
                
                # Bind tooltip
                tooltip_text = self._get_freshness_tooltip(row_data)
                ToolTip(freshness_label, text=tooltip_text)
            else:
                # No indicator for unset shelf life
                empty_label = ctk.CTkLabel(row_frame, text="")
                empty_label.grid(row=idx, column=5, padx=5)
    
    def _get_freshness_icon(self, status: str) -> str:
        """Return emoji for status (never called with None)."""
        return {
            "FRESH": "🟢",
            "EXPIRING_SOON": "🟡",
            "EXPIRED": "🔴"
        }[status]
    
    def _get_freshness_tooltip(self, row_data: dict) -> str:
        """Generate tooltip text with source information."""
        days = row_data['days_until_expiration']
        exp_date = row_data['expiration_date']
        source = row_data['shelf_life_source']
        
        # Base expiration message
        if days < 0:
            base_msg = f"Expired {abs(days)} day(s) ago"
        elif days <= 7:
            base_msg = f"Expires in {days} day(s)"
        else:
            base_msg = f"Expires in {days} days"
        
        # Add formatted date
        date_str = exp_date.strftime('%b %d, %Y')
        
        # Add source hint
        source_text = {
            "purchase_override": "custom",
            "product": "from product",
            "ingredient": "from ingredient"
        }.get(source, "")
        
        return f"{base_msg} ({date_str}) ({source_text})"
```

---

## User Workflows

### Workflow 1: Set Default Shelf Life for Ingredient

**Actor:** Baker  
**Precondition:** Ingredient "All-Purpose Flour" exists  

**Steps:**
1. Open Ingredients tab
2. Edit "All-Purpose Flour"
3. Enter shelf life: "6" + "months"
4. Save

**Result:**
- Ingredient shelf_life_days = 180
- All products using this ingredient inherit 180-day shelf life
- All future purchases compute expiration as purchase_date + 180 days
- Inventory shows freshness indicators for existing inventory

### Workflow 2: Override Shelf Life for Organic Product

**Actor:** Baker  
**Precondition:** 
- Ingredient "All-Purpose Flour" has shelf_life_days = 180
- Product "King Arthur Organic AP" exists

**Steps:**
1. Open Products tab
2. Edit "King Arthur Organic AP"
3. See "(from ingredient: 6 months)" in gray text
4. Enter shelf life override: "3" + "months"
5. Save

**Result:**
- Product shelf_life_days = 90
- Product now uses 90 days instead of ingredient's 180 days
- Purchases of this product compute expiration as purchase_date + 90 days

### Workflow 3: Override Shelf Life for Clearance Purchase

**Actor:** Baker  
**Precondition:**
- Product "King Arthur Organic AP" has shelf_life_days = 90
- User is recording a clearance item nearing expiration

**Steps:**
1. Open Purchases tab
2. Create new purchase for "King Arthur Organic AP"
3. Enter purchase date: 2025-01-01
4. See "(from product: 3 months)" in gray text
5. Enter shelf life override: "30" + "days"
6. Save

**Result:**
- Purchase shelf_life_days = 30
- This specific purchase uses 30 days (not product's 90)
- Inventory shows expiration: 2025-01-31
- Freshness indicator shows status based on proximity to Jan 31

### Workflow 4: Check Inventory Freshness

**Actor:** Baker  
**Precondition:** Inventory has items with varying shelf life

**Steps:**
1. Open Inventory tab
2. Scan "Freshness" column
3. See:
   - 🟢 Most items fresh
   - 🟡 Butter expiring in 4 days
   - 🔴 Milk expired 1 day ago
4. Hover over 🟡 butter indicator
5. See tooltip: "Expires in 4 days (Jan 8, 2026) (from ingredient)"

**Result:**
- User has immediate visual awareness of expiration status
- Can prioritize using expiring items
- Can plan replacement purchases

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input Layer                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ User enters shelf life
                              │ (e.g., "2 weeks")
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ShelfLifeInput Component                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ display_to_days(2, "weeks") → 14                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Stores as integer days
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Database Layer                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Ingredient.shelf_life_days = 14                       │  │
│  │ Product.shelf_life_days = NULL                        │  │
│  │ Purchase.shelf_life_days = NULL                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Query with joins
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Computed Properties Layer                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ purchase.effective_shelf_life_days                    │  │
│  │   → Checks Purchase (NULL)                            │  │
│  │   → Checks Product (NULL)                             │  │
│  │   → Returns Ingredient (14)                           │  │
│  │                                                        │  │
│  │ purchase.computed_expiration_date                     │  │
│  │   → 2025-01-01 + timedelta(days=14)                  │  │
│  │   → 2025-01-15                                        │  │
│  │                                                        │  │
│  │ purchase.days_until_expiration                        │  │
│  │   → 2025-01-15 - 2025-01-04                          │  │
│  │   → 11 days                                           │  │
│  │                                                        │  │
│  │ purchase.freshness_status                             │  │
│  │   → 11 > 7 → "FRESH"                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Service layer enrichment
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  UI Display Layer                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Inventory Tab                                         │  │
│  │ ┌──────────┬──────────┬──────────┬──────────────┐     │  │
│  │ │ Product  │ Quantity │ Date     │ Freshness    │     │  │
│  │ ├──────────┼──────────┼──────────┼──────────────┤     │  │
│  │ │ KA AP    │ 5 lb     │ 01/01/25 │ 🟢           │     │  │
│  │ └──────────┴──────────┴──────────┴──────────────┘     │  │
│  │                                                        │  │
│  │ Tooltip: "Expires in 11 days (Jan 15, 2026)          │  │
│  │           (from ingredient)"                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Gap Analysis

### Current State
- ❌ No shelf life tracking
- ❌ No expiration awareness
- ❌ No freshness indicators in inventory
- ❌ Users manually track expiration separately

### Phase 2 Implementation Adds
- ✅ shelf_life_days column on Ingredient, Product, Purchase tables
- ✅ ShelfLifeInput component for user-friendly time entry
- ✅ 3-tier inheritance (Purchase > Product > Ingredient)
- ✅ Computed expiration dates via properties
- ✅ Freshness status calculation (FRESH/EXPIRING_SOON/EXPIRED)
- ✅ Visual indicators in Inventory tab
- ✅ Tooltips with expiration details and source

### Future Enhancements (Out of Scope)
- ⏳ Filter inventory by freshness status
- ⏳ Sort inventory by expiration date
- ⏳ Expiration report (items expiring this week/month)
- ⏳ System-provided shelf life defaults (web migration)
- ⏳ Alerts/notifications for expiring items
- ⏳ Dashboard widget showing expiration summary

---

## Implementation Tasks

### Phase 1: Data Model & Service Layer
- [ ] Add shelf_life_days columns to Ingredient, Product, Purchase tables
- [ ] Implement computed properties on Purchase model
- [ ] Add InventoryService.get_inventory_with_freshness() method
- [ ] Write unit tests for computed properties
- [ ] Write unit tests for service layer

### Phase 2: Reusable UI Component
- [ ] Implement ShelfLifeInput component
- [ ] Implement days_to_display() conversion logic
- [ ] Implement display_to_days() conversion logic
- [ ] Write unit tests for conversion logic
- [ ] Test component with all time units

### Phase 3: Form Integration
- [ ] Add ShelfLifeInput to Ingredient edit form
- [ ] Add ShelfLifeInput to Product edit form (with source hint)
- [ ] Add ShelfLifeInput to Purchase edit form (with source hint)
- [ ] Update save logic in all forms
- [ ] Test 3-tier inheritance display

### Phase 4: Inventory Tab Display
- [ ] Add "Freshness" column to inventory list
- [ ] Implement freshness icon display logic
- [ ] Implement tooltip generation logic
- [ ] Test visual indicators for all states
- [ ] Test graceful handling of unset shelf life

### Phase 5: Import/Export
- [ ] Add shelf_life_days to normalized export
- [ ] Add shelf_life_days to denormalized export
- [ ] Add shelf_life_days to import handling
- [ ] Test round-trip export/import

### Phase 6: Testing & Documentation
- [ ] Integration tests for full workflow
- [ ] User acceptance testing with real data
- [ ] Update user documentation
- [ ] Update requirements documents

---

## Testing Strategy

### Unit Tests

**Model Tests:**
```python
def test_purchase_effective_shelf_life_purchase_override():
    """Purchase override takes precedence."""
    ingredient = Ingredient(shelf_life_days=180)
    product = Product(ingredient=ingredient, shelf_life_days=90)
    purchase = Purchase(product=product, shelf_life_days=30)
    assert purchase.effective_shelf_life_days == 30

def test_purchase_effective_shelf_life_product_fallback():
    """Product value used when purchase is None."""
    ingredient = Ingredient(shelf_life_days=180)
    product = Product(ingredient=ingredient, shelf_life_days=90)
    purchase = Purchase(product=product, shelf_life_days=None)
    assert purchase.effective_shelf_life_days == 90

def test_purchase_effective_shelf_life_ingredient_fallback():
    """Ingredient value used when product and purchase are None."""
    ingredient = Ingredient(shelf_life_days=180)
    product = Product(ingredient=ingredient, shelf_life_days=None)
    purchase = Purchase(product=product, shelf_life_days=None)
    assert purchase.effective_shelf_life_days == 180

def test_purchase_effective_shelf_life_all_unset():
    """Returns None when all levels are unset."""
    ingredient = Ingredient(shelf_life_days=None)
    product = Product(ingredient=ingredient, shelf_life_days=None)
    purchase = Purchase(product=product, shelf_life_days=None)
    assert purchase.effective_shelf_life_days is None

def test_purchase_freshness_status_fresh():
    """Items >7 days from expiration are FRESH."""
    purchase = create_purchase_with_shelf_life(
        purchase_date=date(2025, 1, 1),
        shelf_life_days=20
    )
    # Today is 2025-01-04, expires 2025-01-21 (17 days)
    assert purchase.freshness_status == "FRESH"

def test_purchase_freshness_status_expiring_soon():
    """Items 0-7 days from expiration are EXPIRING_SOON."""
    purchase = create_purchase_with_shelf_life(
        purchase_date=date(2025, 1, 1),
        shelf_life_days=8
    )
    # Today is 2025-01-04, expires 2025-01-09 (5 days)
    assert purchase.freshness_status == "EXPIRING_SOON"

def test_purchase_freshness_status_expired():
    """Items past expiration are EXPIRED."""
    purchase = create_purchase_with_shelf_life(
        purchase_date=date(2024, 12, 1),
        shelf_life_days=30
    )
    # Today is 2025-01-04, expired 2024-12-31 (-4 days)
    assert purchase.freshness_status == "EXPIRED"

def test_purchase_freshness_status_unset():
    """Items with no shelf life return None status."""
    purchase = create_purchase_with_shelf_life(
        purchase_date=date(2025, 1, 1),
        shelf_life_days=None
    )
    assert purchase.freshness_status is None
```

**Component Tests:**
```python
def test_shelf_life_input_days_to_display_weeks():
    """14 days displays as 2 weeks."""
    value, unit = ShelfLifeInput.days_to_display(14)
    assert value == 2
    assert unit == "weeks"

def test_shelf_life_input_days_to_display_months():
    """90 days displays as 3 months."""
    value, unit = ShelfLifeInput.days_to_display(90)
    assert value == 3
    assert unit == "months"

def test_shelf_life_input_days_to_display_years():
    """365 days displays as 1 year."""
    value, unit = ShelfLifeInput.days_to_display(365)
    assert value == 1
    assert unit == "years"

def test_shelf_life_input_days_to_display_odd_days():
    """10 days displays as 10 days (no conversion)."""
    value, unit = ShelfLifeInput.days_to_display(10)
    assert value == 10
    assert unit == "days"

def test_shelf_life_input_display_to_days():
    """Conversion from user units to days."""
    assert ShelfLifeInput.display_to_days(2, "weeks") == 14
    assert ShelfLifeInput.display_to_days(3, "months") == 90
    assert ShelfLifeInput.display_to_days(1, "years") == 365
    assert ShelfLifeInput.display_to_days(5, "days") == 5
```

### Integration Tests

**Workflow Tests:**
```python
def test_ingredient_shelf_life_propagation():
    """Setting ingredient shelf life affects products and purchases."""
    # Create ingredient with shelf life
    ingredient = create_ingredient(shelf_life_days=180)
    product = create_product(ingredient=ingredient)
    purchase = create_purchase(product=product, purchase_date=date(2025, 1, 1))
    
    # Verify propagation
    assert purchase.effective_shelf_life_days == 180
    assert purchase.computed_expiration_date == date(2025, 6, 30)

def test_product_override_blocks_ingredient():
    """Product override prevents ingredient value from being used."""
    ingredient = create_ingredient(shelf_life_days=180)
    product = create_product(ingredient=ingredient, shelf_life_days=90)
    purchase = create_purchase(product=product, purchase_date=date(2025, 1, 1))
    
    assert purchase.effective_shelf_life_days == 90
    assert purchase.computed_expiration_date == date(2025, 4, 1)

def test_purchase_override_blocks_all():
    """Purchase override takes precedence over product and ingredient."""
    ingredient = create_ingredient(shelf_life_days=180)
    product = create_product(ingredient=ingredient, shelf_life_days=90)
    purchase = create_purchase(
        product=product,
        shelf_life_days=30,
        purchase_date=date(2025, 1, 1)
    )
    
    assert purchase.effective_shelf_life_days == 30
    assert purchase.computed_expiration_date == date(2025, 1, 31)
```

### User Acceptance Tests

**Test Scenario 1: Set Ingredient Shelf Life**
- [ ] Open ingredient edit form for "All-Purpose Flour"
- [ ] Enter shelf life: 6 months
- [ ] Save ingredient
- [ ] Verify stored as 180 days in database
- [ ] Reopen form, verify displays as "6 months"

**Test Scenario 2: Override at Product Level**
- [ ] Open product edit form for "King Arthur Organic AP"
- [ ] See "(from ingredient: 6 months)" hint
- [ ] Enter override: 3 months
- [ ] Save product
- [ ] Create purchase, verify uses 90 days not 180 days

**Test Scenario 3: Override at Purchase Level**
- [ ] Create purchase for clearance item
- [ ] See "(from product: 3 months)" or "(from ingredient: 6 months)" hint
- [ ] Enter override: 2 weeks
- [ ] Save purchase
- [ ] Verify inventory shows expiration in 14 days from purchase date

**Test Scenario 4: Inventory Freshness Display**
- [ ] Create purchases with varying shelf life
- [ ] Open Inventory tab
- [ ] Verify 🟢 for items >7 days from expiration
- [ ] Verify 🟡 for items 0-7 days from expiration
- [ ] Verify 🔴 for expired items
- [ ] Verify blank for items with no shelf life
- [ ] Hover tooltip shows correct expiration date and source

---

## Success Criteria

### Must Have (Phase 2)
- [x] Schema includes shelf_life_days on Ingredient, Product, Purchase
- [x] ShelfLifeInput component reusable across all forms
- [x] 3-tier inheritance works (Purchase > Product > Ingredient)
- [x] User can enter shelf life in days/weeks/months/years
- [x] Values stored consistently as integer days
- [x] Display converts days to most appropriate unit
- [x] Computed expiration dates accurate
- [x] Freshness status calculated correctly
- [x] Inventory tab shows visual indicators
- [x] Tooltips provide expiration details and source
- [x] Unset shelf life shows no indicator (not "unknown")
- [x] No N+1 query issues (eager loading)

### Should Have (Future)
- [ ] Filter inventory by freshness status
- [ ] Sort inventory by expiration date
- [ ] Expiration report
- [ ] System-provided shelf life defaults

### Nice to Have (Future)
- [ ] Dashboard widget for expiration summary
- [ ] Alerts/notifications for expiring items
- [ ] Bulk shelf life updates
- [ ] Shelf life history/audit trail

---

## Related Documents

- **Requirements:** `/docs/requirements/req_ingredients.md`
- **Requirements:** `/docs/requirements/req_products.md`
- **Constitution:** `/.kittify/memory/constitution.md`
- **Data Model:** `/docs/design/architecture.md`
- **Bug Reports:** TBD (to be created during implementation)

---

## Approval & Sign-off

**Feature Owner:** Kent Gale  
**Status:** Draft - Ready for Implementation  
**Next Steps:** Begin Phase 1 implementation (data model & service layer)

---

**END OF FEATURE SPECIFICATION**
