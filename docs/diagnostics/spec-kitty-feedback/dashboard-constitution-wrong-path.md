# Dashboard: Constitution shows "Not created" in Available Artifacts despite existing

**Date**: 2026-01-30
**Spec-Kitty Version**: 0.13.9
**Reporter**: Kent Gale (via Claude Code)
**Severity**: Low (cosmetic/UX issue)
**Status**: Fixed locally, pending upstream

## Summary
The dashboard Overview page's "Available Artifacts" section always shows "Constitution: Not created" even when a constitution file exists and is correctly displayed when clicking the Constitution link in the sidebar.

## Expected Behavior
When `.kittify/memory/constitution.md` exists, the Available Artifacts section should show "Constitution: Available".

## Actual Behavior
- Available Artifacts section shows "Constitution: Not created"
- Sidebar Constitution link works correctly (not disabled)
- Clicking Constitution in sidebar correctly displays the constitution content

## Root Cause
In `specify_cli/dashboard/scanner.py`, the `get_feature_artifacts()` function checks for constitution at the **feature level** (`kitty-specs/<feature>/constitution.md`) instead of the **project level** (`.kittify/memory/constitution.md`).

```python
# Bug: line 162 in original scanner.py
def get_feature_artifacts(feature_dir: Path) -> Dict[str, Dict[str, any]]:
    return {
        "constitution": _get_artifact_info(feature_dir / "constitution.md"),  # WRONG PATH
        ...
    }
```

The constitution is a project-level artifact, not a feature-level artifact. The sidebar works because it:
1. Never disables the constitution link (hardcoded exception)
2. Fetches directly from `/api/constitution` which correctly reads from `.kittify/memory/constitution.md`

## Fix
Modify `get_feature_artifacts()` to accept an optional `project_dir` parameter and check for constitution at the project level:

```python
def get_feature_artifacts(feature_dir: Path, project_dir: Optional[Path] = None) -> Dict[str, Dict[str, any]]:
    # Constitution is a project-level artifact, not feature-level
    if project_dir is not None:
        constitution_path = project_dir / ".kittify" / "memory" / "constitution.md"
    else:
        # Fallback for backwards compatibility
        constitution_path = feature_dir / "constitution.md"

    return {
        "constitution": _get_artifact_info(constitution_path),
        ...
    }
```

Update the call site in `scan_all_features()`:
```python
artifacts = get_feature_artifacts(feature_dir, project_dir=project_dir)
```

## Patched File
See `patches/scanner.py` in this directory for the complete patched file.

## Verification
After applying the fix and restarting the dashboard:
```bash
curl -s http://127.0.0.1:9237/api/features | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Constitution exists:', data['features'][0]['artifacts']['constitution']['exists'])
"
# Output: Constitution exists: True
```

## Files Affected
- `specify_cli/dashboard/scanner.py`

## Discovered
2026-01-30 by Kent Gale with Claude Code assistance
