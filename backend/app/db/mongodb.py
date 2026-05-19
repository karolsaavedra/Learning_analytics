"""
MongoDB Database Connection — Historical Data & Analytics
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_mongo_client = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _mongo_client


def get_mongo_db():
    client = get_mongo_client()
    return client[settings.MONGODB_DB]
