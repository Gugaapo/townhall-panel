from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""

    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


# Global MongoDB instance
mongodb = MongoDB()


async def connect_to_mongo():
    """
    Connect to MongoDB database

    Establishes connection to MongoDB and creates database instance.
    Called on application startup.
    """
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGO_HOST}:{settings.MONGO_PORT}")

        # Create MongoDB client
        mongodb.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000
        )

        # Get database instance
        mongodb.db = mongodb.client[settings.MONGO_DATABASE]

        # Test connection
        await mongodb.client.admin.command('ping')

        logger.info(f"Successfully connected to MongoDB database: {settings.MONGO_DATABASE}")

    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MongoDB connection: {e}")
        raise


async def close_mongo_connection():
    """
    Close MongoDB connection

    Closes the MongoDB client connection.
    Called on application shutdown.
    """
    try:
        if mongodb.client:
            mongodb.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance

    Returns:
        AsyncIOMotorDatabase: MongoDB database instance

    Raises:
        RuntimeError: If database is not connected
    """
    if mongodb.db is None:
        raise RuntimeError("Database is not connected. Call connect_to_mongo() first.")
    return mongodb.db


# Collection names
class Collections:
    """MongoDB collection names"""
    USERS = "users"
    DEPARTMENTS = "departments"
    DOCUMENTS = "documents"
    DOCUMENT_HISTORY = "document_history"
    NOTIFICATIONS = "notifications"
