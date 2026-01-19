# Feature 025: Production Loss Tracking

**Created:** 2025-12-21  
**Status:** DESIGN  
**Priority:** MEDIUM  
**Complexity:** MEDIUM

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

Baked goods production involves real-world failures:
- Items burn in the oven
- Cookies break during handling
- Ingredients are contaminated or dropped before completion
- Wrong ingredients are used, requiring batch discard

**Current Gap:** The application cannot distinguish between successful production and losses. When recording production, users can enter `actual_yield < expected_yield`, but:
1. No explicit tracking of what happened to the "missing" units
2. No loss categorization (burnt vs broken vs contaminated)
3. No cost accounting for waste
4. No analytics on loss trends or patterns

**User Impact:**
- Cannot answer "How much did we lose to burnt cookies this season?"
- Cannot identify problematic recipes with high loss rates
- Cannot track improvement efforts (e.g., "oven temperature adjustment reduced burnt batches")
- Inventory consumed but no record of where finished goods went
- **Lost batches must be remade to fulfill event requirements** - no workflow to loop back to production for replacement batches

---

## Solution Overview

Add explicit production loss tracking that:
1. Enforces accounting for every planned unit (produced or lost)
2. Categorizes loss reasons for trend analysis
3. Calculates waste costs for financial reporting
4. Enables process improvement analytics
5. **Facilitates remake workflow** - when losses occur, user can easily see shortfall and produce replacement batches to meet event targets

**Core Principle:** Use terminology of "loss" rather than "failure" - acknowledges that losses are a normal part of production ("shit happens").

**Remake Workflow:** When production results in losses, the Event Production Dashboard will show the shortfall against targets. User can then record additional production runs to make up the deficit. The system tracks both the lost batch (with costs and loss reason) and the replacement batch separately, providing complete cost accounting for the event.

---

## Scope

### In Scope

**Schema Changes:**
- Add loss tracking fields to `ProductionRun` model
- Create new `ProductionLoss` model for detailed loss records
- Add production status enumeration

**Service Layer:**
- Update `batch_production_service.record_production()` to accept loss parameters
- Add loss validation (actual_yield + loss_quantity = expected_yield)
- Calculate and record loss costs
- Create ProductionLoss records when losses occur

**UI Changes:**
- Update Record Production dialog to show auto-calculated loss quantity
- Add loss details section (category dropdown, notes field) when loss > 0
- Display cost breakdown: good units + lost units
- Show production status visually (complete/partial loss/total loss)

**Reporting:**
- Loss summary by category
- Loss trends over time
- Recipe-level loss rates
- Cost of waste reporting

### Out of Scope

**Current Phase:**
- Assembly loss tracking (future feature - same pattern applies)
- Predictive loss warnings based on historical patterns
- Loss recovery (e.g., "burnt cookies become crumbs for crust")
- Partial ingredient consumption tracking (assumes proportional loss)
- **Automatic remake scheduling** - system tracks losses and shortfalls, but user manually decides when/how to produce replacement batches

**Future Considerations:**
- Integration with quality control workflows
- Loss prevention recommendations based on ML analysis
- Multi-stage production loss tracking (prep → bake → cool → package)
- Automated remake suggestions (e.g., "You need 12 more cookies for Christmas 2025")

---

## Technical Design

### Schema Changes

#### ProductionRun Model Updates

```python
class ProductionRun(BaseModel):
    """
    ProductionRun model for tracking batch production events.
    
    Enhanced with production loss tracking to distinguish successful
    production from partial/total losses.
    """
    
    __tablename__ = "production_runs"
    
    # ... existing fields ...
    
    # Loss tracking (NEW)
    production_status = Column(
        Enum('COMPLETE', 'PARTIAL_LOSS', 'TOTAL_LOSS'),
        nullable=False,
        default='COMPLETE'
    )
    loss_quantity = Column(Integer, nullable=False, default=0)
    loss_notes = Column(Text, nullable=True)
    
    # Relationships (NEW)
    losses = relationship(
        "ProductionLoss",
        back_populates="production_run",
        cascade="all, delete-orphan"
    )
    
    # Constraints (NEW)
    __table_args__ = (
        # ... existing constraints ...
        CheckConstraint(
            "loss_quantity >= 0",
            name="ck_production_run_loss_quantity_non_negative"
        ),
        CheckConstraint(
            "actual_yield + loss_quantity = expected_yield",
            name="ck_production_run_yield_balance"
        ),
    )
```

**Constraint Logic:**
- `actual_yield + loss_quantity = expected_yield` enforces complete accounting
- Example: Expected 24 cookies, made 18, lost 6 → 18 + 6 = 24 ✓
- Prevents data entry errors (forgetting to account for units)

**Status Determination:**
- `COMPLETE`: loss_quantity = 0 (no losses)
- `PARTIAL_LOSS`: 0 < loss_quantity < expected_yield (some good, some lost)
- `TOTAL_LOSS`: loss_quantity = expected_yield (complete batch loss)

#### New ProductionLoss Model

```python
class LossCategory(enum.Enum):
    """Enumeration of production loss categories."""
    BURNT = "burnt"
    BROKEN = "broken"
    CONTAMINATED = "contaminated"
    DROPPED = "dropped"
    WRONG_INGREDIENTS = "wrong_ingredients"
    OTHER = "other"


class ProductionLoss(BaseModel):
    """
    ProductionLoss model for tracking detailed production loss information.
    
    Provides an immutable audit trail of what was lost, why, and at what cost.
    Separate from ProductionRun to enable detailed analytics without cluttering
    the main production table.
    
    Attributes:
        production_run_id: Foreign key to parent ProductionRun
        finished_unit_id: Foreign key to FinishedUnit (denormalized for queries)
        loss_quantity: Number of units lost
        loss_category: Enumerated reason for loss
        per_unit_cost: Cost per unit at time of production (snapshot)
        total_loss_cost: Total cost of loss (quantity * per_unit_cost)
        notes: Optional detailed notes about the loss
    """
    
    __tablename__ = "production_losses"
    
    # Foreign keys
    production_run_id = Column(
        Integer,
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    # Loss data
    loss_quantity = Column(Integer, nullable=False)
    loss_category = Column(Enum(LossCategory), nullable=False)
    per_unit_cost = Column(Numeric(10, 4), nullable=False)
    total_loss_cost = Column(Numeric(10, 4), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    production_run = relationship("ProductionRun", back_populates="losses")
    finished_unit = relationship("FinishedUnit")
    
    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_production_loss_run", "production_run_id"),
        Index("idx_production_loss_finished_unit", "finished_unit_id"),
        Index("idx_production_loss_category", "loss_category"),
        # Constraints
        CheckConstraint(
            "loss_quantity > 0",
            name="ck_production_loss_quantity_positive"
        ),
        CheckConstraint(
            "per_unit_cost >= 0",
            name="ck_production_loss_per_unit_cost_non_negative"
        ),
        CheckConstraint(
            "total_loss_cost >= 0",
            name="ck_production_loss_total_cost_non_negative"
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of production loss."""
        return (
            f"ProductionLoss(id={self.id}, "
            f"production_run_id={self.production_run_id}, "
            f"category={self.loss_category.value}, "
            f"quantity={self.loss_quantity})"
        )
```

**Design Rationale:**

1. **Separate Table vs. Embedded Fields:**
   - Separate table enables clean loss analytics without cluttering ProductionRun
   - Multiple loss categories per run possible (future: "10 burnt, 5 broken")
   - Clearer separation of concerns (production vs. quality issues)

2. **Denormalized finished_unit_id:**
   - Enables efficient queries: "All losses for Sugar Cookies"
   - Avoids JOIN through production_run for common reporting queries
   - Acceptable denormalization per Constitution III (future-proof schema)

3. **Snapshot Cost Fields:**
   - `per_unit_cost` and `total_loss_cost` are snapshots at production time
   - Immutable audit trail (costs may change over time)
   - Matches existing pattern in ProductionConsumption model

### Service Layer Changes

#### Updated batch_production_service.record_production()

```python
def record_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    loss_quantity: int = 0,  # NEW
    loss_category: str = None,  # NEW (LossCategory enum value)
    loss_notes: str = None,  # NEW
    notes: str = None,
    event_id: int = None,
    session=None
) -> ProductionRun:
    """
    Record batch production with optional loss tracking.
    
    Args:
        recipe_id: ID of recipe being produced
        finished_unit_id: ID of finished unit being produced
        num_batches: Number of recipe batches
        actual_yield: Number of good units produced
        loss_quantity: Number of units lost (default 0)
        loss_category: Category of loss (required if loss_quantity > 0)
        loss_notes: Detailed notes about loss (optional)
        notes: General production notes (optional)
        event_id: Optional event linkage
        session: Database session
        
    Returns:
        Created ProductionRun with loss records if applicable
        
    Raises:
        ValueError: If actual_yield + loss_quantity != expected_yield
        ValueError: If loss_quantity > 0 but loss_category not provided
        RecipeNotFoundError: If recipe doesn't exist
        FinishedUnitNotFoundError: If finished unit doesn't exist
        InsufficientInventoryError: If ingredients unavailable
    """
    # Use provided session or create new one
    if session is not None:
        return _record_production_impl(
            recipe_id, finished_unit_id, num_batches,
            actual_yield, loss_quantity, loss_category, loss_notes,
            notes, event_id, session
        )
    with session_scope() as session:
        return _record_production_impl(
            recipe_id, finished_unit_id, num_batches,
            actual_yield, loss_quantity, loss_category, loss_notes,
            notes, event_id, session
        )


def _record_production_impl(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    loss_quantity: int,
    loss_category: str,
    loss_notes: str,
    notes: str,
    event_id: int,
    session
) -> ProductionRun:
    """Implementation of record_production that uses provided session."""
    
    # Validate recipe and finished unit exist (existing logic)
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise RecipeNotFoundError(recipe_id)
        
    finished_unit = session.query(FinishedUnit).filter_by(id=finished_unit_id).first()
    if not finished_unit:
        raise FinishedUnitNotFoundError(finished_unit_id)
    
    # Calculate expected yield
    expected_yield = _calculate_expected_yield(recipe, finished_unit, num_batches)
    
    # Validate yield balance (NEW)
    if actual_yield + loss_quantity != expected_yield:
        raise ValueError(
            f"Yield accounting error: actual_yield ({actual_yield}) + "
            f"loss_quantity ({loss_quantity}) must equal expected_yield ({expected_yield})"
        )
    
    # Validate loss category provided if losses exist (NEW)
    if loss_quantity > 0 and not loss_category:
        raise ValueError("loss_category required when loss_quantity > 0")
    
    # Determine production status (NEW)
    if loss_quantity == 0:
        production_status = 'COMPLETE'
    elif actual_yield == 0:
        production_status = 'TOTAL_LOSS'
    else:
        production_status = 'PARTIAL_LOSS'
    
    # Perform FIFO consumption (existing logic)
    consumption_results = _perform_fifo_consumption(
        recipe_id, num_batches, session
    )
    
    # Calculate costs (existing logic, but now used for loss tracking too)
    total_ingredient_cost = sum(c['total_cost'] for c in consumption_results)
    per_unit_cost = total_ingredient_cost / expected_yield if expected_yield > 0 else Decimal('0.0000')
    
    # Create production run (ENHANCED)
    production_run = ProductionRun(
        recipe_id=recipe_id,
        finished_unit_id=finished_unit_id,
        event_id=event_id,
        num_batches=num_batches,
        expected_yield=expected_yield,
        actual_yield=actual_yield,
        loss_quantity=loss_quantity,  # NEW
        production_status=production_status,  # NEW
        loss_notes=loss_notes,  # NEW
        produced_at=datetime.utcnow(),
        notes=notes,
        total_ingredient_cost=total_ingredient_cost,
        per_unit_cost=per_unit_cost
    )
    session.add(production_run)
    session.flush()  # Get production_run.id
    
    # Create consumption records (existing logic)
    for consumption in consumption_results:
        consumption_record = ProductionConsumption(
            production_run_id=production_run.id,
            ingredient_slug=consumption['ingredient_slug'],
            quantity_consumed=consumption['quantity_consumed'],
            unit=consumption['unit'],
            total_cost=consumption['total_cost']
        )
        session.add(consumption_record)
    
    # Update finished unit inventory (MODIFIED - only add good units)
    finished_unit.inventory_count += actual_yield  # Was: expected_yield
    
    # Create loss record if applicable (NEW)
    if loss_quantity > 0:
        loss_record = ProductionLoss(
            production_run_id=production_run.id,
            finished_unit_id=finished_unit_id,
            loss_quantity=loss_quantity,
            loss_category=LossCategory[loss_category.upper()],
            per_unit_cost=per_unit_cost,
            total_loss_cost=per_unit_cost * loss_quantity,
            notes=loss_notes
        )
        session.add(loss_record)
    
    return production_run
```

**Key Changes:**
1. New parameters for loss tracking with sensible defaults
2. Yield balance validation enforces accounting integrity
3. Production status auto-determined from loss_quantity
4. Inventory update changed: `actual_yield` instead of `expected_yield`
5. ProductionLoss record created when losses occur
6. All existing FIFO and cost logic preserved

### UI Changes

#### RecordProductionDialog Enhancements

**Layout Changes:**

```
┌─────────────────────────────────────────────────┐
│  Record Production - Sugar Cookie               │
├─────────────────────────────────────────────────┤
│  Recipe: Basic Sugar Cookie                     │
│  Event (optional): [Christmas 2025        ▼]    │
│                                                  │
│  Batch Count:      [2]                          │
│  Expected Yield:   48 cookies                   │
│                                                  │
│  Actual Yield:     [42]                         │
│  Loss Quantity:    6 cookies (auto-calculated)  │
│                                                  │
│  ┌─ Loss Details ───────────────────────────┐  │
│  │ ☑ Record loss details                    │  │
│  │                                           │  │
│  │ Loss Category: [Burnt            ▼]      │  │
│  │                                           │  │
│  │ Loss Notes:                               │  │
│  │ ┌──────────────────────────────────────┐ │  │
│  │ │Oven temperature too high - check     │ │  │
│  │ │thermostat calibration                │ │  │
│  │ └──────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  General Notes:                                 │
│  ┌────────────────────────────────────────────┐ │
│  │First batch of the season                  │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌─ Cost Summary ──────────────────────────┐  │
│  │ Good units (42):  $12.60 @ $0.30/ea     │  │
│  │ Lost units (6):    $1.80 @ $0.30/ea     │  │
│  │ Total batch cost: $14.40                 │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  [Ingredient Availability - expandable]         │
│                                                  │
│                         [Cancel]  [Record]      │
└─────────────────────────────────────────────────┘
```

**Field Behavior:**

1. **Loss Quantity (read-only, auto-calculated):**
   - Formula: `expected_yield - actual_yield`
   - Updates in real-time as batch count or actual yield changes
   - Displayed in gray/disabled style to indicate read-only
   - Format: "6 cookies" (includes unit name from finished_unit.item_unit)

2. **Loss Details Section:**
   - Collapsible frame (or checkbox to enable)
   - Only visible when loss_quantity > 0
   - Contains:
     - Loss Category dropdown (Burnt/Broken/Contaminated/Dropped/Wrong Ingredients/Other)
     - Loss Notes textbox (multi-line, optional)
   - If loss_quantity > 0 and user doesn't check "Record loss details", default to category="OTHER"

3. **Cost Summary Box:**
   - Always visible
   - Shows breakdown of good vs lost costs
   - Updates dynamically as actual_yield changes
   - Total cost always same (ingredients consumed regardless)

**Validation:**

```python
def _validate_production(self) -> tuple[bool, str]:
    """Validate production inputs before recording."""
    
    # Parse batch count
    try:
        batch_count = int(self.batch_entry.get())
        if batch_count <= 0:
            return False, "Batch count must be positive"
    except ValueError:
        return False, "Invalid batch count"
    
    # Parse actual yield
    try:
        actual_yield = int(self.yield_entry.get())
        if actual_yield < 0:
            return False, "Actual yield cannot be negative"
    except ValueError:
        return False, "Invalid actual yield"
    
    # Calculate expected yield
    expected_yield = self._calculate_expected_yield(batch_count)
    
    # Calculate loss
    loss_quantity = expected_yield - actual_yield
    
    # Validate yield balance
    if loss_quantity < 0:
        return False, f"Actual yield ({actual_yield}) exceeds expected ({expected_yield})"
    
    # Validate loss details if losses exist
    if loss_quantity > 0:
        if self.record_loss_var.get():  # Checkbox checked
            if not self.loss_category_var.get():
                return False, "Loss category required when recording loss details"
    
    return True, ""
```

**Service Integration:**

```python
def _record_production(self):
    """Record the production run via service layer."""
    
    # Validation (see above)
    valid, error_msg = self._validate_production()
    if not valid:
        show_error(self, "Validation Error", error_msg)
        return
    
    # Parse inputs
    batch_count = int(self.batch_entry.get())
    actual_yield = int(self.yield_entry.get())
    expected_yield = self._calculate_expected_yield(batch_count)
    loss_quantity = expected_yield - actual_yield
    
    # Prepare loss parameters
    loss_category = None
    loss_notes = None
    if loss_quantity > 0:
        if self.record_loss_var.get():
            loss_category = self.loss_category_var.get()
            loss_notes = self.loss_notes_textbox.get("1.0", "end-1c").strip() or None
        else:
            loss_category = "OTHER"  # Default if user skips loss details
    
    # Get event_id if selected
    event_id = self._get_selected_event_id()
    
    # General notes
    notes = self.notes_textbox.get("1.0", "end-1c").strip() or None
    
    # Record via service
    try:
        production_run = self.service_integrator.execute_operation(
            operation_type=OperationType.RECORD_PRODUCTION,
            recipe_id=self.finished_unit.recipe_id,
            finished_unit_id=self.finished_unit.id,
            num_batches=batch_count,
            actual_yield=actual_yield,
            loss_quantity=loss_quantity,
            loss_category=loss_category,
            loss_notes=loss_notes,
            notes=notes,
            event_id=event_id
        )
        
        # Set result and close
        self.result = {
            'production_run_id': production_run.id,
            'actual_yield': actual_yield,
            'loss_quantity': loss_quantity,
            'production_status': production_run.production_status
        }
        self.destroy()
        
    except Exception as e:
        show_error(self, "Production Recording Failed", str(e))
```

#### Production History Table Updates

**Add Status Column:**

```python
# In ProductionHistoryTable widget

def _configure_columns(self):
    """Configure treeview columns."""
    self.tree["columns"] = (
        "date", "recipe", "finished_unit", "batches",
        "expected", "actual", "loss", "status",  # NEW: loss, status
        "cost", "event"
    )
    
    # Column headings
    self.tree.heading("date", text="Date")
    self.tree.heading("recipe", text="Recipe")
    self.tree.heading("finished_unit", text="Product")
    self.tree.heading("batches", text="Batches")
    self.tree.heading("expected", text="Expected")
    self.tree.heading("actual", text="Actual")
    self.tree.heading("loss", text="Loss")  # NEW
    self.tree.heading("status", text="Status")  # NEW
    self.tree.heading("cost", text="Cost")
    self.tree.heading("event", text="Event")
    
    # Column widths
    self.tree.column("#0", width=0, stretch=False)  # Hide first column
    self.tree.column("date", width=100)
    self.tree.column("recipe", width=150)
    self.tree.column("finished_unit", width=150)
    self.tree.column("batches", width=60)
    self.tree.column("expected", width=70)
    self.tree.column("actual", width=70)
    self.tree.column("loss", width=70)  # NEW
    self.tree.column("status", width=100)  # NEW
    self.tree.column("cost", width=80)
    self.tree.column("event", width=150)

def _populate_row(self, production_run: ProductionRun) -> tuple:
    """Generate row values for a production run."""
    
    # Status formatting with emoji/symbol
    status_display = {
        'COMPLETE': '✓ Complete',
        'PARTIAL_LOSS': '⚠ Partial Loss',
        'TOTAL_LOSS': '✗ Total Loss'
    }.get(production_run.production_status, production_run.production_status)
    
    return (
        production_run.produced_at.strftime("%Y-%m-%d"),
        production_run.recipe.name,
        production_run.finished_unit.display_name,
        str(production_run.num_batches),
        str(production_run.expected_yield),
        str(production_run.actual_yield),
        str(production_run.loss_quantity) if production_run.loss_quantity > 0 else "-",
        status_display,
        f"${production_run.total_ingredient_cost:.2f}",
        production_run.event.name if production_run.event else "-"
    )
```

**Row Coloring:**
- `COMPLETE` - default/white background
- `PARTIAL_LOSS` - light yellow background
- `TOTAL_LOSS` - light red background

### Reporting Queries

**Loss Summary by Category:**

```python
def get_loss_summary_by_category(
    start_date: datetime = None,
    end_date: datetime = None,
    session=None
) -> List[Dict[str, Any]]:
    """
    Get summary of production losses grouped by category.
    
    Args:
        start_date: Optional filter start date
        end_date: Optional filter end date
        session: Database session
        
    Returns:
        List of dicts with keys:
            - category: LossCategory value
            - total_quantity: Total units lost
            - total_cost: Total cost of losses
            - occurrence_count: Number of loss events
    """
    if session is not None:
        return _get_loss_summary_impl(start_date, end_date, session)
    with session_scope() as session:
        return _get_loss_summary_impl(start_date, end_date, session)

def _get_loss_summary_impl(
    start_date: datetime,
    end_date: datetime,
    session
) -> List[Dict[str, Any]]:
    """Implementation using provided session."""
    
    query = session.query(
        ProductionLoss.loss_category,
        func.sum(ProductionLoss.loss_quantity).label('total_quantity'),
        func.sum(ProductionLoss.total_loss_cost).label('total_cost'),
        func.count(ProductionLoss.id).label('occurrence_count')
    ).join(ProductionRun)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(ProductionRun.produced_at >= start_date)
    if end_date:
        query = query.filter(ProductionRun.produced_at <= end_date)
    
    query = query.group_by(ProductionLoss.loss_category)
    
    results = query.all()
    
    return [
        {
            'category': row.loss_category.value,
            'total_quantity': int(row.total_quantity),
            'total_cost': float(row.total_cost),
            'occurrence_count': int(row.occurrence_count)
        }
        for row in results
    ]
```

**Recipe Loss Rate:**

```python
def get_recipe_loss_rate(
    recipe_id: int,
    start_date: datetime = None,
    end_date: datetime = None,
    session=None
) -> Dict[str, Any]:
    """
    Calculate loss rate for a specific recipe.
    
    Args:
        recipe_id: Recipe to analyze
        start_date: Optional filter start date
        end_date: Optional filter end date
        session: Database session
        
    Returns:
        Dict with keys:
            - recipe_id: int
            - recipe_name: str
            - total_expected: Total expected yield
            - total_actual: Total actual yield
            - total_loss: Total loss quantity
            - loss_rate_percent: (total_loss / total_expected) * 100
            - production_run_count: Number of production runs
    """
    # Implementation similar to above, aggregating ProductionRun by recipe_id
```

**Cost of Waste Report:**

```python
def get_waste_cost_report(
    event_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    session=None
) -> Dict[str, Any]:
    """
    Generate waste cost report with optional event/date filtering.
    
    Args:
        event_id: Optional event to filter by
        start_date: Optional filter start date
        end_date: Optional filter end date
        session: Database session
        
    Returns:
        Dict with keys:
            - total_production_cost: Total cost of all production
            - total_waste_cost: Total cost of losses
            - waste_percentage: (waste / total) * 100
            - by_category: List of loss summaries by category
            - by_recipe: List of recipes sorted by loss cost
    """
    # Implementation combining multiple queries above
```

---

## Migration Strategy

Per Constitution VI (Schema Change Strategy), schema changes handled via export/reset/import cycle:

### Step 1: Pre-Migration Export

```bash
# Export all data before schema change
python -m src.cli.main export data --output docs/migrations/pre_f025_export.json
```

### Step 2: Schema Update

1. Add new fields to `ProductionRun` model (nullable first for safety)
2. Create new `ProductionLoss` model and table
3. Update `batch_production_service.py` with new signature (backward compatible)

### Step 3: Data Transformation

```python
# docs/migrations/transform_f025_data.py

def transform_production_data(export_data: dict) -> dict:
    """
    Transform exported data to match new schema.
    
    For existing ProductionRun records:
    - Set production_status = 'COMPLETE' (no historical losses tracked)
    - Set loss_quantity = 0
    - Set loss_notes = NULL
    - No ProductionLoss records created (historical data incomplete)
    """
    
    for production_run in export_data.get('production_runs', []):
        # Add new fields with defaults
        production_run['production_status'] = 'COMPLETE'
        production_run['loss_quantity'] = 0
        production_run['loss_notes'] = None
    
    # No historical ProductionLoss records (data didn't exist)
    export_data['production_losses'] = []
    
    return export_data
```

### Step 4: Import Transformed Data

```bash
# Reset database (delete and recreate with new schema)
python -m src.cli.main db reset

# Transform exported data
python docs/migrations/transform_f025_data.py

# Import transformed data
python -m src.cli.main import data --input docs/migrations/f025_transformed_export.json
```

### Step 5: Validation

```python
# Verify migration success
def validate_f025_migration(session):
    """Validate all ProductionRun records have required fields."""
    
    from src.models import ProductionRun
    
    # Check all production runs have status and loss_quantity
    runs = session.query(ProductionRun).all()
    
    for run in runs:
        assert run.production_status is not None, f"Missing status: {run.id}"
        assert run.loss_quantity is not None, f"Missing loss_quantity: {run.id}"
        assert run.loss_quantity >= 0, f"Negative loss_quantity: {run.id}"
        
        # For migrated data, all should be COMPLETE with 0 loss
        assert run.production_status == 'COMPLETE', f"Unexpected status: {run.id}"
        assert run.loss_quantity == 0, f"Unexpected loss in migration: {run.id}"
    
    print(f"✓ Validated {len(runs)} production runs")
```

---

## Testing Strategy

### Unit Tests

**Service Layer:**

```python
# tests/services/test_batch_production_service_losses.py

class TestProductionLossTracking:
    """Test suite for production loss tracking functionality."""
    
    def test_complete_production_no_losses(self, session, test_recipe, test_finished_unit):
        """Verify COMPLETE status when no losses occur."""
        production_run = record_production(
            recipe_id=test_recipe.id,
            finished_unit_id=test_finished_unit.id,
            num_batches=1,
            actual_yield=24,
            loss_quantity=0,
            session=session
        )
        
        assert production_run.production_status == 'COMPLETE'
        assert production_run.loss_quantity == 0
        assert production_run.actual_yield == 24
        assert production_run.expected_yield == 24
        
        # No loss record created
        losses = session.query(ProductionLoss).filter_by(
            production_run_id=production_run.id
        ).all()
        assert len(losses) == 0
    
    def test_partial_loss_production(self, session, test_recipe, test_finished_unit):
        """Verify PARTIAL_LOSS status and loss record creation."""
        production_run = record_production(
            recipe_id=test_recipe.id,
            finished_unit_id=test_finished_unit.id,
            num_batches=1,
            actual_yield=18,
            loss_quantity=6,
            loss_category='BURNT',
            loss_notes='Oven too hot',
            session=session
        )
        
        assert production_run.production_status == 'PARTIAL_LOSS'
        assert production_run.loss_quantity == 6
        assert production_run.actual_yield == 18
        assert production_run.expected_yield == 24
        
        # Loss record created
        losses = session.query(ProductionLoss).filter_by(
            production_run_id=production_run.id
        ).all()
        assert len(losses) == 1
        
        loss = losses[0]
        assert loss.loss_quantity == 6
        assert loss.loss_category == LossCategory.BURNT
        assert loss.notes == 'Oven too hot'
        assert loss.per_unit_cost == production_run.per_unit_cost
        assert loss.total_loss_cost == production_run.per_unit_cost * 6
    
    def test_total_loss_production(self, session, test_recipe, test_finished_unit):
        """Verify TOTAL_LOSS status when entire batch is lost."""
        production_run = record_production(
            recipe_id=test_recipe.id,
            finished_unit_id=test_finished_unit.id,
            num_batches=1,
            actual_yield=0,
            loss_quantity=24,
            loss_category='BURNT',
            loss_notes='Complete batch burnt',
            session=session
        )
        
        assert production_run.production_status == 'TOTAL_LOSS'
        assert production_run.loss_quantity == 24
        assert production_run.actual_yield == 0
        
        # Inventory not increased
        finished_unit = session.query(FinishedUnit).get(test_finished_unit.id)
        assert finished_unit.inventory_count == 0  # Started at 0
    
    def test_yield_balance_validation(self, session, test_recipe, test_finished_unit):
        """Verify yield balance constraint is enforced."""
        with pytest.raises(ValueError, match="Yield accounting error"):
            record_production(
                recipe_id=test_recipe.id,
                finished_unit_id=test_finished_unit.id,
                num_batches=1,
                actual_yield=20,  # 20 + 5 = 25, but expected is 24
                loss_quantity=5,
                session=session
            )
    
    def test_loss_category_required_validation(self, session, test_recipe, test_finished_unit):
        """Verify loss_category required when loss_quantity > 0."""
        with pytest.raises(ValueError, match="loss_category required"):
            record_production(
                recipe_id=test_recipe.id,
                finished_unit_id=test_finished_unit.id,
                num_batches=1,
                actual_yield=20,
                loss_quantity=4,
                loss_category=None,  # Missing category
                session=session
            )
    
    def test_inventory_update_with_losses(self, session, test_recipe, test_finished_unit):
        """Verify inventory only increased by actual_yield, not expected_yield."""
        initial_inventory = test_finished_unit.inventory_count
        
        production_run = record_production(
            recipe_id=test_recipe.id,
            finished_unit_id=test_finished_unit.id,
            num_batches=1,
            actual_yield=20,
            loss_quantity=4,
            loss_category='BROKEN',
            session=session
        )
        
        session.refresh(test_finished_unit)
        assert test_finished_unit.inventory_count == initial_inventory + 20
        # Not initial_inventory + 24 (expected)
```

**Reporting Queries:**

```python
# tests/services/test_production_loss_reports.py

class TestProductionLossReports:
    """Test suite for production loss reporting queries."""
    
    def test_loss_summary_by_category(self, session, sample_production_losses):
        """Verify loss summary aggregates correctly by category."""
        summary = get_loss_summary_by_category(session=session)
        
        # Should have entries for each category with losses
        burnt_summary = next(s for s in summary if s['category'] == 'burnt')
        assert burnt_summary['total_quantity'] == 10  # From test fixtures
        assert burnt_summary['occurrence_count'] == 2
        
        broken_summary = next(s for s in summary if s['category'] == 'broken')
        assert broken_summary['total_quantity'] == 5
    
    def test_recipe_loss_rate_calculation(self, session, test_recipe, sample_production_runs):
        """Verify loss rate calculation for a recipe."""
        loss_rate = get_recipe_loss_rate(test_recipe.id, session=session)
        
        assert loss_rate['recipe_id'] == test_recipe.id
        assert loss_rate['total_expected'] == 72  # 3 runs * 24 expected
        assert loss_rate['total_actual'] == 60
        assert loss_rate['total_loss'] == 12
        assert loss_rate['loss_rate_percent'] == pytest.approx(16.67, rel=0.01)
```

### Integration Tests

**UI Workflow:**

```python
# tests/integration/test_production_loss_ui.py

class TestProductionLossUI:
    """Integration tests for production loss UI workflow."""
    
    def test_loss_quantity_auto_calculation(self, dialog):
        """Verify loss quantity updates when actual yield changes."""
        dialog.batch_entry.delete(0, 'end')
        dialog.batch_entry.insert(0, '1')
        
        dialog.yield_entry.delete(0, 'end')
        dialog.yield_entry.insert(0, '20')
        
        dialog._on_yield_changed()  # Trigger calculation
        
        assert dialog.loss_quantity_label.cget('text') == '4 cookies'
    
    def test_loss_details_section_visibility(self, dialog):
        """Verify loss details section only visible when losses exist."""
        # No losses - section hidden/disabled
        dialog.yield_entry.delete(0, 'end')
        dialog.yield_entry.insert(0, '24')
        dialog._on_yield_changed()
        
        assert not dialog.loss_details_frame.winfo_viewable()
        
        # With losses - section visible
        dialog.yield_entry.delete(0, 'end')
        dialog.yield_entry.insert(0, '20')
        dialog._on_yield_changed()
        
        assert dialog.loss_details_frame.winfo_viewable()
```

---

## Acceptance Criteria

### Must Have (MVP)

1. ✅ Schema updated with production_status, loss_quantity, loss_notes on ProductionRun
2. ✅ ProductionLoss model created with all specified fields
3. ✅ batch_production_service.record_production() accepts loss parameters
4. ✅ Yield balance constraint enforced: actual_yield + loss_quantity = expected_yield
5. ✅ Production status auto-determined (COMPLETE/PARTIAL_LOSS/TOTAL_LOSS)
6. ✅ ProductionLoss record created when losses occur
7. ✅ FinishedUnit inventory updated by actual_yield (not expected_yield)
8. ✅ RecordProductionDialog shows auto-calculated loss quantity
9. ✅ RecordProductionDialog shows loss details section when loss > 0
10. ✅ RecordProductionDialog shows cost breakdown (good vs lost)
11. ✅ ProductionHistoryTable displays loss quantity and status columns
12. ✅ Service layer tests achieve >70% coverage
13. ✅ Migration script transforms existing data successfully
14. ✅ User testing validates loss tracking workflow

### Should Have (Post-MVP)

1. ⬜ Loss summary report UI (dashboard widget)
2. ⬜ Recipe loss rate analysis UI
3. ⬜ Export loss data to CSV for external analysis
4. ⬜ Loss trend visualization (chart showing losses over time)

### Could Have (Future)

1. ⬜ Assembly loss tracking (same pattern)
2. ⬜ Predictive loss warnings based on historical data
3. ⬜ Loss recovery tracking (burnt cookies → crumbs)
4. ⬜ Multi-stage loss tracking (prep → bake → cool → package)

---

## Risks and Mitigation

### Risk: Data Entry Burden

**Risk:** Users may find loss tracking tedious when losses are small/rare.

**Mitigation:**
- Make loss details section optional (checkbox to expand)
- Default to "OTHER" category if user skips details
- Keep loss notes field optional
- Auto-calculate loss quantity (no manual entry)

### Risk: Historical Data Loss

**Risk:** Migration sets all historical production to COMPLETE with 0 losses.

**Mitigation:**
- Document in migration notes that historical loss data is unavailable
- Clearly communicate in UI that loss tracking is "new as of [date]"
- Accept this limitation - perfect historical data not critical for feature value

### Risk: Complexity Creep

**Risk:** Feature could expand to multi-stage tracking, recovery workflows, etc.

**Mitigation:**
- Strict scope boundaries (out of scope section clearly defined)
- MVP focuses on basic loss recording and reporting
- Advanced analytics deferred to future features
- Constitution Principle I: "Features MUST solve actual user problems, not theoretical ones"

---

## Open Questions

1. **Loss Category Extensibility:** Should users be able to add custom loss categories, or is the fixed enum sufficient?
   - **Recommendation:** Start with fixed enum. "OTHER" + notes field handles edge cases. Custom categories add complexity without clear value.

2. **Historical Loss Backfilling:** Should UI provide a way to manually record historical losses for past production runs?
   - **Recommendation:** No. Migration complexity not worth it. Focus on forward-looking loss tracking.

3. **Loss Recovery Workflows:** Some losses can be repurposed (burnt cookies → crumbs for crust). Should this be tracked?
   - **Recommendation:** Out of scope. Record as loss initially; recovery is separate production event using "crumbs" as an ingredient.

4. **Multi-Batch Loss Tracking:** If making 3 batches and 1 batch burns completely, should we track per-batch or aggregate?
   - **Recommendation:** Aggregate. User enters total actual_yield and total loss_quantity. Per-batch granularity adds complexity without clear reporting value.

5. **Remake Workflow Integration:** How should the system facilitate producing replacement batches when losses occur?
   - **Recommendation:** Leverage existing Event Production Dashboard (Feature 016). When losses occur, the dashboard will show actual vs target shortfall. User initiates new production run to make up deficit. No automatic scheduling - user controls when/how to remake. Both original (with loss) and remake production runs are tracked separately for complete cost accounting.

---

## References

### Existing Features

- **Feature 013:** Production & Inventory Tracking (FIFO consumption, cost calculation)
- **Feature 014:** Production UI (RecordProductionDialog foundation)
- **Feature 016:** Event-Centric Production Model (event linkage, targets)

### Architecture Documents

- **Constitution Principle II:** Data Integrity & FIFO Accuracy (ingredients consumed regardless of success/failure)
- **Constitution Principle III:** Future-Proof Schema (industry practices, nullable fields)
- **Constitution Principle VI:** Schema Change Strategy (export/reset/import cycle)

### Code References

- `src/models/production_run.py` - ProductionRun model
- `src/models/production_consumption.py` - Consumption ledger pattern
- `src/services/batch_production_service.py` - Production recording logic
- `src/ui/forms/record_production_dialog.py` - Production UI workflow

---

## Appendix: Schema Change SQL

```sql
-- ProductionRun table updates
ALTER TABLE production_runs
ADD COLUMN production_status TEXT NOT NULL DEFAULT 'COMPLETE'
    CHECK (production_status IN ('COMPLETE', 'PARTIAL_LOSS', 'TOTAL_LOSS'));

ALTER TABLE production_runs
ADD COLUMN loss_quantity INTEGER NOT NULL DEFAULT 0
    CHECK (loss_quantity >= 0);

ALTER TABLE production_runs
ADD COLUMN loss_notes TEXT;

-- Add yield balance constraint
ALTER TABLE production_runs
ADD CONSTRAINT ck_production_run_yield_balance
    CHECK (actual_yield + loss_quantity = expected_yield);

-- Create ProductionLoss table
CREATE TABLE production_losses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    production_run_id INTEGER NOT NULL,
    finished_unit_id INTEGER NOT NULL,
    loss_quantity INTEGER NOT NULL CHECK (loss_quantity > 0),
    loss_category TEXT NOT NULL CHECK (loss_category IN (
        'burnt', 'broken', 'contaminated', 'dropped', 'wrong_ingredients', 'other'
    )),
    per_unit_cost NUMERIC(10, 4) NOT NULL CHECK (per_unit_cost >= 0),
    total_loss_cost NUMERIC(10, 4) NOT NULL CHECK (total_loss_cost >= 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (production_run_id) REFERENCES production_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (finished_unit_id) REFERENCES finished_units(id) ON DELETE RESTRICT
);

-- Indexes for ProductionLoss
CREATE INDEX idx_production_loss_run ON production_losses(production_run_id);
CREATE INDEX idx_production_loss_finished_unit ON production_losses(finished_unit_id);
CREATE INDEX idx_production_loss_category ON production_losses(loss_category);
```

---

**Version:** 1.0  
**Last Updated:** 2025-12-21
