# Chess Agent — POC FFE

## Mission

POC d'un agent IA pour l'apprentissage des ouvertures aux échecs, commandé par la Fédération Française des Échecs (FFE) en vue des championnats d'Europe jeune. Mission OpenClassrooms (track AI Engineer), 2 semaines, livraison via démo locale `docker compose`.

## Architecture cible — pure agentique

LangGraph + LLM avec **tool-calling**. Le LLM est l'orchestrateur, pas un `if/else` codé en dur. Quatre tools exposés à l'agent :

- `lichess_opening_lookup(fen)` — coups théoriques + nom de l'ouverture (API Lichess).
- `stockfish_evaluate(fen)` — meilleur coup + score (centipawns), utilisé hors théorie.
- `wikichess_vector_search(query)` — RAG Milvus sur articles Wikichess.
- `youtube_search(opening_name)` — vidéos pertinentes (YouTube Data API v3).

La **chaîne de raisonnement de l'agent doit être visible** dans le panneau de droite du front (c'est le wow factor du POC).

## Scope produit

**Angle retenu** : tuteur conversationnel transparent (mode exploration libre). Layout chess.com-like : échiquier à gauche, panneau agent (chat + reasoning trace) à droite.

**MVP — must-have** :
- L'utilisateur joue les deux couleurs librement.
- À chaque coup, l'agent réagit dans le panneau de droite.
- Chat libre (texte) en plus des coups.
- Bouton retour arrière pour explorer des variantes.

**Stretch — only if time** : mode contre bot Stockfish bridé (un seul niveau, pas de chrono).

**Out of scope** : multi-niveaux de bots, profils joueur, ELO, time control, écrans fin de partie, multi-utilisateurs, auth.

## Stack

- **Backend** : Python 3.11, FastAPI, LangGraph, python-chess, Stockfish, pymilvus, sentence-transformers, motor (Mongo async).
- **Vector DB** : Milvus.
- **Document DB** : MongoDB (sessions, historiques, caches d'API).
- **Frontend** : Angular (Node 20 LTS) + ngx-chessboard.
- **Orchestration** : Docker Compose.

## Structure

```
chess_agent/
├── backend/
│   ├── .venv/              # Python 3.11 (gitignored)
│   ├── app/                # code FastAPI + LangGraph
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Angular app (à initialiser)
├── docker-compose.yml
├── .env.example            # variables documentées
└── enonce.md               # brief OC original (gitignored)
```

## Démarrage

```bash
cp .env.example .env
docker compose up --build
# Healthcheck : curl http://localhost:8000/api/v1/healthcheck
# Swagger : http://localhost:8000/docs
```

Pour itérer en local sans Docker (dev backend) :

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Conventions

- **Versions pinées** dans `requirements.txt` (`==X.Y.Z`), pas de `>=`.
- **Variables d'env** via `.env` (jamais commiter de secrets). `.env.example` à jour.
- **Endpoints** préfixés `/api/v1/`.
- **Stockfish** est un *outil* de l'agent, pas un adversaire (sauf en stretch).
- **Lichess avant Stockfish** : on consulte d'abord la théorie, on tombe sur Stockfish seulement hors théorie.

## Volet stratégique (étude, pas à coder)

Système avancé d'indexation vidéo via vision board→FEN exposé en serveur **MCP**, à concevoir comme livrable séparé :
- Note 8-10 pages (bénéfices/limites).
- Schéma d'architecture technique.
- Étude de faisabilité avec estimation des coûts (build + opex).

## Posture pour l'assistant

L'utilisateur est un étudiant OC AI Engineer qui apprend. Par défaut : **expliquer, guider, faire écrire le code à l'utilisateur**, pas générer la solution complète. Coder soi-même seulement les tâches de setup/méta (venv, configs, doc) ou sur demande explicite. Réponses en français.
