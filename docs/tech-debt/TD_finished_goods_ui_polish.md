# TD-XXX: Finished Goods Edit Form UI Polish

**Priority**: HIGH (Quick wins, high UX impact)  
**Estimated Effort**: 1-2 hours total  
**Type**: UI Polish / Bug Fix  

---

## Overview

Two UX issues discovered during user testing of Finished Goods Edit form that cause friction but are straightforward to fix.

---

## Issue 1: Save Button Hidden Below Scroll

**Problem:**
- Save Finished Good button located inside scrollable content area
- Hidden when form content scrolled up
- User must scroll to bottom to find Save button
- Violates UX principle: primary actions should always be visible

**Current Structure:**
```
Dialog Frame
└─ Scrollable Content Frame
   ├─ Step 1: Food Selection
   ├─ Step 2: Materials  
   ├─ Step 3: Review
   └─ [Save Finished Good] [Start Over] [Cancel]  ← Inside scroll area
```

**Target Structure:**
```
Dialog Frame
├─ Scrollable Content Frame
│  ├─ Step 1: Food Selection
│  ├─ Step 2: Materials  
│  └─ Step 3: Review
└─ Fixed Button Frame (bottom of dialog)
   └─ [Save Finished Good] [Start Over] [Cancel]  ← Always visible
```

**Implementation:**
- Move button frame outside scrollable content
- Place in fixed footer at bottom of dialog
- Ensure proper spacing/padding
- Test with long form content (buttons stay anchored)

**Files Affected:**
- `src/ui/finished_goods/finished_goods_builder_dialog.py` (or similar)

**Success Criteria:**
- Save, Start Over, Cancel buttons always visible regardless of scroll position
- Buttons anchored to bottom of dialog
- No layout breaks with varying content lengths

---

## Issue 2: Cannot Distinguish EA vs SERVINGS Finished Units

**Problem:**
- Multiple FinishedUnits can have same name but different yield types
- Example: "Butterscotch Pumpkin Cake" exists as both EA (1 cake) and SERVINGS (12 servings)
- Food Selection list shows identical names with no distinguishing information
- User cannot tell which one to select

**Current Display:**
```
Food Selection list shows item names with checkboxes and quantity fields:

[ ] Butterscotch Pumpkin Cake         [1]
[ ] Butterscotch Pumpkin Cake         [1]
[ ] Lemon Bliss Cake                  [1]
[ ] Lemon Bliss Cake                  [1]
```

No additional detail shown - identical names appear multiple times with no way to distinguish which is EA vs SERVINGS yield type.

**Target Display:**
```
Append yield type to item name:

[ ] Butterscotch Pumpkin Cake (EA)         [1]
[ ] Butterscotch Pumpkin Cake (SERVINGS)   [1]
[ ] Lemon Bliss Cake (EA)                  [1]
[ ] Lemon Bliss Cake (SERVINGS)            [1]
```

**Why this approach:**
- Information at point of decision (the name the user reads first)
- Visually distinct without adding UI complexity
- Minimal layout changes - just append text to existing name field
- Consistent with other disambiguating patterns (e.g., "LARGE" in "Eggnog Cake LARGE")

**Data Available:**
- FinishedUnit model has `yield_type` field (EA, WEIGHT, SERVINGS, VOLUME)
- Already queried, just not displayed

**Implementation:**
- Query includes yield_type (likely already does)
- Format display string: `f"{finished_unit.name} ({finished_unit.yield_type.value})"`
- Update item list rendering in Food Selection step

**Files Affected:**
- `src/ui/finished_goods/finished_goods_builder_dialog.py` (Step 1 item list rendering)
- Possibly item formatting utility function if one exists

**Success Criteria:**
- All FinishedUnits display with yield type appended in parentheses
- Duplicate names distinguishable at a glance
- No confusion about which item to select

---

## Testing

**Manual Testing Required:**

**Issue 1 (Save Button):**
1. Open Finished Goods Edit dialog
2. Scroll content up and down
3. Verify Save/Start Over/Cancel buttons always visible at bottom
4. Test with short content (few items) and long content (many items)

**Issue 2 (Yield Type Display):**
1. Create/find recipe with multiple yield types (EA and SERVINGS)
2. Open Finished Goods Edit dialog
3. Navigate to Food Selection step
4. Verify FinishedUnits show yield type in name: "Item Name (EA)"
5. Verify duplicate names now distinguishable

---

## Notes

- Both issues are cosmetic/UX polish, not functional bugs
- High value-to-effort ratio (< 2 hours total for significant UX improvement)
- Discovered during user testing with primary user (Marianne)
- Should be fixed before next user testing session to avoid repeated friction

---

## Related Issues

- None (standalone UI polish items)

---

## Acceptance Criteria

**Issue 1:**
- [ ] Save button visible without scrolling
- [ ] Start Over button visible without scrolling  
- [ ] Cancel button visible without scrolling
- [ ] Buttons remain anchored during scroll
- [ ] Layout works with varying content lengths

**Issue 2:**
- [ ] All FinishedUnits show yield type in display name
- [ ] Format: "Item Name (YIELD_TYPE)"
- [ ] Duplicate names distinguishable
- [ ] No layout breaks with longer names
- [ ] User testing confirms clarity
