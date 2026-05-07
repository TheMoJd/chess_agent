from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BACKEND_PORT: int = 8000
    STOCKFISH_PATH: str = "/usr/games/stockfish"

    # Sources de théorie d'ouvertures
    CHESSDB_BASE: str = "https://www.chessdb.cn"
    LICHESS_EXPLORER_BASE: str = "https://explorer.lichess.ovh"

    HTTP_TIMEOUT_SECONDS: float = 10.0
    LOG_LEVEL: str = "INFO"


settings = Settings()
