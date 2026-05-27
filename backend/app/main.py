import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from pymilvus import Collection, connections, utility
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.agent.builder import build_agent
from app.api.auth import register_auth_routes
from app.api.chat import router as chat_router
from app.api.evaluate import router as evaluate_router
from app.api.healthcheck import router as healthcheck_router
from app.api.moves import router as moves_router
from app.api.vector_search import router as vector_search_router
from app.api.videos import router as videos_router
from app.config import settings

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """Récupère l'IP réelle du client (gère X-Forwarded-For derrière Caddy).

    En prod le backend est derrière un reverse proxy : sans cette extraction,
    toutes les requêtes seraient comptabilisées comme venant de l'IP du proxy
    (= une seule clé pour tout le monde, le rate-limit deviendrait global).
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        # X-Forwarded-For peut chaîner plusieurs IPs : "client, proxy1, proxy2".
        # La première est celle du client d'origine.
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


# Limiter instancié au niveau module : slowapi a besoin d'une référence stable
# pour ses décorateurs. Pas de side-effect à l'import.
limiter = Limiter(key_func=_client_ip)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Réponse JSON propre quand un rate-limit slowapi est dépassé."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ouvre Milvus + OpenAI + Mongo au démarrage, ferme proprement à l'arrêt.

    Les clients sont attachés à app.state et réutilisés par tous les endpoints
    via request.app.state. Une seule connexion pour toute la vie du process.
    """
    connections.connect(
        alias="default",
        host=settings.milvus_host,
        port=str(settings.MILVUS_PORT),
    )
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        raise RuntimeError(
            f"Collection Milvus '{settings.MILVUS_COLLECTION}' absente. "
            "Lance d'abord `python scripts/ingest_chunks.py`."
        )
    collection = Collection(settings.MILVUS_COLLECTION)
    collection.load()
    app.state.milvus_collection = collection
    app.state.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    app.state.http_client = httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)

    # MongoDB : checkpoints LangGraph + collection users (auth)
    mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    await mongo_client.admin.command("ping")  # fail fast si Mongo down

    # Index unique sur users.email : garantit l'unicité au niveau DB,
    # évite la race condition d'un check applicatif "email existe-t-il ?".
    # `create_index` est idempotent → safe à appeler à chaque startup.
    await mongo_client[settings.MONGO_DB]["users"].create_index("email", unique=True)

    checkpointer = AsyncMongoDBSaver(mongo_client, db_name=settings.MONGO_DB)
    app.state.mongo_client = mongo_client
    app.state.checkpointer = checkpointer

    # Agent LangGraph avec checkpointer — sessions persistées dans Mongo
    app.state.agent = build_agent(
        milvus_collection=collection,
        openai_client=app.state.openai_client,
        http_client=app.state.http_client,
        checkpointer=checkpointer,
    )

    logger.info(
        "Lifespan startup: Milvus (%d entités), Mongo (%s), OpenAI, HTTP, agent (%s) prêts",
        collection.num_entities,
        settings.MONGO_DB,
        settings.OPENAI_CHAT_MODEL,
    )

    yield

    await app.state.http_client.aclose()
    app.state.mongo_client.close()
    connections.disconnect(alias="default")
    logger.info("Lifespan shutdown: HTTP fermé, Mongo fermé, Milvus déconnecté")


app = FastAPI(
    title="Chess Agent API",
    description="POC d'un agent IA d'apprentissage des ouvertures aux échecs (FFE).",
    version="0.1.0",
    lifespan=lifespan,
)

# Slowapi : rate-limiter par IP. Activé seulement sur /signup via le décorateur
# `@limiter.limit(...)` posé dans api/auth.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes auth : enregistrées via fonction parce que @limiter.limit doit voir
# l'instance limiter au moment du décorateur (pattern slowapi).
register_auth_routes(app, limiter)

app.include_router(healthcheck_router)
app.include_router(moves_router)
app.include_router(evaluate_router)
app.include_router(vector_search_router)
app.include_router(videos_router)
app.include_router(chat_router)
