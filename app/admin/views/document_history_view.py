"""
Document history/audit trail view for admin panel.

Read-only view of all document actions for audit purposes.
"""

from typing import Any, Dict, List, Optional, Sequence

from starlette.requests import Request
from starlette_admin import (
    StringField,
    TextAreaField,
    DateTimeField,
    EnumField,
    JSONField,
)

from app.admin.providers.base_motor_model_view import BaseMotorModelView
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.db.repositories.user_repository import UserRepository
from app.utils.constants import DocumentAction


class DocumentHistoryView(BaseMotorModelView):
    """Admin view for document history/audit trail (read-only)."""

    # Identity
    identity = "document_history"
    name = "Audit Entry"
    label = "Audit Trail"
    icon = "fa fa-history"

    # Repository
    repository = DocumentHistoryRepository()

    # Read-only mode
    _allow_create = False
    _allow_edit = False
    _allow_delete = False

    # Fields configuration
    fields = [
        StringField(
            "_id",
            label="ID",
            read_only=True,
        ),
        StringField(
            "document_id",
            label="Document ID",
            searchable=True,
        ),
        StringField(
            "document_number",
            label="Document #",
            searchable=True,
        ),
        EnumField(
            "action",
            label="Action",
            enum=DocumentAction,
        ),
        StringField(
            "performed_by",
            label="Performed By (ID)",
            exclude_from_list=True,
        ),
        StringField(
            "performed_by_name",
            label="Performed By",
        ),
        StringField(
            "performed_by_department",
            label="Dept ID",
            exclude_from_list=True,
        ),
        StringField(
            "performed_by_department_name",
            label="Department",
        ),
        StringField(
            "from_department_id",
            label="From Dept ID",
            exclude_from_list=True,
        ),
        StringField(
            "from_department_name",
            label="From Dept",
        ),
        StringField(
            "to_department_id",
            label="To Dept ID",
            exclude_from_list=True,
        ),
        StringField(
            "to_department_name",
            label="To Dept",
        ),
        JSONField(
            "details",
            label="Details",
            exclude_from_list=True,
        ),
        TextAreaField(
            "details_summary",
            label="Summary",
            read_only=True,
        ),
        DateTimeField(
            "timestamp",
            label="Timestamp",
        ),
        DateTimeField(
            "created_at",
            label="Created At",
            exclude_from_list=True,
        ),
    ]

    # List configuration
    fields_default_sort = [("timestamp", True)]  # Descending (most recent first)

    # Pagination
    page_size = 50

    def __init__(self):
        super().__init__(repository=DocumentHistoryRepository())
        self.department_repository = DepartmentRepository()
        self.user_repository = UserRepository()

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """Build search filter for document history."""
        return {
            "$or": [
                {"document_number": {"$regex": search_term, "$options": "i"}},
                {"document_id": {"$regex": search_term, "$options": "i"}},
                {"performed_by_name": {"$regex": search_term, "$options": "i"}},
            ]
        }

    async def _resolve_names(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve all ID fields to display names."""
        # Resolve performed_by_department_name
        if entry.get("performed_by_department"):
            dept = await self.department_repository.find_by_id(
                entry["performed_by_department"]
            )
            entry["performed_by_department_name"] = (
                dept.get("name", "Unknown") if dept else "Unknown"
            )
        else:
            entry["performed_by_department_name"] = "N/A"

        # Resolve from_department_name
        if entry.get("from_department_id"):
            dept = await self.department_repository.find_by_id(
                entry["from_department_id"]
            )
            entry["from_department_name"] = (
                dept.get("name", "Unknown") if dept else "Unknown"
            )
        else:
            entry["from_department_name"] = "N/A"

        # Resolve to_department_name
        if entry.get("to_department_id"):
            dept = await self.department_repository.find_by_id(
                entry["to_department_id"]
            )
            entry["to_department_name"] = (
                dept.get("name", "Unknown") if dept else "Unknown"
            )
        else:
            entry["to_department_name"] = "N/A"

        # Create a summary of the details
        entry["details_summary"] = self._format_details_summary(entry)

        return entry

    def _format_details_summary(self, entry: Dict[str, Any]) -> str:
        """Format a human-readable summary of the action details."""
        action = entry.get("action", "")
        details = entry.get("details", {})

        if action == DocumentAction.FORWARDED.value:
            from_dept = entry.get("from_department_name", "Unknown")
            to_dept = entry.get("to_department_name", "Unknown")
            comment = details.get("comment", "")
            summary = f"Forwarded from {from_dept} to {to_dept}"
            if comment:
                summary += f"\nComment: {comment}"
            return summary

        elif action == DocumentAction.STATUS_CHANGED.value:
            old_status = details.get("old_status", "Unknown")
            new_status = details.get("new_status", "Unknown")
            reason = details.get("reason", "")
            summary = f"Status: {old_status} → {new_status}"
            if reason:
                summary += f"\nReason: {reason}"
            return summary

        elif action == DocumentAction.CREATED.value:
            return "Document created"

        elif action == DocumentAction.ARCHIVED.value:
            reason = details.get("reason", "No reason provided")
            return f"Document archived\nReason: {reason}"

        elif action == DocumentAction.MODIFIED.value:
            field = details.get("field", "Unknown field")
            old_val = details.get("old_value", "Unknown")
            new_val = details.get("new_value", "Unknown")
            return f"Field '{field}' changed: {old_val} → {new_val}"

        elif action == DocumentAction.RESPONDED.value:
            return details.get("response_summary", "Response added")

        elif action == DocumentAction.VIEWED.value:
            return "Document viewed"

        else:
            # Generic handling
            if details:
                return str(details)
            return action

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """Find all history entries with name resolution."""
        # Check for document_id filter in query params
        document_id = request.query_params.get("document_id")
        if document_id and where is None:
            where = {"document_id": document_id}
        elif document_id and isinstance(where, dict):
            where["document_id"] = document_id

        entries = await super().find_all(request, skip, limit, where, order_by)

        # Resolve names for each entry
        resolved = []
        for entry in entries:
            resolved.append(await self._resolve_names(entry))

        return resolved

    async def find_by_pk(self, request: Request, pk: Any) -> Optional[Any]:
        """Find history entry by ID with name resolution."""
        entry = await super().find_by_pk(request, pk)

        if entry:
            entry = await self._resolve_names(entry)

        return entry
