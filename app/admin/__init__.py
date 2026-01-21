"""Admin panel module using Starlette-Admin with custom Motor provider."""

from app.admin.admin_app import create_admin_app

__all__ = ["create_admin_app"]
