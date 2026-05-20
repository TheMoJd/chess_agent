"""Recherche sémantique RAG dans la base Wikichess (Milvus + OpenAI).

Pipeline :
    1. Embed la query via OpenAI (text-embedding-3-large).
    2. Cherche les top-k chunks les plus proches dans Milvus (HNSW, métrique IP).
    3. Mappe les hits en objets Pydantic `ChunkHit`.

Les clients OpenAI et Milvus sont **injectés** par la route (via app.state),
pas créés ici — voir le lifespan dans app/main.py.
"""
import logging
from typing import cast

from openai import AsyncOpenAI, OpenAIError
from pymilvus import Collection
from pymilvus.client.abstract import SearchResult
from pymilvus.exceptions import MilvusException

from app.config import settings
from app.models.rag import ChunkHit

logger = logging.getLogger(__name__)


class WikichessSearchError(Exception):
    """Échec d'une recherche sémantique (embedding indispo, Milvus down, etc.)."""


async def search_chunks(
    query: str,
    collection: Collection,
    client: AsyncOpenAI,
    top_k: int = 5,
    min_score: float = 0.4,
) -> list[ChunkHit]:
    """Renvoie les chunks Wikichess les plus pertinents pour `query`.

    Args:
        query: texte libre, EN ou FR.
        collection: collection Milvus déjà connectée et `.load()` au startup.
        client: client OpenAI async.
        top_k: nombre de résultats (1-20 typiquement).
        min_score: score IP minimal sous lequel un hit est jugé non pertinent
            et droppé. Défaut 0.4 (seuil "faible" documenté dans ChunkHit.score).
            Empêche l'agent de citer un chunk off-topic quand le RAG ne trouve
            pas mieux que des matches sémantiquement éloignés.

    Raises:
        WikichessSearchError: échec OpenAI ou Milvus (à transformer en 503 côté route).
    """
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=[query],
        )
    except OpenAIError as exc:
        logger.warning("OpenAI embedding failed for query=%r: %s", query, exc)
        raise WikichessSearchError(f"Embedding OpenAI indisponible: {exc}") from exc

    query_vec = response.data[0].embedding

    try:
        # cast() : le stub pymilvus déclare Union[SearchResult, SearchFuture].
        # Sans `_async=True` on a forcément un SearchResult (iterable), mais
        # Pylance ne sait pas narrow tout seul. Le cast lève l'ambiguïté.
        results = cast(
            SearchResult,
            collection.search(
                data=[query_vec],
                anns_field="embedding",
                param={"metric_type": "IP", "params": {"ef": 32}},
                limit=top_k,
                output_fields=["opening_name", "section", "text", "source_url"],
            ),
        )
    except MilvusException as exc:
        logger.warning("Milvus search failed for query=%r: %s", query, exc)
        raise WikichessSearchError(f"Search Milvus indisponible: {exc}") from exc

    hits: list[ChunkHit] = []
    for group in results:
        for hit in group:
            hits.append(
                ChunkHit(
                    opening_name=hit.entity.get("opening_name"),
                    section=hit.entity.get("section") or None,
                    text=hit.entity.get("text"),
                    source_url=hit.entity.get("source_url") or None,
                    score=hit.score,
                )
            )

    # Garde-fou anti-citation off-topic : on drop tout hit en dessous du seuil.
    # Si tous les hits sont faibles, on retourne une liste vide et l'agent
    # devra fallback gracefully (cf. system prompt).
    filtered = [h for h in hits if h.score >= min_score]
    if hits and not filtered:
        logger.info(
            "wikichess: all %d hits below min_score=%.2f for query=%r "
            "(top score was %.3f)",
            len(hits),
            min_score,
            query,
            hits[0].score,
        )
    return filtered
