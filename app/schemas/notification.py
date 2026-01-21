from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.utils.constants import NotificationType


class NotificationBase(BaseModel):
    """Base notification schema"""
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    type: NotificationType = Field(..., description="Notification type")


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    user_id: str = Field(..., description="User ID to notify")
    document_id: str = Field(..., description="Related document ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "document_id": "507f1f77bcf86cd799439012",
                "type": "document_received",
                "title": "New Document Assigned: DOC-2025-00001",
                "message": "You have been assigned document 'Budget Request 2025'",
                "metadata": {
                    "action": "assigned",
                    "actor_name": "John Doe"
                }
            }
        }


class NotificationResponse(NotificationBase):
    """Schema for notification response"""
    id: str = Field(..., alias="_id", description="Notification ID")
    user_id: str = Field(..., description="User ID")
    document_id: str = Field(..., description="Related document ID")
    is_read: bool = Field(False, description="Whether notification has been read")
    email_sent: bool = Field(False, description="Whether email was sent")
    email_sent_at: Optional[datetime] = Field(None, description="Email sent timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    created_at: datetime = Field(..., description="Creation timestamp")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "document_id": "507f1f77bcf86cd799439013",
                "type": "document_forwarded",
                "title": "Document Forwarded to You: DOC-2025-00001",
                "message": "Document 'Budget Request 2025' has been forwarded to you by John Doe",
                "is_read": False,
                "email_sent": True,
                "email_sent_at": "2025-01-10T14:00:00",
                "metadata": {
                    "from_department_id": "507f1f77bcf86cd799439014",
                    "to_department_id": "507f1f77bcf86cd799439015",
                    "forwarded_by": "John Doe"
                },
                "created_at": "2025-01-10T14:00:00",
                "read_at": None
            }
        }


class NotificationUpdate(BaseModel):
    """Schema for updating a notification"""
    is_read: Optional[bool] = Field(None, description="Mark as read/unread")

    class Config:
        json_schema_extra = {
            "example": {
                "is_read": True
            }
        }
