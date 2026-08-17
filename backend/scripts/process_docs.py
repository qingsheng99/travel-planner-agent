import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.build_kb import build_knowledge_base


def main():
    docs_dir = os.path.join(os.path.dirname(__file__), "../../data/docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    print(f"Processing documents from: {docs_dir}")
    build_knowledge_base(docs_dir)
    print("Document processing complete!")


if __name__ == "__main__":
    main()
