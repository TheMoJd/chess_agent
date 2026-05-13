"""Schémas Pydantic pour l'API de recherche YouTube."""
from pydantic import BaseModel, Field


class VideoItem(BaseModel):
    video_id: str = Field(
        ..., description="ID YouTube de la vidéo (utile pour un player embed)."
    )
    title: str = Field(..., description="Titre de la vidéo.")
    description: str | None = Field(
        None, description="Snippet de description (peut être vide)."
    )
    channel_title: str = Field(..., description="Nom de la chaîne YouTube.")
    published_at: str = Field(
        ..., description="Date de publication au format ISO 8601."
    )
    thumbnail_url: str = Field(
        ..., description="URL de la miniature (qualité 'medium' ~320×180px)."
    )
    url: str = Field(
        ..., description="URL complète watch?v=... à ouvrir dans un nouvel onglet."
    )


class VideosResponse(BaseModel):
    opening_name: str = Field(..., description="Nom de l'ouverture (echo de la requête).")
    query: str = Field(
        ..., description="Query effectivement envoyée à YouTube après enrichissement."
    )
    items: list[VideoItem] = Field(
        ..., description="Vidéos triées par pertinence YouTube (algo propriétaire)."
    )
