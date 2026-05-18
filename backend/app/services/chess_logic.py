"""Utilitaires purs python-chess.

Service "ground truth" sans appels externes (pas d'API, pas de subprocess) :
juste la logique du jeu d'échecs via python-chess. Sert de garde-fou contre
les hallucinations du LLM — quand l'agent veut citer un coup, on lui force
le passage par cette liste de coups *réellement légaux* sur la position.
"""
from typing import Any

import chess


class ChessLogicError(Exception):
    """FEN invalide ou position incohérente."""


def list_legal_moves(fen: str) -> dict[str, Any]:
    """
    Retourne tous les coups légaux dans la position donnée, en notation SAN.

    Returns:
        {
            "side_to_move": "white" | "black",
            "moves": ["e4", "Nf3", ...],            # SAN international
            "is_check": bool,
            "is_game_over": bool,
            "result": str | None,                    # "1-0", "0-1", "1/2-1/2"
        }

    Raises:
        ChessLogicError: FEN invalide.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ChessLogicError(f"FEN invalide: {exc}") from exc

    moves_san = [board.san(m) for m in board.legal_moves]
    return {
        "side_to_move": "white" if board.turn else "black",
        "moves": moves_san,
        "is_check": board.is_check(),
        "is_game_over": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
    }
