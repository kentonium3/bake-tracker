# Data Management Workflow for Testing & Development

**Document Purpose:** Guide for managing test data during iterative development and testing cycles

**Last Updated:** 2025-11-05
**Status:** Active reference for testing phase

---

## Overview

During the testing phase, you'll be creating real data on the test laptop that needs to be preserved across application updates. This document outlines the best workflows for different scenarios.

---

## Recommended Workflow (Simple - No Schema Changes)

**Use this workflow when:** Making bug fixes, UI improvements, or feature additions that don't change the database structure.

### Step-by-Step Process

**1. Receive Feedback from Testing**
- Note bugs, feature requests, or issues

**2. Make Code Changes on Dev Machine**
- Edit source code
- Test changes locally (optional)
- Ensure no database schema changes

**3. Build Updated Package**
```bash
cd C:\Users\Kent\Vaults-repos\bake-tracker
pyinstaller BakeTracker.spec --clean
```

**4. Transfer Updated App to Test Laptop**
- Option A: Copy entire `dist/BakeTracker/` folder
- Option B: Create new ZIP and extract

**5. Replace Existing App (Database Unaffected)**
- Delete old BakeTracker folder
- Copy in new BakeTracker folder
- Launch BakeTracker.exe
- **Database remains intact** at `C:\Users\[Username]\Documents\BakeTracker\`

### Why This Works

- Database is stored separately from application
- No schema changes = database compatible with new version
- Simple file replacement
- Zero risk of data loss

### When Schema Hasn't Changed

You can tell there are no schema changes if you:
- Only modified Python code in `src/services/` or `src/ui/`
- Didn't change any model files in `src/models/`
- Didn't add/remove database columns or tables

---

## Alternative Workflow (Export/Import - Schema Changes)

**Use this workflow when:** Adding database columns, changing data types, modifying relationships, or when database structure changes.

### Step-by-Step Process

**1. Export Data from Test Laptop**

Transfer the database file back to dev machine:
```bash
# On test laptop, copy:
C:\Users\[Username]\Documents\BakeTracker\bake_tracker.db

# To USB drive or network location
```

Then on dev machine:
```bash
cd C:\Users\Kent\Vaults-repos\bake-tracker

# Copy database to data/ folder
copy Z:\bake_tracker.db data\bake_tracker.db

# Export to JSON (current limitation: only ingredients, recipes, FGs, bundles)
venv/Scripts/python.exe src/utils/import_export_cli.py export test_data_backup.json
```

**Current Export Limitation:** CLI only exports ingredients, recipes, finished goods, and bundles. **Packages, recipients, and events are NOT exported.**

**2. Make Code Changes (Including Schema Changes)**
- Edit model files
- Add migrations if needed
- Create new database with updated schema

**3. Import Data Back**
```bash
# Delete old database
del data\bake_tracker.db

# Application will create new schema on next run
venv/Scripts/python.exe -m src.main

# Close app, then import data
venv/Scripts/python.exe src/utils/import_export_cli.py import test_data_backup.json
```

**4. Build and Deploy Updated App**
- Build with PyInstaller
- Transfer to test laptop
- Copy updated database back to Documents\BakeTracker\

---

## Database File Copy Workflow (Backup/Restore)

**Use this workflow when:** You just want to backup/restore the entire database without export/import.

### Backup from Test Laptop

```bash
# Source location on test laptop
C:\Users\[Username]\Documents\BakeTracker\bake_tracker.db

# Copy to:
- USB drive
- Network share (\\SERVER\Share\backups\)
- Cloud storage (OneDrive, Google Drive, Dropbox)
- Email to yourself (small file, <1 MB typically)
```

### Restore to Test Laptop

```bash
# Copy bake_tracker.db back to:
C:\Users\[Username]\Documents\BakeTracker\bake_tracker.db

# Overwrite existing file
```

### Advantages
- Preserves 100% of data including IDs, relationships, history
- Fast and simple
- No risk of export/import bugs
- Works across application versions (if no schema changes)

### Disadvantages
- Binary format (not human-readable)
- Doesn't work if schema changes significantly
- All-or-nothing (can't selectively import data)

---

## Current Import/Export Capabilities

### CLI Tools Available

**What Works (COMPLETE AS OF 2025-11-05):**
```bash
# Export all (7 types - ingredients, recipes, finished goods, bundles, packages, recipients, events)
venv/Scripts/python.exe src/utils/import_export_cli.py export all_data.json

# Individual exports
venv/Scripts/python.exe src/utils/import_export_cli.py export-ingredients ingredients.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-recipes recipes.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-finished-goods finished_goods.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-bundles bundles.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-packages packages.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-recipients recipients.json
venv/Scripts/python.exe src/utils/import_export_cli.py export-events events.json

# Individual imports (same pattern)
venv/Scripts/python.exe src/utils/import_export_cli.py import all_data.json
venv/Scripts/python.exe src/utils/import_export_cli.py import-ingredients ingredients.json
venv/Scripts/python.exe src/utils/import_export_cli.py import-packages packages.json
venv/Scripts/python.exe src/utils/import_export_cli.py import-recipients recipients.json
venv/Scripts/python.exe src/utils/import_export_cli.py import-events events.json
```

**Features:**
- ✅ Complete export/import for all 7 data types
- ✅ Proper dependency ordering (ingredients → recipes → finished goods → bundles → packages, recipients, events)
- ✅ Event assignments included with events export/import
- ✅ Duplicate detection and skipping
- ✅ Detailed import results with success/skip/fail counts

**What's Still Missing:**
- ❌ UI import/export (must use CLI from dev machine)
- ❌ Progress indicators for long operations

**Note:** Database file copy method is still simpler for non-schema-changing updates, but export/import now preserves 100% of data.

---

## Recommended Strategy for Current Testing Phase

### Initial Approach (Recommended)

**Use simple file copy method:**

1. **Test on laptop** → Create real data
2. **Get feedback** → Note bugs/issues
3. **Copy DB to dev machine** → Backup via USB/network
4. **Make fixes** → Code changes (no schema changes)
5. **Build updated app** → PyInstaller
6. **Deploy to laptop** → Replace app folder
7. **Copy DB back** → Restore from backup
8. **Continue testing** → Data preserved

### If Schema Changes Needed (Advanced)

If you absolutely need to change the database schema:

**Option A: Start Fresh**
- Accept data loss
- Rebuild test data manually
- Fastest for minor schema changes

**Option B: Manual Migration**
- Export what you can (ingredients, recipes, FGs, bundles)
- Manually note packages, recipients, events
- Create new database
- Import exported data
- Manually recreate packages, recipients, events

**Option C: Add Missing Export/Import (Future)**
- Expand import_export_service.py
- Add packages, recipients, events support
- Use enhanced export/import

---

## Roadmap: Planned Improvements

### Short-Term (Phase 4)

**Complete Export/Import CLI:**
- [ ] Add packages export/import
- [ ] Add recipients export/import
- [ ] Add events export/import
- [ ] Add event assignments export/import
- [ ] Test complete backup/restore cycle

**UI Import/Export (HIGH PRIORITY):**
- [ ] Add "File" menu to main window
- [ ] Add "Export All Data..." menu item with file dialog
- [ ] Add "Import All Data..." menu item with file dialog
- [ ] Add progress indicators for long operations
- [ ] Add confirmation dialogs with import statistics

**Database Backup Helper:**
- [ ] "Backup Database..." button (copies .db file with timestamp)
- [ ] "Restore Database..." button (file picker)
- [ ] Auto-backup before imports (safety)

### Long-Term (Post-Testing)

**Database Version Management:**
- [ ] Add schema_version table to database
- [ ] Track schema changes in migrations/
- [ ] Auto-detect version mismatches
- [ ] Run migrations automatically on app start
- [ ] Backup before migration (safety)

**Smart Upgrade System:**
- [ ] Detect old database version
- [ ] Prompt user: "Database needs upgrade"
- [ ] Auto-backup before upgrade
- [ ] Apply migrations
- [ ] Verify upgrade success
- [ ] Rollback on failure

---

## Troubleshooting

### Problem: Database Locked

**Error:** "database is locked" or "unable to open database file"

**Cause:** BakeTracker.exe is running

**Solution:**
1. Close BakeTracker completely (check Task Manager)
2. Wait 5 seconds
3. Try operation again

### Problem: Import Fails with "Duplicate Key"

**Error:** "duplicate key value violates unique constraint"

**Cause:** Data already exists in database

**Solution:**
- Use `--skip-duplicates` flag (if implemented)
- Or delete database and import into clean database

### Problem: Database File Not Found

**Error:** "No such file or directory: bake_tracker.db"

**Cause:** Database not created yet

**Solution:**
- Launch BakeTracker.exe once to create database
- Close app
- Then copy your backup database file

### Problem: Data Loss After Copying Database

**Symptom:** Old data reappears after copying database back

**Cause:** SQLite WAL files not copied

**Solution:** Copy all three files:
- bake_tracker.db
- bake_tracker.db-shm (if exists)
- bake_tracker.db-wal (if exists)

---

## File Locations Reference

### Development Machine

```
C:\Users\Kent\Vaults-repos\bake-tracker\
├── src/                              # Source code
├── data/                             # Dev database location
│   └── bake_tracker.db             # Dev database
├── dist/                             # Built application
│   └── BakeTracker/
│       └── BakeTracker.exe
├── venv/                             # Python virtual environment
├── BakeTracker.spec                  # PyInstaller config
└── examples/                         # Example export files
    └── complete_export.json
```

### Test Laptop

```
C:\Program Files\BakeTracker\         # Application location (extracted ZIP)
├── BakeTracker.exe                   # Main executable
└── _internal/                        # Dependencies

C:\Users\[Username]\Documents\BakeTracker\  # Data location
├── bake_tracker.db                 # Live database
├── bake_tracker.db-shm             # SQLite shared memory
└── bake_tracker.db-wal             # SQLite write-ahead log
```

---

## Example: Complete Testing Iteration

**Scenario:** Fix a bug in recipe cost calculation

**Day 1 - Testing:**
1. User creates test data on laptop (ingredients, recipes, events, assignments)
2. User discovers bug: recipe costs not updating correctly
3. User reports bug to developer

**Day 2 - Development:**
1. Developer receives bug report
2. Developer copies database from laptop to dev machine (backup)
   ```bash
   # On laptop, copy to USB:
   copy C:\Users\Wife\Documents\BakeTracker\bake_tracker.db F:\backup\

   # On dev machine:
   copy F:\backup\bake_tracker.db C:\Users\Kent\Vaults-repos\bake-tracker\data\
   ```

3. Developer fixes bug in `src/services/recipe_service.py`
4. Developer tests fix locally with real data
5. Developer builds updated package:
   ```bash
   cd C:\Users\Kent\Vaults-repos\bake-tracker
   pyinstaller BakeTracker.spec --clean
   ```

6. Developer creates new ZIP:
   ```bash
   # Copy updated app to USB
   xcopy /E /I dist\BakeTracker F:\BakeTracker_v0.3.1\
   copy TESTING_GUIDE.txt F:\

   # Also copy database back (if changes made during testing)
   copy data\bake_tracker.db F:\backup\
   ```

**Day 3 - Deployment:**
1. User copies USB files to laptop
2. User deletes old BakeTracker folder
3. User extracts new BakeTracker folder
4. User copies database back:
   ```bash
   copy F:\backup\bake_tracker.db C:\Users\Wife\Documents\BakeTracker\
   ```
5. User launches BakeTracker.exe
6. User verifies bug is fixed
7. User continues testing with preserved data

---

## Best Practices

**DO:**
- ✅ Backup database before major changes
- ✅ Keep exported JSON files as snapshots
- ✅ Test on clean database occasionally (fresh start)
- ✅ Document what data you created (for recreation if needed)
- ✅ Use descriptive names for backups (e.g., `bake_tracker_2025-11-05.db`)

**DON'T:**
- ❌ Edit database file directly (use app or CLI tools)
- ❌ Copy database while app is running (data corruption risk)
- ❌ Assume backwards compatibility if schema changes
- ❌ Delete backups until testing is complete
- ❌ Mix databases from different schema versions

---

## Summary: Quick Decision Guide

**Choose Database File Copy when:**
- No schema changes
- Want to preserve 100% of data
- Simple backup/restore needed
- Fast iteration required

**Choose Export/Import when:**
- Schema changes required
- Need human-readable backup (JSON)
- Want to selectively import data
- Sharing test data with others

**Choose Fresh Start when:**
- Schema changed significantly
- Test data is quick to recreate
- Want to test "new user" experience
- Previous data no longer relevant

---

**Document Status:** Active reference for testing phase
**Next Action:** Use simple database file copy method until schema changes are needed

