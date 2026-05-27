from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_current_user
from app.models.rag import VectorSearchResponse
from app.models.user import UserPublic
from app.services.wikichess import WikichessSearchError, search_chunks

router = APIRouter(prefix="/api/v1", tags=["RAG"])


@router.get("/vector-search", response_model=VectorSearchResponse)
async def vector_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Texte de la requête."),
    top_k: int = Query(3, ge=1, le=20, description="Nombre de résultats."),
    user: UserPublic = Depends(get_current_user),  # noqa: ARG001 — auth requise, pas de quota
) -> VectorSearchResponse:
    collection = request.app.state.milvus_collection
    client = request.app.state.openai_client

    try: 
        chunks = await search_chunks(q, collection, client, top_k=top_k)
    except WikichessSearchError as exc:
        raise HTTPException(status_code=503, detail=f"Recherche Wikichess indisponible: {exc}") from exc
    return VectorSearchResponse(query=q, top_k=top_k, hits=chunks)  
