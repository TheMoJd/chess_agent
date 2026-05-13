import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pymilvus import Collection, connections, utility

from app.api.evaluate import router as evaluate_router
from app.api.healthcheck import router as healthcheck_router
from app.api.moves import router as moves_router
from app.api.vector_search import router as vector_search_router
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ouvre Milvus + OpenAI au démarrage, ferme proprement à l'arrêt.

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
    logger.info(
        "Lifespan startup: Milvus connecté (%d entités), OpenAI prêt",
        collection.num_entities,
    )

    yield

    connections.disconnect(alias="default")
    logger.info("Lifespan shutdown: Milvus déconnecté")


app = FastAPI(
    title="Chess Agent API",
    description="POC d'un agent IA d'apprentissage des ouvertures aux échecs (FFE).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthcheck_router)
app.include_router(moves_router)
app.include_router(evaluate_router)
app.include_router(vector_search_router)
