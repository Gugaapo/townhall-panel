"""
Document management view for admin panel.

Provides CRUD operations for documents with custom actions for
forwarding, status changes, and archiving.
"""

from datetime import datetime, timezone
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
    row_action,
)
from starlette_admin.exceptions import ActionFailed

from app.admin.providers.base_motor_model_view import BaseMotorModelView
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.document_history_repository import DocumentHistoryRepository
from app.utils.constants import DocumentStatus, DocumentPriority, DocumentAction


class DocumentView(BaseMotorModelView):
    """Admin view for document management."""

    # Identity
    identity = "documents"
    name = "Document"
    label = "Documents"
    icon = "fa fa-file-alt"

    # Repository
    repository = DocumentRepository()

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
            "document_number",
            label="Document #",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
            searchable=True,
        ),
        StringField(
            "title",
            label="Title",
            required=True,
            searchable=True,
        ),
        TextAreaField(
            "description",
            label="Description",
            required=False,
        ),
        StringField(
            "document_type",
            label="Type",
            required=False,
        ),
        EnumField(
            "status",
            label="Status",
            enum=DocumentStatus,
            required=True,
        ),
        EnumField(
            "priority",
            label="Priority",
            enum=DocumentPriority,
            required=True,
        ),
        StringField(
            "creator_id",
            label="Creator ID",
            exclude_from_list=True,
        ),
        StringField(
            "creator_name",
            label="Creator",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "creator_department_id",
            label="Creator Dept ID",
            exclude_from_list=True,
        ),
        StringField(
            "creator_department_name",
            label="Creator Dept",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "current_holder_department_id",
            label="Holder Dept ID",
            exclude_from_list=True,
        ),
        StringField(
            "current_holder_department_name",
            label="Current Holder",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "assigned_to_user_id",
            label="Assigned User ID",
            exclude_from_list=True,
        ),
        StringField(
            "assigned_to_user_name",
            label="Assigned To",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        DateTimeField(
            "deadline",
            label="Deadline",
            required=False,
        ),
        IntegerField(
            "file_count",
            label="Files",
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
        DateTimeField(
            "archived_at",
            label="Archived At",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
    ]

    # List configuration
    fields_default_sort = [("created_at", True)]  # Descending

    # Search configuration
    search_fields = ["document_number", "title"]

    def __init__(self):
        super().__init__(repository=DocumentRepository())
        self.department_repository = DepartmentRepository()
        self.user_repository = UserRepository()
        self.history_repository = DocumentHistoryRepository()

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """Build search filter for documents."""
        return {
            "$or": [
                {"document_number": {"$regex": search_term, "$options": "i"}},
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}},
            ]
        }

    async def _resolve_names(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve all ID fields to display names."""
        # Resolve creator name
        if doc.get("creator_id"):
            user = await self.user_repository.find_by_id(doc["creator_id"])
            doc["creator_name"] = user.get("full_name", "Unknown") if user else "Unknown"
        else:
            doc["creator_name"] = "Unknown"

        # Resolve creator department name
        if doc.get("creator_department_id"):
            dept = await self.department_repository.find_by_id(
                doc["creator_department_id"]
            )
            doc["creator_department_name"] = dept.get("name", "Unknown") if dept else "Unknown"
        else:
            doc["creator_department_name"] = "Unknown"

        # Resolve current holder department name
        if doc.get("current_holder_department_id"):
            dept = await self.department_repository.find_by_id(
                doc["current_holder_department_id"]
            )
            doc["current_holder_department_name"] = dept.get("name", "Unknown") if dept else "Unknown"
        else:
            doc["current_holder_department_name"] = "None"

        # Resolve assigned user name
        if doc.get("assigned_to_user_id"):
            user = await self.user_repository.find_by_id(doc["assigned_to_user_id"])
            doc["assigned_to_user_name"] = user.get("full_name", "Unknown") if user else "Unknown"
        else:
            doc["assigned_to_user_name"] = "None"

        # Add file count
        doc["file_count"] = len(doc.get("files", []))

        return doc

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """Find all documents with name resolution."""
        documents = await super().find_all(request, skip, limit, where, order_by)

        # Resolve names for each document
        resolved = []
        for doc in documents:
            resolved.append(await self._resolve_names(doc))

        return resolved

    async def find_by_pk(self, request: Request, pk: Any) -> Optional[Any]:
        """Find document by ID with name resolution."""
        doc = await super().find_by_pk(request, pk)

        if doc:
            doc = await self._resolve_names(doc)

        return doc

    async def _create_history_entry(
        self,
        document_id: str,
        document_number: str,
        action: str,
        performed_by: str,
        performed_by_name: str,
        details: Dict[str, Any] = None,
    ):
        """Create a history entry for a document action."""
        history_data = {
            "document_id": document_id,
            "document_number": document_number,
            "action": action,
            "performed_by": performed_by,
            "performed_by_name": performed_by_name,
            "details": details or {},
        }
        await self.history_repository.create_history_entry(history_data)

    async def _get_admin_user_info(self, request: Request) -> tuple:
        """Get admin user ID and name from session."""
        user_id = request.session.get("admin_user_id", "admin")
        user_name = request.session.get("admin_name", "Admin")
        return user_id, user_name

    # Custom actions
    @action(
        name="archive",
        text="Archive Documents",
        confirmation="Are you sure you want to archive the selected documents?",
        submit_btn_text="Archive",
        submit_btn_class="btn-warning",
    )
    async def archive_documents(self, request: Request, pks: List[Any]) -> str:
        """Bulk archive selected documents."""
        user_id, user_name = await self._get_admin_user_info(request)
        count = 0

        for pk in pks:
            doc = await self.repository.find_by_id(str(pk))
            if not doc:
                continue

            result = await self.repository.archive_document(str(pk))
            if result:
                count += 1
                # Create history entry
                await self._create_history_entry(
                    document_id=str(pk),
                    document_number=doc.get("document_number", "Unknown"),
                    action=DocumentAction.ARCHIVED.value,
                    performed_by=user_id,
                    performed_by_name=user_name,
                    details={"reason": "Bulk archived via admin panel"},
                )

        return f"Successfully archived {count} document(s)."

    @action(
        name="change_status_pending",
        text="Change Status → Pending",
        confirmation="Change selected documents status to 'Pending'?",
        submit_btn_text="Change",
        submit_btn_class="btn-info",
    )
    async def change_status_pending(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk change status to pending."""
        return await self._bulk_change_status(
            request, pks, DocumentStatus.PENDING.value
        )

    @action(
        name="change_status_in_progress",
        text="Change Status → In Progress",
        confirmation="Change selected documents status to 'In Progress'?",
        submit_btn_text="Change",
        submit_btn_class="btn-primary",
    )
    async def change_status_in_progress(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk change status to in_progress."""
        return await self._bulk_change_status(
            request, pks, DocumentStatus.IN_PROGRESS.value
        )

    @action(
        name="change_status_completed",
        text="Change Status → Completed",
        confirmation="Change selected documents status to 'Completed'?",
        submit_btn_text="Change",
        submit_btn_class="btn-success",
    )
    async def change_status_completed(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk change status to completed."""
        return await self._bulk_change_status(
            request, pks, DocumentStatus.COMPLETED.value
        )

    async def _bulk_change_status(
        self,
        request: Request,
        pks: List[Any],
        new_status: str
    ) -> str:
        """Change status for multiple documents."""
        user_id, user_name = await self._get_admin_user_info(request)
        count = 0

        for pk in pks:
            doc = await self.repository.find_by_id(str(pk))
            if not doc:
                continue

            old_status = doc.get("status")
            result = await self.repository.update_status(str(pk), new_status)

            if result:
                count += 1
                # Create history entry
                await self._create_history_entry(
                    document_id=str(pk),
                    document_number=doc.get("document_number", "Unknown"),
                    action=DocumentAction.STATUS_CHANGED.value,
                    performed_by=user_id,
                    performed_by_name=user_name,
                    details={
                        "old_status": old_status,
                        "new_status": new_status,
                        "reason": "Changed via admin panel",
                    },
                )

        return f"Successfully changed status of {count} document(s) to '{new_status}'."

    @action(
        name="change_priority_high",
        text="Set Priority → High",
        confirmation="Set priority to 'High' for selected documents?",
        submit_btn_text="Change",
        submit_btn_class="btn-warning",
    )
    async def change_priority_high(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk change priority to high."""
        return await self._bulk_change_priority(
            request, pks, DocumentPriority.HIGH.value
        )

    @action(
        name="change_priority_urgent",
        text="Set Priority → Urgent",
        confirmation="Set priority to 'Urgent' for selected documents?",
        submit_btn_text="Change",
        submit_btn_class="btn-danger",
    )
    async def change_priority_urgent(
        self,
        request: Request,
        pks: List[Any]
    ) -> str:
        """Bulk change priority to urgent."""
        return await self._bulk_change_priority(
            request, pks, DocumentPriority.URGENT.value
        )

    async def _bulk_change_priority(
        self,
        request: Request,
        pks: List[Any],
        new_priority: str
    ) -> str:
        """Change priority for multiple documents."""
        user_id, user_name = await self._get_admin_user_info(request)
        count = 0

        for pk in pks:
            doc = await self.repository.find_by_id(str(pk))
            if not doc:
                continue

            result = await self.repository.update_by_id(
                str(pk),
                {"priority": new_priority}
            )

            if result:
                count += 1
                # Create history entry
                await self._create_history_entry(
                    document_id=str(pk),
                    document_number=doc.get("document_number", "Unknown"),
                    action=DocumentAction.MODIFIED.value,
                    performed_by=user_id,
                    performed_by_name=user_name,
                    details={
                        "field": "priority",
                        "old_value": doc.get("priority"),
                        "new_value": new_priority,
                        "reason": "Changed via admin panel",
                    },
                )

        return f"Successfully changed priority of {count} document(s) to '{new_priority}'."

    @row_action(
        name="view_history",
        text="View History",
        icon_class="fa fa-history",
    )
    async def view_history(self, request: Request, pk: Any) -> str:
        """Row action to view document history - returns redirect URL."""
        # Note: In a real implementation, this would redirect to the
        # document_history view filtered by this document ID
        return f"View history for document at: /admin/document_history?document_id={pk}"

    @row_action(
        name="quick_archive",
        text="Archive",
        confirmation="Archive this document?",
        submit_btn_text="Archive",
        submit_btn_class="btn-warning",
        icon_class="fa fa-archive",
    )
    async def quick_archive(self, request: Request, pk: Any) -> str:
        """Quick archive a single document."""
        user_id, user_name = await self._get_admin_user_info(request)

        doc = await self.repository.find_by_id(str(pk))
        if not doc:
            raise ActionFailed("Document not found")

        result = await self.repository.archive_document(str(pk))
        if not result:
            raise ActionFailed("Failed to archive document")

        # Create history entry
        await self._create_history_entry(
            document_id=str(pk),
            document_number=doc.get("document_number", "Unknown"),
            action=DocumentAction.ARCHIVED.value,
            performed_by=user_id,
            performed_by_name=user_name,
            details={"reason": "Archived via admin panel"},
        )

        return "Document has been archived."
