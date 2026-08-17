from sentence_transformers import SentenceTransformer
from typing import List
from app.schemas.config import settings

_model = None


def get_embedder() -> SentenceTransformer:
    """获取 bge-small-zh-v1.5 嵌入模型（懒加载单例）"""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedder()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    model = get_embedder()
    embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embedding[0].tolist()