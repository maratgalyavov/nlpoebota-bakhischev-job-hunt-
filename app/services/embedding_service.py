from __future__ import annotations

import hashlib
import logging

import httpx
import numpy as np

from app.core.config import settings
from app.core.errors import ExternalServiceError

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
        self._provider = settings.embedding_provider
        self._api_key = settings.embedding_api_key or settings.llm_api_key
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._model_name = settings.embedding_model
        self._query_model_name = settings.embedding_query_model
        self._folder_id = settings.yandex_cloud_folder_id

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if settings.use_mock_embeddings or self._provider != "local" or SentenceTransformer is None:
            return
        self._model = SentenceTransformer(self._model_name, device=self._device)
        logger.info(
            "Embedding model loaded: model=%s device=%s",
            self._model_name,
            self._device,
        )

    def warmup(self) -> None:
        if self._provider == "local":
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
        return self.encode_many([text])[0]

    def encode_many(self, texts: list[str]) -> np.ndarray:
        return self._encode_many(texts, model_name=self._model_name)

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode_many(texts, model_name=self._query_model_name)

    def _encode_many(self, texts: list[str], model_name: str) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype="float32")

        if settings.use_mock_embeddings:
            return np.vstack([self._mock_encode(text) for text in texts]).astype("float32")

        if self._provider == "model_studio":
            return self._model_studio_encode_many(texts)

        if self._provider == "yandex_cloud":
            return self._yandex_cloud_encode_many(texts, model_name)

        self._ensure_model()
        if self._model is None:
            return np.vstack([self._mock_encode(text) for text in texts]).astype("float32")

        vectors = np.array(self._model.encode(texts), dtype="float32")
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / (norms + 1e-12)

    def _model_studio_encode_many(self, texts: list[str]) -> np.ndarray:
        if not self._api_key:
            raise ExternalServiceError(
                "Model Studio embeddings are not configured: EMBEDDING_API_KEY/LLM_API_KEY is empty."
            )

        payload = {
            "model": self._model_name,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                f"{self._base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            body = response.json()
            raw_items = body.get("data") or []
            vectors = [np.array(item["embedding"], dtype="float32") for item in raw_items]
            if len(vectors) != len(texts):
                raise ValueError("unexpected number of embeddings returned")
            matrix = np.vstack(vectors).astype("float32")
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            return matrix / (norms + 1e-12)
        except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime dependent
            detail = exc.response.text.strip()
            logger.error(
                "Model Studio embeddings failed: status=%s body=%s",
                exc.response.status_code,
                detail[:1000],
            )
            raise ExternalServiceError(
                f"Model Studio embeddings request failed with HTTP {exc.response.status_code}. "
                "Check API key, region/base URL, and workspace permissions."
            ) from exc
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.exception("Model Studio embeddings failed: %s", exc)
            raise ExternalServiceError("Model Studio embeddings request failed.") from exc

    def _resolve_yandex_embedding_model_uri(self, model_name: str) -> str:
        if model_name.startswith("emb://") or model_name.startswith("gpt://"):
            return model_name
        if not self._folder_id:
            raise ExternalServiceError(
                "Yandex Cloud embeddings are not configured: YANDEX_CLOUD_FOLDER_ID is empty."
            )
        return f"emb://{self._folder_id}/{model_name}/latest"

    def _yandex_cloud_encode_many(self, texts: list[str], model_name: str) -> np.ndarray:
        if not self._api_key:
            raise ExternalServiceError("Yandex Cloud embeddings are not configured: EMBEDDING_API_KEY/LLM_API_KEY is empty.")

        model_uri = self._resolve_yandex_embedding_model_uri(model_name)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "OpenAI-Project": self._folder_id,
        }
        vectors: list[np.ndarray] = []
        for text in texts:
            payload = {
                "model": model_uri,
                "input": text,
                "encoding_format": "float",
            }
            try:
                response = httpx.post(
                    f"{self._base_url}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=120.0,
                )
                response.raise_for_status()
                body = response.json()
                data = body.get("data") or []
                embedding = data[0].get("embedding") if data and isinstance(data[0], dict) else None
                if not isinstance(embedding, list) or not embedding:
                    raise ExternalServiceError("Yandex Cloud embeddings returned an empty vector.")
                vectors.append(np.array(embedding, dtype="float32"))
            except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime dependent
                detail = exc.response.text.strip()
                logger.error(
                    "Yandex Cloud embeddings failed: status=%s body=%s",
                    exc.response.status_code,
                    detail[:1000],
                )
                raise ExternalServiceError(
                    f"Yandex Cloud embeddings request failed with HTTP {exc.response.status_code}. "
                    "Check API key scope, folder ID, and model URI."
                ) from exc
            except ExternalServiceError:
                raise
            except Exception as exc:  # pragma: no cover - runtime dependent
                logger.exception("Yandex Cloud embeddings failed: %s", exc)
                raise ExternalServiceError("Yandex Cloud embeddings request failed.") from exc

        matrix = np.vstack(vectors).astype("float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / (norms + 1e-12)
