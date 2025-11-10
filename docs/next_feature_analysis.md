# Next Feature Implementation Analysis

**Date:** 2025-11-10
**Current Status:** Feature 002 (Service Layer) completed and merged to main
**Purpose:** Determine next feature for spec-kitty implementation cycle

---

## Current State Summary

### What's Complete ✅
- **Phase 1-3:** Foundation, Finished Goods, Event Planning (all complete)
- **Phase 4 Service Layer (Feature 002):** ✅ Complete
  - IngredientService, VariantService, PantryService, PurchaseService
  - 16/16 integration tests passing
  - FIFO consumption algorithm
  - Price trend analysis
  - All service infrastructure (exceptions, session_scope, validators)

### What's Pending ⏳
- **Phase 4 Remaining:**
  - UI implementation (My Ingredients, My Pantry tabs)
  - Data migration execution from v0.3.0 to v0.4.0
  - Recipe/Event service integration with new architecture

- **Phase 5 (Newly Planned):**
  - Materials model & service
  - Bundle-Material associations
  - Auto-creation of Finished Goods (discrete yield flag)
  - Production checkoff workflows
  - Consolidated event summary enhancements
  - Quick inventory update feature

---

## Decision Point: Next Feature

### Option A: Feature 003 - Phase 4 UI Completion
**Description:** Complete Phase 4 by implementing UI for Ingredient/Variant/Pantry architecture

**Scope:**
1. **My Ingredients Tab** (src/ui/ingredients_tab.py - NEW)
   - Ingredient catalog management (generic ingredients)
   - Variant management (brands, packages, preferred variant)
   - Search/filter by category
   - Add/Edit/Delete operations
   - Industry standard fields (optional)

2. **My Pantry Tab** (src/ui/pantry_tab.py - NEW)
   - Pantry inventory by variant with lot tracking
   - FIFO consumption interface
   - Add pantry items (purchase date, location, expiration)
   - View total quantity by ingredient (aggregated)
   - Expiring soon alerts
   - Consumption history

3. **Integration Tasks:**
   - Update main_window.py to add new tabs
   - Replace/deprecate old inventory_tab.py
   - Connect UI to ingredient_service, variant_service, pantry_service, purchase_service

4. **Migration Execution:**
   - Run migration script (dry-run → actual)
   - Validate data integrity
   - Verify cost calculations match v0.3.0

**Dependencies:**
- Service layer complete ✅
- Models refactored ✅
- Migration script ready ✅

**Benefits:**
- Completes Phase 4 end-to-end
- Enables users to interact with new architecture
- Validates service layer with real UI usage
- De-risks migration before adding more complexity
- Natural checkpoint before Phase 5

**Estimated Effort:** Medium-Large
- 2 new UI tabs (complex forms and tables)
- Migration execution and validation
- Integration with 4 services
- Testing and bug fixes

---

### Option B: Feature 004 - Phase 5 Materials & Enhanced Production Tracking
**Description:** Implement materials tracking and production workflow enhancements (User Stories 1-6)

**Scope:**
1. **Materials Model & Service** (NEW)
   - Material model (like legacy Ingredient)
   - MaterialService for CRUD operations
   - Inventory tracking for packaging supplies

2. **Bundle-Material Associations** (NEW)
   - BundleMaterial junction table
   - Associate materials with bundles
   - Quantity tracking per bundle

3. **Auto-Creation of Finished Goods** (User Story 1)
   - Add discrete_yield flag to Recipe model
   - Auto-create/update FinishedGood when flag enabled
   - Prevent duplicate finished goods

4. **Production Tracking** (User Stories 4 & 5)
   - Add production_status to FinishedGood
   - Add assembly_status to Bundle
   - Checkoff workflow in UI
   - Progress tracking

5. **Consolidated Event Summary** (User Story 2)
   - Enhanced event planning view
   - Aggregate ingredients + materials
   - Shopping list generation

6. **Quick Inventory Update** (User Story 3)
   - Event-specific inventory filter
   - Highlight missing/low items

**Dependencies:**
- Service layer complete ✅
- Phase 4 UI completion ❌ (NOT required but helpful)
- Materials can work independently of Ingredient/Variant UI

**Benefits:**
- Delivers new user-requested features immediately
- Materials system is independent (doesn't require Phase 4 UI)
- Provides high-value production tracking improvements
- Aligns with requirements.md v1.2 just completed

**Estimated Effort:** Large
- New model, service, and junction tables
- Recipe model updates
- Bundle model updates
- Event service enhancements
- Multiple UI updates (production tabs, assembly tabs)
- Snapshot updates

---

## Recommendation

### Primary Recommendation: **Option A - Feature 003 (Phase 4 UI Completion)**

**Rationale:**
1. **Natural Progression:** Complete Phase 4 before moving to Phase 5
2. **Validation:** UI implementation will reveal any service layer issues
3. **Migration Risk Mitigation:** Execute migration in isolation before adding materials complexity
4. **User Testing:** Get feedback on Ingredient/Variant architecture before expanding further
5. **Technical Debt:** Prevents accumulating unfinished phases
6. **Dependency Chain:** Phase 5 materials will benefit from having Phase 4 UI complete

**When to Choose Option A:**
- If you want to see the Ingredient/Variant architecture working end-to-end
- If you want to validate migration before adding more features
- If you want to reduce technical debt
- If you prefer completing one phase fully before starting the next

### Alternative: **Option B - Feature 004 (Phase 5 Materials)**

**Rationale:**
1. **User Priority:** Addresses fresh user stories just documented
2. **Independence:** Materials can be implemented without Phase 4 UI
3. **Business Value:** Delivers production tracking improvements sooner
4. **Momentum:** Capitalizes on recent requirements analysis

**When to Choose Option B:**
- If materials tracking is urgent for upcoming event planning
- If you want to deliver User Stories 1-6 immediately
- If you're comfortable having Phase 4 UI incomplete
- If you prefer feature-driven development over phase completion

---

## Next Steps for Chosen Option

### If Option A (Phase 4 UI) - Recommended

**Step 1: Create Feature 003 Specification**
```bash
# Create feature directory structure
mkdir -p kitty-specs/003-phase4-ui-completion

# Create core spec files
touch kitty-specs/003-phase4-ui-completion/spec.md
touch kitty-specs/003-phase4-ui-completion/plan.md
touch kitty-specs/003-phase4-ui-completion/data-model.md
touch kitty-specs/003-phase4-ui-completion/meta.json

# Create work package directories
mkdir -p kitty-specs/003-phase4-ui-completion/tasks/{doing,done,for_review}
```

**Step 2: Write Feature Specification (spec.md)**
- Feature description: UI completion for Phase 4
- User scenarios for My Ingredients tab (5-7 stories)
- User scenarios for My Pantry tab (5-7 stories)
- Migration execution scenarios (3-4 stories)
- Acceptance criteria for each

**Step 3: Create Work Packages**
Suggested breakdown:
- **WP01:** My Ingredients Tab - Basic CRUD
- **WP02:** My Ingredients Tab - Variant Management
- **WP03:** My Pantry Tab - Inventory Display
- **WP04:** My Pantry Tab - FIFO & Consumption
- **WP05:** Migration Execution & Validation
- **WP06:** Integration Testing & Bug Fixes

**Step 4: Create Feature Branch**
```bash
git checkout -b 003-phase4-ui-completion
```

**Step 5: Begin Implementation**
- Start with WP01 (My Ingredients Tab basics)
- Iterate through work packages
- Test continuously with service layer

---

### If Option B (Phase 5 Materials) - Alternative

**Step 1: Create Feature 004 Specification**
```bash
# Create feature directory structure
mkdir -p kitty-specs/004-materials-and-production

# Create core spec files
touch kitty-specs/004-materials-and-production/spec.md
touch kitty-specs/004-materials-and-production/plan.md
touch kitty-specs/004-materials-and-production/data-model.md
touch kitty-specs/004-materials-and-production/meta.json

# Create work package directories
mkdir -p kitty-specs/004-materials-and-production/tasks/{doing,done,for_review}
```

**Step 2: Write Feature Specification (spec.md)**
- Feature description: Materials & production tracking
- User scenarios for each User Story (1-6)
- Material management scenarios
- Bundle-material association scenarios
- Production checkoff scenarios
- Acceptance criteria

**Step 3: Create Work Packages**
Suggested breakdown:
- **WP01:** Material Model & Service
- **WP02:** Bundle-Material Associations
- **WP03:** Auto-Creation of Finished Goods
- **WP04:** Production Tracking Status Fields
- **WP05:** Consolidated Event Summary UI
- **WP06:** Quick Inventory Update Feature
- **WP07:** Integration Testing

**Step 4: Create Feature Branch**
```bash
git checkout -b 004-materials-and-production
```

**Step 5: Begin Implementation**
- Start with WP01 (Material model & service)
- Follow pattern from IngredientService
- Iterate through work packages

---

## Spec-Kitty Workflow Checklist

For either option, follow this spec-kitty workflow:

### Pre-Implementation
- [ ] Create feature directory structure
- [ ] Write spec.md with user scenarios
- [ ] Create meta.json with feature metadata
- [ ] Write plan.md with work package breakdown
- [ ] Document data-model.md if schema changes needed
- [ ] Create initial work packages in tasks/doing/

### During Implementation
- [ ] Work on one work package at a time
- [ ] Move WP to tasks/doing/ when starting
- [ ] Update WP status as tasks complete
- [ ] Commit frequently with descriptive messages
- [ ] Move WP to tasks/done/ when complete

### Post-Implementation
- [ ] All work packages in tasks/done/
- [ ] Update tasks.md with completion status
- [ ] Run full test suite
- [ ] Update documentation (if needed)
- [ ] Accept feature with spec-kitty accept command
- [ ] Merge feature branch to main

---

## Resources Referenced

**Current Documentation:**
- `docs/requirements.md` v1.2 - Phase 5 specification
- `docs/current_priorities.md` - Phase 4 next steps
- `docs/development_status.md` - Project history
- `docs/user_stories.md` - Latest user requirements
- `kitty-specs/002-service-layer-for/` - Feature 002 structure

**Models & Services:**
- `src/models/` - Ingredient, Variant, PantryItem, Purchase
- `src/services/` - ingredient_service, variant_service, pantry_service, purchase_service

---

## Questions for User

1. **Which option do you prefer: Option A (Phase 4 UI) or Option B (Phase 5 Materials)?**

2. **Timing considerations:**
   - Is there an upcoming event that needs materials tracking urgently?
   - Is validating the migration more important right now?

3. **Scope flexibility:**
   - For Option A: Should we include Recipe/Event service integration?
   - For Option B: Can we defer some User Stories (e.g., 3, 4, 5) to later?

4. **Migration timing:**
   - Do you want to migrate data before or after Phase 5?
   - Are you comfortable with v0.3.0 schema until Phase 4 UI is complete?

---

**Recommendation Summary:**
**Choose Option A (Phase 4 UI Completion)** for natural progression and risk mitigation.
**Choose Option B (Phase 5 Materials)** if materials tracking is urgent business need.

Either way, follow the spec-kitty workflow detailed above for structured implementation.
