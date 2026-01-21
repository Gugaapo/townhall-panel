"""
User management view for admin panel.

Provides CRUD operations for users with password hashing and department lookup.
"""

from typing import Any, Dict, List, Optional, Sequence

from starlette.requests import Request
from starlette_admin import (
    StringField,
    EmailField,
    PasswordField,
    BooleanField,
    DateTimeField,
    EnumField,
    action,
    row_action,
)
from starlette_admin.exceptions import ActionFailed

from app.admin.providers.base_motor_model_view import BaseMotorModelView
from app.core.security import get_password_hash
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.utils.constants import UserRole


class UserView(BaseMotorModelView):
    """Admin view for user management."""

    # Identity
    identity = "users"
    name = "User"
    label = "Users"
    icon = "fa fa-users"

    # Repository
    repository = UserRepository()

    # Fields configuration
    fields = [
        StringField(
            "_id",
            label="ID",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        EmailField(
            "email",
            label="Email",
            required=True,
            searchable=True,
        ),
        StringField(
            "full_name",
            label="Full Name",
            required=True,
            searchable=True,
        ),
        PasswordField(
            "password",
            label="Password",
            required=True,
            exclude_from_list=True,
            exclude_from_detail=True,
        ),
        EnumField(
            "role",
            label="Role",
            enum=UserRole,
            required=True,
        ),
        StringField(
            "department_id",
            label="Department ID",
            required=False,
        ),
        StringField(
            "department_name",
            label="Department",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        BooleanField(
            "is_active",
            label="Active",
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
    fields_default_sort = [("created_at", True)]  # Descending

    # Exclude password hash from responses
    exclude_fields_from_list = ["hashed_password"]
    exclude_fields_from_detail = ["hashed_password"]

    # Search configuration
    search_fields = ["email", "full_name"]

    def __init__(self):
        super().__init__(repository=UserRepository())
        self.department_repository = DepartmentRepository()

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """Build search filter for users."""
        return {
            "$or": [
                {"email": {"$regex": search_term, "$options": "i"}},
                {"full_name": {"$regex": search_term, "$options": "i"}},
            ]
        }

    async def _process_create_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data before creating user - hash password."""
        # Extract and hash password
        password = data.pop("password", None)
        if password:
            data["hashed_password"] = get_password_hash(password)

        # Normalize email
        if "email" in data:
            data["email"] = data["email"].lower()

        # Set default is_active if not provided
        if "is_active" not in data:
            data["is_active"] = True

        return data

    async def _process_edit_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data before updating user - hash password if changed."""
        # Hash password only if provided (not empty)
        password = data.pop("password", None)
        if password and password.strip():
            data["hashed_password"] = get_password_hash(password)

        # Normalize email
        if "email" in data:
            data["email"] = data["email"].lower()

        return data

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """Find all users with department name resolution."""
        users = await super().find_all(request, skip, limit, where, order_by)

        # Resolve department names
        for user in users:
            if user.get("department_id"):
                dept = await self.department_repository.find_by_id(
                    user["department_id"]
                )
                user["department_name"] = dept.get("name", "Unknown") if dept else "Unknown"
            else:
                user["department_name"] = "None"

        return users

    async def find_by_pk(self, request: Request, pk: Any) -> Optional[Any]:
        """Find user by ID with department name resolution."""
        user = await super().find_by_pk(request, pk)

        if user and user.get("department_id"):
            dept = await self.department_repository.find_by_id(
                user["department_id"]
            )
            user["department_name"] = dept.get("name", "Unknown") if dept else "Unknown"
        elif user:
            user["department_name"] = "None"

        return user

    # Custom actions
    @action(
        name="activate",
        text="Activate Users",
        confirmation="Are you sure you want to activate the selected users?",
        submit_btn_text="Activate",
        submit_btn_class="btn-success",
    )
    async def activate_users(self, request: Request, pks: List[Any]) -> str:
        """Bulk activate selected users."""
        count = 0
        for pk in pks:
            result = await self.repository.update_by_id(
                str(pk),
                {"is_active": True}
            )
            if result:
                count += 1

        return f"Successfully activated {count} user(s)."

    @action(
        name="deactivate",
        text="Deactivate Users",
        confirmation="Are you sure you want to deactivate the selected users?",
        submit_btn_text="Deactivate",
        submit_btn_class="btn-danger",
    )
    async def deactivate_users(self, request: Request, pks: List[Any]) -> str:
        """Bulk deactivate selected users."""
        count = 0
        for pk in pks:
            result = await self.repository.update_by_id(
                str(pk),
                {"is_active": False}
            )
            if result:
                count += 1

        return f"Successfully deactivated {count} user(s)."

    @row_action(
        name="toggle_active",
        text="Toggle Active Status",
        confirmation="Toggle this user's active status?",
        submit_btn_text="Toggle",
        submit_btn_class="btn-warning",
        icon_class="fa fa-toggle-on",
    )
    async def toggle_active(self, request: Request, pk: Any) -> str:
        """Toggle a single user's active status."""
        user = await self.repository.find_by_id(str(pk))
        if not user:
            raise ActionFailed("User not found")

        new_status = not user.get("is_active", True)
        await self.repository.update_by_id(str(pk), {"is_active": new_status})

        status_text = "activated" if new_status else "deactivated"
        return f"User has been {status_text}."
