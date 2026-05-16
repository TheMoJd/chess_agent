# Déploiement Chess Agent sur VPS Hetzner

Ce guide concerne le **déploiement en production** sur le VPS Hetzner (CX22, Ubuntu 24.04, 46.224.117.225) avec Caddy global comme reverse-proxy.

Pour le développement local, voir [README.md](README.md).

---

## Architecture

```
                Internet
                   │
                   ▼
           chess.duckdns.org (HTTPS)
                   │
                   ▼
            ┌──────────────┐
            │ Caddy global │  ← terminaison HTTPS (Let's Encrypt auto)
            └──────┬───────┘
                   │ réseau Docker "web"
        ┌──────────┴──────────┐
        ▼                     ▼
  /api/*, /docs               /
        │                     │
        ▼                     ▼
   ┌─────────┐          ┌──────────┐
   │ backend │          │ frontend │
   │ FastAPI │          │  nginx   │
   └────┬────┘          └──────────┘
        │
        │ réseau Docker "chess_net"
        ├──────────┬─────────┐
        ▼          ▼         ▼
     Milvus     MongoDB    etcd/minio
```

Le **frontend** sert uniquement les statics Angular (pas de proxy /api dedans). Caddy fait la séparation `/api/*` → backend, reste → frontend.

---

## Setup one-time

### 1. DNS DuckDNS

Sur https://www.duckdns.org :
- Domaine : `chess` (donne `chess.duckdns.org`)
- IP : `46.224.117.225`
- Sauver

Vérifier la propagation (~1-2 min) :
```bash
nslookup chess.duckdns.org
```

### 2. Cloner le repo sur le VPS

```bash
ssh utilisateur@46.224.117.225
mkdir -p ~/apps
cd ~/apps
git clone <url-du-repo>.git chess-agent
cd chess-agent
```

### 3. Configurer `.env` de prod

```bash
cp .env.example .env
nano .env
```

Remplir au minimum :
- `OPENAI_API_KEY` — ta clé OpenAI
- `YOUTUBE_API_KEY` — ta clé YouTube Data API v3
- `MONGO_HOST=mongo` (default, ne pas changer en prod)
- `MILVUS_HOST=milvus` (default, ne pas changer en prod)

⚠ **Ne PAS** mettre `MONGO_HOST_OVERRIDE` ou `MILVUS_HOST_OVERRIDE` en prod — ces variables servent uniquement au dev local hors Docker.

### 4. Vérifier le réseau Docker partagé

```bash
docker network ls | grep web
```

Si absent (peu probable, Redline AI doit déjà l'avoir créé) :
```bash
docker network create web
```

### 5. Ajouter le bloc dans le Caddyfile global

Éditer `~/apps/infra/caddy/Caddyfile` (ou chemin équivalent selon ton infra) — ajouter en fin de fichier :

```caddy
# ═══════════════════════════════════════════════════
# Chess Agent FFE
# ═══════════════════════════════════════════════════
# Tuteur IA d'ouvertures aux échecs.
# Frontend Angular + Backend FastAPI/LangGraph + Milvus + MongoDB.

chess.duckdns.org {
    encode gzip zstd

    # Limite l'upload (pas attendu mais défense en profondeur)
    request_body {
        max_size 10MB
    }

    # API backend + Swagger UI
    @api path /api/* /docs* /openapi.json
    handle @api {
        reverse_proxy chess_agent_backend:8000
        # Le LLM peut être long, on bump le timeout
    }

    # Tout le reste = frontend Angular (SPA)
    handle {
        reverse_proxy chess_agent_frontend:80
    }
}
```

Reload Caddy sans downtime :
```bash
cd ~/apps/infra/caddy
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

---

## Premier déploiement

```bash
cd ~/apps/chess-agent

# Build + démarrage de la stack complète en mode prod
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Vérifier
docker compose ps                      # tous les services UP, milvus en "healthy"
docker compose logs -f backend         # tail logs backend
```

Patienter ~90s pour que Milvus passe `healthy` (start_period long).

### Ingérer les chunks Wikichess (UNE FOIS)

```bash
docker compose exec backend python scripts/fetch_wikichess.py
docker compose exec backend python scripts/chunk_wikichess.py
docker compose exec backend python scripts/ingest_chunks.py
```

Tu dois voir 83 chunks ingérés dans Milvus à la fin.

### Vérifier

Ouvre `https://chess.duckdns.org` dans un navigateur :
- Premier accès : 10-30s d'attente (Caddy obtient le certificat Let's Encrypt).
- Suivants : instantané, cadenas vert.

Test API :
```bash
curl https://chess.duckdns.org/api/v1/healthcheck
# → {"status":"ok"}
```

---

## Redéploiement (workflow récurrent)

```bash
ssh utilisateur@46.224.117.225
cd ~/apps/chess-agent
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Pour ne rebuild que le frontend (si seul le front a bougé, gain de temps) :
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build frontend
```

---

## Surveillance ressources

```bash
docker stats --no-stream
```

**Budget RAM attendu** :
- backend : ~200 MB
- frontend : ~30 MB
- milvus : ~1 GB
- etcd, minio : ~150 MB total
- mongo : ~150 MB

**Total chess agent** : ~1.5 GB. Avec Redline AI déjà sur la machine, marge confortable.

### Plan B si OOM

Si la stack consomme >2 GB stable et Hetzner kill des conteneurs :

1. **Quick win** : `docker compose -f docker-compose.yml -f docker-compose.prod.yml restart milvus` libère le cache.
2. **Migration Milvus-Lite** : passer en mode embedded (~100 MB RAM total). 30 min de boulot, à faire seulement si nécessaire.
3. **Upgrade VPS** : Hetzner CX22 → CX32 (8 GB, +€4/mois).

---

## Troubleshooting

### Le certificat HTTPS n'est pas émis
- Vérifier la propagation DNS : `nslookup chess.duckdns.org` doit renvoyer `46.224.117.225`.
- Logs Caddy : `docker logs caddy --tail 50`.
- Attendre 2 min entre l'ajout DNS et le premier accès.

### `502 Bad Gateway` sur `chess.duckdns.org`
- Le conteneur `chess_agent_frontend` n'est pas joignable depuis Caddy.
- Vérifier qu'il est bien sur le réseau `web` : `docker network inspect web | grep chess_agent_frontend`.
- Si absent, c'est que le compose.prod.yml n'a pas été appliqué — rejouer la commande `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.

### `503` sur `/api/*`
- Backend down ou pas connecté au réseau `web`.
- `docker compose logs backend --tail 50` → voir l'erreur de lifespan (probable : Milvus pas encore prêt, ou clé API manquante).

### Conflit de nom de container
- Si `chess_agent_backend` est déjà pris par une autre app, renommer dans `docker-compose.yml`. Vérifier d'abord : `docker ps -a | grep chess_agent`.

### Le front ne tape pas le bon backend
- En prod, `environment.production.ts` doit pointer vers `/api/v1` (relatif). Si tu vois des requêtes vers `localhost:8000` dans la console navigateur, c'est que le `fileReplacements` d'`angular.json` n'a pas été appliqué au build → rebuild via `docker compose ... build --no-cache frontend`.

---

## Désinstallation

Pour retirer Chess Agent du VPS sans toucher aux autres apps :

```bash
cd ~/apps/chess-agent
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
# -v supprime aussi les volumes (Mongo + Milvus persistants)
```

Retirer le bloc `chess.duckdns.org { ... }` du Caddyfile, puis reload Caddy.

Sur DuckDNS, retirer le sous-domaine `chess`.
