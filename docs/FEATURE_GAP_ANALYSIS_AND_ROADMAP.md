# Feature Gap Analysis & Implementation Roadmap
**Date:** 2026-01-05
**Purpose:** Align pending features with updated requirements, identify gaps, recommend implementation order

---

## Executive Summary

Analysis of requirements (req_*.md) against pending features (_F038-_F041) and completed work (F031-F037) reveals:

**Status:**
- ✅ Ingredient Hierarchy complete (F031-F036)
- ✅ Recipe Redesign complete (F037)
- ⏳ 4 pending features (_F038-_F041)
- ❌ **Major gap:** Planning Workspace (req_planning.md) has NO feature spec

**Key Finding:** The most critical requirement (Planning - automatic batch calculation) has no implementation plan, while pending features address secondary concerns.

**Recommendation:** Reorder features to prioritize Planning Workspace, which is the PRIMARY VALUE PROPOSITION.

---

## Requirements Coverage Analysis

### Documented Requirements

| Requirement | Status | Features Addressing It |
|-------------|--------|----------------------|
| req_ingredients.md | ✅ COMPLETE | F031-F036 complete, shelf life in F041 |
| req_inventory.md | 🟡 PARTIAL | FIFO exists, F041 adds shelf life, **F039 adds AI purchase** |
| req_recipes.md | ✅ COMPLETE | F037 complete (template/snapshot) |
| req_planning.md | ❌ **NO FEATURES** | **CRITICAL GAP** |
| req_products.md | 🟡 PARTIAL | Basic catalog exists, lacks advanced features |
| req_finished_goods.md | 🟡 PARTIAL | Basic models exist, F040 adds service layer |
| req_application.md | 🟢 ONGOING | F038 UI restructure |

### Critical Findings

**1. Planning is THE Core Value Proposition**
From req_planning.md:
> **Core Problem:** Marianne consistently underproduces for events due to manual batch calculations. This year she ran short on nearly all finished goods, providing the primary motivation for building this application.

**Current State:** NO feature spec exists for this critical requirement

**2. Pending Features Focus on Secondary Concerns**
- F038 (UI Restructure): Important for UX but not core value
- F039 (AI Purchase): Nice-to-have efficiency gain
- F040 (Finished Goods): Architecture only, no UI
- F041 (Shelf Life): Enhancement, not core workflow

---

## Pending Features Deep Dive

### F038: UI Mode Restructure
**Purpose:** Reorganize 11 flat tabs into 5 workflow modes
**Blocks:** Planning Workspace (needs mode structure)
**Value:** Foundation for better UX
**Priority:** HIGH (blocking)
**Estimated Effort:** 20-30 hours

**Assessment:** ✅ KEEP - Required foundation for Planning Workspace

---

### F039: Purchase Workflow & AI Assist
**Purpose:** AI-assisted batch purchase import (Google AI Studio)
**Addresses:** req_inventory.md Section 4.2 Use Case
**Value:** Reduces 30-45 min data entry to <5 minutes
**Priority:** MEDIUM (efficiency gain)
**Estimated Effort:** 24-32 hours

**Assessment:** 🟡 DEFER - Nice-to-have, not critical path
**Reason:** Manual entry works; Planning is more urgent

---

### F040: Finished Goods Inventory
**Purpose:** Service layer for finished goods inventory management
**Addresses:** req_finished_goods.md (partial)
**Value:** Architecture preparation for Phase 3
**Priority:** LOW (architecture only, no UI)
**Estimated Effort:** 8-12 hours

**Assessment:** 🟡 DEFER - Phase 3 concern
**Reason:** Phase 2 doesn't use finished goods inventory

---

### F041: Shelf Life & Freshness Tracking
**Purpose:** Track ingredient shelf life, compute expiration dates
**Addresses:** req_ingredients.md (REQ-ING-024 through REQ-ING-032), req_inventory.md (REQ-INV-033 through REQ-INV-037)
**Value:** Prevents waste, improves inventory management
**Priority:** MEDIUM (enhancement)
**Estimated Effort:** 16-24 hours

**Assessment:** 🟡 DEFER to after Planning
**Reason:** Shelf life is valuable but not core workflow blocker

---

## Missing Features (Gaps)

### F0XX: Planning Workspace (CRITICAL - NO SPEC EXISTS)
**Purpose:** The core value proposition - automatic batch calculation
**Addresses:** req_planning.md (entire document)
**Value:** **SOLVES THE PRIMARY PROBLEM** - prevents underproduction
**Priority:** **CRITICAL (P0)**
**Estimated Effort:** 40-60 hours

**Requirements:**
1. Event definition UI
2. Finished goods requirements input
3. Automatic batch calculation from recipes
4. Ingredient aggregation across recipes
5. Inventory gap analysis (what to buy)
6. Shopping list generation
7. Assembly feasibility check

**Dependencies:**
- ✅ Recipes (F037 complete - has scaling/batching)
- ✅ Ingredients (F031-F036 complete)
- ⏳ UI Mode Structure (F038 needed first)
- 🟡 Inventory (basic FIFO exists, good enough)

**Blocks:**
- Everything else - this IS the application

**Status:** **NEEDS SPEC IMMEDIATELY**

---

### F0XX: Manual Inventory Adjustments
**Purpose:** Record spoilage, gifts, ad hoc usage outside app
**Addresses:** req_inventory.md Section 3.2 (now Phase 2)
**Value:** Complete inventory accuracy
**Priority:** MEDIUM (moved to Phase 2 per recent req update)
**Estimated Effort:** 8-12 hours

**Requirements:**
- Manual inventory depletion UI
- Depletion reason dropdown (spoilage, gift, adjustment, etc.)
- Notes field for context
- Validation (can't deplete more than available)

---

### F0XX: Product Shelf Life Inheritance & Display
**Purpose:** Products inherit shelf life from ingredients, display in UI
**Addresses:** req_ingredients.md REQ-ING-029, REQ-ING-030
**Value:** Complete shelf life system (F041 partial)
**Priority:** MEDIUM (completes F041)
**Estimated Effort:** 4-6 hours

---

## Recommended Implementation Order

### Phase 2A: Foundation (4-6 weeks)
**Goal:** Enable Planning Workspace

1. **F038: UI Mode Restructure** (20-30 hrs)
   - Creates "Plan" mode structure
   - Establishes dashboard pattern
   - **Blocks:** Planning Workspace needs mode structure

2. **F0XX: Planning Workspace - Specification** (12-16 hrs)
   - Create comprehensive spec from req_planning.md
   - Design UI mockups
   - Define service layer contracts
   - **Critical:** This is missing entirely

3. **F0XX: Planning Workspace - Implementation** (40-60 hrs)
   - Event requirements input
   - Automatic batch calculation
   - Ingredient gap analysis
   - Shopping list generation
   - **Delivers:** THE CORE VALUE

**Total Phase 2A:** 72-106 hours (~2-3 months)

---

### Phase 2B: Enhancement (3-4 weeks)
**Goal:** Complete Phase 2 requirements

4. **F041: Shelf Life & Freshness** (16-24 hrs)
   - Ingredient shelf life field & UI
   - Expiration date computation
   - Freshness indicators in Inventory tab
   - **Delivers:** Prevents waste

5. **F0XX: Manual Inventory Adjustments** (8-12 hrs)
   - Manual depletion UI
   - Depletion reasons
   - **Delivers:** Complete inventory accuracy

**Total Phase 2B:** 24-36 hours (~1 month)

---

### Phase 2C: Efficiency (3-4 weeks) - Optional
**Goal:** Reduce friction in existing workflows

6. **F039: AI-Assisted Purchase** (24-32 hrs)
   - Google AI Studio integration
   - UPC matching
   - Batch import workflow
   - **Delivers:** Massive time savings (45 min → 5 min)

**Total Phase 2C:** 24-32 hours (~1 month)

---

### Deferred to Phase 3

7. **F040: Finished Goods Inventory** (8-12 hrs)
   - Architecture only
   - No UI in Phase 2
   - **Reason:** Phase 2 doesn't need finished goods inventory

---

## Risk Analysis

### Highest Risk: No Planning Spec
**Risk:** Most critical feature has no implementation plan
**Impact:** Application cannot deliver core value proposition
**Mitigation:** Create F0XX Planning Workspace spec immediately
**Timeline:** Spec should be written this week

### Second Risk: Feature Ordering
**Risk:** Working on F039/F040/F041 before Planning wastes time
**Impact:** Delays core value delivery, may not finish Phase 2
**Mitigation:** Reorder per recommendation above

### Third Risk: Scope Creep
**Risk:** F038 UI restructure could balloon in scope
**Impact:** Delays Planning Workspace
**Mitigation:** Time-box F038 to 30 hours maximum, iterate later

---

## Immediate Action Items

1. **CREATE F0XX: Planning Workspace Specification**
   - Owner: Kent (with Claude/spec-kitty)
   - Timeline: This week (Jan 6-10)
   - Input: req_planning.md
   - Output: Comprehensive feature spec

2. **Review F038 Scope**
   - Ensure it's minimal viable for Planning mode
   - Time-box to 30 hours
   - Defer polish to post-Planning

3. **Update Feature Roadmap**
   - Renumber features
   - Mark F039, F040, F041 as "deferred"
   - Add Planning Workspace as top priority

4. **Communicate Priority Shift**
   - Planning is THE critical path
   - Everything else is secondary
   - Phase 2 success = working Planning Workspace

---

## Conclusion

**The application's core value is automatic batch calculation to prevent underproduction.**

Current pending features (F038-F041) address UX polish and efficiency gains, but miss the primary requirement entirely. Planning Workspace must be specified and implemented before other enhancements.

**Recommended immediate action:** Stop work on F039-F041, complete F038 as minimal foundation, then CREATE and IMPLEMENT Planning Workspace.

**Timeline Impact:** 
- Current plan (F038-F041): ~68-98 hours, doesn't deliver core value
- Recommended plan (F038 + Planning): ~60-90 hours, DOES deliver core value

**ROI:** Reordering focuses effort on the feature that solves Marianne's actual problem (underproduction), rather than nice-to-have enhancements.

---

**END OF ANALYSIS**
