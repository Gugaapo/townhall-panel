from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from bson import ObjectId

from app.schemas.department import DepartmentResponse, DepartmentCreate, DepartmentUpdate
from app.db.repositories.department_repository import DepartmentRepository
from app.db.repositories.user_repository import UserRepository
from app.core.permissions import require_admin, require_authenticated
from app.utils.constants import UserRole

router = APIRouter()


@router.get(
    "",
    response_model=List[DepartmentResponse],
    summary="List All Departments",
    description="Get a list of all departments in the system",
    responses={
        200: {"description": "List of departments"},
        401: {"description": "Not authenticated"}
    }
)
async def list_departments(
    current_user: dict = Depends(require_authenticated)
):
    """
    List all departments

    Returns a list of all active departments in the system.
    Any authenticated user can access this endpoint.
    """
    dept_repo = DepartmentRepository()
    departments = await dept_repo.find_active_departments()

    # Convert ObjectIds to strings
    for dept in departments:
        if "_id" in dept and isinstance(dept["_id"], ObjectId):
            dept["_id"] = str(dept["_id"])

    return departments


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Get Department by ID",
    description="Get details of a specific department",
    responses={
        200: {"description": "Department details"},
        401: {"description": "Not authenticated"},
        404: {"description": "Department not found"}
    }
)
async def get_department(
    department_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get department by ID

    Returns detailed information about a specific department.
    """
    dept_repo = DepartmentRepository()
    department = await dept_repo.find_by_id(department_id)

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Convert ObjectIds to strings
    if "_id" in department and isinstance(department["_id"], ObjectId):
        department["_id"] = str(department["_id"])

    return department


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Department",
    description="Create a new department (admin only)",
    responses={
        201: {"description": "Department created successfully"},
        400: {"description": "Department name or code already exists"},
        403: {"description": "Not authorized"}
    }
)
async def create_department(
    department_data: DepartmentCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Create a new department

    **Admin only endpoint**

    - **name**: Department name (must be unique)
    - **code**: Department code (must be unique, e.g., 'EDU', 'ADM')
    - **type**: Department type (main or regular)
    - **description**: Optional description
    """
    dept_repo = DepartmentRepository()

    # Check if name already exists
    if await dept_repo.name_exists(department_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists"
        )

    # Check if code already exists
    if await dept_repo.code_exists(department_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department code already exists"
        )

    # Create department
    new_department = {
        "name": department_data.name,
        "code": department_data.code.upper(),
        "type": department_data.type.value,
        "description": department_data.description,
        "is_active": True
    }

    created_department = await dept_repo.create(new_department)

    # Convert ObjectIds to strings
    if "_id" in created_department and isinstance(created_department["_id"], ObjectId):
        created_department["_id"] = str(created_department["_id"])

    return created_department


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update Department",
    description="Update an existing department (admin only)",
    responses={
        200: {"description": "Department updated successfully"},
        400: {"description": "Invalid data or duplicate name/code"},
        403: {"description": "Not authorized"},
        404: {"description": "Department not found"}
    }
)
async def update_department(
    department_id: str,
    department_data: DepartmentUpdate,
    current_user: dict = Depends(require_admin)
):
    """
    Update a department

    **Admin only endpoint**

    Updates department information. Name and code must remain unique.
    """
    dept_repo = DepartmentRepository()

    # Check if department exists
    existing_dept = await dept_repo.find_by_id(department_id)
    if not existing_dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Prepare update data
    update_data = {}
    if department_data.name is not None:
        # Check if new name already exists (and it's not the current department)
        existing_with_name = await dept_repo.find_by_name(department_data.name)
        if existing_with_name and str(existing_with_name["_id"]) != department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department name already exists"
            )
        update_data["name"] = department_data.name

    if department_data.code is not None:
        # Check if new code already exists (and it's not the current department)
        existing_with_code = await dept_repo.find_by_code(department_data.code)
        if existing_with_code and str(existing_with_code["_id"]) != department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department code already exists"
            )
        update_data["code"] = department_data.code.upper()

    if department_data.description is not None:
        update_data["description"] = department_data.description

    if department_data.is_active is not None:
        update_data["is_active"] = department_data.is_active

    # Update department
    updated_department = await dept_repo.update_by_id(department_id, update_data)

    if not updated_department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Convert ObjectIds to strings
    if "_id" in updated_department and isinstance(updated_department["_id"], ObjectId):
        updated_department["_id"] = str(updated_department["_id"])

    return updated_department


@router.get(
    "/{department_id}/users",
    response_model=List,
    summary="Get Department Users",
    description="Get all users in a specific department",
    responses={
        200: {"description": "List of users in the department"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this department"},
        404: {"description": "Department not found"}
    }
)
async def get_department_users(
    department_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get all users in a department

    - **Admins** can view users in any department
    - **Department Heads** and **Employees** can only view users in their own department
    """
    dept_repo = DepartmentRepository()
    user_repo = UserRepository()

    # Check if department exists
    department = await dept_repo.find_by_id(department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_same_department = str(department_id) == str(current_user.get("department_id"))

    if not (is_admin or is_same_department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users in this department"
        )

    # Get users
    users = await user_repo.find_by_department(department_id)

    # Convert ObjectIds to strings and remove password hashes
    for user in users:
        if "_id" in user and isinstance(user["_id"], ObjectId):
            user["_id"] = str(user["_id"])
        if "department_id" in user and isinstance(user["department_id"], ObjectId):
            user["department_id"] = str(user["department_id"])
        if "password_hash" in user:
            del user["password_hash"]

    return users


@router.get(
    "/{department_id}/stats",
    summary="Get Department Statistics",
    description="Get statistics for a specific department",
    responses={
        200: {"description": "Department statistics"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to view this department"},
        404: {"description": "Department not found"}
    }
)
async def get_department_stats(
    department_id: str,
    current_user: dict = Depends(require_authenticated)
):
    """
    Get department statistics

    Returns:
    - Total users in department
    - Users by role (admins, department heads, employees)
    - Active vs inactive users

    - **Admins** can view stats for any department
    - **Department Heads** can view stats for their department
    - **Employees** can view stats for their department
    """
    dept_repo = DepartmentRepository()
    user_repo = UserRepository()

    # Check if department exists
    department = await dept_repo.find_by_id(department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Check permissions
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_same_department = str(department_id) == str(current_user.get("department_id"))

    if not (is_admin or is_same_department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view statistics for this department"
        )

    # Get all users in department
    all_users = await user_repo.find_by_department(department_id)

    # Calculate statistics
    total_users = len(all_users)
    active_users = len([u for u in all_users if u.get("is_active", True)])
    inactive_users = total_users - active_users

    # Count by role
    admins = len([u for u in all_users if u.get("role") == UserRole.ADMIN.value])
    dept_heads = len([u for u in all_users if u.get("role") == UserRole.DEPARTMENT_HEAD.value])
    employees = len([u for u in all_users if u.get("role") == UserRole.EMPLOYEE.value])

    return {
        "department_id": str(department["_id"]),
        "department_name": department.get("name"),
        "department_code": department.get("code"),
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_role": {
            "admins": admins,
            "department_heads": dept_heads,
            "employees": employees
        }
    }
