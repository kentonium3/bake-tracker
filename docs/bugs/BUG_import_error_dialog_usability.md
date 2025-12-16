# Claude Code Prompt: BUG FIX - Import Error Dialog Usability + Data Issue

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

## Bug Report

User attempted to import `test_data/sample_data.json` and encountered:
1. Import failures due to NULL constraint on `finished_goods.display_name`
2. Error dialog with severe usability issues

## Part A: Investigate Import Failure

### Error Message
```
finished_good: brownie_box
(sqlite3.IntegrityError) NOT NULL constraint failed: finished_goods.display_name
[SQL: INSERT INTO finished_goods (slug, display_name, ...) VALUES (?, ?, ...)]
[parameters: ('cookie_assortment_box', None, ...)]
```

### Root Cause Investigation

1. Check `test_data/sample_data.json` for `finished_goods` entries
2. Compare field names against `docs/design/import_export_specification.md` v3.4
3. The spec requires `display_name` for finished_goods — verify the JSON uses this exact field name
4. Check if import service is mapping fields correctly in `src/services/import_export_service.py`

### Likely Issue
The JSON may use `name` instead of `display_name`, or the import service isn't reading the field correctly.

### Fix
- If JSON uses wrong field name → fix JSON
- If import service has mapping bug → fix service
- Ensure all finished_goods in sample_data.json have `display_name` populated

## Part B: Error Dialog Usability Issues

### Problems Reported
1. **Display extends past screen bottom** — Content overflows, can't see all errors
2. **Dialog not movable** — Can't reposition to see content
3. **No way to close/clear** — Missing Close/OK button
4. **Can't capture error text** — No copy functionality
5. **No logging** — Errors should be written to a log file

### Required Fixes

#### B.1: Scrollable Content
- Wrap error content in a scrollable frame
- Set reasonable max height (e.g., 400-500px)
- Ensure vertical scrollbar appears when content exceeds max height

#### B.2: Movable Dialog
- Ensure dialog window is movable (standard window behavior)
- Check if dialog is created with correct window manager hints

#### B.3: Close Button
- Add "Close" or "OK" button at bottom of dialog
- Button should close the dialog

#### B.4: Copy to Clipboard
- Add "Copy to Clipboard" button
- Copies full error text for easy capture/sharing

#### B.5: Write to Log File
- Write import results (including errors) to a log file
- Location: `logs/import_YYYY-MM-DD_HHMMSS.log` or similar
- Include timestamp, file imported, full summary, all error details
- Show log file path in dialog so user knows where to find it

### UI Layout Recommendation
```
+------------------------------------------+
|  Import Results                      [X] |
+------------------------------------------+
| [Scrollable area - max 400px height]     |
|                                          |
| Import Summary                           |
| ============                             |
| ingredient: 12 skipped                   |
| product: 13 imported                     |
| ...                                      |
|                                          |
| Errors:                                  |
| - finished_good: brownie_box             |
|   (error details...)                     |
|                                          |
+------------------------------------------+
| Log saved to: logs/import_2025-12-16.log |
+------------------------------------------+
| [Copy to Clipboard]              [Close] |
+------------------------------------------+
```

## Files to Investigate

- `test_data/sample_data.json` — Check finished_goods field names
- `src/services/import_export_service.py` — Import logic for finished_goods
- `src/ui/dialogs/` — Error/results dialog implementation
- Look for where import results are displayed

## Testing

### Part A
1. Fix data/service issue
2. Re-run import of sample_data.json
3. Verify finished_goods import successfully

### Part B
1. Trigger an import with errors (use invalid test data if needed)
2. Verify dialog is scrollable
3. Verify dialog is movable
4. Verify Close button works
5. Verify Copy to Clipboard copies full text
6. Verify log file is created with full details

## Deliverables

1. Fixed sample_data.json OR import service (whichever has the bug)
2. Improved error dialog with:
   - Scrollable content area
   - Movable window
   - Close button
   - Copy to Clipboard button
   - Log file output
3. All existing tests pass
