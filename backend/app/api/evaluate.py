import chess
from fastapi import APIRouter, HTTPException, Path, Query

from app.models.chess import EvaluationResponse
from app.services.stockfish_engine import StockfishError, evaluate_position

router = APIRouter(prefix="/api/v1", tags=["Échecs"])


@router.get("/evaluate/{fen:path}", response_model=EvaluationResponse)
async def evaluate(
    fen: str = Path(..., description="Position FEN URL-encodée."),
    depth: int = Query(15, ge=1, le=30, description="Profondeur d'analyse Stockfish."),
) -> EvaluationResponse:
    """
    Évalue une position avec Stockfish, renvoie le meilleur coup et le score (centipions, POV blancs).
    """
    try:
        chess.Board(fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"FEN invalide: {exc}") from exc

    try:
        result = await evaluate_position(fen, depth=depth)
    except StockfishError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EvaluationResponse(fen=fen, **result)
