from fastapi import FastAPI

app = FastAPI(
    title="Chess Agent API",
    description="POC d'un agent IA d'apprentissage des ouvertures aux échecs (FFE).",
    version="0.1.0",
)


@app.get("/api/v1/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
