import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from pymilvus import Collection, connections, utility

from app.agent.builder import build_agent
from app.api.chat import router as chat_router
from app.api.evaluate import router as evaluate_router
from app.api.healthcheck import router as healthcheck_router
from app.api.moves import router as moves_router
from app.api.vector_search import router as vector_search_router
from app.api.videos import router as videos_router
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
    app.state.http_client = httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)

    # MongoDB pour les checkpoints LangGraph (persistance des sessions agent)
    mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    await mongo_client.admin.command("ping")  # fail fast si Mongo down
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
app.include_router(videos_router)
app.include_router(chat_router)
