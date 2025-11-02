# Contributing to Seasonal Baking Tracker

Thank you for your interest in contributing to the Seasonal Baking Tracker project!

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git for Windows
- VS Code (recommended) or PyCharm

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kentonium3/bake-tracker.git
   cd bake-tracker
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
   - Windows (CMD): `venv\Scripts\activate.bat`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   Or use the convenience script:
   - Windows: `dev install`
   - Linux/Mac: `make install`

### Development Tools

The project uses several tools to maintain code quality:

- **Black** - Code formatter (max line length: 100)
- **Flake8** - Linter
- **MyPy** - Type checker
- **Pytest** - Testing framework

### Running Commands

**Windows:**
```bash
dev test         # Run tests
dev test-cov     # Run tests with coverage
dev lint         # Run linters
dev format       # Format code
dev run          # Run application
dev clean        # Clean build artifacts
```

**Linux/Mac:**
```bash
make test        # Run tests
make test-cov    # Run tests with coverage
make lint        # Run linters
make format      # Format code
make run         # Run application
make clean       # Clean build artifacts
```

### Code Standards

#### PEP 8 Style Guide
- Follow PEP 8 conventions
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)

#### Docstrings
All public classes and methods should have docstrings:

```python
def calculate_recipe_cost(recipe_id: int) -> float:
    """
    Calculate the total cost of a recipe based on ingredient prices.

    Args:
        recipe_id: The unique identifier of the recipe

    Returns:
        Total cost in dollars

    Raises:
        ValueError: If recipe_id is not found
    """
    pass
```

#### Type Hints
Use type hints where beneficial:

```python
def get_ingredient(ingredient_id: int) -> Optional[Ingredient]:
    """Retrieve an ingredient by ID."""
    pass
```

#### Naming Conventions
- Classes: `PascalCase` (e.g., `IngredientService`)
- Functions/methods: `snake_case` (e.g., `calculate_cost`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_INGREDIENTS`)
- Private methods: `_leading_underscore` (e.g., `_validate_input`)

### Testing

#### Writing Tests
- Place tests in `src/tests/`
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names

Example:
```python
def test_ingredient_conversion_factor_calculation():
    """Test that conversion factor correctly converts purchase to recipe units."""
    ingredient = Ingredient(
        name="Flour",
        purchase_unit="bag",
        recipe_unit="cup",
        conversion_factor=200.0
    )
    assert ingredient.convert_to_recipe_units(1.0) == 200.0
```

#### Running Tests
```bash
# Run all tests
dev test  # or: make test

# Run specific test file
venv/Scripts/pytest src/tests/test_models.py

# Run with coverage
dev test-cov  # or: make test-cov
```

### Git Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Format and lint**
   ```bash
   dev format
   dev lint
   ```

4. **Run tests**
   ```bash
   dev test
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add feature description"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting, etc.)
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

6. **Push to GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Describe your changes
   - Link any related issues

### Project Structure

```
src/
├── models/          # SQLAlchemy models
├── services/        # Business logic layer
├── ui/              # CustomTkinter UI components
│   └── widgets/     # Reusable UI widgets
├── utils/           # Utility functions and helpers
└── tests/           # Test suite
```

### Database Schema Changes

If you need to modify the database schema:

1. Update the model in `src/models/`
2. Update `docs/SCHEMA.md`
3. Consider backward compatibility
4. Add migration notes to CHANGELOG.md
5. Test with existing database files

### Documentation

- Update README.md if adding new features
- Update USER_GUIDE.md for user-facing changes
- Update ARCHITECTURE.md for architectural changes
- Update CHANGELOG.md with all changes
- Keep inline comments for complex logic

### VS Code Integration

The project includes VS Code settings in `.vscode/`:
- `settings.json` - Editor and tool configuration
- `launch.json` - Debug configurations
- `extensions.json` - Recommended extensions

Recommended extensions will be suggested automatically.

### Getting Help

- Review the [Requirements Document](REQUIREMENTS.md) for project goals
- Check [Architecture Document](docs/ARCHITECTURE.md) for design decisions
- Read the [User Guide](docs/USER_GUIDE.md) to understand features
- Open an issue on GitHub for questions or bugs

### Code Review

All contributions will be reviewed for:
- Code quality and style adherence
- Test coverage (aim for >70% in services)
- Documentation completeness
- Alignment with project requirements

## Thank You!

Your contributions help make this project better for everyone!
