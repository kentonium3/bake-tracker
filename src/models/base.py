"""
Base model class for all database models.

Provides common functionality and fields for all models:
- Primary key (Integer for now, UUID for future)
- UUID column (for migration to UUID primary keys)
- Timestamp fields (created_at, updated_at)
- Utility methods (to_dict, from_dict)
- SQLAlchemy declarative base
"""

import uuid as uuid_lib
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, validates

from src.utils.datetime_utils import utc_now

# Create the declarative base for all models
Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields and methods.

    All models should inherit from this class to get:
    - id: Primary key (Integer, will be migrated to UUID)
    - uuid: UUID identifier (will become primary key in future)
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last modified
    - to_dict(): Convert model to dictionary
    """

    __abstract__ = True

    # Primary key (Integer for backward compatibility during migration)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # UUID (will become primary key after migration)
    # Stored as string for SQLite compatibility
    uuid = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid_lib.uuid4()), index=True
    )

    # Timestamp fields
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            include_relationships: If True, include related objects (default: False)

        Returns:
            Dictionary representation of the model
        """
        result = {}

        # Include all column values
        for column in self.__table__.columns:
            value = getattr(self, column.name)

            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                value = value.isoformat()

            result[column.name] = value

        # Optionally include relationships
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                rel_name = relationship.key
                rel_value = getattr(self, rel_name)

                if rel_value is None:
                    result[rel_name] = None
                elif isinstance(rel_value, list):
                    # One-to-many or many-to-many relationship
                    result[rel_name] = [item.to_dict() for item in rel_value]
                else:
                    # Many-to-one relationship
                    result[rel_name] = rel_value.to_dict()

        return result

    @validates("uuid")
    def _validate_uuid(self, _key: str, value: Any) -> str:
        """Normalize UUID values to strings for SQLite compatibility."""
        if value is None:
            return value
        return str(value)

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model instance from dictionary.

        Only updates fields that exist in the model and are in the dictionary.

        Args:
            data: Dictionary with field names and values
        """
        for column in self.__table__.columns:
            if column.name in data and column.name not in ["id", "created_at", "updated_at"]:
                setattr(self, column.name, data[column.name])

        # Update timestamp
        self.updated_at = utc_now()

    def __repr__(self) -> str:
        """
        String representation of model instance.

        Returns:
            String like "ClassName(id=1, ...)"
        """
        class_name = self.__class__.__name__
        attrs = []

        # Include id if it exists
        if hasattr(self, "id") and self.id is not None:
            attrs.append(f"id={self.id}")

        # Include name if it exists (common field)
        if hasattr(self, "name") and self.name is not None:
            attrs.append(f"name='{self.name}'")

        attrs_str = ", ".join(attrs)
        return f"{class_name}({attrs_str})"
