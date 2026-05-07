"""Client async pour chessdb.cn — base d'ouvertures publique gratuite.

Source de théorie d'ouvertures retenue pour le POC. L'énoncé indique "API Lichess"
sans URL précise ; or l'API officielle d'ouvertures de Lichess (explorer.lichess.ovh)
est indisponible depuis février 2026 (incident infra OVH côté Lichess, ticket
lila #19610). chessdb.cn fournit une couverture équivalente sans authentification.
Le service `lichess.py` reste en place et pourra reprendre dès le rétablissement
de l'API upstream.
"""
import logging
from typing import Any

import chess
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ChessDBError(Exception):
    """Échec de requête chessdb.cn."""


_ERROR_TOKENS = {"invalid board", "unknown", "checkmate", "stalemate", "nobestmove"}


def _maybe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _maybe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_moves(text: str, board: chess.Board) -> list[dict[str, Any]]:
    """
    Parse le format text de chessdb.cn :
    'move:e7e5,score:-1,rank:2,note:! (29-14),winrate:49.92|move:...'
    """
    text = text.strip()
    if not text or text.lower() in _ERROR_TOKENS:
        return []

    parsed: list[dict[str, Any]] = []
    for entry in text.split("|"):
        fields: dict[str, str] = {}
        for kv in entry.split(","):
            key, sep, value = kv.partition(":")
            if not sep:
                continue
            fields[key.strip()] = value.strip()

        uci = fields.get("move")
        if not uci:
            continue
        try:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                continue
            san = board.san(move)
        except ValueError:
            logger.debug("Skipping unparseable move from chessdb: %s", uci)
            continue

        parsed.append(
            {
                "uci": uci,
                "san": san,
                "score_centipawns": _maybe_int(fields.get("score")),
                "rank": _maybe_int(fields.get("rank")),
                "note": fields.get("note"),
                "winrate": _maybe_float(fields.get("winrate")),
            }
        )
    return parsed


async def fetch_opening_moves(fen: str) -> dict[str, Any]:
    """
    Interroge chessdb.cn pour les coups connus à partir de la position FEN.

    Returns:
        {
            "source": "chessdb.cn",
            "moves": list[{uci, san, score_centipawns, rank, note, winrate}],
            "opening_name": None,
            "eco": None,
        }

    Raises:
        ChessDBError: FEN invalide, timeout, erreur réseau ou réponse non parsable.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ChessDBError(f"FEN invalide: {exc}") from exc

    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS, connect=5.0)
    url = f"{settings.CHESSDB_BASE}/cdb.php"
    params = {"action": "queryall", "board": fen}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            text = response.text
    except httpx.HTTPError as exc:
        logger.warning("chessdb request failed for fen=%s: %s", fen, exc)
        raise ChessDBError(str(exc)) from exc

    return {
        "source": "chessdb.cn",
        "moves": _parse_moves(text, board),
        "opening_name": None,
        "eco": None,
    }
