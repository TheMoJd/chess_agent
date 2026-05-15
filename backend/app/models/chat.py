"""Schémas Pydantic pour l'endpoint /chat (avec checkpoints LangGraph)."""
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifiant de session (UUID généré côté front). L'historique de "
            "conversation est persisté en Mongo par session — le front n'envoie "
            "que le nouveau message à chaque tour."
        ),
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Nouveau message de l'utilisateur (texte libre).",
    )
    fen: str | None = Field(
        None,
        description="Position FEN courante. Injectée comme contexte du tour.",
    )


class ToolCallTrace(BaseModel):
    name: str = Field(..., description="Nom du tool appelé (ex: 'opening_theory_lookup').")
    args: dict[str, Any] = Field(
        ..., description="Arguments passés au tool (ex: {'fen': '...'})."
    )
    result: str = Field(..., description="Résultat brut renvoyé par le tool (JSON string).")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Echo du session_id (utile pour le debug front).")
    reply: str = Field(..., description="Réponse finale de l'agent à afficher dans le chat.")
    tool_calls: list[ToolCallTrace] = Field(
        ...,
        description=(
            "Trace des appels de tools dans l'ordre d'exécution. "
            "À afficher dans le panneau de raisonnement."
        ),
    )
