import os
import faiss
import numpy as np
import pickle
from typing import Dict, List, Tuple, Any

class FAISSStore:
    """
    Manages a FAISS index for child chunks and an associated store for parent sheets.
    Supports index persistence.
    """
    def __init__(self, index_dir: str = None):
        self.index_dir = index_dir or os.environ.get("FAISS_INDEX_DIR", "./faiss_index")
        self.index = None
        self.child_store = []  # Maps FAISS index row to child chunk metadata
        self.parent_store = {}  # Maps parent_id to parent doc dictionary (contains text, metadata)
        
    def clear(self):
        """Resets the vector store and document stores."""
        self.index = None
        self.child_store = []
        self.parent_store = {}
        if os.path.exists(self.index_dir):
            try:
                for f in os.listdir(self.index_dir):
                    os.remove(os.path.join(self.index_dir, f))
                os.rmdir(self.index_dir)
            except Exception:
                pass

    def add_documents(self, child_chunks: List[Dict[str, Any]], embeddings: List[List[float]], parent_docs: Dict[str, Dict[str, Any]]):
        """
        Adds child chunks and their embeddings to the FAISS index,
        and saves parents to the parent store.
        """
        if not child_chunks or not embeddings:
            return
            
        embeddings_np = np.array(embeddings).astype('float32')
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_np)
        
        dimension = embeddings_np.shape[1]
        
        if self.index is None:
            # IndexFlatIP is Inner Product. Since we normalized L2, Inner Product equals Cosine Similarity
            self.index = faiss.IndexFlatIP(dimension)
            
        self.index.add(embeddings_np)
        
        # Store child metadata
        for chunk in child_chunks:
            self.child_store.append(chunk)
            
        # Store parent documents
        for p_id, p_doc in parent_docs.items():
            self.parent_store[p_id] = p_doc

    def search(self, query_embedding: List[float], k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Searches the FAISS index for the top k closest child chunks.
        Returns a list of tuples: (child_chunk_metadata, score)
        """
        if self.index is None or len(self.child_store) == 0:
            return []
            
        query_np = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_np)
        
        # Search index
        scores, indices = self.index.search(query_np, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.child_store):
                continue
            results.append((self.child_store[idx], float(score)))
            
        return results

    def save(self):
        """Persists the FAISS index and document stores to disk."""
        if self.index is None:
            return
            
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, os.path.join(self.index_dir, "index.faiss"))
        
        # Save child store and parent store
        metadata = {
            "child_store": self.child_store,
            "parent_store": self.parent_store
        }
        with open(os.path.join(self.index_dir, "metadata.pkl"), "wb") as f:
            pickle.dump(metadata, f)

    def load(self) -> bool:
        """Loads the FAISS index and stores from disk. Returns True if successful."""
        index_path = os.path.join(self.index_dir, "index.faiss")
        metadata_path = os.path.join(self.index_dir, "metadata.pkl")
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return False
            
        try:
            self.index = faiss.read_index(index_path)
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
                self.child_store = metadata["child_store"]
                self.parent_store = metadata["parent_store"]
            return True
        except Exception as e:
            print(f"Error loading FAISS store: {e}")
            return False
