"""
Vertex AI orqali matn embedding olish (gemini-embedding-001).

Muhim: gemini-embedding-001 "asimmetrik" model — hujjatni indekslashda
task_type="RETRIEVAL_DOCUMENT", foydalanuvchi savolini embedding qilishda
task_type="RETRIEVAL_QUERY" berilishi kerak. Aks holda qidiruv sifati pasayadi.
"""
import logging
import threading
import time

from django.conf import settings

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from google.api_core.exceptions import (
    ResourceExhausted,
    ServiceUnavailable,
    InternalServerError,
    TooManyRequests,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None

# MUHIM: avval bu yerda umuman qayta urinish bo'lmagan — Vertex AI vaqtinchalik
# xatolik bersa (masalan 503 ServiceUnavailable), savolga javob butun jarayoni
# HECH QANDAY qayta urinishsiz, tutilmagan (unhandled) xatolik bilan to'xtab
# qolardi. Endi llm.py'dagi generate_answer bilan bir xil, qayta urinish
# mantig'i qo'shildi — bu ham rag.py'dagi try/except orqali oxir-oqibat
# "sukut" (foydalanuvchiga hech narsa yubormaslik) bilan yakunlanadi.
_RETRYABLE_ERRORS = (ResourceExhausted, ServiceUnavailable, InternalServerError, TooManyRequests)


def _get_model() -> TextEmbeddingModel:
    global _model
    with _lock:
        if _model is None:
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
            _model = TextEmbeddingModel.from_pretrained(settings.VERTEX_EMBEDDING_MODEL)
    return _model


def _get_embeddings_with_retry(model, batch, max_retries: int = 8):
    attempt = 0
    while True:
        try:
            return model.get_embeddings(batch, output_dimensionality=settings.EMBEDDING_DIMENSIONS)
        except _RETRYABLE_ERRORS as exc:
            attempt += 1
            if attempt > max_retries:
                logger.warning(
                    "Vertex AI embedding %s marta urinishdan keyin ham xatolik berdi: %s",
                    attempt, exc,
                )
                raise
            # generate_answer'dagi bilan bir xil sabab — kutish vaqti
            # qisqartirildi, aks holda xatolik takrorlansa javob juda
            # sekinlashib ketardi.
            wait_seconds = min(0.6 * attempt, 3.0)
            logger.info(
                "Vertex AI embedding vaqtinchalik xatolik (%s-urinish), %.1f soniyadan keyin qayta urinamiz: %s",
                attempt, wait_seconds, exc,
            )
            time.sleep(wait_seconds)


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Bir nechta matnni embedding qilib qaytaradi. task_type:
    RETRIEVAL_DOCUMENT — hujjat bo'laklari uchun
    RETRIEVAL_QUERY    — foydalanuvchi savoli uchun
    """
    if not texts:
        return []

    model = _get_model()
    inputs = [TextEmbeddingInput(text=t, task_type=task_type) for t in texts]

    results: list[list[float]] = []
    # API bir martada juda ko'p matnni qabul qilmaydi — 16 tadan bo'lib yuboramiz
    batch_size = 16
    for i in range(0, len(inputs), batch_size):
        batch = inputs[i : i + batch_size]
        embeddings = _get_embeddings_with_retry(model, batch)
        results.extend(e.values for e in embeddings)
    return results


def embed_query(text: str) -> list[float]:
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]
