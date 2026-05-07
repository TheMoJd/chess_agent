from pydantic import BaseModel, Field


class TheoryMove(BaseModel):
    san: str
    uci: str
    white: int
    draws: int
    black: int
    total_games: int
    average_rating: int | None = None


class OpeningMovesResponse(BaseModel):
    fen: str
    opening_name: str | None = None
    eco: str | None = None
    moves: list[TheoryMove]


class EvaluationResponse(BaseModel):
    fen: str
    best_move_uci: str | None
    best_move_san: str | None
    score_centipawns: int | None = Field(
        None, description="Score Stockfish en centipions, du point de vue des blancs."
    )
    mate_in: int | None = Field(
        None, description="Nombre de coups jusqu'au mat (positif = blancs matent)."
    )
    depth: int
