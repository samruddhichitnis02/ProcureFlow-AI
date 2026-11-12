import os
import json
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import OrderReview
from app.rag.embeddings import LocalEmbeddingProvider
from app.config import settings

logger = logging.getLogger(__name__)


class FaissVectorStore:
    """
    High-performance vector store using FAISS CPU for zero-cost semantic search
    over order reviews, delivery disputes, and customer complaints.
    """

    def __init__(self, embedding_provider: Optional[LocalEmbeddingProvider] = None):
        self.embedder = embedding_provider or LocalEmbeddingProvider(settings.EMBEDDING_MODEL_NAME)
        self.dimension = self.embedder.dimension
        self.index = faiss.IndexFlatIP(self.dimension)  # Cosine similarity on unit vectors
        self.metadata: List[Dict[str, Any]] = []

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not texts:
            return
        vectors = self.embedder.embed_texts(texts)
        self.index.add(vectors)
        self.metadata.extend(metadatas)
        logger.info("Added %d documents to FAISS index. Total: %d", len(texts), self.index.ntotal)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant records based on cosine similarity.
        Returns empty list if index is empty.
        """
        if self.index.ntotal == 0 or not query.strip():
            return []

        query_vec = self.embedder.embed_query(query).reshape(1, -1)
        actual_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, actual_k)

        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = dict(self.metadata[idx])
            item["score"] = float(score)
            item["rank"] = rank + 1
            results.append(item)
        return results

    def build_from_db(self, db: Session, max_records: int = 5000) -> int:
        """
        Indexes customer reviews and dispute comments from the database.
        """
        reviews = (
            db.query(OrderReview)
            .filter(OrderReview.review_comment_message.isnot(None))
            .limit(max_records)
            .all()
        )

        texts = []
        metadatas = []
        for r in reviews:
            text = f"{r.review_comment_title or ''} - {r.review_comment_message or ''}".strip()
            if text:
                texts.append(text)
                metadatas.append({
                    "review_id": r.review_id,
                    "order_id": r.order_id,
                    "review_score": r.review_score,
                    "title": r.review_comment_title,
                    "comment": r.review_comment_message,
                    "date": r.review_creation_date.isoformat() if r.review_creation_date else None,
                })

        if texts:
            self.add_documents(texts, metadatas)
        return len(texts)

    def save(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None) -> None:
        idx_path = index_path or settings.FAISS_INDEX_PATH
        meta_path = metadata_path or settings.FAISS_METADATA_PATH
        os.makedirs(os.path.dirname(idx_path), exist_ok=True)

        faiss.write_index(self.index, idx_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info("Saved FAISS index to %s and metadata to %s", idx_path, meta_path)

    def load(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None) -> bool:
        idx_path = index_path or settings.FAISS_INDEX_PATH
        meta_path = metadata_path or settings.FAISS_METADATA_PATH

        if not os.path.exists(idx_path) or not os.path.exists(meta_path):
            return False

        try:
            self.index = faiss.read_index(idx_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info("Loaded FAISS index with %d vectors", self.index.ntotal)
            return True
        except Exception as e:
            logger.error("Failed to load FAISS index: %s", e)
            return False


# Global singleton instance
vector_store = FaissVectorStore()

