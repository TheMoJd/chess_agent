"""Schémas Pydantic pour l'API."""

from pydantic import BaseModel, Field

class ChunkHit(BaseModel):
    opening_name: str = Field(
        ..., description="Nom de l'ouverture (titre de l'article Wikipedia source)."
    )
    section: str | None = Field(
        None,
        description=(
            "Section de l'article (titre H2). None pour les chunks d'introduction "
            "(texte avant la première section)."
        ),
    )
    text: str = Field(..., description="Contenu textuel du chunk.")
    source_url: str | None = Field(
        None, description="URL Wikipedia de l'article source."
    )
    score: float = Field(
        ...,
        description=(
            "Similarité inner-product avec la query. Vecteurs L2-normalisés → "
            "équivalent cosinus. Repères : >0.65 très pertinent, 0.5-0.65 "
            "pertinent, <0.4 faible."
        ),
    )


class VectorSearchResponse(BaseModel):
    query: str = Field(..., description="Requête originale (echo, utile pour le debug).")
    top_k: int = Field(..., description="Nombre de résultats demandés.")
    hits: list[ChunkHit] = Field(
        ..., description="Chunks les plus pertinents, triés par score décroissant."
    )