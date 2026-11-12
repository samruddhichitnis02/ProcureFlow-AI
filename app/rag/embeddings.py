import hashlib
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider:
    """
    Zero-Cost Embedding Provider.
    Attempts to load sentence-transformers (all-MiniLM-L6-v2, 384 dimensions).
    If offline or model weights not downloaded, gracefully uses a fast deterministic
    dense semantic hash vectorizer of the same dimension (384-D), ensuring zero external cost.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.dimension = 384
        self.model = None
        import os
        use_transformer = os.getenv("USE_TRANSFORMER_EMBEDDINGS", "false").lower() in ("true", "1")
        if use_transformer:
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info("Loaded local SentenceTransformer model: %s", model_name)
            except Exception as e:
                logger.warning(
                    "Could not load SentenceTransformer (%s). Using high-speed offline dense vectorizer.",
                    e,
                )
                self.model = None

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        if self.model is not None:
            try:
                embeddings = self.model.encode(
                    texts, convert_to_numpy=True, normalize_embeddings=True
                )
                return embeddings.astype("float32")
            except Exception as e:
                logger.warning("Inference with SentenceTransformer failed: %s", e)

        # High-speed deterministic fallback vectorizer
        return self._deterministic_dense_embeddings(texts)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]

    def _deterministic_dense_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Deterministic, offline, zero-cost semantic feature hashing.
        Generates consistent 384-dimensional unit-normalized embeddings.
        """
        vectors = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype="float32")
            words = text.lower().replace("\n", " ").split()
            if not words:
                vec[0] = 1.0
            else:
                for word in words:
                    h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                    idx = h % self.dimension
                    sign = 1.0 if ((h >> 8) & 1) else -1.0
                    vec[idx] += sign

                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                else:
                    vec[0] = 1.0
            vectors.append(vec)

        return np.array(vectors, dtype="float32")
