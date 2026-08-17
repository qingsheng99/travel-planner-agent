from typing import List, Dict
from app.rag.chroma_client import get_collection
from app.rag.embedder import embed_query


def retrieve_knowledge(query: str, n_results: int = 3) -> str:
    try:
        collection = get_collection()
        query_embedding = embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if results and results["documents"]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
            
            context_parts = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                source = meta.get("source", f"Document {i+1}")
                context_parts.append(f"[{source}]: {doc}")
            
            return "\n\n".join(context_parts)
        
        return ""
    except Exception as e:
        return f"检索知识时出错: {str(e)}"


def search_documents(query: str, n_results: int = 5) -> List[Dict]:
    try:
        collection = get_collection()
        query_embedding = embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else None
                documents.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": distance
                })
        
        return documents
    except Exception as e:
        return [{"error": str(e)}]
