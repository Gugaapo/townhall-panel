from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.db.mongodb import get_database
from app.db.repositories.base import BaseRepository


class DocumentHistoryRepository(BaseRepository):
    """Repository for document history/audit trail operations"""

    def __init__(self):
        super().__init__(collection_name="document_history")

    async def create_history_entry(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new history entry

        Args:
            history_data: History entry data
        """
        # Add timestamp
        history_data["timestamp"] = datetime.now(timezone.utc)

        return await self.create(history_data)

    async def find_by_document(
        self,
        document_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all history entries for a specific document

        Args:
            document_id: Document ID
            skip: Number of entries to skip
            limit: Maximum number of entries to return
        """
        return await self.find_many(
            filter={"document_id": document_id},
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)]  # Most recent first
        )

    async def find_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find all actions performed by a specific user

        Args:
            user_id: User ID
            skip: Number of entries to skip
            limit: Maximum number of entries to return
        """
        return await self.find_many(
            filter={"performed_by": user_id},
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)]
        )

    async def find_by_department(
        self,
        department_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find all actions performed by users in a specific department

        Args:
            department_id: Department ID
            skip: Number of entries to skip
            limit: Maximum number of entries to return
        """
        return await self.find_many(
            filter={"performed_by_department": department_id},
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)]
        )

    async def find_by_action(
        self,
        action: str,
        document_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find history entries by action type

        Args:
            action: Action type (e.g., 'forwarded', 'created')
            document_id: Optionally filter by specific document
            skip: Number of entries to skip
            limit: Maximum number of entries to return
        """
        filter_query = {"action": action}

        if document_id:
            filter_query["document_id"] = document_id

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)]
        )

    async def get_document_timeline(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get complete timeline of a document (all history entries)

        Args:
            document_id: Document ID

        Returns:
            List of all history entries in chronological order
        """
        return await self.find_many(
            filter={"document_id": document_id},
            skip=0,
            limit=1000,  # High limit to get complete timeline
            sort=[("timestamp", 1)]  # Chronological order (oldest first)
        )

    async def get_forwarding_chain(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get the forwarding chain of a document (department-to-department flow)

        Args:
            document_id: Document ID

        Returns:
            List of forwarding actions in chronological order
        """
        return await self.find_many(
            filter={
                "document_id": document_id,
                "action": "forwarded"
            },
            skip=0,
            limit=100,
            sort=[("timestamp", 1)]  # Chronological order
        )

    async def count_user_actions(
        self,
        user_id: str,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count actions performed by a user

        Args:
            user_id: User ID
            action: Optionally filter by action type
            start_date: Optionally filter by start date
            end_date: Optionally filter by end date

        Returns:
            Count of matching actions
        """
        db = await get_database()

        filter_query = {"performed_by": user_id}

        if action:
            filter_query["action"] = action

        if start_date or end_date:
            filter_query["timestamp"] = {}
            if start_date:
                filter_query["timestamp"]["$gte"] = start_date
            if end_date:
                filter_query["timestamp"]["$lte"] = end_date

        count = await db[self.collection_name].count_documents(filter_query)
        return count

    async def get_recent_activity(
        self,
        department_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent document activity

        Args:
            department_id: Optionally filter by department
            limit: Number of recent entries to return

        Returns:
            List of recent history entries
        """
        filter_query = {}

        if department_id:
            filter_query["$or"] = [
                {"performed_by_department": department_id},
                {"from_department_id": department_id},
                {"to_department_id": department_id}
            ]

        return await self.find_many(
            filter=filter_query,
            skip=0,
            limit=limit,
            sort=[("timestamp", -1)]
        )
