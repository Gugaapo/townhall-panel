"""Admin views for collections."""

from app.admin.views.user_view import UserView
from app.admin.views.department_view import DepartmentView
from app.admin.views.document_view import DocumentView
from app.admin.views.document_history_view import DocumentHistoryView
from app.admin.views.notification_view import NotificationView

__all__ = [
    "UserView",
    "DepartmentView",
    "DocumentView",
    "DocumentHistoryView",
    "NotificationView",
]
