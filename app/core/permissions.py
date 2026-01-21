from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from functools import wraps

from app.core.security import verify_token
from app.utils.constants import UserRole
from app.db.repositories.user_repository import UserRepository
from bson import ObjectId

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Get the current authenticated user from JWT token

    Args:
        token: JWT token from Authorization header

    Returns:
        User data from database

    Raises:
        HTTPException: If token is invalid or user not found
    """
    import logging
    logger = logging.getLogger(__name__)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    payload = verify_token(token)
    if payload is None:
        logger.error("Token verification failed")
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        logger.error("No 'sub' in token payload")
        raise credentials_exception

    logger.info(f"Looking up user with ID: {user_id}")

    # Get user from database
    user_repo = UserRepository()
    user = await user_repo.find_by_id(user_id)

    if user is None:
        logger.error(f"User not found with ID: {user_id}")
        raise credentials_exception

    logger.info(f"User found: {user.get('email')}")

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Convert ObjectIds to strings for JSON serialization
    if "_id" in user and isinstance(user["_id"], ObjectId):
        user["_id"] = str(user["_id"])
    if "department_id" in user and isinstance(user["department_id"], ObjectId):
        user["department_id"] = str(user["department_id"])

    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Active user data

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency class to check user roles"""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_active_user)) -> dict:
        user_role = current_user.get("role")

        if user_role not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}"
            )

        return current_user


class DepartmentAccessChecker:
    """Dependency class to check department access"""

    def __init__(self, allow_admin: bool = True):
        self.allow_admin = allow_admin

    def __call__(
        self,
        department_id: str,
        current_user: dict = Depends(get_current_active_user)
    ) -> dict:
        user_role = current_user.get("role")
        user_department_id = str(current_user.get("department_id"))

        # Admins have access to all departments
        if self.allow_admin and user_role == UserRole.ADMIN.value:
            return current_user

        # Check if user belongs to the department
        if user_department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You don't have access to this department"
            )

        return current_user


# Convenience functions for common role checks
def require_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require admin role"""
    return RoleChecker([UserRole.ADMIN])(current_user)


def require_department_head(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require department head or admin role"""
    return RoleChecker([UserRole.ADMIN, UserRole.DEPARTMENT_HEAD])(current_user)


def require_authenticated(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require any authenticated user"""
    return current_user
