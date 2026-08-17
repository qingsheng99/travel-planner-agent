import chromadb
from chromadb import PersistentClient
from app.schemas.config import settings
from typing import Optional

_client: Optional[PersistentClient] = None


def get_chroma_client() -> PersistentClient:
    """获取 ChromaDB PersistentClient（懒加载单例）"""
    global _client
    if _client is None:
        _client = PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
        )
    return _client


def get_collection(collection_name: Optional[str] = None):
    client = get_chroma_client()
    name = collection_name or settings.CHROMA_COLLECTION_NAME
    return client.get_or_create_collection(name=name)