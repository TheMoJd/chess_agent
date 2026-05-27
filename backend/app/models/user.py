"""Schémas Pydantic pour l'auth utilisateur (signup, login, /me) + JWT.

Convention :
- `UserCreate` / `UserLogin` : payloads d'entrée du client.
- `UserPublic` : payload SAFE renvoyé au client (jamais le hash mdp).
- `UserInDB` : représentation interne, utilisée pour mapper depuis Mongo.
- `Token` : enveloppe retournée par signup/login.

Les champs `messages_used` et `quota` ne sont JAMAIS modifiés via API : ils
sont gérés côté backend (consume_quota → find_one_and_update atomique).
"""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Payload de POST /api/v1/auth/signup."""

    email: EmailStr = Field(..., description="Email unique (sert d'identifiant).")
    password: Annotated[str, Field(min_length=8, max_length=128)] = Field(
        ...,
        description=(
            "Mot de passe en clair (transmis via HTTPS en prod). Stocké hashé "
            "(bcrypt) côté serveur. 8 caractères minimum."
        ),
    )


class UserLogin(BaseModel):
    """Payload de POST /api/v1/auth/login.

    Pas de contrainte sur la longueur du mdp pour ne pas leaker la politique :
    si on rejetait un login sur "password trop court", un attaquant saurait
    déjà que ce mdp n'est pas le bon sans avoir à hash-comparer.
    """

    email: EmailStr
    password: str


class UserPublic(BaseModel):
    """Représentation SAFE d'un utilisateur (jamais le hash). Renvoyé par /me."""

    id: str = Field(..., description="ObjectId Mongo sérialisé en string.")
    email: EmailStr
    messages_used: int = Field(..., ge=0, description="Compteur de messages /chat consommés.")
    quota: int = Field(..., ge=0, description="Plafond total à vie pour ce compte.")
    created_at: datetime


class Token(BaseModel):
    """Réponse de signup/login : JWT + infos user pour amorçage côté front."""

    access_token: str
    token_type: str = Field(default="bearer", description="Toujours 'bearer' (spec OAuth2).")
    user: UserPublic
