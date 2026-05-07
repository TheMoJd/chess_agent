# Chess Agent — POC FFE

Agent IA d'apprentissage des ouvertures aux échecs, commandé par la Fédération Française des Échecs en vue des championnats d'Europe jeune. Mission OpenClassrooms (track AI Engineer).

Voir [docs/architecture.md](docs/architecture.md) pour la conception technique détaillée.

## Schémas d'architecture

Vues système, couches backend et boucle agent ReAct dessinées dans Excalidraw :
[ouvrir le tableau](https://excalidraw.com/#json=mDMOREdrkwWvQYZWon7PB,j3kwv2z4Gxbhm4jqGe81IQ)

## Prérequis

- Docker 24+
- Docker Compose v2

## Démarrage

```bash
cp .env.example .env
docker compose up --build
```

## Vérification

```bash
curl http://localhost:8000/api/v1/healthcheck
# → {"status":"ok"}
```

Documentation Swagger interactive : http://localhost:8000/docs

## Développement local (sans Docker)

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
