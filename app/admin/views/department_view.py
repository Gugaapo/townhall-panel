"""
Department management view for admin panel.

Provides CRUD operations for departments with user count display.
"""

from typing import Any, Dict, List, Optional, Sequence

from starlette.requests import Request
from starlette_admin import (
    StringField,
    TextAreaField,
    BooleanField,
    DateTimeField,
    EnumField,
    IntegerField,
    action,
)

from app.admin.providers.base_motor_model_view import BaseMotorModelView
from app.db.repositories.department_repository import DepartmentRepository
from app.db.repositories.user_repository import UserRepository
from app.utils.constants import DepartmentType


class DepartmentView(BaseMotorModelView):
    """Admin view for department management."""

    # Identity
    identity = "departments"
    name = "Department"
    label = "Departments"
    icon = "fa fa-building"

    # Repository
    repository = DepartmentRepository()

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
            "name",
            label="Name",
            required=True,
            searchable=True,
        ),
        StringField(
            "code",
            label="Code",
            required=True,
            searchable=True,
            maxlength=10,
        ),
        TextAreaField(
            "description",
            label="Description",
            required=False,
        ),
        EnumField(
            "type",
            label="Type",
            enum=DepartmentType,
            required=True,
        ),
        BooleanField(
            "is_active",
            label="Active",
        ),
        IntegerField(
            "user_count",
            label="Users",
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
    fields_default_sort = [("name", False)]  # Ascending

    # Search configuration
    search_fields = ["name", "code"]

    def __init__(self):
        super().__init__(repository=DepartmentRepository())
        self.user_repository = UserRepository()

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """Build search filter for departments."""
        return {
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"code": {"$regex": search_term, "$options": "i"}},
            ]
        }

    async def _process_create_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data before creating department - uppercase code."""
        # Uppercase the code
        if "code" in data:
            data["code"] = data["code"].upper()

        # Set default is_active if not provided
        if "is_active" not in data:
            data["is_active"] = True

        return data

    async def _process_edit_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data before updating department - uppercase code."""
        # Uppercase the code
        if "code" in data:
            data["code"] = data["code"].upper()

        return data

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """Find all departments with user count."""
        departments = await super().find_all(request, skip, limit, where, order_by)

        # Add user count for each department
        for dept in departments:
            dept_id = dept.get("_id")
            if dept_id:
                users = await self.user_repository.find_by_department(dept_id)
                dept["user_count"] = len(users)
            else:
                dept["user_count"] = 0

        return departments

    async def find_by_pk(self, request: Request, pk: Any) -> Optional[Any]:
        """Find department by ID with user count."""
        dept = await super().find_by_pk(request, pk)

        if dept:
            users = await self.user_repository.find_by_department(str(pk))
            dept["user_count"] = len(users)

        return dept

    # Custom actions
    @action(
        name="activate",
        text="Activate Departments",
        confirmation="Are you sure you want to activate the selected departments?",
        submit_btn_text="Activate",
        submit_btn_class="btn-success",
    )
    async def activate_departments(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk activate selected departments."""
        count = 0
        for pk in pks:
            result = await self.repository.update_by_id(
                str(pk),
                {"is_active": True}
            )
            if result:
                count += 1

        return f"Successfully activated {count} department(s)."

    @action(
        name="deactivate",
        text="Deactivate Departments",
        confirmation="Are you sure you want to deactivate the selected departments?",
        submit_btn_text="Deactivate",
        submit_btn_class="btn-danger",
    )
    async def deactivate_departments(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk deactivate selected departments."""
        count = 0
        for pk in pks:
            result = await self.repository.update_by_id(
                str(pk),
                {"is_active": False}
            )
            if result:
                count += 1

        return f"Successfully deactivated {count} department(s)."
