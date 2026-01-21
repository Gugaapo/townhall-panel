from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.db.mongodb import get_database
from app.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Repository for document operations"""

    def __init__(self):
        super().__init__(collection_name="documents")

    async def generate_document_number(self) -> str:
        """
        Generate a unique document number in format: DOC-YYYY-NNNNN
        Example: DOC-2025-00001
        """
        db = get_database()
        current_year = datetime.now(timezone.utc).year

        # Find the highest document number for the current year
        pipeline = [
            {
                "$match": {
                    "document_number": {"$regex": f"^DOC-{current_year}-"}
                }
            },
            {
                "$project": {
                    "number_part": {"$substr": ["$document_number", 10, 5]}
                }
            },
            {
                "$sort": {"number_part": -1}
            },
            {
                "$limit": 1
            }
        ]

        result = await db[self.collection_name].aggregate(pipeline).to_list(1)

        if result:
            # Extract the number and increment
            last_number = int(result[0]["number_part"])
            next_number = last_number + 1
        else:
            # First document of the year
            next_number = 1

        # Format: DOC-YYYY-NNNNN (5 digits with leading zeros)
        document_number = f"DOC-{current_year}-{next_number:05d}"
        return document_number

    async def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document with auto-generated document number
        """
        # Generate unique document number
        document_number = await self.generate_document_number()

        # Add document number and default status
        document_data["document_number"] = document_number
        if "status" not in document_data:
            document_data["status"] = "draft"

        # Files array is empty by default
        if "files" not in document_data:
            document_data["files"] = []

        # Create the document
        return await self.create(document_data)

    async def find_by_document_number(self, document_number: str) -> Optional[Dict[str, Any]]:
        """Find a document by its unique document number"""
        db = await get_database()
        return await db[self.collection_name].find_one({"document_number": document_number})

    async def find_by_creator(
        self,
        creator_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find documents created by a specific user"""
        filter_query = {"creator_id": creator_id}

        if status:
            filter_query["status"] = status

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def find_by_department(
        self,
        department_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        as_creator: bool = False,
        as_holder: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find documents related to a department

        Args:
            department_id: Department ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            status: Filter by status
            as_creator: If True, find documents created by the department
            as_holder: If True, find documents currently held by the department
        """
        filter_query = {}

        if as_creator and as_holder:
            # Documents either created by or held by the department
            filter_query["$or"] = [
                {"creator_department_id": department_id},
                {"current_holder_department_id": department_id}
            ]
        elif as_creator:
            filter_query["creator_department_id"] = department_id
        elif as_holder:
            filter_query["current_holder_department_id"] = department_id
        else:
            # Default: either created by or held by
            filter_query["$or"] = [
                {"creator_department_id": department_id},
                {"current_holder_department_id": department_id}
            ]

        if status:
            filter_query["status"] = status

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def find_assigned_to_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find documents assigned to a specific user"""
        filter_query = {"assigned_to_user_id": user_id}

        if status:
            filter_query["status"] = status

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def search_documents(
        self,
        search_query: str,
        department_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search documents by title, description, or document number

        Args:
            search_query: Search term
            department_id: Optionally filter by department (creator or holder)
            skip: Number of documents to skip
            limit: Maximum number of documents to return
        """
        filter_query = {
            "$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"description": {"$regex": search_query, "$options": "i"}},
                {"document_number": {"$regex": search_query, "$options": "i"}}
            ]
        }

        if department_id:
            # Add department filter
            filter_query["$and"] = [
                filter_query,
                {
                    "$or": [
                        {"creator_department_id": department_id},
                        {"current_holder_department_id": department_id}
                    ]
                }
            ]

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def update_status(
        self,
        document_id: str,
        new_status: str
    ) -> Optional[Dict[str, Any]]:
        """Update document status"""
        return await self.update_by_id(
            document_id,
            {"status": new_status}
        )

    async def forward_document(
        self,
        document_id: str,
        to_department_id: str,
        assigned_to_user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Forward a document to another department

        Args:
            document_id: Document ID
            to_department_id: Department to forward to
            assigned_to_user_id: Optional user to assign the document to
        """
        update_data = {
            "current_holder_department_id": to_department_id,
            "assigned_to_user_id": assigned_to_user_id
        }

        return await self.update_by_id(document_id, update_data)

    async def add_file(
        self,
        document_id: str,
        file_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Add a file to a document

        Args:
            document_id: Document ID
            file_info: File information dict
        """
        db = get_database()

        result = await db[self.collection_name].update_one(
            {"_id": ObjectId(document_id)},
            {
                "$push": {"files": file_info},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        if result.modified_count > 0:
            return await self.find_by_id(document_id)
        return None

    async def remove_file(
        self,
        document_id: str,
        file_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Remove a file from a document

        Args:
            document_id: Document ID
            file_id: GridFS file ID to remove
        """
        db = get_database()

        result = await db[self.collection_name].update_one(
            {"_id": ObjectId(document_id)},
            {
                "$pull": {"files": {"file_id": file_id}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        if result.modified_count > 0:
            return await self.find_by_id(document_id)
        return None

    async def archive_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Archive a document"""
        return await self.update_by_id(
            document_id,
            {
                "status": "archived",
                "archived_at": datetime.now(timezone.utc)
            }
        )

    async def get_document_stats(
        self,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get document statistics

        Args:
            department_id: Optionally filter by department
        """
        db = get_database()

        match_query = {}
        if department_id:
            match_query["$or"] = [
                {"creator_department_id": department_id},
                {"current_holder_department_id": department_id}
            ]

        pipeline = [
            {"$match": match_query} if match_query else {"$match": {}},
            {
                "$group": {
                    "_id": None,
                    "total_documents": {"$sum": 1},
                    "by_status": {
                        "$push": "$status"
                    },
                    "by_priority": {
                        "$push": "$priority"
                    }
                }
            }
        ]

        result = await db[self.collection_name].aggregate(pipeline).to_list(1)

        if not result:
            return {
                "total_documents": 0,
                "by_status": {},
                "by_priority": {}
            }

        # Count statuses
        status_counts = {}
        for status in result[0]["by_status"]:
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count priorities
        priority_counts = {}
        for priority in result[0]["by_priority"]:
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return {
            "total_documents": result[0]["total_documents"],
            "by_status": status_counts,
            "by_priority": priority_counts
        }
