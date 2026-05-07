from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Système"])


@router.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
