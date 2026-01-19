# Feature 025: Production Loss Tracking - Quick Reference

**Status:** Design Complete  
**Created:** 2025-12-21  
**Full Spec:** `F025_production_loss_tracking.md`

---

## Key Decisions

### Terminology
- Use "loss" not "failure" - acknowledges that losses are normal ("shit happens")
- Categories: BURNT, BROKEN, CONTAMINATED, DROPPED, WRONG_INGREDIENTS, OTHER

### Architecture: Option B (Separate ProductionLoss Table)
**Why separate table vs embedded fields?**
- ✅ Clean loss analytics without cluttering ProductionRun
- ✅ Multiple loss categories per run possible (future: "10 burnt, 5 broken")
- ✅ Clearer separation of concerns (production vs quality issues)
- ✅ Better reporting queries without complex JOINs

### Core Constraint: Yield Balance
```
actual_yield + loss_quantity = expected_yield
```
- Enforces complete accounting for every planned unit
- Example: Expected 24 cookies, made 18, lost 6 → 18 + 6 = 24 ✓
- Database constraint prevents data entry errors

### Status Auto-Determination
- `COMPLETE`: loss_quantity = 0 (no losses)
- `PARTIAL_LOSS`: 0 < loss_quantity < expected_yield (some good, some lost)
- `TOTAL_LOSS`: loss_quantity = expected_yield (complete batch loss)

---

## Schema Changes

### ProductionRun (Updated)
```python
# NEW FIELDS
production_status = Enum('COMPLETE', 'PARTIAL_LOSS', 'TOTAL_LOSS')
loss_quantity = Integer (default 0, >= 0)
loss_notes = Text (nullable)

# NEW CONSTRAINT
CHECK (actual_yield + loss_quantity = expected_yield)
```

### ProductionLoss (New Table)
```python
production_run_id → ProductionRun
finished_unit_id → FinishedUnit (denormalized for query performance)
loss_quantity → Integer (> 0)
loss_category → Enum(BURNT, BROKEN, CONTAMINATED, DROPPED, WRONG_INGREDIENTS, OTHER)
per_unit_cost → Decimal (snapshot at production time)
total_loss_cost → Decimal (quantity * per_unit_cost)
notes → Text (optional)
```

---

## Service Layer Changes

### Updated Signature
```python
def record_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    loss_quantity: int = 0,        # NEW
    loss_category: str = None,     # NEW (required if loss_quantity > 0)
    loss_notes: str = None,        # NEW
    notes: str = None,
    event_id: int = None,
    session=None
) -> ProductionRun
```

### Key Logic Changes
1. **Validation:** `actual_yield + loss_quantity == expected_yield` enforced
2. **Status:** Auto-determined from loss_quantity
3. **Inventory:** Updated by `actual_yield` (not `expected_yield`)
4. **Loss Record:** Created when `loss_quantity > 0`

---

## UI Changes

### RecordProductionDialog

**Auto-Calculated Loss Display:**
```
Batch Count:      [2]
Expected Yield:   48 cookies

Actual Yield:     [42]        ← User enters this
Loss Quantity:    6 cookies   ← Auto-calculated (read-only)
```

**Loss Details Section (expandable when loss > 0):**
```
┌─ Loss Details ───────────────────────────┐
│ ☑ Record loss details                    │
│                                           │
│ Loss Category: [Burnt            ▼]      │
│                                           │
│ Loss Notes:                               │
│ ┌──────────────────────────────────────┐ │
│ │Oven temperature too high - check     │ │
│ │thermostat calibration                │ │
│ └──────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

**Cost Summary:**
```
┌─ Cost Summary ──────────────────────────┐
│ Good units (42):  $12.60 @ $0.30/ea     │
│ Lost units (6):    $1.80 @ $0.30/ea     │
│ Total batch cost: $14.40                 │
└──────────────────────────────────────────┘
```

### ProductionHistoryTable

**New Columns:**
- Loss (shows quantity or "-")
- Status (✓ Complete / ⚠ Partial Loss / ✗ Total Loss)

**Row Coloring:**
- COMPLETE → white/default
- PARTIAL_LOSS → light yellow
- TOTAL_LOSS → light red

---

## Migration Strategy

Per Constitution VI: Export/Reset/Import

1. **Export:** `python -m src.cli.main export data --output pre_f025.json`
2. **Transform:** All historical ProductionRuns → status='COMPLETE', loss_quantity=0
3. **Reset:** Delete database, update models, recreate with new schema
4. **Import:** Load transformed data

**Rationale:** Historical loss data unavailable - acceptable limitation for forward-looking feature.

---

## Reporting Capabilities

### New Queries Enabled
- Loss summary by category (total quantity, cost, occurrence count)
- Recipe-level loss rates (% of expected yield lost)
- Cost of waste reports (total/by event/by date range)
- Loss trends over time
- Most problematic recipes (highest loss rates)

### Example Report
```
Loss Summary - December 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category        Quantity    Cost      Events
─────────────────────────────────────────
Burnt           24 units    $7.20     3
Broken          12 units    $4.80     2
Contaminated    6 units     $2.40     1
─────────────────────────────────────────
TOTAL           42 units    $14.40    6
```

---

## Testing Strategy

### Unit Tests (>70% coverage required)
- Yield balance constraint enforcement
- Status auto-determination logic
- Loss record creation
- Inventory update (actual_yield only)
- Loss category validation
- Cost calculation accuracy

### Integration Tests
- UI loss quantity auto-calculation
- Loss details section visibility
- Full production workflow with losses
- Reporting query accuracy

---

## Acceptance Criteria

### Must Have (MVP)
- [x] Schema updated with loss tracking fields
- [x] ProductionLoss model created
- [x] Service accepts loss parameters
- [x] Yield balance constraint enforced
- [x] Status auto-determined
- [x] Loss records created
- [x] Inventory updated correctly
- [x] UI shows auto-calculated loss
- [x] UI shows loss details section
- [x] UI shows cost breakdown
- [x] History table shows loss/status
- [x] Tests achieve >70% coverage
- [x] Migration transforms existing data
- [ ] User testing validates workflow

### Post-MVP (Future)
- [ ] Loss summary report UI
- [ ] Recipe loss rate analysis UI
- [ ] Export loss data to CSV
- [ ] Loss trend visualization

---

## Dependencies

**Requires:**
- Feature 013: Production & Inventory Tracking (FIFO, ProductionRun model)
- Feature 014: Production UI (RecordProductionDialog)
- Feature 016: Event-Centric Production Model (event linkage)

**Enables:**
- Process improvement analytics
- Waste cost accounting
- Quality control workflows (future)

---

## Quick Start for Implementation

When ready to implement:
1. Read full spec: `F025_production_loss_tracking.md`
2. Review existing code: `production_run.py`, `batch_production_service.py`, `record_production_dialog.py`
3. Follow Spec-Kitty workflow: specify → plan → tasks → implement → review → merge
4. Start with schema changes (models first, service integration second, UI last)
5. Run migration on test database before production

---

**Questions?** Refer to "Open Questions" section in full spec or discuss before implementation.
