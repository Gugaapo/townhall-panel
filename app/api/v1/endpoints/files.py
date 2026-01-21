from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone
import io

from app.core.gridfs_service import gridfs_service
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.core.permissions import require_authenticated
from app.schemas.document_history import DocumentAction
from app.utils.constants import UserRole

router = APIRouter()

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed file types (MIME types)
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/gif",
    "text/plain",
    "application/zip",
]


@router.post(
    "/upload/{document_id}",
    summary="Upload File to Document",
    description="Upload a file and attach it to a document",
    responses={
        201: {"description": "File uploaded successfully"},
        400: {"description": "Invalid file or file too large"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to upload to this document"},
        404: {"description": "Document not found"}
    }
)
async def upload_file_to_document(
    document_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_authenticated)
):
    """
    Upload a file and attach it to a document

    - Maximum file size: 50MB
    - Allowed file types: PDF, Word, Excel, Images, Text, ZIP

    Only users who can view the document can upload files to it.
    """
    doc_repo = DocumentRepository()
    history_repo = DocumentHistoryRepository()

    # Check if document exists
    document = await doc_repo.find_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check permissions (same as viewing document)
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    user_dept = str(current_user["department_id"])
    doc_creator_dept = str(document.get("creator_department_id"))
    doc_holder_dept = str(document.get("current_holder_department_id"))
    is_creator = str(document.get("creator_id")) == str(current_user["_id"])

    can_upload = is_admin or is_creator or user_dept == doc_creator_dept or user_dept == doc_holder_dept

    if not can_upload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload files to this document"
        )

    # Read file content
    file_content = await file.read()

    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Check file type
    content_type = file.content_type
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Upload to GridFS
    try:
        file_id = await gridfs_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type=content_type,
            user_id=str(current_user["_id"]),
            metadata={
                "document_id": document_id,
                "uploaded_by_name": current_user.get("full_name", "Unknown")
            }
        )

        # Create file info to add to document
        file_info = {
            "file_id": file_id,
            "filename": file.filename,
            "content_type": content_type,
            "size": len(file_content),
            "uploaded_at": datetime.now(timezone.utc),
            "uploaded_by": str(current_user["_id"])
        }

        # Add file to document
        updated_document = await doc_repo.add_file(document_id, file_info)

        # Create audit trail entry
        await history_repo.create_history_entry({
            "document_id": document_id,
            "action": DocumentAction.FILE_ADDED.value,
            "performed_by": str(current_user["_id"]),
            "performed_by_name": current_user.get("full_name", "Unknown"),
            "performed_by_department": str(current_user["department_id"]),
            "comment": f"File uploaded: {file.filename}",
            "metadata": {
                "file_id": file_id,
                "filename": file.filename,
                "size": len(file_content)
            }
        })

        return {
            "success": True,
            "message": "File uploaded successfully",
            "file": file_info
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get(
    "/download/{file_id}",
    summary="Download File",
    description="Download a file from GridFS",
    responses={
        200: {"description": "File content"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to download this file"},
        404: {"description": "File not found"}
    }
)
async def download_file(
    file_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Download a file

    Users can download files from documents they have access to.
    """
    # Get file info
    file_info = await gridfs_service.get_file_info(file_id)

    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if user can access the document this file belongs to
    doc_repo = DocumentRepository()
    document_id = file_info.get("metadata", {}).get("document_id")

    if document_id:
        document = await doc_repo.find_by_id(document_id)
        if document:
            # Check permissions
            is_admin = current_user.get("role") == UserRole.ADMIN.value
            user_dept = str(current_user["department_id"])
            doc_creator_dept = str(document.get("creator_department_id"))
            doc_holder_dept = str(document.get("current_holder_department_id"))
            is_creator = str(document.get("creator_id")) == str(current_user["_id"])

            can_download = is_admin or is_creator or user_dept == doc_creator_dept or user_dept == doc_holder_dept

            if not can_download:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to download this file"
                )

    # Download file
    file_content = await gridfs_service.download_file(file_id)

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=file_info.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename={file_info['filename']}"
        }
    )


@router.get(
    "/info/{file_id}",
    summary="Get File Info",
    description="Get metadata for a file",
    responses={
        200: {"description": "File metadata"},
        401: {"description": "Not authenticated"},
        404: {"description": "File not found"}
    }
)
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get file metadata

    Returns information about a file without downloading it.
    """
    file_info = await gridfs_service.get_file_info(file_id)

    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return file_info


@router.delete(
    "/{document_id}/{file_id}",
    summary="Delete File from Document",
    description="Remove a file from a document",
    responses={
        200: {"description": "File deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this file"},
        404: {"description": "Document or file not found"}
    }
)
async def delete_file_from_document(
    document_id: str,
    file_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Delete a file from a document

    Only admins, document creators, or department heads can delete files.
    """
    doc_repo = DocumentRepository()
    history_repo = DocumentHistoryRepository()

    # Check if document exists
    document = await doc_repo.find_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if file exists in document
    file_found = False
    file_name = None
    for file_info in document.get("files", []):
        if file_info.get("file_id") == file_id:
            file_found = True
            file_name = file_info.get("filename")
            break

    if not file_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in document"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_dept_head = current_user.get("role") == UserRole.DEPARTMENT_HEAD.value
    is_creator = str(document.get("creator_id")) == str(current_user["_id"])
    same_dept = str(document.get("current_holder_department_id")) == str(current_user["department_id"])

    can_delete = is_admin or is_creator or (is_dept_head and same_dept)

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete files from this document"
        )

    # Remove file from document
    updated_document = await doc_repo.remove_file(document_id, file_id)

    # Delete file from GridFS
    await gridfs_service.delete_file(file_id)

    # Create audit trail entry
    await history_repo.create_history_entry({
        "document_id": document_id,
        "action": DocumentAction.FILE_REMOVED.value,
        "performed_by": str(current_user["_id"]),
        "performed_by_name": current_user.get("full_name", "Unknown"),
        "performed_by_department": str(current_user["department_id"]),
        "comment": f"File deleted: {file_name}",
        "metadata": {
            "file_id": file_id,
            "filename": file_name
        }
    })

    return {
        "success": True,
        "message": f"File '{file_name}' deleted successfully"
    }


@router.get(
    "/list/{document_id}",
    summary="List Document Files",
    description="Get all files attached to a document",
    responses={
        200: {"description": "List of files"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this document"},
        404: {"description": "Document not found"}
    }
)
async def list_document_files(
    document_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    List all files attached to a document

    Returns metadata for all files attached to the document.
    """
    doc_repo = DocumentRepository()

    # Check if document exists
    document = await doc_repo.find_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    user_dept = str(current_user["department_id"])
    doc_creator_dept = str(document.get("creator_department_id"))
    doc_holder_dept = str(document.get("current_holder_department_id"))
    is_creator = str(document.get("creator_id")) == str(current_user["_id"])

    can_view = is_admin or is_creator or user_dept == doc_creator_dept or user_dept == doc_holder_dept

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view files for this document"
        )

    # Return files list
    return {
        "document_id": document_id,
        "files": document.get("files", [])
    }
