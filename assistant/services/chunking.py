"""Matnni RAG uchun bo'laklarga (chunk) bo'lish, overlap bilan."""
from django.conf import settings


def split_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
    overlap = overlap or settings.RAG_CHUNK_OVERLAP

    text = " ".join(text.split())  # ortiqcha bo'shliqlarni tozalash
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
