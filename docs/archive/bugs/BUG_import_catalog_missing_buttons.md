# Claude Code Prompt: BUG FIX - Import Catalog Dialog Missing Action Buttons

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

## Bug Description

The Import Catalog dialog (accessed via File menu) is missing "Import" and "Cancel" buttons. Users can configure all import options but have no way to execute or cancel the import.

**Screenshot:** User provided screenshot showing the dialog with:
- File selection (working)
- Import Mode radio buttons (Add Only / Augment)
- Entities to Import checkboxes (Ingredients, Products, Recipes)
- Preview changes checkbox (dry-run)
- **NO action buttons at bottom**

## Expected Behavior

Dialog should have:
1. **Import** button (primary) — Executes the import with selected options
2. **Cancel** button (secondary) — Closes dialog without importing

Standard placement: Bottom-right of dialog, Cancel on left, Import on right.

## Files to Investigate

- `src/ui/dialogs/` — Look for catalog import dialog
- `src/ui/import_catalog_dialog.py` or similar
- Search for "Import Catalog" in UI code

## Fix Requirements

1. Add "Import" button that:
   - Validates a file is selected
   - Validates at least one entity type is checked
   - Calls the catalog import service with selected options
   - Shows progress/results
   - Closes dialog on success

2. Add "Cancel" button that:
   - Closes dialog without action

3. Follow existing dialog patterns in the codebase for button styling and placement

## Testing

1. Open app, go to File > Import Catalog
2. Verify Import and Cancel buttons are visible
3. Click Cancel — dialog closes, no import
4. Select file, check entities, click Import — import executes
5. Verify dry-run checkbox works (preview only, no changes)

## Deliverables

1. Fixed dialog with action buttons
2. Buttons wired to appropriate handlers
3. All existing tests pass
