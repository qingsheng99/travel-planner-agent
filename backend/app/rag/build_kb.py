"""
知识库构建模块

提供从 PDF 和 TXT 文档中提取文本、分块处理并存入 ChromaDB 知识库的功能。
支持按页提取 PDF 内容，以及基于固定大小的文本分块策略。
"""

import os
import fitz                              # PyMuPDF，用于读取 PDF 文件
from typing import List, Dict
from app.rag.chroma_client import get_collection
from app.rag.embedder import embed_texts


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """从 PDF 文件中按页提取文本

    使用 PyMuPDF（fitz）打开 PDF 文件，逐页提取纯文本内容，
    并记录每页文本的来源文件名和页码。

    Args:
        pdf_path: PDF 文件的路径

    Returns:
        List[Dict]: 文档列表，每项包含 text（文本内容）和
                    metadata（元数据，含 source 和 page）
    """
    documents = []
    try:
        doc = fitz.open(pdf_path)                                     # 打开 PDF 文件
        filename = os.path.basename(pdf_path)                         # 获取文件名（不含路径）

        for page_num in range(len(doc)):                              # 遍历每一页
            page = doc[page_num]
            text = page.get_text()                                    # 提取当前页文本
            if text.strip():                                          # 跳过空白页
                documents.append({
                    "text": text,
                    "metadata": {
                        "source": filename,                           # 来源文件名
                        "page": page_num + 1                          # 页码（从 1 开始）
                    }
                })
        doc.close()                                                   # 关闭 PDF 文件
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")                    # 打印错误信息，不中断流程

    return documents


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """将长文本切分为固定大小的文本块

    使用滑动窗口方式切分文本，相邻块之间保留重叠部分，
    以避免关键信息在切分边界处被截断。

    Args:
        text: 待切分的原始文本
        chunk_size: 每个文本块的最大字符数，默认 500
        overlap: 相邻块之间的重叠字符数，默认 50

    Returns:
        List[str]: 切分后的文本块列表
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size                                      # 计算当前块结束位置
        chunk = text[start:end]                                       # 截取当前块
        chunks.append(chunk)
        start = end - overlap                                         # 下一块起始位置回退 overlap 长度

    return chunks


def build_knowledge_base(docs_dir: str):
    """构建知识库：读取文档、分块、生成向量并存入 ChromaDB

    遍历指定目录下的所有 PDF 和 TXT 文件，提取文本后按块切分，
    为每个块生成嵌入向量，最后批量写入 ChromaDB 集合。

    Args:
        docs_dir: 文档目录路径，用于存放 PDF/TXT 格式的原始文档
    """
    collection = get_collection()                                     # 获取 ChromaDB 集合

    # 收集所有文本块、元数据和唯一标识
    all_texts = []
    all_metadatas = []
    all_ids = []

    for filename in os.listdir(docs_dir):                             # 遍历文档目录
        filepath = os.path.join(docs_dir, filename)

        if filename.lower().endswith('.pdf'):                         # 处理 PDF 文件
            docs = extract_text_from_pdf(filepath)                    # 按页提取文本
            for doc in docs:
                chunks = chunk_text(doc["text"])                      # 将每页文本切分为块
                for i, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    metadata = doc["metadata"].copy()                 # 复制元数据，避免引用共享
                    metadata["chunk"] = i                             # 添加块序号
                    all_metadatas.append(metadata)
                    all_ids.append(f"{filename}_page{metadata['page']}_chunk{i}")

        elif filename.lower().endswith('.txt'):                       # 处理 TXT 文件
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()                                       # 读取全部文本内容
            chunks = chunk_text(text)                                 # 切分为块
            for i, chunk in enumerate(chunks):
                all_texts.append(chunk)
                all_metadatas.append({"source": filename, "chunk": i})
                all_ids.append(f"{filename}_chunk{i}")

    if all_texts:
        # 批量生成所有文本块的嵌入向量
        embeddings = embed_texts(all_texts)
        # 将文本块、向量、元数据和 ID 一并写入 ChromaDB
        collection.add(
            embeddings=embeddings,
            documents=all_texts,
            metadatas=all_metadatas,
            ids=all_ids
        )
        print(f"Added {len(all_texts)} chunks to knowledge base")
    else:
        print("No documents found to process")


if __name__ == "__main__":
    import sys
    # 支持命令行参数指定文档目录，默认使用 ../data/docs
    docs_dir = sys.argv[1] if len(sys.argv) > 1 else "../data/docs"
    build_knowledge_base(docs_dir)
