"""
Document-specific admin actions.

Contains action functions that can be reused across views.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.db.repositories.user_repository import UserRepository
from app.utils.constants import DocumentAction, DocumentStatus, NotificationType


class DocumentActionService:
    """Service for executing document actions with proper history and notifications."""

    def __init__(self):
        self.document_repo = DocumentRepository()
        self.history_repo = DocumentHistoryRepository()
        self.notification_repo = NotificationRepository()
        self.department_repo = DepartmentRepository()
        self.user_repo = UserRepository()

    async def forward_document(
        self,
        document_id: str,
        to_department_id: str,
        assigned_to_user_id: Optional[str],
        comment: str,
        performed_by_id: str,
        performed_by_name: str,
    ) -> Dict[str, Any]:
        """
        Forward a document to another department.

        Args:
            document_id: Document ID to forward
            to_department_id: Target department ID
            assigned_to_user_id: Optional user to assign to
            comment: Comment/reason for forwarding
            performed_by_id: User ID performing the action
            performed_by_name: User name performing the action

        Returns:
            Updated document
        """
        # Get current document
        document = await self.document_repo.find_by_id(document_id)
        if not document:
            raise ValueError("Document not found")

        from_department_id = document.get("current_holder_department_id")

        # Forward the document
        updated_doc = await self.document_repo.forward_document(
            document_id,
            to_department_id,
            assigned_to_user_id,
        )

        if not updated_doc:
            raise ValueError("Failed to forward document")

        # Get department names for history
        from_dept = await self.department_repo.find_by_id(from_department_id) if from_department_id else None
        to_dept = await self.department_repo.find_by_id(to_department_id)

        from_dept_name = from_dept.get("name", "Unknown") if from_dept else "Unknown"
        to_dept_name = to_dept.get("name", "Unknown") if to_dept else "Unknown"

        # Create history entry
        history_data = {
            "document_id": document_id,
            "document_number": document.get("document_number", "Unknown"),
            "action": DocumentAction.FORWARDED.value,
            "performed_by": performed_by_id,
            "performed_by_name": performed_by_name,
            "from_department_id": from_department_id,
            "to_department_id": to_department_id,
            "details": {
                "comment": comment,
                "from_department_name": from_dept_name,
                "to_department_name": to_dept_name,
            },
        }
        await self.history_repo.create_history_entry(history_data)

        # Create notifications for target department users
        await self._notify_department_users(
            department_id=to_department_id,
            notification_type=NotificationType.DOCUMENT_FORWARDED.value,
            title="Document Forwarded to Your Department",
            message=f"Document '{document.get('title', 'Untitled')}' "
                    f"({document.get('document_number', 'Unknown')}) "
                    f"has been forwarded from {from_dept_name}.",
            document_id=document_id,
        )

        # Notify assigned user specifically if provided
        if assigned_to_user_id:
            await self._create_notification(
                user_id=assigned_to_user_id,
                notification_type=NotificationType.DOCUMENT_RECEIVED.value,
                title="Document Assigned to You",
                message=f"Document '{document.get('title', 'Untitled')}' "
                        f"({document.get('document_number', 'Unknown')}) "
                        f"has been assigned to you.",
                document_id=document_id,
            )

        return updated_doc

    async def change_status(
        self,
        document_id: str,
        new_status: str,
        reason: str,
        performed_by_id: str,
        performed_by_name: str,
    ) -> Dict[str, Any]:
        """
        Change document status with proper history and notifications.

        Args:
            document_id: Document ID
            new_status: New status value
            reason: Reason for status change
            performed_by_id: User ID performing the action
            performed_by_name: User name performing the action

        Returns:
            Updated document
        """
        # Get current document
        document = await self.document_repo.find_by_id(document_id)
        if not document:
            raise ValueError("Document not found")

        old_status = document.get("status")

        # Update status
        updated_doc = await self.document_repo.update_status(
            document_id, new_status
        )

        if not updated_doc:
            raise ValueError("Failed to update document status")

        # Create history entry
        history_data = {
            "document_id": document_id,
            "document_number": document.get("document_number", "Unknown"),
            "action": DocumentAction.STATUS_CHANGED.value,
            "performed_by": performed_by_id,
            "performed_by_name": performed_by_name,
            "details": {
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            },
        }
        await self.history_repo.create_history_entry(history_data)

        # Notify creator
        creator_id = document.get("creator_id")
        if creator_id:
            await self._create_notification(
                user_id=creator_id,
                notification_type=NotificationType.STATUS_CHANGED.value,
                title="Document Status Changed",
                message=f"Document '{document.get('title', 'Untitled')}' "
                        f"status changed from '{old_status}' to '{new_status}'.",
                document_id=document_id,
            )

        # Notify assigned user if different from creator
        assigned_user_id = document.get("assigned_to_user_id")
        if assigned_user_id and assigned_user_id != creator_id:
            await self._create_notification(
                user_id=assigned_user_id,
                notification_type=NotificationType.STATUS_CHANGED.value,
                title="Document Status Changed",
                message=f"Document '{document.get('title', 'Untitled')}' "
                        f"status changed to '{new_status}'.",
                document_id=document_id,
            )

        return updated_doc

    async def archive_document(
        self,
        document_id: str,
        reason: str,
        performed_by_id: str,
        performed_by_name: str,
    ) -> Dict[str, Any]:
        """
        Archive a document with proper history and notifications.

        Args:
            document_id: Document ID
            reason: Reason for archiving
            performed_by_id: User ID performing the action
            performed_by_name: User name performing the action

        Returns:
            Updated document
        """
        # Get current document
        document = await self.document_repo.find_by_id(document_id)
        if not document:
            raise ValueError("Document not found")

        # Archive the document
        updated_doc = await self.document_repo.archive_document(document_id)

        if not updated_doc:
            raise ValueError("Failed to archive document")

        # Create history entry
        history_data = {
            "document_id": document_id,
            "document_number": document.get("document_number", "Unknown"),
            "action": DocumentAction.ARCHIVED.value,
            "performed_by": performed_by_id,
            "performed_by_name": performed_by_name,
            "details": {
                "reason": reason,
            },
        }
        await self.history_repo.create_history_entry(history_data)

        # Notify creator
        creator_id = document.get("creator_id")
        if creator_id:
            await self._create_notification(
                user_id=creator_id,
                notification_type=NotificationType.STATUS_CHANGED.value,
                title="Document Archived",
                message=f"Document '{document.get('title', 'Untitled')}' "
                        f"({document.get('document_number', 'Unknown')}) "
                        f"has been archived.",
                document_id=document_id,
            )

        return updated_doc

    async def _create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        document_id: Optional[str] = None,
    ):
        """Create a notification for a user."""
        notification_data = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "document_id": document_id,
            "is_read": False,
            "email_sent": False,
        }
        await self.notification_repo.create(notification_data)

    async def _notify_department_users(
        self,
        department_id: str,
        notification_type: str,
        title: str,
        message: str,
        document_id: Optional[str] = None,
    ):
        """Create notifications for all users in a department."""
        users = await self.user_repo.find_by_department(department_id)

        for user in users:
            user_id = str(user.get("_id"))
            await self._create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                document_id=document_id,
            )


# Singleton instance for use in views
document_action_service = DocumentActionService()
