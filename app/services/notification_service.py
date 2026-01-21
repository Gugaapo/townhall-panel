from typing import Dict, Any, List, Optional
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.utils.constants import NotificationType
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""

    def __init__(self):
        self.notification_repo = NotificationRepository()
        self.user_repo = UserRepository()
        self.dept_repo = DepartmentRepository()

    async def create_notification(
        self,
        user_id: str,
        document_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Create a notification for a user

        Args:
            user_id: User to notify
            document_id: Related document
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            metadata: Additional context

        Returns:
            Created notification
        """
        notification_data = {
            "user_id": user_id,
            "document_id": document_id,
            "type": notification_type.value,
            "title": title,
            "message": message,
            "is_read": False,
            "email_sent": False,
            "metadata": metadata or {}
        }

        return await self.notification_repo.create(notification_data)

    async def notify_document_created(
        self,
        document: Dict[str, Any],
        assigned_user_id: Optional[str] = None
    ):
        """
        Notify when a document is created

        Notifies:
        - Assigned user (if specified)

        Args:
            document: Document data
            assigned_user_id: Optional assigned user ID

        Returns:
            List of created notifications
        """
        notifications = []

        doc_title = document.get("title", "Untitled")
        doc_number = document.get("document_number", "N/A")
        document_id = str(document["_id"])

        # Notify assigned user
        if assigned_user_id:
            try:
                notif = await self.create_notification(
                    user_id=assigned_user_id,
                    document_id=document_id,
                    notification_type=NotificationType.DOCUMENT_RECEIVED,
                    title=f"New Document Assigned: {doc_number}",
                    message=f"You have been assigned document '{doc_title}' ({doc_number})",
                    metadata={"action": "assigned"}
                )
                notifications.append(notif)
            except Exception as e:
                logger.error(f"Failed to notify assigned user {assigned_user_id}: {e}")

        return notifications

    async def notify_document_forwarded(
        self,
        document: Dict[str, Any],
        from_department_id: str,
        to_department_id: str,
        assigned_user_id: Optional[str] = None,
        forwarded_by_name: str = "Unknown"
    ):
        """
        Notify when a document is forwarded

        Notifies:
        - Assigned user in target department (if specified)
        - All users in target department (if no specific user assigned)

        Args:
            document: Document data
            from_department_id: Source department ID
            to_department_id: Target department ID
            assigned_user_id: Optional assigned user ID
            forwarded_by_name: Name of user who forwarded

        Returns:
            List of created notifications
        """
        notifications = []

        doc_title = document.get("title", "Untitled")
        doc_number = document.get("document_number", "N/A")
        document_id = str(document["_id"])

        # Get target department name
        target_dept = await self.dept_repo.find_by_id(to_department_id)
        dept_name = target_dept.get("name", "Unknown Department") if target_dept else "Unknown Department"

        # If assigned to specific user, notify them
        if assigned_user_id:
            try:
                notif = await self.create_notification(
                    user_id=assigned_user_id,
                    document_id=document_id,
                    notification_type=NotificationType.DOCUMENT_FORWARDED,
                    title=f"Document Forwarded to You: {doc_number}",
                    message=f"'{doc_title}' has been forwarded to you by {forwarded_by_name}",
                    metadata={
                        "from_department_id": from_department_id,
                        "to_department_id": to_department_id,
                        "forwarded_by": forwarded_by_name
                    }
                )
                notifications.append(notif)
            except Exception as e:
                logger.error(f"Failed to notify assigned user {assigned_user_id}: {e}")
        else:
            # Notify all users in target department
            users = await self.user_repo.find_by_department(to_department_id)
            for user in users:
                if user.get("is_active", True):
                    try:
                        notif = await self.create_notification(
                            user_id=str(user["_id"]),
                            document_id=document_id,
                            notification_type=NotificationType.DOCUMENT_FORWARDED,
                            title=f"Document Forwarded to {dept_name}: {doc_number}",
                            message=f"'{doc_title}' has been forwarded to your department by {forwarded_by_name}",
                            metadata={
                                "from_department_id": from_department_id,
                                "to_department_id": to_department_id,
                                "forwarded_by": forwarded_by_name
                            }
                        )
                        notifications.append(notif)
                    except Exception as e:
                        logger.error(f"Failed to notify user {user['_id']}: {e}")

        return notifications

    async def notify_status_changed(
        self,
        document: Dict[str, Any],
        old_status: str,
        new_status: str,
        changed_by_name: str = "Unknown"
    ):
        """
        Notify when document status changes

        Notifies:
        - Document creator
        - Assigned user (if different from creator)

        Args:
            document: Document data
            old_status: Previous status
            new_status: New status
            changed_by_name: Name of user who changed status

        Returns:
            List of created notifications
        """
        notifications = []

        doc_title = document.get("title", "Untitled")
        doc_number = document.get("document_number", "N/A")
        document_id = str(document["_id"])
        creator_id = str(document.get("creator_id"))
        assigned_user_id = document.get("assigned_to_user_id")

        # Notify creator
        try:
            notif = await self.create_notification(
                user_id=creator_id,
                document_id=document_id,
                notification_type=NotificationType.STATUS_CHANGED,
                title=f"Status Changed: {doc_number}",
                message=f"Document '{doc_title}' status changed from {old_status} to {new_status} by {changed_by_name}",
                metadata={
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by": changed_by_name
                }
            )
            notifications.append(notif)
        except Exception as e:
            logger.error(f"Failed to notify creator {creator_id}: {e}")

        # Notify assigned user if different from creator
        if assigned_user_id and str(assigned_user_id) != creator_id:
            try:
                notif = await self.create_notification(
                    user_id=str(assigned_user_id),
                    document_id=document_id,
                    notification_type=NotificationType.STATUS_CHANGED,
                    title=f"Status Changed: {doc_number}",
                    message=f"Document '{doc_title}' status changed from {old_status} to {new_status} by {changed_by_name}",
                    metadata={
                        "old_status": old_status,
                        "new_status": new_status,
                        "changed_by": changed_by_name
                    }
                )
                notifications.append(notif)
            except Exception as e:
                logger.error(f"Failed to notify assigned user {assigned_user_id}: {e}")

        return notifications

    async def notify_document_assigned(
        self,
        document: Dict[str, Any],
        new_assignee_id: str,
        assigned_by_name: str = "Unknown"
    ):
        """
        Notify when document is assigned to a new user

        Args:
            document: Document data
            new_assignee_id: New assignee user ID
            assigned_by_name: Name of user who assigned

        Returns:
            Created notification or None if failed
        """
        doc_title = document.get("title", "Untitled")
        doc_number = document.get("document_number", "N/A")
        document_id = str(document["_id"])

        try:
            return await self.create_notification(
                user_id=new_assignee_id,
                document_id=document_id,
                notification_type=NotificationType.DOCUMENT_RECEIVED,
                title=f"Document Assigned to You: {doc_number}",
                message=f"You have been assigned document '{doc_title}' by {assigned_by_name}",
                metadata={"assigned_by": assigned_by_name}
            )
        except Exception as e:
            logger.error(f"Failed to notify new assignee {new_assignee_id}: {e}")
            return None
