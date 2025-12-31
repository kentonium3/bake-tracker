# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Feature 031: Ingredient Hierarchy Taxonomy**
  - Three-level ingredient hierarchy (root → mid-tier → leaf)
  - Tree widget for browsing ingredients by category
  - Leaf-only enforcement for recipes and products
  - Breadcrumb navigation showing ingredient path
  - Search with auto-expand for matching branches
  - Parent selection in ingredient create/edit forms
  - Migration tooling for categorizing existing ingredients
  - Export/import support for hierarchy fields (v3.6 format)
- `src/utils/datetime_utils.py` - UTC datetime helper (replaces deprecated `datetime.utcnow()`)

### Changed
- Ingredient model now includes `parent_ingredient_id` and `hierarchy_level` fields
- Export format version bumped to 3.6 (adds hierarchy fields)
- Replaced all `datetime.utcnow()` calls with `utc_now()` across codebase

### Deprecated
- `Ingredient.category` field (retained for rollback safety, use hierarchy instead)

---

## Previous

### Added
- Initial project structure
- Requirements document (v1.1)
- Basic documentation framework
- Git repository initialization

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

## Project Phases

### Phase 1: Foundation (MVP) - Planned
- Database schema and models
- Basic unit conversion system
- Ingredient CRUD with inventory management
- Simple recipe CRUD
- Basic CustomTkinter UI shell with navigation

### Phase 2: Core Planning - Planned
- Bundle and package creation
- Event creation and planning
- Recipient management
- Shopping list generation
- Basic reports

### Phase 3: Production Tracking - Planned
- Finished goods production recording
- Package assembly/delivery tracking
- Actual vs planned tracking
- Inventory depletion

### Phase 4: Polish & Reporting - Planned
- Advanced reports and analysis
- CSV export functionality
- Undo system refinement
- UI polish and usability improvements
- Comprehensive testing

### Phase 5: Nice-to-Haves - Future
- PDF export for reports
- Inventory snapshot comparison tool
- Recipe scaling
- Bulk import from CSV

---

## Version History

### [0.1.0] - 2025-11-02
- Initial repository setup
- Project structure created
- Documentation framework established
