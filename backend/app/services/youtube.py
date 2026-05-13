"""Recherche de vidéos YouTube via l'API Data v3.

Appel REST direct via httpx (déjà dans les deps). Le client AsyncClient
partagé est créé au lifespan et passé via app.state.http_client.
"""
import logging
from typing import Any

import httpx

from app.config import settings
from app.models.youtube import VideoItem

logger = logging.getLogger(__name__)


class YouTubeError(Exception):
    """Échec d'appel à l'API YouTube (clé invalide, quota épuisé, réseau...)."""


def _build_query(opening_name: str) -> str:
    """Enrichit le nom de l'ouverture pour cibler du contenu chess.

    Sans enrichissement, "Italian Game" remonte aussi des résultats non-chess.
    Les mots-clés "chess opening tutorial" cadrent fortement le contexte.
    """
    return f"{opening_name} chess opening tutorial"


def _parse_item(item: dict[str, Any]) -> VideoItem:
    snippet = item["snippet"]
    video_id = item["id"]["videoId"]
    thumbnails = snippet.get("thumbnails", {})
    thumb_url = (
        thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url", "")
    )
    return VideoItem(
        video_id=video_id,
        title=snippet["title"],
        description=snippet.get("description") or None,
        channel_title=snippet["channelTitle"],
        published_at=snippet["publishedAt"],
        thumbnail_url=thumb_url,
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


async def search_videos(
    opening_name: str,
    client: httpx.AsyncClient,
    max_results: int = 5,
) -> tuple[str, list[VideoItem]]:
    """Renvoie (query_effective, vidéos pertinentes).

    Args:
        opening_name: nom de l'ouverture (ex: "Italian Game").
        client: AsyncClient partagé (via app.state.http_client).
        max_results: 1-10 typiquement. Au-delà, YouTube facture plus de quota.

    Raises:
        YouTubeError: si l'API échoue (clé, quota, réseau, JSON malformé).
    """
    if not settings.YOUTUBE_API_KEY or "REPLACE" in settings.YOUTUBE_API_KEY:
        raise YouTubeError("YOUTUBE_API_KEY manquante ou placeholder dans .env")

    query = _build_query(opening_name)
    params = {
        "key": settings.YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "videoDuration": "medium",  # 4-20 min : sweet spot tuto, pas de shorts ni de streams 2h
        "maxResults": max_results,
        "relevanceLanguage": "en",  # le contenu chess EN est ~10× plus riche
    }
    url = f"{settings.YOUTUBE_API_BASE}/search"

    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("YouTube search failed for opening=%r: %s", opening_name, exc)
        raise YouTubeError(str(exc)) from exc

    items = [_parse_item(it) for it in data.get("items", [])]
    return query, items
