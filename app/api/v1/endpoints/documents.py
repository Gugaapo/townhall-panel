from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from typing import List, Optional
from bson import ObjectId

from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentForward,
    DocumentStatusUpdate,
    DocumentStatus
)
from app.schemas.document_history import DocumentHistoryCreate, DocumentHistoryResponse, DocumentAction
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.core.permissions import require_authenticated
from app.utils.constants import UserRole

router = APIRouter()


def convert_document_ids(doc: dict) -> dict:
    """Convert ObjectIds to strings in a document"""
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    if "creator_id" in doc and isinstance(doc["creator_id"], ObjectId):
        doc["creator_id"] = str(doc["creator_id"])
    if "creator_department_id" in doc and isinstance(doc["creator_department_id"], ObjectId):
        doc["creator_department_id"] = str(doc["creator_department_id"])
    if "current_holder_department_id" in doc and isinstance(doc["current_holder_department_id"], ObjectId):
        doc["current_holder_department_id"] = str(doc["current_holder_department_id"])
    if "assigned_to_user_id" in doc and isinstance(doc["assigned_to_user_id"], ObjectId):
        doc["assigned_to_user_id"] = str(doc["assigned_to_user_id"])
    return doc


def convert_history_ids(history: dict) -> dict:
    """Convert ObjectIds to strings in a history entry"""
    if "_id" in history and isinstance(history["_id"], ObjectId):
        history["_id"] = str(history["_id"])
    if "document_id" in history and isinstance(history["document_id"], ObjectId):
        history["document_id"] = str(history["document_id"])
    if "performed_by" in history and isinstance(history["performed_by"], ObjectId):
        history["performed_by"] = str(history["performed_by"])
    if "performed_by_department" in history and isinstance(history["performed_by_department"], ObjectId):
        history["performed_by_department"] = str(history["performed_by_department"])
    if "from_department_id" in history and isinstance(history["from_department_id"], ObjectId):
        history["from_department_id"] = str(history["from_department_id"])
    if "to_department_id" in history and isinstance(history["to_department_id"], ObjectId):
        history["to_department_id"] = str(history["to_department_id"])
    return history


async def create_audit_entry(
    document_id: str,
    action: DocumentAction,
    user: dict,
    **kwargs
):
    """Helper to create audit trail entry"""
    history_repo = DocumentHistoryRepository()

    history_data = {
        "document_id": document_id,
        "action": action.value,
        "performed_by": str(user["_id"]),
        "performed_by_name": user.get("full_name", "Unknown"),
        "performed_by_department": str(user["department_id"]),
        **kwargs
    }

    await history_repo.create_history_entry(history_data)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Document",
    description="Create a new document in the system",
    responses={
        201: {"description": "Document created successfully"},
        400: {"description": "Invalid data"},
        401: {"description": "Not authenticated"},
        404: {"description": "Department or user not found"}
    }
)
async def create_document(
    document_data: DocumentCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated)
):
    """
    Create a new document

    The document will be created with:
    - Auto-generated document number (format: DOC-YYYY-NNNNN)
    - Status: draft
    - Creator: current user
    - Current holder: creator's department
    """
    doc_repo = DocumentRepository()
    dept_repo = DepartmentRepository()
    user_repo = UserRepository()

    # Validate assigned user if provided
    if document_data.assigned_to_user_id:
        assigned_user = await user_repo.find_by_id(document_data.assigned_to_user_id)
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )

    # Prepare document data
    new_document = {
        "title": document_data.title,
        "description": document_data.description,
        "document_type": document_data.document_type.value,
        "priority": document_data.priority.value,
        "creator_id": str(current_user["_id"]),
        "creator_department_id": str(current_user["department_id"]),
        "current_holder_department_id": str(current_user["department_id"]),
        "assigned_to_user_id": document_data.assigned_to_user_id,
        "metadata": document_data.metadata.model_dump() if document_data.metadata else {}
    }

    # Create document (will auto-generate document number)
    created_document = await doc_repo.create_document(new_document)

    # Create audit trail entry
    await create_audit_entry(
        document_id=str(created_document["_id"]),
        action=DocumentAction.CREATED,
        user=current_user,
        comment=f"Document created: {document_data.title}"
    )

    # Create notifications for document creation
    if document_data.assigned_to_user_id:
        notification_service = NotificationService()
        email_service = EmailService()

        notifications = await notification_service.notify_document_created(
            document=created_document,
            assigned_user_id=document_data.assigned_to_user_id
        )

        # Send emails in background
        for notif in notifications:
            user = await user_repo.find_by_id(notif["user_id"])
            if user:
                background_tasks.add_task(
                    email_service.send_notification_email,
                    to_email=user["email"],
                    notification_type=notif["type"],
                    title=notif["title"],
                    message=notif["message"],
                    document_number=created_document.get("document_number"),
                    metadata=notif.get("metadata")
                )

    return convert_document_ids(created_document)


@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List Documents",
    description="Get a list of documents with optional filters",
    responses={
        200: {"description": "List of documents"},
        401: {"description": "Not authenticated"}
    }
)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = None,
    search: Optional[str] = None,
    assigned_to_me: bool = False,
    created_by_me: bool = False,
    current_user: dict = Depends(require_authenticated)
):
    """
    List documents with optional filtering

    - **Admins** can see all documents
    - **Department Heads** and **Employees** can see documents related to their department
    - All users can filter to see only documents assigned to them or created by them

    Filters:
    - **status**: Filter by document status
    - **search**: Search by title, description, or document number
    - **assigned_to_me**: Show only documents assigned to current user
    - **created_by_me**: Show only documents created by current user
    """
    doc_repo = DocumentRepository()

    # Check if user is admin
    is_admin = current_user.get("role") == UserRole.ADMIN.value

    # Handle specific user filters
    if assigned_to_me:
        documents = await doc_repo.find_assigned_to_user(
            user_id=str(current_user["_id"]),
            skip=skip,
            limit=limit,
            status=status.value if status else None
        )
    elif created_by_me:
        documents = await doc_repo.find_by_creator(
            creator_id=str(current_user["_id"]),
            skip=skip,
            limit=limit,
            status=status.value if status else None
        )
    elif search:
        # Search documents
        department_id = None if is_admin else str(current_user["department_id"])
        documents = await doc_repo.search_documents(
            search_query=search,
            department_id=department_id,
            skip=skip,
            limit=limit
        )
    elif is_admin:
        # Admin sees all documents
        filter_query = {}
        if status:
            filter_query["status"] = status.value

        documents = await doc_repo.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    else:
        # Non-admins see documents from their department
        documents = await doc_repo.find_by_department(
            department_id=str(current_user["department_id"]),
            skip=skip,
            limit=limit,
            status=status.value if status else None
        )

    # Convert ObjectIds to strings
    for doc in documents:
        convert_document_ids(doc)

    return documents


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document by ID",
    description="Get details of a specific document",
    responses={
        200: {"description": "Document details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this document"},
        404: {"description": "Document not found"}
    }
)
async def get_document(
    document_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get document by ID

    - **Admins** can view any document
    - **Others** can only view documents related to their department
    """
    doc_repo = DocumentRepository()
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

    # User can view if: admin, creator, or department is involved
    can_view = is_admin or is_creator or user_dept == doc_creator_dept or user_dept == doc_holder_dept

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this document"
        )

    # Create audit entry for viewing
    await create_audit_entry(
        document_id=document_id,
        action=DocumentAction.VIEWED,
        user=current_user
    )

    return convert_document_ids(document)


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update Document",
    description="Update document information",
    responses={
        200: {"description": "Document updated successfully"},
        400: {"description": "Invalid data"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to update this document"},
        404: {"description": "Document not found"}
    }
)
async def update_document(
    document_id: str,
    document_data: DocumentUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated)
):
    """
    Update a document

    Only the document creator or admins can update documents.
    Department heads can update documents in their department.
    """
    doc_repo = DocumentRepository()
    user_repo = UserRepository()

    # Check if document exists
    existing_doc = await doc_repo.find_by_id(document_id)
    if not existing_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_dept_head = current_user.get("role") == UserRole.DEPARTMENT_HEAD.value
    is_creator = str(existing_doc.get("creator_id")) == str(current_user["_id"])
    same_dept = str(existing_doc.get("current_holder_department_id")) == str(current_user["department_id"])

    can_update = is_admin or is_creator or (is_dept_head and same_dept)

    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this document"
        )

    # Track old assignment for notification
    old_assignee = existing_doc.get("assigned_to_user_id")

    # Prepare update data
    update_data = {}

    if document_data.title is not None:
        update_data["title"] = document_data.title

    if document_data.description is not None:
        update_data["description"] = document_data.description

    if document_data.document_type is not None:
        update_data["document_type"] = document_data.document_type.value

    if document_data.priority is not None:
        update_data["priority"] = document_data.priority.value

    if document_data.status is not None:
        update_data["status"] = document_data.status.value

    if document_data.assigned_to_user_id is not None:
        # Validate user exists
        user = await user_repo.find_by_id(document_data.assigned_to_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )
        update_data["assigned_to_user_id"] = document_data.assigned_to_user_id

    if document_data.metadata is not None:
        update_data["metadata"] = document_data.metadata.model_dump()

    # Update document
    updated_document = await doc_repo.update_by_id(document_id, update_data)

    if not updated_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Create audit trail entry
    await create_audit_entry(
        document_id=document_id,
        action=DocumentAction.MODIFIED,
        user=current_user,
        comment="Document updated"
    )

    # Create notification if assignment changed
    new_assignee = document_data.assigned_to_user_id
    if new_assignee and str(old_assignee) != str(new_assignee):
        notification_service = NotificationService()
        email_service = EmailService()

        notification = await notification_service.notify_document_assigned(
            document=updated_document,
            new_assignee_id=new_assignee,
            assigned_by_name=current_user.get("full_name", "Unknown")
        )

        if notification:
            user = await user_repo.find_by_id(new_assignee)
            if user:
                background_tasks.add_task(
                    email_service.send_notification_email,
                    to_email=user["email"],
                    notification_type=notification["type"],
                    title=notification["title"],
                    message=notification["message"],
                    document_number=updated_document.get("document_number"),
                    metadata=notification.get("metadata")
                )

    return convert_document_ids(updated_document)


@router.post(
    "/{document_id}/forward",
    response_model=DocumentResponse,
    summary="Forward Document",
    description="Forward a document to another department",
    responses={
        200: {"description": "Document forwarded successfully"},
        400: {"description": "Invalid department or user"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to forward this document"},
        404: {"description": "Document not found"}
    }
)
async def forward_document(
    document_id: str,
    forward_data: DocumentForward,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated)
):
    """
    Forward a document to another department

    Only admins, department heads, or the assigned user can forward documents.
    """
    doc_repo = DocumentRepository()
    dept_repo = DepartmentRepository()
    user_repo = UserRepository()

    # Check if document exists
    document = await doc_repo.find_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if target department exists
    target_dept = await dept_repo.find_by_id(forward_data.to_department_id)
    if not target_dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target department not found"
        )

    # Check if assigned user exists (if provided)
    if forward_data.assigned_to_user_id:
        assigned_user = await user_repo.find_by_id(forward_data.assigned_to_user_id)
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )
        # Check if user belongs to target department
        if str(assigned_user["department_id"]) != forward_data.to_department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user must belong to the target department"
            )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_dept_head = current_user.get("role") == UserRole.DEPARTMENT_HEAD.value
    is_assigned = str(document.get("assigned_to_user_id")) == str(current_user["_id"])
    same_dept = str(document.get("current_holder_department_id")) == str(current_user["department_id"])

    can_forward = is_admin or (is_dept_head and same_dept) or is_assigned

    if not can_forward:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to forward this document"
        )

    # Store the old department for audit trail
    from_department_id = str(document["current_holder_department_id"])

    # Forward the document
    updated_document = await doc_repo.forward_document(
        document_id=document_id,
        to_department_id=forward_data.to_department_id,
        assigned_to_user_id=forward_data.assigned_to_user_id
    )

    # Create audit trail entry
    await create_audit_entry(
        document_id=document_id,
        action=DocumentAction.FORWARDED,
        user=current_user,
        from_department_id=from_department_id,
        to_department_id=forward_data.to_department_id,
        comment=forward_data.comment
    )

    # Create notifications for document forwarding
    notification_service = NotificationService()
    email_service = EmailService()

    notifications = await notification_service.notify_document_forwarded(
        document=updated_document,
        from_department_id=from_department_id,
        to_department_id=forward_data.to_department_id,
        assigned_user_id=forward_data.assigned_to_user_id,
        forwarded_by_name=current_user.get("full_name", "Unknown")
    )

    # Send emails in background
    for notif in notifications:
        user = await user_repo.find_by_id(notif["user_id"])
        if user:
            background_tasks.add_task(
                email_service.send_notification_email,
                to_email=user["email"],
                notification_type=notif["type"],
                title=notif["title"],
                message=notif["message"],
                document_number=updated_document.get("document_number"),
                metadata=notif.get("metadata")
            )

    return convert_document_ids(updated_document)


@router.put(
    "/{document_id}/status",
    response_model=DocumentResponse,
    summary="Update Document Status",
    description="Update the status of a document",
    responses={
        200: {"description": "Status updated successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to update status"},
        404: {"description": "Document not found"}
    }
)
async def update_document_status(
    document_id: str,
    status_data: DocumentStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated)
):
    """
    Update document status

    Admins, department heads (for their dept), or assigned users can update status.
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
    is_dept_head = current_user.get("role") == UserRole.DEPARTMENT_HEAD.value
    is_assigned = str(document.get("assigned_to_user_id")) == str(current_user["_id"])
    same_dept = str(document.get("current_holder_department_id")) == str(current_user["department_id"])

    can_update_status = is_admin or (is_dept_head and same_dept) or is_assigned

    if not can_update_status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update document status"
        )

    # Store old status for audit
    old_status = document.get("status")

    # Update status
    updated_document = await doc_repo.update_status(
        document_id=document_id,
        new_status=status_data.status.value
    )

    # Create audit trail entry
    await create_audit_entry(
        document_id=document_id,
        action=DocumentAction.STATUS_CHANGED,
        user=current_user,
        old_status=old_status,
        new_status=status_data.status.value,
        status_reason=status_data.reason
    )

    # Create notifications for status change
    notification_service = NotificationService()
    email_service = EmailService()
    user_repo = UserRepository()

    notifications = await notification_service.notify_status_changed(
        document=updated_document,
        old_status=old_status,
        new_status=status_data.status.value,
        changed_by_name=current_user.get("full_name", "Unknown")
    )

    # Send emails in background
    for notif in notifications:
        user = await user_repo.find_by_id(notif["user_id"])
        if user:
            background_tasks.add_task(
                email_service.send_notification_email,
                to_email=user["email"],
                notification_type=notif["type"],
                title=notif["title"],
                message=notif["message"],
                document_number=updated_document.get("document_number"),
                metadata=notif.get("metadata")
            )

    return convert_document_ids(updated_document)


@router.get(
    "/{document_id}/history",
    response_model=List[DocumentHistoryResponse],
    summary="Get Document History",
    description="Get the complete audit trail for a document",
    responses={
        200: {"description": "Document history"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this document"},
        404: {"description": "Document not found"}
    }
)
async def get_document_history(
    document_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get complete audit trail for a document

    Returns all actions performed on the document in chronological order.
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

    can_view = is_admin or is_creator or user_dept == doc_creator_dept or user_dept == doc_holder_dept

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this document's history"
        )

    # Get history
    history = await history_repo.get_document_timeline(document_id)

    # Convert ObjectIds
    for entry in history:
        convert_history_ids(entry)

    return history


@router.delete(
    "/{document_id}",
    summary="Archive Document",
    description="Archive a document (soft delete)",
    responses={
        200: {"description": "Document archived successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to archive this document"},
        404: {"description": "Document not found"}
    }
)
async def archive_document(
    document_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Archive a document

    Only admins or the document creator can archive documents.
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
    is_creator = str(document.get("creator_id")) == str(current_user["_id"])

    if not (is_admin or is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to archive this document"
        )

    # Archive document
    await doc_repo.archive_document(document_id)

    # Create audit trail entry
    await create_audit_entry(
        document_id=document_id,
        action=DocumentAction.ARCHIVED,
        user=current_user,
        comment="Document archived"
    )

    return {
        "success": True,
        "message": f"Document {document.get('document_number')} archived successfully"
    }


@router.get(
    "/stats/overview",
    summary="Get Document Statistics",
    description="Get document statistics for the system or department",
    responses={
        200: {"description": "Document statistics"},
        401: {"description": "Not authenticated"}
    }
)
async def get_document_stats(
    current_user: dict = Depends(require_authenticated)
):
    """
    Get document statistics

    - **Admins** get stats for all documents
    - **Others** get stats for their department
    """
    doc_repo = DocumentRepository()

    is_admin = current_user.get("role") == UserRole.ADMIN.value
    department_id = None if is_admin else str(current_user["department_id"])

    stats = await doc_repo.get_document_stats(department_id=department_id)

    return stats
