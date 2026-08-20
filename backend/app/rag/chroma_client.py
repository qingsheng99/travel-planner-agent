"""
ChromaDB 客户端模块

提供 ChromaDB 持久化客户端的单例管理和集合（Collection）获取功能。
所有 RAG 检索操作均依赖此模块获取数据库连接。
"""

import chromadb
from chromadb import PersistentClient
from app.schemas.config import settings
from typing import Optional

# 全局单例客户端实例，初始为 None
_client: Optional[PersistentClient] = None


def get_chroma_client() -> PersistentClient:
    """获取 ChromaDB 持久化客户端（懒加载单例）

    首次调用时创建 PersistentClient 实例，后续调用复用同一实例。
    持久化路径由配置项 settings.CHROMA_PERSIST_DIRECTORY 指定。

    Returns:
        PersistentClient: ChromaDB 持久化客户端实例
    """
    global _client
    if _client is None:
        # 首次调用，创建客户端并指定持久化目录
        _client = PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
        )
    return _client


def get_collection(collection_name: Optional[str] = None):
    """获取或创建指定名称的 ChromaDB 集合

    如果集合已存在则直接返回，否则创建一个新集合。
    集合名称默认为配置文件中的 CHROMA_COLLECTION_NAME。

    Args:
        collection_name: 集合名称，若为 None 则使用默认名称

    Returns:
        Collection: ChromaDB 集合对象
    """
    client = get_chroma_client()                                      # 获取客户端实例
    name = collection_name or settings.CHROMA_COLLECTION_NAME         # 确定集合名称
    return client.get_or_create_collection(name=name)                 # 获取或创建集合