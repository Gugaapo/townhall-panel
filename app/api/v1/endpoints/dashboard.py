from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.db.repositories.notification_repository import NotificationRepository
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


@router.get(
    "/stats",
    summary="Get Dashboard Statistics",
    description="Get statistics for current user or department",
    responses={
        200: {"description": "Dashboard statistics"},
        401: {"description": "Not authenticated"}
    }
)
async def get_dashboard_stats(
    current_user: dict = Depends(require_authenticated)
):
    """
    Get dashboard statistics

    Returns:
    - Document counts by status
    - Documents assigned to user
    - Documents created by user
    - Unread notifications count
    - Upcoming deadlines
    """
    doc_repo = DocumentRepository()
    notification_repo = NotificationRepository()

    user_id = str(current_user["_id"])
    department_id = str(current_user["department_id"])
    is_admin = current_user.get("role") == UserRole.ADMIN.value

    # Get document stats for department (or all for admin)
    dept_stats = await doc_repo.get_document_stats(
        department_id=None if is_admin else department_id
    )

    # Get documents assigned to user
    assigned_docs = await doc_repo.find_assigned_to_user(
        user_id=user_id,
        limit=1000  # Get all for counting
    )
    assigned_by_status = {}
    for doc in assigned_docs:
        status = doc.get("status", "unknown")
        assigned_by_status[status] = assigned_by_status.get(status, 0) + 1

    # Get documents created by user
    created_docs = await doc_repo.find_by_creator(
        creator_id=user_id,
        limit=1000
    )
    created_count = len(created_docs)

    # Get unread notifications count
    unread_notifications = await notification_repo.count_unread(user_id)

    # Get documents with upcoming deadlines (next 7 days)
    upcoming_deadline_docs = []
    now = datetime.now(timezone.utc)
    seven_days_later = now + timedelta(days=7)

    for doc in assigned_docs:
        deadline = doc.get("metadata", {}).get("deadline")
        if deadline:
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                except ValueError:
                    continue
            if now < deadline <= seven_days_later:
                upcoming_deadline_docs.append(doc)

    return {
        "department_stats": dept_stats,
        "assigned_to_me": {
            "total": len(assigned_docs),
            "by_status": assigned_by_status
        },
        "created_by_me": created_count,
        "unread_notifications": unread_notifications,
        "upcoming_deadlines": len(upcoming_deadline_docs)
    }


@router.get(
    "/recent-activity",
    summary="Get Recent Activity",
    description="Get recent document activity for current user",
    responses={
        200: {"description": "Recent activity feed"},
        401: {"description": "Not authenticated"}
    }
)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent documents to return"),
    current_user: dict = Depends(require_authenticated)
):
    """
    Get recent document activity

    Returns recent documents the user is involved with:
    - Documents created by user
    - Documents assigned to user
    - Documents in user's department
    """
    doc_repo = DocumentRepository()
    history_repo = DocumentHistoryRepository()

    user_id = str(current_user["_id"])

    # Get recent documents user is involved with
    recent_docs = []

    # Documents assigned to user
    assigned = await doc_repo.find_assigned_to_user(
        user_id=user_id,
        limit=limit,
    )
    recent_docs.extend(assigned)

    # Documents created by user (if not already included)
    created = await doc_repo.find_by_creator(
        creator_id=user_id,
        limit=limit,
    )
    for doc in created:
        if doc not in recent_docs:
            recent_docs.append(doc)

    # Sort by updated_at and limit
    recent_docs.sort(key=lambda x: x.get("updated_at", x.get("created_at")), reverse=True)
    recent_docs = recent_docs[:limit]

    # For each document, get latest activity
    activity_feed = []
    for doc in recent_docs:
        doc_id = str(doc["_id"])

        # Get latest history entry
        history = await history_repo.get_document_timeline(doc_id)
        latest_action = history[-1] if history else None

        activity_item = {
            "document": convert_document_ids(doc),
            "latest_action": {
                "action": latest_action.get("action") if latest_action else "created",
                "performed_by_name": latest_action.get("performed_by_name") if latest_action else "System",
                "timestamp": latest_action.get("timestamp") if latest_action else doc.get("created_at")
            }
        }
        activity_feed.append(activity_item)

    return activity_feed


@router.get(
    "/pending-actions",
    summary="Get Pending Actions",
    description="Get documents requiring action from current user",
    responses={
        200: {"description": "Pending actions list"},
        401: {"description": "Not authenticated"}
    }
)
async def get_pending_actions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of pending documents"),
    current_user: dict = Depends(require_authenticated)
):
    """
    Get pending actions for current user

    Returns:
    - Documents assigned to user with status pending or in_progress
    - Documents with approaching deadlines
    """
    doc_repo = DocumentRepository()
    user_id = str(current_user["_id"])

    # Get documents assigned to user that need action
    pending_statuses = ["pending", "in_progress"]
    pending_docs = []

    for status in pending_statuses:
        docs = await doc_repo.find_assigned_to_user(
            user_id=user_id,
            status=status,
            limit=limit
        )
        pending_docs.extend(docs)

    # Sort by priority (urgent first) and deadline
    def sort_key(doc):
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        priority = priority_order.get(doc.get("priority", "medium"), 2)

        deadline = doc.get("metadata", {}).get("deadline")
        if deadline:
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    deadline_timestamp = deadline.timestamp()
                except ValueError:
                    deadline_timestamp = float('inf')
            else:
                deadline_timestamp = deadline.timestamp() if hasattr(deadline, 'timestamp') else float('inf')
        else:
            deadline_timestamp = float('inf')

        return (priority, deadline_timestamp)

    pending_docs.sort(key=sort_key)
    pending_docs = pending_docs[:limit]

    # Convert IDs
    for doc in pending_docs:
        convert_document_ids(doc)

    # Add deadline warning flag
    now = datetime.now(timezone.utc)
    for doc in pending_docs:
        deadline = doc.get("metadata", {}).get("deadline")
        if deadline:
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                except ValueError:
                    doc["deadline_warning"] = False
                    continue
            days_until_deadline = (deadline - now).days
            doc["deadline_warning"] = days_until_deadline <= 3
        else:
            doc["deadline_warning"] = False

    return pending_docs


@router.get(
    "/deadline-reminders",
    summary="Get Deadline Reminders",
    description="Get documents with upcoming deadlines",
    responses={
        200: {"description": "Documents with deadlines"},
        401: {"description": "Not authenticated"}
    }
)
async def get_deadline_reminders(
    days: int = Query(7, ge=1, le=30, description="Days ahead to check"),
    current_user: dict = Depends(require_authenticated)
):
    """
    Get documents with deadlines in the next N days

    Returns documents assigned to user with deadlines approaching
    """
    doc_repo = DocumentRepository()
    user_id = str(current_user["_id"])

    # Get all assigned documents
    assigned_docs = await doc_repo.find_assigned_to_user(
        user_id=user_id,
        limit=1000
    )

    # Filter by deadline
    now = datetime.now(timezone.utc)
    future_date = now + timedelta(days=days)

    deadline_docs = []
    for doc in assigned_docs:
        # Skip completed or archived
        if doc.get("status") in ["completed", "archived"]:
            continue

        deadline = doc.get("metadata", {}).get("deadline")
        if deadline:
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                except ValueError:
                    continue

            if now < deadline <= future_date:
                doc["days_until_deadline"] = (deadline - now).days
                doc["hours_until_deadline"] = int((deadline - now).total_seconds() / 3600)
                convert_document_ids(doc)
                deadline_docs.append(doc)

    # Sort by deadline (soonest first)
    deadline_docs.sort(key=lambda x: x.get("metadata", {}).get("deadline", ""))

    return deadline_docs
