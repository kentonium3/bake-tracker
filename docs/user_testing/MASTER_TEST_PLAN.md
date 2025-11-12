# Seasonal Baking Tracker - Master Test Plan

**Version:** 1.0
**Last Updated:** 2025-11-12
**Current Phase:** Phase 4 UI Completion - Session #6+ Testing

---

## 📋 Current Test Status

**Overall Progress:** 0/10 tests completed
**Last Test Session:** Session #6 (failed due to SQLAlchemy errors - now fixed)
**Next Action:** Run Session #7 with updated test plan

---

## 🎯 Active Test Suite - Session #7

### Test Environment Setup
- [ ] **ENV-01:** App launches without critical errors
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

### Core Functionality Tests

#### Test Group A: Ingredient Management
- [ ] **ING-01:** Duplicate ingredient detection shows friendly error
  - **Action:** Try to add "Black Licorice" (already exists)
  - **Expected:** User-friendly popup error message
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **ING-02:** Add new ingredient successfully
  - **Action:** Add "Test Sugar v6" / Category: "Sugar" / Unit: "cup"
  - **Expected:** Ingredient appears in list
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

#### Test Group B: Variant Management (Critical - Previous Failures)
- [ ] **VAR-01:** View Variants dialog opens without errors
  - **Action:** Select ingredient → Click "View Variants"
  - **Expected:** Dialog opens, no SQLAlchemy session errors
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **VAR-02:** Add Variant dialog shows preferred checkbox
  - **Action:** In Variants dialog → Click "Add Variant"
  - **Expected:** "Mark as Preferred" checkbox is visible
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **VAR-03:** Save variant with preferred setting
  - **Action:** Fill Brand: "Domino" / Qty: "5" / Unit: "lb" / Check "Preferred" → Save
  - **Expected:** Variant appears in list with ⭐ star, no session errors
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **VAR-04:** Refresh variants list shows saved variants
  - **Action:** Click "Refresh" in variants dialog
  - **Expected:** All variants display correctly, no session binding errors
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

#### Test Group C: Pantry Operations
- [ ] **PAN-01:** My Pantry tab displays content
  - **Action:** Click "My Pantry" tab
  - **Expected:** Tab shows controls and content (not blank screen)
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **PAN-02:** Add Pantry Item dialog opens successfully
  - **Action:** In My Pantry → Click "Add Pantry Item"
  - **Expected:** Dialog opens with ingredient/variant dropdowns, no session errors
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

- [ ] **PAN-03:** Add pantry item end-to-end workflow
  - **Action:** Select ingredient/variant → Enter quantity/date → Save
  - **Expected:** Item appears in pantry list
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

#### Test Group D: Data Persistence (Critical)
- [ ] **PER-01:** Restart app retains all data
  - **Action:** Close app → Restart → Check all added data still exists
  - **Expected:** All ingredients, variants, pantry items persist correctly
  - **Status:** ⏳ PENDING
  - **Comments:**
  - **Images:**

---

## 📸 Image Guidelines

Save all test screenshots in: `user_testing/images/`

**Naming Convention:**
- `session7_test_[ID]_[status].png`
- Example: `session7_test_VAR01_PASS.png` or `session7_test_VAR03_FAIL.png`

**Link in test comments:**
```markdown
**Images:** ![Screenshot](images/session7_test_VAR01_PASS.png)
```

---

## 🔄 Test Iteration Process

### After Each Test Run:
1. **Update Status:** Change ⏳ PENDING to ✅ PASS or ❌ FAIL
2. **Add Comments:** Describe what happened, any errors seen
3. **Add Screenshots:** Link relevant images showing results
4. **Report Results:** Let Claude know which tests failed for immediate fixes

### When Tests Fail:
1. **Don't proceed:** Stop testing and report failure details
2. **Include specifics:** Error messages, unexpected behavior
3. **Add screenshots:** Visual evidence of the failure
4. **Wait for fixes:** Claude will fix issues and update test plan

### When All Tests Pass:
1. **Archive session:** Move to "Completed Sessions" section
2. **Plan next phase:** Add new test scenarios as needed
3. **Celebrate:** We're making progress! 🎉

---

## 📚 Test History

### Completed Sessions
*(None yet - Session #7 is our first with this new process)*

### Known Issues Fixed
- ✅ **Session #5:** SQLAlchemy session binding error (pantry service)
- ✅ **Session #6:** SQLAlchemy session binding error (variant service)
- ✅ **Previous:** My Pantry blank screen, missing Preferred checkbox, ValidationError formatting

---

## 🎯 Success Criteria

**Session #7 Success Definition:**
- All 10 tests in Active Test Suite show ✅ PASS
- No critical SQLAlchemy session errors
- Core ingredient → variant → pantry workflow functional
- Data persists across app restarts

**Overall Phase 4 Success:**
- End-to-end workflow: Add Ingredient → Add Variant → Add Pantry Item → View/Manage inventory
- No critical bugs in core functionality
- Ready for integration with Recipes/Events tabs (next phase)

---

*This document will be continuously updated as we iterate through testing sessions.*