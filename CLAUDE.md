# Chess Agent — POC FFE

## Mission

POC d'un agent IA pour l'apprentissage des ouvertures aux échecs, commandé par la Fédération Française des Échecs (FFE) en vue des championnats d'Europe jeune. Mission OpenClassrooms (track AI Engineer), 2 semaines, livraison via démo locale `docker compose`.

## Architecture cible — pure agentique

LangGraph + LLM avec **tool-calling**. Le LLM est l'orchestrateur, pas un `if/else` codé en dur. Quatre tools exposés à l'agent (nommés par leur **capacité**, pas par leur fournisseur) :

- `opening_theory_lookup(fen)` — coups théoriques + nom de l'ouverture. Source actuelle : chessdb.cn (l'API Lichess Opening Explorer est indisponible depuis l'incident OVH de février 2026, voir [services/lichess.py](backend/app/services/lichess.py) pour réactivation future).
- `stockfish_evaluate(fen)` — meilleur coup + score (centipawns), utilisé hors théorie.
- `wikichess_search(query)` — RAG Milvus sur articles **Wikipedia** d'ouvertures (substitution de Wikichess, autorisée par l'énoncé « toutes sources pertinentes acceptées » ; justification dans [docs/architecture.md](docs/architecture.md#source-du-corpus-rag--wikichess--wikipedia)). Le nom du tool abstrait volontairement le fournisseur (cf. convention de naming plus bas).
- `find_chess_videos(opening_name)` — vidéos pertinentes (YouTube Data API v3).

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

- **Backend** : Python 3.11, FastAPI, LangGraph, python-chess, Stockfish, pymilvus, openai (embeddings + LLM), motor (Mongo async).
- **Vector DB** : Milvus.
- **Document DB** : MongoDB (sessions, historiques, caches d'API).
- **Frontend** : Angular 21 standalone components + Signals + Tailwind CSS v3 + `ngx-chess-board` (échiquier interactif) + `lucide-angular` (icônes).
- **Orchestration** : Docker Compose (local) + overlay `docker-compose.prod.yml` pour déploiement VPS derrière Caddy.

## Structure

```
chess_agent/
├── backend/
│   ├── .venv/              # Python 3.11 (gitignored)
│   ├── app/                # FastAPI + LangGraph (agent, api, services, models)
│   ├── scripts/            # ingest Wikichess, sanity checks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Angular 21 standalone + Tailwind v3 + ngx-chess-board
│   ├── src/app/components/ # board, chat-panel, message-bubble, reasoning-trace, tool-call-card, ...
│   ├── src/app/services/   # chat, chess, session
│   ├── src/app/models/     # chat, message, tool-meta (mapping tool → icône/couleur)
│   ├── Dockerfile          # multi-stage node→nginx
│   └── nginx.conf          # SPA fallback, pas de proxy /api (géré par Caddy en prod)
├── docker-compose.yml      # stack locale
├── docker-compose.prod.yml # overlay VPS (réseau "web" externe, ports retirés)
├── DEPLOY.md               # procédure déploiement VPS Hetzner + Caddy
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
- **Théorie avant Stockfish** : `opening_theory_lookup` est appelé en premier, Stockfish n'intervient qu'en cas de position hors théorie. La règle est portée par le system prompt de l'agent, pas par du code.
- **Naming des tools agent-side** : abstraire le fournisseur (ex: `opening_theory_lookup` plutôt que `chessdb_query`). Exception assumée : `stockfish_evaluate` car "Stockfish" est devenu un terme générique chez les joueurs d'échecs.

## Volet stratégique (étude, pas à coder)

Système avancé d'indexation vidéo via vision board→FEN exposé en serveur **MCP**, à concevoir comme livrable séparé :
- Note 8-10 pages (bénéfices/limites).
- Schéma d'architecture technique.
- Étude de faisabilité avec estimation des coûts (build + opex).

## Posture pour l'assistant

L'utilisateur est un étudiant OC AI Engineer qui apprend. Par défaut : **expliquer, guider, faire écrire le code à l'utilisateur**, pas générer la solution complète. Coder soi-même seulement les tâches de setup/méta (venv, configs, doc) ou sur demande explicite. Réponses en français.
