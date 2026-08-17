import os
import fitz
from typing import List, Dict
from app.rag.chroma_client import get_collection
from app.rag.embedder import embed_texts


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    documents = []
    try:
        doc = fitz.open(pdf_path)
        filename = os.path.basename(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                documents.append({
                    "text": text,
                    "metadata": {
                        "source": filename,
                        "page": page_num + 1
                    }
                })
        doc.close()
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
    
    return documents


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def build_knowledge_base(docs_dir: str):
    collection = get_collection()
    
    all_texts = []
    all_metadatas = []
    all_ids = []
    
    for filename in os.listdir(docs_dir):
        filepath = os.path.join(docs_dir, filename)
        
        if filename.lower().endswith('.pdf'):
            docs = extract_text_from_pdf(filepath)
            for doc in docs:
                chunks = chunk_text(doc["text"])
                for i, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    metadata = doc["metadata"].copy()
                    metadata["chunk"] = i
                    all_metadatas.append(metadata)
                    all_ids.append(f"{filename}_page{metadata['page']}_chunk{i}")
        elif filename.lower().endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_texts.append(chunk)
                all_metadatas.append({"source": filename, "chunk": i})
                all_ids.append(f"{filename}_chunk{i}")
    
    if all_texts:
        embeddings = embed_texts(all_texts)
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
    docs_dir = sys.argv[1] if len(sys.argv) > 1 else "../data/docs"
    build_knowledge_base(docs_dir)
