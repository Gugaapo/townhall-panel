"""
Main admin application setup for Starlette-Admin.

Creates and configures the admin panel with all views and authentication.
"""

import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import BaseAdmin

from app.admin.auth import AdminAuthProvider
from app.admin.views.user_view import UserView
from app.admin.views.department_view import DepartmentView
from app.admin.views.document_view import DocumentView
from app.admin.views.document_history_view import DocumentHistoryView
from app.admin.views.notification_view import NotificationView

logger = logging.getLogger(__name__)


def create_admin_app(
    title: str = "Townhall Admin Panel",
    base_url: str = "/admin",
) -> BaseAdmin:
    """
    Create and configure the Starlette-Admin application.

    Args:
        title: Admin panel title
        base_url: Base URL for admin routes

    Returns:
        Configured Admin instance
    """
    # Create admin instance with authentication
    admin = BaseAdmin(
        title=title,
        base_url=base_url,
        auth_provider=AdminAuthProvider(),
    )

    # Add views (order matters for menu)
    admin.add_view(UserView())
    admin.add_view(DepartmentView())
    admin.add_view(DocumentView())
    admin.add_view(DocumentHistoryView())
    admin.add_view(NotificationView())

    logger.info(f"Admin panel created at {base_url}")

    return admin
