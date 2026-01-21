from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentAction(str, Enum):
    """Document action types for audit trail"""
    CREATED = "created"
    FORWARDED = "forwarded"
    VIEWED = "viewed"
    RESPONDED = "responded"
    STATUS_CHANGED = "status_changed"
    MODIFIED = "modified"
    ARCHIVED = "archived"
    FILE_ADDED = "file_added"
    FILE_REMOVED = "file_removed"
    ASSIGNED = "assigned"


class ChangeInfo(BaseModel):
    """Information about a field change"""
    field: str = Field(..., description="Field name that changed")
    old_value: Any = Field(None, description="Previous value")
    new_value: Any = Field(None, description="New value")


class DocumentHistoryCreate(BaseModel):
    """Schema for creating a document history entry"""
    document_id: str = Field(..., description="Document ID")
    action: DocumentAction = Field(..., description="Action performed")
    performed_by: str = Field(..., description="User ID who performed the action")
    performed_by_name: str = Field(..., description="User name (denormalized for audit)")
    performed_by_department: str = Field(..., description="Department ID of user")

    from_department_id: Optional[str] = Field(None, description="Source department (for forwards)")
    to_department_id: Optional[str] = Field(None, description="Destination department (for forwards)")

    old_status: Optional[str] = Field(None, description="Previous status")
    new_status: Optional[str] = Field(None, description="New status")
    status_reason: Optional[str] = Field(None, description="Reason for status change")

    changes: Optional[ChangeInfo] = Field(None, description="Field changes")
    comment: Optional[str] = Field(None, description="Additional comment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "674d9e8b1234567890abcdef",
                "action": "forwarded",
                "performed_by": "674d9e8b1234567890abcd01",
                "performed_by_name": "John Doe",
                "performed_by_department": "693481b9006baf115c78ea51",
                "from_department_id": "693481b9006baf115c78ea51",
                "to_department_id": "693481b9006baf115c78ea52",
                "comment": "Forwarding for review and approval"
            }
        }
    )


class DocumentHistoryResponse(BaseModel):
    """Schema for document history response"""
    id: str = Field(..., alias="_id", description="History entry ID")
    document_id: str = Field(..., description="Document ID")
    action: DocumentAction = Field(..., description="Action performed")

    performed_by: str = Field(..., description="User ID who performed the action")
    performed_by_name: str = Field(..., description="User name")
    performed_by_department: str = Field(..., description="Department ID")

    from_department_id: Optional[str] = Field(None, description="Source department")
    to_department_id: Optional[str] = Field(None, description="Destination department")

    old_status: Optional[str] = Field(None, description="Previous status")
    new_status: Optional[str] = Field(None, description="New status")
    status_reason: Optional[str] = Field(None, description="Reason for status change")

    changes: Optional[ChangeInfo] = Field(None, description="Field changes")
    comment: Optional[str] = Field(None, description="Comment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    timestamp: datetime = Field(..., description="When the action occurred")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "674d9e8b1234567890abc123",
                "document_id": "674d9e8b1234567890abcdef",
                "action": "forwarded",
                "performed_by": "674d9e8b1234567890abcd01",
                "performed_by_name": "John Doe",
                "performed_by_department": "693481b9006baf115c78ea51",
                "from_department_id": "693481b9006baf115c78ea51",
                "to_department_id": "693481b9006baf115c78ea52",
                "comment": "Forwarding for review",
                "timestamp": "2025-12-06T10:30:00Z"
            }
        }
    )
