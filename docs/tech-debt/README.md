# Tech Debt Log

This directory tracks technical debt items identified during development. Each item is documented in its own file with a unique ID.

## Naming Convention

Files follow the pattern: `TD###_short_description.md`

## Priority Levels

- **Critical**: Blocks feature development or causes data integrity issues
- **High**: Significant maintenance burden or performance impact
- **Medium**: Code quality issue that complicates future work
- **Low**: Minor cleanup, nice-to-have improvements

## Effort Levels

- **Large**: Multiple days, architectural changes
- **Medium**: Half-day to full day
- **Small**: A few hours or less

---

## Open Items

| ID | Description | Priority | Effort | Area |
|----|-------------|----------|--------|------|
| [TD001](TD001_consolidate_slug_utils.md) | Consolidate duplicate slug generation functions | Low | Small | src/utils/slug_utils.py |

## Resolved Items

(None yet)
