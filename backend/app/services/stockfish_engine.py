"""Wrapper async pour Stockfish via python-chess UCI.

Implémentation : on utilise `SimpleEngine.popen_uci` (synchrone, basé sur
subprocess.Popen) plutôt que `chess.engine.popen_uci` (asynchrone, basé sur
asyncio.subprocess_exec). Raison : sur Windows, uvicorn force la boucle
WindowsSelectorEventLoop qui ne supporte PAS les subprocesses asyncio
(NotImplementedError). L'API SimpleEngine, elle, marche partout.

On l'exécute via `asyncio.to_thread` pour ne pas bloquer la boucle async :
le subprocess tourne dans un thread worker pendant que la boucle reste libre.
"""
import asyncio
import logging
from typing import Any

import chess
import chess.engine

from app.config import settings

logger = logging.getLogger(__name__)


class StockfishError(Exception):
    """Échec d'évaluation Stockfish."""


def _evaluate_sync(fen: str, depth: int) -> dict[str, Any]:
    """Variante synchrone, à appeler dans un thread via asyncio.to_thread."""
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise StockfishError(f"FEN invalide: {exc}") from exc

    if board.is_game_over():
        raise StockfishError("La partie est déjà terminée.")

    try:
        engine = chess.engine.SimpleEngine.popen_uci(settings.STOCKFISH_PATH)
    except (FileNotFoundError, PermissionError) as exc:
        raise StockfishError(
            f"Binaire Stockfish introuvable à {settings.STOCKFISH_PATH}: {exc}"
        ) from exc

    try:
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
    except chess.engine.EngineError as exc:
        raise StockfishError(f"Erreur engine: {exc}") from exc
    finally:
        engine.quit()

    score_white = info["score"].white()
    pv = info.get("pv") or []
    best_move = pv[0] if pv else None

    return {
        "best_move_uci": best_move.uci() if best_move else None,
        "best_move_san": board.san(best_move) if best_move else None,
        "score_centipawns": score_white.score(),
        "mate_in": score_white.mate(),
        "depth": depth,
    }


async def evaluate_position(fen: str, depth: int = 15) -> dict[str, Any]:
    """
    Lance Stockfish sur une position FEN et renvoie son évaluation.

    Returns:
        {
            "best_move_uci": str | None,
            "best_move_san": str | None,
            "score_centipawns": int | None,   # POV blancs
            "mate_in": int | None,            # POV blancs
            "depth": int
        }

    Raises:
        StockfishError: FEN invalide, partie terminée, ou échec de l'engine.
    """
    return await asyncio.to_thread(_evaluate_sync, fen, depth)
