# Seasonal Baking Tracker

A desktop application for managing holiday baking inventory, recipes, and gift package planning.

## Overview

The Seasonal Baking Tracker helps you plan and execute large-scale holiday baking operations by tracking:
- Ingredient inventory with flexible unit conversions
- Recipes with automatic cost calculation
- Gift packages and bundles
- Recipients and delivery tracking
- Shopping lists based on planned vs available inventory
- Production tracking and reporting

## Technology Stack

- **Python 3.10+**
- **CustomTkinter** - Modern UI framework
- **SQLite** - Local database
- **SQLAlchemy** - ORM
- **Pandas** - Data manipulation and CSV export

## Quick Start

### Installation

1. **Install Python 3.10 or higher** from [python.org](https://python.org)

2. **Clone the repository**
   ```bash
   git clone https://github.com/kentonium3/bake-tracker.git
   cd bake-tracker
   ```

3. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python src/main.py
   ```

## Project Structure

```
bake-tracker/
├── src/              # Application source code
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   ├── ui/           # User interface
│   ├── utils/        # Utilities and helpers
│   └── tests/        # Test suite
├── data/             # SQLite database (created at runtime)
├── docs/             # Documentation
└── requirements.txt  # Python dependencies
```

## Documentation

- [Requirements Document](REQUIREMENTS.md) - Full project requirements and specifications
- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [User Guide](docs/USER_GUIDE.md) - How to use the application
- [Database Schema](docs/SCHEMA.md) - Database structure and relationships
- [Changelog](CHANGELOG.md) - Version history

## Features

### Phase 1: Foundation (MVP)
- Ingredient inventory management with unit conversions
- Recipe creation and management
- Basic user interface

### Phase 2: Core Planning
- Bundle and package creation
- Event planning with recipient assignments
- Shopping list generation

### Phase 3: Production Tracking
- Production recording
- Package assembly and delivery tracking
- Planned vs actual reporting

### Phase 4: Polish & Reporting
- Advanced analytics
- CSV export
- UI enhancements

## Development Status

**Current Phase:** Initial Setup

See [CHANGELOG.md](CHANGELOG.md) for detailed progress updates.

## License

MIT License - See LICENSE file for details

## Contributing

This is a personal project developed with assistance from Claude Code. Issues and suggestions are welcome!

## Support

For questions or issues, please create an issue on GitHub.
