"""Service auth : hash bcrypt + JWT HS256.

Choix techniques :
- **passlib[bcrypt]** plutôt qu'argon2 → c'est la stack de référence FastAPI,
  largement auditée. Argon2 serait préférable pour de la prod haute sensibilité,
  mais on n'en a pas besoin sur un POC.
- **HS256** (symétrique) pour le JWT : un seul service signe ET vérifie, pas
  besoin de la complexité d'une paire de clés (RS256/ES256).
- Payload JWT minimal : `sub` (user id), `email` (pratique pour debug et
  affichage front sans roundtrip /me), `iat`, `exp`.
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Schémas bcrypt — `deprecated="auto"` permettra de migrer (re-hash au login)
# si on change un jour d'algo sans casser les anciens hashes.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash un mot de passe en clair (bcrypt, cost 12 par défaut)."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mdp clair contre son hash. Renvoie False (jamais d'exception)
    si le hash est mal formé — pas la peine de leaker la nature de l'erreur."""
    try:
        return _pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(*, sub: str, email: str) -> str:
    """Crée un JWT signé HS256.

    Args:
        sub: identifiant unique (ObjectId user converti en string).
        email: email du user, inclus pour pouvoir l'afficher côté front sans
            avoir à requêter /me.

    Returns:
        Token JWT encodé.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Décode et valide un JWT. Lève `JWTError` si invalide (signature, exp...).

    Le caller (get_current_user) traduit l'exception en 401.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
