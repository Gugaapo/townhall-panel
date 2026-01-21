"""
Admin authentication provider for Starlette-Admin.

Integrates with existing JWT authentication and enforces admin role.
"""

import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminUser, AuthProvider

from app.core.security import verify_password
from app.db.repositories.user_repository import UserRepository
from app.utils.constants import UserRole

logger = logging.getLogger(__name__)


class AdminAuthProvider(AuthProvider):
    """
    Custom authentication provider for Starlette-Admin.

    Uses existing security module and only allows admin users.
    Session-based authentication for admin panel.
    """

    def __init__(self):
        super().__init__(
            login_path="/login",
            logout_path="/logout",
        )
        self.user_repository = UserRepository()

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        """
        Authenticate admin user.

        Args:
            username: Email address
            password: Plain text password
            remember_me: Whether to remember the session
            request: Starlette request
            response: Starlette response

        Returns:
            Response with session cookie set on success
        """
        try:
            # Find user by email
            user = await self.user_repository.find_by_email(username)

            if not user:
                logger.warning(f"Admin login failed: user not found - {username}")
                return response

            # Verify password (field can be password_hash or hashed_password)
            password_field = user.get("hashed_password") or user.get("password_hash", "")
            if not verify_password(password, password_field):
                logger.warning(f"Admin login failed: invalid password - {username}")
                return response

            # Check if user is active
            if not user.get("is_active", False):
                logger.warning(
                    f"Admin login failed: user inactive - {username}"
                )
                return response

            # Check if user is admin
            if user.get("role") != UserRole.ADMIN.value:
                logger.warning(
                    f"Admin login failed: not an admin - {username} "
                    f"(role: {user.get('role')})"
                )
                return response

            # Store user info in session
            request.session.update({
                "admin_user_id": str(user["_id"]),
                "admin_email": user["email"],
                "admin_name": user.get("full_name", user["email"]),
                "admin_role": user["role"],
            })

            logger.info(f"Admin login successful: {username}")

            return response

        except Exception as e:
            logger.error(f"Admin login error: {e}")
            return response

    async def is_authenticated(self, request: Request) -> bool:
        """
        Check if the current request is authenticated.

        Args:
            request: Starlette request

        Returns:
            True if authenticated as admin, False otherwise
        """
        try:
            user_id = request.session.get("admin_user_id")

            if not user_id:
                return False

            # Verify user still exists and is admin
            user = await self.user_repository.find_by_id(user_id)

            if not user:
                logger.warning(f"Admin session invalid: user not found - {user_id}")
                return False

            if not user.get("is_active", False):
                logger.warning(f"Admin session invalid: user inactive - {user_id}")
                return False

            if user.get("role") != UserRole.ADMIN.value:
                logger.warning(f"Admin session invalid: not admin - {user_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Admin authentication check error: {e}")
            return False

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        """
        Get the current admin user from session.

        Args:
            request: Starlette request

        Returns:
            AdminUser object if authenticated, None otherwise
        """
        user_id = request.session.get("admin_user_id")

        if not user_id:
            return None

        return AdminUser(
            username=request.session.get("admin_email", "admin"),
            photo_url=None,
        )

    async def logout(
        self,
        request: Request,
        response: Response,
    ) -> Response:
        """
        Log out the admin user.

        Args:
            request: Starlette request
            response: Starlette response

        Returns:
            Response with session cleared
        """
        email = request.session.get("admin_email", "unknown")

        # Clear admin session data
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_email", None)
        request.session.pop("admin_name", None)
        request.session.pop("admin_role", None)

        logger.info(f"Admin logout: {email}")

        return response
