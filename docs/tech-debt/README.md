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
| [TD-008](<./TD-008_materials_composition_layering_and_quantity_validation.md>) | Materials composition layering and quantity validation | Medium | Medium | Materials system |
| [TD-010](<./TD-010_purchase_service_boundary_violations.md>) | Purchase service boundary violations | Medium | Medium | src/services/purchase_service.py |
| [TD-011](<./TD-011_consolidate_slug_utils.md>) | Consolidate duplicate slug generation functions | Low | Small | src/utils/slug_utils.py |
| [TD-012](<./TD-012_import_slug_upgrade_via_previous_slug.md>) | Import does not upgrade slugs via previous_slug | High | Small | src/services/enhanced_import_service.py |

## Resolved Items

(None yet)
