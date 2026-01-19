# Agent Compliance Issue: `/spec-kitty.tasks` created legacy lane subdirectories despite explicit instructions

## Summary

When `/spec-kitty.tasks` was executed on feature 049-import-export-phase1, the AI agent created legacy lane subdirectories (`planned/`, `doing/`, `done/`) despite the skill template explicitly instructing NOT to create them.

**This is NOT a spec-kitty bug.** The v0.10.12 skill template clearly states the correct behavior. The AI agent failed to follow the instructions.

## Environment

- spec-kitty version: v0.10.12
- Project: bake-tracker feature 049-import-export-phase1
- Date observed: 2026-01-12

## Template Instructions (Correct)

The `/spec-kitty.tasks` skill template at `/Users/kentgale/Library/Python/3.14/lib/python/site-packages/specify_cli/missions/software-dev/command-templates/tasks.md` explicitly states (lines 81-97):

```markdown
- **CRITICAL PATH RULE**: All work package files MUST be created in a FLAT `FEATURE_DIR/tasks/` directory, NOT in subdirectories!
- Correct structure: `FEATURE_DIR/tasks/WPxx-slug.md` (flat, no subdirectories)
- WRONG (do not create): `FEATURE_DIR/tasks/planned/`, `FEATURE_DIR/tasks/doing/`, or ANY lane subdirectories
- WRONG (do not create): `/tasks/`, `tasks/`, or any path not under FEATURE_DIR
...
**IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location.
```

## What Happened

Despite these clear instructions, the AI agent created:

```
kitty-specs/049-import-export-phase1/tasks/
├── README.md
├── .gitkeep
├── doing/          (empty - WRONG)
├── done/           (empty - WRONG)
└── planned/        (WRONG)
    └── WP01-WP09 files...
```

Instead of the correct flat structure:

```
kitty-specs/049-import-export-phase1/tasks/
├── README.md
├── WP01-complete-system-backup.md
├── WP02-materials-catalog-import.md
└── ... etc
```

## Root Cause

Unknown. Possible causes:
1. Agent may have had cached/stale instructions from an older spec-kitty version
2. Agent may have inferred structure from existing projects that use the legacy format
3. Agent may have prioritized the README.md content (which describes both formats) over the skill instructions

## Impact

- The local `.kittify/scripts/tasks/tasks_cli.py` correctly detects this as "legacy format" and warns about it
- The `spec-kitty agent tasks` commands will work but with legacy format handling
- Manual workaround: Run `spec-kitty upgrade` to migrate to flat structure

## Recommendation

Consider adding even stronger guardrails in the skill template, or having the skill invoke a spec-kitty CLI command that validates/creates the correct structure rather than relying on the AI to create directories manually.

## Files Involved

- Skill template: `/Users/kentgale/Library/Python/3.14/lib/python/site-packages/specify_cli/missions/software-dev/command-templates/tasks.md`
- Local tasks CLI: `.kittify/scripts/tasks/tasks_cli.py` (has legacy detection)
- Generated (wrong) structure: `kitty-specs/049-import-export-phase1/tasks/planned/`
