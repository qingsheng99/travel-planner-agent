"""
文本嵌入（Embedding）模块

提供基于 sentence-transformers 的文本向量化功能。
使用 bge-small-zh-v1.5 模型将文本转换为稠密向量，支持批量嵌入和单条查询嵌入。
"""

from typing import List, TYPE_CHECKING
from app.schemas.config import settings

# 尝试导入 sentence-transformers，若未安装则置为 None 以便后续给出友好提示
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# 类型检查场景下保证 IDE 能获取到完整的类型信息
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# 全局单例模型实例，初始为 None
_model = None


def get_embedder():
    """获取文本嵌入模型实例（懒加载单例）

    首次调用时加载 bge-small-zh-v1.5 模型，后续调用复用同一实例。
    若 sentence-transformers 未安装则抛出 RuntimeError。

    Returns:
        SentenceTransformer: 嵌入模型实例
    """
    global _model
    if SentenceTransformer is None:
        # 依赖缺失时抛出明确错误信息
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Please install it to use RAG features: pip install sentence-transformers"
        )
    if _model is None:
        # 首次调用，根据配置加载指定模型
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量将文本列表转换为嵌入向量

    对传入的文本列表进行编码，返回归一化后的稠密向量列表。

    Args:
        texts: 待编码的文本列表

    Returns:
        List[List[float]]: 嵌入向量列表，每个向量对应一条输入文本
    """
    model = get_embedder()                                            # 获取模型实例
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,    # 输出向量归一化，便于余弦相似度计算
        show_progress_bar=False,      # 批量处理时隐藏进度条
    )
    return embeddings.tolist()                                        # 将 numpy 数组转为 Python 列表


def embed_query(query: str) -> List[float]:
    """将单条查询文本转换为嵌入向量

    用于检索场景，将用户查询编码为向量以便与知识库中的文档向量进行相似度匹配。

    Args:
        query: 用户查询文本

    Returns:
        List[float]: 查询文本对应的嵌入向量
    """
    model = get_embedder()                                            # 获取模型实例
    embedding = model.encode(
        [query],                       # 模型接受列表输入，将单条文本包装为列表
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embedding[0].tolist()                                      # 提取第一个（也是唯一一个）结果并转为列表