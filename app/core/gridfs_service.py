from typing import Optional, BinaryIO, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import gridfs
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
import magic  # python-magic for MIME type detection

from app.db.mongodb import get_database


class GridFSService:
    """Service for managing files with GridFS"""

    def __init__(self):
        self._bucket: Optional[AsyncIOMotorGridFSBucket] = None

    async def get_bucket(self) -> AsyncIOMotorGridFSBucket:
        """Get or create GridFS bucket"""
        if self._bucket is None:
            db = get_database()
            self._bucket = AsyncIOMotorGridFSBucket(db)
        return self._bucket

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a file to GridFS

        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            user_id: User ID who uploaded the file
            metadata: Additional metadata to store with the file

        Returns:
            GridFS file ID as string
        """
        bucket = await self.get_bucket()

        # Auto-detect content type if not provided
        if content_type is None:
            try:
                mime = magic.Magic(mime=True)
                content_type = mime.from_buffer(file_content)
            except Exception:
                content_type = "application/octet-stream"

        # Prepare metadata
        file_metadata = {
            "uploaded_at": datetime.now(timezone.utc),
            "uploaded_by": user_id,
            "original_filename": filename,
            **(metadata or {})
        }

        # Upload file
        file_id = await bucket.upload_from_stream(
            filename,
            file_content,
            metadata=file_metadata,
            content_type=content_type
        )

        return str(file_id)

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download a file from GridFS

        Args:
            file_id: GridFS file ID

        Returns:
            File content as bytes, or None if file not found
        """
        try:
            bucket = await self.get_bucket()
            file_data = await bucket.open_download_stream(ObjectId(file_id))
            content = await file_data.read()
            return content
        except gridfs.errors.NoFile:
            return None
        except Exception:
            return None

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            file_id: GridFS file ID

        Returns:
            File metadata dict, or None if file not found
        """
        try:
            bucket = await self.get_bucket()
            file_doc = await bucket.open_download_stream(ObjectId(file_id))

            return {
                "file_id": str(file_doc._id),
                "filename": file_doc.filename,
                "content_type": file_doc.content_type,
                "length": file_doc.length,
                "upload_date": file_doc.upload_date,
                "metadata": file_doc.metadata
            }
        except gridfs.errors.NoFile:
            return None
        except Exception:
            return None

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from GridFS

        Args:
            file_id: GridFS file ID

        Returns:
            True if deleted, False if file not found
        """
        try:
            bucket = await self.get_bucket()
            await bucket.delete(ObjectId(file_id))
            return True
        except gridfs.errors.NoFile:
            return False
        except Exception:
            return False

    async def file_exists(self, file_id: str) -> bool:
        """
        Check if a file exists in GridFS

        Args:
            file_id: GridFS file ID

        Returns:
            True if file exists, False otherwise
        """
        try:
            bucket = await self.get_bucket()
            await bucket.open_download_stream(ObjectId(file_id))
            return True
        except gridfs.errors.NoFile:
            return False
        except Exception:
            return False

    async def list_files(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> list:
        """
        List files in GridFS

        Args:
            user_id: Optionally filter by uploader
            skip: Number of files to skip
            limit: Maximum number of files to return

        Returns:
            List of file metadata dicts
        """
        db = get_database()

        # Build filter
        filter_query = {}
        if user_id:
            filter_query["metadata.uploaded_by"] = user_id

        # Query GridFS files collection
        cursor = db.fs.files.find(filter_query).sort("uploadDate", -1).skip(skip).limit(limit)

        files = []
        async for file_doc in cursor:
            files.append({
                "file_id": str(file_doc["_id"]),
                "filename": file_doc["filename"],
                "content_type": file_doc.get("contentType"),
                "length": file_doc["length"],
                "upload_date": file_doc["uploadDate"],
                "metadata": file_doc.get("metadata", {})
            })

        return files


# Global GridFS service instance
gridfs_service = GridFSService()
