import asyncio
import logging
from pymongo import IndexModel, ASCENDING, DESCENDING

from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database, Collections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """
    Create all database indexes for optimal performance

    This should be run once during initial setup and whenever
    new indexes are added to the schema.
    """
    try:
        await connect_to_mongo()
        db = get_database()

        logger.info("Creating database indexes...")

        # Users Collection Indexes
        users_indexes = [
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
            IndexModel([("department_id", ASCENDING)], name="department_id"),
            IndexModel([("role", ASCENDING)], name="role"),
            IndexModel([("is_active", ASCENDING)], name="is_active"),
        ]
        await db[Collections.USERS].create_indexes(users_indexes)
        logger.info(f"Created {len(users_indexes)} indexes on {Collections.USERS} collection")

        # Departments Collection Indexes
        departments_indexes = [
            IndexModel([("name", ASCENDING)], unique=True, name="name_unique"),
            IndexModel([("code", ASCENDING)], unique=True, name="code_unique"),
            IndexModel([("type", ASCENDING)], name="type"),
            IndexModel([("is_active", ASCENDING)], name="is_active"),
        ]
        await db[Collections.DEPARTMENTS].create_indexes(departments_indexes)
        logger.info(f"Created {len(departments_indexes)} indexes on {Collections.DEPARTMENTS} collection")

        # Documents Collection Indexes
        documents_indexes = [
            IndexModel([("document_number", ASCENDING)], unique=True, name="document_number_unique"),
            IndexModel([("current_holder_department_id", ASCENDING)], name="current_holder_department"),
            IndexModel([("creator_id", ASCENDING)], name="creator_id"),
            IndexModel([("creator_department_id", ASCENDING)], name="creator_department"),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("priority", ASCENDING)], name="priority"),
            IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_desc"),
            # Compound indexes for common queries
            IndexModel(
                [("current_holder_department_id", ASCENDING), ("status", ASCENDING)],
                name="department_status"
            ),
            IndexModel(
                [("creator_id", ASCENDING), ("created_at", DESCENDING)],
                name="creator_created"
            ),
        ]
        await db[Collections.DOCUMENTS].create_indexes(documents_indexes)
        logger.info(f"Created {len(documents_indexes)} indexes on {Collections.DOCUMENTS} collection")

        # Document History Collection Indexes
        history_indexes = [
            IndexModel(
                [("document_id", ASCENDING), ("timestamp", DESCENDING)],
                name="document_timestamp"
            ),
            IndexModel([("performed_by", ASCENDING)], name="performed_by"),
            IndexModel([("action", ASCENDING)], name="action"),
            IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
            IndexModel(
                [("performed_by_department", ASCENDING), ("timestamp", DESCENDING)],
                name="department_timestamp"
            ),
        ]
        await db[Collections.DOCUMENT_HISTORY].create_indexes(history_indexes)
        logger.info(f"Created {len(history_indexes)} indexes on {Collections.DOCUMENT_HISTORY} collection")

        # Notifications Collection Indexes
        notifications_indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("is_read", ASCENDING)],
                name="user_read_status"
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="user_created"
            ),
            IndexModel([("document_id", ASCENDING)], name="document_id"),
            IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
            IndexModel([("type", ASCENDING)], name="type"),
        ]
        await db[Collections.NOTIFICATIONS].create_indexes(notifications_indexes)
        logger.info(f"Created {len(notifications_indexes)} indexes on {Collections.NOTIFICATIONS} collection")

        logger.info("All indexes created successfully!")

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(create_indexes())
