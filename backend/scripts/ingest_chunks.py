"""Ingère les chunks Wikichess dans Milvus avec embeddings OpenAI.

Pipeline:
    1. Charger les chunks depuis JSONL              (déjà codé)
    2. Calculer leurs embeddings via OpenAI         ◀ TODO 1: embed_batch()
    3. (Re)créer la collection Milvus + index HNSW  (déjà codé)
    4. Insérer les vecteurs + métadonnées           ◀ TODO 2: insert_batch()
    5. Logger le résumé                              (déjà codé)

Préalable : avoir lancé `scripts/chunk_wikichess.py` et avoir une OPENAI_API_KEY
valide dans le .env de la racine du projet.

Usage :
    cd backend
    .venv/bin/python scripts/ingest_chunks.py

(Le script tourne depuis le host et attaque Milvus via le port mappé localhost:19530.)
"""
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

# Charge .env depuis la racine du projet (../../.env relatif au script)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingest_chunks")

# === Configuration ===
CHUNKS_FILE = Path(__file__).resolve().parent.parent / "data" / "wikichess_chunks.jsonl"
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "wikichess_chunks")
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIM = int(os.environ.get("OPENAI_EMBEDDING_DIM", "3072"))

# Quand on lance le script depuis le host (hors docker), on cible le port mappé.
MILVUS_HOST = os.environ.get("MILVUS_HOST_OVERRIDE", "localhost")
MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")

# OpenAI accepte jusqu'à 2048 inputs par batch. 50 est confortable et limite
# l'impact d'une éventuelle erreur transitoire.
BATCH_SIZE = 50

# Limites VarChar Milvus (coût mémoire ↗ avec max_length, on dimensionne au juste)
MAX_TEXT_LEN = 30000
MAX_OPENING_LEN = 200
MAX_SECTION_LEN = 200
MAX_URL_LEN = 500


def load_chunks(path: Path) -> list[dict]:
    """Charge les chunks depuis le fichier JSONL produit par chunk_wikichess.py."""
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {path}. Run scripts/chunk_wikichess.py first."
        )
    chunks = [json.loads(line) for line in path.open("r", encoding="utf-8")]
    logger.info("Loaded %d chunks from %s", len(chunks), path.name)
    return chunks


def get_or_create_collection() -> Collection:
    """(Re)crée la collection Milvus avec son schéma + index HNSW.

    Pour l'idempotence du POC, on drop+recreate à chaque exécution.
    En prod tu ferais un upsert par chunk_id stable, pas un drop.
    """
    if utility.has_collection(COLLECTION_NAME):
        logger.info("Collection '%s' exists — dropping for fresh ingest", COLLECTION_NAME)
        utility.drop_collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        FieldSchema(name="opening_name", dtype=DataType.VARCHAR, max_length=MAX_OPENING_LEN),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=MAX_SECTION_LEN),
        FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=MAX_URL_LEN),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=MAX_TEXT_LEN),
    ]
    schema = CollectionSchema(fields, description="Wikichess article chunks for RAG")
    collection = Collection(name=COLLECTION_NAME, schema=schema)

    # Index HNSW sur le vecteur. Métrique IP (inner product) = cosine pour
    # vecteurs normalisés, et OpenAI text-embedding-3-* renvoie déjà des
    # vecteurs L2-normalisés.
    index_params = {
        "metric_type": "IP",
        "index_type": "HNSW",
        "params": {"M": 8, "efConstruction": 64},
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    logger.info(
        "Created collection '%s' (HNSW, metric=IP, dim=%d)",
        COLLECTION_NAME,
        EMBEDDING_DIM,
    )
    return collection


# ============================================================================
# TODO 1 — à toi
# ============================================================================
def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Calcule les embeddings d'un batch de textes via l'API OpenAI.

    Args:
        client: instance OpenAI déjà authentifiée.
        texts: liste de textes à embedder (1 à 50 par appel typiquement).

    Returns:
        Liste de vecteurs (un par texte d'entrée), dans le même ordre.
        Chaque vecteur = list[float] de dimension EMBEDDING_DIM.
    """
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    # on trie les embeddngs pour correspondre à l'ordre des chunks 
    sorted_data = sorted(response.data, key=lambda e: e.index)
    return [e.embedding for e in sorted_data]

# ============================================================================
# TODO 2 — à toi
# ============================================================================
def insert_batch(
    collection: Collection, chunks: list[dict], embeddings: list[list[float]]
) -> int:
    """Insère un batch de chunks (avec leurs embeddings) dans Milvus.

    Args:
        collection: objet Collection pymilvus déjà créé.
        chunks: liste de dicts {opening_name, section, source_url, chunk_index, text}.
        embeddings: liste de vecteurs alignée sur `chunks`.

    Returns:
        Nombre d'entités insérées.

    """
    rows = [
        {
            "embedding": e,
            "opening_name": c["opening_name"],
            "section": c["section"] or "",
            "source_url": c["source_url"] or "",
            "chunk_index": c["chunk_index"],
            "text": c["text"],
        }
        for c, e in zip(chunks, embeddings)
    ]
    result = collection.insert(rows)
    return result.insert_count


# ============================================================================


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or "REPLACE" in api_key:
        logger.error("OPENAI_API_KEY missing or placeholder in .env")
        return 1

    chunks = load_chunks(CHUNKS_FILE)

    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    logger.info("Connected to Milvus at %s:%s", MILVUS_HOST, MILVUS_PORT)

    collection = get_or_create_collection()
    client = OpenAI(api_key=api_key)

    total_inserted = 0
    for offset in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[offset : offset + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        logger.info("Embedding batch [%d..%d]...", offset, offset + len(batch))
        embeddings = embed_batch(client, texts)

        if len(embeddings) != len(batch):
            logger.error(
                "Embedding count mismatch: expected %d, got %d", len(batch), len(embeddings)
            )
            return 1

        n = insert_batch(collection, batch, embeddings)
        total_inserted += n
        logger.info("  ✓ %d inserted (cumul %d/%d)", n, total_inserted, len(chunks))

    collection.flush()
    collection.load()
    logger.info("Final entity count: %d", collection.num_entities)
    connections.disconnect(alias="default")
    return 0


if __name__ == "__main__":
    sys.exit(main())
