from typing import List, Dict, Any, Tuple
from embeddings.embedder import OpenAIEmbedder
from retrieval.faiss_store import FAISSStore

class ParentChildRetriever:
    """
    RAG retriever that embeds queries, queries FAISS for matching child chunks,
    and then swaps the matching child chunks for their full parent markdown sheets.
    """
    def __init__(self, vector_store: FAISSStore, embedder: OpenAIEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant parent documents (full sheet markdown) based on a query.
        Returns:
            List[Dict]: A list of parent documents with relevance details.
            [
                {
                    "parent_id": str,
                    "text": str (full sheet markdown),
                    "sheet_name": str,
                    "workbook_name": str,
                    "score": float (highest score of its child chunk),
                    "matched_rows": List[str] (list of matched row indices/ranges)
                }
            ]
        """
        # Embed user query
        query_embedding = self.embedder.embed_query(query)
        if not query_embedding:
            return []

        # Find matching child chunks
        child_matches = self.vector_store.search(query_embedding, k=top_k)
        
        # Group by parent_id
        parents_grouped = {}
        for child_chunk, score in child_matches:
            parent_id = child_chunk.get("parent_id")
            if not parent_id:
                continue
                
            # If parent document is not in parent_store, skip
            parent_doc = self.vector_store.parent_store.get(parent_id)
            if not parent_doc:
                continue
                
            matched_row_info = child_chunk.get("metadata", {}).get("rows", "unknown")
            
            if parent_id not in parents_grouped:
                parents_grouped[parent_id] = {
                    "parent_id": parent_id,
                    "text": parent_doc["text"],
                    "sheet_name": parent_doc["metadata"]["sheet_name"],
                    "workbook_name": parent_doc["metadata"]["workbook_name"],
                    "score": score,
                    "matched_rows": [matched_row_info]
                }
            else:
                # Keep highest score
                parents_grouped[parent_id]["score"] = max(parents_grouped[parent_id]["score"], score)
                if matched_row_info not in parents_grouped[parent_id]["matched_rows"]:
                    parents_grouped[parent_id]["matched_rows"].append(matched_row_info)

        # Sort by relevance score descending
        sorted_parents = sorted(parents_grouped.values(), key=lambda x: x["score"], reverse=True)
        return sorted_parents
