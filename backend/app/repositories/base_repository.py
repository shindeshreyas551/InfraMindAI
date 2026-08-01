"""
Generic Base Repository — typed CRUD operations for any SQLAlchemy model.

Design decisions:
  - Uses Python generics (TypeVar + Generic) so subclasses get full
    type-safety and IDE autocompletion without duplicating code.
  - All methods accept an injected `Session` (from FastAPI's `get_db`),
    keeping DB access stateless — no session is stored on the repository.
  - `get_multi` supports limit/offset pagination used by list endpoints.
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository. Subclass with a concrete SQLAlchemy model."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, record_id: int) -> Optional[ModelType]:
        """Fetch a single record by primary key. Returns None if not found."""
        return db.get(self.model, record_id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Fetch a paginated list of records ordered by primary key."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj: ModelType) -> ModelType:
        """Persist a new ORM object and return it with its generated id."""
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, *, db_obj: ModelType, updates: dict) -> ModelType:
        """Apply a dictionary of field updates to an existing record."""
        for field, value in updates.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, record_id: int) -> Optional[ModelType]:
        """Hard-delete a record by primary key. Returns the deleted object."""
        obj = db.get(self.model, record_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
