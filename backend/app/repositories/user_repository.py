"""User Repository — lookup methods specific to the User model."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Fetch a user by email address (used during login)."""
        return db.query(User).filter(User.email == email).first()

    def email_exists(self, db: Session, email: str) -> bool:
        """Returns True if an account with this email already exists."""
        return db.query(User.id).filter(User.email == email).first() is not None


user_repository = UserRepository()
