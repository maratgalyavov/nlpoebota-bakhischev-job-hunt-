from __future__ import annotations


def chunk_text(text: str, max_len: int = 4000) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]
