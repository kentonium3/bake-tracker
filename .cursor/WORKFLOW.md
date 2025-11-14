# Cursor Code Review & Repair Workflow

This document describes how to use Cursor IDE for code review and repair in the bake-tracker project.

## Quick Start

Cursor has been configured as the **Code Review and Repair Specialist** for this project.

### Primary Commands

1. **`/review-code [files]`** - Comprehensive code review
2. **`/fix-issues [description]`** - Repair bugs and quality issues
3. **`/quick-fix [files]`** - Auto-fix linting and formatting

## Typical Workflows

### Workflow 1: Pre-Commit Review

**Use Case:** You've made changes and want to review before committing.

```bash
# 1. Check for issues
dev lint
dev test

# 2. In Cursor, run code review
/review-code

# 3. Fix any critical or major issues found
/fix-issues

# 4. Quick cleanup
/quick-fix

# 5. Verify everything passes
dev lint
dev test

# 6. Commit
git add .
git commit -m "fix: [description of fixes]"
```

### Workflow 2: CI/CD Failure Response

**Use Case:** CI/CD pipeline failed due to linting or test errors.

```bash
# 1. Pull latest changes
git pull

# 2. Reproduce the failure locally
dev lint
dev test

# 3. In Cursor, fix the issues
/fix-issues

# 4. Verify fixes
dev lint
dev test

# 5. Commit and push
git add .
git commit -m "fix: resolve CI/CD failures"
git push
```

### Workflow 3: Code Quality Audit

**Use Case:** Periodic review to maintain code quality.

```bash
# 1. Review entire codebase or specific module
/review-code src/services/

# 2. Review generates a report with prioritized issues

# 3. Fix critical issues first
/fix-issues

# 4. Address major issues
/fix-issues

# 5. Clean up minor issues
/quick-fix

# 6. Document improvements
# Update CHANGELOG.md or create issue tickets for remaining work
```

### Workflow 4: Bug Investigation and Fix

**Use Case:** User reported a bug, need to find and fix it.

```bash
# 1. Reproduce the bug
dev run
# ... reproduce issue ...

# 2. Run tests to identify failures
dev test

# 3. Review the problematic area
/review-code src/[affected-module]/

# 4. Implement the fix
/fix-issues [bug description]

# 5. Add regression test (if not exists)
# Edit test file to add test case

# 6. Verify fix
dev test

# 7. Commit
git add .
git commit -m "fix: [bug description]"
```

### Workflow 5: Refactoring Review

**Use Case:** After refactoring, ensure quality is maintained.

```bash
# 1. Run comprehensive review on refactored code
/review-code src/[refactored-module]/

# 2. Check for any issues introduced
dev lint
dev test

# 3. Fix any issues found
/fix-issues

# 4. Ensure tests still pass
dev test

# 5. Commit refactoring
git add .
git commit -m "refactor: [description]"
```

## Review Checklist

When using `/review-code`, Cursor checks:

### Code Quality (PEP 8 Compliance)
- [ ] Line length ≤ 100 characters
- [ ] Proper spacing and formatting
- [ ] Type hints on all functions
- [ ] Google-style docstrings
- [ ] Proper naming conventions

### Architecture
- [ ] Single responsibility principle
- [ ] Proper layer separation (Models/Services/UI)
- [ ] No circular dependencies
- [ ] Database operations use SQLAlchemy properly

### Security
- [ ] Input validation
- [ ] No SQL injection vulnerabilities
- [ ] Safe file operations
- [ ] Data sanitization

### Performance
- [ ] Efficient database queries
- [ ] No N+1 query problems
- [ ] Proper resource management
- [ ] Algorithm efficiency

### Testing
- [ ] Test coverage for new code
- [ ] Tests are meaningful
- [ ] Edge cases covered

## Fix Priorities

Cursor categorizes issues by severity:

### Critical (Fix Immediately)
- Security vulnerabilities
- Data corruption risks
- Runtime crashes
- Test failures blocking deployment

### Major (Fix Soon)
- Significant code quality issues
- Performance problems
- Missing error handling
- Technical debt accumulation

### Minor (Fix When Convenient)
- Style inconsistencies
- Missing docstrings
- Minor optimizations
- Code simplification opportunities

## Integration with Development Workflow

### With Claude Code
- **Claude Code**: Feature development and implementation
- **Cursor**: Code review and quality assurance

Example workflow:
1. Use Claude Code to implement feature
2. Use Cursor to review and fix quality issues
3. Commit when both are satisfied

### With Spec Kitty
- Follow spec-kitty workflow for feature planning
- Use Cursor during "implement" and "review" phases
- Run `/review-code` before marking tasks complete

### With Git
```bash
# Feature branch workflow
git checkout -b feature/new-feature

# ... implement feature with Claude Code ...

# Review with Cursor
/review-code

# Fix issues
/fix-issues
/quick-fix

# Verify
dev lint
dev test

# Commit and push
git add .
git commit -m "feat: new feature"
git push origin feature/new-feature
```

## Tips for Effective Reviews

1. **Review early and often**: Don't wait until code is "done"
2. **Fix critical issues first**: Security and correctness before style
3. **Run tests after every fix**: Ensure nothing breaks
4. **Use quick-fix for bulk cleanup**: Save time on formatting issues
5. **Document complex fixes**: Add comments explaining non-obvious solutions
6. **Commit fixes separately**: Don't mix feature code with quality fixes

## Common Commands Reference

```bash
# Development commands
dev test          # Run pytest
dev lint          # Run flake8, black, mypy
dev format        # Auto-format with black
dev run           # Run the application

# Cursor commands
/review-code [files]     # Comprehensive review
/fix-issues [desc]       # Fix bugs and issues
/quick-fix [files]       # Auto-fix formatting

# Spec-kitty commands (when needed)
/spec-kitty.implement    # Implement a task
/spec-kitty.review       # Review implementation
/spec-kitty.tasks        # View task status
```

## Troubleshooting

### "No issues found but tests failing"
- Logic error, not a style issue
- Use `/fix-issues` with test output
- May need manual debugging

### "Too many issues reported"
- Start with `/quick-fix` to auto-fix formatting
- Then address remaining issues with `/fix-issues`
- Tackle by severity: Critical → Major → Minor

### "Fixes break other code"
- Run full test suite after each fix
- Review related code for dependencies
- May need broader refactoring (consult Claude Code)

## Getting Help

- **Project docs**: See `CONTRIBUTING.md` and `README.md`
- **Agent instructions**: See `ai-agents/cursor-instructions.md`
- **Spec Kitty docs**: See `.kittify/AGENTS.md`
- **Code standards**: See `pyproject.toml` for linting rules
