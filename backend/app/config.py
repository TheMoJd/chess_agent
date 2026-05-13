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

    # Milvus
    MILVUS_HOST: str = "milvus"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "wikichess_chunks"
    # Override pour le dev local hors Docker : MILVUS_HOST_OVERRIDE=localhost
    # (le service `milvus` n'existe en DNS que sur le réseau Docker `chess_net`).
    MILVUS_HOST_OVERRIDE: str | None = None

    @property
    def milvus_host(self) -> str:
        """Hostname Milvus effectif (override > config)."""
        return self.MILVUS_HOST_OVERRIDE or self.MILVUS_HOST

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_EMBEDDING_DIM: int = 3072


settings = Settings()
