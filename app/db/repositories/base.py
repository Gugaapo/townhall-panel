from typing import TypeVar, Generic, Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from datetime import datetime

from app.db.mongodb import get_database

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Base repository for MongoDB operations

    Provides common CRUD operations for all repositories.
    """

    def __init__(self, collection_name: str):
        """
        Initialize repository with collection name

        Args:
            collection_name: Name of the MongoDB collection
        """
        self.collection_name = collection_name

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection"""
        db = get_database()
        return db[self.collection_name]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document

        Args:
            data: Document data to insert

        Returns:
            Created document with _id
        """
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()

        result = await self.collection.insert_one(data)
        data["_id"] = result.inserted_id

        return data

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Find a document by ID

        Args:
            id: Document ID (string or ObjectId)

        Returns:
            Document if found, None otherwise
        """
        try:
            object_id = ObjectId(id)
            return await self.collection.find_one({"_id": object_id})
        except Exception:
            return None

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching the filter

        Args:
            filter: MongoDB filter query

        Returns:
            Document if found, None otherwise
        """
        return await self.collection.find_one(filter)

    async def find_many(
        self,
        filter: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 20,
        sort: List[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents matching the filter

        Args:
            filter: MongoDB filter query
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of documents
        """
        filter = filter or {}
        cursor = self.collection.find(filter)

        if sort:
            cursor = cursor.sort(sort)

        cursor = cursor.skip(skip).limit(limit)

        return await cursor.to_list(length=limit)

    async def count(self, filter: Dict[str, Any] = None) -> int:
        """
        Count documents matching the filter

        Args:
            filter: MongoDB filter query

        Returns:
            Count of matching documents
        """
        filter = filter or {}
        return await self.collection.count_documents(filter)

    async def update_by_id(
        self,
        id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a document by ID

        Args:
            id: Document ID
            data: Data to update

        Returns:
            Updated document if found, None otherwise
        """
        try:
            object_id = ObjectId(id)
            data["updated_at"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": data},
                return_document=True
            )

            return result
        except Exception:
            return None

    async def update_one(
        self,
        filter: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a single document matching the filter

        Args:
            filter: MongoDB filter query
            data: Data to update

        Returns:
            Updated document if found, None otherwise
        """
        data["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            filter,
            {"$set": data},
            return_document=True
        )

        return result

    async def update_many(
        self,
        filter: Dict[str, Any],
        data: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents matching the filter

        Args:
            filter: MongoDB filter query
            data: Data to update

        Returns:
            Number of documents updated
        """
        data["updated_at"] = datetime.utcnow()

        result = await self.collection.update_many(
            filter,
            {"$set": data}
        )

        return result.modified_count

    async def delete_by_id(self, id: str) -> bool:
        """
        Delete a document by ID

        Args:
            id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            object_id = ObjectId(id)
            result = await self.collection.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except Exception:
            return False

    async def delete_one(self, filter: Dict[str, Any]) -> bool:
        """
        Delete a single document matching the filter

        Args:
            filter: MongoDB filter query

        Returns:
            True if deleted, False otherwise
        """
        result = await self.collection.delete_one(filter)
        return result.deleted_count > 0

    async def delete_many(self, filter: Dict[str, Any]) -> int:
        """
        Delete multiple documents matching the filter

        Args:
            filter: MongoDB filter query

        Returns:
            Number of documents deleted
        """
        result = await self.collection.delete_many(filter)
        return result.deleted_count

    async def exists(self, filter: Dict[str, Any]) -> bool:
        """
        Check if a document exists

        Args:
            filter: MongoDB filter query

        Returns:
            True if exists, False otherwise
        """
        count = await self.collection.count_documents(filter, limit=1)
        return count > 0
