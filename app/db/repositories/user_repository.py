from typing import Optional, Dict, Any
from app.db.repositories.base import BaseRepository
from app.db.mongodb import Collections


class UserRepository(BaseRepository):
    """Repository for user operations"""

    def __init__(self):
        super().__init__(Collections.USERS)

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email

        Args:
            email: User email address

        Returns:
            User document if found, None otherwise
        """
        return await self.find_one({"email": email.lower()})

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email already exists

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        return await self.exists({"email": email.lower()})

    async def find_by_department(self, department_id: str) -> list:
        """
        Find all users in a department

        Args:
            department_id: Department ID

        Returns:
            List of users in the department
        """
        return await self.find_many({"department_id": department_id})

    async def find_active_users(self, skip: int = 0, limit: int = 20) -> list:
        """
        Find all active users

        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of active users
        """
        return await self.find_many(
            {"is_active": True},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
