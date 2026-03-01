# Current Development Priorities

**Last Updated:** 2025-12-10
**Active Branch:** `main`
**Target Version:** 0.6.0

---

## High-Level Status

**Completed:**
- ✅ Phase 1-4: Foundation, Finished Goods, Event Planning, Ingredient/Product Architecture
- ✅ Features 001-014: Full service and UI layer for production tracking
- ✅ TD-001: Schema cleanup (Variant→Product, PantryItem→InventoryItem)
- ✅ Nested Recipes: RecipeComponent model with recursive cost/ingredient aggregation
- ✅ Production Tracking: BatchProductionService, AssemblyService, FIFO consumption ledgers
- ✅ Production UI: Record Production/Assembly dialogs with availability checking

**Current Focus:**
- 🔄 **Feature 015: Event-Centric Production Model** (CRITICAL STRUCTURAL FIX)

**Blocked (Pending Feature 015):**
- ⏸️ Feature 016: Reporting & Event Planning
- ⏸️ Feature 017: Event Production Dashboard

---

## ⚠️ CRITICAL: Event-Production Linkage Gap

### The Problem

The v0.5 schema correctly models:
- **Definition:** What IS a Cookie Gift Box? ✅
- **Inventory:** How many Cookie Gift Boxes EXIST? ✅

But **cannot answer:**
- **Commitment:** How many are FOR Christmas 2025? ❌
- **Progress:** Am I on track to fulfill this event? ❌
- **Attribution:** Which production runs were for which event? ❌

### Root Cause

`ProductionRun` and `AssemblyRun` have no `event_id` foreign key. Production is recorded but "orphaned" from events.

### Impact

- Event summary reports cannot show accurate "planned vs actual"
- Production dashboards cannot show event-specific progress  
- Package fulfillment status is not tracked
- Multi-event planning is impossible

### Resolution: Feature 015

**Schema v0.6 Design:** `docs/design/schema_v0.6_design.md`

---

## Feature 015: Event-Centric Production Model

### Scope

**Schema Changes:**
- [ ] Add `event_id` (nullable FK) to ProductionRun
- [ ] Add `event_id` (nullable FK) to AssemblyRun
- [ ] New table: `EventProductionTarget` (event_id, recipe_id, target_batches)
- [ ] New table: `EventAssemblyTarget` (event_id, finished_good_id, target_quantity)
- [ ] Add `fulfillment_status` to EventRecipientPackage (pending/ready/delivered)

**Service Changes:**
- [ ] Update `record_batch_production()` with optional event_id param
- [ ] Update `record_assembly()` with optional event_id param
- [ ] Add target management methods to EventService
- [ ] Add progress calculation methods to EventService
- [ ] Add fulfillment status methods to EventService

**UI Changes:**
- [ ] Add event selector to Record Production dialog
- [ ] Add event selector to Record Assembly dialog
- [ ] Add Targets tab to Event Detail window
- [ ] Add progress display (produced vs target)
- [ ] Add fulfillment status to package assignments view

**Migration:**
- [ ] Existing ProductionRun/AssemblyRun get null event_id
- [ ] Existing EventRecipientPackage get 'pending' status

### Implementation Checklist

See `docs/design/schema_v0.6_design.md` Section 9 for complete checklist.

---

## Next Steps (After Feature 015)

### Feature 016: Reporting & Event Planning
- Shopping list CSV export
- Event summary reports (planned vs actual)
- Cost analysis views
- Recipient history reports
- Dashboard enhancements

### Feature 017: Event Production Dashboard
- "Where do I stand for Christmas 2025?" view
- Progress bars per recipe/finished good
- Fulfillment status tracking

---

## Recent Completions

### Feature 014: Production UI (2025-12-10)
- Record Production dialog with availability checking
- Record Assembly dialog with component availability
- Integration with FinishedUnits and FinishedGoods tabs
- Production actions in context menus

### Feature 013: Production & Inventory Tracking (2025-12-09)
- BatchProductionService with FIFO consumption
- AssemblyService with component consumption
- 51 tests, 91% coverage
- Bug fixes: transaction atomicity, timestamp consistency, packaging validation

### Feature 012: Nested Recipes (2025-12-09)
- RecipeComponent junction table
- Recursive cost calculation
- Recursive ingredient aggregation
- Maximum 3 levels of nesting

### Feature 011: Packaging & BOM Foundation (2025-12-08)
- `is_packaging` flag on Ingredient
- Packaging materials in Composition
- BOM patterns established

---

## Key Design Documents

| Document | Purpose |
|----------|---------|
| `docs/design/schema_v0.6_design.md` | Feature 015 schema design |
| `docs/design/schema_v0.5_design.md` | Current production schema |
| `docs/feature_roadmap.md` | Feature sequencing and dependencies |
| `docs/workflow-refactoring-spec.md` | Production flow architecture |
| `docs/known_limitations.md` | Documented gaps and constraints |

---

## Quick Reference Commands

```bash
# Run all tests
pytest src/tests -v

# Run with coverage
pytest src/tests -v --cov=src

# Run application
python src/main.py

# Import/Export
python -m src.utils.load_test_data examples/test_data_v2.json
```

---

## Spec-Kitty Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| 001-014 | ✅ Complete | Foundation through Production UI |
| 015 | 🔄 Planning | Event-Centric Production Model |
| 016-017 | ⏸️ Blocked | Pending Feature 015 |
| 018 | Planned | Packaging & Distribution |

**Ready for Feature 015 via `/spec-kitty.specify`**
