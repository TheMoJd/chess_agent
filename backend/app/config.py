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
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_CHAT_TEMPERATURE: float = 0.3

    # YouTube Data API v3
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_API_BASE: str = "https://www.googleapis.com/youtube/v3"

    # MongoDB (LangGraph checkpoints)
    MONGO_HOST: str = "mongo"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "chess_agent"
    MONGO_HOST_OVERRIDE: str | None = None  # dev local hors Docker → "localhost"

    @property
    def mongo_uri(self) -> str:
        host = self.MONGO_HOST_OVERRIDE or self.MONGO_HOST
        return f"mongodb://{host}:{self.MONGO_PORT}"

    # Auth (JWT email/password) + quota par compte
    # JWT_SECRET DOIT être override en prod via .env (génération : openssl rand -hex 32).
    # La valeur par défaut "change-me-in-prod" sert au dev local uniquement.
    JWT_SECRET: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours

    # Quota total fixe par utilisateur (à vie, pas de reset auto).
    # Reset manuel via Mongo : db.users.updateOne({email}, {$set: {messages_used: 0}}).
    MESSAGE_QUOTA_PER_USER: int = 50

    # Rate-limit slowapi sur /auth/signup uniquement, syntaxe "<count>/<period>".
    SIGNUP_RATE_LIMIT: str = "5/hour"


settings = Settings()
