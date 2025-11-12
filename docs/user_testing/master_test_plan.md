# Seasonal Baking Tracker - Master Test Plan

**Version:** 1.1
**Last Updated:** 2025-11-12
**Current Phase:** Phase 4 UI Completion - Session #8 Testing

---

## 📋 Current Test Status

**Overall Progress:** 9/10 tests completed (90% success rate!)
**Last Test Session:** Session #7 (major progress - SQLAlchemy errors resolved)
**Next Action:** Fix VAR-03 variant list display issue → Run Session #8

---

## 🎯 Active Test Suite - Session #8

### Test Environment Setup
- [ ] **ENV-01:** App launches without critical errors
  - **Action:** Start app, verify no critical error dialogs
  - **Expected:** App opens cleanly
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

### Core Functionality Tests

#### Test Group A: Ingredient Management
- [ ] **ING-01:** Duplicate ingredient detection shows friendly error
  - **Action:** Try to add "Black Licorice" (already exists)
  - **Expected:** User-friendly popup error message
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **ING-02:** Add new ingredient successfully
  - **Action:** Add "Test Sugar v7" / Category: "Sugar" / Unit: "cup"
  - **Expected:** Ingredient appears in list
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

#### Test Group B: Variant Management (Critical - VAR-03 was failing)
- [ ] **VAR-01:** View Variants dialog opens without errors
  - **Action:** Select ingredient → Click "View Variants"
  - **Expected:** Dialog opens, no SQLAlchemy session errors
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **VAR-02:** Add Variant dialog shows preferred checkbox
  - **Action:** In Variants dialog → Click "Add Variant"
  - **Expected:** "Mark as Preferred" checkbox is visible
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **VAR-03:** Save variant with preferred setting (CRITICAL FIX)
  - **Action:** Fill Brand: "Domino" / Qty: "5" / Unit: "lb" / Check "Preferred" → Save
  - **Expected:** Variant appears in list with proper variant name (not ingredient name) and ⭐ star
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **VAR-04:** Refresh variants list shows saved variants
  - **Action:** Click "Refresh" in variants dialog
  - **Expected:** All variants display correctly with proper variant names
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

#### Test Group C: Pantry Operations
- [ ] **PAN-01:** My Pantry tab displays content
  - **Action:** Click "My Pantry" tab
  - **Expected:** Tab shows controls and content (not blank screen)
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **PAN-02:** Add Pantry Item dialog opens successfully
  - **Action:** In My Pantry → Click "Add Pantry Item"
  - **Expected:** Dialog opens with ingredient/variant dropdowns, no session errors
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

- [ ] **PAN-03:** Add pantry item end-to-end workflow
  - **Action:** Select ingredient/variant → Enter quantity/date → Save
  - **Expected:** Item appears in pantry list with visible quantities
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

#### Test Group D: Data Persistence (Critical)
- [ ] **PER-01:** Restart app retains all data
  - **Action:** Close app → Restart → Check all added data still exists
  - **Expected:** All ingredients, variants, pantry items persist correctly
  - [ ] **PASS** - [ ] **FAIL**
  - **Comments:**
  - **Images:**

---

## 📸 Image Guidelines

Save screenshots in: `docs/user_testing/images/`
Use any filename - no naming convention required. Just drag and drop images into the markdown.

---

## 🔄 Test Iteration Process

### After Each Test Run:
1. **Check boxes:** Mark [x] for PASS or FAIL
2. **Add Comments:** Describe what happened, any errors seen
3. **Add Screenshots:** Drag/drop relevant images
4. **Report Results:** Let Claude know which tests failed for immediate fixes

### When Tests Fail:
1. **Stop testing** and report failure details
2. **Include specifics:** Error messages, unexpected behavior
3. **Add screenshots:** Visual evidence of the failure
4. **Wait for fixes:** Claude will fix issues and update test plan

---

## 📚 Test History

### Completed Sessions

#### ✅ Session #7 Results (9/10 PASS - 90% Success!)
- **ENV-01:** ✅ PASS - App launches without critical errors
- **ING-01:** ✅ PASS - Duplicate ingredient detection works
- **ING-02:** ✅ PASS - Add new ingredient successful
- **VAR-01:** ✅ PASS - View Variants dialog opens without errors
- **VAR-02:** ✅ PASS - Add Variant dialog shows preferred checkbox
- **VAR-03:** ❌ FAIL - Variant list shows ingredient name instead of variant name
- **VAR-04:** ✅ PASS - Refresh variants list works
- **PAN-01:** ✅ PASS - My Pantry tab displays content
- **PAN-02:** ✅ PASS - Add Pantry Item dialog opens (note: quantities not visible in list)
- **PAN-03:** ✅ PASS - Add pantry item end-to-end workflow
- **PER-01:** ✅ PASS - Restart app retains all data

### Known Issues Fixed
- ✅ **Session #5:** SQLAlchemy session binding error (pantry service)
- ✅ **Session #6:** SQLAlchemy session binding error (variant service)
- ✅ **Previous:** My Pantry blank screen, missing Preferred checkbox, ValidationError formatting

### Issues to Fix
- 🔧 **VAR-03:** Variant list display shows ingredient name instead of variant name/brand
- 🔧 **PAN-02:** Pantry list should show quantities (enhancement)

---

## 🎯 Success Criteria

**Session #8 Success Definition:**
- VAR-03 fixed: Variant list shows proper variant names (brand, size, etc.)
- All 10 tests show PASS
- Core ingredient → variant → pantry workflow fully functional

**Overall Phase 4 Success:**
- End-to-end workflow: Add Ingredient → Add Variant → Add Pantry Item → View/Manage inventory
- No critical bugs in core functionality
- Ready for integration with Recipes/Events tabs (next phase)

---

*This document will be continuously updated as we iterate through testing sessions.*