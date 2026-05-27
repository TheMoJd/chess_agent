import chess
from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.deps import get_current_user
from app.models.chess import OpeningMovesResponse, TheoryMove
from app.models.user import UserPublic
from app.services.chessdb import ChessDBError, fetch_opening_moves

router = APIRouter(prefix="/api/v1", tags=["Échecs"])


@router.get("/moves/{fen:path}", response_model=OpeningMovesResponse)
async def get_theory_moves(
    fen: str = Path(..., description="Position FEN URL-encodée (slashes et espaces)."),
    user: UserPublic = Depends(get_current_user),  # noqa: ARG001 — auth requise, pas de quota
) -> OpeningMovesResponse:
    """
    Renvoie les coups théoriques connus pour la position donnée.

    Source: chessdb.cn (l'API Lichess Opening Explorer étant indisponible
    depuis février 2026 — voir services/chessdb.py).
    """
    try:
        chess.Board(fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"FEN invalide: {exc}") from exc

    try:
        result = await fetch_opening_moves(fen)
    except ChessDBError as exc:
        raise HTTPException(
            status_code=502, detail=f"chessdb.cn indisponible: {exc}"
        ) from exc

    return OpeningMovesResponse(
        fen=fen,
        source=result["source"],
        opening_name=result["opening_name"],
        eco=result["eco"],
        moves=[TheoryMove(**m) for m in result["moves"]],
    )
