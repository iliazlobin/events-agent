"""Abstract base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

# Generic type for domain models
T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base repository interface.

    Defines minimal CRUD operations that all repositories must implement.
    Follows Interface Segregation Principle - only essential methods.

    Type parameter T represents the domain model (e.g., Event).
    """

    @abstractmethod
    def save(self, entity: T) -> T:
        """Save a single entity.

        Args:
            entity: Domain model instance to save.

        Returns:
            Saved entity with populated ID if applicable.
        """
        pass

    @abstractmethod
    def save_many(self, entities: List[T]) -> int:
        """Save multiple entities in a batch.

        Args:
            entities: List of domain model instances to save.

        Returns:
            Number of entities successfully saved.
        """
        pass

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[T]:
        """Find entity by primary key ID.

        Args:
            id: Primary key ID.

        Returns:
            Domain model instance if found, None otherwise.
        """
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """Retrieve all entities.

        Returns:
            List of all entities (may be empty).
        """
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Delete entity by primary key ID.

        Args:
            id: Primary key ID.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total number of entities.

        Returns:
            Total entity count.
        """
        pass
