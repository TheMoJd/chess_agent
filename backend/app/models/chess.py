from pydantic import BaseModel, Field


class TheoryMove(BaseModel):
    san: str
    uci: str
    score_centipawns: int | None = Field(
        None, description="Score d'évaluation du coup (centipions, POV trait à jouer)."
    )
    rank: int | None = Field(
        None, description="Classement chessdb (0 = mauvais, plus haut = meilleur)."
    )
    note: str | None = Field(
        None, description="Annotation chess (!, ?, !!, etc.) si fournie par la source."
    )
    winrate: float | None = Field(
        None, description="Taux de victoire en pourcentage (0-100) si fourni."
    )


class OpeningMovesResponse(BaseModel):
    fen: str
    source: str = Field(..., description="Source de la donnée (chessdb.cn, lichess, ...).")
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
