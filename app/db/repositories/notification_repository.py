from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.db.repositories.base import BaseRepository
from app.db.mongodb import Collections


class NotificationRepository(BaseRepository):
    """Repository for notification operations"""

    def __init__(self):
        super().__init__(Collections.NOTIFICATIONS)

    async def find_by_user(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find notifications for a user

        Args:
            user_id: User ID to find notifications for
            is_read: Optional filter by read status
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of notifications for the user
        """
        filter_query = {"user_id": user_id}
        if is_read is not None:
            filter_query["is_read"] = is_read

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def count_unread(self, user_id: str) -> int:
        """
        Count unread notifications for a user

        Args:
            user_id: User ID

        Returns:
            Number of unread notifications
        """
        return await self.count({"user_id": user_id, "is_read": False})

    async def mark_as_read(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a notification as read

        Args:
            notification_id: Notification ID

        Returns:
            Updated notification if found, None otherwise
        """
        return await self.update_by_id(
            notification_id,
            {"is_read": True, "read_at": datetime.now(timezone.utc)}
        )

    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all user's notifications as read

        Args:
            user_id: User ID

        Returns:
            Number of notifications updated
        """
        return await self.update_many(
            {"user_id": user_id, "is_read": False},
            {"is_read": True, "read_at": datetime.now(timezone.utc)}
        )

    async def find_by_document(
        self,
        document_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find all notifications for a document

        Args:
            document_id: Document ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of notifications for the document
        """
        return await self.find_many(
            filter={"document_id": document_id},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
