from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user import UserLogin, Token, TokenRefresh, UserResponse, UserCreate
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.permissions import get_current_active_user, require_admin
from app.utils.constants import UserRole

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens",
    responses={
        200: {
            "description": "Successfully authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {"description": "Invalid credentials"}
    }
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint to authenticate users

    - **username**: User email address
    - **password**: User password

    Returns JWT access token and refresh token
    """
    user_repo = UserRepository()

    # Find user by email
    user = await user_repo.find_by_email(form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "department_id": str(user["department_id"])
        }
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"]
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new user (admin only)",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email already exists or invalid data"},
        403: {"description": "Not authorized"}
    }
)
async def register(
    user_data: UserCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Register a new user in the system

    **Admin only endpoint**

    - **email**: User email address (must be unique)
    - **full_name**: User's full name
    - **password**: User password (minimum 6 characters)
    - **department_id**: ID of the department the user belongs to
    - **role**: User role (admin, department_head, employee)
    """
    user_repo = UserRepository()
    dept_repo = DepartmentRepository()

    # Check if email already exists
    if await user_repo.email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if department exists
    department = await dept_repo.find_by_id(user_data.department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department not found"
        )

    # Create user
    new_user = {
        "email": user_data.email.lower(),
        "password_hash": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "department_id": user_data.department_id,
        "role": user_data.role.value,
        "is_active": True
    }

    created_user = await user_repo.create(new_user)

    return created_user


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh Access Token",
    description="Get a new access token using a refresh token",
    responses={
        200: {"description": "New tokens generated successfully"},
        401: {"description": "Invalid or expired refresh token"}
    }
)
async def refresh_token(token_data: TokenRefresh):
    """
    Refresh access token

    Use a valid refresh token to get a new access token and refresh token.

    - **refresh_token**: Valid refresh token from login
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get user from database
    user_repo = UserRepository()
    user = await user_repo.find_by_id(user_id)

    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    access_token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "department_id": str(user["department_id"])
        }
    )

    new_refresh_token = create_refresh_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"]
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get the currently authenticated user's information",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated"}
    }
)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """
    Get current authenticated user information

    Returns the profile of the currently logged-in user.

    Requires authentication token in the Authorization header.
    """
    return current_user


@router.post(
    "/logout",
    summary="User Logout",
    description="Logout the current user (client should discard tokens)",
    responses={
        200: {"description": "Successfully logged out"}
    }
)
async def logout(current_user: dict = Depends(get_current_active_user)):
    """
    Logout endpoint

    Note: With JWT tokens, the actual logout is handled client-side by
    discarding the tokens. This endpoint is provided for consistency
    and can be extended to implement token blacklisting if needed.
    """
    return {
        "success": True,
        "message": "Successfully logged out. Please discard your tokens."
    }


@router.post(
    "/change-password",
    summary="Change Password",
    description="Change the current user's password",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid current password"},
        401: {"description": "Not authenticated"}
    }
)
async def change_password(
    current_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Change password for the current user

    Requires:
    - **current_password**: Current password for verification
    - **new_password**: New password (minimum 6 characters)

    The user must be authenticated to use this endpoint.
    """
    from pydantic import Field
    from app.schemas.user import UserBase

    # Validate new password length
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )

    user_repo = UserRepository()

    # Get fresh user data from database
    user = await user_repo.find_by_id(str(current_user["_id"]))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_password_hash = get_password_hash(new_password)

    # Update password
    await user_repo.update_by_id(
        str(current_user["_id"]),
        {"password_hash": new_password_hash}
    )

    return {
        "success": True,
        "message": "Password changed successfully"
    }
