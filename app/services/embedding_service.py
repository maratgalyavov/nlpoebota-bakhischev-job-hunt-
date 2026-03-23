from __future__ import annotations

import hashlib
import logging

import numpy as np

from app.core.config import settings

try:
    import torch
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional runtime dependency behavior
    SentenceTransformer = None
    torch = None

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        self._device = self._resolve_device()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if settings.use_mock_embeddings or SentenceTransformer is None:
            return
        self._model = SentenceTransformer(settings.embedding_model, device=self._device)
        logger.info(
            "Embedding model loaded: model=%s device=%s",
            settings.embedding_model,
            self._device,
        )

    def warmup(self) -> None:
        self._ensure_model()

    @staticmethod
    def _resolve_device() -> str:
        requested = settings.embedding_device
        if requested != "auto":
            return requested
        if torch is not None:
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            if torch.cuda.is_available():
                return "cuda"
        return "cpu"

    @staticmethod
    def _mock_encode(text: str, dim: int = 384) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little", signed=False)
        rng = np.random.default_rng(seed)
        vector = rng.normal(size=dim).astype("float32")
        norm = np.linalg.norm(vector)
        return vector / (norm + 1e-12)

    def encode(self, text: str) -> np.ndarray:
        self._ensure_model()
        if self._model is None:
            return self._mock_encode(text)
        vector = np.array(self._model.encode(text), dtype="float32")
        norm = np.linalg.norm(vector)
        return vector / (norm + 1e-12)
