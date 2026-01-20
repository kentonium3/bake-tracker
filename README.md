# Bake Tracker

A desktop application for managing event-based food production: inventory, recipes, finished goods, and gift package planning.

## Overview

Bake Tracker helps you plan and execute large-scale baking operations by tracking:

- **Ingredients & Products** - Three-tier ingredient taxonomy with brand-specific products
- **Materials** - Non-food items (boxes, ribbons, labels) with separate inventory tracking
- **Recipes** - Nested recipe support with automatic cost calculation via FIFO
- **Finished Goods** - Yield tracking, bundles, and gift packages
- **Event Planning** - Recipients, package assignments, and production targets
- **Inventory** - FIFO lot tracking with purchase-linked cost snapshots
- **Import/Export** - JSON-based backup, catalog seeding, and AI-assisted data entry

**Dual Purpose:** This application serves as both a practical tool for real users AND a workflow validation platform for future AI-assisted SaaS evolution. See [Architecture](docs/design/architecture.md) for the vision and design principles.

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.10+ | Type hints, modern syntax |
| **UI** | CustomTkinter | Cross-platform desktop widgets |
| **Database** | SQLite (WAL mode) | Portable single-file storage |
| **ORM** | SQLAlchemy 2.x | Type-safe database abstraction |
| **Testing** | pytest | 2,500+ unit and integration tests |

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/kentonium3/bake-tracker.git
cd bake-tracker

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### Running Tests

```bash
./run-tests.sh                    # All tests
./run-tests.sh -v                 # Verbose
./run-tests.sh -k "test_name"     # Specific test
./run-tests.sh --cov=src          # With coverage
```

## Project Structure

```
bake-tracker/
├── src/
│   ├── models/           # 42 SQLAlchemy model classes
│   ├── services/         # 45 business logic modules
│   ├── ui/               # CustomTkinter components
│   ├── utils/            # Helpers, unit conversion, CLI
│   └── tests/            # pytest test suite (2,500+ tests)
├── docs/
│   ├── design/           # Architecture, schemas, design specs
│   ├── func-spec/        # Feature specifications (F0xx documents)
│   ├── requirements/     # Requirements documents by domain
│   ├── code-reviews/     # Feature code review artifacts
│   └── archive/          # Historical bugs, tech debt
├── kitty-specs/          # Active feature workspaces (spec-kitty)
├── .kittify/             # Spec-kitty templates and constitution
├── data/                 # SQLite database (created at runtime)
└── requirements.txt      # Python dependencies
```

## Documentation

### Architecture & Design

- [Architecture](docs/design/architecture.md) - System overview, design principles, vision
- [Schema Design](docs/design/schema_v0.6_design.md) - Entity relationships
- [Import/Export Spec](docs/design/spec_import_export.md) - JSON format specification (v4.2)

### Requirements (by Domain)

- [Ingredients](docs/requirements/req_ingredients.md) - Three-tier taxonomy, products
- [Materials](docs/requirements/req_materials.md) - Non-food inventory
- [Recipes](docs/requirements/req_recipes.md) - Nested recipes, snapshots
- [Inventory](docs/requirements/req_inventory.md) - FIFO tracking
- [Planning](docs/requirements/req_planning.md) - Events, packages, recipients

### Guides

- [User Guide](docs/user_guide.md) - Application usage
- [Development Workflow](docs/development_workflow.md) - Contribution process
- [Feature Roadmap](docs/feature_roadmap.md) - Planned features

## Development Phases

| Phase | Status | Focus |
|-------|--------|-------|
| **Phase 1-2** | Complete | Foundation, learning app development basics |
| **Phase 3** | **In Progress** | Locally functional app with professional data modeling |
| **Phase 4** | Pending | AI-assisted interaction demonstrator (voice/chat input) |
| **Phase 5** | Planned | Web app port, cloud hosting, multi-user (15-20) |
| **Phase 6** | Planned | Web platform demonstrator, AI-assisted workflows |
| **Phase 7** | Aspirational | Commercial prototype, 10K+ users, reskinnable |

See [App Vision](docs/design/app_vision_note.md) for detailed phase descriptions.

## Feature Maturity

| Domain | Feature | Status |
|--------|---------|--------|
| **Catalog** | Ingredient/Material Hierarchy | Mature |
| **Catalog** | Products & MaterialProducts | Mature |
| **Catalog** | Recipes (nested, snapshots) | Mature |
| **Inventory** | FIFO Tracking (food & materials) | Mature |
| **Import/Export** | JSON backup, catalog import | Mature |
| **Production** | ProductionRuns, cost snapshots | Functional |
| **Assembly** | Finished Goods, Bundles | Partial |
| **Planning** | Events, Recipients, Packages | Partial |
| **Analytics** | Reporting, Dashboards | Planned |

## Development Workflow

This project uses [spec-kitty](https://github.com/your-org/spec-kitty) for documentation-first feature development:

1. `/spec-kitty.specify` - Create feature specification
2. `/spec-kitty.plan` - Research and design
3. `/spec-kitty.tasks` - Generate work packages
4. `/spec-kitty.implement` - TDD implementation
5. `/spec-kitty.review` - Code review
6. `/spec-kitty.merge` - Merge and cleanup

Features are developed in isolated git worktrees with multi-agent orchestration support (Claude Code lead, Gemini CLI teammate).

## License

MIT License - See LICENSE file for details.

## Contributing

This project is developed with AI assistance (Claude Code, Gemini CLI). Issues and suggestions welcome!

## Support

For questions or issues, please create an issue on [GitHub](https://github.com/kentonium3/bake-tracker/issues).
