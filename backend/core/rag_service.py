"""
RAG Service Module - Retrieval-Augmented Generation for codebase understanding.
Uses ChromaDB for vector storage and OpenAI embeddings.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("rag_service")

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAG_DIR = os.path.join(DATA_DIR, "rag")
CHROMA_DIR = os.path.join(RAG_DIR, "chroma")

# File extensions to index
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".md", ".yaml", ".yml", ".json"}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".next"}


class RAGService:
    """RAG service for code indexing and retrieval."""
    
    def __init__(self):
        self._client = None
        self._collection = None
        self._embeddings = None
    
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB and embeddings."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
                
                os.makedirs(CHROMA_DIR, exist_ok=True)
                
                self._client = chromadb.PersistentClient(
                    path=CHROMA_DIR,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                # Use OpenAI embeddings
                self._collection = self._client.get_or_create_collection(
                    name="codebase",
                    metadata={"hnsw:space": "cosine"}
                )
                
                logger.info(f"RAG service initialized. Collection has {self._collection.count()} documents.")
                
            except ImportError:
                logger.error("chromadb not installed. Run: pip install chromadb")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {e}")
                raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding using OpenAI API."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []
    
    def _chunk_code(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split code into overlapping chunks."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                # Keep overlap
                overlap_lines = []
                overlap_size = 0
                for l in reversed(current_chunk):
                    if overlap_size + len(l) < overlap:
                        overlap_lines.insert(0, l)
                        overlap_size += len(l) + 1
                    else:
                        break
                current_chunk = overlap_lines
                current_size = overlap_size
            
            current_chunk.append(line)
            current_size += line_size
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def index_repository(self, repo_path: str, repo_name: Optional[str] = None) -> int:
        """Index a repository into the vector database."""
        self._ensure_initialized()
        
        if not os.path.exists(repo_path):
            logger.error(f"Repository path does not exist: {repo_path}")
            return 0
        
        if repo_name is None:
            repo_name = os.path.basename(repo_path)
        
        indexed_count = 0
        path = Path(repo_path)
        
        for file_path in path.rglob("*"):
            # Skip directories and non-code files
            if file_path.is_dir():
                continue
            if file_path.suffix not in CODE_EXTENSIONS:
                continue
            
            # Skip excluded directories
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) < 50:  # Skip very small files
                    continue
                
                relative_path = str(file_path.relative_to(repo_path))
                
                # Chunk the content
                chunks = self._chunk_code(content)
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"{repo_name}:{relative_path}:{i}"
                    
                    # Get embedding
                    embedding = self._get_embedding(chunk)
                    if not embedding:
                        continue
                    
                    # Add to collection
                    self._collection.upsert(
                        ids=[doc_id],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            "repo": repo_name,
                            "file": relative_path,
                            "chunk_index": i,
                            "language": file_path.suffix.lstrip(".")
                        }]
                    )
                    indexed_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                continue
        
        logger.info(f"Indexed {indexed_count} chunks from {repo_name}")
        return indexed_count
    
    def query(self, query_text: str, top_k: int = 5, repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query the RAG database for relevant code chunks."""
        self._ensure_initialized()
        
        if self._collection.count() == 0:
            logger.warning("RAG collection is empty. Run indexing first.")
            return []
        
        try:
            embedding = self._get_embedding(query_text)
            if not embedding:
                return []
            
            where_filter = {"repo": repo_filter} if repo_filter else None
            
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0
                    })
            
            return formatted
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG database statistics."""
        self._ensure_initialized()
        return {
            "total_documents": self._collection.count(),
            "storage_path": CHROMA_DIR
        }
    
    def clear(self):
        """Clear all indexed data."""
        self._ensure_initialized()
        # Delete and recreate collection
        self._client.delete_collection("codebase")
        self._collection = self._client.get_or_create_collection(
            name="codebase",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("RAG collection cleared")


# Singleton instance
_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    """Get the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
