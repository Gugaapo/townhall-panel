from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from bson import ObjectId

from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.core.security import get_password_hash
from app.core.permissions import require_admin, require_authenticated
from app.utils.constants import UserRole

router = APIRouter()


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List Users",
    description="Get a list of users with optional filters (admins see all, others see their department)",
    responses={
        200: {"description": "List of users"},
        401: {"description": "Not authenticated"}
    }
)
async def list_users(
    skip: int = 0,
    limit: int = 20,
    department_id: str = None,
    role: UserRole = None,
    is_active: bool = None,
    search: str = None,
    current_user: dict = Depends(require_authenticated)
):
    """
    List users with optional filtering

    - **Admins** can see all users and use all filters
    - **Department Heads** and **Employees** can only see users in their department

    Filters:
    - **department_id**: Filter by department
    - **role**: Filter by role (admin, department_head, employee)
    - **is_active**: Filter by active status
    - **search**: Search by name or email (case-insensitive)
    """
    user_repo = UserRepository()

    # Build filter query
    query_filter = {}

    # Check permissions and apply department filter
    if current_user.get("role") == UserRole.ADMIN.value:
        # Admins can filter by any department
        if department_id:
            query_filter["department_id"] = department_id
    else:
        # Others can only see their department
        query_filter["department_id"] = current_user.get("department_id")

    # Apply role filter
    if role:
        query_filter["role"] = role.value

    # Apply active status filter
    if is_active is not None:
        query_filter["is_active"] = is_active
    else:
        # Default to active users only
        query_filter["is_active"] = True

    # Apply search filter
    if search:
        # Search in name or email using regex
        query_filter["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    # Get users with filters
    users = await user_repo.find_many(
        filter=query_filter,
        skip=skip,
        limit=limit,
        sort=[("created_at", -1)]
    )

    # Convert ObjectIds to strings
    for user in users:
        if "_id" in user and isinstance(user["_id"], ObjectId):
            user["_id"] = str(user["_id"])
        if "department_id" in user and isinstance(user["department_id"], ObjectId):
            user["department_id"] = str(user["department_id"])

    return users


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID",
    description="Get details of a specific user",
    responses={
        200: {"description": "User details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this user"},
        404: {"description": "User not found"}
    }
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get user by ID

    - **Admins** can view any user
    - **Others** can only view users in their department or themselves
    """
    user_repo = UserRepository()
    user = await user_repo.find_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_same_department = str(user.get("department_id")) == str(current_user.get("department_id"))
    is_self = str(user.get("_id")) == str(current_user.get("_id"))

    if not (is_admin or is_same_department or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    # Convert ObjectIds to strings
    if "_id" in user and isinstance(user["_id"], ObjectId):
        user["_id"] = str(user["_id"])
    if "department_id" in user and isinstance(user["department_id"], ObjectId):
        user["department_id"] = str(user["department_id"])

    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update User",
    description="Update user information (admin only)",
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid data"},
        403: {"description": "Not authorized"},
        404: {"description": "User or department not found"}
    }
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_admin)
):
    """
    Update a user

    **Admin only endpoint**

    Allows updating user information including:
    - Full name
    - Department (useful for correcting errors)
    - Role
    - Active status
    """
    user_repo = UserRepository()
    dept_repo = DepartmentRepository()

    # Check if user exists
    existing_user = await user_repo.find_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prepare update data
    update_data = {}

    if user_data.full_name is not None:
        update_data["full_name"] = user_data.full_name

    if user_data.department_id is not None:
        # Check if new department exists
        department = await dept_repo.find_by_id(user_data.department_id)
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        update_data["department_id"] = user_data.department_id

    if user_data.role is not None:
        update_data["role"] = user_data.role.value

    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active

    # Update user
    updated_user = await user_repo.update_by_id(user_id, update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Convert ObjectIds to strings
    if "_id" in updated_user and isinstance(updated_user["_id"], ObjectId):
        updated_user["_id"] = str(updated_user["_id"])
    if "department_id" in updated_user and isinstance(updated_user["department_id"], ObjectId):
        updated_user["department_id"] = str(updated_user["department_id"])

    return updated_user


@router.delete(
    "/{user_id}",
    summary="Deactivate User",
    description="Deactivate a user account (admin only)",
    responses={
        200: {"description": "User deactivated successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"}
    }
)
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Deactivate a user

    **Admin only endpoint**

    Soft delete - marks the user as inactive rather than deleting the record.
    """
    user_repo = UserRepository()

    # Check if user exists
    existing_user = await user_repo.find_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Deactivate user
    await user_repo.update_by_id(user_id, {"is_active": False})

    return {
        "success": True,
        "message": f"User {existing_user.get('email')} deactivated successfully"
    }
