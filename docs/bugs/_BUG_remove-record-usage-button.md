# Bug Fix: Remove Redundant Record Usage Button

**Branch**: `bugfix/remove-record-usage-button`  
**Priority**: LOW (cleanup)  
**Estimated Effort**: 5 minutes

## Context

The orange "Record Usage" button at the top of the My Pantry tab is now redundant. The quantity update functionality has been moved into the Edit Inventory form as a collapsible calculator section (from BUG_inventory-quantity-calculator.md).

**Action**: Remove the button and its handler.

## Current State vs Expected

### Current (Redundant Button)
```
My Pantry Tab Toolbar:
[Add Item] [Record Usage] [Refresh] [Other buttons...]
              ↑ Redundant - remove this
```

### Expected (Clean)
```
My Pantry Tab Toolbar:
[Add Item] [Refresh] [Other buttons...]
```

## Implementation Requirements

### 1. Remove Record Usage Button
**File**: `src/ui/inventory_tab.py`

**Remove button widget**:
```python
# Find and remove these lines:
self.record_usage_btn = ctk.CTkButton(
    toolbar_frame,
    text="Record Usage",
    command=self._on_record_usage,
    fg_color="orange",  # or whatever color it is
    width=120,
)
self.record_usage_btn.pack(side="left", padx=5, pady=5)
# or .grid(...) depending on layout
```

### 2. Remove Handler Method
**File**: Same file

**Remove the handler**:
```python
# Find and remove this entire method:
def _on_record_usage(self):
    """Handle Record Usage button click."""
    # ... whatever this does ...
```

### 3. Remove Any Related Code
**File**: Same file

**Check for**:
- Imports related to record usage dialog/function
- Any state variables related to record usage
- Any comments or documentation references

## Implementation Tasks

### Task 1: Locate and Remove Button
**File**: `src/ui/inventory_tab.py`

1. Find the Record Usage button creation code
2. Delete the button widget lines
3. Adjust layout if needed (other buttons may shift)

### Task 2: Remove Handler Method
**File**: Same file

1. Find `_on_record_usage()` method
2. Delete the entire method
3. Check if it calls any other functions that are now unused

### Task 3: Clean Up Imports
**File**: Same file

1. Check imports at top of file
2. Remove any imports only used by Record Usage
3. Remove any related dialog/form imports

### Task 4: Verify No Other References
**Files**: Search codebase

```bash
# Search for references to record_usage
grep -r "record_usage" src/
grep -r "Record Usage" src/
```

If found elsewhere, remove those references too.

## Testing Checklist

### Visual
- [ ] Record Usage button no longer visible
- [ ] Toolbar layout looks clean (no gap)
- [ ] Other toolbar buttons still work
- [ ] Tab loads without errors

### Functionality
- [ ] Quantity updates work via Edit form calculator
- [ ] No console errors about missing handlers
- [ ] No broken imports

### Code Quality
- [ ] No dead code left behind
- [ ] No unused imports
- [ ] Layout code is clean

## Success Criteria

1. **Button Gone**: Record Usage button removed from toolbar
2. **No Errors**: Application runs without errors
3. **Clean Code**: No dead code or unused imports remain
4. **Alternative Works**: Users can update quantities via Edit form calculator

## Notes

**Why removing**:
- Functionality moved to Edit form as collapsible calculator
- Redundant button clutters UI
- Calculator approach is more discoverable and integrated

**User impact**:
- No functionality lost
- Cleaner, less cluttered interface
- Record usage now in the logical place (edit form)

## Related Issues

**Replaced by**:
- BUG_inventory-quantity-calculator.md - Calculator in edit form

## Related Files

**Primary File**:
- `src/ui/inventory_tab.py` - Toolbar with button

## Git Workflow

```bash
git checkout -b bugfix/remove-record-usage-button
git commit -m "remove: redundant Record Usage button from pantry toolbar"
git push
```

---

**Quick Cleanup**: 5-minute task to remove redundant UI element.
