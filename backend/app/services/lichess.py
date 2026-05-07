"""Client async pour l'API Lichess Opening Explorer (base masters).

Note: au moment du POC (mai 2026), explorer.lichess.ovh est indisponible
(401/429 systématiques depuis l'incident OVH de février 2026, ticket lila #19610).
Ce service est conservé pour réactivation immédiate dès le rétablissement.
La source de théorie active est actuellement chessdb.cn (voir services/chessdb.py).
"""
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LichessError(Exception):
    """Échec d'appel à l'API Lichess."""


async def fetch_opening_moves(fen: str) -> dict[str, Any]:
    """
    Interroge la base "masters" de Lichess pour une position FEN.

    Returns:
        {
            "source": "lichess",
            "opening_name": str | None,
            "eco": str | None,
            "moves": list[{san, uci, white, draws, black, total_games, average_rating}]
        }

    Raises:
        LichessError: timeout, erreur réseau, ou réponse non-JSON.
    """
    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS, connect=5.0)
    url = f"{settings.LICHESS_EXPLORER_BASE}/masters"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params={"fen": fen})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Lichess request failed for fen=%s: %s", fen, exc)
        raise LichessError(str(exc)) from exc

    moves = [
        {
            "san": move["san"],
            "uci": move["uci"],
            "white": move["white"],
            "draws": move["draws"],
            "black": move["black"],
            "total_games": move["white"] + move["draws"] + move["black"],
            "average_rating": move.get("averageRating"),
        }
        for move in data.get("moves", [])
    ]
    opening = data.get("opening") or {}
    return {
        "source": "lichess",
        "opening_name": opening.get("name"),
        "eco": opening.get("eco"),
        "moves": moves,
    }
