"""
文档处理脚本

将 data/docs 目录下的原始文档（PDF/TXT）处理并构建为向量知识库。
供 RAG 检索模块使用，在运行 RAG 功能前需要先执行此脚本。
"""

import sys
import os
# 将项目根目录加入 Python 模块搜索路径，确保可以直接导入 backend 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.build_kb import build_knowledge_base


def main():
    """主入口：处理文档并构建知识库

    确保文档目录存在（若不存在则自动创建），
    然后调用 build_knowledge_base 执行文档提取、分块和向量入库。

    Returns:
        None
    """
    # 文档目录位于项目根目录下的 data/docs
    docs_dir = os.path.join(os.path.dirname(__file__), "../../data/docs")
    os.makedirs(docs_dir, exist_ok=True)                              # 确保文档目录存在

    print(f"Processing documents from: {docs_dir}")
    build_knowledge_base(docs_dir)                                    # 构建知识库
    print("Document processing complete!")


if __name__ == "__main__":
    main()
