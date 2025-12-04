# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-03
**Workflow:** Spec-Kitty driven development

---

## Completed Features

| # | Name | Status | Notes |
|---|------|--------|-------|
| 001 | System Health Check | ABANDONED | Scope mismatch - multi-tenant features inappropriate for local desktop app |
| 002 | Phase 4 Services (Part 1) | MERGED | IngredientService, VariantService |
| 003 | Phase 4 Services (Part 2) | MERGED | PantryService, PurchaseService |
| 004 | Phase 4 UI | MERGED | ingredients_tab.py, pantry_tab.py |
| 005 | Recipe FIFO Cost Integration | MERGED | RecipeService calculates costs using FIFO from PantryService |

---

## Planned Features

| # | Name | Priority | Description |
|---|------|----------|-------------|
| 006 | Event Planning Restoration | CRITICAL | Re-enable Bundle → Package → Event chain with Ingredient/Variant architecture. Currently disabled due to cascading dependencies from Phase 4 refactor. |
| 007 | Shopping List Variant Integration | MEDIUM | Enhance EventService shopping lists with variant-aware brand recommendations. Basic "needs vs inventory" works after 006. |
| 008 | Production Tracking | HIGH | Phase 5: Record finished goods production, mark packages assembled/delivered, track actual vs planned quantities and costs, "in progress" visibility. |
| 009 | UI Import/Export | MEDIUM | Add File menu with import/export dialogs. Enables non-technical user to backup/restore data without CLI. |
| 010 | Reporting Enhancements | LOW | Phase 6: Dashboard improvements, CSV exports, recipient history reports, year-over-year comparisons. |
| 011 | Packaging & Distribution | LOW | Inno Setup installer creation, code signing evaluation, wider distribution preparation. |

---

## Implementation Order

**Critical Path:** 006 → 008 → User Testing

1. **006 - Event Planning Restoration** (CRITICAL)
   - Unblocks: Gift planning workflow, package assignments, event cost calculations
   - Dependency: None (builds on completed 002-005)

2. **008 - Production Tracking** (HIGH)
   - Unblocks: "In progress" visibility, actual vs planned tracking
   - Dependency: 006 (needs working events/packages)

3. **User Testing Checkpoint**
   - Run local build with wife
   - Validate end-to-end workflow: Ingredients → Recipes → Bundles → Packages → Events → Production
   - Gather feedback on gaps and usability issues

4. **007, 009, 010, 011** - Prioritize based on user testing feedback

---

## Dependencies

```
006 Event Planning Restoration
 └── 008 Production Tracking
      └── [User Testing]
           ├── 007 Shopping List Variant Integration
           ├── 009 UI Import/Export
           ├── 010 Reporting Enhancements
           └── 011 Packaging & Distribution
```

---

## Notes

- **Disabled Models:** Bundle, Package, Event models were disabled during Phase 4 Ingredient/Variant refactor. Feature 006 restores these with updated foreign key relationships.

- **Shopping List Status:** Basic shopping list (needs - inventory = to buy) should function after 006. Feature 007 adds brand/variant recommendations as enhancement.

- **User Testing Priority:** Getting to testable state with core workflow is higher priority than polish features. Real-world usage will reveal actual gaps.

- **Spec-Kitty Workflow:** All features follow: specify → plan → tasks → implement → review → accept → merge

---

## Document History

- 2025-12-03: Initial creation based on project state assessment and roadmap discussion
