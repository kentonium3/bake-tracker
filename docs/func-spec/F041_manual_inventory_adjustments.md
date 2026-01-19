# Manual Inventory Adjustments - Feature Specification

**Feature ID**: F041
**Feature Name**: Manual Inventory Adjustments (Depletions Only)
**Priority**: MEDIUM (Phase 2 completion)
**Status**: Design Specification
**Created**: 2026-01-05
**Updated**: 2026-01-07
**Dependencies**: Inventory system (F028, F029) ✅
**Constitutional References**: Principle I (Data Integrity), Principle V (Layered Architecture)

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

**The requirements (req_inventory.md Section 3.2) and business logic are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Scope Clarification (Updated 2026-01-07)

**This feature supports DEPLETIONS ONLY (inventory reductions).**

**In Scope:**
- Manual inventory reductions for spoilage, gifts, corrections, ad hoc usage
- Depletion reason tracking with optional notes
- Live preview of quantity/cost impact
- Audit trail integration
- FIFO system integration

**Out of Scope (by design decision):**
- Inventory additions/increases are NOT supported through manual adjustment
- All inventory increases must go through the **Purchase workflow**
- This includes: found inventory, donations, missed purchases, initial inventory setup

**Rationale:** An inventory increase implies a purchase occurred. The Purchase workflow ensures proper data collection (date, supplier, price) for accurate FIFO costing and audit trails. Donations and found inventory should be recorded as $0 purchases to maintain data integrity.

---

## Executive Summary

Manual Inventory Adjustments closes a critical gap in the inventory tracking system: real-world inventory changes that occur outside the application. Current system only tracks automatic depletions (production/assembly), but cannot handle:
- **Spoilage** (ingredient went bad, must be discarded)
- **Gifts** (gave ingredients to friend/family, not tracked in app)
- **Corrections** (physical count doesn't match system, need adjustment)
- **Ad hoc usage** (used ingredients for testing, personal consumption)

**Without this feature**: Inventory becomes inaccurate over time, planning unreliable
**With this feature**: Users can record real-world changes, maintain inventory accuracy

**Scope**:
- Manual depletion interface (reduce inventory)
- Depletion reason tracking (why adjusted)
- Notes field (context)
- Validation (cannot deplete below zero)
- Integration with existing FIFO system
- Audit trail (who, when, how much, why)

---

## 1. Problem Statement

### 1.1 Real-World Inventory Changes

**Current Limitation**:
```
System tracks:
✓ Production depletions (recipe consumed ingredients)
✓ Assembly depletions (future Phase 3)

System does NOT track:
✗ Spoilage (flour got moldy, discard 5 cups)
✗ Gifts (gave friend 2 cups chocolate chips)
✗ Corrections (physical count shows 10 cups, system shows 15 cups)
✗ Ad hoc usage (tested new recipe outside app, used 3 eggs)
```

**Impact**:
- Inventory records drift from reality
- Planning system shows incorrect availability
- User discovers shortfalls during production ("System says I have 10 cups flour, but I only have 5")
- FIFO cost calculations become inaccurate

### 1.2 User Pain Points

**Scenario 1: Spoilage**
```
User discovers bag of flour infested with weevils.
Must discard entire bag (5 cups remaining).
System still shows 5 cups available.
Next week: Planning says "sufficient flour", but user has none.
Result: Emergency shopping trip, production delay.
```

**Scenario 2: Gift**
```
User gives friend 3 cups chocolate chips for holiday baking.
Chips came from FIFO purchase (oldest bag).
System still shows 3 cups available from that purchase.
Later: Production tries to use those chips, discovers they're gone.
Result: Production cannot complete.
```

**Scenario 3: Physical Count Correction**
```
User does periodic physical inventory check.
System shows: 10 cups sugar
Actual: 7 cups sugar
Reason: Unknown (spillage? measurement error? untracked usage?)
System needs correction: Reduce by 3 cups.
Result: Inventory accuracy restored.
```

**Scenario 4: Ad Hoc Usage**
```
User tests new recipe outside app (personal consumption).
Used: 2 eggs, 1 cup flour, 0.5 cup butter.
These depleted inventory but not tracked.
System shows incorrect available quantities.
Result: Planning calculations wrong.
```

---

## 2. Proposed Solution

### 2.1 Manual Adjustment Interface

**Location**: SHOP Mode → Inventory tab → [Adjust Inventory] action button

**Workflow**:
```
User identifies inventory item needing adjustment
  ↓
Clicks [Adjust Inventory] button
  ↓
Adjustment dialog appears:
  - Purchase: King Arthur AP Flour 25lb (2024-12-15)
  - Current Quantity: 10 cups
  - Adjust By: [____] (user enters amount to deplete)
  - Reason: [Spoilage ▼] (dropdown)
  - Notes: [Optional explanation...]
  ↓
User enters: -5 cups, Spoilage, "Weevils discovered"
  ↓
System validates:
  ✓ New quantity = 10 - 5 = 5 cups (valid, non-negative)
  ↓
System creates InventoryDepletion record:
  - inventory_item_id: Purchase XYZ
  - quantity_depleted: -5
  - depletion_reason: SPOILAGE
  - depletion_date: 2026-01-05
  - notes: "Weevils discovered"
  ↓
System updates inventory_item:
  - current_quantity: 10 → 5
  ↓
User sees updated inventory list:
  - King Arthur AP Flour: 5 cups remaining
```

### 2.2 Depletion Reasons

**Enum: DepletionReason**
```python
class DepletionReason(str, Enum):
    # Automatic (system-generated)
    PRODUCTION = "production"        # Recipe execution
    ASSEMBLY = "assembly"            # Bundle assembly (Phase 3)

    # Manual (user-initiated)
    SPOILAGE = "spoilage"           # Ingredient went bad
    GIFT = "gift"                   # Gave to friend/family
    CORRECTION = "correction"       # Physical count adjustment
    AD_HOC_USAGE = "ad_hoc_usage"   # Personal/testing usage
    OTHER = "other"                 # User-specified reason
```

**UI Labels:**
- SPOILAGE: "Spoilage/Waste"
- GIFT: "Gift/Donation"
- CORRECTION: "Physical Count Correction"
- AD_HOC_USAGE: "Ad Hoc Usage (Testing/Personal)"
- OTHER: "Other (specify in notes)"

---

## 3. Data Model (No Schema Changes)

### 3.1 Existing Models (Reused)

**InventoryDepletion** (already exists, just extend reason enum):
```python
class InventoryDepletion(BaseModel):
    __tablename__ = "inventory_depletions"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid4()))

    # Which purchase/inventory item
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
    purchase_id = Column(Integer, ForeignKey("purchases.id"))

    # Depletion details
    quantity_depleted = Column(Numeric(10, 2))  # Negative value
    depletion_date = Column(DateTime, default=datetime.now)
    depletion_reason = Column(String(50))  # EXTEND with manual reasons

    # Context (optional for automatic, populated for manual)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)  # USER NOTES for manual adjustments

    # Cost tracking
    cost = Column(Numeric(10, 2))  # Computed at depletion time

    # Audit
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(100), nullable=True)  # User identifier
```

**Key Insight:** No schema changes needed! Just extend existing DepletionReason enum and use notes field for user context.

---

## 4. Service Layer

### 4.1 Inventory Service Extension

**File:** `src/services/inventory_service.py`

**New Method:**
```python
class InventoryService:
    """Existing inventory service with manual adjustment extension."""

    def manual_adjustment(
        self,
        inventory_item_id: int,
        quantity_adjustment: Decimal,
        reason: DepletionReason,
        notes: Optional[str],
        user: str,
        session: Session
    ) -> InventoryDepletion:
        """
        Manually adjust inventory (spoilage, gift, correction, ad hoc).

        Args:
            inventory_item_id: Which inventory item to adjust
            quantity_adjustment: Amount to deplete (negative value)
            reason: Why (SPOILAGE, GIFT, CORRECTION, AD_HOC_USAGE, OTHER)
            notes: User explanation (required for OTHER, optional otherwise)
            user: Who made adjustment (for audit)
            session: DB session

        Returns:
            InventoryDepletion record created

        Raises:
            ValueError: Invalid adjustment (would go negative)
            ValueError: Notes required when reason=OTHER
        """
        # Validation
        if quantity_adjustment >= 0:
            raise ValueError("Quantity adjustment must be negative (depletion)")

        if reason == DepletionReason.OTHER and not notes:
            raise ValueError("Notes required when reason is OTHER")

        # Get inventory item
        item = session.query(InventoryItem).get(inventory_item_id)
        if not item:
            raise ValueError(f"Inventory item {inventory_item_id} not found")

        # Validate won't go negative
        new_quantity = item.current_quantity + quantity_adjustment  # adjustment is negative
        if new_quantity < 0:
            raise ValueError(
                f"Cannot deplete {abs(quantity_adjustment)}: "
                f"only {item.current_quantity} available"
            )

        # Calculate cost (for accounting)
        unit_cost = item.unit_cost
        cost = abs(quantity_adjustment) * unit_cost

        # Create depletion record
        depletion = InventoryDepletion(
            inventory_item_id=inventory_item_id,
            purchase_id=item.purchase_id,
            quantity_depleted=quantity_adjustment,  # Negative
            depletion_date=datetime.now(),
            depletion_reason=reason.value,
            related_entity_type="manual_adjustment",
            related_entity_id=None,
            notes=notes,
            cost=cost,
            created_by=user
        )
        session.add(depletion)

        # Update inventory item
        item.current_quantity = new_quantity

        session.commit()

        return depletion
```

**Usage Example:**
```python
# User adjusts inventory for spoilage
depletion = inventory_service.manual_adjustment(
    inventory_item_id=123,
    quantity_adjustment=Decimal("-5.0"),  # Deplete 5 cups
    reason=DepletionReason.SPOILAGE,
    notes="Weevils discovered in bag",
    user="marianne@example.com",
    session=session
)

# Result:
# - InventoryDepletion record created
# - inventory_item.current_quantity: 10 → 5
# - Audit trail preserved (who, when, why, notes)
```

---

## 5. UI Design

### 5.1 Inventory Tab Enhancement

**Existing Inventory Tab (SHOP Mode):**
```
┌─ Inventory ──────────────────────────────────────────────┐
│  [+ Add Purchase] [Refresh]                 [Export]     │
│                                                           │
│  Ingredient Filter: [All ▼]  Freshness: [All ▼]          │
│                                                           │
│  ┌─ Inventory List ─────────────────────────────────┐   │
│  │ Ingredient         Product           Qty    Fresh │   │
│  │ ────────────────   ──────────────   ─────  ───── │   │
│  │ All-Purpose Flour  King Arthur 25lb  10 c  🟢    │   │
│  │   Purchase: 2024-12-15  Cost: $0.64/c             │   │
│  │   [View History] [Adjust] ← NEW ACTION            │   │
│  │                                                     │   │
│  │ Chocolate Chips    Nestle 12oz       3 c   🟡    │   │
│  │   Purchase: 2024-12-20  Cost: $1.20/c             │   │
│  │   [View History] [Adjust] ← NEW ACTION            │   │
│  └───────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

### 5.2 Manual Adjustment Dialog

**Triggered by: Click [Adjust] button on inventory item**

```
┌─ Adjust Inventory ─────────────────────────────────────┐
│                                                         │
│  Purchase Information:                                  │
│  • Product: King Arthur All-Purpose Flour 25lb         │
│  • Purchase Date: 2024-12-15                            │
│  • Purchase Price: $15.99 ($0.64/cup)                   │
│                                                         │
│  Current Inventory:                                     │
│  • Available: 10.0 cups                                 │
│  • Unit Cost: $0.64/cup                                 │
│  • Freshness: 🟢 Fresh (expires in 45 days)            │
│                                                         │
│  ──────────────────────────────────────────────────    │
│                                                         │
│  Adjustment:                                            │
│  Reduce By: [______] cups (enter positive number)      │
│             ↑ User types: 5                             │
│                                                         │
│  Reason: [Spoilage/Waste ▼]                            │
│    Options:                                             │
│    • Spoilage/Waste                                     │
│    • Gift/Donation                                      │
│    • Physical Count Correction                          │
│    • Ad Hoc Usage (Testing/Personal)                    │
│    • Other (specify in notes)                           │
│                                                         │
│  Notes: (optional)                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Weevils discovered in bag. Entire bag           │   │
│  │ discarded.                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Preview:                                               │
│  • New Quantity: 5.0 cups (10.0 - 5.0)                 │
│  • Cost Impact: $3.20 (5 cups × $0.64)                 │
│                                                         │
│  [Cancel]  [Apply Adjustment]                           │
└─────────────────────────────────────────────────────────┘
```

**Validation:**
- Reduce By must be positive number
- Cannot reduce by more than current quantity (error: "Only 10 cups available")
- Notes required if Reason = "Other"

**Success:**
```
✓ Adjustment applied successfully
  - 5.0 cups depleted (Spoilage/Waste)
  - New quantity: 5.0 cups
```

### 5.3 Depletion History View (Enhanced)

**Existing depletion history shows automatic + manual:**

```
┌─ Depletion History: King Arthur AP Flour ───────────────┐
│                                                          │
│  Purchase: 2024-12-15 | Original: 25.0 cups             │
│  Current: 5.0 cups    | Depleted: 20.0 cups total       │
│                                                          │
│  ┌─ History ──────────────────────────────────────┐     │
│  │ Date       Reason         Qty      Cost  Notes │     │
│  │ ─────────  ────────────   ──────   ────  ───── │     │
│  │ 2025-01-05 Spoilage       -5.0 c  $3.20 Weevi…│     │
│  │ 2025-01-04 Production     -7.0 c  $4.48 Sugar…│     │
│  │ 2024-12-28 Production     -8.0 c  $5.12 Brown…│     │
│  └──────────────────────────────────────────────────┘     │
│                                                          │
│  [Close]                                                 │
└──────────────────────────────────────────────────────────┘
```

**Notes Column (Expandable):**
- Truncated: "Weevi..." → Hover shows full: "Weevils discovered in bag"
- Manual adjustments always show notes
- Production/Assembly may have notes (optional)

---

## 6. Functional Requirements

### 6.1 Manual Adjustment Interface

**REQ-F041-001:** System shall provide [Adjust] action on each inventory item
**REQ-F041-002:** Adjustment dialog shall display current inventory quantity
**REQ-F041-003:** User shall enter positive number to reduce inventory
**REQ-F041-004:** User shall select depletion reason from dropdown
**REQ-F041-005:** User shall optionally enter notes (required for OTHER reason)
**REQ-F041-006:** System shall show preview of new quantity before applying

### 6.2 Validation

**REQ-F041-007:** System shall validate adjustment amount is positive
**REQ-F041-008:** System shall validate new quantity ≥ 0 (cannot go negative)
**REQ-F041-009:** System shall require notes when reason = OTHER
**REQ-F041-010:** System shall show error message for invalid adjustments

### 6.3 Depletion Tracking

**REQ-F041-011:** System shall create InventoryDepletion record for manual adjustment
**REQ-F041-012:** Depletion shall include: quantity, reason, notes, user, timestamp
**REQ-F041-013:** Depletion shall calculate cost impact (quantity × unit_cost)
**REQ-F041-014:** System shall update inventory_item.current_quantity
**REQ-F041-015:** Depletion records shall be immutable (audit trail)

### 6.4 Depletion History

**REQ-F041-016:** Depletion history shall show all depletions (automatic + manual)
**REQ-F041-017:** Manual adjustments shall display reason and notes
**REQ-F041-018:** History shall show: date, reason, quantity, cost, notes
**REQ-F041-019:** History shall be sorted by date (newest first)

### 6.5 Integration

**REQ-F041-020:** Manual adjustments shall use existing InventoryDepletion model
**REQ-F041-021:** Manual adjustments shall respect FIFO ordering (deplete oldest first when viewing)
**REQ-F041-022:** Cost calculations shall include manual adjustment costs
**REQ-F041-023:** Planning system shall account for manually adjusted inventory

---

## 7. Non-Functional Requirements

### 7.1 Usability

**REQ-F041-NFR-001:** Adjustment dialog shall be accessible from inventory list
**REQ-F041-NFR-002:** UI shall clearly show impact before applying (preview)
**REQ-F041-NFR-003:** Error messages shall be specific and actionable
**REQ-F041-NFR-004:** Success confirmation shall show what changed

### 7.2 Data Integrity

**REQ-F041-NFR-005:** Inventory quantities shall never go negative (enforced)
**REQ-F041-NFR-006:** Depletion records shall be immutable after creation
**REQ-F041-NFR-007:** Audit trail shall capture who, when, why, how much

### 7.3 Performance

**REQ-F041-NFR-008:** Adjustment operation shall complete in <200ms
**REQ-F041-NFR-009:** Depletion history query shall complete in <100ms

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Validation Logic:**
```python
def test_manual_adjustment_validates_positive():
    """Adjustment amount must be positive."""
    with pytest.raises(ValueError, match="must be negative"):
        inventory_service.manual_adjustment(
            inventory_item_id=1,
            quantity_adjustment=Decimal("5.0"),  # Wrong: positive
            reason=DepletionReason.SPOILAGE,
            notes=None,
            user="test",
            session=session
        )

def test_manual_adjustment_prevents_negative_inventory():
    """Cannot deplete more than available."""
    item = InventoryItem(current_quantity=Decimal("3.0"))
    session.add(item)
    session.commit()

    with pytest.raises(ValueError, match="only 3.0 available"):
        inventory_service.manual_adjustment(
            inventory_item_id=item.id,
            quantity_adjustment=Decimal("-5.0"),  # Want 5, only have 3
            reason=DepletionReason.SPOILAGE,
            notes=None,
            user="test",
            session=session
        )

def test_manual_adjustment_requires_notes_for_other():
    """Notes required when reason=OTHER."""
    with pytest.raises(ValueError, match="Notes required"):
        inventory_service.manual_adjustment(
            inventory_item_id=1,
            quantity_adjustment=Decimal("-2.0"),
            reason=DepletionReason.OTHER,
            notes=None,  # Missing notes
            user="test",
            session=session
        )
```

**Depletion Logic:**
```python
def test_manual_adjustment_creates_depletion_record():
    """Manual adjustment creates InventoryDepletion."""
    item = InventoryItem(
        current_quantity=Decimal("10.0"),
        unit_cost=Decimal("0.64")
    )
    session.add(item)
    session.commit()

    depletion = inventory_service.manual_adjustment(
        inventory_item_id=item.id,
        quantity_adjustment=Decimal("-5.0"),
        reason=DepletionReason.SPOILAGE,
        notes="Weevils discovered",
        user="test@example.com",
        session=session
    )

    assert depletion.quantity_depleted == Decimal("-5.0")
    assert depletion.depletion_reason == "spoilage"
    assert depletion.notes == "Weevils discovered"
    assert depletion.created_by == "test@example.com"
    assert depletion.cost == Decimal("3.20")  # 5 × $0.64

def test_manual_adjustment_updates_inventory():
    """Manual adjustment updates current_quantity."""
    item = InventoryItem(current_quantity=Decimal("10.0"))
    session.add(item)
    session.commit()

    inventory_service.manual_adjustment(
        inventory_item_id=item.id,
        quantity_adjustment=Decimal("-5.0"),
        reason=DepletionReason.GIFT,
        notes="Gave to friend",
        user="test",
        session=session
    )

    session.refresh(item)
    assert item.current_quantity == Decimal("5.0")
```

### 8.2 Integration Tests

**End-to-End Workflow:**
```python
def test_manual_adjustment_full_workflow():
    """Test complete manual adjustment workflow."""
    # 1. Create purchase
    purchase = Purchase(
        product_id=flour_product.id,
        purchase_quantity=Decimal("25.0"),
        purchase_unit="cups",
        purchase_price=Decimal("15.99"),
        purchase_date=date(2024, 12, 15)
    )
    session.add(purchase)
    session.commit()

    # 2. Create inventory item (automatic)
    item = InventoryItem(
        purchase_id=purchase.id,
        current_quantity=Decimal("25.0"),
        unit="cups",
        unit_cost=Decimal("0.6396")
    )
    session.add(item)
    session.commit()

    # 3. Production depletes some
    depletion1 = inventory_service.deplete_fifo(
        ingredient_id=flour.id,
        quantity_needed=Decimal("8.0"),
        reason=DepletionReason.PRODUCTION,
        related_entity=production_run,
        session=session
    )
    session.refresh(item)
    assert item.current_quantity == Decimal("17.0")

    # 4. Manual adjustment (spoilage)
    depletion2 = inventory_service.manual_adjustment(
        inventory_item_id=item.id,
        quantity_adjustment=Decimal("-5.0"),
        reason=DepletionReason.SPOILAGE,
        notes="Weevils discovered",
        user="marianne@example.com",
        session=session
    )
    session.refresh(item)
    assert item.current_quantity == Decimal("12.0")

    # 5. Query depletion history
    history = inventory_service.get_depletion_history(item.id, session)
    assert len(history) == 2
    assert history[0].depletion_reason == "spoilage"
    assert history[0].notes == "Weevils discovered"
    assert history[1].depletion_reason == "production"
```

### 8.3 User Acceptance Tests

**UAT-001: Record Spoilage**
```
Given: User has 10 cups flour in inventory
When: User discovers bag has weevils, must discard 5 cups
Then: User clicks [Adjust] on flour item
And: Enters 5 cups, selects "Spoilage/Waste", notes "Weevils"
And: Clicks [Apply Adjustment]
Then: Inventory shows 5 cups remaining
And: Depletion history shows spoilage entry with notes
```

**UAT-002: Physical Count Correction**
```
Given: System shows 10 cups sugar
When: User does physical count, finds only 7 cups
Then: User clicks [Adjust] on sugar item
And: Enters 3 cups, selects "Physical Count Correction"
And: Clicks [Apply Adjustment]
Then: Inventory shows 7 cups (matches physical count)
```

**UAT-003: Prevent Negative Inventory**
```
Given: User has 3 cups chocolate chips in inventory
When: User tries to adjust by 5 cups (more than available)
Then: System shows error "Cannot deplete 5.0: only 3.0 available"
And: Adjustment is not applied
```

---

## 9. Implementation Phases

### Phase 1: Core Functionality (MVP)
**Effort:** 4-6 hours

**Scope:**
- Extend DepletionReason enum (add manual reasons)
- InventoryService.manual_adjustment() method
- Basic validation (positive amount, non-negative result)
- Create depletion record, update inventory

**Deliverables:**
- ✓ Manual adjustment service method
- ✓ Validation logic
- ✓ Unit tests

### Phase 2: UI Implementation
**Effort:** 4-6 hours

**Scope:**
- [Adjust] button on inventory list
- Manual adjustment dialog
- Preview calculation
- Success/error messages
- Depletion history display (enhanced)

**Deliverables:**
- ✓ Adjustment dialog UI
- ✓ Integration with inventory tab
- ✓ Error handling and user feedback

### Total Effort Estimate
**8-12 hours** (1-1.5 working days)

---

## 10. Success Criteria

**Must Have:**
- [ ] [Adjust] button available on each inventory item
- [ ] Manual adjustment dialog with reason dropdown
- [ ] Validation prevents negative inventory
- [ ] Depletion record created with reason and notes
- [ ] Inventory quantity updated correctly
- [ ] Depletion history shows manual adjustments
- [ ] Cost impact calculated and tracked

**Should Have:**
- [ ] Preview shows new quantity before applying
- [ ] Error messages specific and actionable
- [ ] Success confirmation shows what changed
- [ ] Notes required for OTHER reason

**Nice to Have:**
- [ ] Bulk adjustment (multiple items at once)
- [ ] Adjustment history report
- [ ] Adjustment approval workflow (for team environments)

---

## 11. Future Enhancements (Phase 3+)

**Advanced Features:**
- Bulk adjustments (adjust multiple items in one operation)
- Adjustment templates (common adjustment patterns)
- Approval workflow (manager approval for large adjustments)
- Adjustment audit reports (who adjusted what, when)
- Undo adjustment (within time window)

**Analytics:**
- Spoilage trends (which ingredients spoil most)
- Cost of waste (total $ lost to spoilage)
- Gift/donation tracking (for tax purposes)

---

## 12. Constitutional Compliance

**Principle I (Data Integrity):**
- ✓ Validation prevents negative inventory
- ✓ Depletion records immutable (audit trail)
- ✓ Cost calculations accurate

**Principle V (Layered Architecture):**
- ✓ Service method in InventoryService (not UI)
- ✓ UI calls service, doesn't do business logic
- ✓ Existing models reused (no schema changes)

---

## 13. Related Documents

- **Requirements:** `docs/requirements/req_inventory.md` Section 3.2 (Manual Adjustments)
- **Dependencies:** `docs/func-spec/F028_purchase_tracking_enhanced_costing.md` (Purchase system)
- **Dependencies:** `docs/func-spec/F029_streamlined_inventory_entry.md` (Inventory UI)
- **Constitution:** `.kittify/memory/constitution.md` (Data integrity principles)

---

**END OF SPECIFICATION**
