from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DocumentPriority(str, Enum):
    """Document priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DocumentType(str, Enum):
    """Document type enumeration"""
    REQUEST = "request"
    RESPONSE = "response"
    MEMO = "memo"
    REPORT = "report"
    NOTIFICATION = "notification"
    OTHER = "other"


class FileInfo(BaseModel):
    """File information embedded in document"""
    file_id: str = Field(..., description="GridFS file ID")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    uploaded_by: str = Field(..., description="User ID who uploaded the file")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "674d9e8b1234567890abcdef",
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "size": 524288,
                "uploaded_at": "2025-12-06T10:30:00Z",
                "uploaded_by": "674d9e8b1234567890abcd01"
            }
        }
    )


class DocumentMetadata(BaseModel):
    """Document metadata"""
    deadline: Optional[datetime] = Field(None, description="Document deadline")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom key-value pairs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deadline": "2025-12-15T17:00:00Z",
                "tags": ["urgent", "budget", "2025"],
                "custom_fields": {
                    "fiscal_year": "2025",
                    "budget_category": "infrastructure"
                }
            }
        }
    )


class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    description: str = Field(..., min_length=1, description="Document description")
    document_type: DocumentType = Field(..., description="Type of document")
    priority: DocumentPriority = Field(default=DocumentPriority.MEDIUM, description="Document priority")
    metadata: Optional[DocumentMetadata] = Field(default_factory=DocumentMetadata, description="Document metadata")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    assigned_to_user_id: Optional[str] = Field(None, description="User ID to assign the document to")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Budget Request for 2025",
                "description": "Request for approval of the infrastructure budget for fiscal year 2025",
                "document_type": "request",
                "priority": "high",
                "assigned_to_user_id": "674d9e8b1234567890abcd02",
                "metadata": {
                    "deadline": "2025-12-20T17:00:00Z",
                    "tags": ["budget", "2025", "infrastructure"],
                    "custom_fields": {
                        "fiscal_year": "2025",
                        "amount_requested": "500000"
                    }
                }
            }
        }
    )


class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    document_type: Optional[DocumentType] = None
    priority: Optional[DocumentPriority] = None
    status: Optional[DocumentStatus] = None
    assigned_to_user_id: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Budget Request for 2025",
                "priority": "urgent",
                "status": "in_progress",
                "assigned_to_user_id": "674d9e8b1234567890abcd03"
            }
        }
    )


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: str = Field(..., alias="_id", description="Document ID")
    document_number: str = Field(..., description="Auto-generated unique document number")
    status: DocumentStatus = Field(..., description="Current document status")

    creator_id: str = Field(..., description="User ID of document creator")
    creator_department_id: str = Field(..., description="Department ID of creator")

    current_holder_department_id: str = Field(..., description="Department currently holding the document")
    assigned_to_user_id: Optional[str] = Field(None, description="User ID if assigned to specific user")

    files: List[FileInfo] = Field(default_factory=list, description="Attached files")

    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp if archived")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "674d9e8b1234567890abcdef",
                "document_number": "DOC-2025-00001",
                "title": "Budget Request for 2025",
                "description": "Request for approval of the infrastructure budget for fiscal year 2025",
                "document_type": "request",
                "status": "pending",
                "priority": "high",
                "creator_id": "674d9e8b1234567890abcd01",
                "creator_department_id": "693481b9006baf115c78ea51",
                "current_holder_department_id": "693481b9006baf115c78ea51",
                "assigned_to_user_id": "674d9e8b1234567890abcd02",
                "files": [],
                "metadata": {
                    "deadline": "2025-12-20T17:00:00Z",
                    "tags": ["budget", "2025"],
                    "custom_fields": {}
                },
                "created_at": "2025-12-06T10:30:00Z",
                "updated_at": "2025-12-06T10:30:00Z",
                "archived_at": None
            }
        }
    )


class DocumentForward(BaseModel):
    """Schema for forwarding a document to another department"""
    to_department_id: str = Field(..., description="Department ID to forward the document to")
    assigned_to_user_id: Optional[str] = Field(None, description="Optionally assign to specific user in department")
    comment: Optional[str] = Field(None, description="Comment explaining the forward action")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "to_department_id": "693481b9006baf115c78ea52",
                "assigned_to_user_id": "674d9e8b1234567890abcd03",
                "comment": "Please review and provide feedback on this budget request"
            }
        }
    )


class DocumentStatusUpdate(BaseModel):
    """Schema for updating document status"""
    status: DocumentStatus = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "reason": "All requirements have been met and approved"
            }
        }
    )
