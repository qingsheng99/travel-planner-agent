"""
知识检索模块

提供基于向量相似度的知识库检索功能。
支持将检索结果拼接为上下文文本（供 LLM 使用），以及返回结构化检索结果。
"""

from typing import List, Dict
from app.rag.chroma_client import get_collection
from app.rag.embedder import embed_query


def retrieve_knowledge(query: str, n_results: int = 3) -> str:
    """检索知识库并将结果拼接为上下文文本

    根据用户查询从知识库中检索最相关的文档片段，
    将结果格式化为带来源标记的文本，便于 LLM 理解和使用。

    Args:
        query: 用户查询文本
        n_results: 返回的匹配文档数量，默认 3

    Returns:
        str: 拼接后的上下文文本，每段前标注来源；无结果时返回空字符串；
             出错时返回错误信息
    """
    try:
        collection = get_collection()                                 # 获取 ChromaDB 集合
        query_embedding = embed_query(query)                          # 将查询转为向量

        # 在知识库中执行向量相似度搜索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        if results and results["documents"]:
            documents = results["documents"][0]                       # 匹配到的文档列表
            # 获取元数据，若无元数据则用空字典填充
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)

            context_parts = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                source = meta.get("source", f"Document {i+1}")       # 提取来源文件名
                context_parts.append(f"[{source}]: {doc}")            # 格式化：来源 + 内容

            return "\n\n".join(context_parts)                         # 用空行分隔各段文本

        return ""                                                     # 无匹配结果返回空字符串
    except Exception as e:
        return f"检索知识时出错: {str(e)}"                             # 异常时返回错误信息


def search_documents(query: str, n_results: int = 5) -> List[Dict]:
    """搜索知识库并返回结构化文档列表

    与 retrieve_knowledge 类似，但返回包含内容、元数据和距离分数的结构化数据，
    便于前端或下游程序进一步处理。

    Args:
        query: 用户查询文本
        n_results: 返回的匹配文档数量，默认 5

    Returns:
        List[Dict]: 文档列表，每项包含 content（内容）、metadata（元数据）、
                    distance（距离分数）；出错时返回包含 error 字段的列表
    """
    try:
        collection = get_collection()                                 # 获取 ChromaDB 集合
        query_embedding = embed_query(query)                          # 将查询转为向量

        # 在知识库中执行向量相似度搜索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}    # 元数据
                distance = results["distances"][0][i] if results["distances"] else None  # 距离分数
                documents.append({
                    "content": doc,                                   # 文档内容
                    "metadata": meta,                                 # 来源、页码等元数据
                    "distance": distance                              # 与查询的向量距离
                })

        return documents
    except Exception as e:
        return [{"error": str(e)}]                                    # 异常时返回错误信息
