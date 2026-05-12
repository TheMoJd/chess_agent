"""Sanity-check la collection Milvus en exécutant quelques recherches vectorielles.

Pour chaque query du jeu de test, embed via OpenAI puis search dans Milvus
et affiche les top-3 hits avec leur score. Objectif : juger sémantiquement
si le retrieval est cohérent avant de bâtir l'endpoint /vector-search.

Préalable : avoir lancé `scripts/ingest_chunks.py` avec succès.

Usage :
    cd backend
    .venv/Scripts/python.exe scripts/check_vector_search.py
"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import Collection, connections, utility

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger("check_vector_search")

COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "wikichess_chunks")
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
MILVUS_HOST = os.environ.get("MILVUS_HOST_OVERRIDE", "localhost")
MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")

TOP_K = 3
SNIPPET_LEN = 180

# Chaque tuple = (query, ouverture attendue dans le top-1 idéalement).
# Mélange volontaire d'EN/FR et de formulations variées pour tester la robustesse.
TEST_QUERIES: list[tuple[str, str]] = [
    ("Sicilian Najdorof variation pawn structure", "Sicilian Defence"),
    ("Italian Game main line for white", "Italian Game"),
    ("Why is the Ruy Lopez called the Spanish Opening?", "Ruy Lopez"),
    ("Caro-Kann advance variation", "Caro-Kann Defence"),
    ("Comment jouer le London System avec les blancs", "London System"),
    ("King's Indian fianchetto setup", "King's Indian Defence"),
]


def embed_query(client: OpenAI, query: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    return response.data[0].embedding


def search(collection: Collection, query_vec: list[float], top_k: int) -> list[dict]:
    # ef = effort de recherche HNSW. Plus grand = plus précis et plus lent.
    # 32 est un bon défaut sur un index construit avec efConstruction=64.
    results = collection.search(
        data=[query_vec],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"ef": 32}},
        limit=top_k,
        output_fields=["opening_name", "section", "text", "source_url"],
    )
    # pymilvus 2.4 : on itère sur results (un Hits par vecteur de query),
    # puis sur chaque Hits. results[0] renvoie un SequenceIterator non
    # itérable directement — piège classique.
    hits_data: list[dict] = []
    for hits in results:
        for hit in hits:
            hits_data.append(
                {
                    "score": hit.score,
                    "opening_name": hit.entity.get("opening_name"),
                    "section": hit.entity.get("section") or "(intro)",
                    "text": hit.entity.get("text"),
                    "source_url": hit.entity.get("source_url"),
                }
            )
    return hits_data


def truncate(text: str, n: int) -> str:
    text = " ".join(text.split())  # collapse whitespace
    return text if len(text) <= n else text[: n - 1] + "…"


def normalize(s: str) -> str:
    """Pour comparer des titres : harmonise les tirets Unicode (en/em-dash) et la casse."""
    return s.replace("–", "-").replace("—", "-").lower().strip()


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or "REPLACE" in api_key:
        print("ERREUR : OPENAI_API_KEY manquante ou placeholder dans .env", file=sys.stderr)
        return 1

    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    if not utility.has_collection(COLLECTION_NAME):
        print(
            f"ERREUR : collection '{COLLECTION_NAME}' introuvable. "
            "Lance d'abord scripts/ingest_chunks.py.",
            file=sys.stderr,
        )
        return 1

    collection = Collection(COLLECTION_NAME)
    collection.load()  # charge l'index en RAM ; idempotent
    print(f"Collection '{COLLECTION_NAME}' chargée — {collection.num_entities} entités\n")

    client = OpenAI(api_key=api_key)
    successes = 0

    for query, expected in TEST_QUERIES:
        print(f"━━ Query: {query!r}")
        print(f"   Attendu (top-1) : {expected}")
        query_vec = embed_query(client, query)
        hits = search(collection, query_vec, TOP_K)

        top_match = normalize(hits[0]["opening_name"]) == normalize(expected)
        successes += int(top_match)
        flag = "✓" if top_match else "✗"
        print(f"   Résultat        : {flag}")

        for rank, hit in enumerate(hits, start=1):
            print(
                f"   #{rank}  score={hit['score']:.3f}  "
                f"[{hit['opening_name']} / {hit['section']}]"
            )
            print(f"        {truncate(hit['text'], SNIPPET_LEN)}")
        print()

    print(f"=== Résultat global : {successes}/{len(TEST_QUERIES)} top-1 corrects ===")
    connections.disconnect(alias="default")
    return 0 if successes == len(TEST_QUERIES) else 2


if __name__ == "__main__":
    sys.exit(main())
