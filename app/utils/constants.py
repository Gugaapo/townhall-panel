from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEPARTMENT_HEAD = "department_head"
    EMPLOYEE = "employee"


class DepartmentType(str, Enum):
    """Department type enumeration"""
    MAIN = "main"
    REGULAR = "regular"


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


class DocumentAction(str, Enum):
    """Document action enumeration for audit trail"""
    CREATED = "created"
    FORWARDED = "forwarded"
    VIEWED = "viewed"
    RESPONDED = "responded"
    STATUS_CHANGED = "status_changed"
    MODIFIED = "modified"
    ARCHIVED = "archived"


class NotificationType(str, Enum):
    """Notification type enumeration"""
    DOCUMENT_RECEIVED = "document_received"
    DOCUMENT_FORWARDED = "document_forwarded"
    RESPONSE_RECEIVED = "response_received"
    STATUS_CHANGED = "status_changed"
    DEADLINE_APPROACHING = "deadline_approaching"
