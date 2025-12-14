"""
MongoDB connection management.

Provides both sync (pymongo) and async (motor) clients.
- Use sync client for scripts and CLI tools
- Use async client for FastAPI endpoints
"""

from pymongo import MongoClient
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config.settings import settings


# ============================================================
# Synchronous Client (for scripts, CLI, simple operations)
# ============================================================

_sync_client: MongoClient | None = None


def get_sync_client() -> MongoClient:
    """Get or create the synchronous MongoDB client."""
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.MONGODB_URI)
    return _sync_client


def get_sync_database() -> Database:
    """Get the synchronous database instance."""
    client = get_sync_client()
    return client[settings.MONGODB_DATABASE]


def close_sync_client() -> None:
    """Close the synchronous client connection."""
    global _sync_client
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None


# ============================================================
# Asynchronous Client (for FastAPI, high-performance operations)
# ============================================================

_async_client: AsyncIOMotorClient | None = None


def get_async_client() -> AsyncIOMotorClient:
    """Get or create the asynchronous MongoDB client."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _async_client


def get_async_database() -> AsyncIOMotorDatabase:
    """Get the asynchronous database instance."""
    client = get_async_client()
    return client[settings.MONGODB_DATABASE]


async def close_async_client() -> None:
    """Close the asynchronous client connection."""
    global _async_client
    if _async_client is not None:
        _async_client.close()
        _async_client = None


# ============================================================
# Convenience function for testing connection
# ============================================================

def test_connection() -> bool:
    """
    Test that we can connect to MongoDB.
    
    Returns:
        True if connection successful, raises exception otherwise.
    """
    client = get_sync_client()
    # The ping command is lightweight and confirms connectivity
    result = client.admin.command("ping")
    return result.get("ok") == 1.0