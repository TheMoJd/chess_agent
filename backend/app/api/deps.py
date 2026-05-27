"""Dependencies FastAPI partagées : DB Mongo, auth user, consommation quota.

Concentre toutes les briques d'auth ici :
- `get_db` : accès à la base Mongo (motor) via app.state.
- `get_current_user` : décode le JWT, charge l'utilisateur, renvoie 401 sinon.
- `consume_quota` : incrémente atomiquement le compteur, renvoie 429 si plafond
  atteint. À utiliser UNIQUEMENT sur les endpoints qui consomment des tokens
  OpenAI (essentiellement /chat).

Pattern d'usage :
    @router.post("/chat")
    async def chat(payload: ChatRequest, user=Depends(consume_quota)): ...
"""
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.config import settings
from app.models.user import UserPublic
from app.services.auth import JWTError, decode_access_token

# tokenUrl pointe vers /auth/login. Sert UNIQUEMENT à la doc Swagger
# (bouton "Authorize" génère le bon flow). N'impacte pas l'auth réelle.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=True)


async def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Renvoie la base Mongo configurée via lifespan.

    On passe par app.state.mongo_client plutôt que de réinstancier un client
    par requête (la connection pool de motor est globale et thread-safe).
    """
    return request.app.state.mongo_client[settings.MONGO_DB]


def _doc_to_public(doc: dict[str, Any]) -> UserPublic:
    """Convertit un document Mongo brut en UserPublic (sans password_hash)."""
    return UserPublic(
        id=str(doc["_id"]),
        email=doc["email"],
        messages_used=doc.get("messages_used", 0),
        quota=doc.get("quota", settings.MESSAGE_QUOTA_PER_USER),
        created_at=doc["created_at"],
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserPublic:
    """Décode le JWT et charge l'utilisateur correspondant.

    Lève 401 si :
    - token invalide (signature, expiration),
    - `sub` n'est pas un ObjectId valide,
    - user introuvable en base,
    - user inactif (`is_active=False`).

    Message d'erreur volontairement générique pour ne pas leak d'info.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise credentials_error from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise credentials_error

    try:
        user_oid = ObjectId(sub)
    except InvalidId as exc:
        raise credentials_error from exc

    doc = await db.users.find_one({"_id": user_oid, "is_active": True})
    if doc is None:
        raise credentials_error

    return _doc_to_public(doc)


async def consume_quota(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserPublic:
    """Incrémente messages_used si quota non atteint, sinon 429.

    Race condition gérée par `find_one_and_update` atomique + filtre
    `messages_used < quota` : deux POST /chat simultanés ne peuvent jamais
    dépasser le plafond (Mongo sérialise les writes sur le même document).

    Crash de l'agent APRÈS décrément : pas de rollback (cf. plan POC). Le
    compteur mesure les tentatives, ce qui est honnête : si l'agent a démarré
    sa réflexion il a déjà partiellement consommé des tokens OpenAI.
    """
    updated = await db.users.find_one_and_update(
        {"_id": ObjectId(user.id), "messages_used": {"$lt": user.quota}},
        {"$inc": {"messages_used": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Message quota exhausted ({user.quota}/{user.quota}). "
                "Contact admin to reset."
            ),
        )
    return _doc_to_public(updated)


__all__ = ["consume_quota", "get_current_user", "get_db", "oauth2_scheme"]
