"""Outils LangGraph pour l'agent tuteur d'échecs.

Chaque tool est un wrapper *fin* autour d'un service existant. Le naming est
**capacité-first** (cf. CLAUDE.md) : pas de mention de la source dans le nom,
sauf pour Stockfish (devenu terme générique chez les joueurs).

Principe d'erreur :
    Les tools ne lèvent PAS d'exception — ils renvoient les erreurs en JSON.
    Raison : LangGraph propage les exceptions et stoppe l'agent. En renvoyant
    {"error": "..."} le LLM peut décider de retry, basculer sur un autre tool,
    ou présenter une excuse à l'utilisateur. C'est la robustesse agentique.
"""
import json
import logging

import httpx
from langchain_core.tools import BaseTool, tool
from openai import AsyncOpenAI
from pymilvus import Collection

from app.services.chess_logic import (
    ChessLogicError,
    list_legal_moves as fetch_legal_moves,
)
from app.services.chessdb import ChessDBError, fetch_opening_moves
from app.services.stockfish_engine import StockfishError, evaluate_position
from app.services.wikichess import WikichessSearchError, search_chunks
from app.services.youtube import YouTubeError, search_videos

logger = logging.getLogger(__name__)


def _err(message: str) -> str:
    """Format JSON d'une erreur retournée au LLM."""
    return json.dumps({"error": message}, ensure_ascii=False)


def build_tools(
    *,
    milvus_collection: Collection,
    openai_client: AsyncOpenAI,
    http_client: httpx.AsyncClient,
) -> list[BaseTool]:
    """Construit la liste des 4 tools en capturant les dépendances via closure.

    Pattern factory : l'agent reçoit des tools prêts à l'emploi, sans connaître
    Milvus, OpenAI ou httpx. Testable en injectant des mocks à la place.

    Returns:
        Liste des 4 BaseTool LangChain, dans l'ordre d'usage pédagogique attendu
        (theory → engine → context → resources).
    """

    @tool
    async def opening_theory_lookup(fen: str) -> str:
        """Look up theoretical moves played by masters from a known opening database.

        Use this FIRST for any chess position. It returns the moves real players
        have chosen historically, with their win rates and statistical context.
        This is the canonical pedagogical source for opening guidance.

        Args:
            fen: chess position in FEN notation.

        Returns:
            JSON with: source, moves (list of {uci, san, score_centipawns, rank,
            note, winrate}), opening_name, eco. An empty 'moves' list means the
            position is OFF theory — fall back to stockfish_evaluate in that case.
        """
        try:
            result = await fetch_opening_moves(fen)
        except ChessDBError as exc:
            logger.warning("opening_theory_lookup failed for fen=%r: %s", fen, exc)
            return _err(f"Theory lookup failed: {exc}")
        except Exception as exc:
            logger.exception("opening_theory_lookup unexpected error fen=%r", fen)
            return _err(f"Theory lookup unavailable ({type(exc).__name__}).")
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def list_legal_moves(fen: str) -> str:
        """List ALL legal moves in the current position, in international SAN.

        Use this as a GUARDRAIL before citing ANY specific move (yours or the
        opponent's) that did not come from opening_theory_lookup.moves[] or
        stockfish_evaluate.best_move_san. The chess engine here is the source
        of truth — if a move isn't in this list, it's illegal, period.

        Args:
            fen: chess position in FEN notation.

        Returns:
            JSON with: side_to_move, moves (SAN list), is_check, is_game_over,
            result.
        """
        try:
            result = fetch_legal_moves(fen)
        except ChessLogicError as exc:
            logger.warning("list_legal_moves failed for fen=%r: %s", fen, exc)
            return _err(f"Legal-moves listing failed: {exc}")
        except Exception as exc:
            logger.exception("list_legal_moves unexpected error fen=%r", fen)
            return _err(f"Legal-moves unavailable ({type(exc).__name__}).")
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def stockfish_evaluate(fen: str) -> str:
        """Get the best move and centipawn evaluation from the Stockfish engine.

        Use this when the position is OFF theory (opening_theory_lookup returned
        an empty moves list) or when you specifically need the engine's objective
        assessment. Stockfish gives raw chess truth — translate it into pedagogical
        language for the young player.

        Args:
            fen: chess position in FEN notation.

        Returns:
            JSON with: best_move_uci, best_move_san, score_centipawns (POV white,
            negative = black winning), mate_in (None unless forced mate), depth.
        """
        try:
            result = await evaluate_position(fen)
        except StockfishError as exc:
            logger.warning("stockfish_evaluate failed for fen=%r: %s", fen, exc)
            return _err(f"Stockfish evaluation failed: {exc}")
        except Exception as exc:
            # Filet de sécurité : toute exception non prévue (NotImplementedError
            # côté event loop, OSError, etc.) doit rester DANS le tool. Sinon
            # LangGraph la décore avec son "Please fix your mistakes" qui finit
            # affiché à l'utilisateur — mauvaise expérience.
            logger.exception("stockfish_evaluate unexpected error fen=%r", fen)
            return _err(f"Stockfish unavailable ({type(exc).__name__}).")
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def wikichess_search(query: str) -> str:
        """Search semantic chess knowledge for context on openings, plans, and concepts.

        Use this when the user wants to UNDERSTAND a position or opening:
        history, typical pawn structures, strategic ideas, famous games. Returns
        the most relevant text chunks from Wikipedia articles on top openings.
        NOT for finding moves — use opening_theory_lookup or stockfish_evaluate.

        Args:
            query: free-form text, preferably English (e.g., "Sicilian Najdorf plans").

        Returns:
            JSON with: query, hits (list of {opening_name, section, text,
            source_url, score}). Empty 'hits' = no relevant content; rephrase.
        """
        try:
            chunks = await search_chunks(
                query, milvus_collection, openai_client, top_k=5
            )
        except WikichessSearchError as exc:
            logger.warning("wikichess_search failed for query=%r: %s", query, exc)
            return _err(f"Knowledge search failed: {exc}")
        except Exception as exc:
            logger.exception("wikichess_search unexpected error query=%r", query)
            return _err(f"Knowledge search unavailable ({type(exc).__name__}).")
        return json.dumps(
            {"query": query, "hits": [h.model_dump() for h in chunks]},
            ensure_ascii=False,
            default=str,
        )

    @tool
    async def find_chess_videos(opening_name: str) -> str:
        """Find YouTube tutorial videos for a specific chess opening.

        Use this ONLY when the user explicitly asks for a video, lesson, or
        external resource. Do not spam video links on every turn — the user is
        interacting with the board, not browsing YouTube.

        Args:
            opening_name: literal opening name (e.g., "Italian Game", "Sicilian Defence").

        Returns:
            JSON with: opening_name, query (server-enriched), items (list of
            {video_id, title, channel_title, description, url, thumbnail_url,
            published_at}).
        """
        try:
            query, items = await search_videos(
                opening_name, http_client, max_results=3
            )
        except YouTubeError as exc:
            logger.warning(
                "find_chess_videos failed for opening=%r: %s", opening_name, exc
            )
            return _err(f"Video search failed: {exc}")
        except Exception as exc:
            logger.exception(
                "find_chess_videos unexpected error opening=%r", opening_name
            )
            return _err(f"Video search unavailable ({type(exc).__name__}).")
        return json.dumps(
            {
                "opening_name": opening_name,
                "query": query,
                "items": [v.model_dump() for v in items],
            },
            ensure_ascii=False,
            default=str,
        )

    return [
        opening_theory_lookup,
        list_legal_moves,
        stockfish_evaluate,
        wikichess_search,
        find_chess_videos,
    ]
