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

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..utils.config import get_config
from ..models.base import Base

# Configure logging
logger = logging.getLogger(__name__)

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

    # Set synchronous mode for better performance while maintaining safety
    cursor.execute("PRAGMA synchronous=NORMAL")

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

    # Create engine with appropriate configuration
    if ":memory:" in database_url or "mode=memory" in database_url:
        # For in-memory databases (testing), use StaticPool
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # For file-based databases
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

    return engine


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

    # Create all tables
    Base.metadata.create_all(engine)

    logger.info("Database tables initialized successfully")


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
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False


def reset_database(confirm: bool = False) -> None:
    """
    Drop all tables and recreate the database.

    WARNING: This will delete all data!

    Args:
        confirm: Must be True to actually reset. Safety check.

    Raises:
        ValueError: If confirm is not True
    """
    if not confirm:
        raise ValueError("Must pass confirm=True to reset database. This will delete all data!")

    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST")

    engine = get_engine()

    # Import all models
    from ..models import ingredient, recipe, inventory_snapshot, finished_good  # noqa: F401

    # Drop all tables
    Base.metadata.drop_all(engine)
    logger.info("All tables dropped")

    # Recreate tables
    Base.metadata.create_all(engine)
    logger.info("Tables recreated")


def close_connections() -> None:
    """
    Close all database connections.

    Useful for cleanup or before application exit.
    """
    global _engine, _SessionFactory

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
