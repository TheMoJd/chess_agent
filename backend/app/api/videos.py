"""Route /api/v1/videos/{opening_name} — recherche YouTube pour une ouverture."""
import httpx
from fastapi import APIRouter, HTTPException, Path, Query, Request

from app.models.youtube import VideosResponse
from app.services.youtube import YouTubeError, search_videos

router = APIRouter(prefix="/api/v1", tags=["YouTube"])


@router.get("/videos/{opening_name}", response_model=VideosResponse)
async def get_videos(
    request: Request,
    opening_name: str = Path(
        ..., min_length=1, description="Nom de l'ouverture (ex: 'Italian Game')."
    ),
    max_results: int = Query(
        5, ge=1, le=10, description="Nombre de vidéos à retourner (1-10)."
    ),
) -> VideosResponse:
    client: httpx.AsyncClient = request.app.state.http_client
    try:
        query, items = await search_videos(opening_name, client, max_results=max_results)
    except YouTubeError as exc:
        raise HTTPException(
            status_code=503, detail=f"YouTube indisponible: {exc}"
        ) from exc
    return VideosResponse(opening_name=opening_name, query=query, items=items)
