from __future__ import annotations

import hashlib

import numpy as np

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional runtime dependency behavior
    SentenceTransformer = None


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        if not settings.use_mock_embeddings and SentenceTransformer is not None:
            self._model = SentenceTransformer(settings.embedding_model)

    @staticmethod
    def _mock_encode(text: str, dim: int = 384) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little", signed=False)
        rng = np.random.default_rng(seed)
        vector = rng.normal(size=dim).astype("float32")
        norm = np.linalg.norm(vector)
        return vector / (norm + 1e-12)

    def encode(self, text: str) -> np.ndarray:
        if self._model is None:
            return self._mock_encode(text)
        vector = np.array(self._model.encode(text), dtype="float32")
        norm = np.linalg.norm(vector)
        return vector / (norm + 1e-12)

