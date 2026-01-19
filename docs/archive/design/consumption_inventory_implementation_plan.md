# CONSUMPTION & INVENTORY MANAGEMENT - IMPLEMENTATION PLAN

**Version:** 1.0
**Date:** 2025-11-14
**Status:** ACTIVE
**Based on:** Consumption & Inventory Management Design Document v1.1

---

## 🎯 **PROJECT OVERVIEW**

**Goal:** Implement consumption and inventory management features through 11 logical feature additions
**Approach:** Strict spec-kitty workflow adherence for each feature
**Constitution:** No changes needed (confirmed from previous analysis)
**Cursor Integration:** Available for parallel development and code review

---

## 📋 **IMPLEMENTATION STRATEGY**

### **Core Principles:**
- **Each feature delivers working user value**
- **Build foundation → calculation engine → UI → integration**
- **Maintain backward compatibility during transitions**
- **Prioritize testability and solid data model**
- **Follow full spec-kitty workflow for every feature**

### **Quality Focus:**
- Comprehensive testing at each layer
- Consistent UI patterns (dense design from pantry)
- Event-driven architecture throughout
- FIFO consumption accuracy
- User experience optimization

---

## 🏗️ **FEATURE IMPLEMENTATION SEQUENCE**

### **FOUNDATION LAYER (Features 4-5)**

#### **Feature 004: ProductionRun Core Architecture**
**Goal:** Establish event-driven production data model
**User Value:** Foundation for all production planning

**Scope:**
- Create ProductionRun model with event association
- Create ProductionStatus enum (planned/in_progress/completed)
- Add production_runs table and relationships
- Basic CRUD operations and service layer
- Database migrations and constraints

**Testing Focus:**
- Unit tests for model relationships and validations
- Database constraint enforcement
- Service layer CRUD operations
- Migration safety and rollback

**Acceptance Criteria:**
- ProductionRun can be created with event association
- Status transitions work correctly
- Database relationships maintain integrity
- Service layer provides clean API

---

#### **Feature 005: FinishedUnit Model Refactoring**
**Goal:** Replace FinishedGood concept with individual unit tracking
**User Value:** Proper conceptual foundation for batch calculations

**Scope:**
- Global rename FinishedGood → FinishedUnit throughout codebase
- Update database schema and migrations
- Modify service layer for individual unit concepts
- Update existing UI references and terminology
- Maintain backward compatibility during transition

**Testing Focus:**
- Migration tests for data preservation
- Backward compatibility verification
- UI terminology consistency
- Service layer functionality preservation

**Acceptance Criteria:**
- All FinishedGood references updated to FinishedUnit
- Existing functionality unchanged
- Database migration completes successfully
- No broken UI references

---

### **CALCULATION ENGINE LAYER (Features 6-7)**

#### **Feature 006: Batch Calculation Service**
**Goal:** Core "how many batches do I need?" engine
**User Value:** Answers primary user question about production scale

**Scope:**
- Implement batch requirement calculation logic
- Handle recipe yield vs target quantity math
- Support packaging constraint rounding
- Create calculation service with comprehensive testing
- Edge case handling (zero yield, fractional batches)

**Testing Focus:**
- Comprehensive unit tests for edge cases
- Rounding scenario validation
- Performance testing for complex calculations
- Error handling for invalid inputs

**Acceptance Criteria:**
- Accurate batch calculation for all scenarios
- Proper rounding for packaging constraints
- Performance acceptable for complex recipes
- Clear error messages for invalid inputs

---

#### **Feature 007: Multi-Recipe Event Planning**
**Goal:** Coordinate multiple ProductionRuns per event
**User Value:** Plan complex events with multiple food items

**Scope:**
- Extend Events to contain multiple required items
- Create ProductionRun generation from event requirements
- Build total ingredient analysis across multiple recipes
- Implement availability vs requirements checking
- Cross-recipe dependency handling

**Testing Focus:**
- Integration tests for multi-recipe scenarios
- Ingredient aggregation accuracy
- Event-to-ProductionRun generation
- Complex event planning workflows

**Acceptance Criteria:**
- Events can contain multiple food requirements
- ProductionRuns generated automatically from requirements
- Ingredient totals calculated correctly across recipes
- Availability checking works for complex events

---

### **UI FOUNDATION LAYER (Features 8-9)**

#### **Feature 008: Enhanced Pantry Adjust Mode**
**Goal:** Simplified inventory adjustments with percentage support
**User Value:** Addresses User Stories 10-11 for quick inventory updates

**Scope:**
- Add toggle "Adjust Mode" to My Pantry tab
- Implement inline editing for quantities
- Support both absolute and percentage input
- Remove complex reason tracking (initially)
- Streamlined UI for rapid inventory updates

**Testing Focus:**
- UI interaction tests for adjust mode
- Input validation for percentages and absolutes
- Data persistence verification
- User experience flow testing

**Acceptance Criteria:**
- Adjust mode toggles cleanly in pantry UI
- Both percentage and absolute input work correctly
- Changes persist properly to database
- UI provides clear feedback during updates

---

#### **Feature 009: Event Production Planning UI**
**Goal:** Event-driven production planning interface
**User Value:** Primary entry point for production planning

**Scope:**
- Create event production requirements management
- Add ProductionRun display within events
- Show batch calculations and ingredient requirements
- Implement "Add Required Item" workflow
- Dense UI pattern application

**Testing Focus:**
- End-to-end workflow tests from event to production
- UI responsiveness with complex events
- Batch calculation display accuracy
- User workflow optimization

**Acceptance Criteria:**
- Events show production requirements clearly
- Batch calculations display in real-time
- "Add Required Item" workflow intuitive
- UI follows dense design pattern

---

### **EXECUTION LAYER (Features 10-11)**

#### **Feature 010: Production Execution Workflow**
**Goal:** Execute ProductionRuns with consumption tracking
**User Value:** Complete production-to-inventory workflow

**Scope:**
- Add production start workflow with FIFO preview
- Implement actual ingredient consumption
- Create batch completion tracking
- Connect to FinishedUnit creation
- Progress monitoring within ProductionRuns

**Testing Focus:**
- FIFO consumption correctness
- Inventory update validation
- Progress tracking accuracy
- Error handling for insufficient ingredients

**Acceptance Criteria:**
- Production start shows accurate FIFO preview
- Ingredient consumption updates inventory correctly
- Batch progress tracked properly
- FinishedUnits created upon completion

---

#### **Feature 011: Cross-Run Ingredient Analysis**
**Goal:** Event-level ingredient planning and shopping lists
**User Value:** Complete event planning with shopping preparation

**Scope:**
- Aggregate ingredient needs across multiple ProductionRuns
- Generate consolidated shopping lists
- Show availability vs total requirements
- Implement shortage detection and alerts
- Shopping optimization suggestions

**Testing Focus:**
- Cross-recipe calculation accuracy
- Shopping list generation correctness
- Availability analysis precision
- Alert system reliability

**Acceptance Criteria:**
- Ingredient totals accurate across all ProductionRuns
- Shopping lists generated with correct quantities
- Shortages detected and highlighted
- Alerts provide actionable information

---

### **INTEGRATION LAYER (Features 12-13)**

#### **Feature 012: Production Progress Dashboard**
**Goal:** Visual production management and status tracking
**User Value:** Clear visibility into production status and progress

**Scope:**
- Create production progress views within events
- Add batch-level progress indicators
- Implement production timeline display
- Show completion status across all event requirements
- Visual status indicators and progress bars

**Testing Focus:**
- Progress calculation accuracy
- UI state management
- Real-time update functionality
- Visual indicator correctness

**Acceptance Criteria:**
- Progress displays accurately reflect actual status
- Visual indicators update in real-time
- Timeline view provides clear overview
- Status tracking works across multiple ProductionRuns

---

#### **Feature 013: Dense UI Pattern Standardization**
**Goal:** Apply pantry's superior design pattern globally
**User Value:** Consistent, efficient UI experience across all tabs

**Scope:**
- Redesign My Ingredients with dense column pattern
- Standardize column widths and action patterns
- Apply consistent padding and inline actions
- Remove disabled button states throughout app
- Implement fixed-width column layouts

**Testing Focus:**
- Visual regression tests
- UI consistency verification
- Performance impact assessment
- User experience validation

**Acceptance Criteria:**
- All tabs follow consistent dense UI pattern
- Column widths standardized across app
- Inline actions work consistently
- No disabled button states remain

---

### **POLISH LAYER (Feature 14)**

#### **Feature 014: Production Workflow Integration Polish**
**Goal:** Final integration touches and user experience refinement
**User Value:** Seamless, polished production planning experience

**Scope:**
- Add cross-tab navigation from production to pantry/ingredients
- Implement production shortcuts and workflow optimizations
- Add comprehensive error handling and user feedback
- Create production workflow documentation
- Performance optimization and polish

**Testing Focus:**
- End-to-end user journey tests
- Error scenario coverage
- Performance validation
- Documentation completeness

**Acceptance Criteria:**
- Cross-tab navigation works seamlessly
- Error handling provides helpful feedback
- Workflow feels intuitive and efficient
- Documentation covers all user scenarios

---

## 🔄 **WORKFLOW EXECUTION STRATEGY**

### **Spec-Kitty Command Order (For Each Feature):**

```bash
# 1. Feature Specification
/spec-kitty.specify

# 2. Research (if needed for complex features)
/spec-kitty.research

# 3. Implementation Planning
/spec-kitty.plan

# 4. Task Breakdown
/spec-kitty.tasks

# 5. Development Execution
/spec-kitty.implement

# 6. Code Review
/spec-kitty.review

# 7. Acceptance Testing
/spec-kitty.accept

# 8. Merge to Main
/spec-kitty.merge
```

### **Quality Gates:**
- **Each feature must pass acceptance before next begins**
- **No shortcuts or workflow deviations**
- **Comprehensive testing at each stage**
- **Documentation updated per feature**

---

## 🎮 **CURSOR INTEGRATION OPPORTUNITIES**

### **Parallel Development Potential:**
- **Features 4-5:** Different data layers, can parallelize
- **Features 6-7:** Backend/frontend split possible
- **Features 8-9:** UI/UX can parallel backend work
- **Features 12-13:** Dashboard and standardization can overlap

### **Code Review Strategy:**
- Use Cursor for **cross-feature consistency** analysis
- **Pattern conformance** checking (dense UI application)
- **Performance impact** assessment for database changes
- **Test coverage** gap identification
- **Migration safety** verification

### **Quality Assurance:**
- **Naming consistency** during FinishedUnit refactoring
- **Database migration** safety analysis
- **UI pattern compliance** across features
- **Performance regression** detection

---

## 📊 **SUCCESS METRICS BY LAYER**

### **Foundation Success (Features 4-5):**
- ✅ ProductionRun model passes all relationship tests
- ✅ FinishedUnit refactoring maintains all existing functionality
- ✅ Zero regression in current workflows
- ✅ Database migrations complete without data loss

### **Engine Success (Features 6-7):**
- ✅ Batch calculation handles all edge cases correctly
- ✅ Multi-recipe events generate accurate ingredient totals
- ✅ Performance acceptable for 50+ recipe events
- ✅ Calculation accuracy verified against manual methods

### **UI Success (Features 8-14):**
- ✅ Pantry adjust mode reduces inventory update time by 75%
- ✅ Event planning workflow intuitive for new users
- ✅ Dense UI pattern applied consistently across all tabs
- ✅ Production workflow feels seamless and efficient

### **Integration Success:**
- ✅ End-to-end event-to-production workflow complete
- ✅ All User Stories 9-11 fully addressed
- ✅ No performance degradation from baseline
- ✅ Comprehensive test coverage maintained

---

## 📝 **TRACKING AND DOCUMENTATION**

### **Feature Documentation:**
- Each feature gets full spec-kitty artifact set
- Implementation notes captured in feature directories
- Decision rationale documented for future reference

### **Progress Tracking:**
- Feature completion status maintained
- Blocked/delayed features identified quickly
- Success metrics tracked per feature

### **Knowledge Management:**
- Implementation lessons learned captured
- Pattern decisions documented for consistency
- Testing strategies refined per feature

---

## 🚀 **NEXT STEPS**

**Starting Point:** Feature 004 - ProductionRun Core Architecture
**Current State:** Clean main branch with solid foundation from Phase 4
**Ready to Begin:** `/spec-kitty.specify` for Feature 004

**Command to Start:**
```bash
/spec-kitty.specify
```

---

## 📚 **RELATED DOCUMENTS**

- **Design Foundation:** `docs/design/consumption_inventory_design.md`
- **User Stories:** User Stories 9-11 in main documentation
- **Spec-Kitty Workflow:** [spec-kitty README Quick Reference](https://github.com/Priivacy-ai/spec-kitty/blob/main/README.md)
- **Phase 4 Completion:** Feature 003 artifacts for reference

---

**This plan provides a comprehensive roadmap for implementing the consumption and inventory management features while maintaining strict spec-kitty workflow adherence and optimizing for quality, testability, and user value delivery.**