"""
Database connection and session management for the Seasonal Baking Tracker.

This module provides:
- Database engine creation and configuration
- Session factory for database operations
- Database initialization (create tables)
- WAL mode configuration
- Foreign key enforcement
"""

from typing import Optional
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..utils.config import get_config
from ..models.base import Base
from ..utils.constants import WEIGHT_UNITS, VOLUME_UNITS, COUNT_UNITS, PACKAGE_UNITS
from .exceptions import ServiceError

# Configure logging
logger = logging.getLogger(__name__)

# Unit metadata for seeding - maps code to (display_name, symbol, un_cefact_code)
UNIT_METADATA = {
    # Weight units
    "oz": ("ounce", "oz", "ONZ"),
    "lb": ("pound", "lb", "LBR"),
    "g": ("gram", "g", "GRM"),
    "kg": ("kilogram", "kg", "KGM"),
    # Volume units
    "tsp": ("teaspoon", "tsp", None),
    "tbsp": ("tablespoon", "tbsp", None),
    "cup": ("cup", "cup", None),
    "ml": ("milliliter", "ml", "MLT"),
    "l": ("liter", "l", "LTR"),
    "fl oz": ("fluid ounce", "fl oz", "OZA"),
    "pt": ("pint", "pt", "PTI"),
    "qt": ("quart", "qt", "QTI"),
    "gal": ("gallon", "gal", "GLL"),
    # Count units
    "each": ("each", "ea", "EA"),
    "count": ("count", "ct", None),
    "piece": ("piece", "pc", "PCE"),
    "dozen": ("dozen", "dz", "DZN"),
    # Package/container types
    "bag": ("bag", "bag", "BG"),
    "bar": ("bar", "bar", None),
    "bottle": ("bottle", "bottle", "BO"),
    "box": ("box", "box", "BX"),
    "can": ("can", "can", "CA"),
    "carton": ("carton", "carton", "CT"),
    "case": ("case", "case", "CS"),
    "clamshell": ("clamshell", "clamshell", None),
    "container": ("container", "container", None),
    "jar": ("jar", "jar", "JR"),
    "package": ("package", "pkg", "PK"),
    "packet": ("packet", "packet", "PA"),
    "pouch": ("pouch", "pouch", "PO"),
    "roll": ("roll", "roll", "RL"),
    "sachet": ("sachet", "sachet", None),
    "sheet": ("sheet", "sheet", "ST"),
    "stick": ("stick", "stick", None),
    "tub": ("tub", "tub", "TB"),
    "tube": ("tube", "tube", "TU"),
    "wrapper": ("wrapper", "wrapper", None),
}

# Global engine and session factory
_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Set SQLite pragmas on connection.

    This event listener is called for every new database connection.
    It enables foreign key constraints and sets WAL mode.
    """
    cursor = dbapi_connection.cursor()

    # Enable foreign key constraints (critical for referential integrity)
    cursor.execute("PRAGMA foreign_keys=ON")

    # Set WAL (Write-Ahead Logging) mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")

    # Set synchronous mode - FULL ensures WAL writes are durable on disk
    # before returning from commit (prevents data loss on app exit)
    cursor.execute("PRAGMA synchronous=FULL")

    cursor.close()


def create_database_engine(database_url: Optional[str] = None, echo: bool = False) -> Engine:
    """
    Create and configure the database engine.

    Args:
        database_url: Optional database URL. If None, uses config default.
        echo: If True, log all SQL statements (useful for debugging)

    Returns:
        Configured SQLAlchemy Engine
    """
    if database_url is None:
        database_url = get_config().database_url

    logger.info(f"Creating database engine: {database_url}")

    # Get config for database connection settings
    config = get_config()

    # Create engine with appropriate configuration
    if ":memory:" in database_url or "mode=memory" in database_url:
        # For in-memory databases (testing), use StaticPool
        # Keep check_same_thread=False for test isolation
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # For file-based databases, use Config.db_connect_args
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args=config.db_connect_args,
        )

    return engine


def seed_units() -> None:
    """
    Seed the units reference table with standard units.

    This function is idempotent - it only seeds if the units table is empty.
    Units are sourced from constants.py with additional metadata for UI display.
    """
    # Import Unit model locally to avoid circular imports
    from ..models.unit import Unit

    with session_scope() as session:
        # Check if units already exist (idempotent)
        existing_count = session.query(Unit).count()
        if existing_count > 0:
            logger.debug(f"Units table already has {existing_count} units, skipping seed")
            return

        logger.info("Seeding units reference table")

        units_to_add = []

        # Seed weight units
        for sort_order, code in enumerate(WEIGHT_UNITS):
            display_name, symbol, un_cefact_code = UNIT_METADATA.get(code, (code, code, None))
            units_to_add.append(
                Unit(
                    code=code,
                    display_name=display_name,
                    symbol=symbol,
                    category="weight",
                    un_cefact_code=un_cefact_code,
                    sort_order=sort_order,
                )
            )

        # Seed volume units
        for sort_order, code in enumerate(VOLUME_UNITS):
            display_name, symbol, un_cefact_code = UNIT_METADATA.get(code, (code, code, None))
            units_to_add.append(
                Unit(
                    code=code,
                    display_name=display_name,
                    symbol=symbol,
                    category="volume",
                    un_cefact_code=un_cefact_code,
                    sort_order=sort_order,
                )
            )

        # Seed count units
        for sort_order, code in enumerate(COUNT_UNITS):
            display_name, symbol, un_cefact_code = UNIT_METADATA.get(code, (code, code, None))
            units_to_add.append(
                Unit(
                    code=code,
                    display_name=display_name,
                    symbol=symbol,
                    category="count",
                    un_cefact_code=un_cefact_code,
                    sort_order=sort_order,
                )
            )

        # Seed package units
        for sort_order, code in enumerate(PACKAGE_UNITS):
            display_name, symbol, un_cefact_code = UNIT_METADATA.get(code, (code, code, None))
            units_to_add.append(
                Unit(
                    code=code,
                    display_name=display_name,
                    symbol=symbol,
                    category="package",
                    un_cefact_code=un_cefact_code,
                    sort_order=sort_order,
                )
            )

        session.add_all(units_to_add)
        logger.info(f"Seeded {len(units_to_add)} units to reference table")


def seed_recipe_categories() -> None:
    """
    Seed default recipe categories. Idempotent.

    Seeds the recipe_categories table with standard baking categories on
    first run. Also discovers any distinct Recipe.category values not
    already in the defaults and adds them.

    This function is idempotent - it only seeds if the table is empty.
    """
    from ..models.recipe_category import RecipeCategory
    from ..models.recipe import Recipe

    with session_scope() as session:
        existing_count = session.query(RecipeCategory).count()
        if existing_count > 0:
            logger.debug("Recipe categories already exist, skipping seed")
            return

        # Default categories with sort_order gaps for easy reordering
        defaults = [
            ("Cakes", "cakes", 10),
            ("Cookies", "cookies", 20),
            ("Candies", "candies", 30),
            ("Brownies", "brownies", 40),
            ("Bars", "bars", 50),
            ("Breads", "breads", 60),
            ("Other", "other", 70),
        ]

        # Also discover existing recipe categories not in defaults
        default_names = {name for name, _, _ in defaults}
        existing_recipe_cats = (
            session.query(Recipe.category)
            .distinct()
            .filter(Recipe.category.isnot(None))
            .all()
        )

        sort_order = 80
        for (cat_name,) in existing_recipe_cats:
            if cat_name and cat_name not in default_names:
                slug = cat_name.lower().replace(" ", "-")
                defaults.append((cat_name, slug, sort_order))
                sort_order += 10

        for name, slug, order in defaults:
            category = RecipeCategory(
                name=name, slug=slug, sort_order=order
            )
            session.add(category)

        logger.info(f"Seeded {len(defaults)} recipe categories")


def init_database(engine: Optional[Engine] = None) -> None:
    """
    Initialize the database by creating all tables.

    This function creates all tables defined in the models if they don't exist.
    It's safe to call multiple times - existing tables won't be recreated.

    Args:
        engine: Optional engine to use. If None, uses global engine.
    """
    if engine is None:
        engine = get_engine()

    logger.info("Initializing database tables")

    # Import all models to ensure they're registered with Base
    # This is necessary for Base.metadata.create_all() to work
    from ..models import ingredient, recipe, inventory_snapshot, finished_good  # noqa: F401
    from ..models import production_record  # noqa: F401  # Feature 008
    from ..models import unit  # noqa: F401  # Feature 022
    from ..models import event  # noqa: F401  # Events and targets (F065 adds snapshot FKs)
    from ..models import recipe_snapshot, finished_good_snapshot  # noqa: F401  # Snapshots
    from ..models import production_plan_snapshot  # noqa: F401  # Planning (F065 refactored)
    from ..models import production_run, assembly_run  # noqa: F401  # Production/assembly runs

    # Feature 047: Materials Management System
    from ..models import material_category, material_subcategory, material  # noqa: F401
    from ..models import material_product, material_unit  # noqa: F401
    from ..models import material_purchase, material_consumption  # noqa: F401

    # Feature 096: Recipe Category Management
    from ..models import recipe_category  # noqa: F401

    # Create all tables
    Base.metadata.create_all(engine)

    logger.info("Database tables initialized successfully")

    # Seed reference data
    logger.info("Seeding unit reference table")
    seed_units()

    logger.info("Seeding recipe categories")
    seed_recipe_categories()


def get_engine(force_recreate: bool = False) -> Engine:
    """
    Get the global database engine.

    This implements a singleton pattern for the engine.

    Args:
        force_recreate: If True, recreate the engine even if one exists

    Returns:
        Database engine
    """
    global _engine

    if _engine is None or force_recreate:
        _engine = create_database_engine()

    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get the global session factory.

    Returns:
        Session factory (sessionmaker)
    """
    global _SessionFactory

    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    return _SessionFactory


def get_session() -> Session:
    """
    Create a new database session.

    Returns:
        New Session instance

    Example:
        session = get_session()
        try:
            # Do database operations
            ingredient = session.query(Ingredient).first()
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    """
    session_factory = get_session_factory()
    return session_factory()


@contextmanager
def session_scope():
    """
    Provide a transactional scope for database operations.

    This context manager handles session lifecycle automatically:
    - Creates a new session
    - Commits on success
    - Rolls back on exception
    - Always closes the session

    Yields:
        Database session

    Example:
        with session_scope() as session:
            ingredient = Ingredient(name="Flour", ...)
            session.add(ingredient)
            # Commit happens automatically if no exception
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_session():
    """
    Provide a database session for read operations without automatic transaction management.

    This context manager is primarily used for read operations where you need manual
    control over transactions. For operations that modify data, prefer session_scope().

    Yields:
        Database session

    Example:
        with get_db_session() as session:
            items = session.query(Item).all()
            # No automatic commit - session is just closed
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def database_exists() -> bool:
    """
    Check if the database file exists.

    Returns:
        True if database exists, False otherwise
    """
    return get_config().database_exists()


def verify_database() -> bool:
    """
    Verify that the database is accessible and has tables.

    Returns:
        True if database is valid, False otherwise
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Check if we have at least some expected tables
        expected_tables = ["ingredients", "recipes"]
        has_tables = any(table in tables for table in expected_tables)

        return has_tables
    except (ServiceError, Exception) as e:
        logger.error(f"Database verification failed: {e}")
        return False


def reset_database(confirm: bool = False) -> None:
    """
    Delete and recreate the database file.

    WARNING: This will delete all data!

    Args:
        confirm: Must be True to actually reset. Safety check.

    Raises:
        ValueError: If confirm is not True
    """
    import traceback
    print("=" * 60)
    print("WARNING: reset_database called!")
    traceback.print_stack()
    print("=" * 60)

    if not confirm:
        raise ValueError("Must pass confirm=True to reset database. This will delete all data!")

    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST")

    config = get_config()
    db_path = config.database_path

    # Close all connections first
    close_connections()

    # Delete the database file and related SQLite files (WAL, SHM)
    import os

    for suffix in ["", "-wal", "-shm"]:
        file_path = str(db_path) + suffix
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted: {file_path}")

    logger.info("Database files deleted - will be recreated on next initialization")


def checkpoint_wal() -> None:
    """
    Force a WAL checkpoint to move all WAL data into the main database file.

    Should be called before application exit to ensure all committed data
    is durably stored in the main database file, not just the WAL.
    """
    global _engine

    if _engine is not None:
        try:
            with _engine.connect() as conn:
                conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            logger.info("WAL checkpoint completed")
        except Exception as e:
            logger.error(f"WAL checkpoint failed: {e}")


def close_connections() -> None:
    """
    Close all database connections.

    Checkpoints the WAL and disposes the engine. Should be called
    before application exit.
    """
    global _engine, _SessionFactory

    # Checkpoint WAL before closing to ensure durability
    checkpoint_wal()

    if _SessionFactory is not None:
        _SessionFactory.close_all()
        _SessionFactory = None

    if _engine is not None:
        _engine.dispose()
        _engine = None

    logger.info("Database connections closed")


# Convenience function for common initialization pattern
def initialize_app_database() -> None:
    """
    Initialize the application database.

    This is the main entry point for setting up the database when the app starts.
    It will create the database file and tables if they don't exist.
    """
    config = get_config()

    if not config.database_exists():
        logger.info(f"Creating new database at: {config.database_path}")
    else:
        logger.info(f"Using existing database at: {config.database_path}")

    # Create engine and initialize tables
    engine = get_engine()
    init_database(engine)

    # Verify database is working
    if verify_database():
        logger.info("Database initialized and verified successfully")
    else:
        logger.warning("Database verification failed - tables may not exist")
