from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BACKEND_PORT: int = 8000
    STOCKFISH_PATH: str = "/usr/games/stockfish"
    LICHESS_EXPLORER_BASE: str = "https://explorer.lichess.ovh"
    LICHESS_TIMEOUT_SECONDS: float = 10.0
    LOG_LEVEL: str = "INFO"


settings = Settings()
