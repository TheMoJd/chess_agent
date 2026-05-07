from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.evaluate import router as evaluate_router
from app.api.healthcheck import router as healthcheck_router
from app.api.moves import router as moves_router

app = FastAPI(
    title="Chess Agent API",
    description="POC d'un agent IA d'apprentissage des ouvertures aux échecs (FFE).",
    version="0.1.0",
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
