# Bug Fix: Remove Obsolete View Products Button from Ingredients Tab

**Branch**: `bugfix/remove-view-products-button`  
**Priority**: Low (cleanup, remove unused functionality)  
**Estimated Effort**: 15 minutes

## Context

The "View Products" button on My Ingredients tab appears to connect to an obsolete form. If the form is no longer needed, both the button and form should be removed.

## Changes Required

### 1. Remove View Products Button
**File**: `src/ui/ingredients_tab.py`

1. Locate "View Products" button in UI layout
2. Remove button widget
3. Remove button click handler method
4. Clean up any related instance variables

### 2. Identify and Remove Associated Form
**Location**: Unknown - need to find it

1. Trace the button's command/handler to find which form/dialog it opens
2. Check if form is used anywhere else
3. If form is only used by this button, remove the entire form file
4. Remove any imports related to the form

### 3. Verify No Other References
**Files**: Search codebase

1. Search for references to the form class
2. Search for references to the button handler
3. Ensure no other code depends on removed functionality

## Testing Checklist

- [ ] My Ingredients tab displays without View Products button
- [ ] No errors when loading Ingredients tab
- [ ] All other Ingredients tab functionality works (add, edit, delete, filter)
- [ ] No broken imports or references
- [ ] Application starts cleanly

## Success Criteria

1. **Button Removed**: View Products button no longer visible
2. **Form Removed**: Associated form deleted if unused elsewhere
3. **No Errors**: No console errors or broken references
4. **Clean Code**: Related handlers and imports removed

## Git Workflow

```bash
git checkout -b bugfix/remove-view-products-button
git commit -m "remove: obsolete View Products button and form from ingredients tab"
git push
```

---

**Simple Cleanup**: Remove unused UI element and associated code.
