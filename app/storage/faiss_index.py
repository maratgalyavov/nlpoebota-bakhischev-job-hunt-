from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np


class FaissIndex:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.ids: list[str] = []

    def add(self, item_ids: list[str], vectors: np.ndarray) -> None:
        if vectors.dtype != np.float32:
            vectors = vectors.astype("float32")
        self.index.add(vectors)
        self.ids.extend(item_ids)

    def search(self, query: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
        if query.dtype != np.float32:
            query = query.astype("float32")
        query = query.reshape(1, -1)
        scores, idxs = self.index.search(query, top_k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self.ids):
                continue
            results.append((self.ids[idx], float(score)))
        return results

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, path)
        ids_path = f"{path}.ids"
        Path(ids_path).write_text("\n".join(self.ids), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "FaissIndex":
        index = faiss.read_index(path)
        ids = Path(f"{path}.ids").read_text(encoding="utf-8").splitlines()
        obj = cls(index.d)
        obj.index = index
        obj.ids = ids
        return obj
