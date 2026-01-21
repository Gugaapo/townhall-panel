"""
Notification management view for admin panel.

Provides notification viewing and admin broadcast capabilities.
"""

from typing import Any, Dict, List, Optional, Sequence

from starlette.requests import Request
from starlette_admin import (
    StringField,
    TextAreaField,
    BooleanField,
    DateTimeField,
    EnumField,
    action,
)

from app.admin.providers.base_motor_model_view import BaseMotorModelView
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.user_repository import UserRepository
from app.utils.constants import NotificationType


class NotificationView(BaseMotorModelView):
    """Admin view for notification management."""

    # Identity
    identity = "notifications"
    name = "Notification"
    label = "Notifications"
    icon = "fa fa-bell"

    # Repository
    repository = NotificationRepository()

    # Fields configuration
    fields = [
        StringField(
            "_id",
            label="ID",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "title",
            label="Title",
            required=True,
            searchable=True,
        ),
        TextAreaField(
            "message",
            label="Message",
            required=True,
            searchable=True,
        ),
        EnumField(
            "type",
            label="Type",
            enum=NotificationType,
            required=True,
        ),
        StringField(
            "user_id",
            label="User ID",
            exclude_from_list=True,
        ),
        StringField(
            "user_name",
            label="Recipient",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "document_id",
            label="Document ID",
            required=False,
        ),
        StringField(
            "link",
            label="Link",
            required=False,
        ),
        BooleanField(
            "is_read",
            label="Read",
        ),
        BooleanField(
            "email_sent",
            label="Email Sent",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        DateTimeField(
            "read_at",
            label="Read At",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        DateTimeField(
            "created_at",
            label="Created At",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        DateTimeField(
            "updated_at",
            label="Updated At",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
    ]

    # List configuration
    fields_default_sort = [("created_at", True)]  # Descending (most recent first)

    # Pagination
    page_size = 50

    def __init__(self):
        super().__init__(repository=NotificationRepository())
        self.user_repository = UserRepository()

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """Build search filter for notifications."""
        return {
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"message": {"$regex": search_term, "$options": "i"}},
            ]
        }

    async def _resolve_names(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve user ID to display name."""
        if notification.get("user_id"):
            user = await self.user_repository.find_by_id(notification["user_id"])
            notification["user_name"] = (
                user.get("full_name", "Unknown") if user else "Unknown"
            )
        else:
            notification["user_name"] = "N/A"

        return notification

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """Find all notifications with user name resolution."""
        notifications = await super().find_all(request, skip, limit, where, order_by)

        # Resolve names for each notification
        resolved = []
        for notification in notifications:
            resolved.append(await self._resolve_names(notification))

        return resolved

    async def find_by_pk(self, request: Request, pk: Any) -> Optional[Any]:
        """Find notification by ID with user name resolution."""
        notification = await super().find_by_pk(request, pk)

        if notification:
            notification = await self._resolve_names(notification)

        return notification

    # Custom actions
    @action(
        name="mark_as_read",
        text="Mark as Read",
        confirmation="Mark selected notifications as read?",
        submit_btn_text="Mark Read",
        submit_btn_class="btn-success",
    )
    async def mark_as_read_action(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk mark notifications as read."""
        count = 0
        for pk in pks:
            result = await self.repository.mark_as_read(str(pk))
            if result:
                count += 1

        return f"Successfully marked {count} notification(s) as read."

    @action(
        name="mark_as_unread",
        text="Mark as Unread",
        confirmation="Mark selected notifications as unread?",
        submit_btn_text="Mark Unread",
        submit_btn_class="btn-warning",
    )
    async def mark_as_unread_action(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk mark notifications as unread."""
        count = 0
        for pk in pks:
            result = await self.repository.update_by_id(
                str(pk),
                {"is_read": False, "read_at": None}
            )
            if result:
                count += 1

        return f"Successfully marked {count} notification(s) as unread."

    @action(
        name="broadcast_notification",
        text="Broadcast to All Users",
        confirmation="This will create a notification for ALL active users. Continue?",
        submit_btn_text="Broadcast",
        submit_btn_class="btn-primary",
        form="""
        <form>
            <div class="mb-3">
                <label class="form-label">Title</label>
                <input type="text" name="broadcast_title" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Message</label>
                <textarea name="broadcast_message" class="form-control" rows="3" required></textarea>
            </div>
        </form>
        """,
    )
    async def broadcast_notification(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Create a notification for all active users (admin broadcast)."""
        # Get form data
        form_data = await request.form()
        title = form_data.get("broadcast_title", "Admin Announcement")
        message = form_data.get("broadcast_message", "")

        if not message:
            return "Message cannot be empty."

        # Get all active users
        active_users = await self.user_repository.find_active_users(
            skip=0, limit=10000
        )

        from bson import ObjectId

        count = 0
        for user in active_users:
            # Get user ID, handling both dict and ObjectId
            user_id = user.get("_id") if isinstance(user, dict) else user._id
            if isinstance(user_id, ObjectId):
                user_id = str(user_id)

            notification_data = {
                "title": title,
                "message": message,
                "type": "deadline_approaching",  # Using a generic type
                "user_id": user_id,
                "is_read": False,
                "email_sent": False,
            }
            await self.repository.create(notification_data)
            count += 1

        return f"Successfully broadcast notification to {count} user(s)."
