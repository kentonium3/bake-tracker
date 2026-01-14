# Key Changes Required

## specify.md

### Line 74 (was)
```markdown
Store the final mission selection to pass to the script via `--mission "<selected-mission>"`.
```

### Line 74 (fixed)
```markdown
Store the final mission selection internally for use when creating the meta.json file.
```

---

### Line 82 (was)
```markdown
- You will pass this confirmed title to the feature creation script via `--feature-name "<Friendly Title>"` so downstream tooling surfaces it consistently.
```

### Line 82 (fixed)
```markdown
- You will convert this confirmed title to a kebab-case slug for the feature creation command.
```

---

## accept.md

### Lines 29-33 (was)
```markdown
1. Compile the acceptance options into an argument list:
   - Always include `--actor "__AGENT__"`.
   - Append `--feature "<slug>"` when the user supplied a slug.
   - Append `--mode <mode>` (`pr`, `local`, or `checklist`).
   - Append `--test "<command>"` for each validation command provided.
```

### Lines 29-33 (fixed)
```markdown
1. Compile the acceptance options into an argument list:
   - Append `--feature "<slug>"` when the user supplied a slug (otherwise auto-detected).
   - Append `--mode <mode>` (`auto`, `pr`, `local`, or `checklist`).
   - Append `--lenient` if user requested lenient validation.
   - Append `--no-commit` if user requested report-only mode.
```

---

## Template Expansion Logic (spec-kitty codebase)

The `{SCRIPT}` placeholder must expand to include `feature` subcommand:

| Current (broken) | Fixed |
|-----------------|-------|
| `spec-kitty agent check-prerequisites` | `spec-kitty agent feature check-prerequisites` |
| `spec-kitty agent setup-plan` | `spec-kitty agent feature setup-plan` |
| `spec-kitty agent accept` | `spec-kitty agent feature accept` |

---

## CLI Help Text (spec-kitty codebase)

Update example strings in decorators:

| Current (broken) | Fixed |
|-----------------|-------|
| `spec-kitty agent check-prerequisites --json` | `spec-kitty agent feature check-prerequisites --json` |
| `spec-kitty agent setup-plan --json` | `spec-kitty agent feature setup-plan --json` |
