from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from bson import ObjectId

from app.schemas.notification import NotificationResponse, NotificationUpdate
from app.db.repositories.notification_repository import NotificationRepository
from app.core.permissions import require_authenticated

router = APIRouter()


def convert_notification_ids(notif: dict) -> dict:
    """Convert ObjectIds to strings in notification"""
    if "_id" in notif and isinstance(notif["_id"], ObjectId):
        notif["_id"] = str(notif["_id"])
    if "user_id" in notif and isinstance(notif["user_id"], ObjectId):
        notif["user_id"] = str(notif["user_id"])
    if "document_id" in notif and isinstance(notif["document_id"], ObjectId):
        notif["document_id"] = str(notif["document_id"])
    return notif


@router.get(
    "",
    response_model=List[NotificationResponse],
    summary="List Notifications",
    description="Get current user's notifications with optional filters",
    responses={
        200: {"description": "List of notifications"},
        401: {"description": "Not authenticated"}
    }
)
async def list_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip (pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of notifications to return"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    current_user: dict = Depends(require_authenticated)
):
    """
    List notifications for the current user

    - **skip**: Number of notifications to skip (pagination)
    - **limit**: Maximum number of notifications to return
    - **is_read**: Filter by read/unread status
    """
    notification_repo = NotificationRepository()

    notifications = await notification_repo.find_by_user(
        user_id=str(current_user["_id"]),
        is_read=is_read,
        skip=skip,
        limit=limit
    )

    # Convert ObjectIds
    for notif in notifications:
        convert_notification_ids(notif)

    return notifications


@router.get(
    "/unread-count",
    summary="Get Unread Count",
    description="Get the count of unread notifications for current user",
    responses={
        200: {"description": "Unread notification count"},
        401: {"description": "Not authenticated"}
    }
)
async def get_unread_count(
    current_user: dict = Depends(require_authenticated)
):
    """
    Get count of unread notifications for the current user

    Useful for badge counts in UI
    """
    notification_repo = NotificationRepository()

    count = await notification_repo.count_unread(str(current_user["_id"]))

    return {"unread_count": count}


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark Notification as Read",
    description="Mark a specific notification as read",
    responses={
        200: {"description": "Notification marked as read"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Notification not found"}
    }
)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Mark a notification as read

    Users can only mark their own notifications as read
    """
    notification_repo = NotificationRepository()

    # Check if notification exists and belongs to user
    notification = await notification_repo.find_by_id(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Check ownership
    if str(notification["user_id"]) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this notification"
        )

    # Mark as read
    updated = await notification_repo.mark_as_read(notification_id)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to update notification"
        )

    return convert_notification_ids(updated)


@router.put(
    "/read-all",
    summary="Mark All as Read",
    description="Mark all notifications as read for current user",
    responses={
        200: {"description": "All notifications marked as read"},
        401: {"description": "Not authenticated"}
    }
)
async def mark_all_read(
    current_user: dict = Depends(require_authenticated)
):
    """
    Mark all notifications as read for the current user
    """
    notification_repo = NotificationRepository()

    updated_count = await notification_repo.mark_all_as_read(str(current_user["_id"]))

    return {
        "success": True,
        "message": f"{updated_count} notifications marked as read"
    }


@router.delete(
    "/{notification_id}",
    summary="Delete Notification",
    description="Delete a specific notification",
    responses={
        200: {"description": "Notification deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Notification not found"}
    }
)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Delete a notification

    Users can only delete their own notifications
    """
    notification_repo = NotificationRepository()

    # Check if notification exists and belongs to user
    notification = await notification_repo.find_by_id(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Check ownership
    if str(notification["user_id"]) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this notification"
        )

    # Delete
    deleted = await notification_repo.delete_by_id(notification_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to delete notification"
        )

    return {
        "success": True,
        "message": "Notification deleted successfully"
    }
