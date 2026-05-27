"""Routes d'authentification : signup, login, me.

`/signup` est le seul endpoint rate-limité (par IP via slowapi) : on accepte
le self-signup libre, mais on borne la création de comptes pour éviter qu'un
script ne crée 1000 comptes en 5 secondes.

`/login` et `/me` ne sont PAS rate-limités : un mot de passe correctement hashé
(bcrypt cost 12) est lui-même une protection naturelle contre le bruteforce
(~250ms par tentative). Si besoin futur de durcir, on ajoutera un rate-limit
plus intelligent (fail2ban style sur IP+email).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from slowapi import Limiter

from app.api.deps import _doc_to_public, get_current_user, get_db
from app.config import settings
from app.models.user import Token, UserCreate, UserLogin, UserPublic
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _build_token(user: UserPublic) -> Token:
    """Crée un Token (JWT + UserPublic) à partir d'un user fraîchement chargé."""
    jwt = create_access_token(sub=user.id, email=user.email)
    return Token(access_token=jwt, user=user)


def register_auth_routes(app, limiter: Limiter) -> None:
    """Attache les routes auth à l'app FastAPI avec le rate-limiter slowapi.

    On enregistre les routes en deux temps (router + décorateur slowapi) parce
    que `@limiter.limit(...)` doit être appliqué après l'instanciation du
    Limiter (qui se fait dans le lifespan, pas à l'import). C'est plus propre
    que le pattern global module-level.
    """

    @router.post(
        "/signup",
        response_model=Token,
        status_code=status.HTTP_201_CREATED,
        summary="Inscription email/mot de passe",
    )
    @limiter.limit(settings.SIGNUP_RATE_LIMIT)
    async def signup(
        request: Request,  # noqa: ARG001 — requis par slowapi pour extraire l'IP
        payload: UserCreate,
        db: AsyncIOMotorDatabase = Depends(get_db),
    ) -> Token:
        """Crée un compte. 409 si l'email est déjà pris, 429 si l'IP a abusé."""
        now = datetime.now(timezone.utc)
        doc = {
            "email": payload.email.lower(),
            "password_hash": hash_password(payload.password),
            "messages_used": 0,
            "quota": settings.MESSAGE_QUOTA_PER_USER,
            "created_at": now,
            "is_active": True,
        }
        try:
            result = await db.users.insert_one(doc)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            ) from exc

        doc["_id"] = result.inserted_id
        user = _doc_to_public(doc)
        logger.info("New user signup: %s (id=%s)", user.email, user.id)
        return _build_token(user)

    @router.post("/login", response_model=Token, summary="Connexion email/mot de passe")
    async def login(
        payload: UserLogin,
        db: AsyncIOMotorDatabase = Depends(get_db),
    ) -> Token:
        """401 générique en cas d'échec (email inconnu OU mot de passe faux).

        Volontaire : un message distinct "email inconnu" / "mdp invalide"
        permettrait à un attaquant d'énumérer les emails enregistrés.
        """
        doc = await db.users.find_one(
            {"email": payload.email.lower(), "is_active": True}
        )
        if doc is None or not verify_password(payload.password, doc["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _build_token(_doc_to_public(doc))

    @router.get("/me", response_model=UserPublic, summary="Profil de l'utilisateur connecté")
    async def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        """Renvoie l'utilisateur courant + son compteur de quota live.

        Appelé par le front après chaque /chat OK pour rafraîchir le badge
        `messages_used / quota` dans le header.
        """
        return user

    app.include_router(router)
