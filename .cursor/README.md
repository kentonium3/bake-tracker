# Cursor IDE Configuration for Bake Tracker

This directory contains Cursor IDE configuration for the bake-tracker project.

## Role: Code Review & Repair Specialist

Cursor has been configured as the **Code Review and Repair Specialist** for this project. Its primary responsibilities are:

- **Code Reviews**: Analyze code quality, standards, security
- **Bug Fixes**: Identify and repair errors and issues
- **Quality Improvements**: Fix linting, add type hints, improve docs
- **Security Audits**: Find and fix vulnerabilities

## Quick Start

### Primary Commands (Review & Repair)

Use these commands in Cursor's command palette:

1. **`/review-code`** - Comprehensive code quality review
   - Checks PEP 8, type hints, docstrings, security
   - Generates detailed report with severity levels
   - Provides specific recommendations

2. **`/fix-issues`** - Repair bugs and quality problems
   - Fixes linting errors, type errors, runtime bugs
   - Handles test failures
   - Addresses security issues

3. **`/quick-fix`** - Auto-fix common formatting issues
   - Runs Black formatter
   - Removes unused imports
   - Adds obvious type hints and docstrings

### Workflow Example

```bash
# 1. Make code changes

# 2. Review your changes
/review-code

# 3. Fix any issues found
/fix-issues

# 4. Quick cleanup
/quick-fix

# 5. Verify everything works
dev lint
dev test

# 6. Commit
git commit -m "fix: description"
```

## Directory Structure

```
.cursor/
├── README.md                    # This file
├── WORKFLOW.md                  # Detailed workflow documentation
├── commands/                    # Cursor command definitions
│   ├── review-code.md          # Code review command
│   ├── fix-issues.md           # Issue repair command
│   ├── quick-fix.md            # Quick cleanup command
│   └── spec-kitty.*.md         # Spec-kitty integration commands
└── rules/
    └── specify-rules.mdc       # Auto-generated project context
```

## Files

### Commands (Primary)

- **`review-code.md`**: Comprehensive code review command
  - Checks quality, architecture, security, performance, testing
  - Generates structured reports with severity levels
  - Provides specific fixes with code examples

- **`fix-issues.md`**: Code repair command
  - Fixes linting errors, type errors, runtime bugs
  - Handles test failures and security issues
  - Includes verification steps

- **`quick-fix.md`**: Rapid cleanup command
  - Auto-formats with Black
  - Removes unused imports
  - Adds missing type hints and docstrings

### Commands (Secondary - Spec Kitty)

The following spec-kitty commands are available when needed:
- `spec-kitty.specify` - Create feature specifications
- `spec-kitty.plan` - Plan implementation
- `spec-kitty.tasks` - Manage tasks
- `spec-kitty.implement` - Implement features
- `spec-kitty.review` - Review implementations
- `spec-kitty.merge` - Merge features
- And more... (see `commands/` directory)

### Context Files

- **`rules/specify-rules.mdc`**: Auto-generated project context
  - Updated by `.kittify/scripts/powershell/update-agent-context.ps1`
  - Contains technology stack, project structure, recent changes
  - Referenced automatically by Cursor

## Usage Guidelines

### When to Use Each Command

**Use `/review-code` when:**
- Before committing code
- After implementing a feature
- Performing periodic quality audits
- CI/CD reports failures

**Use `/fix-issues` when:**
- Tests are failing
- Linting errors need fixing
- Bugs need repair
- Security issues identified

**Use `/quick-fix` when:**
- Need quick formatting cleanup
- Pre-commit hook failures
- CI/CD lint failures
- After rapid prototyping

### Integration with Other Agents

**With Claude Code:**
- Claude Code: Feature development and implementation
- Cursor: Code review and quality assurance

**Workflow:**
1. Claude Code implements the feature
2. Cursor reviews and fixes quality issues
3. Both agents satisfied → commit

**With Spec Kitty:**
- Follow spec-kitty workflow for planning
- Use Cursor during implement and review phases
- Run `/review-code` before marking tasks complete

## Code Standards

All code must meet these standards (enforced by reviews):

- **PEP 8**: Max line length 100 characters
- **Type Hints**: All function parameters and returns
- **Docstrings**: Google-style for all public API
- **Naming**: snake_case functions, PascalCase classes
- **Testing**: Pytest tests for all new code
- **Security**: Input validation, safe file operations

## Development Commands

```bash
# Run tests
dev test

# Run linters (flake8, black, mypy)
dev lint

# Auto-format code
dev format

# Run application
dev run
```

## Updating Context

To update Cursor's project context after plan changes:

```powershell
.\.kittify\scripts\powershell\update-agent-context.ps1 -AgentType cursor
```

This updates `.cursor/rules/specify-rules.mdc` with:
- Current technology stack
- Active features
- Recent changes
- Project structure

## Additional Documentation

- **Workflow Guide**: See `WORKFLOW.md` for detailed workflows
- **Agent Instructions**: See `../ai-agents/cursor-instructions.md`
- **Project Docs**: See `../CONTRIBUTING.md` and `../README.md`
- **Spec Kitty**: See `../.kittify/AGENTS.md`

## Support

For issues or questions:
- Check `WORKFLOW.md` for common scenarios
- Review `ai-agents/cursor-instructions.md` for detailed guidance
- Consult spec-kitty documentation in `.kittify/`

---

**Last Updated**: 2025-11-10
**Cursor Role**: Code Review & Repair Specialist
**Primary Commands**: `/review-code`, `/fix-issues`, `/quick-fix`
