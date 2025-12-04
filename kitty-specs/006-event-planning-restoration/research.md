# Research: Event Planning Restoration

**Feature**: 006-event-planning-restoration
**Date**: 2025-12-03
**Status**: Complete

## Executive Summary

Systematic codebase research reveals that Phase 3b event planning components exist but are DISABLED due to dependency on a removed "Bundle" model. The new Ingredient/Variant architecture introduced FinishedUnit (individual items) and repurposed FinishedGood as an assembly container. The recommended approach is to adapt Package to reference FinishedGood directly, eliminating the Bundle intermediate concept.

## Research Questions

### RQ1: What is the current state of event planning models?

**Finding**: Models exist in files but are disabled in `src/models/__init__.py`

| Model | File Status | Import Status | Notes |
|-------|-------------|---------------|-------|
| Event | EXISTS | DISABLED | References Package |
| EventRecipientPackage | EXISTS | DISABLED | Junction table |
| Package | EXISTS | DISABLED | References Bundle (removed) |
| PackageBundle | EXISTS | DISABLED | References Bundle (removed) |
| Recipient | EXISTS | ENABLED | No dependencies on removed models |
| Bundle | REMOVED | N/A | No longer exists |

**Evidence**: `src/models/__init__.py` lines 24-26:
```python
# from .package import Package, PackageBundle  # DISABLED: References removed Bundle model
# from .event import Event, EventRecipientPackage  # DISABLED: References removed Package model
```

### RQ2: What is the new FinishedGood/FinishedUnit architecture?

**Finding**: Two-tier hierarchical system

| Model | Purpose | Cost Calculation |
|-------|---------|------------------|
| FinishedUnit | Individual baked item (cookie, cake) | `unit_cost` from Recipe via `calculate_recipe_cost_per_item()` |
| FinishedGood | Assembly of items (gift box) | `total_cost` from component costs via `calculate_component_cost()` |
| Composition | Junction table (polymorphic) | Links FinishedGood to FinishedUnit OR FinishedGood |

**Key architectural change**: Original FinishedGood functionality moved to FinishedUnit. New FinishedGood is assembly-focused.

### RQ3: How does cost flow through the new model?

**Finding**: Cost propagation chain:

```
Recipe.calculate_cost()
    ↓
FinishedUnit.unit_cost (per item)
    ↓
Composition.get_total_cost() (unit_cost × quantity)
    ↓
FinishedGood.calculate_component_cost() (sum of compositions)
    ↓
Package.calculate_cost() (sum of FinishedGood costs)
    ↓
EventRecipientPackage.calculate_cost() (package cost × quantity)
    ↓
Event.get_total_cost() (sum of all assignments)
```

### RQ4: What obsolete patterns should be avoided?

**Finding**: The following are obsolete or broken:

1. **Bundle model** - Removed entirely, no longer exists
2. **Old Bundle concept in UI** - `src/ui/bundles_tab.py` imports `from src.models.finished_good import Bundle` which doesn't exist
3. **yield_mode on FinishedGood** - Moved to FinishedUnit; the bundles_tab.py references `bundle.finished_good.yield_mode` which is invalid
4. **density calculation mechanism** - User confirmed this was simplified (avoid complex density patterns)
5. **Services referencing Bundle** - `event_service.py` and `package_service.py` both import Bundle

### RQ5: What services exist and their status?

| Service | Status | Issue |
|---------|--------|-------|
| event_service.py | BROKEN | Imports Bundle, Package (disabled) |
| package_service.py | BROKEN | Imports Bundle (removed) |
| recipient_service.py | FUNCTIONAL | No disabled dependencies |
| finished_good_service.py | FUNCTIONAL | Updated for new architecture |
| finished_unit_service.py | FUNCTIONAL | New service for FinishedUnits |
| recipe_service.py | FUNCTIONAL | Has FIFO cost calculation (Feature 005) |

## Decisions

### D1: Eliminate Bundle, Package contains FinishedGood directly

**Decision**: Remove the Bundle intermediate layer. Package will directly contain FinishedGoods.

**Rationale**:
- Bundle model was removed and doesn't exist
- FinishedGood now serves the "assembly" role that Bundle partially fulfilled
- Simplifies the model hierarchy: `FinishedGood → Package → Event`
- Reduces complexity without losing functionality

**Alternative rejected**: Reintroducing Bundle model
- Would add complexity without clear benefit
- FinishedGood assemblies already handle grouping items
- User confirmed reimplementation approach over restoration

### D2: Adapt PackageBundle to reference FinishedGood

**Decision**: Rename/adapt PackageBundle to PackageFinishedGood or similar, linking Package to FinishedGood with quantity.

**Rationale**:
- Maintains the quantity-per-package concept
- Leverages existing FinishedGood cost calculation
- Clean separation of concerns

### D3: Use RecipeService.calculate_actual_cost() for FIFO costing

**Decision**: All cost calculations must use Feature 005's FIFO-based recipe costing via RecipeService.

**Rationale**:
- Constitution mandates FIFO accuracy
- Feature 005 provides this capability
- FinishedUnit.calculate_recipe_cost_per_item() should call RecipeService

### D4: Reimplement services from scratch

**Decision**: Write new services rather than fixing broken imports.

**Rationale**:
- User confirmed reimplementation approach
- Existing services have fundamental architecture mismatches
- Cleaner to build fresh with correct dependencies

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FinishedGood cost calculation not integrated with FIFO | Medium | High | Verify integration in implementation |
| UI tabs reference obsolete Bundle patterns | High | Medium | Rewrite UI tabs to use new architecture |
| Test data import incompatible with new schema | Low | Medium | Reshape sample_data.json as needed |

## Open Questions

1. Should PackageFinishedGood include `quantity` (multiple of same assembly) or just link one assembly per row?
   - **Recommendation**: Include quantity for flexibility (same pattern as old PackageBundle)

2. Does EventDetailWindow need to show FinishedUnit-level detail or just FinishedGood assemblies?
   - **Recommendation**: Show FinishedGood level for packages, expand to units in Recipe Needs

## Next Steps

1. Create data-model.md with updated entity relationships
2. Define service contracts for Package, Event, Recipient operations
3. Identify UI components requiring updates
